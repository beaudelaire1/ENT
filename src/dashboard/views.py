from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_POST

from .models import DashboardWidget
from .services import ensure_default_widgets


@login_required
def home(request):
    from formations.models import LearningPath
    from library.models import LibraryItem
    from notifications.models import Notification
    from planner.models import CalendarEvent, Task

    widgets = ensure_default_widgets(request.user)
    now = timezone.now()
    today = timezone.localdate()
    context = {
        "widgets": widgets,
        "events_today": CalendarEvent.objects.filter(owner=request.user, starts_at__date=today).order_by("starts_at")[
            :8
        ],
        "tasks": Task.objects.filter(owner=request.user)
        .exclude(status=Task.Status.DONE)
        .order_by("priority", "due_at")[:8],
        "notifications": Notification.objects.filter(owner=request.user, read_at__isnull=True)[:6],
        "recent_items": LibraryItem.objects.filter(owner=request.user).order_by("-updated_at")[:6],
        "formations": LearningPath.objects.filter(owner=request.user).order_by("title")[:6],
        "now": now,
    }
    return render(request, "dashboard/home.html", context)


@login_required
@require_POST
def save_layout(request):
    try:
        payload = json.loads(request.body)
        widgets = payload["widgets"]
        if not isinstance(widgets, list):
            raise ValueError
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return JsonResponse({"error": "Disposition invalide."}, status=400)
    allowed = set(DashboardWidget.Kind.values)
    for position, data in enumerate(widgets):
        kind = data.get("kind")
        if kind not in allowed:
            return JsonResponse({"error": "Widget inconnu."}, status=400)
        DashboardWidget.objects.update_or_create(
            owner=request.user,
            kind=kind,
            defaults={"position": position, "visible": bool(data.get("visible", True))},
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
