from __future__ import annotations

import json
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.deletion import confirm_delete
from core.editing import form_page
from core.navigation import safe_next
from library.models import LibraryItem

from .academics import struggling_competencies, unit_average
from .catalog import CatalogError, export_catalog, get_template, import_catalog, templates, validate_catalog
from .curated_resources import ROLE_LABELS, recommendations_for
from .forms import (
    AssessmentForm,
    AssessmentResultForm,
    CompetencyForm,
    FormationDuplicateForm,
    FormationImportConfirmForm,
    FormationImportForm,
    FormationTemplateForm,
    LearningGroupForm,
    LearningPathForm,
    LearningUnitForm,
    MetricDefinitionForm,
    PeriodForm,
    ProgressForm,
    ProgressRowFormSet,
    UnitCompetencyForm,
)
from .history import level_timeline, sparkline
from .models import (
    Assessment,
    Competency,
    LearningGroup,
    LearningPath,
    LearningUnit,
    MetricDefinition,
    Period,
    ProgressRecord,
    UnitCompetency,
)
from .navigation import competency_crumbs, path_crumbs, period_crumbs, unit_crumbs
from .progression import MASTERY_DESCRIPTIONS
from .resource_services import attach_curated_recommendations
from .revision import suggest_from_result
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
        LearningPath.objects.select_related("current_period", "weight_metric").prefetch_related(
            "periods__units__competencies", "metric_definitions"
        ),
        owner=request.user,
        pk=pk,
    )
    return render(request, "formations/detail.html", {"path": path, "breadcrumbs": path_crumbs(path)})


@login_required
def path_templates(request):
    return render(
        request,
        "formations/templates.html",
        {
            "templates": templates(),
            "breadcrumbs": [
                {"label": "Formations", "url": reverse("formations:list")},
                {"label": "Modèles", "url": None},
            ],
        },
    )


@login_required
def path_template_preview(request, slug):
    try:
        template = get_template(slug)
    except CatalogError:
        return redirect("formations:templates")
    data = template["data"]
    form = FormationTemplateForm(
        request.POST or None,
        initial_title=data["formation"]["title"],
        initial={"title": data["formation"]["title"]},
    )
    if request.method == "POST" and form.is_valid():
        path = import_catalog(
            data,
            owner=request.user,
            title=form.cleaned_data["title"],
            academic_year=form.cleaned_data["academic_year"],
        )
        messages.success(request, f"« {path.title} » a été créée depuis le modèle. Tout reste modifiable.")
        return redirect("formations:detail", pk=path.pk)
    return render(
        request,
        "formations/template_preview.html",
        {
            "template": template,
            "form": form,
            "breadcrumbs": [
                {"label": "Formations", "url": reverse("formations:list")},
                {"label": "Modèles", "url": reverse("formations:templates")},
                {"label": template["preview"]["title"], "url": None},
            ],
        },
    )


@login_required
def path_import(request):
    upload_form = FormationImportForm()
    confirm_form = None
    preview = None
    if request.method == "POST" and "confirm" in request.POST:
        confirm_form = FormationImportConfirmForm(request.POST)
        if confirm_form.is_valid():
            try:
                data = confirm_form.cleaned_data["payload"]
                validate_catalog(data)
                path = import_catalog(
                    data,
                    owner=request.user,
                    title=confirm_form.cleaned_data["title"],
                    academic_year=confirm_form.cleaned_data["academic_year"],
                )
            except CatalogError as exc:
                confirm_form.add_error("payload", str(exc))
            else:
                messages.success(request, f"« {path.title} » a été importée.")
                return redirect("formations:detail", pk=path.pk)
    elif request.method == "POST":
        upload_form = FormationImportForm(request.POST, request.FILES)
        if upload_form.is_valid():
            data = upload_form.cleaned_data["catalog"]
            try:
                preview = validate_catalog(data)
            except CatalogError as exc:
                upload_form.add_error("catalog", str(exc))
            else:
                confirm_form = FormationImportConfirmForm(
                    initial={
                        "payload": json.dumps(data, ensure_ascii=False),
                        "title": data["formation"]["title"],
                        "academic_year": data["formation"].get("academic_year", ""),
                    }
                )
    return render(
        request,
        "formations/import.html",
        {
            "upload_form": upload_form,
            "confirm_form": confirm_form,
            "preview": preview,
            "breadcrumbs": [
                {"label": "Formations", "url": reverse("formations:list")},
                {"label": "Importer", "url": None},
            ],
        },
    )


