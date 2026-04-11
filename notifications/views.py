from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from .models import Notification


@login_required
def notification_count(request):
    """Returns unread count — polled every 30s by the bell."""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"count": count})


@login_required
def notification_list(request):
    """Returns latest 30 notifications as JSON for the dropdown."""
    notifs = request.user.notifications.all()[:30]
    data = [{
        "id":         n.pk,
        "type":       n.notif_type,
        "title":      n.title,
        "body":       n.body,
        "is_read":    n.is_read,
        "created_at": n.created_at.strftime("%b %d, %I:%M %p"),
        "icon":       _icon(n.notif_type),
    } for n in notifs]
    return JsonResponse({"notifications": data})


@login_required
@require_POST
def mark_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})


def _icon(notif_type):
    return {
        "otp":                          "🔐",
        "interview_scheduled":          "📅",
        "interview_accepted":           "✅",
        "interview_reschedule_requested":"🔄",
        "interview_cancelled":          "❌",
        "interview_reminder":           "⏰",
        "application_received":         "📩",
    }.get(notif_type, "🔔")