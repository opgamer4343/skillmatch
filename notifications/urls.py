from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("api/count/",          views.notification_count, name="count"),
    path("api/list/",           views.notification_list,  name="list"),
    path("api/<int:pk>/read/",  views.mark_read,          name="mark_read"),
    path("api/read-all/",       views.mark_all_read,      name="mark_all_read"),
]