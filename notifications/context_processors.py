def unread_notifications(request):
    count = 0
    if request.user.is_authenticated:
        try:
            count = request.user.notifications.filter(is_read=False).count()
        except Exception:
            count = 0
    return {"unread_notifications_count": count}
