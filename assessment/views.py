from datetime import timedelta
from functools import wraps
from pathlib import Path
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.db import IntegrityError
from django.http import FileResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Max

from accounts.models import StudentProfile
from .ai_engine import (
    analyze_score,
    generate_course_recommendations,
    generate_gap_questions,
    generate_hybrid_questions,
    generate_initial_questions,
)
from .cv_generator import generate_cv_content, generate_cv_pdf
from .models import AssessmentAttempt, AssessmentAnswer, CourseRecommendation, Question, SkillCategory, StudentCV
from .question_bank import QUESTION_BANK
from .scoring import calculate_assessment_scores


def _student_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if getattr(request.user, "role", None) != "student":
            messages.error(request, "You are not allowed to access the assessment area.")
            return redirect("accounts:welcome")
        return view_func(request, *args, **kwargs)
    return wrapped


def _latest_attempt(user):
    return AssessmentAttempt.objects.filter(student=user).order_by("-attempt_number", "-started_at").first()


def _cooldown_remaining(user):
    latest = _latest_attempt(user)
    if not latest or latest.status != AssessmentAttempt.Status.COMPLETED or not latest.completed_at:
        return None
    next_time = latest.completed_at + timedelta(days=getattr(settings, "ASSESSMENT_COOLDOWN_DAYS", 7))
    remaining = next_time - timezone.now()
    return remaining if remaining.total_seconds() > 0 else None


def _ensure_question_bank():
    if Question.objects.exists():
        return
    categories = {}
    for item in QUESTION_BANK:
        name = item.get("category", "General")
        category_type = item.get("category_type", "technical")
        if name not in categories:
            categories[name], _ = SkillCategory.objects.get_or_create(name=name, defaults={"category_type": category_type})
        Question.objects.create(
            category=categories[name],
            text=item["text"],
            options=item["options"],
            correct_index=item["correct_index"],
            difficulty=item.get("difficulty", "medium"),
            explanation=item.get("explanation", ""),
            is_ai_generated=False,
        )


def _session_questions(attempt_id):
    return f"assessment_questions_{attempt_id}"


def _session_index(attempt_id):
    return f"assessment_current_index_{attempt_id}"


@_student_required
def assessment_home(request):
    student_profile = StudentProfile.objects.filter(user=request.user).first()
    latest_attempt = _latest_attempt(request.user)
    attempts = AssessmentAttempt.objects.filter(student=request.user).order_by("attempt_number", "started_at")
    courses = CourseRecommendation.objects.filter(student=request.user).order_by("is_completed", "priority", "id")
    cooldown = _cooldown_remaining(request.user)
    from .scoring import get_result_message  # noqa: local import to avoid circular
    result_message = ""
    if latest_attempt:
        result_message = get_result_message(latest_attempt.score_band)

    cooldown_seconds = 0
    if cooldown:
        cooldown_seconds = int(cooldown.total_seconds())

    return render(request, "assessment/home.html", {
        "student_profile": student_profile,
        "latest_attempt": latest_attempt,
        "attempts": attempts,
        "courses": courses,
        "cooldown": cooldown,
        "can_retake": cooldown is None,
        "can_start": cooldown is None,
        "result_message": result_message,
        "cooldown_seconds": cooldown_seconds,
    })


@_student_required
def start_assessment(request):
    cooldown = _cooldown_remaining(request.user)
    if cooldown:
        messages.warning(request, "Assessment retake is available after the cooldown ends.")
        return redirect("assessment:home")

    _ensure_question_bank()
    previous_attempt = _latest_attempt(request.user)

    # Use the actual MAX attempt_number across ALL attempts (including abandoned ones)
    max_num = AssessmentAttempt.objects.filter(student=request.user).aggregate(
        max_num=Max("attempt_number")
    )["max_num"] or 0
    next_attempt_number = max_num + 1

    weak_areas = []
    previous_score = 0
    if previous_attempt and previous_attempt.status == AssessmentAttempt.Status.COMPLETED:
        previous_score = float(previous_attempt.overall_score or 0)
        weak_areas = list(previous_attempt.weak_areas or [])

    mode = getattr(settings, "ASSESSMENT_MODE", "hybrid").lower()
    db_count = getattr(settings, "ASSESSMENT_HYBRID_DB_COUNT", 10)

    if mode == "hybrid":
        generated_questions = generate_hybrid_questions(
            db_count=db_count,
            weak_areas=weak_areas,
            previous_score=previous_score,
            is_retest=bool(previous_attempt),
        )
    elif previous_attempt:
        generated_questions = generate_gap_questions(weak_areas, previous_score)
    else:
        generated_questions = generate_initial_questions()

    try:
        attempt = AssessmentAttempt.objects.create(student=request.user, attempt_number=next_attempt_number, status=AssessmentAttempt.Status.STARTED)
    except IntegrityError:
        # Race condition: another request created the same number; recalculate
        max_num = AssessmentAttempt.objects.filter(student=request.user).aggregate(
            max_num=Max("attempt_number")
        )["max_num"] or 0
        attempt = AssessmentAttempt.objects.create(student=request.user, attempt_number=max_num + 1, status=AssessmentAttempt.Status.STARTED)
    request.session[_session_questions(attempt.id)] = generated_questions
    request.session[_session_index(attempt.id)] = 0
    ai_count = len(generated_questions) - db_count if mode == "hybrid" else len(generated_questions)
    return render(request, "assessment/intro.html", {
        "attempt": attempt,
        "question_count": len(generated_questions),
        "assessment_mode": mode,
        "db_count": db_count if mode == "hybrid" else 0,
        "ai_count": ai_count,
    })


