"""Fabriques partagées par les tests des formations.

Créer une compétence demande maintenant deux objets : la compétence, rattachée à la
formation, et son lien vers la matière où elle se travaille. Le geste courant — « une
compétence dans cette matière » — tient donc en une fonction, pour que les tests parlent
de ce qu'ils vérifient et non de la mécanique du modèle.
"""

from __future__ import annotations

from formations.models import Competency, UnitCompetency


def competency_in(unit, title, *, order=1, is_primary=True, **kwargs):
    """Une compétence de la formation, rattachée à ``unit``."""
    competency = Competency.objects.create(
        path=unit.period.path,
        period=kwargs.pop("period", unit.period),
        title=title,
        order=order,
        **kwargs,
    )
    UnitCompetency.objects.create(unit=unit, competency=competency, order=order, is_primary=is_primary)
    return competency


def share_competency(competency, unit, *, order=1, is_primary=False, local_objective=""):
    """Rattache une compétence existante à une matière de plus."""
    return UnitCompetency.objects.create(
        unit=unit,
        competency=competency,
        order=order,
        is_primary=is_primary,
        local_objective=local_objective,
    )
