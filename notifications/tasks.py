# ─────────────────────────────────────────────────────────────────────
# FULL FILE: notifications/tasks.py
# Replace your entire tasks.py with this.
# ─────────────────────────────────────────────────────────────────────
"""
Smart notification timing:
  > 48h away  → sends 48h reminder, 1h reminder, and NOW notification
  < 48h away  → sends 1h reminder and NOW notification
  same day    → sends NOW notification only at exact start time

All via Celery apply_async(eta=...).
Celery Beat runs a 15-minute safety scanner as fallback.
"""
from __future__ import annotations
import logging
from datetime import timedelta

from celery import shared_task
from django.apps import apps
from django.utils import timezone

from .email_service import (
    send_application_received_email,
    send_interview_accepted_email,
    send_interview_cancelled_email,
    send_interview_reminder_company_email,
    send_interview_reminder_student_email,
    send_interview_reschedule_requested_email,
)

logger = logging.getLogger(__name__)


def _get_models():
    Interview   = apps.get_model('company', 'Interview')
    Application = apps.get_model('company', 'Application')
    return Interview, Application


def _load_interview(interview_id: int):
    Interview, _ = _get_models()
    return Interview.objects.select_related(
        'application__applicant',
        'application__internship__company',
        'scheduled_by',
    ).get(pk=interview_id)


# ── Confirmation email (sent by view directly, task here as fallback) ─

@shared_task(name="notifications.send_interview_scheduled_email_task")
def send_interview_scheduled_email_task(interview_id: int):
    """
    Schedules 48h / 1h / NOW follow-up reminders.
    The view already sends the confirmation email synchronously, so this task avoids duplicate confirmation emails.
    """
    iv      = _load_interview(interview_id)
    now          = timezone.now()
    interview_dt = iv.interview_date
    hours_away   = (interview_dt - now).total_seconds() / 3600

    # Schedule 48-hour reminder
    if hours_away > 48:
        eta_48h = interview_dt - timedelta(hours=48)
        send_interview_48h_reminder_task.apply_async(
            args=[interview_id],
            eta=eta_48h,
            task_id=f"48h-{interview_id}",
        )
        logger.info("Scheduled 48h reminder for #%s at %s",
                    interview_id, eta_48h)

    # Schedule 1-hour reminder
    if hours_away > 1:
        eta_1h = interview_dt - timedelta(hours=1)
        send_interview_1h_reminder_task.apply_async(
            args=[interview_id],
            eta=eta_1h,
            task_id=f"1h-{interview_id}",
        )
        logger.info("Scheduled 1h reminder for #%s at %s",
                    interview_id, eta_1h)

    # Schedule "Starting NOW" at exact interview time
    send_interview_starting_now_task.apply_async(
        args=[interview_id],
        eta=interview_dt,
        task_id=f"now-{interview_id}",
    )
    logger.info("Scheduled NOW notification for #%s at %s",
                interview_id, interview_dt)


# ── 48-hour reminder ──────────────────────────────────────────────────

@shared_task(name="notifications.send_interview_48h_reminder_task")
def send_interview_48h_reminder_task(interview_id: int):
    try:
        iv = _load_interview(interview_id)
    except Exception:
        return
    if iv.status in ('cancelled', 'completed') or iv.reminder_48h_sent:
        return
    iv._reminder_type  = '48h'
    iv._subject_prefix = '48-Hour Reminder'
    send_interview_reminder_student_email(
        iv.application.applicant, iv, iv.application)
    send_interview_reminder_company_email(
        iv.application.internship.company, iv, iv.application)
    iv.reminder_48h_sent = True
    iv.save(update_fields=['reminder_48h_sent'])
    logger.info("Sent 48h reminder for #%s", interview_id)


# ── 1-hour reminder ───────────────────────────────────────────────────

@shared_task(name="notifications.send_interview_1h_reminder_task")
def send_interview_1h_reminder_task(interview_id: int):
    try:
        iv = _load_interview(interview_id)
    except Exception:
        return
    if iv.status in ('cancelled', 'completed') or iv.reminder_1h_sent:
        return
    iv._reminder_type  = '1h'
    iv._subject_prefix = '1-Hour Reminder'
    send_interview_reminder_student_email(
        iv.application.applicant, iv, iv.application)
    send_interview_reminder_company_email(
        iv.application.internship.company, iv, iv.application)
    iv.reminder_1h_sent = True
    iv.save(update_fields=['reminder_1h_sent'])
    logger.info("Sent 1h reminder for #%s", interview_id)


