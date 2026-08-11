"""Construction de la grille de suivi de compétences.

La page reprend la structure du tableau de suivi : une ligne par matière portant ses
métriques, puis une ligne par compétence portant le niveau de maîtrise et les heures.

Les colonnes chiffrées ne sont pas figées : ce sont les MetricDefinition du parcours.
Une L3 déclare Coefficient/ECTS/CM/TD/TP, une formation professionnelle déclarera ce
qu’elle veut, et la grille suit.

Les totaux d’une matière ne sont pas saisis mais calculés à partir de ses compétences.
Le prototype d’origine laissait ces deux niveaux se contredire ; ici la ligne de matière
est toujours la somme de ce qu’elle contient.
"""

from __future__ import annotations

from decimal import Decimal

from .models import Competency, MetricDefinition, MetricValue, ProgressRecord

# Colonnes présentes quelle que soit la formation : intitulé, travail estimé, temps réel,
# niveau de maîtrise, progression, commentaires.
FIXED_COLUMNS = 6


def ensure_progress_records(user, path) -> None:
    """Garantit une ligne de suivi par compétence du parcours."""
    competencies = Competency.objects.filter(unit__period__path=path)
    tracked = set(
        ProgressRecord.objects.filter(owner=user, competency__in=competencies).values_list("competency_id", flat=True)
    )
    missing = [
        ProgressRecord(owner=user, competency=competency) for competency in competencies if competency.pk not in tracked
    ]
    if missing:
        ProgressRecord.objects.bulk_create(missing)


def tracked_records(user, path):
    return (
        ProgressRecord.objects.filter(owner=user, competency__unit__period__path=path)
        .select_related("competency__unit__period")
        .order_by(
            "competency__unit__period__order",
            "competency__unit__period__title",
            "competency__unit__order",
            "competency__unit__title",
            "competency__order",
            "competency__title",
        )
    )


def _metrics_by_unit(path) -> dict[int, dict[str, Decimal]]:
    values = MetricValue.objects.filter(definition__path=path).select_related("definition")
    metrics: dict[int, dict[str, Decimal]] = {}
    for value in values:
        metrics.setdefault(value.unit_id, {})[value.definition.key] = value.value
    return metrics


def _totals(rows):
    planned = sum((row["form"].instance.planned_hours or 0) for row in rows)
    actual = sum((row["form"].instance.actual_hours or 0) for row in rows)
    levels = [row["form"].instance.mastery_level or 0 for row in rows]
    percent = round(sum(levels) * 100 / (4 * len(levels))) if levels else 0
    return {"planned": planned, "actual": actual, "percent": percent}


def build_tracking_grid(path, formset):
    """Assemble la grille : les colonnes déclarées, puis les lignes par période.

    La structure vient de la base et non du formset : une matière sans compétence doit
    quand même apparaître dans la grille, avec ses métriques et une invitation à la
    remplir.
    """
    definitions = list(MetricDefinition.objects.filter(path=path).order_by("order", "label"))
    metrics = _metrics_by_unit(path)
    forms_by_competency = {form.instance.competency_id: form for form in formset}

    periods = []
    for period in path.periods.prefetch_related("units__competencies"):
        units = []
        for unit in period.units.all():
            rows = [
                {"competency": competency, "form": forms_by_competency[competency.pk]}
                for competency in unit.competencies.all()
                if competency.pk in forms_by_competency
            ]
            unit_metrics = metrics.get(unit.pk, {})
            units.append(
                {
                    "unit": unit,
                    # Alignée sur `definitions` : une case par colonne, vide si non renseignée.
                    "cells": [unit_metrics.get(definition.key) for definition in definitions],
                    "rows": rows,
                    "totals": _totals(rows),
                }
            )
        all_rows = [row for unit in units for row in unit["rows"]]
        periods.append({"period": period, "units": units, "totals": _totals(all_rows)})

    return {
        "definitions": definitions,
        "periods": periods,
        "metric_count": len(definitions),
        "column_count": len(definitions) + FIXED_COLUMNS,
    }
