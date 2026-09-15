"""Annuler la dernière action sur une tâche : la terminer ou la reporter.

Un clic sur « Terminer » à côté du mauvais intitulé ne doit pas coûter une recherche dans
la liste des tâches terminées. L'état d'avant est gardé dans la session, pour une seule
action — la suivante le remplace — et pour dix minutes : au-delà, « Annuler » ne dirait
plus clairement sur quoi il revient.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Task
from .services import sync_task_reminder

SESSION_KEY = "planner_undo"
LIFETIME = timedelta(minutes=10)


def _stamp(moment):
    return moment.isoformat() if moment else None


def remember(request, task: Task, label: str) -> None:
    """Retient l'état actuel de ``task``, avant qu'une action ne le modifie."""
    request.session[SESSION_KEY] = {
        "task": task.pk,
        "status": task.status,
        "due_at": _stamp(task.due_at),
        "reminder_at": _stamp(task.reminder_at),
        "label": label,
        "expires": _stamp(timezone.now() + LIFETIME),
    }


def forget(request) -> None:
    request.session.pop(SESSION_KEY, None)


def pending(request) -> dict | None:
    """L'action annulable, si elle n'a pas expiré."""
    data = request.session.get(SESSION_KEY)
    if not data:
        return None
    expires = parse_datetime(data.get("expires") or "")
    if not expires or expires <= timezone.now():
        forget(request)
        return None
    return data


def restore(request) -> Task | None:
    """Rétablit l'état retenu et vide l'emplacement. ``None`` s'il n'y a rien à annuler.

    La tâche est relue par propriétaire : une session ne peut rien rétablir sur la tâche
    d'un autre compte, quelle que soit la valeur qu'elle contient.
    """
    data = pending(request)
    forget(request)
    if not data:
        return None
    task = Task.objects.filter(owner=request.user, pk=data["task"]).first()
    if task is None:
        return None
    task.status = data["status"]
    task.due_at = parse_datetime(data["due_at"]) if data["due_at"] else None
    task.reminder_at = parse_datetime(data["reminder_at"]) if data["reminder_at"] else None
    task.save(update_fields=["status", "due_at", "reminder_at", "updated_at"])
    sync_task_reminder(task)
    return task
