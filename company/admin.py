"""
SkillMatch Admin — Company Review Moderation
Safe version — works whether or not migration 0003 has run.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import CompanyReview, Internship, Application, Interview


def _has_field(model, field_name):
    """Check if a field exists on the model."""
    return any(f.name == field_name for f in model._meta.get_fields()
               if hasattr(f, 'name'))


# Build dynamic lists based on what fields exist
_EXTRA_FIELDS_EXIST = _has_field(CompanyReview, 'spam_score')


@admin.register(CompanyReview)
class CompanyReviewAdmin(admin.ModelAdmin):

    # ── Base list display (always safe fields) ─────────────────
    list_display = [
        'reviewer_name', 'company_name', 'overall_stars',
        'approval_badge', 'created_at',
    ]

    list_filter = ['is_approved']
    search_fields = [
        'reviewer__email', 'reviewer__first_name',
        'company__email', 'title', 'body',
    ]

    # readonly fields — only safe base fields
    readonly_fields = [
        'reviewer', 'company', 'application',
        'overall_rating', 'process_rating', 'communication_rating',
        'title', 'body_display',
        'created_at',
    ]

    # base fields layout
    fields = [
        'reviewer', 'company', 'application',
        'overall_rating', 'process_rating', 'communication_rating',
        'title', 'body_display',
        'is_anonymous', 'is_approved',
        'created_at',
    ]

    actions = ['approve_reviews', 'reject_reviews']
    ordering = ['-created_at']
    list_per_page = 20

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamically add extra fields if migration has run
        if _EXTRA_FIELDS_EXIST:
            self.list_display = [
                'reviewer_name', 'company_name', 'overall_stars',
                'spam_badge', 'approval_badge', 'recommend_badge', 'created_at',
            ]
            self.list_filter = [
                'is_approved', 'flagged_by_admin', 'would_recommend'
            ]
            self.readonly_fields = [
                'reviewer', 'company', 'application',
                'overall_rating', 'process_rating', 'communication_rating',
                'title', 'body_display', 'interview_experience_display',
                'spam_score', 'spam_flags_display', 'ip_address',
                'created_at',
            ]
            self.fields = [
                'reviewer', 'company', 'application',
                'overall_rating', 'process_rating', 'communication_rating',
                'title', 'body_display', 'interview_experience_display',
                'would_recommend', 'is_anonymous',
                'spam_score', 'spam_flags_display', 'ip_address',
                'is_approved', 'flagged_by_admin', 'admin_note',
                'created_at',
            ]
            self.actions = ['approve_reviews', 'reject_reviews', 'flag_as_spam']
            self.ordering = ['-spam_score', '-created_at']

    # ── Display helpers ────────────────────────────────────────

    def reviewer_name(self, obj):
        name = obj.reviewer.get_full_name() or obj.reviewer.email
        anon = ' <em style="color:#94a3b8">(anon)</em>' \
               if obj.is_anonymous else ''
        return format_html('<strong>{}</strong>{}', name, anon)
    reviewer_name.short_description = 'Reviewer'

    def company_name(self, obj):
        cp = getattr(obj.company, 'company_profile', None)
        return cp.company_name if cp else obj.company.email
    company_name.short_description = 'Company'

    def overall_stars(self, obj):
        stars = '★' * obj.overall_rating + '☆' * (5 - obj.overall_rating)
        color = ('#f59e0b' if obj.overall_rating >= 4
                 else '#64748b' if obj.overall_rating == 3
                 else '#ef4444')
        return format_html(
            '<span style="color:{};font-size:15px;">{}</span> {}/5',
            color, stars, obj.overall_rating
        )
    overall_stars.short_description = 'Rating'

    def approval_badge(self, obj):
        flagged = getattr(obj, 'flagged_by_admin', False)
        if flagged:
            return format_html(
                '<span style="background:#fee2e2;color:#dc2626;'
                'border-radius:4px;padding:2px 8px;font-size:11px;">'
                '🚩 Flagged</span>'
            )
        if obj.is_approved:
            return format_html(
                '<span style="background:#d1fae5;color:#065f46;'
                'border-radius:4px;padding:2px 8px;font-size:11px;">'
                '✅ Published</span>'
            )
        return format_html(
            '<span style="background:#fef3c7;color:#92400e;'
            'border-radius:4px;padding:2px 8px;font-size:11px;">'
            '⏳ Pending</span>'
        )
    approval_badge.short_description = 'Status'

    def spam_badge(self, obj):
        s = getattr(obj, 'spam_score', 0) or 0
        if s >= 85:   c, l = '#dc2626', f'🔴 Spam ({s})'
        elif s >= 60: c, l = '#d97706', f'🟠 Hold ({s})'
        elif s >= 30: c, l = '#ca8a04', f'🟡 Check ({s})'
        else:         c, l = '#16a34a', f'🟢 OK ({s})'
        return format_html(
            '<span style="color:{};font-weight:600;font-size:12px;">{}</span>',
            c, l
        )
    spam_badge.short_description = 'Spam Score'

    def recommend_badge(self, obj):
        rec = getattr(obj, 'would_recommend', True)
        if rec:
            return format_html('<span style="font-size:16px;">👍</span>')
        return format_html('<span style="font-size:16px;">👎</span>')
    recommend_badge.short_description = 'Rec.'

    def body_display(self, obj):
        return format_html(
            '<div style="background:#f8fafc;padding:12px;border-radius:8px;'
            'border-left:4px solid #4f46e5;font-size:14px;'
            'line-height:1.7;max-width:600px;">{}</div>',
            obj.body
        )
    body_display.short_description = 'Review Body'

    def interview_experience_display(self, obj):
        exp = getattr(obj, 'interview_experience', '') or '—'
        return format_html(
            '<div style="background:#f0fdf4;padding:12px;border-radius:8px;'
            'border-left:4px solid #10b981;font-size:14px;'
            'line-height:1.7;max-width:600px;">{}</div>',
            exp
        )
    interview_experience_display.short_description = 'Interview Experience'

    def spam_flags_display(self, obj):
        flags = getattr(obj, 'spam_flags', []) or []
        if not flags:
            return format_html(
                '<span style="color:#64748b;font-size:13px;">'
                'None detected ✓</span>'
            )
        items = ''.join(
            f'<li style="color:#dc2626;margin-bottom:4px;">⚠ {f}</li>'
            for f in flags
        )
        return format_html(
            '<ul style="margin:0;padding-left:18px;font-size:12px;">{}</ul>',
            items
        )
    spam_flags_display.short_description = 'Spam Flags'

    # ── Actions ────────────────────────────────────────────────

    @admin.action(description='✅ Approve and publish selected reviews')
    def approve_reviews(self, request, queryset):
        update = {'is_approved': True}
        if _EXTRA_FIELDS_EXIST:
            update['flagged_by_admin'] = False
        count = queryset.update(**update)
        self.message_user(request, f'{count} review(s) approved and published.')

    @admin.action(description='❌ Reject selected reviews')
    def reject_reviews(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'{count} review(s) rejected.')

    @admin.action(description='🚩 Flag selected as spam')
    def flag_as_spam(self, request, queryset):
        if _EXTRA_FIELDS_EXIST:
            count = queryset.update(flagged_by_admin=True, is_approved=False)
        else:
            count = queryset.update(is_approved=False)
        self.message_user(request, f'{count} review(s) flagged.')


# ── Other models ──────────────────────────────────────────────

@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display  = ['title', 'company_name', 'status', 'work_type', 'created_at']
    list_filter   = ['status', 'work_type']
    search_fields = ['title', 'company__email']
    ordering      = ['-created_at']

    def company_name(self, obj):
        cp = getattr(obj.company, 'company_profile', None)
        return cp.company_name if cp else obj.company.email
    company_name.short_description = 'Company'


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display  = ['applicant_name', 'internship_title', 'status', 'created_at']
    list_filter   = ['status']
    search_fields = ['applicant__email', 'internship__title']
    ordering      = ['-created_at']

    def applicant_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.email
    applicant_name.short_description = 'Applicant'

    def internship_title(self, obj):
        return obj.internship.title
    internship_title.short_description = 'Internship'


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display  = ['candidate', 'internship_title', 'interview_date', 'status']
    list_filter   = ['status', 'interview_type']
    search_fields = [
        'application__applicant__email',
        'application__internship__title',
    ]
    ordering = ['-interview_date']

    def candidate(self, obj):
        return obj.application.applicant.get_full_name() or \
               obj.application.applicant.email
    candidate.short_description = 'Candidate'

    def internship_title(self, obj):
        return obj.application.internship.title
    internship_title.short_description = 'Role'