@login_required
def path_export(request, pk):
    path = get_object_or_404(LearningPath, owner=request.user, pk=pk)
    response = JsonResponse(
        export_catalog(path),
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )
    response["Content-Disposition"] = f'attachment; filename="formation-{path.pk}.json"'
    return response


@login_required
def path_duplicate(request, pk):
    source = get_object_or_404(LearningPath, owner=request.user, pk=pk)
    form = FormationDuplicateForm(request.POST or None, initial={"title": f"Copie de {source.title}"})
    if request.method == "POST" and form.is_valid():
        path = import_catalog(export_catalog(source), owner=request.user, title=form.cleaned_data["title"])
        messages.success(request, f"« {path.title} » est une copie indépendante.")
        return redirect("formations:detail", pk=path.pk)
    return render(
        request,
        "formations/duplicate.html",
        {
            "source": source,
            "form": form,
            "breadcrumbs": path_crumbs(source) + [{"label": "Dupliquer", "url": None}],
        },
    )


@login_required
def path_tracking(request, pk):
    """Grille de suivi : toutes les compétences du parcours, éditables en place.

    L'enregistrement est indivisible : ``save_tracking`` valide les chiffres des matières
    et la progression des compétences avant d'écrire quoi que ce soit.
    """
    path = get_object_or_404(LearningPath, owner=request.user, pk=pk)
    ensure_progress_records(request.user, path)
    formset = ProgressRowFormSet(request.POST or None, queryset=tracked_records(request.user, path))
    timeline = level_timeline(request.user, path)
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
            # Le nom du niveau et son critère voyagent ensemble : les séparer laisserait
            # le gabarit rapprocher deux listes par leur ordre, ce qui casse en silence.
            "levels": [
                {"value": value, "label": label, "description": MASTERY_DESCRIPTIONS.get(value, "")}
                for value, label in ProgressRecord.Mastery.choices
            ],
            "timeline": timeline,
            "sparkline": sparkline(timeline),
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
        form=LearningUnitForm(
            request.POST or None, instance=unit, user=request.user, period=period, scope={"period": period}
        ),
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
def group_edit(request, period_pk=None, pk=None):
    """Un regroupement — UE, bloc, domaine — à l'intérieur d'une période."""
    group = get_object_or_404(LearningGroup, period__path__owner=request.user, pk=pk) if pk else None
    period = group.period if group else get_object_or_404(Period, path__owner=request.user, pk=period_pk)
    return _form_page(
        request,
        form=LearningGroupForm(request.POST or None, instance=group, scope={"period": period}),
        title="Modifier le regroupement" if group else "Nouveau regroupement",
        subtitle=f"{period.path.title} · {period.title}",
        breadcrumbs=period_crumbs(period) + [{"label": group.title if group else "Nouveau regroupement", "url": None}],
        fallback=lambda obj: reverse("formations:detail", args=[period.path_id]),
        delete_url=reverse("formations:group_delete", args=[group.pk]) if group else None,
        delete_label="ce regroupement",
    )


@login_required
def group_delete(request, pk):
    group = get_object_or_404(LearningGroup, period__path__owner=request.user, pk=pk)
    return confirm_delete(
        request,
        group,
        redirect_to=reverse("formations:detail", args=[group.period.path_id]),
        title="Supprimer ce regroupement",
    )


