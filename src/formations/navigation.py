"""Fils d'Ariane du module Formations.

Une compétence se lit dans son contexte : Formations → Licence → Semestre 5 → Topologie.
Sans ce chemin, une page de matière atteinte depuis la recherche globale ne disait pas à
quelle formation ni à quel semestre elle appartenait, et remonter d'un cran demandait de
repasser par la liste.

Une période n'a pas de page à elle : son maillon pointe vers sa section dans la structure
de la formation.
"""

from __future__ import annotations

from django.urls import reverse

from core.navigation import crumb


def path_crumbs(path) -> list[dict]:
    return [
        crumb("Formations", reverse("formations:list")),
        crumb(path.title, reverse("formations:detail", args=[path.pk])),
    ]


def period_crumbs(period) -> list[dict]:
    anchor = f"{reverse('formations:detail', args=[period.path_id])}#periode-{period.pk}"
    return path_crumbs(period.path) + [crumb(period.title, anchor)]


def unit_crumbs(unit) -> list[dict]:
    return period_crumbs(unit.period) + [crumb(unit.title, reverse("formations:unit", args=[unit.pk]))]


def competency_crumbs(competency) -> list[dict]:
    """Le chemin d'une compétence dépend de ce à quoi elle est rattachée.

    Une compétence transversale n'appartient à aucune matière : son fil s'arrête à la
    période, ou à la formation. Passer par une matière inexistante aurait échoué.
    """
    unit = competency.primary_unit
    if unit is not None:
        head = unit_crumbs(unit)
    elif competency.period_id:
        head = period_crumbs(competency.period)
    else:
        head = path_crumbs(competency.path)
    return head + [crumb(competency.title, reverse("formations:competency", args=[competency.pk]))]
