"""
Company views — ALL data from real database, zero mock data.
"""
from __future__ import annotations

import os
if os.getenv("DEBUG", "True").lower() == "true":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import CompanyProfile, User
from assessment.models import AssessmentAttempt
from .forms import (
    CompanyProfileForm,
    InternshipForm,
    ScheduleInterviewForm,
)
from .models import Application, Interview, Internship
from .google_calendar import create_google_meet_event, delete_google_event, update_google_meet_event
from .google_oauth import build_google_flow
from .permissions import company_required


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_company_profile(user):
    return CompanyProfile.objects.filter(user=user).first()


def _match_percent(student_score, threshold):
    if not threshold:
        return 100
    if student_score is None:
        return 0
    buf = 2
    effective = max(0, threshold - buf)
    if float(student_score) >= effective:
        return 100
    ratio = float(student_score) / float(threshold)
    return min(99, max(0, int(ratio * 100)))


def _student_latest_score(student_user):
    attempt = (
        AssessmentAttempt.objects
        .filter(student=student_user, status="completed")
        .order_by("-completed_at")
        .first()
    )
    return attempt.overall_score if attempt else None


def _student_score_band(student_user):
    attempt = (
        AssessmentAttempt.objects
        .filter(student=student_user, status="completed")
        .order_by("-completed_at")
        .first()
    )
    return attempt.score_band if attempt else None




def _company_has_google(user):
    profile = getattr(user, "company_profile", None)
    return bool(profile and profile.has_google_connected)


def _safe_create_or_update_google_meet(interview, create=False):
    if interview.interview_type != Interview.InterviewType.VIDEO:
        return
    if not _company_has_google(interview.scheduled_by):
        return
    try:
        if create or not interview.google_event_id:
            event_id, meet_link = create_google_meet_event(interview)
        else:
            event_id, meet_link = update_google_meet_event(interview)
        interview.google_event_id = event_id or interview.google_event_id
        if meet_link:
            interview.google_meet_link = meet_link
            interview.meeting_link = meet_link
        interview.google_calendar_sync_status = "synced"
        interview.save(update_fields=["google_event_id", "google_meet_link", "meeting_link", "google_calendar_sync_status"])
    except Exception:
        interview.google_calendar_sync_status = "failed"
        interview.save(update_fields=["google_calendar_sync_status"])

# ── Overview ──────────────────────────────────────────────────────────────────

@company_required
def overview(request):
    profile = _get_company_profile(request.user)

    active_listings     = Internship.objects.filter(company=request.user, status="active").count()
    total_applicants    = Application.objects.filter(internship__company=request.user).count()
    upcoming_interviews = Interview.objects.filter(
        application__internship__company=request.user,
        interview_date__gte=timezone.now(),
        status__in=["scheduled", "accepted"],
    ).count()
    offers_count = Application.objects.filter(
        internship__company=request.user, status="offer"
    ).count()

    recent_internships = (
        Internship.objects
        .filter(company=request.user)
        .annotate(app_count=Count("applications"))
        .order_by("-created_at")[:5]
    )

    recent_applications = (
        Application.objects
        .filter(internship__company=request.user)
        .select_related("applicant", "internship")
        .order_by("-created_at")[:5]
    )

    upcoming_ivs = (
        Interview.objects
        .filter(
            application__internship__company=request.user,
            interview_date__gte=timezone.now(),
            status__in=["scheduled", "accepted"],
        )
        .select_related("application__applicant", "application__internship")
        .order_by("interview_date")[:5]
    )

    return render(request, "company/overview.html", {
        "profile": profile,
        "stats": {
            "active_listings":  active_listings,
            "total_applicants": total_applicants,
            "interviews":       upcoming_interviews,
            "offers":           offers_count,
        },
        "recent_internships":  recent_internships,
        "recent_applications": recent_applications,
        "upcoming_interviews": upcoming_ivs,
    })


# ── Internships ───────────────────────────────────────────────────────────────

