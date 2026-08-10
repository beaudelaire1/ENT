from __future__ import annotations


def shell_context(request):
    if not request.user.is_authenticated:
        return {"appearance": None, "unread_notifications": 0}
    from accounts.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    try:
        unread = request.user.notifications.filter(read_at__isnull=True).count()
    except Exception:
        unread = 0
    return {"appearance": profile, "unread_notifications": unread}
