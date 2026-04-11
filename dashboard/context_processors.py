from __future__ import annotations


def dashboard_shell(request):
    unread_notifications = 0
    if request.user.is_authenticated:
        try:
            unread_notifications = request.user.notifications.filter(is_read=False).count()
        except Exception:
            unread_notifications = 0

    return {
        "dashboard_app_name": "SkillMatch",
        "dashboard_unread_notifications": unread_notifications,
        "student_nav_links": [
            {"label": "Overview", "url_name": "dashboard:overview"},
            {"label": "Internships", "url_name": "dashboard:internships"},
            {"label": "Applications", "url_name": "dashboard:applications"},
            {"label": "Interviews", "url_name": "dashboard:interviews"},
            {"label": "Profile", "url_name": "dashboard:profile"},
        ],
    }
