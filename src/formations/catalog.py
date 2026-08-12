"""Format portable et catalogue de formations.

Une maquette n'est pas un jeu de lignes SQL : c'est un document versionné, lisible et
validable avant d'écrire. Le même format sert aux modèles livrés avec MyENT, à l'export
d'une formation personnelle et à sa duplication.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils.text import slugify

from .models import (
    Competency,
    LearningGroup,
    LearningPath,
    LearningUnit,
    MetricDefinition,
    MetricValue,
    Period,
    ProgressRecord,
    UnitCompetency,
)
from .resource_services import sync_path_curated_resources

SCHEMA_NAME = "myent.learning-path"
SCHEMA_VERSION = 1
GUYANE_TEMPLATE = "licence-mathematiques-guyane-l3"


class CatalogError(ValueError):
    """Une maquette est illisible ou incohérente, sans exposer une erreur serveur."""


def _key(label: str, used: set[str]) -> str:
    base = slugify(label)[:60] or "element"
    candidate, suffix = base, 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _decimal(raw: Any, label: str) -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CatalogError(f"{label} doit être un nombre.") from exc
    if not value.is_finite():
        raise CatalogError(f"{label} doit être un nombre fini.")
    return value


def _text(value: Any, label: str, *, required: bool = True, maximum: int = 220) -> str:
    if not isinstance(value, str):
        raise CatalogError(f"{label} doit être un texte.")
    value = value.strip()
    if required and not value:
        raise CatalogError(f"{label} ne peut pas être vide.")
    if len(value) > maximum:
        raise CatalogError(f"{label} dépasse {maximum} caractères.")
    return value


def validate_catalog(data: Any) -> dict[str, Any]:
    """Valide le contrat public avant toute écriture et renvoie un aperçu."""
    if not isinstance(data, dict):
        raise CatalogError("Le fichier doit contenir un objet JSON.")
    if data.get("schema") != SCHEMA_NAME:
        raise CatalogError(f"Format inconnu : « {data.get('schema', '')} ».")
    if data.get("version") != SCHEMA_VERSION:
        raise CatalogError(
            f"Version non prise en charge : {data.get('version', 'absente')} (attendue : {SCHEMA_VERSION})."
        )
    formation = data.get("formation")
    if not isinstance(formation, dict):
        raise CatalogError("La rubrique « formation » est absente.")
    _text(formation.get("title"), "Le titre de la formation", maximum=180)

    metrics = data.get("metrics", [])
    periods = data.get("periods", [])
    competencies = data.get("competencies", [])
    if not all(isinstance(value, list) for value in (metrics, periods, competencies)):
        raise CatalogError("Les métriques, périodes et compétences doivent être des listes.")

    metric_keys: set[str] = set()
    for index, metric in enumerate(metrics, 1):
        if not isinstance(metric, dict):
            raise CatalogError(f"La métrique {index} est invalide.")
        key = _text(metric.get("key"), f"Clé de la métrique {index}", maximum=40)
        if key in metric_keys:
            raise CatalogError(f"La clé de métrique « {key} » est déclarée deux fois.")
        metric_keys.add(key)
        _text(metric.get("label"), f"Libellé de la métrique {index}", maximum=80)

    period_keys: set[str] = set()
    unit_keys: set[str] = set()
    groups_count = units_count = 0
    for period_index, period in enumerate(periods, 1):
        if not isinstance(period, dict):
            raise CatalogError(f"La période {period_index} est invalide.")
        period_key = _text(period.get("key"), f"Clé de la période {period_index}", maximum=80)
        if period_key in period_keys:
            raise CatalogError(f"La période « {period_key} » est déclarée deux fois.")
        period_keys.add(period_key)
        _text(period.get("title"), f"Titre de la période {period_index}", maximum=140)
        groups = period.get("groups", [])
        units = period.get("units", [])
        if not isinstance(groups, list) or not isinstance(units, list):
            raise CatalogError(f"Groupes ou matières invalides dans « {period_key} ».")
        local_groups: set[str] = set()
        for group in groups:
            if not isinstance(group, dict):
                raise CatalogError(f"Un regroupement de « {period_key} » est invalide.")
            group_key = _text(group.get("key"), "Clé du regroupement", maximum=80)
            if group_key in local_groups:
                raise CatalogError(f"Le regroupement « {group_key} » est déclaré deux fois.")
            local_groups.add(group_key)
            _text(group.get("title"), "Titre du regroupement", maximum=180)
        groups_count += len(groups)
        for unit in units:
            if not isinstance(unit, dict):
                raise CatalogError(f"Une matière de « {period_key} » est invalide.")
            unit_key = _text(unit.get("key"), "Clé de la matière", maximum=100)
            if unit_key in unit_keys:
                raise CatalogError(f"La matière « {unit_key} » est déclarée deux fois.")
            unit_keys.add(unit_key)
            _text(unit.get("title"), "Titre de la matière", maximum=180)
            if unit.get("group") and unit["group"] not in local_groups:
                raise CatalogError(f"Le regroupement « {unit['group']} » de « {unit_key} » n'existe pas.")
            values = unit.get("metrics", {})
            if not isinstance(values, dict) or not set(values).issubset(metric_keys):
                raise CatalogError(f"Une métrique de « {unit_key} » n'est pas déclarée.")
            for metric_key, raw in values.items():
                _decimal(raw, f"Valeur {metric_key} de {unit_key}")
        units_count += len(units)

    competency_keys: set[str] = set()
    links_count = 0
    for index, competency in enumerate(competencies, 1):
        if not isinstance(competency, dict):
            raise CatalogError(f"La compétence {index} est invalide.")
        key = _text(competency.get("key"), f"Clé de la compétence {index}", maximum=100)
        if key in competency_keys:
            raise CatalogError(f"La compétence « {key} » est déclarée deux fois.")
        competency_keys.add(key)
        _text(competency.get("title"), f"Titre de la compétence {index}")
        if competency.get("period") and competency["period"] not in period_keys:
            raise CatalogError(f"La période de la compétence « {key} » n'existe pas.")
        links = competency.get("units", [])
        if not isinstance(links, list):
            raise CatalogError(f"Les matières de la compétence « {key} » sont invalides.")
        for link in links:
            if not isinstance(link, dict) or link.get("unit") not in unit_keys:
                raise CatalogError(f"Une matière de la compétence « {key} » n'existe pas.")
        if competency.get("planned_hours") not in (None, ""):
            if _decimal(competency["planned_hours"], f"Temps prévu de {key}") < 0:
                raise CatalogError(f"Le temps prévu de « {key} » ne peut pas être négatif.")
        links_count += len(links)

    return {
        "title": formation["title"],
        "periods": len(periods),
        "groups": groups_count,
        "units": units_count,
        "competencies": len(competencies),
        "links": links_count,
        "metrics": len(metrics),
        "metadata": data.get("metadata", {}),
    }


def _available_title(owner, title: str) -> str:
    """Évite deux cartes indiscernables sans imposer une contrainte historique."""
    if not LearningPath.objects.filter(owner=owner, title=title).exists():
        return title
    stem, suffix = title, 2
    while LearningPath.objects.filter(owner=owner, title=f"{stem} ({suffix})").exists():
        suffix += 1
    return f"{stem} ({suffix})"


@transaction.atomic
def import_catalog(data: dict[str, Any], *, owner, title: str = "", academic_year: str = "") -> LearningPath:
    """Crée une copie autonome après validation complète du document."""
    validate_catalog(data)
    info = data["formation"]
    chosen_title = _available_title(owner, (title or info["title"]).strip())
    path = LearningPath.objects.create(
        owner=owner,
        title=chosen_title,
        training_type=str(info.get("training_type", ""))[:120],
        level_label=str(info.get("level_label", ""))[:120],
        academic_year=(academic_year or str(info.get("academic_year", "")))[:20],
        description=str(info.get("description", "")),
        status=LearningPath.Status.ACTIVE,
        # Absent des documents de la version 1 : une maquette qui ne se prononce pas
        # garde le comportement par défaut, les paliers de temps actifs.
        time_suggests_level=bool(info.get("time_suggests_level", True)),
    )
    metrics = {}
    for order, item in enumerate(data.get("metrics", []), 1):
        metrics[item["key"]] = MetricDefinition.objects.create(
            path=path,
            key=item["key"],
            label=item["label"],
            unit_label=str(item.get("unit_label", ""))[:20],
            order=int(item.get("order", order)),
            min_value=item.get("min_value"),
            max_value=item.get("max_value"),
            decimal_places=int(item.get("decimal_places", 2)),
        )
    periods, units = {}, {}
    for period_order, item in enumerate(data.get("periods", []), 1):
        period = Period.objects.create(path=path, title=item["title"], order=int(item.get("order", period_order)))
        periods[item["key"]] = period
        groups = {
            group["key"]: LearningGroup.objects.create(
                period=period,
                title=group["title"],
                code=str(group.get("code", ""))[:40],
                kind=str(group.get("kind", ""))[:40],
                order=int(group.get("order", group_order)),
            )
            for group_order, group in enumerate(item.get("groups", []), 1)
        }
        for unit_order, source in enumerate(item.get("units", []), 1):
            unit = LearningUnit.objects.create(
                period=period,
                group=groups.get(source.get("group")),
                title=source["title"],
                description=str(source.get("description", "")),
                order=int(source.get("order", unit_order)),
            )
            units[source["key"]] = unit
            for metric_key, raw in source.get("metrics", {}).items():
                MetricValue.objects.create(definition=metrics[metric_key], unit=unit, value=_decimal(raw, metric_key))

    for competency_order, source in enumerate(data.get("competencies", []), 1):
        competency = Competency.objects.create(
            path=path,
            period=periods.get(source.get("period")),
            title=source["title"],
            description=str(source.get("description", "")),
            order=int(source.get("order", competency_order)),
        )
        for link_order, link in enumerate(source.get("units", []), 1):
            UnitCompetency.objects.create(
                unit=units[link["unit"]],
                competency=competency,
                order=int(link.get("order", link_order)),
                is_primary=bool(link.get("is_primary", True)),
                local_objective=str(link.get("local_objective", ""))[:240],
            )
        planned = source.get("planned_hours")
        if planned not in (None, ""):
            ProgressRecord.objects.create(owner=owner, competency=competency, planned_hours=_decimal(planned, "Temps"))

    current_key = info.get("current_period")
    path.current_period = periods.get(current_key) or next(iter(periods.values()), None)
    path.weight_metric = metrics.get(info.get("weight_metric"))
    path.full_clean()
    path.save(update_fields=["current_period", "weight_metric", "updated_at"])
    # Une formation importée doit être immédiatement utilisable : les parcours
    # pédagogiques connus sont présents dans la bibliothèque, pas seulement suggérés sur
    # une page que l'étudiant devrait ouvrir compétence par compétence.
    sync_path_curated_resources(owner=owner, path=path)
    return path


def export_catalog(path: LearningPath) -> dict[str, Any]:
    """Exporte la structure et le travail prévu, jamais les notes ni le temps réalisé."""
    used_periods: set[str] = set()
    used_units: set[str] = set()
    used_competencies: set[str] = set()
    period_keys, unit_keys = {}, {}
    periods_data = []
    for period in path.periods.prefetch_related("groups", "units__metric_values__definition").all():
        period_key = _key(period.title, used_periods)
        period_keys[period.pk] = period_key
        used_groups: set[str] = set()
        group_keys = {group.pk: _key(group.title, used_groups) for group in period.groups.all()}
        units_data = []
        for unit in period.units.all():
            unit_key = _key(f"{period.title}-{unit.title}", used_units)
            unit_keys[unit.pk] = unit_key
            units_data.append(
                {
                    "key": unit_key,
                    "title": unit.title,
                    "description": unit.description,
                    "order": unit.order,
                    "group": group_keys.get(unit.group_id),
                    "metrics": {value.definition.key: str(value.value) for value in unit.metric_values.all()},
                }
            )
        periods_data.append(
            {
                "key": period_key,
                "title": period.title,
                "order": period.order,
                "groups": [
                    {
                        "key": group_keys[group.pk],
                        "title": group.title,
                        "code": group.code,
                        "kind": group.kind,
                        "order": group.order,
                    }
                    for group in period.groups.all()
                ],
                "units": units_data,
            }
        )
    progress = {
        progress_record.competency_id: progress_record
        for competency in path.competencies.prefetch_related("progress_records")
        for progress_record in competency.progress_records.all()
        if progress_record.owner_id == path.owner_id
    }
    competencies_data = []
    for competency in path.competencies.prefetch_related("unit_links").all():
        record = progress.get(competency.pk)
        competencies_data.append(
            {
                "key": _key(competency.title, used_competencies),
                "title": competency.title,
                "description": competency.description,
                "order": competency.order,
                "period": period_keys.get(competency.period_id),
                "planned_hours": str(record.planned_hours) if record else "",
                "units": [
                    {
                        "unit": unit_keys[link.unit_id],
                        "order": link.order,
                        "is_primary": link.is_primary,
                        "local_objective": link.local_objective,
                    }
                    for link in competency.unit_links.all()
                ],
            }
        )
    return {
        "schema": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "metadata": {"exported_on": date.today().isoformat(), "generator": "MyENT"},
        "formation": {
            "title": path.title,
            "training_type": path.training_type,
            "level_label": path.level_label,
            "academic_year": path.academic_year,
            "description": path.description,
            "current_period": period_keys.get(path.current_period_id),
            "weight_metric": path.weight_metric.key if path.weight_metric_id else None,
            "time_suggests_level": path.time_suggests_level,
        },
        "metrics": [
            {
                "key": metric.key,
                "label": metric.label,
                "unit_label": metric.unit_label,
                "order": metric.order,
                "min_value": str(metric.min_value) if metric.min_value is not None else None,
                "max_value": str(metric.max_value) if metric.max_value is not None else None,
                "decimal_places": metric.decimal_places,
            }
            for metric in path.metric_definitions.all()
        ],
        "periods": periods_data,
        "competencies": competencies_data,
    }


def guyane_catalog() -> dict[str, Any]:
    """Traduit la maquette historique vers le format public, sans la dupliquer."""
    from .management.commands.load_licence_guyane import COLONNES, EFFORT, PROGRAMME, readable_share

    used_units: set[str] = set()
    periods_data, competency_plan = [], OrderedDict()
    for period_order, (period_title, subjects) in enumerate(PROGRAMME.items(), 5):
        period_key = slugify(period_title)
        group_titles = list(dict.fromkeys(subject[1] for subject in subjects))
        group_keys = {title: slugify(title) for title in group_titles}
        units_data = []
        for unit_order, (title, group, hours, ects, nature, competencies) in enumerate(subjects, 1):
            unit_key = _key(f"{period_title}-{title}", used_units)
            personal = (Decimal(hours) * EFFORT[nature]).quantize(Decimal("1"))
            units_data.append(
                {
                    "key": unit_key,
                    "title": title,
                    "description": nature,
                    "order": unit_order,
                    "group": group_keys[group],
                    "metrics": {"ects": str(ects), "encadre": str(hours), "perso": str(personal)},
                }
            )
            share = readable_share(personal, len(competencies))
            for link_order, competency_title in enumerate(competencies, 1):
                entry = competency_plan.setdefault(
                    competency_title,
                    {"periods": set(), "units": [], "planned_hours": Decimal(0)},
                )
                entry["periods"].add(period_key)
                entry["units"].append({"unit": unit_key, "order": link_order, "is_primary": True})
                entry["planned_hours"] += share
        periods_data.append(
            {
                "key": period_key,
                "title": period_title,
                "order": period_order,
                "groups": [
                    {"key": group_keys[title], "title": title, "kind": "UE", "order": order}
                    for order, title in enumerate(group_titles, 1)
                ],
                "units": units_data,
            }
        )
    data = {
        "schema": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "metadata": {
            "name": "Licence 3 Mathématiques · Université de Guyane",
            "source": "https://www.univ-guyane.fr/choisir-sa-formation/dfr-sciences-et-technologies/licence-mathematiques/",
            "notice": (
                "Les ECTS sont repris tels que publiés. Le travail personnel et le découpage en compétences "
                "sont des estimations modifiables, pas des données officielles."
            ),
        },
        "formation": {
            "title": "Licence 3 Mathématiques",
            "training_type": "Licence Mathématiques · Université de Guyane",
            "level_label": "L3",
            "description": "Maquette de départ personnalisable après import.",
            "current_period": next(iter(periods_data), {}).get("key"),
            "weight_metric": "ects",
        },
        "metrics": [
            {
                "key": key,
                "label": label,
                "unit_label": unit_label,
                "order": order,
                "min_value": "0",
                "decimal_places": 0,
            }
            for order, (key, label, unit_label) in enumerate(COLONNES, 1)
        ],
        "periods": periods_data,
        "competencies": [
            {
                "key": f"competence-{order}",
                "title": title,
                "order": order,
                "period": next(iter(entry["periods"])) if len(entry["periods"]) == 1 else None,
                "planned_hours": str(entry["planned_hours"]),
                "units": entry["units"],
            }
            for order, (title, entry) in enumerate(competency_plan.items(), 1)
        ],
    }
    validate_catalog(data)
    return data


def templates() -> list[dict[str, Any]]:
    data = guyane_catalog()
    return [{"slug": GUYANE_TEMPLATE, "data": data, "preview": validate_catalog(data)}]


def get_template(slug: str) -> dict[str, Any]:
    for item in templates():
        if item["slug"] == slug:
            return item
    raise CatalogError("Modèle de formation inconnu.")
