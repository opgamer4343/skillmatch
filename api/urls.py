from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from .views import (
    api_root,
    StudentProfileMeAPIView,
    CompanyProfileMeAPIView,
    InternshipListAPIView,
    InternshipDetailAPIView,
    CompanyInternshipListCreateAPIView,
    CompanyInternshipRetrieveUpdateDestroyAPIView,
    AssessmentHistoryAPIView,
    LatestAssessmentAPIView,
    CourseRecommendationListAPIView,
    MarkCourseCompleteAPIView,
    StudentCVListCreateAPIView,
    StudentCVDetailAPIView,
    NotificationListAPIView,
    NotificationCountAPIView,
    NotificationReadAPIView,
    NotificationReadAllAPIView,
)

urlpatterns = [
    path("", api_root, name="api-root"),

    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    path("student/profile/", StudentProfileMeAPIView.as_view(), name="student-profile-me"),
    path("company/profile/", CompanyProfileMeAPIView.as_view(), name="company-profile-me"),

    path("internships/", InternshipListAPIView.as_view(), name="internship-list"),
    path("internships/<int:pk>/", InternshipDetailAPIView.as_view(), name="internship-detail"),
    path("company/internships/", CompanyInternshipListCreateAPIView.as_view(), name="company-internship-list-create"),
    path("company/internships/<int:pk>/", CompanyInternshipRetrieveUpdateDestroyAPIView.as_view(), name="company-internship-detail"),

    path("assessment/history/", AssessmentHistoryAPIView.as_view(), name="assessment-history"),
    path("assessment/latest/", LatestAssessmentAPIView.as_view(), name="assessment-latest"),
    path("courses/", CourseRecommendationListAPIView.as_view(), name="course-list"),
    path("courses/<int:pk>/complete/", MarkCourseCompleteAPIView.as_view(), name="course-complete"),

    path("cvs/", StudentCVListCreateAPIView.as_view(), name="cv-list-create"),
    path("cvs/<int:pk>/", StudentCVDetailAPIView.as_view(), name="cv-detail"),

    path("notifications/", NotificationListAPIView.as_view(), name="notification-list"),
    path("notifications/count/", NotificationCountAPIView.as_view(), name="notification-count"),
    path("notifications/<int:pk>/read/", NotificationReadAPIView.as_view(), name="notification-read"),
    path("notifications/read-all/", NotificationReadAllAPIView.as_view(), name="notification-read-all"),
]

try:
    from .views import (
        StudentApplicationListCreateAPIView,
        StudentApplicationDetailAPIView,
        CompanyApplicantListAPIView,
        StudentInterviewListAPIView,
        CompanyInterviewListCreateAPIView,
        StudentInterviewActionAPIView,
    )
except Exception:  # pragma: no cover
    pass
else:
    urlpatterns += [
        path("applications/", StudentApplicationListCreateAPIView.as_view(), name="student-application-list-create"),
        path("applications/<int:pk>/", StudentApplicationDetailAPIView.as_view(), name="student-application-detail"),
        path("company/applicants/", CompanyApplicantListAPIView.as_view(), name="company-applicant-list"),
        path("student/interviews/", StudentInterviewListAPIView.as_view(), name="student-interview-list"),
        path("company/interviews/", CompanyInterviewListCreateAPIView.as_view(), name="company-interview-list-create"),
        path("student/interviews/<int:pk>/<str:action>/", StudentInterviewActionAPIView.as_view(), name="student-interview-action"),
    ]
