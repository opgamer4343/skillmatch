import json
import random
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import (
    CompanyRegisterProfileForm,
    CompanyRegisterStepOneForm,
    ForgotPasswordForm,
    LoginForm,
    OTPVerificationForm,
    StudentRegisterProfileForm,
    StudentRegisterSkillsForm,
    StudentRegisterStepOneForm,
)
from .models import CompanyProfile, StudentProfile, User


STUDENT_REGISTRATION_SESSION_KEY = "student_registration_data"
COMPANY_REGISTRATION_SESSION_KEY = "company_registration_data"
OTP_SESSION_KEY = "pending_otp"
OTP_VALID_MINUTES = 10


def _send_otp_email(user, request):
    code = f"{random.randint(0, 999999):06d}"
    expires_at = timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)
    request.session[OTP_SESSION_KEY] = {
        "user_id": user.id,
        "code": code,
        "expires_at": expires_at.isoformat(),
    }
    request.session.modified = True
    send_mail(
        subject="SkillMatch email verification code",
        message=(
            f"Hi {user.first_name or user.email},\n\n"
            f"Your SkillMatch verification code is: {code}\n"
            f"This code expires in {OTP_VALID_MINUTES} minutes.\n\n"
            "If you did not create this account, you can ignore this email."
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
        fail_silently=True,
    )
    return code


def _get_pending_otp_payload(request):
    payload = request.session.get(OTP_SESSION_KEY)
    if not payload:
        return None
    try:
        expires_at = timezone.datetime.fromisoformat(payload["expires_at"])
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
    except Exception:
        request.session.pop(OTP_SESSION_KEY, None)
        return None
    payload["expires_at_dt"] = expires_at
    return payload


def _redirect_by_role(user):
    if user.role == User.Role.COMPANY:
        return redirect("company:overview")
    return redirect("dashboard:overview")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    form = LoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, "Welcome back.")
        return _redirect_by_role(user)
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    initial = request.session.get(STUDENT_REGISTRATION_SESSION_KEY, {})
    form = StudentRegisterStepOneForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        request.session[STUDENT_REGISTRATION_SESSION_KEY] = form.cleaned_data
        request.session.modified = True
        return redirect("accounts:register_profile")
    return render(request, "accounts/register.html", {"form": form, "step": 1})


@require_http_methods(["GET", "POST"])
def register_profile_view(request):
    step1 = request.session.get(STUDENT_REGISTRATION_SESSION_KEY)
    if not step1:
        messages.warning(request, "Complete step 1 first.")
        return redirect("accounts:register")

    form = StudentRegisterProfileForm(request.POST or None, initial=step1.get("profile", {}))
    if request.method == "POST" and form.is_valid():
        step1["profile"] = form.cleaned_data
        request.session[STUDENT_REGISTRATION_SESSION_KEY] = step1
        request.session.modified = True
        return redirect("accounts:register_skills")
    return render(request, "accounts/register_profile.html", {"form": form, "step": 2})


@require_http_methods(["GET", "POST"])
def register_skills_view(request):
    registration = request.session.get(STUDENT_REGISTRATION_SESSION_KEY)
    if not registration or "profile" not in registration:
        messages.warning(request, "Complete the previous registration steps first.")
        return redirect("accounts:register")

    initial = {"skills_json": json.dumps(registration.get("skills", []))}
    form = StudentRegisterSkillsForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            email=registration["email"],
            password=registration["password1"],
            role=User.Role.STUDENT,
            first_name=registration["first_name"],
            last_name=registration["last_name"],
            is_active=True,
        )
        user.is_email_verified = False
        user.save(update_fields=["is_email_verified"])

        profile_data = registration["profile"]
        StudentProfile.objects.create(
            user=user,
            university=profile_data["university"],
            degree=profile_data["degree"],
            major=profile_data["major"],
            graduation_year=profile_data["graduation_year"],
            city=profile_data["city"],
            linkedin_url=profile_data.get("linkedin_url", ""),
            bio=profile_data.get("bio", ""),
            skills=form.cleaned_data["skills_json"],
            resume=form.cleaned_data.get("resume"),
        )
        request.session.pop(STUDENT_REGISTRATION_SESSION_KEY, None)
        _send_otp_email(user, request)
        messages.success(request, "Account created. Enter the OTP sent to your email.")
        return redirect("accounts:verify")
    return render(request, "accounts/register_skills.html", {"form": form, "step": 3})


@require_http_methods(["GET", "POST"])
def company_register_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    initial = request.session.get(COMPANY_REGISTRATION_SESSION_KEY, {})
    form = CompanyRegisterStepOneForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        request.session[COMPANY_REGISTRATION_SESSION_KEY] = form.cleaned_data
        request.session.modified = True
        return redirect("accounts:register_company_profile")
    return render(request, "accounts/company_register.html", {"form": form, "step": 1})


