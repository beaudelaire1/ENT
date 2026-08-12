from __future__ import annotations

from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.deletion import confirm_delete
from core.editing import form_page
from library.models import LibraryItem

from .forms import (
    CompetencyForm,
    LearningPathForm,
    LearningUnitForm,
    MetricDefinitionForm,
    PeriodForm,
    ProgressForm,
    ProgressRowFormSet,
)
from .models import Competency, LearningPath, LearningUnit, MetricDefinition, Period, ProgressRecord
from .navigation import competency_crumbs, path_crumbs, period_crumbs, unit_crumbs
from .services import build_tracking_grid, ensure_progress_records, save_tracking, tracked_records


def _form_page(request, **kwargs):
    """L'écran partagé de `core.editing`, avec le contexte propre aux formations."""
    kwargs.setdefault("eyebrow", "FORMATIONS")
    kwargs.setdefault("default_back", reverse("formations:list"))
    return form_page(request, **kwargs)


@login_required
def path_list(request):
    return render(
        request,
        "formations/list.html",
        {
            "paths": LearningPath.objects.filter(owner=request.user),
            "breadcrumbs": [{"label": "Formations", "url": None}],
        },
    )


@login_required
def path_detail(request, pk):
    path = get_object_or_404(
        LearningPath.objects.prefetch_related("periods__units__competencies", "metric_definitions"),
        owner=request.user,
        pk=pk,
    )
    return render(request, "formations/detail.html", {"path": path, "breadcrumbs": path_crumbs(path)})


@login_required
def path_tracking(request, pk):
    """Grille de suivi : toutes les compétences du parcours, éditables en place.

    L'enregistrement est indivisible : ``save_tracking`` valide les chiffres des matières
    et la progression des compétences avant d'écrire quoi que ce soit.
    """
    path = get_object_or_404(LearningPath, owner=request.user, pk=pk)
    ensure_progress_records(request.user, path)
    formset = ProgressRowFormSet(request.POST or None, queryset=tracked_records(request.user, path))
    metric_errors = []
    if request.method == "POST":
        saved, metric_errors = save_tracking(path, formset, request.POST)
        if saved:
            messages.success(request, "Suivi enregistré.")
            return redirect("formations:tracking", pk=path.pk)
    return render(
        request,
        "formations/tracking.html",
        {
            "path": path,
            "formset": formset,
            # Les cases reprennent la saisie rejetée plutôt que la valeur en base.
            "grid": build_tracking_grid(path, formset, submitted=request.POST if request.method == "POST" else None),
            "levels": ProgressRecord.Mastery.choices,
            "metric_errors": metric_errors,
            "save_failed": request.method == "POST",
            "breadcrumbs": path_crumbs(path) + [{"label": "Suivi", "url": None}],
        },
    )


@login_required
def path_edit(request, pk=None):
    path = get_object_or_404(LearningPath, owner=request.user, pk=pk) if pk else None
    return _form_page(
        request,
        form=LearningPathForm(request.POST or None, instance=path, scope={"owner": request.user}),
        title="Modifier la formation" if path else "Nouvelle formation",
        breadcrumbs=(path_crumbs(path) if path else [{"label": "Formations", "url": reverse("formations:list")}])
        + [{"label": "Modifier" if path else "Nouvelle formation", "url": None}],
        fallback=lambda obj: reverse("formations:detail", args=[obj.pk]),
        delete_url=reverse("formations:delete", args=[path.pk]) if path else None,
        delete_label="cette formation",
    )