@login_required
def unit_competencies(request, pk):
    """Rattacher à une matière des compétences qui existent déjà dans la formation.

    C'est ce qui rend la transversalité utilisable : « Rédiger une démonstration au
    tableau » se déclare une fois, puis se rattache à chaque matière qui l'exerce, au lieu
    d'être ressaisie et suivie deux fois.
    """
    unit = get_object_or_404(
        LearningUnit.objects.select_related("period__path"), period__path__owner=request.user, pk=pk
    )
    if request.method == "POST":
        removed = request.POST.get("remove")
        chosen = request.POST.getlist("competencies")
        if removed:
            link = get_object_or_404(UnitCompetency, unit=unit, competency_id=removed)
            label = link.competency.title
            link.delete()
            messages.success(
                request, f"« {label} » n’est plus rattachée à cette matière. La compétence reste dans la formation."
            )
        elif chosen:
            competencies = list(Competency.objects.filter(path=unit.period.path, pk__in=chosen))
            for competency in competencies:
                UnitCompetency.objects.get_or_create(
                    unit=unit, competency=competency, defaults={"order": competency.order, "is_primary": False}
                )
            messages.success(request, f"{len(competencies)} compétence(s) rattachée(s).")
        else:
            messages.error(request, "Aucune compétence sélectionnée.")
        return redirect(request.get_full_path())

    query = request.GET.get("q", "").strip()
    candidates = Competency.objects.filter(path=unit.period.path).exclude(units=unit)
    if query:
        candidates = candidates.filter(title__icontains=query)
    candidates = candidates.select_related("period").order_by("period__order", "order", "title")
    total = candidates.count()
    return render(
        request,
        "formations/unit_competencies.html",
        {
            "unit": unit,
            "links": unit.competency_links.select_related("competency__period").order_by("-is_primary", "order"),
            "candidates": candidates[:RESOURCE_RESULT_LIMIT],
            "total": total,
            "truncated": max(0, total - RESOURCE_RESULT_LIMIT),
            "query": query,
            "breadcrumbs": unit_crumbs(unit) + [{"label": "Compétences", "url": None}],
            "back_to": reverse("formations:unit", args=[unit.pk]),
        },
    )


@login_required
def link_edit(request, pk):
    """Régler ce qui n'appartient qu'au lien : ordre, caractère principal, objectif local."""
    link = get_object_or_404(
        UnitCompetency.objects.select_related("unit__period__path", "competency"),
        unit__period__path__owner=request.user,
        pk=pk,
    )
    return _form_page(
        request,
        form=UnitCompetencyForm(request.POST or None, instance=link),
        title="Rôle dans la matière",
        subtitle=f"{link.competency.title} · {link.unit.title}",
        breadcrumbs=unit_crumbs(link.unit) + [{"label": link.competency.title, "url": None}],
        fallback=lambda obj: reverse("formations:unit_competencies", args=[link.unit_id]),
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
        for record in ProgressRecord.objects.filter(owner=request.user, competency__units=unit)
    }
    rows = [
        {
            "competency": link.competency,
            "link": link,
            "progress": progress.get(link.competency_id),
            "resources": link.competency.resources.all(),
        }
        for link in unit.competency_links.select_related("competency").prefetch_related("competency__resources")
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
        Competency.objects.select_related("path", "period").prefetch_related("unit_links__unit__period"),
        path__owner=request.user,
        pk=pk,
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
        Competency.objects.select_related("path", "period").prefetch_related("resources", "unit_links__unit__period"),
        path__owner=request.user,
        pk=pk,
    )
    progress, _ = ProgressRecord.objects.get_or_create(owner=request.user, competency=competency)
    links = list(competency.unit_links.select_related("unit__period").order_by("-is_primary", "order"))
    curated = recommendations_for(competency.title, [link.unit.title for link in links])
    saved_urls = set(competency.resources.exclude(url="").values_list("url", flat=True))
    curated_missing_count = sum(resource.url not in saved_urls for resource in curated)
    curated_groups = [
        {
            "role": role,
            "label": label,
            "items": [
                {"resource": resource, "saved": resource.url in saved_urls}
                for resource in curated
                if resource.role == role
            ],
        }
        for role, label in ROLE_LABELS.items()
        if any(resource.role == role for resource in curated)
    ]
    return render(
        request,
        "formations/competency.html",
        {
            "competency": competency,
            "progress": progress,
            # Une compétence peut se travailler dans plusieurs matières : le lien porte son
            # ordre, son caractère principal et son objectif local.
            "links": links,
            "resource_groups": group_by_purpose(competency.resources.all()),
            "curated_groups": curated_groups,
            "curated_count": len(curated),
            "curated_missing_count": curated_missing_count,
            "sessions": competency.focus_sessions.filter(owner=request.user)[:8],
            # Le chemin parcouru, et pas seulement le point d'arrivée : c'est ce qui
            # distingue une compétence qui monte d'une compétence qui stagne.
            "events": progress.events.all()[:10],
            "breadcrumbs": competency_crumbs(competency),
        },
    )


