from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SkillCategory(models.Model):
    class CategoryType(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        SOFT = "soft", "Soft"

    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(max_length=20, choices=CategoryType.choices)
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=1.00)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Skill categories"
        ordering = ["category_type", "name"]

    def __str__(self):
        return self.name


class Question(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    options = models.JSONField(default=list)
    correct_index = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(3)])
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    explanation = models.TextField(blank=True)
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category__name", "id"]

    def __str__(self):
        return f"{self.category.name}: {self.text[:60]}"


class AssessmentAttempt(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"
        ABANDONED = "abandoned", "Abandoned"

    class ScoreBand(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        FOUNDATION = "foundation", "Foundation"
        INTERMEDIATE = "intermediate", "Intermediate"
        STRONG = "strong", "Strong"
        EXPERT = "expert", "Expert"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_attempts", limit_choices_to={"role": "student"})
    attempt_number = models.PositiveIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    technical_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    soft_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    score_band = models.CharField(max_length=20, choices=ScoreBand.choices, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STARTED)
    strengths = models.JSONField(default=list, blank=True)
    weak_areas = models.JSONField(default=list, blank=True)
    job_readiness_message = models.TextField(blank=True)
    improvement_priority = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        unique_together = ("student", "attempt_number")

    def __str__(self):
        return f"Attempt {self.attempt_number} - {self.student.email}"


class AssessmentAnswer(models.Model):
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers", null=True, blank=True)
    selected_answer = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(3)], null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    time_taken_seconds = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("attempt", "question")

    def __str__(self):
        return f"Answer<{self.attempt_id}:{self.question_id}>"


class CourseRecommendation(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_recommendations", limit_choices_to={"role": "student"})
    title = models.CharField(max_length=255)
    provider = models.CharField(max_length=255)
    url = models.URLField()
    platform = models.CharField(max_length=100)
    duration_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    reason = models.TextField(blank=True)
    priority = models.PositiveSmallIntegerField(default=1)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["priority", "-created_at"]

    def __str__(self):
        return self.title


class StudentCV(models.Model):
    class Source(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        AI_GENERATED = "ai_generated", "AI Generated"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_cv", limit_choices_to={"role": "student"})
    file = models.FileField(upload_to="cvs/")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.UPLOADED)
    uploaded_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CV<{self.user.email}>"
