"""Limitation des tentatives de connexion.

Le comptage porte sur le nom d'utilisateur visé, pas sur l'adresse IP. Derrière le
proxy de Coolify, toutes les requêtes arrivent avec la même adresse : compter par IP
reviendrait à verrouiller tout le monde dès qu'une seule personne se trompe, ou à ne
rien verrouiller du tout si l'on faisait confiance à un en-tête falsifiable.

Contrepartie assumée : quelqu'un qui connaît un nom d'utilisateur peut en bloquer la
connexion pendant la durée du verrou. Avec un service à quelques comptes, ralentir une
attaque par force brute vaut mieux que ce risque-là.
"""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache

MAX_ATTEMPTS = getattr(settings, "LOGIN_MAX_ATTEMPTS", 10)
LOCKOUT_SECONDS = getattr(settings, "LOGIN_LOCKOUT_SECONDS", 900)


def _key(username: str) -> str:
    return f"login-attempts:{(username or '').strip().lower()[:150]}"


def attempts_exhausted(username: str) -> bool:
    return cache.get(_key(username), 0) >= MAX_ATTEMPTS


def record_failure(username: str) -> int:
    key = _key(username)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOCKOUT_SECONDS)
        count = 1
    return count


def clear(username: str) -> None:
    cache.delete(_key(username))
