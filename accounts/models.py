from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _generate_username(self, email: str) -> str:
        base = slugify(email.split("@")[0]) or "user"
        candidate = base
        counter = 1
        while self.model.objects.filter(username=candidate).exists():
            candidate = f"{base}{counter}"
            counter += 1
        return candidate

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", self._generate_username(email))
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "company")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        COMPANY = "company", "Company"

    username = models.CharField(max_length=150, unique=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    university = models.CharField(max_length=255, blank=True)
    degree = models.CharField(max_length=255, blank=True)
    major = models.CharField(max_length=255, blank=True)
    graduation_year = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    city = models.CharField(max_length=120, blank=True)
    linkedin_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    resume = models.FileField(upload_to="resumes/", blank=True, null=True)
    profile_views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"StudentProfile<{self.user.email}>"


class CompanyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company_profile")
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)

    google_email = models.EmailField(blank=True, null=True)
    google_access_token = models.TextField(blank=True, null=True)
    google_refresh_token = models.TextField(blank=True, null=True)
    google_token_uri = models.URLField(blank=True, null=True, default="https://oauth2.googleapis.com/token")
    google_scopes = models.TextField(blank=True, null=True)
    google_account_connected_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

    @property
    def has_google_connected(self):
        return bool(self.google_refresh_token or self.google_access_token)
