from django.contrib import admin
from .models import (
    AssessmentAnswer,
    AssessmentAttempt,
    CourseRecommendation,
    Question,
    SkillCategory,
    StudentCV,
)


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display  = ("name", "category_type", "weight")
    list_filter   = ("category_type",)
    search_fields = ("name",)
    ordering      = ("category_type", "name")


class AssessmentAnswerInline(admin.TabularInline):
    model  = AssessmentAnswer
    extra  = 0
    fields = ("question", "selected_answer", "is_correct", "time_taken_seconds")
    readonly_fields = ("question", "selected_answer", "is_correct", "time_taken_seconds")
    can_delete = False


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display   = ("short_text", "category", "difficulty", "is_ai_generated", "created_at")
    list_filter    = ("category__category_type", "category", "difficulty", "is_ai_generated")
    search_fields  = ("text",)
    ordering       = ("category__name", "difficulty")
    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {
            "fields": ("category", "difficulty", "is_ai_generated"),
        }),
        ("Question", {
            "fields": ("text", "options", "correct_index", "explanation"),
        }),
        ("Meta", {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    def short_text(self, obj):
        return obj.text[:80] + "…" if len(obj.text) > 80 else obj.text
    short_text.short_description = "Question"


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display   = ("student", "attempt_number", "overall_score", "score_band", "status", "started_at")
    list_filter    = ("status", "score_band")
    search_fields  = ("student__email",)
    ordering       = ("-started_at",)
    readonly_fields = (
        "student", "attempt_number", "started_at", "completed_at",
        "technical_score", "soft_score", "overall_score", "score_band",
        "strengths", "weak_areas", "job_readiness_message", "improvement_priority",
    )
    inlines = [AssessmentAnswerInline]


@admin.register(CourseRecommendation)
class CourseRecommendationAdmin(admin.ModelAdmin):
    list_display  = ("title", "student", "platform", "priority", "is_completed")
    list_filter   = ("platform", "is_completed")
    search_fields = ("title", "student__email")
    ordering      = ("priority",)


@admin.register(StudentCV)
class StudentCVAdmin(admin.ModelAdmin):
    list_display  = ("user", "source", "uploaded_at")
    list_filter   = ("source",)
    search_fields = ("user__email",)
    ordering      = ("-uploaded_at",)
