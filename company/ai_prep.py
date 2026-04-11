"""
AI Interview Preparation Generator
Uses Google Gemini to generate role-specific prep questions,
company background summary, and interview tips.
"""
import json
import logging
import os
from typing import Any, Dict, List

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
except Exception:
    genai = None

DEFAULT_MODEL = getattr(settings, "GOOGLE_GENAI_MODEL", "gemini-2.0-flash")


def _get_client():
    key = (
        getattr(settings, "GEMINI_API_KEY", None)
        or getattr(settings, "GOOGLE_API_KEY", None)
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )
    if not genai or not key:
        return None
    try:
        return genai.Client(api_key=key)
    except Exception:
        logger.exception("Gemini client init failed")
        return None


def _parse_json(text: str) -> Any:
    text = (text or "").strip()
    for attempt in [text] + [
        b.replace("json", "", 1).strip()
        for b in text.split("```") if b.strip()
    ]:
        try:
            return json.loads(attempt)
        except Exception:
            pass
    raise ValueError("No JSON found in response")


def generate_interview_prep(interview) -> Dict[str, Any]:
    """
    Generate a full interview prep pack for a student.
    Returns dict with questions, tips, company_summary.
    Falls back to static content if Gemini unavailable.
    """
    application = interview.application
    internship  = application.internship
    student     = application.applicant
    profile     = getattr(student, "student_profile", None)

    role        = internship.title
    company_name = getattr(
        getattr(internship.company, "company_profile", None),
        "company_name", internship.company.email
    )
    description  = internship.description or ""
    required_skills = internship.required_skills or []
    student_skills  = getattr(profile, "skills", []) or []
    interview_type  = interview.get_interview_type_display()

    # Build fallback in case AI is unavailable
    fallback = _fallback_prep(role, company_name, required_skills, interview_type)

    client = _get_client()
    if not client:
        return fallback

    prompt = f"""You are an expert interview coach preparing a student for an internship interview.

INTERVIEW DETAILS:
- Role: {role}
- Company: {company_name}
- Interview Type: {interview_type}
- Job Description: {description[:500]}
- Required Skills: {", ".join(required_skills)}
- Student Skills: {", ".join(student_skills)}

Generate a comprehensive interview prep pack. Return ONLY valid JSON:

{{
  "company_summary": "2-3 sentences about what the company likely does based on name/role (be general if unknown)",
  "questions": [
    {{
      "category": "Technical",
      "question": "Specific technical question about the role",
      "hint": "Key point to cover in your answer",
      "difficulty": "easy|medium|hard"
    }},
    {{
      "category": "Behavioural",
      "question": "Tell me about a time when...",
      "hint": "Use the STAR method: Situation, Task, Action, Result",
      "difficulty": "medium"
    }}
  ],
  "tips": [
    {{
      "icon": "🎯",
      "title": "Short tip title",
      "body": "Actionable tip description"
    }}
  ],
  "checklist": [
    "Research {company_name}'s recent projects",
    "Prepare 2-3 examples from past work",
    "Test your camera and microphone 30 min before",
    "Have your CV and portfolio open"
  ]
}}

Rules:
- Generate exactly 8 questions: 4 technical, 2 behavioural, 2 situational
- Generate exactly 5 tips specific to this role and interview type
- Generate exactly 5 checklist items
- Keep each question realistic and role-specific
- Return ONLY JSON, no markdown"""

    try:
        resp = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        data = _parse_json(getattr(resp, "text", "") or "")
        if isinstance(data, dict) and data.get("questions"):
            return data
        return fallback
    except Exception:
        logger.exception("Gemini prep generation failed")
        return fallback


def _fallback_prep(role: str, company: str, skills: List[str], iv_type: str) -> Dict:
    """Static fallback when Gemini is unavailable."""
    tech_q = skills[:3] if skills else ["your core skills"]
    return {
        "company_summary": (
            f"{company} is looking for a motivated {role} intern to join their team. "
            f"They work with {', '.join(tech_q[:2]) if tech_q else 'modern technologies'}. "
            "Research the company website before your interview for more context."
        ),
        "questions": [
            {"category": "Technical",    "difficulty": "medium",
             "question": f"Can you walk me through a project where you used {tech_q[0] if tech_q else 'your skills'}?",
             "hint": "Describe the problem, your approach, and the outcome with specific metrics."},
            {"category": "Technical",    "difficulty": "medium",
             "question": "How do you approach debugging a problem you've never seen before?",
             "hint": "Show systematic thinking: reproduce, isolate, fix, test."},
            {"category": "Technical",    "difficulty": "hard",
             "question": f"What are the key differences between {tech_q[0] if tech_q else 'option A'} and {tech_q[1] if len(tech_q) > 1 else 'option B'}?",
             "hint": "Be specific about trade-offs, use cases, and performance considerations."},
            {"category": "Technical",    "difficulty": "easy",
             "question": "What tools do you use for version control and collaboration?",
             "hint": "Mention Git, GitHub/GitLab, branching strategies, pull requests."},
            {"category": "Behavioural",  "difficulty": "medium",
             "question": "Tell me about a time you faced a tight deadline. How did you handle it?",
             "hint": "STAR method: Situation → Task → Action → Result. Focus on the result."},
            {"category": "Behavioural",  "difficulty": "medium",
             "question": "Describe a situation where you had to learn something new very quickly.",
             "hint": "Show learning agility, resourcefulness, and a growth mindset."},
            {"category": "Situational",  "difficulty": "medium",
             "question": f"If you were given a {role} task with unclear requirements, what would you do?",
             "hint": "Ask clarifying questions, document assumptions, confirm with stakeholders."},
            {"category": "Situational",  "difficulty": "easy",
             "question": "Where do you see yourself in 2 years, and how does this internship fit?",
             "hint": "Be specific about skills you want to gain and how they align with the role."},
        ],
        "tips": [
            {"icon": "🔍", "title": "Research the company",
             "body": f"Spend 20 minutes reading about {company}. Know their product, team size, and recent news."},
            {"icon": "📂", "title": "Prepare your portfolio",
             "body": "Have 2-3 projects ready to discuss. For each: what was the problem, what you built, what the outcome was."},
            {"icon": "⏰", "title": f"Test your setup {'30 min early' if iv_type == 'Video' else 'the day before'}",
             "body": f"{'Check camera, mic, lighting, and internet connection before the call.' if iv_type == 'Video' else 'Plan your route and arrive 10 minutes early.'}"},
            {"icon": "❓", "title": "Prepare 3 questions to ask them",
             "body": "Ask about team culture, tech stack, or what success looks like in this role. It shows genuine interest."},
            {"icon": "🧘", "title": "Manage interview nerves",
             "body": "Take 3 deep breaths before. Pause before answering — it's okay to think for 5 seconds."},
        ],
        "checklist": [
            f"Research {company}'s website and LinkedIn page",
            "Prepare examples for 3 past projects with specific outcomes",
            f"{'Test camera, microphone, and internet connection' if iv_type == 'Video' else 'Plan your commute route'}",
            "Print / open your CV to reference during the interview",
            "Prepare 3 thoughtful questions to ask the interviewer",
        ],
    }