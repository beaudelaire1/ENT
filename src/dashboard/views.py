from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_POST

from .models import DashboardWidget
from .services import ensure_default_widgets


@login_required
def home(request):
    from formations.academics import period_average
    from formations.models import Assessment, LearningPath, ProgressRecord, UnitCompetency
    from formations.progression import weighted_progress
    from formations.revision import to_revisit
    from library.models import LibraryItem
    from notifications.models import Notification
    from planner.calendar import day_bounds, events_in_window
    from planner.focus import current_focus_rows
    from planner.models import CalendarEvent, Task

    widgets = ensure_default_widgets(request.user)
    now = timezone.now()
    today = timezone.localdate()
    day_start, day_end = day_bounds(today)
    formations = LearningPath.objects.filter(owner=request.user).select_related("current_period").order_by("title")
    current_path = formations.filter(status=LearningPath.Status.ACTIVE, current_period__isnull=False).first()
    academic = None
    if current_path:
        period = current_path.current_period
        competency_ids = list(
            current_path.competencies.filter(Q(period=period) | Q(units__period=period))
            .distinct()
            .values_list("pk", flat=True)
        )
        records = list(
            ProgressRecord.objects.filter(owner=request.user, competency_id__in=competency_ids).select_related(
                "competency"
            )
        )
        acquired = sum(record.confirmed_level >= ProgressRecord.Mastery.ACQUIRED for record in records)
        # Une compétence principale dans une matière pèse le double d'une compétence
        # seulement rappelée ailleurs, et le niveau entre pour ce qu'il vaut plutôt qu'en
        # tout ou rien : voir `formations.progression.weighted_progress`.
        primary_ids = set(
            UnitCompetency.objects.filter(is_primary=True, competency_id__in=competency_ids).values_list(
                "competency_id", flat=True
            )
        )
        academic = {
            "path": current_path,
            "period": period,
            "average": period_average(request.user, period),
            "competencies": len(competency_ids),
            "acquired": acquired,
            "progress_percent": weighted_progress(records, primary_ids, competency_ids=competency_ids),
            "suggested": sum(record.is_suggested for record in records),
            # Ce qui appelle un retour — objectif dépassé, évaluation proche, niveau
            # ancien — et sa raison. Une liste que l'on consulte, jamais une notification
            # qui interrompt.
            "to_revisit": to_revisit(request.user, current_path, period),
            "assessments": Assessment.objects.filter(
                owner=request.user,
                status=Assessment.Status.PLANNED,
                scheduled_for__gte=now,
            )
            .filter(Q(period=period) | Q(unit__period=period))
            .select_related("unit")
            .order_by("scheduled_for")[:4],
        }
    context = {
        "widgets": widgets,
        "events_today": events_in_window(CalendarEvent.objects.filter(owner=request.user), day_start, day_end).order_by(
            "starts_at"
        )[:8],
        "tasks": Task.objects.filter(owner=request.user)
        .exclude(status=Task.Status.DONE)
        .order_by("priority", "due_at")[:8],
        "task_focuses": current_focus_rows(request.user, today),
        "notifications": Notification.objects.filter(owner=request.user, read_at__isnull=True)[:6],
        "recent_items": LibraryItem.objects.filter(owner=request.user).order_by("-updated_at")[:6],
        "formations": formations[:6],
        "academic": academic,
        "now": now,
    }
    return render(request, "dashboard/home.html", context)


@login_required
@require_POST
def save_layout(request):
    try:
        payload = json.loads(request.body)
        widgets = payload["widgets"]
        if not isinstance(widgets, list) or len(widgets) > len(DashboardWidget.Kind.values):
            raise ValueError
        kinds = set()
        for data in widgets:
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("kind"), str)
                or data["kind"] not in DashboardWidget.Kind.values
                or data["kind"] in kinds
                or type(data.get("visible", True)) is not bool
            ):
                raise ValueError
            kinds.add(data["kind"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return JsonResponse({"error": "Disposition invalide."}, status=400)
    with transaction.atomic():
        for position, data in enumerate(widgets):
            DashboardWidget.objects.update_or_create(
                owner=request.user,
                kind=data["kind"],
                defaults={"position": position, "visible": data.get("visible", True)},
            )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def quick_note(request):
    from library.models import LibraryItem

    text = request.POST.get("text", "").strip()
    if text:
        LibraryItem.objects.create(
            owner=request.user,
            kind=LibraryItem.Kind.NOTE,
            title=text[:70],
            note_text=text,
            note_delta={"ops": [{"insert": text + "\n"}]},
            note_html=f"<p>{escape(text)}</p>",
        )
        messages.success(request, "Note ajoutée à la bibliothèque.")
    return redirect("dashboard:home")
