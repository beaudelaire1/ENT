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

from .models import Competency, LearningUnit, MetricDefinition, MetricValue, ProgressRecord, UnitCompetency

# Colonnes présentes quelle que soit la formation : intitulé, travail estimé, temps réel,
# niveau de maîtrise, progression, commentaires.
FIXED_COLUMNS = 6


def ensure_progress_records(user, path) -> None:
    """Garantit une ligne de suivi par compétence du parcours."""
    competencies = Competency.objects.filter(path=path)
    tracked = set(
        ProgressRecord.objects.filter(owner=user, competency__in=competencies).values_list("competency_id", flat=True)
    )
    missing = [
        ProgressRecord(owner=user, competency=competency) for competency in competencies if competency.pk not in tracked
    ]
    if missing:
        ProgressRecord.objects.bulk_create(missing)


def tracked_records(user, path):
    """Les lignes de suivi du parcours, une par compétence.

    L'ordre suit la période puis l'ordre déclaré de la compétence. Il ne passe plus par la
    matière : une compétence peut en concerner plusieurs, et trier par un rattachement
    devenu multiple n'aurait plus de sens. La grille se charge du placement.
    """
    return (
        ProgressRecord.objects.filter(owner=user, competency__path=path)
        .select_related("competency__period")
        .order_by(
            "competency__period__order",
            "competency__period__title",
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


def _primary_unit_by_competency(path) -> dict[int, int]:
    """Où chaque compétence est saisie dans la grille.

    Une compétence partagée entre deux matières ne peut pas être saisie deux fois : il n'y
    a qu'une ligne de suivi, et deux formulaires pour la même ligne s'écraseraient l'un
    l'autre. Elle est donc saisissable sous une seule matière — la première où elle est
    déclarée principale — et rappelée en lecture sous les autres.
    """
    chosen: dict[int, int] = {}
    links = (
        UnitCompetency.objects.filter(unit__period__path=path)
        .select_related("unit__period")
        .order_by("-is_primary", "unit__period__order", "unit__order", "order", "pk")
    )
    for link in links:
        chosen.setdefault(link.competency_id, link.unit_id)
    return chosen


def _row(link, form, *, editable: bool, others: list, primary_label: str = "") -> dict:
    return {
        "competency": link.competency,
        "link": link,
        "form": form,
        "editable": editable,
        # Les autres matières où la compétence se travaille, pour le dire là où elle est
        # affichée en lecture seule.
        "shared_with": others,
        # Où elle se saisit, quand ce n'est pas ici : sans cette indication, une ligne en
        # lecture seule ressemble à un bogue.
        "primary_label": primary_label,
    }


def build_tracking_grid(path, formset, submitted=None):
    """Assemble la grille : les colonnes déclarées, puis les lignes par période.

    La structure vient de la base et non du formset : une matière sans compétence doit
    quand même apparaître dans la grille, avec ses métriques et une invitation à la
    remplir.

    Les matières sont regroupées par UE quand la formation en déclare, et une compétence
    transversale — rattachée au parcours sans matière — apparaît dans une section à part
    plutôt que de disparaître de l'écran.

    ``submitted`` est le POST rejeté. Les cases reprennent alors ce qui a été tapé, y
    compris ce qui était invalide : la corriger suppose de la voir, et recharger la
    valeur d'origine effacerait tout le travail de saisie.
    """
    definitions = list(MetricDefinition.objects.filter(path=path).order_by("order", "label"))
    metrics = _metrics_by_unit(path)
    forms_by_competency = {form.instance.competency_id: form for form in formset}
    primary = _primary_unit_by_competency(path)

    links_by_unit: dict[int, list] = {}
    units_by_competency: dict[int, list] = {}
    unit_titles: dict[int, str] = {}
    for link in (
        UnitCompetency.objects.filter(unit__period__path=path)
        .select_related("competency", "unit__period")
        .order_by("order", "competency__order", "competency__title")
    ):
        links_by_unit.setdefault(link.unit_id, []).append(link)
        units_by_competency.setdefault(link.competency_id, []).append(link.unit)
        # La période fait partie du repère : deux matières peuvent porter le même
        # intitulé — « Oraux de mathématiques » existe aux deux semestres — et « se
        # saisit sous Oraux de mathématiques » ne dirait alors pas laquelle.
        unit_titles[link.unit_id] = f"{link.unit.title} ({link.unit.period.title})"

    periods = []
    linked = set(units_by_competency)
    for period in path.periods.prefetch_related("units__group", "groups"):
        groups: dict[int | None, dict] = {}
        for unit in period.units.all():
            rows = []
            for link in links_by_unit.get(unit.pk, []):
                form = forms_by_competency.get(link.competency_id)
                if form is None:
                    continue
                others = [
                    unit_titles[other.pk] for other in units_by_competency[link.competency_id] if other.pk != unit.pk
                ]
                owner_unit = primary.get(link.competency_id)
                rows.append(
                    _row(
                        link,
                        form,
                        editable=owner_unit == unit.pk,
                        others=others,
                        primary_label=unit_titles.get(owner_unit, ""),
                    )
                )
            unit_metrics = metrics.get(unit.pk, {})
            entry = {
                "unit": unit,
                # Alignée sur `definitions` : une case saisissable par colonne.
                "cells": [
                    _cell(unit, definition, unit_metrics.get(definition.key), submitted) for definition in definitions
                ],
                "rows": rows,
                # Les totaux ne comptent qu'une fois une compétence partagée : sinon un
                # même travail serait additionné dans deux matières.
                "totals": _totals([row for row in rows if row["editable"]]),
            }
            bucket = groups.setdefault(unit.group_id, {"group": unit.group, "units": []})
            bucket["units"].append(entry)

        ordered_groups = sorted(
            groups.values(),
            key=lambda bucket: (bucket["group"].order, bucket["group"].title) if bucket["group"] else (-1, ""),
        )
        units = [entry for bucket in ordered_groups for entry in bucket["units"]]
        # Compétences de la période qui ne sont rattachées à aucune matière.
        loose = [
            _row_from_competency(record, forms_by_competency)
            for record in period.competencies.all()
            if record.pk not in linked and record.pk in forms_by_competency
        ]
        periods.append(
            {
                "period": period,
                "groups": ordered_groups,
                "units": units,
                "loose": loose,
                "totals": _totals([row for row in units for row in row["rows"] if row["editable"]] + loose),
            }
        )

    # Compétences du parcours sans période ni matière : elles existent, elles doivent se
    # saisir quelque part.
    orphans = [
        _row_from_competency(record, forms_by_competency)
        for record in Competency.objects.filter(path=path, period__isnull=True).order_by("order", "title")
        if record.pk not in linked and record.pk in forms_by_competency
    ]

    return {
        "definitions": definitions,
        "periods": periods,
        "orphans": orphans,
        "orphan_totals": _totals(orphans),
        "metric_count": len(definitions),
        "column_count": len(definitions) + FIXED_COLUMNS,
    }


def _row_from_competency(competency, forms_by_competency) -> dict:
    """Ligne d'une compétence sans matière : saisissable, sans lien ni partage."""
    return {
        "competency": competency,
        "link": None,
        "form": forms_by_competency[competency.pk],
        "editable": True,
        "shared_with": [],
    }
