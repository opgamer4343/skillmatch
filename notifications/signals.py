# ─────────────────────────────────────────────────────────────────────
# FULL FILE: notifications/signals.py
# Replace your entire signals.py with this.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.apps import apps

logger = logging.getLogger(__name__)


def get_interview_model():
    return apps.get_model('company', 'Interview')


def get_application_model():
    return apps.get_model('company', 'Application')


def _safe_delay(task, *args, **kwargs):
    """
    Fire a Celery task safely.
    If Redis is not running, logs a warning instead of crashing.
    """
    try:
        task.delay(*args, **kwargs)
    except Exception as exc:
        logger.warning(
            "Celery task %s could not be queued (Redis unavailable): %s",
            getattr(task, 'name', str(task)),
            exc,
        )


def _connect_signals():
    """Called from NotificationsConfig.ready() after app registry is ready."""
    from .tasks import (
        send_application_received_email_task,
        send_interview_accepted_email_task,
        send_interview_cancelled_email_task,
        send_interview_reschedule_requested_email_task,
        send_interview_scheduled_email_task,
    )

    Interview   = get_interview_model()
    Application = get_application_model()

    @receiver(pre_save, sender=Interview,
              dispatch_uid="cache_prev_interview_status")
    def cache_previous_interview_status(sender, instance, **kwargs):
        if not instance.pk:
            instance._previous_status = None
            return
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._previous_status = old.status
        except sender.DoesNotExist:
            instance._previous_status = None

    @receiver(post_save, sender=Interview,
              dispatch_uid="interview_event_signal")
    def interview_event_signal(sender, instance, created, **kwargs):
        # NOTE: initial confirmation email is sent directly in the view
        # (no Redis needed). Signals only handle status change emails.
        if created:
            return  # view already sent the confirmation email
        prev = getattr(instance, '_previous_status', None)
        curr = instance.status
        if prev == curr:
            return
        if curr == 'accepted':
            _safe_delay(send_interview_accepted_email_task, instance.pk)
        elif curr == 'reschedule_requested':
            _safe_delay(send_interview_reschedule_requested_email_task, instance.pk)
        elif curr == 'cancelled':
            _safe_delay(send_interview_cancelled_email_task, instance.pk)

    @receiver(post_save, sender=Application,
              dispatch_uid="application_created_signal")
    def application_created_signal(sender, instance, created, **kwargs):
        if created:
            # Send directly (no Redis needed) — fallback to Celery if available
            try:
                from .email_service import send_application_received_email
                company_user = instance.internship.company
                send_application_received_email(company_user, instance)
            except Exception as exc:
                logger.warning("Application email failed: %s", exc)