@login_required
@require_POST
def competency_import_recommendations(request, pk):
    """Copie le parcours conseillé dans la bibliothèque privée, sans créer de doublons.

    Les recommandations restent consultables sans rien enregistrer. Ce POST explicite
    matérialise ensuite le choix de l'étudiant : chaque lien devient une ``LibraryItem``
    ordinaire, donc modifiable, classable et réutilisable ailleurs.
    """
    competency = get_object_or_404(
        Competency.objects.prefetch_related("unit_links__unit"),
        path__owner=request.user,
        pk=pk,
    )
    if not recommendations_for(
        competency.title,
        [link.unit.title for link in competency.unit_links.all()],
    ):
        messages.error(request, "Aucun parcours recommandé n’est disponible pour cette compétence.")
        return redirect("formations:competency", pk=competency.pk)

    result = attach_curated_recommendations(owner=request.user, competency=competency)

    if result.attached:
        messages.success(
            request,
            f"{result.attached} ressource(s) du parcours ajoutée(s) à cette compétence"
            f" — {result.created} nouvelle(s) dans la bibliothèque.",
        )
    else:
        messages.info(request, "Tout le parcours recommandé est déjà associé à cette compétence.")
    return redirect("formations:competency", pk=competency.pk)


@login_required
def competency_edit(request, unit_pk=None, pk=None):
    """Une compétence appartient à la formation ; la matière d'où on la crée la reçoit.

    Créer depuis une matière reste le geste courant, mais ne l'y enferme plus : le lien
    créé au passage peut ensuite être complété par d'autres matières.
    """
    competency = get_object_or_404(Competency, path__owner=request.user, pk=pk) if pk else None
    unit = None if competency else get_object_or_404(LearningUnit, period__path__owner=request.user, pk=unit_pk)
    path = competency.path if competency else unit.period.path
    scope = {"path": path}
    if unit is not None:
        # La période de la matière sert de valeur de départ ; elle reste modifiable.
        scope["period"] = unit.period

    def attach(created):
        if unit is not None:
            UnitCompetency.objects.get_or_create(
                unit=unit, competency=created, defaults={"order": created.order, "is_primary": True}
            )

    return _form_page(
        request,
        form=CompetencyForm(request.POST or None, instance=competency, path=path, scope=scope),
        title="Modifier la compétence" if competency else "Nouvelle compétence",
        subtitle=unit.title if unit else path.title,
        breadcrumbs=(
            competency_crumbs(competency) + [{"label": "Modifier", "url": None}]
            if competency
            else unit_crumbs(unit) + [{"label": "Nouvelle compétence", "url": None}]
        ),
        fallback=lambda obj: reverse("formations:competency", args=[obj.pk]),
        delete_url=reverse("formations:competency_delete", args=[competency.pk]) if competency else None,
        delete_label="cette compétence",
        after_save=attach,
    )


