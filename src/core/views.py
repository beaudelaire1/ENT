from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render

from core.search import SOURCES, count_by_type
from core.search import search as search_entries

logger = logging.getLogger(__name__)


def root_redirect(request):
    return redirect("dashboard:home" if request.user.is_authenticated else "accounts:login")


def health(request):
    checks = {"database": "ok", "cache": "ok"}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Readiness database check failed", extra={"request_id": getattr(request, "request_id", "")})
        checks["database"] = "error"
    try:
        cache.set("myent:health", "ok", timeout=10)
        if cache.get("myent:health") != "ok":
            raise RuntimeError("cache readback failed")
    except Exception:
        logger.exception("Readiness cache check failed", extra={"request_id": getattr(request, "request_id", "")})
        checks["cache"] = "error"
    ready = all(value == "ok" for value in checks.values())
    return JsonResponse({"status": "ok" if ready else "error", "checks": checks}, status=200 if ready else 503)


def live(request):
    """Vivacité sans dépendance externe : le processus Django répond."""
    return JsonResponse({"status": "ok"})


@login_required
def search(request):
    query = request.GET.get("q", "").strip()
    object_type = request.GET.get("type") or ""
    if object_type not in SOURCES:
        object_type = ""
    entries = search_entries(request.user, query, object_type or None)
    page = Paginator(entries, 25).get_page(request.GET.get("page"))
    # Chaque filtre dit ce qu'il contient ; un type sans résultat n'est pas proposé, sauf
    # celui qu'on regarde, pour pouvoir en sortir.
    counts = count_by_type(request.user, query)
    return render(
        request,
        "core/search.html",
        {
            "query": query,
            "page": page,
            "object_type": object_type,
            "types": [
                (key, source.label, counts.get(key, 0))
                for key, source in SOURCES.items()
                if counts.get(key) or key == object_type
            ],
            "all_count": sum(counts.values()),
            "total": page.paginator.count if query else 0,
        },
    )
