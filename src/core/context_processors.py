from __future__ import annotations


def nav_section(request) -> str:
    """La rubrique du volet latéral à marquer comme active.

    Le volet ne portait aucun repère : rien ne disait dans quelle rubrique on se trouvait,
    et deux entrées — Agenda et Tâches — partagent la même application. La rubrique se
    déduit donc de l'URL résolue plutôt que d'être passée par chaque vue, sans quoi il
    suffirait d'en oublier une pour que le repère disparaisse.
    """
    match = getattr(request, "resolver_match", None)
    if match is None:
        return ""
    app = match.app_name or ""
    if app == "planner":
        return "tasks" if (match.url_name or "").startswith("task") else "agenda"
    if app == "accounts":
        return "settings"
    return app


def shell_context(request):
    if not request.user.is_authenticated:
        return {"appearance": None, "unread_notifications": 0, "nav_section": ""}
    from accounts.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    try:
        unread = request.user.notifications.filter(read_at__isnull=True).count()
    except Exception:
        unread = 0
    return {"appearance": profile, "unread_notifications": unread, "nav_section": nav_section(request)}
