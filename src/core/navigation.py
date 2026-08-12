"""Fil d'Ariane et retours contextuels, partagés par tous les modules.

Deux besoins qui vont ensemble. Le fil d'Ariane dit où l'on est ; le retour contextuel
ramène là d'où l'on vient. Sans le second, modifier une matière depuis une bibliothèque
filtrée renvoyait sur une liste vierge, et le filtre était à refaire.

Une URL de retour vient de la requête, donc de l'extérieur : elle est vérifiée avant
usage. Autrement le paramètre ``next`` transformerait chaque formulaire en tremplin vers
un site tiers, avec l'adresse de MyENT dans la barre au moment du clic.
"""

from __future__ import annotations

from django.utils.http import url_has_allowed_host_and_scheme


def crumb(label: str, url: str | None = None) -> dict[str, str | None]:
    """Un maillon du fil. Sans URL, il est affiché sans être cliquable."""
    return {"label": label, "url": url}


def safe_next(request, fallback: str) -> str:
    """L'adresse de retour demandée si elle mène bien à l'intérieur du site.

    Accepte ``next`` en POST comme en GET : le formulaire le reçoit dans son adresse et
    le renvoie dans un champ caché, pour que la page de retour survive à un envoi
    rejeté.
    """
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return fallback
