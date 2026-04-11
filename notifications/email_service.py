"""
SkillMatch Email Service
All transactional emails with smart reminder type support.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Notification

DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@skillmatch.local')
SITE_URL           = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')


@dataclass
class EmailResult:
    sent: bool
    notification: Optional[Notification] = None


def _safe_user_display(user: Any) -> str:
    full = ''
    if hasattr(user, 'get_full_name'):
        full = user.get_full_name().strip()
    return full or getattr(user, 'username', '') or getattr(user, 'email', 'User')


def _send_notification_email(
    *,
    recipient,
    notif_type: str,
    title: str,
    body: str,
    template_name: str,
    context: Optional[Dict[str, Any]] = None,
    interview_id: Optional[int] = None,
) -> EmailResult:

    context = context or {}
    context.setdefault('site_url',       SITE_URL)
    context.setdefault('recipient_name', _safe_user_display(recipient))
    context.setdefault('title',          title)
    if 'interview' in context and getattr(context['interview'], 'effective_meeting_link', None):
        context['interview'].meeting_link = context['interview'].effective_meeting_link

    try:
        html_body = render_to_string(template_name, context)
    except Exception:
        html_body = f"<p>{body}</p>"
    text_body = strip_tags(html_body)

    notification = Notification.objects.create(
        recipient=recipient,
        notif_type=notif_type,
        title=title,
        body=body,
        interview_id=interview_id,
    )

    try:
        msg = EmailMultiAlternatives(
            subject=title,
            body=text_body,
            from_email=DEFAULT_FROM_EMAIL,
            to=[recipient.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        notification.email_sent = True
        notification.save(update_fields=['email_sent'])
        return EmailResult(sent=True, notification=notification)
    except Exception:
        return EmailResult(sent=False, notification=notification)


# ── OTP ───────────────────────────────────────────────────────────────────────

def send_otp_verification_email(user, otp_code: str) -> EmailResult:
    return _send_notification_email(
        recipient=user,
        notif_type=Notification.TYPE_OTP,
        title='Verify your SkillMatch email',
        body=f'Your verification code is {otp_code}.',
        template_name='notifications/email/otp_verification.html',
        context={'otp_code': otp_code, 'user': user},
    )


# ── Interview scheduled (initial confirmation) ────────────────────────────────

def send_interview_scheduled_email(student, interview, application=None) -> EmailResult:
    app       = application or getattr(interview, 'application', None)
    internship = getattr(app, 'internship', None)
    accept_url     = f"{SITE_URL}/dashboard/interviews/{interview.pk}/accept/"
    reschedule_url = f"{SITE_URL}/dashboard/interviews/{interview.pk}/reschedule/"

    return _send_notification_email(
        recipient=student,
        notif_type=Notification.TYPE_INTERVIEW_SCHEDULED,
        title='Interview Scheduled — SkillMatch',
        body='A company has scheduled your interview.',
        template_name='notifications/email/interview_scheduled.html',
        interview_id=interview.pk,
        context={
            'user':           student,
            'interview':      interview,
            'application':    app,
            'internship':     internship,
            'accept_url':     accept_url,
            'reschedule_url': reschedule_url,
            'site_url':       SITE_URL,
        },
    )


# ── Reminder emails (48h / 1h / NOW) ─────────────────────────────────────────

def send_interview_reminder_student_email(student, interview, application=None) -> EmailResult:
    app        = application or getattr(interview, 'application', None)
    internship = getattr(app, 'internship', None)

    reminder_type  = getattr(interview, '_reminder_type',  '1h')
    subject_prefix = getattr(interview, '_subject_prefix', 'Reminder')

    TITLES = {
        '48h': f'⏰ 48-Hour Reminder: Your Interview Tomorrow',
        '1h':  f'⏰ 1-Hour Reminder: Your Interview is Coming Up',
        'now': f'🔴 Your Interview is Starting NOW — Join Now!',
    }
    title = TITLES.get(reminder_type, f'{subject_prefix}: Interview Reminder')

    accept_url     = f"{SITE_URL}/dashboard/interviews/{interview.pk}/accept/"
    reschedule_url = f"{SITE_URL}/dashboard/interviews/{interview.pk}/reschedule/"

    return _send_notification_email(
        recipient=student,
        notif_type=Notification.TYPE_INTERVIEW_REMINDER,
        title=title,
        body=title,
        template_name='notifications/email/interview_reminder_student.html',
        interview_id=interview.pk,
        context={
            'user':           student,
            'interview':      interview,
            'application':    app,
            'internship':     internship,
            'reminder_type':  reminder_type,
            'subject_prefix': subject_prefix,
            'is_now':         reminder_type == 'now',
            'is_48h':         reminder_type == '48h',
            'is_1h':          reminder_type == '1h',
            'accept_url':     accept_url,
            'reschedule_url': reschedule_url,
            'site_url':       SITE_URL,
        },
    )


def send_interview_reminder_company_email(company_user, interview, application=None) -> EmailResult:
    app        = application or getattr(interview, 'application', None)
    internship = getattr(app, 'internship', None)
    student    = getattr(app, 'applicant', None)

    reminder_type  = getattr(interview, '_reminder_type',  '1h')
    subject_prefix = getattr(interview, '_subject_prefix', 'Reminder')

    TITLES = {
        '48h': '⏰ 48-Hour Reminder: Upcoming Interview',
        '1h':  '⏰ 1-Hour Reminder: Interview Starting Soon',
        'now': '🔴 Interview Starting NOW',
    }
    title = TITLES.get(reminder_type, f'{subject_prefix}: Interview Reminder')

    return _send_notification_email(
        recipient=company_user,
        notif_type=Notification.TYPE_INTERVIEW_REMINDER,
        title=title,
        body=title,
        template_name='notifications/email/interview_reminder_company.html',
        interview_id=interview.pk,
        context={
            'user':           company_user,
            'interview':      interview,
            'application':    app,
            'internship':     internship,
            'student':        student,
            'reminder_type':  reminder_type,
            'subject_prefix': subject_prefix,
            'is_now':         reminder_type == 'now',
            'is_48h':         reminder_type == '48h',
            'is_1h':          reminder_type == '1h',
            'site_url':       SITE_URL,
        },
    )


# ── Other status emails ───────────────────────────────────────────────────────

def send_interview_accepted_email(company_user, interview, application=None) -> EmailResult:
    app        = application or getattr(interview, 'application', None)
    internship = getattr(app, 'internship', None)
    student    = getattr(app, 'applicant', None)
    return _send_notification_email(
        recipient=company_user,
        notif_type=Notification.TYPE_INTERVIEW_ACCEPTED,
        title='Interview Accepted by Student',
        body='A student has accepted the interview invitation.',
        template_name='notifications/email/interview_accepted.html',
        interview_id=interview.pk,
        context={'user':company_user,'interview':interview,
                 'application':app,'internship':internship,'student':student,'site_url':SITE_URL},
    )


def send_interview_reschedule_requested_email(company_user, interview, application=None) -> EmailResult:
    app        = application or getattr(interview, 'application', None)
    internship = getattr(app, 'internship', None)
    student    = getattr(app, 'applicant', None)
    return _send_notification_email(
        recipient=company_user,
        notif_type=Notification.TYPE_INTERVIEW_RESCHEDULE_REQUESTED,
        title='Student Requested Interview Reschedule',
        body='A student requested to reschedule the interview.',
        template_name='notifications/email/interview_reschedule_requested.html',
        interview_id=interview.pk,
        context={'user':company_user,'interview':interview,
                 'application':app,'internship':internship,'student':student,'site_url':SITE_URL},
    )


def send_interview_cancelled_email(student, interview, application=None) -> EmailResult:
    app        = application or getattr(interview, 'application', None)
    internship = getattr(app, 'internship', None)
    return _send_notification_email(
        recipient=student,
        notif_type=Notification.TYPE_INTERVIEW_CANCELLED,
        title='Interview Cancelled',
        body='The company has cancelled your interview.',
        template_name='notifications/email/interview_cancelled.html',
        interview_id=interview.pk,
        context={'user':student,'interview':interview,
                 'application':app,'internship':internship,'site_url':SITE_URL},
    )


def send_application_received_email(company_user, application) -> EmailResult:
    internship = getattr(application, 'internship', None)
    student    = getattr(application, 'applicant', None)
    return _send_notification_email(
        recipient=company_user,
        notif_type=Notification.TYPE_APPLICATION_RECEIVED,
        title='New Internship Application Received',
        body='A student has applied to your internship listing.',
        template_name='notifications/email/application_received.html',
        context={'user':company_user,'application':application,
                 'internship':internship,'student':student,'site_url':SITE_URL},
    )