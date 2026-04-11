from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import CustomSetPasswordForm
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("register/profile/", views.register_profile_view, name="register_profile"),
    path("register/skills/", views.register_skills_view, name="register_skills"),
    path("register/company/", views.company_register_view, name="register_company"),
    path("register/company/profile/", views.company_register_profile_view, name="register_company_profile"),
    path("verify/", views.verify_email_view, name="verify"),
    path("verify/resend/", views.resend_verification_view, name="verify_resend"),
    path("welcome/", views.welcome_view, name="welcome"),
    path("delete/", views.delete_account_view, name="delete_account"),
    path("password/reset/", views.forgot_password_view, name="password_reset"),
    path(
        "password/reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            form_class=CustomSetPasswordForm,
            success_url="/accounts/password/reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]