@company_required
def internships(request):
    qs = (
        Internship.objects
        .filter(company=request.user)
        .annotate(app_count=Count("applications"))
        .order_by("-created_at")
    )

    status_filter    = request.GET.get("status", "")
    work_type_filter = request.GET.get("work_type", "")
    q                = request.GET.get("q", "").strip()

    if status_filter:    qs = qs.filter(status=status_filter)
    if work_type_filter: qs = qs.filter(work_type=work_type_filter)
    if q:                qs = qs.filter(Q(title__icontains=q) | Q(department__icontains=q))

    return render(request, "company/internships.html", {
        "internships":       qs,
        "status_filter":     status_filter,
        "work_type_filter":  work_type_filter,
        "q":                 q,
        "status_choices":    Internship.Status.choices,
        "work_type_choices": Internship.WorkType.choices,
    })


@company_required
def post_internship(request):
    form = InternshipForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        internship         = form.save(commit=False)
        internship.company = request.user
        internship.save()
        messages.success(request, f"✓ '{internship.title}' posted successfully.")
        return redirect("company:internships")
    return render(request, "company/internship_form.html", {
        "form":       form,
        "page_title": "Post New Internship",
        "edit_mode":  False,
    })


@company_required
def edit_internship(request, pk):
    internship = get_object_or_404(Internship, pk=pk, company=request.user)
    form       = InternshipForm(request.POST or None, instance=internship)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"✓ '{internship.title}' updated.")
        return redirect("company:internships")
    return render(request, "company/internship_form.html", {
        "form":        form,
        "page_title":  f"Edit: {internship.title}",
        "edit_mode":   True,
        "internship":  internship,
    })


@company_required
@require_POST
def delete_internship(request, pk):
    internship = get_object_or_404(Internship, pk=pk, company=request.user)
    title      = internship.title
    internship.delete()
    messages.success(request, f"'{title}' deleted.")
    return redirect("company:internships")


# ── Applicants ────────────────────────────────────────────────────────────────

@company_required
def applicants(request):
    internship_filter = request.GET.get("internship", "")
    status_filter     = request.GET.get("status", "")

    apps_qs = (
        Application.objects
        .filter(internship__company=request.user)
        .select_related("applicant__student_profile", "internship")
        .order_by("-created_at")
    )

    if internship_filter: apps_qs = apps_qs.filter(internship_id=internship_filter)
    if status_filter:     apps_qs = apps_qs.filter(status=status_filter)

    enriched = []
    for app in apps_qs:
        score     = _student_latest_score(app.applicant)
        band      = _student_score_band(app.applicant)
        threshold = app.internship.required_score_threshold or 0
        match     = _match_percent(score, threshold)
        enriched.append({
            "app":    app,
            "score":  score,
            "band":   band,
            "match":  match,
            "has_cv": bool(getattr(app.applicant, "student_cv", None)),
        })

    enriched.sort(key=lambda x: float(x["score"] or 0), reverse=True)

    my_internships = Internship.objects.filter(company=request.user).values("id", "title")

    return render(request, "company/applicants.html", {
        "applicants":         enriched,
        "my_internships":     my_internships,
        "internship_filter":  internship_filter,
        "status_filter":      status_filter,
        "status_choices":     Application.Status.choices,
    })


@company_required
@require_POST
def update_application_status(request, pk):
    app        = get_object_or_404(Application, pk=pk, internship__company=request.user)
    new_status = request.POST.get("status")
    valid      = [c[0] for c in Application.Status.choices]
    if new_status not in valid:
        return JsonResponse({"ok": False, "error": "Invalid status"}, status=400)
    app.status = new_status
    app.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": new_status, "label": app.get_status_display()})


@company_required
def download_cv(request, applicant_id):
    student    = get_object_or_404(User, pk=applicant_id, role="student")
    has_applied = Application.objects.filter(
        applicant=student, internship__company=request.user
    ).exists()
    if not has_applied:
        raise Http404("Applicant not found.")

    cv = getattr(student, "student_cv", None)
    if cv and cv.file:
        return FileResponse(
            cv.file.open("rb"), as_attachment=True,
            filename=f"CV_{student.get_full_name().replace(' ', '_')}.pdf"
        )

    profile = getattr(student, "student_profile", None)
    if profile and profile.resume:
        return FileResponse(
            profile.resume.open("rb"), as_attachment=True,
            filename=f"Resume_{student.get_full_name().replace(' ', '_')}.pdf"
        )

    messages.error(request, "This applicant has not uploaded a CV or resume.")
    return redirect("company:applicants")


