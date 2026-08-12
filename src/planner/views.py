from __future__ import annotations

from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
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
    from formations.models import LearningPath

    view = request.GET.get("view", "month")
    selected_path = LearningPath.objects.filter(owner=request.user, pk=request.GET.get("path")).first()
    events = CalendarEvent.objects.filter(owner=request.user).select_related(
        "unit__period__path", "competency__path", "assessment"
    )
    tasks = (
        Task.objects.filter(owner=request.user)
        .exclude(status=Task.Status.DONE)
        .select_related("unit__period__path", "competency__path", "assessment", "series")
    )
    if selected_path:
        academic_scope = (
            Q(unit__period__path=selected_path)
            | Q(competency__path=selected_path)
            | Q(assessment__unit__period__path=selected_path)
            | Q(assessment__period__path=selected_path)
        )
        events = events.filter(academic_scope).distinct()
        tasks = tasks.filter(academic_scope).distinct()

    if view == "week":
        try:
            chosen = datetime.strptime(request.GET.get("date", ""), "%Y-%m-%d").date()
        except ValueError:
            chosen = timezone.localdate()
        week_start = chosen - timedelta(days=chosen.weekday())
        week_end = week_start + timedelta(days=7)
        start = timezone.make_aware(datetime.combine(week_start, time.min))
        end = timezone.make_aware(datetime.combine(week_end, time.min))
        events = list(events.filter(starts_at__lt=end, ends_at__gte=start).order_by("starts_at"))
        tasks = list(tasks.filter(due_at__gte=start, due_at__lt=end).order_by("due_at"))
        days = [
            {
                "date": week_start + timedelta(days=offset),
                "events": [event for event in events if event.starts_at.date() == week_start + timedelta(days=offset)],
                "tasks": [task for task in tasks if task.due_at.date() == week_start + timedelta(days=offset)],
            }
            for offset in range(7)
        ]
        return render(
            request,
            "planner/agenda.html",
            {
                "view": "week",
                "week_start": week_start,
                "week_end": week_end - timedelta(days=1),
                "previous_week": week_start - timedelta(days=7),
                "next_week": week_start + timedelta(days=7),
                "is_current_week": week_start <= timezone.localdate() < week_end,
                "today": timezone.localdate(),
                "days": days,
                "formations": LearningPath.objects.filter(owner=request.user),
                "selected_path": selected_path,
                "breadcrumbs": [crumb("Agenda")],
            },
        )

    try:
        anchor = datetime.strptime(request.GET.get("month", ""), "%Y-%m").date().replace(day=1)
    except ValueError:
        anchor = timezone.localdate().replace(day=1)
    next_month = (anchor.replace(day=28) + timedelta(days=4)).replace(day=1)
    previous_month = (anchor - timedelta(days=1)).replace(day=1)
    start = timezone.make_aware(datetime.combine(anchor, time.min))
    end = timezone.make_aware(datetime.combine(next_month, time.min))
    events = events.filter(starts_at__lt=end, ends_at__gte=start)
    tasks = tasks.filter(due_at__gte=start, due_at__lt=end)
    return render(
        request,
        "planner/agenda.html",
        {
            "anchor": anchor,
            "view": "month",
            "previous_month": previous_month,
            "next_month": next_month,
            "is_current_month": anchor == timezone.localdate().replace(day=1),
            "events": events,
            "tasks": tasks,
            "formations": LearningPath.objects.filter(owner=request.user),
            "selected_path": selected_path,
            "breadcrumbs": [crumb("Agenda")],
        },
    )


@login_required
def task_list(request):
    from formations.models import LearningPath

    tasks = Task.objects.filter(owner=request.user).select_related("series", "unit__period__path", "competency")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    selected_path = LearningPath.objects.filter(owner=request.user, pk=request.GET.get("path")).first()
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if status in Task.Status.values:
        tasks = tasks.filter(status=status)
    if selected_path:
        tasks = tasks.filter(
            Q(unit__period__path=selected_path)
            | Q(competency__path=selected_path)
            | Q(assessment__unit__period__path=selected_path)
            | Q(assessment__period__path=selected_path)
        ).distinct()
    return render(
        request,
        "planner/tasks.html",
        {
            "tasks": tasks,
            "query": query,
            "status": status,
            "statuses": Task.Status.choices,
            "formations": LearningPath.objects.filter(owner=request.user),
            "selected_path": selected_path,
            "breadcrumbs": [crumb("Tâches")],
        },
    )


@login_required
def task_edit(request, pk=None):
    task = get_object_or_404(Task, owner=request.user, pk=pk) if pk else None
    form = TaskForm(request.POST or None, instance=task, user=request.user, scope={"owner": request.user})
    if request.method == "POST" and form.is_valid():
        task = form.save()
        sync_task_reminder(task)
        rule, until = form.recurrence
        created = expand_task_series(task, rule, until)
        repeated_tasks = task.series.tasks.exclude(pk=task.pk) if task.series_id else Task.objects.none()
        for repeated in repeated_tasks:
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
    target_status = Task.Status.TODO if task.status == Task.Status.DONE else Task.Status.DONE
    targets = task.series.tasks.all() if request.POST.get("scope") == "series" and task.series_id else [task]
    for target in targets:
        target.status = target_status
        target.save(update_fields=["status", "updated_at"])
        sync_task_reminder(target)
    return redirect(request.POST.get("next") or "planner:tasks")


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, owner=request.user, pk=pk)
    return confirm_delete(request, task, redirect_to=reverse("planner:tasks"), title="Supprimer cette tâche")


@login_required
def task_series_delete(request, pk):
    task = get_object_or_404(Task.objects.select_related("series"), owner=request.user, pk=pk, series__isnull=False)
    series = task.series
    count = series.tasks.count()
    if request.method == "POST":
        series.delete()
        messages.success(request, f"La série et ses {count} tâche(s) ont été supprimées.")
        return redirect("planner:tasks")
    return render(
        request,
        "planner/series_delete.html",
        {"kind": "tâches", "title": task.title, "count": count, "back_to": reverse("planner:tasks")},
    )


@login_required
def event_delete(request, pk):
    event = get_object_or_404(CalendarEvent, owner=request.user, pk=pk)
    return confirm_delete(request, event, redirect_to=reverse("planner:agenda"), title="Supprimer cet événement")


@login_required
def event_series_delete(request, pk):
    event = get_object_or_404(CalendarEvent, owner=request.user, pk=pk)
    head = event.series or event
    count = 1 + head.occurrences.count()
    if count == 1:
        return redirect("planner:event_delete", pk=event.pk)
    if request.method == "POST":
        head.delete()
        messages.success(request, f"La série et ses {count} événement(s) ont été supprimés.")
        return redirect("planner:agenda")
    return render(
        request,
        "planner/series_delete.html",
        {"kind": "événements", "title": head.title, "count": count, "back_to": reverse("planner:agenda")},
    )


@login_required
def event_edit(request, pk=None):
    event = get_object_or_404(CalendarEvent, owner=request.user, pk=pk) if pk else None
    form = CalendarEventForm(request.POST or None, instance=event, user=request.user, scope={"owner": request.user})
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