@login_required
def period_edit(request, path_pk=None, pk=None):
    """Une période se crée depuis sa formation et se modifie depuis elle-même."""
    period = get_object_or_404(Period, path__owner=request.user, pk=pk) if pk else None
    path = period.path if period else get_object_or_404(LearningPath, owner=request.user, pk=path_pk)
    return _form_page(
        request,
        form=PeriodForm(request.POST or None, instance=period, scope={"path": path}),
        title="Modifier la période" if period else "Nouvelle période",
        subtitle=path.title,
        breadcrumbs=path_crumbs(path) + [{"label": period.title if period else "Nouvelle période", "url": None}],
        fallback=lambda obj: reverse("formations:detail", args=[path.pk]),
        delete_url=reverse("formations:period_delete", args=[period.pk]) if period else None,
        delete_label="cette période",
    )


@login_required
def unit_edit(request, period_pk=None, pk=None):
    unit = get_object_or_404(LearningUnit, period__path__owner=request.user, pk=pk) if pk else None
    period = unit.period if unit else get_object_or_404(Period, path__owner=request.user, pk=period_pk)
    return _form_page(
        request,
        form=LearningUnitForm(request.POST or None, instance=unit, user=request.user, scope={"period": period}),
        title="Modifier la matière" if unit else "Nouvelle matière",
        subtitle=f"{period.path.title} · {period.title}",
        breadcrumbs=(
            unit_crumbs(unit) + [{"label": "Modifier", "url": None}]
            if unit
            else period_crumbs(period) + [{"label": "Nouvelle matière", "url": None}]
        ),
        fallback=lambda obj: reverse("formations:unit", args=[obj.pk]),
        delete_url=reverse("formations:unit_delete", args=[unit.pk]) if unit else None,
        delete_label="cette matière",
    )


@login_required
def unit_detail(request, pk):
    unit = get_object_or_404(
        LearningUnit.objects.select_related("period__path").prefetch_related(
            "competencies__resources", "resources", "metric_values__definition"
        ),
        period__path__owner=request.user,
        pk=pk,
    )
    ensure_progress_records(request.user, unit.period.path)
    # La progression est rattachée en une requête plutôt que dans le gabarit : appeler
    # `competency.progress_records` par ligne ferait une requête par compétence, et rien
    # ne garantirait qu'il s'agit bien de celle du propriétaire connecté.
    progress = {
        record.competency_id: record
        for record in ProgressRecord.objects.filter(owner=request.user, competency__unit=unit)
    }
    rows = [
        {"competency": competency, "progress": progress.get(competency.pk), "resources": competency.resources.all()}
        for competency in unit.competencies.all()
    ]
    return render(request, "formations/unit.html", {"unit": unit, "rows": rows, "breadcrumbs": unit_crumbs(unit)})


RESOURCE_RESULT_LIMIT = 40


def group_by_purpose(resources) -> list[dict]:
    """Regroupe des ressources par nature pédagogique, dans l'ordre des choix déclarés.

    On cherche « les annales » ou « le corrigé », pas « les fichiers » : le classement
    suit donc l'usage et non le format de stockage.
    """
    labels = dict(LibraryItem.Purpose.choices)
    buckets: dict[str, list] = {}
    for resource in resources:
        buckets.setdefault(resource.purpose, []).append(resource)
    return [
        {"purpose": value, "label": labels[value], "items": buckets[value]}
        for value, _label in LibraryItem.Purpose.choices
        if value in buckets
    ]


