from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


def root_redirect(request):
    if request.user.is_authenticated:
        if getattr(request.user, "role", None) == "company":
            return redirect("company:overview")
        return redirect("dashboard:overview")
    return redirect("accounts:login")


urlpatterns = [
    path("", root_redirect, name="root"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("company/", include("company.urls")),
    path("assessment/", include("assessment.urls")),
    path("notifications/", include("notifications.urls")),
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