@login_required
def progress_edit(request, competency_pk):
    competency = get_object_or_404(Competency, path__owner=request.user, pk=competency_pk)
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
@require_POST
def progress_adopt(request, competency_pk):
    """Fait sien le niveau que le temps a proposé.

    Un seul geste couvre les deux situations visibles à l'écran : confirmer un palier qui
    s'est appliqué tout seul, et adopter une proposition restée en attente parce qu'un
    niveau avait déjà été déclaré. Dans les deux cas le niveau devient une appréciation
    personnelle, datée, que plus aucun palier ne réécrira.
    """
    competency = get_object_or_404(
        Competency.objects.select_related("path"), path__owner=request.user, pk=competency_pk
    )
    progress, _ = ProgressRecord.objects.get_or_create(owner=request.user, competency=competency)
    progress.competency = competency
    if progress.adopt_suggested_level():
        messages.success(request, f"Niveau confirmé : {progress.get_mastery_level_display().lower()}.")
    else:
        messages.info(request, "Ce niveau est déjà le vôtre.")
    return redirect(safe_next(request, reverse("formations:competency", args=[competency.pk])))


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
    competency = get_object_or_404(Competency, path__owner=request.user, pk=pk)
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


# ----------------------------------------------------------------------- évaluations


@login_required
def assessment_list(request):
    """Les évaluations, à venir d'abord : c'est ce qui se prépare qui compte."""
    assessments = (
        Assessment.objects.filter(owner=request.user)
        .select_related("unit__period__path", "period", "result")
        .prefetch_related("competencies")
    )
    upcoming = sorted((a for a in assessments if a.is_upcoming), key=lambda a: a.scheduled_for)
    past = [a for a in assessments if not a.is_upcoming]
    return render(
        request,
        "formations/assessments.html",
        {
            "upcoming": upcoming,
            "past": past,
            "breadcrumbs": [{"label": "Évaluations", "url": None}],
        },
    )


@login_required
def assessment_edit(request, pk=None):
    assessment = get_object_or_404(Assessment, owner=request.user, pk=pk) if pk else None
    return _form_page(
        request,
        form=AssessmentForm(
            request.POST or None, instance=assessment, user=request.user, scope={"owner": request.user}
        ),
        eyebrow="ÉVALUATIONS",
        title="Modifier l’évaluation" if assessment else "Nouvelle évaluation",
        breadcrumbs=[
            {"label": "Évaluations", "url": reverse("formations:assessments")},
            {"label": assessment.title if assessment else "Nouvelle évaluation", "url": None},
        ],
        fallback=lambda obj: reverse("formations:assessment", args=[obj.pk]),
        default_back=reverse("formations:assessments"),
        delete_url=reverse("formations:assessment_delete", args=[assessment.pk]) if assessment else None,
        delete_label="cette évaluation",
    )


@login_required
def assessment_detail(request, pk):
    """Une évaluation : ce qu'elle couvre, et quoi en faire — avant comme après.

    Avant, l'écran sert à réviser : temps restant, compétences visées, celles qui ne sont
    pas acquises, et leurs ressources. Après, il sert à décider quoi reprendre.
    """
    assessment = get_object_or_404(
        Assessment.objects.select_related("unit__period__path", "period", "result").prefetch_related(
            "competencies", "resources"
        ),
        owner=request.user,
        pk=pk,
    )
    weak = struggling_competencies(request.user, assessment)
    resources = LibraryItem.objects.filter(competencies__in=assessment.competencies.all()).distinct()
    return render(
        request,
        "formations/assessment.html",
        {
            "assessment": assessment,
            "result": getattr(assessment, "result", None),
            "weak": weak,
            "competency_resources": group_by_purpose(resources),
            "average": unit_average(request.user, assessment.unit) if assessment.unit_id else None,
            "breadcrumbs": [
                {"label": "Évaluations", "url": reverse("formations:assessments")},
                {"label": assessment.title, "url": None},
            ],
        },
    )


@login_required
def assessment_delete(request, pk):
    assessment = get_object_or_404(Assessment, owner=request.user, pk=pk)
    return confirm_delete(
        request,
        assessment,
        redirect_to=reverse("formations:assessments"),
        title="Supprimer cette évaluation",
        back_to=reverse("formations:assessment", args=[assessment.pk]),
    )


