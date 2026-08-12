from __future__ import annotations

from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.deletion import confirm_delete
from core.navigation import crumb, safe_next

from .forms import CalendarEventForm, TaskForm
from .models import CalendarEvent, Task
from .services import expand_event_series, expand_task_series, sync_event_reminder, sync_task_reminder


@login_required
def agenda(request):
    try:
        anchor = datetime.strptime(request.GET.get("month", ""), "%Y-%m").date().replace(day=1)
    except ValueError:
        anchor = timezone.localdate().replace(day=1)
    next_month = (anchor.replace(day=28) + timedelta(days=4)).replace(day=1)
    previous_month = (anchor - timedelta(days=1)).replace(day=1)
    start = timezone.make_aware(datetime.combine(anchor, time.min))
    end = timezone.make_aware(datetime.combine(next_month, time.min))
    events = CalendarEvent.objects.filter(owner=request.user, starts_at__lt=end, ends_at__gte=start)
    tasks = Task.objects.filter(owner=request.user, due_at__gte=start, due_at__lt=end).exclude(status=Task.Status.DONE)
    return render(
        request,
        "planner/agenda.html",
        {
            "anchor": anchor,
            "previous_month": previous_month,
            "next_month": next_month,
            "is_current_month": anchor == timezone.localdate().replace(day=1),
            "events": events,
            "tasks": tasks,
            "breadcrumbs": [crumb("Agenda")],
        },
    )


@login_required
def task_list(request):
    tasks = Task.objects.filter(owner=request.user)
    return render(request, "planner/tasks.html", {"tasks": tasks, "breadcrumbs": [crumb("Tâches")]})


@login_required
def task_edit(request, pk=None):
    task = get_object_or_404(Task, owner=request.user, pk=pk) if pk else None
    form = TaskForm(request.POST or None, instance=task, scope={"owner": request.user})
    if request.method == "POST" and form.is_valid():
        task = form.save()
        sync_task_reminder(task)
        rule, until = form.recurrence
        created = expand_task_series(task, rule, until)
        for repeated in Task.objects.filter(owner=request.user, title=task.title).exclude(pk=task.pk):
            sync_task_reminder(repeated)
        if created:
            messages.success(request, f"Tâche enregistrée, avec {created} répétition{'s' if created > 1 else ''}.")
        else:
            messages.success(request, "Tâche enregistrée.")
        return redirect(safe_next(request, reverse("planner:tasks")))
    title = "Modifier la tâche" if task else "Nouvelle tâche"
    return render(
        request,
        "planner/form.html",
        {
            "form": form,
            "title": title,
            "eyebrow": "TÂCHES",
            "breadcrumbs": [crumb("Tâches", reverse("planner:tasks")), crumb(task.title if task else title)],
            "back_to": safe_next(request, reverse("planner:tasks")),
            "delete_url": reverse("planner:task_delete", args=[task.pk]) if task else None,
            "delete_label": "cette tâche",
        },
    )


@login_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task, owner=request.user, pk=pk)
    task.status = Task.Status.TODO if task.status == Task.Status.DONE else Task.Status.DONE
    task.save(update_fields=["status", "updated_at"])
    sync_task_reminder(task)
    return redirect(request.POST.get("next") or "planner:tasks")


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, owner=request.user, pk=pk)
    return confirm_delete(request, task, redirect_to=reverse("planner:tasks"), title="Supprimer cette tâche")


@login_required
def event_delete(request, pk):
    event = get_object_or_404(CalendarEvent, owner=request.user, pk=pk)
    return confirm_delete(request, event, redirect_to=reverse("planner:agenda"), title="Supprimer cet événement")


@login_required
def event_edit(request, pk=None):
    event = get_object_or_404(CalendarEvent, owner=request.user, pk=pk) if pk else None
    form = CalendarEventForm(request.POST or None, instance=event, scope={"owner": request.user})
    if request.method == "POST" and form.is_valid():
        event = form.save()
        sync_event_reminder(event)
        rule, until = form.recurrence
        created = expand_event_series(event, rule, until)
        for occurrence in event.occurrences.all():
            sync_event_reminder(occurrence)
        if created:
            messages.success(request, f"Événement enregistré, avec {created} séance{'s' if created > 1 else ''}.")
        else:
            messages.success(request, "Événement enregistré.")
        return redirect(safe_next(request, reverse("planner:agenda")))
    title = "Modifier l’événement" if event else "Nouvel événement"
    return render(
        request,
        "planner/form.html",
        {
            "form": form,
            "title": title,
            "eyebrow": "AGENDA",
            "breadcrumbs": [crumb("Agenda", reverse("planner:agenda")), crumb(event.title if event else title)],
            "back_to": safe_next(request, reverse("planner:agenda")),
            "delete_url": reverse("planner:event_delete", args=[event.pk]) if event else None,
            "delete_label": "cet événement",
        },
    )
