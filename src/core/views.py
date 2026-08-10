from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render

from core.search import SOURCES
from core.search import search as search_entries


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
    object_type = request.GET.get("type") or ""
    if object_type not in SOURCES:
        object_type = ""
    entries = search_entries(request.user, query, object_type or None)
    page = Paginator(entries, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "core/search.html",
        {
            "query": query,
            "page": page,
            "object_type": object_type,
            "types": [(key, source.label) for key, source in SOURCES.items()],
            "total": page.paginator.count if query else 0,
        },
    )
