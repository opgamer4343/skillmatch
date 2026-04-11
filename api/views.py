from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import StudentProfile, CompanyProfile
from assessment.models import AssessmentAttempt, CourseRecommendation, StudentCV
from company.models import Internship
from notifications.models import Notification

try:
    from company.models import Application, Interview
except Exception:  # pragma: no cover
    Application = None
    Interview = None

from .pagination import DefaultPageNumberPagination, LargeResultsPagination, SmallResultsPagination
from .permissions import IsStudent, IsCompany
from .serializers import (
    StudentProfileSerializer,
    StudentProfileUpdateSerializer,
    CompanyProfileSerializer,
    CompanyProfileUpdateSerializer,
    InternshipSerializer,
    InternshipCreateUpdateSerializer,
    AssessmentAttemptSerializer,
    CourseRecommendationSerializer,
    StudentCVSerializer,
    NotificationSerializer,
)

if Application is not None:
    from .serializers import ApplicationSerializer, ApplicationCreateSerializer
if Interview is not None:
    from .serializers import InterviewSerializer, InterviewCreateSerializer


class StudentProfileMeAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        profile, _ = StudentProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return StudentProfileUpdateSerializer
        return StudentProfileSerializer


class CompanyProfileMeAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCompany]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        profile, _ = CompanyProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return CompanyProfileUpdateSerializer
        return CompanyProfileSerializer


