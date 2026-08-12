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

from dataclasses import dataclass
from decimal import Decimal

from django.db import connection, transaction

from .models import Competency, LearningUnit, MetricDefinition, MetricValue, ProgressRecord

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


def metric_field_name(unit, definition) -> str:
    return f"metric_{unit.pk}_{definition.pk}"


@dataclass(frozen=True)
class MetricEdit:
    """Une écriture décidée mais pas encore faite.

    ``value`` à ``None`` signifie que la case a été vidée : la valeur doit disparaître.
    C'est ainsi qu'on distingue « zéro heure de TP » d'une matière où la colonne n'a pas
    de sens.
    """

    definition: MetricDefinition
    unit: LearningUnit
    value: Decimal | None


def validate_metric_values(path, data) -> tuple[list[MetricEdit], list[str]]:
    """Lit les cases chiffrées de la grille et n'écrit rien.

    Les chiffres étaient auparavant saisis un par un, chacun sur sa propre page : cinq
    colonnes pour sept matières faisaient trente-cinq formulaires pour installer un
    semestre. Ils se remplissent maintenant là où on les lit.

    Cette fonction ne touche pas la base. Elle rend la liste des écritures à faire et la
    liste des erreurs ; l'appelant n'applique les premières que si la seconde est vide.
    Auparavant validation et écriture étaient entremêlées : une trente-cinquième case
    illisible laissait les trente-quatre précédentes enregistrées, sous un bandeau qui
    affirmait le contraire.
    """
    definitions = list(MetricDefinition.objects.filter(path=path))
    units = list(LearningUnit.objects.filter(period__path=path).select_related("period"))

    edits: list[MetricEdit] = []
    errors: list[str] = []
    for unit in units:
        for definition in definitions:
            name = metric_field_name(unit, definition)
            if name not in data:
                continue
            value, error = definition.parse(data.get(name) or "")
            if error:
                errors.append(f"{unit.title} · {definition.label} : {error}")
                continue
            edits.append(MetricEdit(definition=definition, unit=unit, value=value))
    return edits, errors


def apply_metric_values(path, edits: list[MetricEdit]) -> None:
    """Écrit les valeurs validées. À appeler dans une transaction.

    Le verrou porte sur toutes les valeurs du parcours : la grille s'enregistre d'un
    bloc, deux envois simultanés doivent se suivre et non s'entrelacer.
    """
    if not edits:
        return
    if connection.features.has_select_for_update:
        # SQLite ne connaît pas SELECT ... FOR UPDATE ; il sérialise déjà les écritures.
        list(MetricValue.objects.select_for_update().filter(definition__path=path).values_list("pk", flat=True))
    for edit in edits:
        if edit.value is None:
            MetricValue.objects.filter(definition=edit.definition, unit=edit.unit).delete()
        else:
            MetricValue.objects.update_or_create(
                definition=edit.definition, unit=edit.unit, defaults={"value": edit.value}
            )


def save_tracking(path, formset, data) -> tuple[bool, list[str]]:
    """Enregistre la grille entière — chiffres des matières et progression — ou rien.

    Rend ``(enregistré, erreurs sur les chiffres)``. Le formset porte les siennes.

    Les deux ensembles sont validés avant que l'un des deux soit écrit : une case
    chiffrée illisible empêche l'enregistrement des niveaux de maîtrise, et un niveau
    refusé empêche celui des chiffres.
    """
    edits, errors = validate_metric_values(path, data)
    # ``is_valid()`` est appelé même si les chiffres sont déjà fautifs : l'utilisateur
    # doit voir toutes ses erreurs d'un coup, pas les découvrir l'une après l'autre.
    formset_ok = formset.is_valid()
    if errors or not formset_ok:
        return False, errors
    with transaction.atomic():
        apply_metric_values(path, edits)
        formset.save()
    return True, []


def format_metric(value: Decimal | None) -> str:
    """Rend la valeur telle qu'elle est stockée, sans arrondi d'affichage.

    ``floatformat`` ramenait 7,25 à « 7,3 » dans la case de saisie : renvoyer le
    formulaire réécrivait alors la valeur arrondie en base, sans que personne ne l'ait
    demandé. On écrit donc le chiffre exact, débarrassé de ses seuls zéros inutiles.
    """
    if value is None:
        return ""
    return format(value.normalize(), "f")


def _cell(unit, definition, stored: Decimal | None, submitted) -> dict:
    name = metric_field_name(unit, definition)
    display = format_metric(stored)
    if submitted is not None and name in submitted:
        display = (submitted.get(name) or "").strip()
    return {"name": name, "value": stored, "display": display, "definition": definition}


def build_tracking_grid(path, formset, submitted=None):
    """Assemble la grille : les colonnes déclarées, puis les lignes par période.

    La structure vient de la base et non du formset : une matière sans compétence doit
    quand même apparaître dans la grille, avec ses métriques et une invitation à la
    remplir.

    ``submitted`` est le POST rejeté. Les cases reprennent alors ce qui a été tapé, y
    compris ce qui était invalide : la corriger suppose de la voir, et recharger la
    valeur d'origine effacerait tout le travail de saisie.
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
                    # Alignée sur `definitions` : une case saisissable par colonne.
                    "cells": [
                        _cell(unit, definition, unit_metrics.get(definition.key), submitted)
                        for definition in definitions
                    ],
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
