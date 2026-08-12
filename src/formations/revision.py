"""Ce qu'il y aurait lieu de reprendre, et pourquoi.

L'application savait enregistrer où en était une compétence ; elle ne ramenait jamais vers
elle. Un état qu'on ne relit pas ne sert à rien : c'est le retour sur ce qui a été laissé
qui fait la différence entre un tableau de bord et un outil d'apprentissage.

Trois raisons de revenir, et rien d'autre :

* un objectif que l'étudiant s'est fixé et dont la date est passée — c'est lui qui l'a
  demandé, le lui rappeler n'est pas s'inviter dans son travail ;
* une évaluation qui approche sur une compétence pas encore acquise ;
* une autoévaluation ancienne sur une compétence qui n'est pas au bout — non pour
  supposer un oubli, mais parce qu'un niveau vieux de plusieurs mois ne décrit plus
  personne.

Le résultat est une liste que l'on consulte, jamais une notification qui interrompt : la
règle de la feuille de route — « l'outil doit rester calme » — vaut ici plus qu'ailleurs,
parce que c'est précisément le point où un outil de suivi devient harcelant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Assessment, Competency, ProgressRecord

# Au-delà, un niveau déclaré décrit surtout le passé. Huit semaines couvrent la moitié d'un
# semestre : assez pour qu'un chapitre ait vécu, pas assez pour qu'on l'ait perdu.
STALE_AFTER = timedelta(weeks=8)
# Une évaluation dans quinze jours est proche : c'est encore le moment de reprendre, et
# plus tôt la liste serait pleine de choses dont on ne peut rien faire aujourd'hui.
SOON = timedelta(days=15)


@dataclass(frozen=True, slots=True)
class Revision:
    record: ProgressRecord
    reason: str
    # Plus le rang est bas, plus c'est pressant. Sert au tri, pas à l'affichage : afficher
    # un score de priorité inviterait à le comparer, ce qui n'aurait aucun sens.
    rank: int

    @property
    def competency(self) -> Competency:
        return self.record.competency


def to_revisit(user, path, period=None, *, limit: int = 6) -> list[Revision]:
    """Les compétences qui appellent un retour, les plus pressantes d'abord."""
    records = list(
        ProgressRecord.objects.filter(owner=user, competency__path=path)
        .select_related("competency", "competency__path")
        .exclude(mastery_level=ProgressRecord.Mastery.MASTERED)
    )
    if period is not None:
        allowed = set(
            Competency.objects.filter(path=path)
            .filter(Q(period=period) | Q(units__period=period))
            .values_list("pk", flat=True)
        )
        records = [record for record in records if record.competency_id in allowed]
    if not records:
        return []

    upcoming = _upcoming_assessments(user, [record.competency_id for record in records])
    now = timezone.now()
    found: list[Revision] = []
    for record in records:
        assessment = upcoming.get(record.competency_id)
        if record.target_is_late:
            found.append(Revision(record, f"objectif « {record.target_label.lower()} » dépassé", rank=0))
        elif assessment is not None and record.mastery_level < ProgressRecord.Mastery.ACQUIRED:
            days = (assessment.scheduled_for.date() - timezone.localdate()).days
            when = "aujourd’hui" if days <= 0 else ("demain" if days == 1 else f"dans {days} jours")
            found.append(Revision(record, f"{assessment.title} {when}", rank=1))
        elif record.assessed_at is not None and now - record.assessed_at > STALE_AFTER:
            weeks = (now - record.assessed_at).days // 7
            found.append(Revision(record, f"autoévalué il y a {weeks} semaines", rank=2))
    found.sort(key=lambda revision: (revision.rank, revision.record.mastery_level, revision.competency.title))
    return found[:limit]


def _upcoming_assessments(user, competency_ids) -> dict[int, Assessment]:
    """La prochaine évaluation à venir de chaque compétence, quand il y en a une."""
    horizon = timezone.now() + SOON
    assessments = (
        Assessment.objects.filter(
            owner=user,
            status=Assessment.Status.PLANNED,
            scheduled_for__gte=timezone.now(),
            scheduled_for__lte=horizon,
            competencies__in=competency_ids,
        )
        .order_by("scheduled_for")
        .prefetch_related("competencies")
    )
    nearest: dict[int, Assessment] = {}
    for assessment in assessments:
        for competency in assessment.competencies.all():
            nearest.setdefault(competency.pk, assessment)
    return nearest


def suggest_from_result(user, assessment) -> tuple[list, list]:
    """Propose un niveau aux compétences évaluées, à partir de la note obtenue.

    Rend ``(appliquées, en attente)``. Les premières n'avaient aucun niveau déclaré : la
    proposition s'y est écrite, marquée comme suggérée. Les secondes en avaient un ; la
    proposition leur est présentée sans rien écrire, parce qu'une note ne prime pas sur
    l'appréciation de la personne qui l'a obtenue.
    """
    from .progression import level_from_result

    result = getattr(assessment, "result", None)
    if result is None:
        return [], []
    level = level_from_result(result)
    if level is None:
        return [], []

    applied, pending = [], []
    for competency in assessment.competencies.all():
        record, _ = ProgressRecord.objects.get_or_create(owner=user, competency=competency)
        record.competency = competency
        if record.suggest_level(level):
            applied.append(record)
        elif level > record.mastery_level:
            pending.append(record)
    return applied, pending