@_student_required
def question_view(request, attempt_id):
    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id, student=request.user)
    if attempt.status == AssessmentAttempt.Status.COMPLETED:
        return redirect("assessment:finish", attempt_id=attempt.id)

    questions = request.session.get(_session_questions(attempt.id)) or generate_initial_questions()
    request.session[_session_questions(attempt.id)] = questions
    current_index = int(request.session.get(_session_index(attempt.id), 0))

    if request.method == "POST":
        if current_index < len(questions):
            current_question = questions[current_index]
            selected = request.POST.get("selected_answer")
            time_taken = int(request.POST.get("time_taken_seconds") or 60)
            selected_int = int(selected) if str(selected).isdigit() else None
            AssessmentAnswer.objects.create(
                attempt=attempt,
                question=None,
                selected_answer=selected_int,
                is_correct=(selected_int == int(current_question.get("correct_index", 0))) if selected_int is not None else False,
                time_taken_seconds=max(0, min(time_taken, 60)),
            )

        current_index += 1
        request.session[_session_index(attempt.id)] = current_index
        if current_index >= len(questions):
            return redirect("assessment:finish", attempt_id=attempt.id)
        return redirect("assessment:question", attempt_id=attempt.id)

    if current_index >= len(questions):
        return redirect("assessment:finish", attempt_id=attempt.id)

    question = questions[current_index]
    return render(request, "assessment/question.html", {
        "attempt": attempt,
        "question": question,
        "current_index": current_index + 1,
        "total_questions": len(questions),
        "timer_seconds": 60,
    })


@_student_required
def finish_assessment(request, attempt_id):
    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id, student=request.user)
    questions = request.session.get(_session_questions(attempt.id)) or []
    answers = list(AssessmentAnswer.objects.filter(attempt=attempt).order_by("id"))

    if attempt.status != AssessmentAttempt.Status.COMPLETED:
        result = calculate_assessment_scores(questions, answers)
        attempt.technical_score = result["technical_score"]
        attempt.soft_score = result["soft_score"]
        attempt.overall_score = result["overall_score"]
        attempt.score_band = result["score_band"]
        attempt.completed_at = timezone.now()
        attempt.status = AssessmentAttempt.Status.COMPLETED

        skills = list(getattr(getattr(request.user, "student_profile", None), "skills", []) or [])
        analysis = analyze_score(float(attempt.technical_score), float(attempt.soft_score), float(attempt.overall_score), skills)
        attempt.strengths = analysis.get("strengths", [])
        attempt.weak_areas = analysis.get("weak_areas", [])
        attempt.job_readiness_message = analysis.get("message", "")
        attempt.improvement_priority = analysis.get("improvement_priority", "")
        attempt.save()

        CourseRecommendation.objects.filter(student=request.user).delete()
        generated_courses = generate_course_recommendations(float(attempt.overall_score), attempt.weak_areas, skills)
        for item in generated_courses:
            CourseRecommendation.objects.create(
                student=request.user,
                title=item.get("title", ""),
                provider=item.get("provider", ""),
                url=item.get("url", "https://example.com"),
                platform=item.get("platform", "Online"),
                duration_hours=item.get("duration_hours", 0) or 0,
                reason=item.get("reason", ""),
                priority=item.get("priority", 1) or 1,
                is_completed=False,
            )
        request.session.pop(_session_questions(attempt.id), None)
        request.session.pop(_session_index(attempt.id), None)

    analysis = {
        "strengths": attempt.strengths,
        "weak_areas": attempt.weak_areas,
        "message": attempt.job_readiness_message,
        "improvement_priority": attempt.improvement_priority,
    }

    # Hybrid breakdown stats (only meaningful when session questions are still around)
    hybrid_ctx = {}
    saved_questions = request.session.get(_session_questions(attempt.id)) or questions
    if saved_questions and any(q.get("source") in ("db", "ai") for q in saved_questions):
        all_answers = list(AssessmentAnswer.objects.filter(attempt=attempt).order_by("id"))
        db_correct = db_total = ai_correct = ai_total = 0
        for idx, q in enumerate(saved_questions):
            ans = all_answers[idx] if idx < len(all_answers) else None
            correct = bool(getattr(ans, "is_correct", False))
            if q.get("source") == "db":
                db_total += 1
                if correct:
                    db_correct += 1
            else:
                ai_total += 1
                if correct:
                    ai_correct += 1
        if db_total > 0 and ai_total > 0:
            hybrid_ctx = {
                "hybrid_db_score": round(db_correct / db_total * 100, 1),
                "hybrid_db_correct": db_correct,
                "hybrid_db_total": db_total,
                "hybrid_ai_score": round(ai_correct / ai_total * 100, 1),
                "hybrid_ai_correct": ai_correct,
                "hybrid_ai_total": ai_total,
            }

    from .scoring import get_result_message
    return render(request, "assessment/results.html", {
        "attempt": attempt,
        "analysis": analysis,
        "courses": CourseRecommendation.objects.filter(student=request.user),
        "result_message": get_result_message(attempt.score_band),
        **hybrid_ctx,
    })


