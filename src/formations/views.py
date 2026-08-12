from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.deletion import confirm_delete

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
from .services import build_tracking_grid, ensure_progress_records, save_tracking, tracked_records


@login_required
def path_list(request):
    return render(request, "formations/list.html", {"paths": LearningPath.objects.filter(owner=request.user)})


@login_required
def path_detail(request, pk):
    path = get_object_or_404(
        LearningPath.objects.prefetch_related("periods__units__competencies", "metric_definitions"),
        owner=request.user,
        pk=pk,
    )
    return render(request, "formations/detail.html", {"path": path})


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
        },
    )


@login_required
def path_edit(request, pk=None):
    path = get_object_or_404(LearningPath, owner=request.user, pk=pk) if pk else None
    form = LearningPathForm(request.POST or None, instance=path, scope={"owner": request.user})
    if request.method == "POST" and form.is_valid():
        path = form.save()
        messages.success(request, "Formation enregistrée.")
        return redirect("formations:detail", pk=path.pk)
    return render(
        request,
        "formations/form.html",
        {"form": form, "title": "Modifier la formation" if path else "Nouvelle formation"},
    )


@login_required
def period_new(request, path_pk):
    path = get_object_or_404(LearningPath, owner=request.user, pk=path_pk)
    form = PeriodForm(request.POST or None, scope={"path": path})
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("formations:detail", pk=path.pk)
    return render(request, "formations/form.html", {"form": form, "title": f"Nouvelle période · {path.title}"})


@login_required
def unit_new(request, period_pk):
    period = get_object_or_404(Period, path__owner=request.user, pk=period_pk)
    form = LearningUnitForm(request.POST or None, user=request.user, scope={"period": period})
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("formations:detail", pk=period.path_id)
    return render(request, "formations/form.html", {"form": form, "title": f"Nouveau module · {period.title}"})


@login_required
def unit_detail(request, pk):
    unit = get_object_or_404(
        LearningUnit.objects.prefetch_related("competencies", "resources", "metric_values__definition"),
        period__path__owner=request.user,
        pk=pk,
    )
    return render(request, "formations/unit.html", {"unit": unit})


@login_required
def competency_new(request, unit_pk):
    unit = get_object_or_404(LearningUnit, period__path__owner=request.user, pk=unit_pk)
    form = CompetencyForm(request.POST or None, user=request.user, scope={"unit": unit})
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("formations:unit", pk=unit.pk)
    return render(request, "formations/form.html", {"form": form, "title": f"Nouvelle compétence · {unit.title}"})


@login_required
def progress_edit(request, competency_pk):
    competency = get_object_or_404(Competency, unit__period__path__owner=request.user, pk=competency_pk)
    progress, _ = ProgressRecord.objects.get_or_create(owner=request.user, competency=competency)
    form = ProgressForm(
        request.POST or None, instance=progress, scope={"owner": request.user, "competency": competency}
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("formations:unit", pk=competency.unit_id)
    return render(request, "formations/form.html", {"form": form, "title": f"Progression · {competency.title}"})


@login_required
def metric_definition_new(request, path_pk):
    path = get_object_or_404(LearningPath, owner=request.user, pk=path_pk)
    form = MetricDefinitionForm(request.POST or None, scope={"path": path})
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("formations:detail", pk=path.pk)
    return render(request, "formations/form.html", {"form": form, "title": f"Nouvelle métrique · {path.title}"})


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
        title="Supprimer ce module",
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
