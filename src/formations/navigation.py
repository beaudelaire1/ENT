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
    return unit_crumbs(competency.unit) + [
        crumb(competency.title, reverse("formations:competency", args=[competency.pk]))
    ]