@_student_required
def score_history_json(request):
    attempts = AssessmentAttempt.objects.filter(
        student=request.user, status=AssessmentAttempt.Status.COMPLETED
    ).order_by("attempt_number", "started_at")

    labels = []
    overall_scores = []
    technical_scores = []
    soft_scores = []
    bands = []
    dates = []

    for a in attempts:
        labels.append(f"Attempt {a.attempt_number}")
        overall_scores.append(float(a.overall_score or 0))
        technical_scores.append(float(a.technical_score or 0))
        soft_scores.append(float(a.soft_score or 0))
        bands.append(a.score_band or "")
        dates.append(a.completed_at.strftime("%b %d, %Y") if a.completed_at else "")

    return JsonResponse({
        "labels": labels,
        "overall_scores": overall_scores,
        "technical_scores": technical_scores,
        "soft_scores": soft_scores,
        "bands": bands,
        "dates": dates,
        "count": len(labels),
    })


@_student_required
@require_POST
def mark_course_complete(request, pk):
    course = get_object_or_404(CourseRecommendation, id=pk, student=request.user)
    course.is_completed = True
    course.save(update_fields=["is_completed"])
    messages.success(request, "Course marked as completed.")
    return redirect("assessment:home")


@_student_required
def cv_home(request):
    return render(request, "assessment/cv_home.html", {
        "student_cv": StudentCV.objects.filter(user=request.user).first(),
        "latest_attempt": _latest_attempt(request.user),
        "student_profile": StudentProfile.objects.filter(user=request.user).first(),
    })


@_student_required
def cv_upload(request):
    if request.method == "POST" and request.FILES.get("cv_file"):
        cv_obj, _ = StudentCV.objects.get_or_create(user=request.user, defaults={"file": request.FILES["cv_file"], "source": StudentCV.Source.UPLOADED})
        if cv_obj.pk:
            cv_obj.file = request.FILES["cv_file"]
            cv_obj.source = StudentCV.Source.UPLOADED
            cv_obj.save()
        messages.success(request, "CV uploaded successfully.")
    return redirect("assessment:cv_home")


@_student_required
def cv_generate(request):
    student_profile = get_object_or_404(StudentProfile, user=request.user)
    assessment_attempt = _latest_attempt(request.user)
    if not assessment_attempt or assessment_attempt.status != AssessmentAttempt.Status.COMPLETED:
        messages.error(request, "Complete an assessment before generating an AI CV.")
        return redirect("assessment:cv_home")

    cv_content = generate_cv_content(student_profile, assessment_attempt)
    output_dir = Path(settings.MEDIA_ROOT) / "cvs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"ai_cv_{request.user.id}.pdf"
    generate_cv_pdf(cv_content, output_path)

    cv_obj, _ = StudentCV.objects.get_or_create(user=request.user, defaults={"file": f"cvs/{output_path.name}", "source": StudentCV.Source.AI_GENERATED})
    with open(output_path, "rb") as fh:
        cv_obj.file.save(output_path.name, File(fh), save=False)
    cv_obj.source = StudentCV.Source.AI_GENERATED
    cv_obj.save()
    messages.success(request, "AI CV generated successfully.")
    return redirect("assessment:cv_home")


@_student_required
def cv_download(request):
    student_cv = StudentCV.objects.filter(user=request.user).first()
    if not student_cv or not student_cv.file:
        raise Http404("No CV found.")
    return FileResponse(student_cv.file.open("rb"), as_attachment=True, filename=Path(student_cv.file.name).name)