@login_required
def result_edit(request, pk):
    """Saisir ou corriger le résultat d'une évaluation.

    Le barème part de celui de l'évaluation, puis vit sa vie : changer le barème d'une
    épreuve à venir ne doit pas réécrire une note déjà obtenue.
    """
    assessment = get_object_or_404(Assessment, owner=request.user, pk=pk)
    result = getattr(assessment, "result", None)
    initial = {} if result else {"scale": assessment.scale}

    def mark_as_corrected(saved):
        if assessment.status in {Assessment.Status.PLANNED, Assessment.Status.TAKEN}:
            assessment.status = Assessment.Status.MARKED
            assessment.save(update_fields=["status", "updated_at"])
        # Une note obtenue est une information sur la maîtrise : la laisser sans effet
        # obligeait à retourner déclarer soi-même ce que le résultat venait de montrer.
        # Elle propose donc un niveau, sans jamais primer sur une appréciation déclarée.
        assessment.refresh_from_db()
        applied, pending = suggest_from_result(request.user, assessment)
        if applied:
            messages.info(
                request,
                f"{len(applied)} compétence(s) ont reçu un niveau suggéré par ce résultat, à confirmer.",
            )
        if pending:
            messages.info(
                request,
                f"{len(pending)} compétence(s) où ce résultat suggère mieux que le niveau que vous aviez déclaré.",
            )

    return _form_page(
        request,
        form=AssessmentResultForm(
            request.POST or None, instance=result, initial=initial, scope={"assessment": assessment}
        ),
        eyebrow="RÉSULTAT",
        title="Modifier le résultat" if result else "Saisir le résultat",
        subtitle=assessment.title,
        breadcrumbs=[
            {"label": "Évaluations", "url": reverse("formations:assessments")},
            {"label": assessment.title, "url": reverse("formations:assessment", args=[assessment.pk])},
            {"label": "Résultat", "url": None},
        ],
        fallback=lambda obj: reverse("formations:assessment", args=[assessment.pk]),
        default_back=reverse("formations:assessment", args=[assessment.pk]),
        after_save=mark_as_corrected,
    )


@login_required
def assessment_competencies(request, pk):
    """Déclarer ce que l'évaluation évalue, par recherche dans la formation."""
    assessment = get_object_or_404(Assessment, owner=request.user, pk=pk)
    if request.method == "POST":
        removed = request.POST.get("remove")
        chosen = request.POST.getlist("competencies")
        if removed:
            competency = get_object_or_404(Competency, path__owner=request.user, pk=removed)
            assessment.competencies.remove(competency)
            messages.success(request, f"« {competency.title} » n’est plus évaluée ici.")
        elif chosen:
            competencies = list(Competency.objects.filter(path__owner=request.user, pk__in=chosen))
            assessment.competencies.add(*competencies)
            messages.success(request, f"{len(competencies)} compétence(s) ajoutée(s).")
        else:
            messages.error(request, "Aucune compétence sélectionnée.")
        return redirect(request.get_full_path())

    query = request.GET.get("q", "").strip()
    candidates = Competency.objects.filter(path__owner=request.user).exclude(assessments=assessment)
    if query:
        candidates = candidates.filter(title__icontains=query)
    elif assessment.unit_id:
        # Sans recherche, la matière de l'évaluation d'abord : c'est presque toujours là.
        candidates = candidates.filter(units=assessment.unit)
    candidates = candidates.select_related("period", "path").order_by("period__order", "order", "title")
    total = candidates.count()
    return render(
        request,
        "formations/assessment_competencies.html",
        {
            "assessment": assessment,
            "attached": assessment.competencies.select_related("period"),
            "candidates": candidates[:RESOURCE_RESULT_LIMIT],
            "total": total,
            "truncated": max(0, total - RESOURCE_RESULT_LIMIT),
            "query": query,
            "breadcrumbs": [
                {"label": "Évaluations", "url": reverse("formations:assessments")},
                {"label": assessment.title, "url": reverse("formations:assessment", args=[assessment.pk])},
                {"label": "Compétences évaluées", "url": None},
            ],
            "back_to": reverse("formations:assessment", args=[assessment.pk]),
        },
    )
