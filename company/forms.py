from django import forms
from accounts.models import CompanyProfile
from .models import Internship, Application, Interview


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%dT%H:%M")
        super().__init__(**kwargs)


class InternshipForm(forms.ModelForm):
    required_skills_input = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Comma-separated skills, set by JS tag input",
    )

    class Meta:
        model = Internship
        fields = [
            "title", "department", "description",
            "work_type", "duration", "stipend",
            "deadline", "status", "required_score_threshold",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Backend Developer Intern"}),
            "department": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Engineering"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "work_type": forms.Select(attrs={"class": "form-select"}),
            "duration": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 3 months"}),
            "stipend": forms.NumberInput(attrs={"class": "form-control", "placeholder": "15000"}),
            "deadline": DateInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "required_score_threshold": forms.NumberInput(attrs={
                "class": "form-control", "min": 0, "max": 100, "placeholder": "0 = no minimum"
            }),
        }

    def __init__(self, *args, company_user=None, **kwargs):
        self.company_user = company_user
        super().__init__(*args, **kwargs)
        self.fields["stipend"].required = False
        self.fields["deadline"].required = False
        # Pre-populate hidden field from existing instance
        if self.instance and self.instance.pk and self.instance.required_skills:
            import json
            self.fields["required_skills_input"].initial = json.dumps(
                self.instance.required_skills
            )

    def clean(self):
        cleaned = super().clean()
        import json
        raw = cleaned.get("required_skills_input", "[]") or "[]"
        try:
            skills = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            skills = []
        cleaned["required_skills_parsed"] = [s.strip() for s in skills if s.strip()]
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.required_skills = self.cleaned_data.get("required_skills_parsed", [])
        if commit:
            instance.save()
        return instance


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ["company_name", "industry", "website", "city", "description", "logo"]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "industry": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class ScheduleInterviewForm(forms.ModelForm):
    auto_create_google_meet = forms.BooleanField(
        required=False,
        initial=True,
        label="Auto-create Google Meet link"
    )

    class Meta:
        model = Interview
        fields = ["application", "interview_date", "interview_type", "meeting_link", "location", "notes"]
        widgets = {
            "application": forms.Select(attrs={"class": "form-select"}),
            "interview_date": DateTimeInput(attrs={"class": "form-control"}),
            "interview_type": forms.Select(attrs={"class": "form-select", "id": "id_interview_type"}),
            "meeting_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://meet.google.com/..."}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "Office address"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, company_user=None, selected_app=None, **kwargs):
        self.company_user = company_user
        super().__init__(*args, **kwargs)
        self.fields["meeting_link"].required = False
        self.fields["location"].required = False
        self.fields["notes"].required = False
        self.fields["auto_create_google_meet"].widget.attrs.update({"class": "form-check-input"})

        if company_user:
            eligible = Application.objects.filter(
                internship__company=company_user,
            ).exclude(
                status__in=["rejected"]
            ).filter(
                # Only show apps that don't already have an interview
                interview__isnull=True
            ).select_related("applicant", "internship")
            self.fields["application"].queryset = eligible
            self.fields["application"].label_from_instance = (
                lambda obj: f"{obj.applicant.get_full_name()} — {obj.internship.title}"
            )

        if selected_app:
            self.fields["application"].initial = selected_app
            self.fields["application"].widget.attrs["disabled"] = "disabled"

        has_google = bool(getattr(getattr(company_user, "company_profile", None), "has_google_connected", False))
        if not has_google:
            self.fields["auto_create_google_meet"].initial = False
            self.fields["auto_create_google_meet"].help_text = "Connect company Google Calendar to auto-generate Meet links."

    def clean(self):
        cleaned = super().clean()
        itype = cleaned.get("interview_type")
        auto_google = cleaned.get("auto_create_google_meet")
        has_google = bool(getattr(getattr(self.company_user, "company_profile", None), "has_google_connected", False))
        if itype == "video" and auto_google and not has_google:
            self.add_error("auto_create_google_meet", "Connect company Google account first.")
        if itype in ("video", "phone") and not cleaned.get("meeting_link") and not (itype == "video" and auto_google and has_google):
            self.add_error("meeting_link", "Meeting link is required for video/phone interviews.")
        if itype == "onsite" and not cleaned.get("location"):
            self.add_error("location", "Location is required for onsite interviews.")
        return cleaned


class RescheduleInterviewForm(forms.ModelForm):
    """Company uses this to pick a new date/time + update meeting details."""
    auto_create_google_meet = forms.BooleanField(required=False, initial=True, label="Keep Google Meet synced")

    class Meta:
        model   = Interview
        fields  = ["interview_date", "interview_type", "meeting_link", "location", "notes"]
        widgets = {
            "interview_date": DateTimeInput(attrs={"class": "form-control"}),
            "interview_type": forms.Select(attrs={
                "class": "form-select", "id": "id_reschedule_type"
            }),
            "meeting_link": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://meet.google.com/...",
            }),
            "location": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Office address",
            }),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, company_user=None, **kwargs):
        self.company_user = company_user
        super().__init__(*args, **kwargs)
        self.fields["meeting_link"].required = False
        self.fields["location"].required     = False
        self.fields["notes"].required        = False
        self.fields["auto_create_google_meet"].widget.attrs.update({"class": "form-check-input"})
        if self.instance and getattr(self.instance, "google_event_id", ""):
            self.fields["auto_create_google_meet"].initial = True

    def clean(self):
        cleaned = super().clean()
        itype   = cleaned.get("interview_type")
        auto_google = cleaned.get("auto_create_google_meet")
        has_google = bool(getattr(getattr(self.company_user, "company_profile", None), "has_google_connected", False))
        if itype == "video" and auto_google and not has_google:
            self.add_error("auto_create_google_meet", "Connect company Google account first.")
        if itype in ("video", "phone") and not cleaned.get("meeting_link") and not (itype == "video" and auto_google and has_google):
            self.add_error(
                "meeting_link",
                "Meeting link is required for video/phone interviews."
            )
        if itype == "onsite" and not cleaned.get("location"):
            self.add_error("location", "Location is required for onsite interviews.")
        return cleaned