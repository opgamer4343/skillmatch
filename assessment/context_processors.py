from __future__ import annotations

from django.conf import settings


def assessment_settings(request):
    return {
        "ASSESSMENT_QUESTIONS_PER_ATTEMPT": getattr(settings, "ASSESSMENT_QUESTIONS_PER_ATTEMPT", 30),
        "ASSESSMENT_COOLDOWN_DAYS": getattr(settings, "ASSESSMENT_COOLDOWN_DAYS", 7),
    }
