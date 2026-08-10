from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    CompetencyForm,
    LearningPathForm,
    LearningUnitForm,
    MetricDefinitionForm,
    MetricValueForm,
    PeriodForm,
    ProgressForm,
)
from .models import Competency, LearningPath, LearningUnit, Period, ProgressRecord


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
def metric_value_new(request, unit_pk):
    unit = get_object_or_404(LearningUnit, period__path__owner=request.user, pk=unit_pk)
    form = MetricValueForm(request.POST or None, path=unit.period.path, scope={"unit": unit})
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("formations:unit", pk=unit.pk)
    return render(request, "formations/form.html", {"form": form, "title": f"Métrique · {unit.title}"})