# ── Starting NOW notification ─────────────────────────────────────────

@shared_task(name="notifications.send_interview_starting_now_task")
def send_interview_starting_now_task(interview_id: int):
    try:
        iv = _load_interview(interview_id)
    except Exception:
        return
    if iv.status in ('cancelled', 'completed') or iv.reminder_now_sent:
        return
    iv._reminder_type  = 'now'
    iv._subject_prefix = '🔴 Starting Now'
    send_interview_reminder_student_email(
        iv.application.applicant, iv, iv.application)
    send_interview_reminder_company_email(
        iv.application.internship.company, iv, iv.application)
    iv.reminder_now_sent = True
    iv.save(update_fields=['reminder_now_sent'])
    logger.info("Sent NOW notification for #%s", interview_id)


# ── Other status-change tasks ─────────────────────────────────────────

@shared_task(name="notifications.send_interview_accepted_email_task")
def send_interview_accepted_email_task(interview_id: int):
    iv = _load_interview(interview_id)
    send_interview_accepted_email(
        iv.application.internship.company, iv, iv.application)


@shared_task(name="notifications.send_interview_reschedule_requested_email_task")
def send_interview_reschedule_requested_email_task(interview_id: int):
    iv = _load_interview(interview_id)
    send_interview_reschedule_requested_email(
        iv.application.internship.company, iv, iv.application)


@shared_task(name="notifications.send_interview_cancelled_email_task")
def send_interview_cancelled_email_task(interview_id: int):
    iv = _load_interview(interview_id)
    send_interview_cancelled_email(
        iv.application.applicant, iv, iv.application)


@shared_task(name="notifications.send_application_received_email_task")
def send_application_received_email_task(application_id: int):
    _, Application = _get_models()
    app = Application.objects.select_related(
        'applicant', 'internship__company'
    ).get(pk=application_id)
    send_application_received_email(app.internship.company, app)


# ── Celery Beat 15-minute safety scanner ─────────────────────────────

@shared_task(name="notifications.scan_and_send_interview_reminders")
def scan_and_send_interview_reminders():
    """
    Runs every 15 minutes via Celery Beat as a safety net.
    Catches any reminders that missed their eta (e.g. Redis was down).
    """
    Interview, _ = _get_models()
    now   = timezone.now()
    sent  = 0
    statuses = ['scheduled', 'accepted']

    # 48h window
    for iv in Interview.objects.filter(
        interview_date__gte=now + timedelta(hours=47, minutes=45),
        interview_date__lte=now + timedelta(hours=48, minutes=15),
        status__in=statuses,
        reminder_48h_sent=False,
    ).select_related('application__applicant',
                     'application__internship__company'):
        iv._reminder_type = '48h'
        send_interview_reminder_student_email(
            iv.application.applicant, iv, iv.application)
        send_interview_reminder_company_email(
            iv.application.internship.company, iv, iv.application)
        iv.reminder_48h_sent = True
        iv.save(update_fields=['reminder_48h_sent'])
        sent += 2

    # 1h window
    for iv in Interview.objects.filter(
        interview_date__gte=now + timedelta(minutes=45),
        interview_date__lte=now + timedelta(hours=1, minutes=15),
        status__in=statuses,
        reminder_1h_sent=False,
    ).select_related('application__applicant',
                     'application__internship__company'):
        iv._reminder_type = '1h'
        send_interview_reminder_student_email(
            iv.application.applicant, iv, iv.application)
        send_interview_reminder_company_email(
            iv.application.internship.company, iv, iv.application)
        iv.reminder_1h_sent = True
        iv.save(update_fields=['reminder_1h_sent'])
        sent += 2

    # NOW window (±2 min)
    for iv in Interview.objects.filter(
        interview_date__gte=now - timedelta(minutes=2),
        interview_date__lte=now + timedelta(minutes=13),
        status__in=statuses,
        reminder_now_sent=False,
    ).select_related('application__applicant',
                     'application__internship__company'):
        iv._reminder_type = 'now'
        send_interview_reminder_student_email(
            iv.application.applicant, iv, iv.application)
        send_interview_reminder_company_email(
            iv.application.internship.company, iv, iv.application)
        iv.reminder_now_sent = True
        iv.save(update_fields=['reminder_now_sent'])
        sent += 2

    logger.info("Reminder scanner sent %d notifications", sent)
    return {"sent": sent}


# Legacy alias
@shared_task(name="notifications.send_upcoming_interview_reminders")
def send_upcoming_interview_reminders():
    return scan_and_send_interview_reminders()