class InternshipListAPIView(generics.ListAPIView):
    serializer_class = InternshipSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargeResultsPagination

    def get_queryset(self):
        queryset = Internship.objects.filter(status="active").select_related("company").order_by("-created_at")
        work_type = self.request.query_params.get("work_type")
        skill = self.request.query_params.get("skill")
        duration = self.request.query_params.get("duration")
        search = self.request.query_params.get("search")

        if work_type:
            queryset = queryset.filter(work_type__iexact=work_type)
        if duration:
            queryset = queryset.filter(duration__icontains=duration)
        if skill:
            queryset = queryset.filter(required_skills__icontains=skill)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(department__icontains=search) |
                Q(description__icontains=search)
            )
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class InternshipDetailAPIView(generics.RetrieveAPIView):
    queryset = Internship.objects.select_related("company").all()
    serializer_class = InternshipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class CompanyInternshipListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCompany]
    pagination_class = DefaultPageNumberPagination

    def get_queryset(self):
        return Internship.objects.filter(company=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return InternshipCreateUpdateSerializer
        return InternshipSerializer

    def perform_create(self, serializer):
        serializer.save(company=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class CompanyInternshipRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCompany]

    def get_queryset(self):
        return Internship.objects.filter(company=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return InternshipCreateUpdateSerializer
        return InternshipSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


if Application is not None:
    class StudentApplicationListCreateAPIView(generics.ListCreateAPIView):
        permission_classes = [permissions.IsAuthenticated, IsStudent]
        pagination_class = DefaultPageNumberPagination

        def get_queryset(self):
            return (
                Application.objects.filter(applicant=self.request.user)
                .select_related("internship", "internship__company", "applicant")
                .order_by("-created_at")
            )

        def get_serializer_class(self):
            if self.request.method == "POST":
                return ApplicationCreateSerializer
            return ApplicationSerializer

        def perform_create(self, serializer):
            internship = serializer.validated_data["internship"]
            already_applied = Application.objects.filter(internship=internship, applicant=self.request.user).exists()
            if already_applied:
                raise ValidationError({"detail": "You have already applied to this internship."})
            serializer.save(applicant=self.request.user)

        def get_serializer_context(self):
            context = super().get_serializer_context()
            context["request"] = self.request
            return context


    class StudentApplicationDetailAPIView(generics.RetrieveAPIView):
        serializer_class = ApplicationSerializer
        permission_classes = [permissions.IsAuthenticated, IsStudent]

        def get_queryset(self):
            return Application.objects.filter(applicant=self.request.user).select_related("internship", "internship__company", "applicant")

        def get_serializer_context(self):
            context = super().get_serializer_context()
            context["request"] = self.request
            return context


    class CompanyApplicantListAPIView(generics.ListAPIView):
        serializer_class = ApplicationSerializer
        permission_classes = [permissions.IsAuthenticated, IsCompany]
        pagination_class = LargeResultsPagination

        def get_queryset(self):
            queryset = (
                Application.objects.filter(internship__company=self.request.user)
                .select_related("internship", "applicant", "applicant__student_profile")
                .order_by("-created_at")
            )

            internship_id = self.request.query_params.get("internship")
            status_param = self.request.query_params.get("status")
            if internship_id:
                queryset = queryset.filter(internship_id=internship_id)
            if status_param:
                queryset = queryset.filter(status=status_param)

            # Annotate with latest assessment score for ordering
            from django.db.models import Subquery, OuterRef, DecimalField
            from django.db.models.functions import Coalesce
            latest_score = (
                AssessmentAttempt.objects
                .filter(student=OuterRef("applicant"), status="completed")
                .order_by("-completed_at", "-started_at")
                .values("overall_score")[:1]
            )
            queryset = queryset.annotate(
                latest_score=Coalesce(
                    Subquery(latest_score, output_field=DecimalField()),
                    -1,
                    output_field=DecimalField(),
                )
            ).order_by("-latest_score")

            return queryset

        def get_serializer_context(self):
            context = super().get_serializer_context()
            context["request"] = self.request
            return context


if Interview is not None:
    class StudentInterviewListAPIView(generics.ListAPIView):
        serializer_class = InterviewSerializer
        permission_classes = [permissions.IsAuthenticated, IsStudent]
        pagination_class = DefaultPageNumberPagination

        def get_queryset(self):
            return (
                Interview.objects.filter(application__applicant=self.request.user)
                .select_related("application", "application__internship", "application__applicant", "scheduled_by")
                .order_by("interview_date")
            )


    class CompanyInterviewListCreateAPIView(generics.ListCreateAPIView):
        permission_classes = [permissions.IsAuthenticated, IsCompany]
        pagination_class = DefaultPageNumberPagination

        def get_queryset(self):
            return (
                Interview.objects.filter(application__internship__company=self.request.user)
                .select_related("application", "application__internship", "application__applicant", "scheduled_by")
                .order_by("interview_date")
            )

        def get_serializer_class(self):
            if self.request.method == "POST":
                return InterviewCreateSerializer
            return InterviewSerializer

        def perform_create(self, serializer):
            application = serializer.validated_data["application"]
            if application.internship.company_id != self.request.user.id:
                raise PermissionDenied("You can only schedule interviews for your own internships.")

            interview = serializer.save(scheduled_by=self.request.user)
            if hasattr(application, "status"):
                application.status = "interview"
                application.save(update_fields=["status"])
            return interview


    class StudentInterviewActionAPIView(APIView):
        permission_classes = [permissions.IsAuthenticated, IsStudent]

        def post(self, request, pk, action):
            try:
                interview = Interview.objects.select_related("application").get(pk=pk, application__applicant=request.user)
            except Interview.DoesNotExist:
                raise PermissionDenied("Interview not found.")

            if action == "accept":
                interview.status = "accepted"
                interview.save(update_fields=["status"])
                return Response({"detail": "Interview accepted."}, status=status.HTTP_200_OK)

            if action == "reschedule":
                notes = request.data.get("notes", "").strip()
                interview.status = "reschedule_requested"
                interview.notes = f"{interview.notes or ''}\n\nReschedule request: {notes}".strip()
                interview.save(update_fields=["status", "notes"])
                return Response({"detail": "Reschedule requested."}, status=status.HTTP_200_OK)

            raise ValidationError({"detail": "Unsupported action."})


class AssessmentHistoryAPIView(generics.ListAPIView):
    serializer_class = AssessmentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    pagination_class = SmallResultsPagination

    def get_queryset(self):
        return AssessmentAttempt.objects.filter(student=self.request.user).order_by("-completed_at", "-started_at")


class LatestAssessmentAPIView(generics.RetrieveAPIView):
    serializer_class = AssessmentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get_object(self):
        attempt = (
            AssessmentAttempt.objects.filter(student=self.request.user, status="completed")
            .order_by("-completed_at", "-started_at")
            .first()
        )
        if not attempt:
            raise ValidationError({"detail": "No completed assessment attempt found."})
        return attempt


class CourseRecommendationListAPIView(generics.ListAPIView):
    serializer_class = CourseRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    pagination_class = DefaultPageNumberPagination

    def get_queryset(self):
        return CourseRecommendation.objects.filter(student=self.request.user).order_by("-id")


class MarkCourseCompleteAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request, pk):
        try:
            course = CourseRecommendation.objects.get(pk=pk, student=request.user)
        except CourseRecommendation.DoesNotExist:
            raise ValidationError({"detail": "Course not found."})
        course.is_completed = True
        course.save(update_fields=["is_completed"])
        return Response({"detail": "Course marked as completed."}, status=status.HTTP_200_OK)


class StudentCVListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = StudentCVSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = SmallResultsPagination

    def get_queryset(self):
        return StudentCV.objects.filter(user=self.request.user).order_by("-uploaded_at")

    def perform_create(self, serializer):
        existing = StudentCV.objects.filter(user=self.request.user)
        if existing.exists():
            existing.delete()
        serializer.save(user=self.request.user)


class StudentCVDetailAPIView(generics.RetrieveAPIView):
    serializer_class = StudentCVSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get_queryset(self):
        return StudentCV.objects.filter(user=self.request.user)


class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPageNumberPagination

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by("-created_at")


class NotificationCountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": unread_count}, status=status.HTTP_200_OK)


class NotificationReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            raise ValidationError({"detail": "Notification not found."})
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"detail": "Notification marked as read."}, status=status.HTTP_200_OK)


class NotificationReadAllAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "Notifications marked as read.", "updated": updated}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_root(request):
    return Response(
        {
            "message": "SkillMatch API",
            "user_role": getattr(request.user, "role", None),
            "server_time": timezone.now(),
        }
    )