def _resource_picker(request, *, holder, subtitle, breadcrumbs, back_to):
    """Associer des ressources par recherche, plutôt que dans une liste de cases.

    Le formulaire d'édition affichait toute la bibliothèque en cases à cocher : passé
    quelques dizaines de ressources, trouver la bonne devenait un exercice de patience, et
    une case décochée par inadvertance rompait une association sans prévenir.

    Retirer une association ne supprime pas la ressource : elle reste dans la
    bibliothèque, où elle peut servir ailleurs.
    """
    owner = request.user
    if request.method == "POST":
        removed = request.POST.get("remove")
        chosen = request.POST.getlist("resources")
        if removed:
            resource = get_object_or_404(LibraryItem, owner=owner, pk=removed)
            holder.resources.remove(resource)
            messages.success(request, f"« {resource.title} » n’est plus associée. Elle reste dans la bibliothèque.")
        elif chosen:
            resources = list(LibraryItem.objects.filter(owner=owner, pk__in=chosen))
            holder.resources.add(*resources)
            messages.success(request, f"{len(resources)} ressource(s) associée(s).")
        else:
            messages.error(request, "Aucune ressource sélectionnée.")
        return redirect(request.get_full_path())

    query = request.GET.get("q", "").strip()
    kind = request.GET.get("kind", "")
    purpose = request.GET.get("purpose", "")
    candidates = LibraryItem.objects.filter(owner=owner).exclude(pk__in=holder.resources.values("pk"))
    if query:
        candidates = candidates.search(query)
    if kind in LibraryItem.Kind.values:
        candidates = candidates.filter(kind=kind)
    if purpose in LibraryItem.Purpose.values:
        candidates = candidates.filter(purpose=purpose)
    candidates = candidates.order_by("-updated_at")
    total = candidates.count()
    return render(
        request,
        "formations/resources.html",
        {
            "holder": holder,
            "subtitle": subtitle,
            "attached": holder.resources.all().order_by("purpose", "title"),
            "candidates": candidates[:RESOURCE_RESULT_LIMIT],
            "total": total,
            # Une liste tronquée le dit : sinon elle passe pour la liste complète.
            "truncated": max(0, total - RESOURCE_RESULT_LIMIT),
            "query": query,
            "kind": kind,
            "purpose": purpose,
            "kinds": LibraryItem.Kind.choices,
            "purposes": LibraryItem.Purpose.choices,
            "breadcrumbs": breadcrumbs,
            "back_to": back_to,
            "create_url": f"{reverse('library:new')}?next={quote(request.get_full_path())}",
        },
    )


@login_required
def competency_resources(request, pk):
    competency = get_object_or_404(
        Competency.objects.select_related("unit__period__path"), unit__period__path__owner=request.user, pk=pk
    )
    return _resource_picker(
        request,
        holder=competency,
        subtitle=f"Compétence · {competency.title}",
        breadcrumbs=competency_crumbs(competency) + [{"label": "Ressources", "url": None}],
        back_to=reverse("formations:competency", args=[competency.pk]),
    )


@login_required
def unit_resources(request, pk):
    unit = get_object_or_404(
        LearningUnit.objects.select_related("period__path"), period__path__owner=request.user, pk=pk
    )
    return _resource_picker(
        request,
        holder=unit,
        subtitle=f"Matière · {unit.title}",
        breadcrumbs=unit_crumbs(unit) + [{"label": "Ressources", "url": None}],
        back_to=reverse("formations:unit", args=[unit.pk]),
    )


@login_required
def competency_detail(request, pk):
    """La page d'une compétence : son état, et ce qui permet de la travailler.

    Une compétence en difficulté est le point de départ naturel d'une séance de travail.
    Elle n'avait pourtant pas de page : la recherche globale menait à sa matière, et il
    fallait la retrouver dans une liste.
    """
    competency = get_object_or_404(
        Competency.objects.select_related("unit__period__path").prefetch_related("resources"),
        unit__period__path__owner=request.user,
        pk=pk,
    )
    progress, _ = ProgressRecord.objects.get_or_create(owner=request.user, competency=competency)
    return render(
        request,
        "formations/competency.html",
        {
            "competency": competency,
            "progress": progress,
            "unit": competency.unit,
            "resource_groups": group_by_purpose(competency.resources.all()),
            "sessions": competency.focus_sessions.filter(owner=request.user)[:8],
            "breadcrumbs": competency_crumbs(competency),
        },
    )


