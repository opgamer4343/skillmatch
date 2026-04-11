"""
SkillMatch Review Spam Detector
Analyses a review before saving and returns a spam_score (0-100).
  0-29  → Looks genuine  → auto-approve
  30-59 → Quick check    → auto-approve with flag
  60-84 → Hold for review → pending
  85+   → Likely spam    → pending + flagged
"""
import re
from typing import Dict, List, Tuple

SPAM_KEYWORDS = [
    "great company","awesome","very good","good company","nice company",
    "best company","excellent company","good experience","great experience",
    "nice experience","highly recommend","recommend this","5 stars",
    "click here","visit","http","www.",".com","whatsapp","telegram",
    "contact me","call me","earn money","work from home",
    "no experience needed","ok","okay","fine","average","nothing special",
]

GIBBERISH_PATTERN = re.compile(
    r'(.)\1{4,}|[^\w\s,.!?]{4,}|\b(\w)\s\2\s\2\b',
    re.IGNORECASE
)

MIN_BODY_WORDS       = 30
MIN_EXPERIENCE_WORDS = 15


def analyse_review(
    title: str,
    body: str,
    interview_experience: str,
    overall_rating: int,
    process_rating: int,
    communication_rating: int,
    reviewer_app_count: int = 0,
) -> Tuple[int, List[str]]:
    score = 0
    flags = []

    body_words       = len(body.strip().split())
    experience_words = len(interview_experience.strip().split())
    title_words      = len(title.strip().split())

    # 1. Too short
    if body_words < MIN_BODY_WORDS:
        pts = int((MIN_BODY_WORDS - body_words) * 1.2)
        score += pts
        flags.append(f"Review body too short ({body_words} words, min {MIN_BODY_WORDS})")

    if experience_words < MIN_EXPERIENCE_WORDS:
        pts = int((MIN_EXPERIENCE_WORDS - experience_words) * 1.5)
        score += pts
        flags.append(f"Interview experience too short ({experience_words} words, min {MIN_EXPERIENCE_WORDS})")

    if title_words <= 2:
        score += 10
        flags.append("Review title too short")

    # 2. Spam keywords
    combined = (title + " " + body + " " + interview_experience).lower()
    found_kw = [kw for kw in SPAM_KEYWORDS if kw in combined]
    if found_kw:
        score += min(len(found_kw) * 8, 30)
        flags.append(f"Suspicious keywords: {', '.join(found_kw[:3])}")

    # 3. Gibberish
    if GIBBERISH_PATTERN.search(body) or GIBBERISH_PATTERN.search(interview_experience):
        score += 25
        flags.append("Gibberish or repeated characters detected")

    # 4. All ratings identical
    if overall_rating == process_rating == communication_rating:
        score += 8
        flags.append("All ratings identical")

    # 5. Extreme rating with thin content
    if overall_rating == 5 and body_words < 50:
        score += 12
        flags.append("5-star rating with very short review")
    if overall_rating == 1 and body_words < 50:
        score += 12
        flags.append("1-star rating with very short review")

    # 6. Copy-paste body == experience
    body_clean = re.sub(r'\s+', ' ', body.strip().lower())
    exp_clean  = re.sub(r'\s+', ' ', interview_experience.strip().lower())
    if body_clean == exp_clean:
        score += 30
        flags.append("Review body and interview experience are identical")
    elif len(body_clean) > 30 and body_clean[:60] == exp_clean[:60]:
        score += 20
        flags.append("Review body and interview experience appear copy-pasted")

    # 7. ALL CAPS
    caps_ratio = sum(1 for c in body if c.isupper()) / max(len(body), 1)
    if caps_ratio > 0.5 and body_words > 5:
        score += 15
        flags.append("Excessive capital letters")

    # 8. No application history
    if reviewer_app_count == 0:
        score += 20
        flags.append("Reviewer has no application history with this company")

    return min(score, 100), flags


def spam_verdict(score: int) -> Dict:
    if score >= 85:
        return {"label": "🔴 Likely Spam",   "color": "#dc2626", "approve": False}
    if score >= 60:
        return {"label": "🟠 Needs Review",  "color": "#d97706", "approve": False}
    if score >= 30:
        return {"label": "🟡 Quick Check",   "color": "#ca8a04", "approve": True}
    return     {"label": "🟢 Looks Genuine", "color": "#16a34a", "approve": True}