from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import StudentProfile, CompanyProfile
from assessment.models import (
    Question,
    AssessmentAttempt,
    AssessmentAnswer,
    CourseRecommendation,
    StudentCV,
)
from company.models import Internship
from notifications.models import Notification

User = get_user_model()

try:
    from company.models import Application, Interview
except Exception:  # pragma: no cover
    Application = None
    Interview = None


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_email_verified",
            "full_name",
        ]
        read_only_fields = ["id", "role", "is_email_verified", "full_name"]

    def get_full_name(self, obj):
        return (obj.get_full_name() or obj.username or obj.email).strip()


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "user",
            "university",
            "degree",
            "major",
            "graduation_year",
            "city",
            "linkedin_url",
            "bio",
            "skills",
            "resume",
        ]
        read_only_fields = ["id", "user"]


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = [
            "university",
            "degree",
            "major",
            "graduation_year",
            "city",
            "linkedin_url",
            "bio",
            "skills",
            "resume",
        ]


class CompanyProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = CompanyProfile
        fields = [
            "id",
            "user",
            "company_name",
            "industry",
            "website",
            "city",
            "description",
            "logo",
        ]
        read_only_fields = ["id", "user"]


class CompanyProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile
        fields = [
            "company_name",
            "industry",
            "website",
            "city",
            "description",
            "logo",
        ]


class InternshipSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    match_percentage = serializers.SerializerMethodField()
    qualifies_for_threshold = serializers.SerializerMethodField()

    class Meta:
        model = Internship
        fields = [
            "id",
            "company",
            "company_name",
            "title",
            "department",
            "description",
            "work_type",
            "duration",
            "required_skills",
            "stipend",
            "deadline",
            "status",
            "created_at",
            "match_percentage",
            "qualifies_for_threshold",
        ]
        read_only_fields = ["id", "company", "created_at", "company_name", "match_percentage", "qualifies_for_threshold"]

    def _get_student_profile(self):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or getattr(request.user, "role", None) != "student":
            return None
        return getattr(request.user, "student_profile", None)

    def _get_latest_attempt(self):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return (
            AssessmentAttempt.objects.filter(student=request.user, status="completed")
            .order_by("-completed_at", "-started_at")
            .first()
        )

    def get_company_name(self, obj):
        try:
            return obj.company.company_profile.company_name
        except Exception:
            return obj.company.get_full_name() or obj.company.username

    def get_match_percentage(self, obj):
        profile = self._get_student_profile()
        if not profile:
            return None

        student_skills = {str(s).strip().lower() for s in (profile.skills or []) if str(s).strip()}
        required_skills = {str(s).strip().lower() for s in (obj.required_skills or []) if str(s).strip()}

        if not required_skills:
            return 100

        matched = len(student_skills.intersection(required_skills))
        return round((matched / max(len(required_skills), 1)) * 100, 2)

    def get_qualifies_for_threshold(self, obj):
        attempt = self._get_latest_attempt()
        if not attempt:
            return None
        threshold = getattr(obj, "required_score_threshold", 0) or 0
        buffer_value = 2
        return attempt.overall_score >= max(threshold - buffer_value, 0)

    def validate_required_skills(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("required_skills must be a list.")
        return value


class InternshipCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Internship
        fields = [
            "title",
            "department",
            "description",
            "work_type",
            "duration",
            "required_skills",
            "stipend",
            "deadline",
            "status",
            "required_score_threshold",
        ]

    def validate_required_skills(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("required_skills must be a list.")
        return value


if Application is not None:
    class ApplicationSerializer(serializers.ModelSerializer):
        internship = InternshipSerializer(read_only=True)
        internship_id = serializers.PrimaryKeyRelatedField(
            queryset=Internship.objects.all(),
            source="internship",
            write_only=True,
        )
        applicant = UserSerializer(read_only=True)
        assessment_score = serializers.SerializerMethodField()
        assessment_band = serializers.SerializerMethodField()
        match_percentage = serializers.SerializerMethodField()
        cv_url = serializers.SerializerMethodField()

        class Meta:
            model = Application
            fields = [
                "id",
                "internship",
                "internship_id",
                "applicant",
                "cover_letter",
                "status",
                "created_at",
                "assessment_score",
                "assessment_band",
                "match_percentage",
                "cv_url",
            ]
            read_only_fields = ["id", "created_at", "status", "applicant", "assessment_score", "assessment_band", "match_percentage", "cv_url"]

        def get_latest_attempt(self, obj):
            return (
                AssessmentAttempt.objects.filter(student=obj.applicant, status="completed")
                .order_by("-completed_at", "-started_at")
                .first()
            )

        def get_assessment_score(self, obj):
            attempt = self.get_latest_attempt(obj)
            return getattr(attempt, "overall_score", None)

        def get_assessment_band(self, obj):
            attempt = self.get_latest_attempt(obj)
            return getattr(attempt, "score_band", None)

        def get_match_percentage(self, obj):
            profile = getattr(obj.applicant, "student_profile", None)
            if not profile:
                return None
            student_skills = {str(s).strip().lower() for s in (profile.skills or []) if str(s).strip()}
            required_skills = {str(s).strip().lower() for s in (obj.internship.required_skills or []) if str(s).strip()}
            if not required_skills:
                return 100
            return round((len(student_skills.intersection(required_skills)) / len(required_skills)) * 100, 2)

        def get_cv_url(self, obj):
            cv = StudentCV.objects.filter(user=obj.applicant).order_by("-uploaded_at").first()
            if not cv or not cv.file:
                return None
            request = self.context.get("request")
            url = cv.file.url
            return request.build_absolute_uri(url) if request else url


    class ApplicationCreateSerializer(serializers.ModelSerializer):
        internship_id = serializers.PrimaryKeyRelatedField(
            queryset=Internship.objects.filter(status="active"),
            source="internship",
        )

        class Meta:
            model = Application
            fields = ["internship_id", "cover_letter"]


if Interview is not None:
    class InterviewSerializer(serializers.ModelSerializer):
        application = serializers.SerializerMethodField()
        applicant = serializers.SerializerMethodField()
        role = serializers.SerializerMethodField()
        internship_title = serializers.SerializerMethodField()

        class Meta:
            model = Interview
            fields = [
                "id",
                "application",
                "applicant",
                "role",
                "internship_title",
                "scheduled_by",
                "interview_date",
                "interview_type",
                "meeting_link",
                "location",
                "notes",
                "status",
                "created_at",
            ]
            read_only_fields = ["id", "scheduled_by", "created_at"]

        def get_application(self, obj):
            return getattr(obj.application, "id", None)

        def get_applicant(self, obj):
            applicant = getattr(obj.application, "applicant", None)
            return UserSerializer(applicant).data if applicant else None

        def get_role(self, obj):
            internship = getattr(obj.application, "internship", None)
            return getattr(internship, "department", "") or getattr(internship, "title", "")

        def get_internship_title(self, obj):
            internship = getattr(obj.application, "internship", None)
            return getattr(internship, "title", None)


    class InterviewCreateSerializer(serializers.ModelSerializer):
        application_id = serializers.PrimaryKeyRelatedField(queryset=Application.objects.all(), source="application")

        class Meta:
            model = Interview
            fields = [
                "application_id",
                "interview_date",
                "interview_type",
                "meeting_link",
                "location",
                "notes",
            ]

        def validate(self, attrs):
            interview_type = attrs.get("interview_type")
            meeting_link = attrs.get("meeting_link")
            location = attrs.get("location")

            if interview_type == "video" and not meeting_link:
                raise serializers.ValidationError({"meeting_link": "Meeting link is required for video interviews."})
            if interview_type == "onsite" and not location:
                raise serializers.ValidationError({"location": "Location is required for onsite interviews."})
            return attrs


class SkillCategoryQuestionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_type = serializers.CharField(source="category.category_type", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "category",
            "category_name",
            "category_type",
            "text",
            "options",
            "difficulty",
            "is_ai_generated",
        ]


class AssessmentAnswerSerializer(serializers.ModelSerializer):
    question = SkillCategoryQuestionSerializer(read_only=True)
    question_id = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all(), source="question", write_only=True)

    class Meta:
        model = AssessmentAnswer
        fields = [
            "id",
            "attempt",
            "question",
            "question_id",
            "selected_answer",
            "is_correct",
            "time_taken_seconds",
        ]
        read_only_fields = ["id", "attempt", "is_correct"]


class AssessmentAttemptSerializer(serializers.ModelSerializer):
    answers = AssessmentAnswerSerializer(many=True, read_only=True)
    score_analysis = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentAttempt
        fields = [
            "id",
            "student",
            "attempt_number",
            "started_at",
            "completed_at",
            "technical_score",
            "soft_score",
            "overall_score",
            "score_band",
            "status",
            "answers",
            "score_analysis",
        ]
        read_only_fields = ["id", "student", "attempt_number", "started_at", "completed_at", "technical_score", "soft_score", "overall_score", "score_band", "status", "score_analysis"]

    def get_score_analysis(self, obj):
        return {
            "technical_score": obj.technical_score,
            "soft_score": obj.soft_score,
            "overall_score": obj.overall_score,
            "score_band": obj.score_band,
        }


class CourseRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseRecommendation
        fields = [
            "id",
            "student",
            "title",
            "provider",
            "url",
            "platform",
            "duration_hours",
            "is_completed",
        ]
        read_only_fields = ["id", "student"]


class StudentCVSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentCV
        fields = ["id", "user", "file", "source", "uploaded_at"]
        read_only_fields = ["id", "user", "uploaded_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "notif_type",
            "title",
            "body",
            "is_read",
            "email_sent",
            "interview_id",
            "created_at",
        ]
        read_only_fields = ["id", "recipient", "email_sent", "created_at"]
