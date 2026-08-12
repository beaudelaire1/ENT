"""Travaux de fond de la recherche.

Renommer une formation change le texte projeté de toutes ses périodes, matières,
compétences, évaluations et résultats. Fait dans le cycle de la requête, cela tenait
l'utilisateur devant un écran figé le temps de plusieurs centaines d'aller-retours SQL —
pour une opération dont il n'attend rien de visible.

La réindexation part donc en file. Si le courtier est injoignable, ``core.queue.enqueue``
la fait sur place : mieux vaut une requête longue qu'un index qui ment.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.apps import apps

logger = logging.getLogger(__name__)


@shared_task(name="core.reindex_dependents")
def reindex_dependents_task(label: str, pk: int) -> int:
    """Réindexe les descendants de l'objet désigné, s'il existe encore.

    L'objet est retrouvé par son étiquette et sa clé plutôt que transmis tel quel : une
    tâche reçoit du JSON, et un objet sérialisé serait de toute façon périmé au moment
    où le worker le lit. Sa disparition entre-temps n'est pas une erreur — la suppression
    a déjà retiré ses entrées.
    """
    from core.search import reindex_dependents

    model = apps.get_model(label)
    instance = model.objects.filter(pk=pk).first()
    if instance is None:
        return 0
    return reindex_dependents(instance)
