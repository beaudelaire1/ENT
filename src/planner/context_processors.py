"""Données du planning visibles depuis toutes les pages."""


def undo(request):
    """L'action sur une tâche encore annulable, affichée à côté des messages."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not hasattr(request, "session"):
        return {}
    from .undo import pending

    data = pending(request)
    return {"planner_undo": data} if data else {}
