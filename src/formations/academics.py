"""Moyennes, et ce qu'elles ne disent pas.

Une moyenne affichée sans sa méthode est un chiffre qu'on ne peut ni vérifier ni
contester. Chaque calcul rend donc trois choses : la valeur, la phrase qui décrit
comment elle a été obtenue, et la liste de ce qui manquait.

Trois refus explicites, qui suivent le plan :

* aucune compensation n'est appliquée d'office — compenser ou non est une règle
  d'établissement, pas une propriété des nombres ;
* une absence ne devient jamais un zéro : elle est signalée et écartée, parce que la
  transformer en note inventerait un résultat ;
* rien ne conclut sur la validation d'un diplôme. L'outil aide à se situer, pas à
  prononcer un verdict que seul un jury peut rendre.

La moyenne de période a besoin d'un poids par matière. Aucun n'est deviné : la formation
désigne la colonne de suivi qui le porte — ECTS, coefficient, ce qu'elle veut. Sans ce
choix, la moyenne n'est pas calculée et l'écran dit pourquoi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .models import Assessment, AssessmentResult, MetricValue

TWENTY = Decimal("20")


@dataclass(frozen=True)
class Average:
    """Une moyenne, sa méthode et ses réserves."""

    value: Decimal | None
    counted: int = 0
    weight: Decimal = Decimal(0)
    method: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return self.value is not None


def _graded(results) -> list[AssessmentResult]:
    return [result for result in results if result.ratio is not None]


def assessment_average(results: list[AssessmentResult], *, subject: str) -> Average:
    """Moyenne pondérée sur 20 d'une liste de résultats.

    Le coefficient vient de l'évaluation ; une évaluation de coefficient nul est écartée
    du calcul et le dit, plutôt que d'y entrer pour rien.
    """
    warnings: list[str] = []
    graded = _graded(results)
    absent = [result for result in results if result.absent]
    if absent:
        warnings.append(
            f"{len(absent)} absence{'s' if len(absent) > 1 else ''} écartée{'s' if len(absent) > 1 else ''} "
            "du calcul : une absence n'est pas un zéro."
        )
    missing = [result for result in results if not result.absent and result.score is None]
    if missing:
        warnings.append(f"{len(missing)} évaluation(s) sans note ne sont pas comptées.")

    weighted = [(result, result.assessment.coefficient) for result in graded]
    ignored = [result for result, coefficient in weighted if coefficient == 0]
    if ignored:
        warnings.append(f"{len(ignored)} évaluation(s) de coefficient nul sont exclues.")
    weighted = [(result, coefficient) for result, coefficient in weighted if coefficient > 0]

    if not weighted:
        return Average(
            value=None,
            method=f"Aucune note exploitable pour {subject}.",
            warnings=warnings,
        )

    total_weight = sum((coefficient for _result, coefficient in weighted), Decimal(0))
    total = sum((result.ratio * TWENTY * coefficient for result, coefficient in weighted), Decimal(0))
    value = (total / total_weight).quantize(Decimal("0.01"))
    coefficients = ", ".join(f"{result.assessment.title} × {coefficient:f}" for result, coefficient in weighted)
    return Average(
        value=value,
        counted=len(weighted),
        weight=total_weight,
        method=(
            f"Moyenne pondérée de {len(weighted)} note(s) ramenée(s) sur 20, pour {subject} : {coefficients}. "
            f"Somme des coefficients : {total_weight:f}."
        ),
        warnings=warnings,
    )


def unit_average(user, unit) -> Average:
    """Moyenne d'une matière, à partir des évaluations qui lui sont rattachées."""
    results = list(
        AssessmentResult.objects.filter(assessment__owner=user, assessment__unit=unit).select_related("assessment")
    )
    total = Assessment.objects.filter(owner=user, unit=unit).exclude(status=Assessment.Status.CANCELLED).count()
    average = assessment_average(results, subject=unit.title)
    if total and not results:
        return Average(
            value=None,
            method=f"{total} évaluation(s) prévue(s) pour {unit.title}, aucun résultat saisi.",
            warnings=average.warnings,
        )
    return average


