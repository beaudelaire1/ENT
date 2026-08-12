from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone


@transaction.atomic
def record_session(user, *, seconds: int, started_at, intention: str = "", competency=None):
    """Enregistre une session terminée et reporte son temps sur la compétence visée.

    Le report est cumulatif et ne touche qu'au temps réel : ce que l'utilisateur a saisi
    à la main dans la grille de suivi n'est jamais écrasé, seulement complété. Sans
    compétence choisie, la session est simplement journalisée.
    """
    from formations.models import ProgressRecord

    from .models import FocusSession

    session = FocusSession.objects.create(
        owner=user,
        competency=competency,
        intention=intention[:80],
        started_at=started_at,
        seconds=seconds,
    )
    if competency is None:
        return session

    ProgressRecord.objects.get_or_create(owner=user, competency=competency)
    # L'écriture passe par l'instance et non par un `update()` de queryset : c'est
    # `ProgressRecord.save()` qui recalcule le total et laisse le temps proposer un
    # palier de maîtrise. Un `update()` écrivait les heures sans jamais déclencher cela,
    # et c'est pourtant ici — une session terminée — que le palier a le plus de sens.
    _adjust_competency_time(user, competency, session.hours)
    session.counted_at = timezone.now()
    session.save(update_fields=["counted_at", "updated_at"])
    return session


def _adjust_competency_time(owner, competency, delta: Decimal) -> None:
    from formations.models import ProgressRecord

    record, _ = ProgressRecord.objects.get_or_create(owner=owner, competency=competency)
    record = ProgressRecord.objects.select_for_update().select_related("competency__path").get(pk=record.pk)
    record.session_hours = max(Decimal(0), record.session_hours + delta)
    record.actual_hours = record.manual_hours + record.session_hours
    record.save(update_fields=["session_hours", "actual_hours"])


@transaction.atomic
def revise_session(session, *, seconds: int, started_at, intention: str, competency, excluded: bool):
    """Corrige une session et répercute exactement son ancienne puis sa nouvelle part."""
    from .models import FocusSession

    session = FocusSession.objects.select_for_update().get(pk=session.pk, owner=session.owner)
    if session.is_counted:
        _adjust_competency_time(session.owner, session.competency, -session.hours)

    session.seconds = seconds
    session.started_at = started_at
    session.intention = intention[:80]
    session.competency = competency
    session.excluded_at = timezone.now() if excluded else None
    if competency is None:
        session.counted_at = None
    elif not excluded:
        session.counted_at = session.counted_at or timezone.now()
        _adjust_competency_time(session.owner, competency, session.hours)
    session.save(
        update_fields=["seconds", "started_at", "intention", "competency", "excluded_at", "counted_at", "updated_at"]
    )
    return session


def parse_duration(value: str) -> int:
    """Parse minutes, MM:SS or HH:MM:SS into 1..86400 seconds."""
    value = value.strip().replace(",", ".")
    if not value:
        raise ValueError("La durée est vide.")
    if ":" not in value:
        try:
            seconds = round(float(value) * 60)
        except ValueError as exc:
            raise ValueError("Durée invalide.") from exc
    else:
        parts = value.split(":")
        if len(parts) not in {2, 3}:
            raise ValueError("Utilisez MM:SS ou HH:MM:SS.")
        try:
            numbers = [int(part) for part in parts]
        except ValueError as exc:
            raise ValueError("Durée invalide.") from exc
        if any(number < 0 for number in numbers) or numbers[-1] >= 60 or (len(numbers) == 3 and numbers[-2] >= 60):
            raise ValueError("Minutes ou secondes invalides.")
        seconds = (
            numbers[0] * 60 + numbers[1] if len(numbers) == 2 else numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
        )
    if not 1 <= seconds <= 86400:
        raise ValueError("La durée doit être comprise entre 1 seconde et 24 heures.")
    return seconds


def format_duration(seconds: float) -> str:
    total = max(0, int(seconds + 0.999999))
    hours, remainder = divmod(total, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
    return f"{minutes:02d}:{remaining_seconds:02d}"
