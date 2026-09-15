"""Les tâches ouvertes, rangées par échéance dans le fuseau du compte.

L'accueil triait huit tâches d'abord par priorité : une échéance du soir pouvait disparaître
derrière des tâches importantes à rendre dans un mois. Ici l'échéance range, la priorité
départage : ce qui est en retard, puis ce qui tombe aujourd'hui, puis la semaine qui
vient, et enfin ce qui n'a pas de date.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from .calendar import day_bounds
from .continuity import RESOURCE_PREFETCH
from .models import Task

# Assez pour voir d'un coup d'œil ce qui presse, trop peu pour transformer l'accueil en liste.
GROUP_LIMIT = 6
UPCOMING_DAYS = 7


def task_agenda(owner, day=None) -> list[dict]:
    """Quatre groupes de tâches non terminées, chacun borné, avec le nombre de tâches masquées."""
    day = day or timezone.localdate()
    start, end = day_bounds(day)
    horizon, _ = day_bounds(day + timedelta(days=UPCOMING_DAYS))
    open_tasks = (
        Task.objects.filter(owner=owner)
        .exclude(status=Task.Status.DONE)
        .select_related("competency")
        .prefetch_related(*RESOURCE_PREFETCH)
    )
    by_due = ("due_at", "priority", "title")
    selections = [
        ("overdue", "En retard", open_tasks.filter(due_at__lt=start).order_by(*by_due)),
        ("today", "Aujourd’hui", open_tasks.filter(due_at__gte=start, due_at__lt=end).order_by(*by_due)),
        (
            "upcoming",
            f"Les {UPCOMING_DAYS} prochains jours",
            open_tasks.filter(due_at__gte=end, due_at__lt=horizon).order_by(*by_due),
        ),
        ("undated", "Sans échéance", open_tasks.filter(due_at__isnull=True).order_by("priority", "-created_at")),
    ]
    groups = []
    for key, label, queryset in selections:
        total = queryset.count()
        groups.append(
            {"key": key, "label": label, "tasks": list(queryset[:GROUP_LIMIT]), "more": max(0, total - GROUP_LIMIT)}
        )
    return groups