def weight_for_unit(path, unit) -> Decimal | None:
    """Le poids d'une matière, lu dans la colonne que la formation a désignée."""
    if path.weight_metric_id is None:
        return None
    value = MetricValue.objects.filter(definition_id=path.weight_metric_id, unit=unit).values_list("value", flat=True)
    return value[0] if value else None


def period_average(user, period) -> Average:
    """Moyenne d'une période, pondérée par la colonne désignée par la formation.

    Sans colonne de pondération, le calcul n'est pas tenté : additionner des matières de
    poids inconnus produirait un chiffre arbitraire.
    """
    path = period.path
    units = list(period.units.all())
    if path.weight_metric_id is None:
        return Average(
            value=None,
            method="Aucune colonne de pondération n'est désignée pour cette formation.",
            warnings=[
                "Désignez la colonne qui porte le poids des matières — ECTS, coefficient — "
                "pour qu'une moyenne de période puisse être calculée."
            ],
        )

    label = path.weight_metric.label
    warnings: list[str] = []
    parts: list[tuple[str, Decimal, Decimal]] = []
    # Les moyennes sont calculées une fois et retenues : la liste des matières notées, plus
    # bas, les redemandait toutes, ce qui doublait le nombre de requêtes d'un écran affiché
    # à chaque ouverture du tableau de bord.
    averages = {unit.pk: unit_average(user, unit) for unit in units}
    # Les poids arrivent en une requête plutôt qu'une par matière.
    weights = dict(
        MetricValue.objects.filter(definition_id=path.weight_metric_id, unit__in=units).values_list("unit_id", "value")
    )
    for unit in units:
        average = averages[unit.pk]
        if not average.exists:
            continue
        weight = weights.get(unit.pk)
        if weight is None:
            warnings.append(f"{unit.title} : aucun {label} renseigné, la matière est écartée.")
            continue
        if weight <= 0:
            warnings.append(f"{unit.title} : {label} nul, la matière est écartée.")
            continue
        parts.append((unit.title, average.value, weight))

    graded_units = [unit for unit in units if averages[unit.pk].exists]
    if not parts:
        return Average(
            value=None,
            method=f"Aucune matière de {period.title} ne réunit à la fois une moyenne et un {label}.",
            warnings=warnings,
        )
    if len(parts) < len(graded_units):
        warnings.append(
            f"{len(graded_units) - len(parts)} matière(s) notée(s) sont absentes du calcul, faute de {label}."
        )

    total_weight = sum((weight for _title, _value, weight in parts), Decimal(0))
    total = sum((value * weight for _title, value, weight in parts), Decimal(0))
    detail = ", ".join(f"{title} {value:f} × {weight:f}" for title, value, weight in parts)
    return Average(
        value=(total / total_weight).quantize(Decimal("0.01")),
        counted=len(parts),
        weight=total_weight,
        method=(
            f"Moyenne de {period.title} pondérée par {label} : {detail}. "
            f"Total des poids : {total_weight:f}. Aucune compensation n'est appliquée."
        ),
        warnings=warnings,
    )


def struggling_competencies(user, assessment, *, limit=None):
    """Les compétences évaluées que l'étudiant ne déclare pas acquises.

    Sert à préparer une évaluation à venir, puis à décider quoi reprendre après un
    résultat décevant. La sélection ne juge pas : elle reprend le niveau déclaré.
    """
    from .models import ProgressRecord

    competencies = list(assessment.competencies.all())
    if not competencies:
        return []
    records = {
        record.competency_id: record
        for record in ProgressRecord.objects.filter(owner=user, competency__in=competencies)
    }
    weak = [
        {"competency": competency, "record": records.get(competency.pk)}
        for competency in competencies
        if records.get(competency.pk) is None or records[competency.pk].mastery_level < ProgressRecord.Mastery.ACQUIRED
    ]
    weak.sort(key=lambda row: (row["record"].mastery_level if row["record"] else 0, row["competency"].title))
    return weak[:limit] if limit else weak
