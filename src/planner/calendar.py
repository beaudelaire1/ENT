"""Bornes locales et chevauchements, partagés par l'agenda et l'accueil."""

from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone


def day_bounds(day):
    # Construire les deux minuits locaux : une journée peut durer 23 ou 25 heures.
    return (
        timezone.make_aware(datetime.combine(day, time.min)),
        timezone.make_aware(datetime.combine(day + timedelta(days=1), time.min)),
    )


def events_in_window(events, start, end):
    # Fin exclusive, sauf événement ponctuel : il appartient au jour de son début.
    return events.filter(starts_at__lt=end).filter(Q(ends_at__gt=start) | Q(starts_at__gte=start))


def overlaps(event, start, end):
    return event.starts_at < end and (event.ends_at > start or event.starts_at >= start)
