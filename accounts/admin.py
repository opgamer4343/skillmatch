from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import CompanyProfile, StudentProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = ("email", "first_name", "last_name", "role", "is_email_verified", "is_staff")
    list_filter = ("role", "is_email_verified", "is_staff", "is_superuser", "is_active")
    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name", "username")

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("SkillMatch", {"fields": ("role", "is_email_verified")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("SkillMatch", {"fields": ("email", "role", "is_email_verified")}),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "degree", "major", "graduation_year", "city")
    search_fields = ("user__email", "user__first_name", "user__last_name", "university", "major")


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "user", "industry", "city", "website")
    search_fields = ("company_name", "user__email", "industry", "city")