# ── Interviews ────────────────────────────────────────────────────────────────

@company_required
def interviews(request):
    now = timezone.now()
    all_ivs = (
        Interview.objects
        .filter(application__internship__company=request.user)
        .select_related("application__applicant", "application__internship")
        .order_by("interview_date")
    )
    upcoming = [
        i for i in all_ivs
        if i.interview_date >= now and i.status not in ("cancelled", "completed")
    ]
    past = [
        i for i in all_ivs
        if i.interview_date < now or i.status in ("cancelled", "completed")
    ]
    return render(request, "company/interviews.html", {
        "upcoming_interviews": upcoming,
        "past_interviews":     past,
    })


@company_required
def schedule_interview(request, application_id=None):
    selected_app = None
    if application_id:
        selected_app = get_object_or_404(
            Application,
            pk=application_id,
            internship__company=request.user,
        )

    if request.method == "POST":
        form = ScheduleInterviewForm(request.POST, company_user=request.user, selected_app=selected_app)
        if form.is_valid():
            interview              = form.save(commit=False)
            interview.scheduled_by = request.user

            if selected_app:
                interview.application = selected_app

            auto_google = form.cleaned_data.get("auto_create_google_meet")
            if interview.interview_type == "onsite" and not interview.location:
                form.add_error("location", "Location is required for onsite interviews.")
                return render(request, "company/schedule_interview.html", {"form": form, "selected_app": selected_app})

            if interview.interview_type == "video" and auto_google and _company_has_google(request.user):
                interview.google_calendar_sync_status = "pending"
            elif interview.interview_type in ("video", "phone") and not interview.meeting_link:
                form.add_error("meeting_link", "A meeting link is required for video/phone interviews.")
                return render(request, "company/schedule_interview.html", {"form": form, "selected_app": selected_app})

            interview.save()
            if interview.interview_type == "video" and auto_google and _company_has_google(request.user):
                _safe_create_or_update_google_meet(interview, create=True)

            # Set application status → interview
            app_obj        = interview.application
            app_obj.status = Application.Status.INTERVIEW
            app_obj.save(update_fields=["status"])

            # Send confirmation email directly (works without Redis)
            try:
                from notifications.email_service import send_interview_scheduled_email
                send_interview_scheduled_email(
                    interview.application.applicant,
                    interview,
                    interview.application,
                )
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("Interview email failed: %s", exc)

            # Also queue smart reminders in Celery if Redis is available
            try:
                from notifications.tasks import send_interview_scheduled_email_task
                send_interview_scheduled_email_task.delay(interview.pk)
            except Exception:
                pass  # Redis not running — confirmation already sent above

            messages.success(
                request,
                f"✓ Interview scheduled for "
                f"{interview.application.applicant.get_full_name()}. "
                f"Email notification sent." + (" Google Meet created." if interview.google_meet_link else "")
            )
            return redirect("company:interviews")

    else:
        initial = {"application": selected_app.pk} if selected_app else {}
        form    = ScheduleInterviewForm(company_user=request.user, initial=initial, selected_app=selected_app)

    return render(request, "company/schedule_interview.html", {
        "form":         form,
        "selected_app": selected_app,
    })


@company_required
@require_POST
def cancel_interview(request, pk):
    interview = get_object_or_404(
        Interview, pk=pk,
        application__internship__company=request.user
    )
    if interview.status not in ("completed",):
        if interview.google_event_id:
            try:
                delete_google_event(interview)
            except Exception:
                pass
        interview.status = Interview.Status.CANCELLED
        interview.google_calendar_sync_status = "cancelled" if interview.google_event_id else interview.google_calendar_sync_status
        interview.save(update_fields=["status", "google_calendar_sync_status"])
        try:
            from notifications.tasks import send_interview_cancelled_email_task
            send_interview_cancelled_email_task.delay(interview.pk)
        except Exception:
            pass
        messages.success(request, "Interview cancelled. Candidate has been notified.")
    return redirect("company:interviews")




@company_required
def google_connect_start(request):
    if not getattr(request.user, "company_profile", None):
        messages.error(request, "Complete your company profile first.")
        return redirect("company:settings")
    try:
        flow = build_google_flow()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        # Store PKCE code_verifier in session for callback
        request.session["google_oauth_state"] = state
        request.session["google_code_verifier"] = flow.code_verifier
        request.session.modified = True
        return redirect(authorization_url)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Google connection failed: {exc}")
        return redirect("company:settings")


