import json
from datetime import date

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError

from .models import CompanyProfile, StudentProfile, User


CURRENT_YEAR = date.today().year
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_SIZE = 5 * 1024 * 1024


def validate_resume_file(upload):
    if not upload:
        return
    extension = (upload.name or "").lower()
    if not any(extension.endswith(ext) for ext in ALLOWED_RESUME_EXTENSIONS):
        raise ValidationError("Upload a PDF, DOC, or DOCX file.")
    if upload.size > MAX_RESUME_SIZE:
        raise ValidationError("Resume must be 5MB or smaller.")


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter your email"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter your password"})
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise ValidationError("Invalid email or password.")
            if not self.user_cache.is_active:
                raise ValidationError("This account is inactive.")
            if not self.user_cache.is_email_verified:
                raise ValidationError("Please verify your email before logging in.")
        return cleaned_data

    def get_user(self):
        return self.user_cache


class StudentRegisterStepOneForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Last name"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email address"})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Create password"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password"})
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        return cleaned_data


class StudentRegisterProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["university", "degree", "major", "graduation_year", "city", "linkedin_url", "bio"]
        widgets = {
            "university": forms.TextInput(attrs={"class": "form-control", "placeholder": "University"}),
            "degree": forms.TextInput(attrs={"class": "form-control", "placeholder": "Degree"}),
            "major": forms.TextInput(attrs={"class": "form-control", "placeholder": "Major"}),
            "graduation_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Graduation year"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}),
            "linkedin_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "LinkedIn URL"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Tell us about yourself"}),
        }

    def clean_graduation_year(self):
        year = self.cleaned_data.get("graduation_year")
        if year is None:
            return year
        if year < 2000 or year > CURRENT_YEAR + 10:
            raise ValidationError("Enter a valid graduation year.")
        return year


class StudentRegisterSkillsForm(forms.Form):
    skills_json = forms.CharField(widget=forms.HiddenInput())
    resume = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
        validators=[validate_resume_file],
    )

    def clean_skills_json(self):
        raw = self.cleaned_data.get("skills_json", "[]")
        try:
            skills = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError("Invalid skills payload.") from exc
        if not isinstance(skills, list):
            raise ValidationError("Skills must be a list.")
        cleaned = []
        seen = set()
        for item in skills:
            value = str(item).strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            cleaned.append(value)
            seen.add(key)
        if not cleaned:
            raise ValidationError("Add at least one skill.")
        return cleaned


class CompanyRegisterStepOneForm(forms.Form):
    company_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Company name"}),
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Last name"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Work email"})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Create password"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password"})
    )
    terms = forms.BooleanField(required=True)

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") and cleaned_data.get("password2"):
            if cleaned_data["password1"] != cleaned_data["password2"]:
                raise ValidationError("Passwords do not match.")
        return cleaned_data


class CompanyRegisterProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ["industry", "city", "website", "description"]
        widgets = {
            "industry": forms.TextInput(attrs={"class": "form-control", "placeholder": "Industry"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}),
            "website": forms.URLInput(attrs={"class": "form-control", "placeholder": "Website"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Company description"}),
        }


class OTPVerificationForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control otp-input",
                "placeholder": "Enter 6-digit code",
                "inputmode": "numeric",
                "maxlength": "6",
                "autocomplete": "one-time-code",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise ValidationError("OTP must contain only digits.")
        return code


class ForgotPasswordForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter your email"})
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "New password"})
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm new password"})
    )
