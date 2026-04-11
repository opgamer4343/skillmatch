from django.urls import path
from . import views

app_name = "assessment"

urlpatterns = [
    path("", views.assessment_home, name="home"),
    path("start/", views.start_assessment, name="start"),
    path("<int:attempt_id>/question/", views.question_view, name="question"),
    path("<int:attempt_id>/finish/", views.finish_assessment, name="finish"),
    path("api/history/", views.score_history_json, name="history_json"),
    path("courses/<int:pk>/complete/", views.mark_course_complete, name="course_complete"),
    path("cv/", views.cv_home, name="cv_home"),
    path("cv/upload/", views.cv_upload, name="cv_upload"),
    path("cv/generate/", views.cv_generate, name="generate_cv"),
    path("cv/download/", views.cv_download, name="cv_download"),
]
