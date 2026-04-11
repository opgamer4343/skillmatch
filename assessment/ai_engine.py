import json
import logging
import os
import random
from typing import Any, Dict, List, Optional

from django.conf import settings

from .question_bank import QUESTION_BANK

logger = logging.getLogger(__name__)

try:
    from google import genai
except Exception:  # pragma: no cover
    genai = None


DEFAULT_MODEL = getattr(settings, "GOOGLE_GENAI_MODEL", "gemini-2.0-flash")


def _get_client():
    api_key = (
        getattr(settings, "GOOGLE_API_KEY", None)
        or getattr(settings, "GEMINI_API_KEY", None)
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )
    if genai is None or not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        logger.exception("Failed to initialize Google GenAI client.")
        return None


def _extract_json_block(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty AI response")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    if "```" in text:
        blocks = text.split("```")
        for block in blocks:
            cleaned = block.replace("json", "", 1).strip()
            if not cleaned:
                continue
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                continue
    first_obj = text.find("{")
    first_arr = text.find("[")
    candidates = [i for i in [first_obj, first_arr] if i >= 0]
    if candidates:
        start = min(candidates)
        for end in range(len(text), start, -1):
            snippet = text[start:end].strip()
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue
    raise ValueError("No valid JSON payload found in model response.")


def _generate_json(prompt: str, fallback: Any) -> Any:
    client = _get_client()
    if client is None:
        return fallback
    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
        )
        payload = getattr(response, "text", "") or ""
        return _extract_json_block(payload)
    except Exception:
        logger.exception("Google GenAI request failed. Using fallback.")
        return fallback