@company_required
def google_connect_callback(request):
    if os.getenv("DEBUG", "True").lower() == "true":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    company_profile = request.user.company_profile
    code = request.GET.get("code")

    if not code:
        messages.error(request, "Google callback failed: no code returned.")
        return redirect("company:settings")

    try:
        flow = build_google_flow()
        
        # Restore PKCE code_verifier from session
        code_verifier = request.session.get("google_code_verifier")
        if code_verifier:
            flow.code_verifier = code_verifier
        
        # fetch token using full authorization response URL
        authorization_response = request.build_absolute_uri()
        # force http for local dev
        if authorization_response.startswith("https://"):
            authorization_response = "http://" + authorization_response[8:]

        flow.fetch_token(authorization_response=authorization_response)

        creds = flow.credentials
        company_profile.google_email = request.user.email
        company_profile.google_access_token = creds.token
        company_profile.google_refresh_token = (
            creds.refresh_token or company_profile.google_refresh_token
        )
        company_profile.google_token_uri = creds.token_uri
        company_profile.google_scopes = " ".join(
            creds.scopes or getattr(settings, "GOOGLE_CALENDAR_SCOPES", [])
        )
        company_profile.google_account_connected_at = timezone.now()
        company_profile.save(update_fields=[
            "google_email", "google_access_token", "google_refresh_token",
            "google_token_uri", "google_scopes", "google_account_connected_at",
            "updated_at",
        ])
        messages.success(
            request,
            "Google Calendar connected. Video interviews can now auto-create Meet links."
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Google callback failed: {exc}")

    return redirect("company:settings")


@company_required
def google_disconnect(request):
    company_profile = request.user.company_profile
    company_profile.google_email = None
    company_profile.google_access_token = None
    company_profile.google_refresh_token = None
    company_profile.google_scopes = None
    company_profile.google_account_connected_at = None
    company_profile.save(update_fields=[
        "google_email", "google_access_token", "google_refresh_token",
        "google_scopes", "google_account_connected_at", "updated_at"
    ])
    messages.success(request, "Google Calendar disconnected.")
    return redirect("company:settings")

# ── Settings ──────────────────────────────────────────────────────────────────

@company_required
def settings_view(request):
    profile = _get_company_profile(request.user)
    form    = CompanyProfileForm(
        request.POST or None, request.FILES or None, instance=profile
    )
    if request.method == "POST" and form.is_valid():
        cp      = form.save(commit=False)
        cp.user = request.user
        cp.save()
        messages.success(request, "Company profile updated.")
        return redirect("company:settings")
    return render(request, "company/settings.html", {
        "form": form,
        "profile": profile,
        "google_connected": bool(profile and profile.has_google_connected),
        "google_connect_url": reverse("company:google_connect_start"),
        "google_disconnect_url": reverse("company:google_disconnect"),
    })


@company_required
def setup_profile(request):
    profile = _get_company_profile(request.user)
    form    = CompanyProfileForm(
        request.POST or None, request.FILES or None, instance=profile
    )
    if request.method == "POST":
        if "skip" in request.POST:
            return redirect("company:overview")
        if form.is_valid():
            cp      = form.save(commit=False)
            cp.user = request.user
            cp.save()
            messages.success(request, "Profile set up.")
            return redirect("company:overview")
    return render(request, "company/setup_profile.html", {"form": form})


# ── Company Reviews (company sees their reviews) ──────────────────────────────

@company_required
def all_reviews(request):
    """Company sees all approved reviews + pending count.
    Safe version — works whether migration 0003 has run or not."""
    from .models import CompanyReview

    # Check which fields exist in DB
    existing = [f.name for f in CompanyReview._meta.get_fields()
                if hasattr(f, 'name')]
    has_spam    = 'flagged_by_admin' in existing
    has_recommend = 'would_recommend' in existing

    all_rev = CompanyReview.objects.filter(company=request.user)
    reviews = all_rev.filter(
        is_approved=True
    ).select_related("reviewer").order_by("-created_at")

    # Pending count — safe query
    if has_spam:
        pending = all_rev.filter(is_approved=False, flagged_by_admin=False).count()
        flagged = all_rev.filter(flagged_by_admin=True).count()
    else:
        pending = all_rev.filter(is_approved=False).count()
        flagged = 0

    total = reviews.count()
    if total > 0:
        avg_overall       = sum(r.overall_rating       for r in reviews) / total
        avg_process       = sum(r.process_rating       for r in reviews) / total
        avg_communication = sum(r.communication_rating for r in reviews) / total
        dist = {i: sum(1 for r in reviews if r.overall_rating == i)
                for i in range(1, 6)}
        recommend_pct = int(
            sum(1 for r in reviews
                if getattr(r, "would_recommend", True)) / total * 100
        ) if has_recommend else None
    else:
        avg_overall = avg_process = avg_communication = 0
        dist = {i: 0 for i in range(1, 6)}
        recommend_pct = None

    return render(request, "company/reviews.html", {
        "reviews":           reviews,
        "total":             total,
        "pending":           pending,
        "flagged":           flagged,
        "avg_overall":       round(avg_overall, 1),
        "avg_process":       round(avg_process, 1),
        "avg_communication": round(avg_communication, 1),
        "dist":              dist,
        "recommend_pct":     recommend_pct,
    })


# ── Reschedule Interview (Company) ────────────────────────────────────────────

@company_required
def reschedule_interview(request, pk):
    """
    Company picks a new date/time (and optionally new meeting link/location).
    After saving:
      - Interview status → scheduled
      - Email sent to student with new details
    """
    from .forms import RescheduleInterviewForm

    interview = get_object_or_404(
        Interview, pk=pk,
        application__internship__company=request.user
    )

    if interview.status == "completed":
        messages.error(request, "Cannot reschedule a completed interview.")
        return redirect("company:interviews")

    if request.method == "POST":
        form = RescheduleInterviewForm(request.POST, instance=interview, company_user=request.user)
        if form.is_valid():
            iv = form.save(commit=False)
            iv.status = Interview.Status.SCHEDULED
            auto_google = form.cleaned_data.get("auto_create_google_meet")
            if iv.interview_type == Interview.InterviewType.VIDEO and auto_google and _company_has_google(request.user):
                iv.google_calendar_sync_status = "pending"
            iv.reminder_48h_sent = False
            iv.reminder_1h_sent = False
            iv.reminder_now_sent = False
            iv.save()
            if iv.interview_type == Interview.InterviewType.VIDEO and auto_google and _company_has_google(request.user):
                _safe_create_or_update_google_meet(iv, create=not bool(iv.google_event_id))

            # Notify student with new details
            try:
                from notifications.email_service import send_interview_scheduled_email
                send_interview_scheduled_email(
                    iv.application.applicant, iv, iv.application
                )
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "Reschedule email failed: %s", exc
                )

            messages.success(
                request,
                f"✓ Interview rescheduled for "
                f"{iv.application.applicant.get_full_name()}. "
                f"Student has been notified with the new details."
            )
            return redirect("company:interviews")
    else:
        form = RescheduleInterviewForm(instance=interview, company_user=request.user)

    return render(request, "company/reschedule_interview.html", {
        "form":      form,
        "interview": interview,
    })


# ── Company Profile View ──────────────────────────────────────────────────────

@company_required
def company_profile(request):
    """Company views their own full profile page."""
    from .models import CompanyReview
    profile        = _get_company_profile(request.user)
    active_listings= Internship.objects.filter(
        company=request.user, status="active"
    ).count()
    total_applicants = Application.objects.filter(
        internship__company=request.user
    ).count()
    internships    = Internship.objects.filter(
        company=request.user
    ).order_by("-created_at")[:5]

    # Average rating
    reviews = CompanyReview.objects.filter(
        company=request.user, is_approved=True
    )
    total_reviews = reviews.count()
    avg_rating = (
        round(sum(r.overall_rating for r in reviews) / total_reviews, 1)
        if total_reviews > 0 else "—"
    )

    return render(request, "company/profile.html", {
        "profile":          profile,
        "active_listings":  active_listings,
        "total_applicants": total_applicants,
        "internships":      internships,
        "avg_rating":       avg_rating,
        "total_reviews":    total_reviews,
    })