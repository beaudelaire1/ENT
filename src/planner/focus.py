from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from .models import TaskFocus


ORDERED_SCOPES = (TaskFocus.Scope.DAY, TaskFocus.Scope.WEEK, TaskFocus.Scope.MONTH)


def period_start(scope: str, day: date | None = None) -> date:
    """Début canonique de la période contenant ``day``.

    La semaine commence le lundi, conformément aux vues agenda. Utiliser une date locale
    évite qu'un changement de priorité près de minuit bascule dans la mauvaise journée.
    """
    day = day or timezone.localdate()
    if scope == TaskFocus.Scope.DAY:
        return day
    if scope == TaskFocus.Scope.WEEK:
        return day - timedelta(days=day.weekday())
    if scope == TaskFocus.Scope.MONTH:
        return day.replace(day=1)
    raise ValueError(f"horizon de priorité inconnu : {scope!r}")


def current_focus_rows(owner, day: date | None = None):
    """Les trois caps actuels, dans un ordre stable pour l'interface."""
    day = day or timezone.localdate()
    starts = {scope: period_start(scope, day) for scope in ORDERED_SCOPES}
    selections = {
        selection.scope: selection
        for selection in TaskFocus.objects.filter(
            owner=owner,
            period_start__in=set(starts.values()),
        )
        .exclude(task__status="done")
        .select_related("task")
        if selection.period_start == starts.get(selection.scope)
    }
    labels = dict(TaskFocus.Scope.choices)
    return [
        {
            "scope": scope,
            "label": labels[scope],
            "period_start": starts[scope],
            "selection": selections.get(scope),
            "task": selections[scope].task if scope in selections else None,
        }
        for scope in ORDERED_SCOPES
    ]
