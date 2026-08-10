from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render


def root_redirect(request):
    return redirect("dashboard:home" if request.user.is_authenticated else "accounts:login")


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return JsonResponse({"status": "error", "database": str(exc)}, status=503)
    return JsonResponse({"status": "ok"})


@login_required
def search(request):
    query = request.GET.get("q", "").strip()
    results = {"library": [], "tasks": [], "events": [], "formations": []}
    if query:
        from formations.models import Competency, LearningPath, LearningUnit
        from library.models import LibraryItem
        from planner.models import CalendarEvent, Task

        results["library"] = LibraryItem.objects.for_user(request.user).search(query)[:20]
        results["tasks"] = Task.objects.filter(owner=request.user).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )[:20]
        results["events"] = CalendarEvent.objects.filter(owner=request.user).filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query)
        )[:20]
        results["formations"] = (
            list(
                LearningPath.objects.filter(owner=request.user).filter(
                    Q(title__icontains=query) | Q(description__icontains=query)
                )[:10]
            )
            + list(
                LearningUnit.objects.filter(period__path__owner=request.user).filter(
                    Q(title__icontains=query) | Q(description__icontains=query)
                )[:10]
            )
            + list(
                Competency.objects.filter(unit__period__path__owner=request.user).filter(
                    Q(title__icontains=query) | Q(description__icontains=query)
                )[:10]
            )
        )
    return render(request, "core/search.html", {"query": query, "results": results})
