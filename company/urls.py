from django.urls import path
from . import views

app_name = "company"

urlpatterns = [
    path("",                                            views.overview,                 name="overview"),
    path("setup/",                                      views.setup_profile,            name="setup"),
    path("internships/",                                views.internships,              name="internships"),
    path("internships/post/",                           views.post_internship,          name="post_internship"),
    path("internships/<int:pk>/edit/",                  views.edit_internship,          name="edit_internship"),
    path("internships/<int:pk>/delete/",                views.delete_internship,        name="delete_internship"),
    path("applicants/",                                 views.applicants,               name="applicants"),
    path("applicants/<int:pk>/status/",                 views.update_application_status,name="update_status"),
    path("applicants/<int:applicant_id>/cv/",           views.download_cv,              name="download_cv"),
    path("interviews/",                                 views.interviews,               name="interviews"),
    path("interviews/schedule/",                        views.schedule_interview,       name="schedule_interview"),
    path("interviews/schedule/<int:application_id>/",   views.schedule_interview,       name="schedule_interview_for"),
    path("interviews/<int:pk>/cancel/",                 views.cancel_interview,         name="cancel_interview"),
    path("interviews/<int:pk>/reschedule/",             views.reschedule_interview,      name="reschedule_interview"),
    path("profile/",                                    views.company_profile,          name="profile"),
    path("google/connect/",                             views.google_connect_start,     name="google_connect_start"),
    path("google/callback/",                            views.google_connect_callback,  name="google_connect_callback"),
    path("google/disconnect/",                          views.google_disconnect,        name="google_disconnect"),
    path("reviews/",                                    views.all_reviews,              name="reviews"),
    path("settings/",                                   views.settings_view,            name="settings"),
]