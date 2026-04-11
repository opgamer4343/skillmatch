from __future__ import annotations

from typing import Iterable, Mapping

TECHNICAL_WEIGHT = 0.80
SOFT_WEIGHT = 0.20


def _safe_percent(correct: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((correct / total) * 100, 2)


def get_score_band(score: float) -> str:
    if score >= 90:
        return "expert"
    if score >= 80:
        return "strong"
    if score >= 70:
        return "intermediate"
    if score >= 50:
        return "foundation"
    return "beginner"


def calculate_scores(answer_rows: Iterable[Mapping]) -> dict:
    technical_total = technical_correct = 0
    soft_total = soft_correct = 0
    for row in answer_rows:
        category_type = row.get("category_type")
        is_correct = bool(row.get("is_correct"))
        if category_type == "soft":
            soft_total += 1
            if is_correct:
                soft_correct += 1
        else:
            technical_total += 1
            if is_correct:
                technical_correct += 1
    technical_score = _safe_percent(technical_correct, technical_total)
    soft_score = _safe_percent(soft_correct, soft_total)
    overall_score = round((technical_score * TECHNICAL_WEIGHT) + (soft_score * SOFT_WEIGHT), 2)
    return {
        "technical_score": technical_score,
        "soft_score": soft_score,
        "overall_score": overall_score,
        "score_band": get_score_band(overall_score),
        "technical_correct": technical_correct,
        "technical_total": technical_total,
        "soft_correct": soft_correct,
        "soft_total": soft_total,
    }


def calculate_assessment_scores(questions, answers):
    rows = []
    for idx, question in enumerate(questions):
        answer = answers[idx] if idx < len(answers) else None
        rows.append({
            "category_type": question.get("category_type", "technical"),
            "is_correct": bool(getattr(answer, "is_correct", False)),
        })
    return calculate_scores(rows)


def get_result_message(score_band: str) -> str:
    messages = {
        "expert": "Outstanding work. You’re showing high readiness for competitive internship roles.",
        "strong": "You have a solid profile. A bit more refinement can push you into top-tier readiness.",
        "intermediate": "You have good fundamentals, but some gaps still need attention before tougher roles.",
        "foundation": "You’re building the base. Focused practice can raise your score quickly.",
        "beginner": "You need stronger fundamentals first. Start with basics and build consistency.",
    }
    return messages.get(score_band, "Keep improving with focused practice.")
