from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.navigation import safe_next

from .focus import period_start
from .models import Task, TaskFocus


@login_required
@require_POST
def set_task_focus(request, pk: int, scope: str):
    """Choisit la tâche qui fait foi pour la période courante."""
    if scope not in TaskFocus.Scope.values:
        raise Http404
    task = get_object_or_404(Task, owner=request.user, pk=pk)
    if task.status == Task.Status.DONE:
        messages.error(request, "Une tâche terminée ne peut pas devenir votre priorité.")
        return redirect(safe_next(request, reverse("planner:tasks")))

    TaskFocus.objects.update_or_create(
        owner=request.user,
        scope=scope,
        period_start=period_start(scope),
        defaults={"task": task},
    )
    messages.success(request, f"{dict(TaskFocus.Scope.choices)[scope]} : {task.title}.")
    return redirect(safe_next(request, reverse("planner:tasks")))


@login_required
@require_POST
def clear_task_focus(request, scope: str):
    """Retire le cap de la période courante, sans effacer l'historique antérieur."""
    if scope not in TaskFocus.Scope.values:
        raise Http404
    TaskFocus.objects.filter(
        owner=request.user,
        scope=scope,
        period_start=period_start(scope),
    ).delete()
    messages.success(request, f"{dict(TaskFocus.Scope.choices)[scope]} : priorité retirée.")
    return redirect(safe_next(request, reverse("planner:tasks")))
