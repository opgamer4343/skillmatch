"""
Student dashboard views — ALL data from real database.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from functools import wraps
import json

from accounts.models import StudentProfile, User
from assessment.models import AssessmentAttempt, StudentCV
from company.models import Application, Interview, Internship


# ── Auth guard ────────────────────────────────────────────────────────────────

def student_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if getattr(request.user, "role", None) != "student":
            messages.error(request, "Access restricted to students.")
            return redirect("accounts:login")
        return view_func(request, *args, **kwargs)
    return _wrapped


# ── Helpers ───────────────────────────────────────────────────────────────────

def _latest_attempt(user):
    return (
        AssessmentAttempt.objects
        .filter(student=user, status="completed")
        .order_by("-completed_at")
        .first()
    )


def _match_percent(student_score, threshold):
    if not threshold:
        return 100
    if student_score is None:
        return 0
    buf = 2
    effective = max(0, float(threshold) - buf)
    if float(student_score) >= effective:
        return 100
    ratio = float(student_score) / float(threshold)
    return min(99, max(0, int(ratio * 100)))


# ── Views ─────────────────────────────────────────────────────────────────────

@student_required
def overview(request):
    user = request.user
    profile = StudentProfile.objects.filter(user=user).first()
    latest = _latest_attempt(user)

    total_apps = Application.objects.filter(applicant=user).count()
    upcoming_interviews = Interview.objects.filter(
        application__applicant=user,
        interview_date__gte=timezone.now(),
        status__in=["scheduled", "accepted"],
    ).count()

    recent_apps = (
        Application.objects
        .filter(applicant=user)
        .select_related("internship__company__company_profile")
        .order_by("-created_at")[:5]
    )

    upcoming_ivs = (
        Interview.objects
        .filter(
            application__applicant=user,
            interview_date__gte=timezone.now(),
            status__in=["scheduled", "accepted"],
        )
        .select_related("application__internship__company__company_profile")
        .order_by("interview_date")[:3]
    )

    return render(request, "dashboard/overview.html", {
        "profile": profile,
        "latest_attempt": latest,
        "total_apps": total_apps,
        "upcoming_interviews": upcoming_interviews,
        "recent_apps": recent_apps,
        "upcoming_ivs": upcoming_ivs,
    })


@student_required
def internships(request):
    user = request.user
    latest = _latest_attempt(user)
    student_score = float(latest.overall_score) if latest else None

    qs = Internship.objects.filter(status="active").select_related(
        "company__company_profile"
    ).order_by("-created_at")

    # Filters
    work_type = request.GET.get("work_type", "")
    skill = request.GET.get("skill", "").strip()
    duration = request.GET.get("duration", "").strip()
    q = request.GET.get("q", "").strip()

    if work_type:
        qs = qs.filter(work_type=work_type)
    if duration:
        qs = qs.filter(duration__icontains=duration)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    # Skill filter (JSONField contains)
    if skill:
        # Filter Python-side (JSONField array contains)
        qs_list = [i for i in qs if any(skill.lower() in s.lower() for s in (i.required_skills or []))]
    else:
        qs_list = list(qs)

    # Already applied IDs
    applied_ids = set(
        Application.objects.filter(applicant=user).values_list("internship_id", flat=True)
    )

    enriched = []
    for intern in qs_list:
        match = _match_percent(student_score, intern.required_score_threshold)
        enriched.append({
            "internship": intern,
            "match": match,
            "applied": intern.pk in applied_ids,
            "company_name": intern.company.company_profile.company_name if hasattr(intern.company, "company_profile") else intern.company.email,
        })

    # Sort by match descending
    enriched.sort(key=lambda x: x["match"], reverse=True)

    return render(request, "dashboard/internships.html", {
        "internships": enriched,
        "work_type": work_type,
        "skill": skill,
        "duration": duration,
        "q": q,
        "work_type_choices": Internship.WorkType.choices,
        "student_score": student_score,
    })


@student_required
@require_POST
def apply_internship(request, pk):
    internship = get_object_or_404(Internship, pk=pk, status="active")

    if Application.objects.filter(internship=internship, applicant=request.user).exists():
        messages.warning(request, "You have already applied for this internship.")
        return redirect("dashboard:internships")

    cover_letter = request.POST.get("cover_letter", "")
    Application.objects.create(
        internship=internship,
        applicant=request.user,
        cover_letter=cover_letter,
        status=Application.Status.APPLIED,
    )
    messages.success(request, f"✓ Applied for '{internship.title}'! Good luck.")
    return redirect("dashboard:applications")


@student_required
def applications(request):
    user = request.user
    qs = (
        Application.objects
        .filter(applicant=user)
        .select_related("internship__company__company_profile")
        .order_by("-created_at")
    )

    status_filter = request.GET.get("status", "")
    if status_filter:
        qs = qs.filter(status=status_filter)

    return render(request, "dashboard/applications.html", {
        "applications": qs,
        "status_filter": status_filter,
        "status_choices": Application.Status.choices,
    })


@student_required
def interviews(request):
    user = request.user
    now = timezone.now()
    all_ivs = (
        Interview.objects
        .filter(application__applicant=user)
        .select_related("application__internship__company__company_profile")
        .order_by("interview_date")
    )
    upcoming = [i for i in all_ivs if i.interview_date >= now and i.status not in ("cancelled", "completed")]
    past = [i for i in all_ivs if i.interview_date < now or i.status in ("cancelled", "completed")]

    return render(request, "dashboard/interviews.html", {
        "upcoming_interviews": upcoming,
        "past_interviews": past,
    })


@student_required
@require_POST
def accept_interview(request, pk):
    interview = get_object_or_404(Interview, pk=pk, application__applicant=request.user)
    if interview.status == "scheduled":
        interview.status = Interview.Status.ACCEPTED
        interview.save(update_fields=["status"])
        messages.success(request, "Interview accepted.")
    return redirect("dashboard:interviews")


@student_required
@require_POST
def reschedule_interview(request, pk):
    interview = get_object_or_404(Interview, pk=pk, application__applicant=request.user)
    if interview.status not in ("cancelled", "completed"):
        interview.status = Interview.Status.RESCHEDULE_REQUESTED
        interview.save(update_fields=["status"])
        messages.info(request, "Reschedule request sent.")
    return redirect("dashboard:interviews")


@student_required
def profile_view(request):
    user = request.user
    profile = StudentProfile.objects.filter(user=user).first()
    latest = _latest_attempt(user)
    cv = getattr(user, "student_cv", None)

    if request.method == "POST":
        # Name
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.save(update_fields=["first_name", "last_name"])

        if profile:
            profile.university = request.POST.get("university", profile.university)
            profile.degree = request.POST.get("degree", profile.degree)
            profile.major = request.POST.get("major", profile.major)
            profile.city = request.POST.get("city", profile.city)
            profile.linkedin_url = request.POST.get("linkedin_url", profile.linkedin_url)
            profile.bio = request.POST.get("bio", profile.bio)
            try:
                profile.graduation_year = int(request.POST.get("graduation_year", profile.graduation_year))
            except (ValueError, TypeError):
                pass

            skills_raw = request.POST.get("skills_json", "[]")
            try:
                profile.skills = json.loads(skills_raw)
            except Exception:
                pass

            resume = request.FILES.get("resume")
            if resume:
                if resume.size > 5 * 1024 * 1024:
                    messages.error(request, "Resume must be under 5MB.")
                else:
                    profile.resume = resume

            profile.save()
            messages.success(request, "Profile updated.")
        return redirect("dashboard:profile")

    return render(request, "dashboard/profile.html", {
        "profile": profile,
        "latest_attempt": latest,
        "cv": cv,
        "skills_json": json.dumps(profile.skills if profile else []),
    })


@student_required
def download_resume(request):
    profile = getattr(request.user, "student_profile", None)
    if not profile or not profile.resume:
        messages.error(request, "No resume uploaded.")
        return redirect("dashboard:profile")
    return FileResponse(
        profile.resume.open("rb"), as_attachment=True,
        filename=f"Resume_{request.user.get_full_name().replace(' ', '_')}.pdf"
    )


@student_required
def download_cv(request):
    cv = getattr(request.user, "student_cv", None)
    if not cv or not cv.file:
        messages.error(request, "No CV available. Generate one first.")
        return redirect("dashboard:profile")
    return FileResponse(
        cv.file.open("rb"), as_attachment=True,
        filename=f"CV_{request.user.get_full_name().replace(' ', '_')}.pdf"
    )


# ── Company Reviews ───────────────────────────────────────────────────────────

@student_required
def write_review(request, company_id):
    """
    Student writes a verified review for a company.
    - Must have applied to this company
    - All fields mandatory (title, body, interview_experience)
    - Anti-spam scoring runs before save
    - Score >= 60 → held for admin approval
    - Score >= 85 → marked likely spam, also held
    """
    from company.models import CompanyReview
    from company.spam_detector import analyse_review, spam_verdict

    company_user    = get_object_or_404(User, pk=company_id, role="company")
    company_profile = getattr(company_user, "company_profile", None)

    # Must have applied to this company
    applications = Application.objects.filter(
        applicant=request.user,
        internship__company=company_user,
    )
    if not applications.exists():
        messages.error(request, "You can only review companies you have applied to.")
        return redirect("dashboard:applications")

    # Already reviewed?
    existing = CompanyReview.objects.filter(
        company=company_user, reviewer=request.user
    ).first()
    if existing:
        messages.info(request, "You have already submitted a review for this company.")
        return redirect("dashboard:company_reviews", company_id=company_id)

    errors = {}

    if request.method == "POST":
        # Collect all fields
        overall       = request.POST.get("overall_rating", "").strip()
        process       = request.POST.get("process_rating", "").strip()
        communication = request.POST.get("communication_rating", "").strip()
        title         = request.POST.get("title", "").strip()
        body          = request.POST.get("body", "").strip()
        experience    = request.POST.get("interview_experience", "").strip()
        recommend     = request.POST.get("would_recommend") == "yes"
        is_anonymous  = request.POST.get("is_anonymous") == "on"

        # ── Mandatory field validation ────────────────────────────
        if not overall or not overall.isdigit() or not (1 <= int(overall) <= 5):
            errors["overall_rating"] = "Please select an overall rating."
        if not process or not process.isdigit() or not (1 <= int(process) <= 5):
            errors["process_rating"] = "Please rate the hiring process."
        if not communication or not communication.isdigit()                 or not (1 <= int(communication) <= 5):
            errors["communication_rating"] = "Please rate the communication."
        if not title:
            errors["title"] = "Review title is required."
        elif len(title) < 10:
            errors["title"] = "Title must be at least 10 characters."
        if not body:
            errors["body"] = "Review body is required."
        elif len(body.split()) < 30:
            errors["body"] = (
                f"Please write at least 30 words. "
                f"You wrote {len(body.split())} words."
            )
        if not experience:
            errors["interview_experience"] = "Interview experience is required."
        elif len(experience.split()) < 15:
            errors["interview_experience"] = (
                f"Please describe your interview experience in at least 15 words. "
                f"You wrote {len(experience.split())} words."
            )

        if not errors:
            overall_i  = int(overall)
            process_i  = int(process)
            comm_i     = int(communication)

            # ── Run spam detection (safe — falls back if module missing) ──
            try:
                app_count = applications.count()
                spam_score, spam_flags = analyse_review(
                    title=title,
                    body=body,
                    interview_experience=experience,
                    overall_rating=overall_i,
                    process_rating=process_i,
                    communication_rating=comm_i,
                    reviewer_app_count=app_count,
                )
                verdict    = spam_verdict(spam_score)
                is_approved= verdict["approve"]
            except Exception:
                spam_score  = 0
                spam_flags  = []
                is_approved = True

            # Get client IP
            ip = (
                request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or request.META.get("REMOTE_ADDR", "")
            )

            # Link to most recent application
            application = applications.order_by("-created_at").first()

            # Build review data — only include fields that exist in DB
            existing_fields = [
                f.name for f in CompanyReview._meta.get_fields()
                if hasattr(f, 'name')
            ]
            review_data = dict(
                company=company_user,
                reviewer=request.user,
                application=application,
                overall_rating=overall_i,
                process_rating=process_i,
                communication_rating=comm_i,
                title=title,
                body=body,
                is_anonymous=is_anonymous,
                is_approved=is_approved,
            )
            if 'interview_experience' in existing_fields:
                review_data['interview_experience'] = experience
            if 'would_recommend' in existing_fields:
                review_data['would_recommend'] = recommend
            if 'spam_score' in existing_fields:
                review_data['spam_score'] = spam_score
            if 'spam_flags' in existing_fields:
                review_data['spam_flags'] = spam_flags
            if 'ip_address' in existing_fields:
                review_data['ip_address'] = ip or None

            CompanyReview.objects.create(**review_data)

            if is_approved:
                messages.success(
                    request,
                    "✓ Review submitted and published! Thank you for your feedback."
                )
            else:
                messages.info(
                    request,
                    "✓ Review submitted! It is under review by our team "
                    "and will be published shortly."
                )
            return redirect("dashboard:company_reviews", company_id=company_id)

    return render(request, "dashboard/write_review.html", {
        "company_user":    company_user,
        "company_profile": company_profile,
        "errors":          errors,
        "post":            request.POST if request.method == "POST" else {},
    })


@student_required
def company_reviews(request, company_id):
    """View all reviews for a company."""
    from company.models import CompanyReview
    from accounts.models import User

    company_user    = get_object_or_404(User, pk=company_id, role="company")
    company_profile = getattr(company_user, "company_profile", None)
    reviews         = CompanyReview.objects.filter(
        company=company_user, is_approved=True
    ).order_by("-created_at")

    # Aggregated stats
    total = reviews.count()
    if total > 0:
        avg_overall       = sum(r.overall_rating       for r in reviews) / total
        avg_process       = sum(r.process_rating       for r in reviews) / total
        avg_communication = sum(r.communication_rating for r in reviews) / total
    else:
        avg_overall = avg_process = avg_communication = 0

    # Check if current user already reviewed
    user_reviewed = CompanyReview.objects.filter(
        company=company_user, reviewer=request.user
    ).exists()

    has_applied = Application.objects.filter(
        applicant=request.user,
        internship__company=company_user,
    ).exists()

    # Rating distribution and recommend %
    dist = {i: sum(1 for r in reviews if r.overall_rating == i) for i in range(1, 6)}
    recommend_pct = (
        int(sum(1 for r in reviews if getattr(r, "would_recommend", True)) / total * 100)
        if total > 0 else 0
    )

    return render(request, "dashboard/company_reviews.html", {
        "company_user":       company_user,
        "company_profile":    company_profile,
        "reviews":            reviews,
        "dist":               dist,
        "recommend_pct":      recommend_pct,
        "total":              total,
        "avg_overall":        round(avg_overall, 1),
        "avg_process":        round(avg_process, 1),
        "avg_communication":  round(avg_communication, 1),
        "user_reviewed":      user_reviewed,
        "has_applied":        has_applied,
    })


# ── Interview Prep Room ───────────────────────────────────────────────────────

@student_required
def interview_prep(request, interview_id):
    """Student opens their AI-generated interview prep room."""
    from company.models import InterviewPrepSession
    from company.ai_prep import generate_interview_prep

    interview = get_object_or_404(
        Interview,
        pk=interview_id,
        application__applicant=request.user,
    )

    # Check if prep already generated (reuse to save API calls)
    prep = getattr(interview, "prep_session", None)

    if request.method == "POST" and request.POST.get("regenerate"):
        # Allow student to regenerate
        if prep:
            prep.delete()
        prep = None

    if not prep:
        # Generate AI prep
        data = generate_interview_prep(interview)
        # Use get_or_create to avoid duplicate key error if session already exists
        prep, created = InterviewPrepSession.objects.get_or_create(
            interview=interview,
            defaults={
                "student": request.user,
                "questions": data.get("questions", []),
                "tips": data.get("tips", []),
                "company_summary": data.get("company_summary", ""),
            }
        )
        # Store checklist in questions field as extra key (simple approach)
        prep._checklist = data.get("checklist", [])
    else:
        prep._checklist = []

    # Group questions by category
    questions  = prep.questions or []
    technical  = [q for q in questions if q.get("category") == "Technical"]
    behavioural= [q for q in questions if q.get("category") == "Behavioural"]
    situational= [q for q in questions if q.get("category") == "Situational"]

    company_profile = getattr(
        interview.application.internship.company, "company_profile", None
    )

    return render(request, "dashboard/interview_prep.html", {
        "interview":        interview,
        "prep":             prep,
        "technical":        technical,
        "behavioural":      behavioural,
        "situational":      situational,
        "company_profile":  company_profile,
        "checklist":        prep._checklist,
    })