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


NAV_PATH_LIMIT = 6


def nav_formations(request) -> tuple[list, int, int | None]:
    """Les formations listées sous la rubrique Formations du volet.

    Une formation est une destination fréquente : la nommer dans le volet évite de
    repasser par la liste à chaque fois. Le nombre est borné pour que le volet reste
    court, et le dépassement est annoncé au lieu d'être tronqué en silence.
    """
    from formations.models import LearningPath

    owned = LearningPath.objects.filter(owner=request.user).order_by("title")
    paths = list(owned[:NAV_PATH_LIMIT])
    # Le nombre restant est compté pour de vrai : annoncer « et 1 autre » là où il y en a
    # trois est pire que ne rien annoncer.
    overflow = max(0, owned.count() - NAV_PATH_LIMIT) if len(paths) == NAV_PATH_LIMIT else 0
    match = getattr(request, "resolver_match", None)
    current = None
    if match and match.app_name == "formations":
        # Seules les vues portant directement l'identifiant du parcours le désignent.
        if match.url_name in {"detail", "tracking", "edit"}:
            current = match.kwargs.get("pk")
        else:
            current = match.kwargs.get("path_pk")
    return paths, overflow, current


def shell_context(request):
    if not request.user.is_authenticated:
        return {
            "appearance": None,
            "unread_notifications": 0,
            "nav_section": "",
            "nav_paths": [],
            "nav_paths_overflow": 0,
            "nav_path_id": None,
        }
    from accounts.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    try:
        unread = request.user.notifications.filter(read_at__isnull=True).count()
    except Exception:
        unread = 0
    paths, overflow, current = nav_formations(request)
    return {
        "appearance": profile,
        "unread_notifications": unread,
        "nav_section": nav_section(request),
        "nav_paths": paths,
        "nav_paths_overflow": overflow,
        "nav_path_id": current,
    }