@require_http_methods(["GET", "POST"])
def company_register_profile_view(request):
    registration = request.session.get(COMPANY_REGISTRATION_SESSION_KEY)
    if not registration:
        messages.warning(request, "Complete company registration step 1 first.")
        return redirect("accounts:register_company")

    form = CompanyRegisterProfileForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            email=registration["email"],
            password=registration["password1"],
            role=User.Role.COMPANY,
            first_name=registration["first_name"],
            last_name=registration["last_name"],
            is_active=True,
        )
        user.is_email_verified = False
        user.save(update_fields=["is_email_verified"])
        CompanyProfile.objects.create(
            user=user,
            company_name=registration["company_name"],
            industry=form.cleaned_data.get("industry", ""),
            city=form.cleaned_data.get("city", ""),
            website=form.cleaned_data.get("website", ""),
            description=form.cleaned_data.get("description", ""),
        )
        request.session.pop(COMPANY_REGISTRATION_SESSION_KEY, None)
        _send_otp_email(user, request)
        messages.success(request, "Company account created. Verify your email to continue.")
        return redirect("accounts:verify")
    return render(request, "accounts/company_register_profile.html", {"form": form, "step": 2})


@require_http_methods(["GET", "POST"])
def verify_email_view(request):
    payload = _get_pending_otp_payload(request)
    if not payload:
        messages.warning(request, "No verification is pending. Please register first.")
        return redirect("accounts:login")

    form = OTPVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if timezone.now() > payload["expires_at_dt"]:
            request.session.pop(OTP_SESSION_KEY, None)
            messages.error(request, "Your OTP has expired. Request a new code.")
            return redirect("accounts:verify")
        if form.cleaned_data["code"] != payload["code"]:
            messages.error(request, "Invalid verification code.")
        else:
            user = User.objects.filter(id=payload["user_id"]).first()
            if not user:
                request.session.pop(OTP_SESSION_KEY, None)
                messages.error(request, "The account could not be found.")
                return redirect("accounts:login")
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
            request.session.pop(OTP_SESSION_KEY, None)
            login(request, user)
            messages.success(request, "Email verified successfully.")
            return redirect("accounts:welcome")
    return render(request, "accounts/verify_email.html", {"form": form, "pending": payload})


@login_required
def resend_verification_view(request):
    if request.user.is_email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect("accounts:welcome")
    _send_otp_email(request.user, request)
    messages.success(request, "A new verification code has been sent.")
    return redirect("accounts:verify")


@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    view = PasswordResetView.as_view(
        template_name="accounts/forgot_password.html",
        email_template_name="registration/password_reset_email.html",
        subject_template_name="registration/password_reset_subject.txt",
        form_class=ForgotPasswordForm,
        success_url=reverse_lazy("accounts:password_reset_done"),
    )
    return view(request)


@login_required
def welcome_view(request):
    if not request.user.is_email_verified:
        messages.warning(request, "Verify your email to continue.")
        return redirect("accounts:verify")
    return render(request, "accounts/welcome.html")


# ── Delete Account ────────────────────────────────────────────────────────────

@login_required
def delete_account_view(request):
    """
    Permanently deletes the user account and all related data from DB.
    Requires password confirmation before deletion.
    Works for both student and company roles.
    """
    from django.contrib.auth import logout, authenticate

    if request.method == "POST":
        password    = request.POST.get("password", "").strip()
        confirm_text= request.POST.get("confirm_text", "").strip()

        # Must type DELETE to confirm
        if confirm_text != "DELETE":
            messages.error(request, "Please type DELETE exactly to confirm.")
            return redirect("accounts:delete_account")

        # Verify password
        user = authenticate(
            request,
            username=request.user.username or request.user.email,
            password=password,
        )
        if user is None:
            # Try email-based auth
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()
            try:
                u = UserModel.objects.get(email=request.user.email)
                if not u.check_password(password):
                    messages.error(request, "Incorrect password. Account not deleted.")
                    return redirect("accounts:delete_account")
                user = u
            except UserModel.DoesNotExist:
                messages.error(request, "Incorrect password. Account not deleted.")
                return redirect("accounts:delete_account")

        role  = request.user.role
        email = request.user.email
        name  = request.user.get_full_name() or email

        # Log out before deleting
        logout(request)

        # Delete user — CASCADE removes all related objects:
        # StudentProfile, CompanyProfile, Applications,
        # Interviews, AssessmentAttempts, Notifications, etc.
        user.delete()

        # Redirect to login with goodbye message
        return redirect(f"/accounts/login/?deleted=1&role={role}")

    return render(request, "accounts/delete_account.html", {
        "user": request.user,
    })