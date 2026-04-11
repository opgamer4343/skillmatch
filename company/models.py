from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Internship(models.Model):
    class WorkType(models.TextChoices):
        REMOTE = "remote", "Remote"
        ONSITE = "onsite", "Onsite"
        HYBRID = "hybrid", "Hybrid"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DRAFT = "draft", "Draft"
        CLOSED = "closed", "Closed"

    company = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="internships", limit_choices_to={"role": "company"}
    )
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    work_type = models.CharField(max_length=20, choices=WorkType.choices)
    duration = models.CharField(max_length=100)
    required_skills = models.JSONField(default=list, blank=True)
    stipend = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)], null=True, blank=True
    )
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    required_score_threshold = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}"


class Application(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        REVIEW = "review", "Review"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer"
        REJECTED = "rejected", "Rejected"

    internship = models.ForeignKey(Internship, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="applications", limit_choices_to={"role": "student"}
    )
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("internship", "applicant")

    def __str__(self):
        return f"{self.applicant} -> {self.internship}"


class Interview(models.Model):
    class InterviewType(models.TextChoices):
        VIDEO = "video", "Video"
        PHONE = "phone", "Phone"
        ONSITE = "onsite", "Onsite"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ACCEPTED = "accepted", "Accepted"
        RESCHEDULE_REQUESTED = "reschedule_requested", "Reschedule Requested"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="interview")
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scheduled_interviews"
    )
    interview_date = models.DateTimeField()
    interview_type = models.CharField(max_length=20, choices=InterviewType.choices)
    meeting_link = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SCHEDULED)

    google_event_id = models.CharField(max_length=255, blank=True)
    google_meet_link = models.URLField(blank=True)
    google_calendar_sync_status = models.CharField(max_length=30, default="not_synced", blank=True)
    reminder_48h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)
    reminder_now_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["interview_date"]

    def clean(self):
        if self.interview_type in {"video", "phone"} and not self.meeting_link:
            raise ValidationError({"meeting_link": "Meeting link is required for video or phone interviews."})
        if self.interview_type == "onsite" and not self.location:
            raise ValidationError({"location": "Location is required for onsite interviews."})


    @property
    def effective_meeting_link(self):
        return self.google_meet_link or self.meeting_link

    def __str__(self):
        return f"Interview for {self.application}"


# ── Company Review ────────────────────────────────────────────────────────────

class CompanyReview(models.Model):
    class Rating(models.IntegerChoices):
        ONE   = 1, "★☆☆☆☆"
        TWO   = 2, "★★☆☆☆"
        THREE = 3, "★★★☆☆"
        FOUR  = 4, "★★★★☆"
        FIVE  = 5, "★★★★★"

    company     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="reviews", limit_choices_to={"role": "company"}
    )
    reviewer    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="company_reviews", limit_choices_to={"role": "student"}
    )
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE,
        related_name="review", null=True, blank=True
    )
    # Ratings
    overall_rating      = models.PositiveSmallIntegerField(choices=Rating.choices)
    process_rating      = models.PositiveSmallIntegerField(
        choices=Rating.choices, help_text="How smooth was the hiring process?")
    communication_rating = models.PositiveSmallIntegerField(
        choices=Rating.choices, help_text="How well did they communicate?")
    # Written review
    title   = models.CharField(max_length=120)
    body    = models.TextField(help_text="Share your experience with this company.")
    # Anonymous option
    is_anonymous = models.BooleanField(default=False)
    # Moderation
    is_approved  = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("company", "reviewer")

    def __str__(self):
        return f"{self.reviewer} → {self.company} ({self.overall_rating}★)"

    @property
    def display_name(self):
        if self.is_anonymous:
            return "Anonymous Student"
        return self.reviewer.get_full_name() or self.reviewer.email


# ── Interview Prep Session ────────────────────────────────────────────────────

class InterviewPrepSession(models.Model):
    interview   = models.OneToOneField(
        Interview, on_delete=models.CASCADE,
        related_name="prep_session"
    )
    student     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="prep_sessions"
    )
    questions   = models.JSONField(default=list)   # AI-generated questions
    tips        = models.JSONField(default=list)   # AI tips
    company_summary = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prep for {self.interview}"