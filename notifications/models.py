from django.conf import settings
from django.db import models


class Notification(models.Model):
    TYPE_OTP = 'otp'
    TYPE_INTERVIEW_SCHEDULED = 'interview_scheduled'
    TYPE_INTERVIEW_ACCEPTED = 'interview_accepted'
    TYPE_INTERVIEW_RESCHEDULE_REQUESTED = 'interview_reschedule_requested'
    TYPE_INTERVIEW_CANCELLED = 'interview_cancelled'
    TYPE_INTERVIEW_REMINDER = 'interview_reminder'
    TYPE_APPLICATION_RECEIVED = 'application_received'

    TYPE_CHOICES = [
        (TYPE_OTP, 'OTP Verification'),
        (TYPE_INTERVIEW_SCHEDULED, 'Interview Scheduled'),
        (TYPE_INTERVIEW_ACCEPTED, 'Interview Accepted'),
        (TYPE_INTERVIEW_RESCHEDULE_REQUESTED, 'Interview Reschedule Requested'),
        (TYPE_INTERVIEW_CANCELLED, 'Interview Cancelled'),
        (TYPE_INTERVIEW_REMINDER, 'Interview Reminder'),
        (TYPE_APPLICATION_RECEIVED, 'Application Received'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notif_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    interview_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient} - {self.title}'