@login_required
def competency_edit(request, unit_pk=None, pk=None):
    competency = get_object_or_404(Competency, unit__period__path__owner=request.user, pk=pk) if pk else None
    unit = (
        competency.unit if competency else get_object_or_404(LearningUnit, period__path__owner=request.user, pk=unit_pk)
    )
    return _form_page(
        request,
        form=CompetencyForm(request.POST or None, instance=competency, user=request.user, scope={"unit": unit}),
        title="Modifier la compétence" if competency else "Nouvelle compétence",
        subtitle=unit.title,
        breadcrumbs=(
            competency_crumbs(competency) + [{"label": "Modifier", "url": None}]
            if competency
            else unit_crumbs(unit) + [{"label": "Nouvelle compétence", "url": None}]
        ),
        fallback=lambda obj: reverse("formations:competency", args=[obj.pk]),
        delete_url=reverse("formations:competency_delete", args=[competency.pk]) if competency else None,
        delete_label="cette compétence",
    )


@login_required
def progress_edit(request, competency_pk):
    competency = get_object_or_404(Competency, unit__period__path__owner=request.user, pk=competency_pk)
    progress, _ = ProgressRecord.objects.get_or_create(owner=request.user, competency=competency)
    return _form_page(
        request,
        form=ProgressForm(
            request.POST or None, instance=progress, scope={"owner": request.user, "competency": competency}
        ),
        title="Où j’en suis",
        subtitle=competency.title,
        breadcrumbs=competency_crumbs(competency) + [{"label": "Progression", "url": None}],
        fallback=lambda obj: reverse("formations:competency", args=[competency.pk]),
    )


@login_required
def metric_definition_edit(request, path_pk=None, pk=None):
    metric = get_object_or_404(MetricDefinition, path__owner=request.user, pk=pk) if pk else None
    path = metric.path if metric else get_object_or_404(LearningPath, owner=request.user, pk=path_pk)
    return _form_page(
        request,
        form=MetricDefinitionForm(request.POST or None, instance=metric, scope={"path": path}),
        title="Modifier la colonne" if metric else "Nouvelle colonne de suivi",
        subtitle=path.title,
        breadcrumbs=path_crumbs(path) + [{"label": metric.label if metric else "Nouvelle colonne", "url": None}],
        fallback=lambda obj: reverse("formations:detail", args=[path.pk]),
        delete_url=reverse("formations:metric_delete", args=[metric.pk]) if metric else None,
        delete_label="cette colonne",
    )


@login_required
def path_delete(request, pk):
    path = get_object_or_404(LearningPath, owner=request.user, pk=pk)
    return confirm_delete(
        request,
        path,
        redirect_to=reverse("formations:list"),
        title="Supprimer cette formation",
        back_to=reverse("formations:detail", args=[path.pk]),
    )


@login_required
def period_delete(request, pk):
    period = get_object_or_404(Period, path__owner=request.user, pk=pk)
    return confirm_delete(
        request,
        period,
        redirect_to=reverse("formations:detail", args=[period.path_id]),
        title="Supprimer cette période",
    )


@login_required
def unit_delete(request, pk):
    unit = get_object_or_404(LearningUnit, period__path__owner=request.user, pk=pk)
    return confirm_delete(
        request,
        unit,
        redirect_to=reverse("formations:detail", args=[unit.period.path_id]),
        title="Supprimer cette matière",
        back_to=reverse("formations:unit", args=[unit.pk]),
    )


@login_required
def competency_delete(request, pk):
    competency = get_object_or_404(Competency, unit__period__path__owner=request.user, pk=pk)
    return confirm_delete(
        request,
        competency,
        redirect_to=reverse("formations:unit", args=[competency.unit_id]),
        title="Supprimer cette compétence",
        back_to=reverse("formations:competency", args=[competency.pk]),
    )


@login_required
def metric_definition_delete(request, pk):
    metric = get_object_or_404(MetricDefinition, path__owner=request.user, pk=pk)
    return confirm_delete(
        request,
        metric,
        redirect_to=reverse("formations:detail", args=[metric.path_id]),
        title="Supprimer cette colonne",
    )
