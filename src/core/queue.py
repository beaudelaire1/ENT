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
import time

from kombu.exceptions import OperationalError

logger = logging.getLogger(__name__)

# Une tentative de connexion à un courtier absent coûte son délai d'attente. Payé une fois,
# c'est le prix d'une panne ; payé à chaque mise en file — et la réindexation en produit
# une par enregistrement — cela immobilise l'application entière. On retient donc l'échec
# pendant ce laps de temps avant de retenter, assez court pour qu'un courtier revenu soit
# retrouvé sans redémarrage.
BROKER_COOLDOWN = 30.0
_unreachable_until = 0.0


def broker_is_resting() -> bool:
    return time.monotonic() < _unreachable_until


def forget_broker_failure() -> None:
    """Oublie une panne constatée. Pour les tests, et pour une reprise commandée à la main."""
    global _unreachable_until

    _unreachable_until = 0.0


def enqueue(task, *args, **kwargs):
    """Met la tâche en file, ou l'exécute immédiatement si le courtier est injoignable.

    L'exécution sur place allonge la requête ; c'est préférable à un échec, et cela
    reste l'exception plutôt que la règle dès qu'un worker tourne.
    """
    global _unreachable_until

    if broker_is_resting():
        return task.run(*args, **kwargs)
    try:
        result = task.delay(*args, **kwargs)
    except OperationalError:
        _unreachable_until = time.monotonic() + BROKER_COOLDOWN
        logger.warning("Courtier injoignable : %s exécutée sur place.", task.name)
        return task.run(*args, **kwargs)
    _unreachable_until = 0.0
    return result
