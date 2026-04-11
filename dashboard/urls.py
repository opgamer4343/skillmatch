from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("",                                    views.overview,           name="overview"),
    path("internships/",                        views.internships,        name="internships"),
    path("internships/<int:pk>/apply/",         views.apply_internship,   name="apply"),
    path("applications/",                       views.applications,       name="applications"),
    path("interviews/",                         views.interviews,         name="interviews"),
    path("interviews/<int:pk>/accept/",         views.accept_interview,   name="accept_interview"),
    path("interviews/<int:pk>/reschedule/",     views.reschedule_interview, name="reschedule_interview"),
    path("interviews/<int:interview_id>/prep/", views.interview_prep,     name="interview_prep"),
    path("profile/",                            views.profile_view,       name="profile"),
    path("resume/download/",                    views.download_resume,    name="download_resume"),
    path("cv/download/",                        views.download_cv,        name="download_cv"),
    path("reviews/<int:company_id>/",           views.company_reviews,    name="company_reviews"),
    path("reviews/<int:company_id>/write/",     views.write_review,       name="write_review"),
]