def _fallback_questions(weak_areas: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    weak_areas = weak_areas or []
    preferred = []
    for item in QUESTION_BANK:
        category = str(item.get("category", "")).lower()
        if any(area.lower() in category for area in weak_areas):
            preferred.append(item)
    pool = preferred + [q for q in QUESTION_BANK if q not in preferred]
    result = pool[:30]
    if len(result) < 30:
        idx = 0
        while len(result) < 30 and QUESTION_BANK:
            result.append(QUESTION_BANK[idx % len(QUESTION_BANK)])
            idx += 1
    normalized = []
    for i, item in enumerate(result, start=1):
        normalized.append({
            "id": i,
            "source": "db",
            "category": item.get("category", "general"),
            "category_type": item.get("category_type", "technical"),
            "difficulty": item.get("difficulty", "medium"),
            "text": item.get("text", ""),
            "options": item.get("options", []),
            "correct_index": item.get("correct_index", 0),
            "explanation": item.get("explanation", ""),
        })
    return normalized[:30]


# ─── DB question helper ───────────────────────────────────────────────────────

def _db_questions_as_dicts(count: int) -> List[Dict[str, Any]]:
    """Pull `count` random technical questions from the DB Question table."""
    from django.apps import apps
    try:
        Question = apps.get_model("assessment", "Question")
        ids = list(
            Question.objects.filter(
                category__category_type="technical"
            ).values_list("id", flat=True)
        )
        if not ids:
            raise LookupError("No technical questions in DB")
        sample_ids = random.sample(ids, min(count, len(ids)))
        rows = Question.objects.filter(id__in=sample_ids).select_related("category")
        return [
            {
                "id": f"db_{q.id}",
                "source": "db",
                "category": q.category.name,
                "category_type": q.category.category_type,
                "difficulty": q.difficulty,
                "text": q.text,
                "options": q.options,
                "correct_index": q.correct_index,
                "explanation": q.explanation or "",
            }
            for q in rows
        ]
    except Exception:
        logger.exception("Could not fetch DB questions; using QUESTION_BANK slice")
        technical_bank = [q for q in QUESTION_BANK if q.get("category_type") == "technical"]
        sample = random.sample(technical_bank, min(count, len(technical_bank)))
        return [
            {
                "id": f"db_{i}",
                "source": "db",
                "category": q.get("category", "coding"),
                "category_type": "technical",
                "difficulty": q.get("difficulty", "medium"),
                "text": q["text"],
                "options": q["options"],
                "correct_index": q["correct_index"],
                "explanation": q.get("explanation", ""),
            }
            for i, q in enumerate(sample, start=1)
        ]


# ─── Hybrid generator ─────────────────────────────────────────────────────────

def generate_hybrid_questions(
    db_count: int = 10,
    weak_areas: Optional[List[str]] = None,
    previous_score: float = 0,
    is_retest: bool = False,
) -> List[Dict[str, Any]]:
    """
    Hybrid assessment: `db_count` questions from the database (all technical) +
    (30 - db_count) questions generated by Gemini AI (technical + soft).
    The two batches are shuffled together before being returned.
    Falls back to the local question bank when Gemini is unavailable.
    """
    total = 30
    ai_count = total - db_count
    weak_areas = weak_areas or []

    # 1. DB questions
    db_qs = _db_questions_as_dicts(db_count)

    # 2. AI prompt
    if is_retest:
        ai_prompt = (
            f"You are generating a RETEST question set for a skill-matching internship platform.\n\n"
            f"Student weak areas: {json.dumps(weak_areas)}\n"
            f"Previous overall score: {previous_score}\n\n"
            f"IMPORTANT: The student has already answered {db_count} standard technical questions "
            f"from a verified question bank (basic coding, finance, marketing, design, data science).\n"
            f"Generate {ai_count} FRESH questions that:\n"
            f"- Target the student's weak areas heavily\n"
            f"- Include medium and hard difficulty items\n"
            f"- Mix technical domains AND soft skills\n"
            f"- Are scenario-based and practical (not basic definitions)\n"
            f"- Do NOT repeat concepts already covered by standard bank questions\n\n"
            f"Return exactly {ai_count} questions as a strict JSON array. No markdown, no text outside JSON.\n"
            f'Each item: {{"id":1,"source":"ai","category":"coding","category_type":"technical",'
            f'"difficulty":"medium","text":"...","options":["A","B","C","D"],"correct_index":2,"explanation":"..."}}'
        )
    else:
        ai_prompt = (
            f"You are generating assessment questions for a skill-matching internship platform.\n\n"
            f"IMPORTANT: The student will also answer {db_count} verified technical questions from a "
            f"standard question bank (basic coding, finance, marketing, design, data science).\n"
            f"Generate {ai_count} COMPLEMENTARY questions that:\n"
            f"- Go beyond basic definitions — focus on real-world, scenario-based challenges\n"
            f"- Cover technical domains (coding, finance, marketing, design, data science) AND soft skills\n"
            f"- Include a balanced easy/medium/hard spread\n"
            f"- Do NOT duplicate basic definitional or textbook questions\n\n"
            f"Return exactly {ai_count} questions as a strict JSON array. No markdown, no text outside JSON.\n"
            f'Each item: {{"id":1,"source":"ai","category":"coding","category_type":"technical",'
            f'"difficulty":"medium","text":"...","options":["A","B","C","D"],"correct_index":2,"explanation":"..."}}'
        )

    # Build fallback (slice of question bank, different from DB slice)
    fallback_pool = _fallback_questions(weak_areas=weak_areas)
    fallback_ai = fallback_pool[db_count: db_count + ai_count]
    if len(fallback_ai) < ai_count:
        fallback_ai = fallback_pool[:ai_count]
    for i, q in enumerate(fallback_ai):
        q["source"] = "ai"
        q["id"] = f"ai_{i + 1}"

    raw = _generate_json(ai_prompt, fallback_ai)
    ai_qs_raw = raw[:ai_count] if isinstance(raw, list) and len(raw) >= ai_count else fallback_ai

    # Normalise AI questions
    ai_qs = [
        {
            "id": f"ai_{i + 1}",
            "source": "ai",
            "category": q.get("category", "general"),
            "category_type": q.get("category_type", "technical"),
            "difficulty": q.get("difficulty", "medium"),
            "text": q.get("text", ""),
            "options": q.get("options", []),
            "correct_index": int(q.get("correct_index", 0)),
            "explanation": q.get("explanation", ""),
        }
        for i, q in enumerate(ai_qs_raw)
    ]

    # 3. Merge, shuffle, add display sequence
    combined = db_qs + ai_qs
    random.shuffle(combined)
    for i, q in enumerate(combined, start=1):
        q["seq"] = i
    return combined


# ─── Pure-AI generators (original / "ai" mode) ───────────────────────────────

def generate_initial_questions() -> List[Dict[str, Any]]:
    """Returns 30 all-AI assessment questions; falls back to question bank."""
    fallback = _fallback_questions()
    prompt = (
        "You are generating assessment questions for a skill matching and internship finder platform.\n\n"
        "Create exactly 30 multiple-choice questions in strict JSON array format.\n"
        "Requirements:\n"
        "- 24 technical questions across: coding, finance, marketing, design, data science\n"
        "- 6 soft skill questions\n"
        "- Mixed difficulty: easy, medium, hard\n"
        "- Exactly 4 options per question; correct_index is 0-3\n"
        "- Market-level, internship-ready, practical\n"
        "- Return only JSON, no markdown\n\n"
        'JSON shape: {"id":1,"source":"ai","category":"coding","category_type":"technical",'
        '"difficulty":"medium","text":"...","options":["A","B","C","D"],"correct_index":2,"explanation":"..."}'
    )
    data = _generate_json(prompt, fallback)
    return data if isinstance(data, list) and len(data) == 30 else fallback


def generate_gap_questions(weak_areas: List[str], previous_score: float) -> List[Dict[str, Any]]:
    fallback = _fallback_questions(weak_areas=weak_areas)
    prompt = (
        f"You are generating a retest question set for a student assessment.\n\n"
        f"Student weak areas: {json.dumps(weak_areas)}\n"
        f"Previous overall score: {previous_score}\n\n"
        f"Create exactly 30 multiple-choice questions in strict JSON array format.\n"
        f"Target weak areas, balanced technical + soft, 4 options each. Return only JSON.\n\n"
        f'JSON shape: {{"id":1,"source":"ai","category":"coding","category_type":"technical",'
        f'"difficulty":"medium","text":"...","options":["A","B","C","D"],"correct_index":2,"explanation":"..."}}'
    )
    data = _generate_json(prompt, fallback)
    return data if isinstance(data, list) and len(data) == 30 else fallback


def generate_course_recommendations(overall_score: float, weak_areas: List[str], skills: List[str]) -> List[Dict[str, Any]]:
    fallback = [
        {"title": "Python for Everybody", "provider": "Coursera",
         "url": "https://www.coursera.org/specializations/python",
         "platform": "Coursera", "duration_hours": 20,
         "reason": "Builds strong beginner-friendly technical fundamentals.", "priority": 1},
        {"title": "Google Data Analytics", "provider": "Coursera",
         "url": "https://www.coursera.org/professional-certificates/google-data-analytics",
         "platform": "Coursera", "duration_hours": 30,
         "reason": "Improves data handling and business analysis skills.", "priority": 2},
        {"title": "Introduction to Marketing", "provider": "YouTube",
         "url": "https://www.youtube.com/results?search_query=introduction+to+marketing+course",
         "platform": "YouTube", "duration_hours": 6,
         "reason": "Covers campaign basics, targeting, and messaging.", "priority": 3},
        {"title": "Figma UI/UX Crash Course", "provider": "YouTube",
         "url": "https://www.youtube.com/results?search_query=figma+ui+ux+crash+course",
         "platform": "YouTube", "duration_hours": 5,
         "reason": "Helps improve design thinking and interface fundamentals.", "priority": 4},
        {"title": "Communication Skills for Career Growth", "provider": "Coursera",
         "url": "https://www.coursera.org/search?query=communication%20skills",
         "platform": "Coursera", "duration_hours": 8,
         "reason": "Strengthens soft skills needed for interviews and teamwork.", "priority": 5},
    ]
    prompt = (
        f"Recommend exactly 5 courses for a student.\n\n"
        f"Student details:\n- overall_score: {overall_score}\n"
        f"- weak_areas: {json.dumps(weak_areas)}\n- existing_skills: {json.dumps(skills)}\n\n"
        f"Mix YouTube, Coursera, focus on weak areas and internship readiness. Return only JSON array.\n"
        f'Shape: {{"title":"...","provider":"...","url":"...","platform":"...","duration_hours":6,"reason":"...","priority":1}}'
    )
    data = _generate_json(prompt, fallback)
    return data if isinstance(data, list) and len(data) == 5 else fallback


def analyze_score(technical_score: float, soft_score: float, overall_score: float, skills: List[str]) -> Dict[str, Any]:
    fallback = {
        "strengths": skills[:3] if skills else ["Adaptability", "Learning potential"],
        "weak_areas": ["Problem solving", "Communication"] if overall_score < 70 else ["Advanced specialization"],
        "message": "You have a workable base. Focus on consistency in your weaker areas to improve internship readiness.",
        "job_readiness": "developing" if overall_score < 70 else "ready",
        "improvement_priority": "Focus first on the lowest-scoring skill category and practice timed questions weekly.",
    }
    prompt = (
        f"Analyze a student's assessment performance and return strict JSON.\n\n"
        f"Input: technical_score={technical_score}, soft_score={soft_score}, "
        f"overall_score={overall_score}, declared_skills={json.dumps(skills)}\n\n"
        f"Return JSON with: strengths (3-5 items), weak_areas (3-5 items), "
        f"message (short personalized readiness message), "
        f"job_readiness (beginner|developing|ready|strong), "
        f"improvement_priority (one practical next step). Return only JSON."
    )
    data = _generate_json(prompt, fallback)
    return data if isinstance(data, dict) else fallback
