"""Mise en file tolérante à l'absence de courtier.

Celery lève une erreur si Redis est injoignable. Sans précaution, un téléversement
audio ou une invitation renvoient une erreur 500 alors que l'objet est déjà enregistré :
l'utilisateur voit un plantage, et la piste reste bloquée en « Validation » sans que
rien ne puisse la débloquer.

En développement local, où l'on ne lance ni Redis ni worker, c'est le comportement par
défaut. En production, cela couvre une coupure passagère du courtier.
"""

from __future__ import annotations

import logging

from kombu.exceptions import OperationalError

logger = logging.getLogger(__name__)


def enqueue(task, *args, **kwargs):
    """Met la tâche en file, ou l'exécute immédiatement si le courtier est injoignable.

    L'exécution sur place allonge la requête ; c'est préférable à un échec, et cela
    reste l'exception plutôt que la règle dès qu'un worker tourne.
    """
    try:
        return task.delay(*args, **kwargs)
    except OperationalError:
        logger.warning("Courtier injoignable : %s exécutée sur place.", task.name)
        return task.run(*args, **kwargs)
