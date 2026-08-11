from __future__ import annotations

from datetime import date, timedelta

from .models import CalendarEvent, Recurrence, Reminder, Task

# Garde-fou : une règle mal saisie ne doit pas remplir l'agenda de milliers de lignes.
MAX_OCCURRENCES = 200


def _add_months(anchor, count: int):
    """`count` mois après l'ancre, replié sur le dernier jour des mois plus courts."""
    total = anchor.month - 1 + count
    year, month = anchor.year + total // 12, total % 12 + 1
    last_day = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
    return anchor.replace(year=year, month=month, day=min(anchor.day, last_day))


def _advance(moment, rule: str):
    """Date suivante selon la règle, en conservant l'heure."""
    if rule == Recurrence.DAILY:
        return moment + timedelta(days=1)
    if rule == Recurrence.WEEKDAYS:
        step = {4: 3, 5: 2}.get(moment.weekday(), 1)  # vendredi et samedi sautent au lundi
        return moment + timedelta(days=step)
    if rule == Recurrence.WEEKLY:
        return moment + timedelta(weeks=1)
    if rule == Recurrence.BIWEEKLY:
        return moment + timedelta(weeks=2)
    raise ValueError(f"Règle de récurrence inconnue : {rule}")


def _stepwise(anchor, rule: str):
    moment = anchor
    for _ in range(MAX_OCCURRENCES):
        moment = _advance(moment, rule)
        yield moment


def occurrences_until(anchor, rule: str, until):
    """Dates successives d'une série, bornées par `until` et par MAX_OCCURRENCES.

    Le mensuel se calcule depuis l'ancre et non depuis l'occurrence précédente : sinon
    un 31 janvier replié sur le 28 février entraînerait toute la suite sur le 28.
    """
    if rule == Recurrence.MONTHLY:
        candidates = (_add_months(anchor, index) for index in range(1, MAX_OCCURRENCES + 1))
    else:
        candidates = _stepwise(anchor, rule)

    for moment in candidates:
        if moment.date() > until:
            return
        yield moment


def expand_event_series(event: CalendarEvent, rule: str, until) -> int:
    """Crée les séances suivantes d'un événement jusqu'à la date de fin incluse.

    Les occurrences déjà présentes sont laissées telles quelles : réenregistrer la série
    ne doit ni dupliquer ni écraser une séance que l'on aurait déplacée à la main.
    """
    if rule == Recurrence.NONE or not until:
        return 0

    existing = set(event.occurrences.values_list("starts_at", flat=True))
    duration = event.ends_at - event.starts_at
    reminder_offset = event.reminder_at - event.starts_at if event.reminder_at else None

    created = 0
    for starts_at in occurrences_until(event.starts_at, rule, until):
        if starts_at in existing:
            continue
        CalendarEvent.objects.create(
            owner=event.owner,
            series=event,
            title=event.title,
            description=event.description,
            starts_at=starts_at,
            ends_at=starts_at + duration,
            all_day=event.all_day,
            location=event.location,
            reminder_at=starts_at + reminder_offset if reminder_offset else None,
            email_reminder=event.email_reminder,
        )
        created += 1
    return created


def expand_task_series(task: Task, rule: str, until) -> int:
    """Même principe pour les tâches, qui se répètent sur leur échéance."""
    if rule == Recurrence.NONE or not until or not task.due_at:
        return 0

    reminder_offset = task.reminder_at - task.due_at if task.reminder_at else None
    existing = set(
        Task.objects.filter(owner=task.owner, title=task.title, due_at__isnull=False).values_list("due_at", flat=True)
    )

    created = 0
    for due_at in occurrences_until(task.due_at, rule, until):
        if due_at in existing:
            continue
        Task.objects.create(
            owner=task.owner,
            title=task.title,
            description=task.description,
            status=Task.Status.TODO,
            priority=task.priority,
            due_at=due_at,
            reminder_at=due_at + reminder_offset if reminder_offset else None,
            email_reminder=task.email_reminder,
        )
        created += 1
    return created


def sync_task_reminder(task: Task) -> None:
    if not task.reminder_at or task.status == Task.Status.DONE:
        Reminder.objects.filter(task=task).delete()
        return
    Reminder.objects.update_or_create(
        task=task,
        defaults={
            "owner": task.owner,
            "scheduled_for": task.reminder_at,
            "internal": True,
            "email": task.email_reminder,
            "status": Reminder.Status.PENDING,
            "sent_at": None,
            "last_error": "",
        },
    )


def sync_event_reminder(event: CalendarEvent) -> None:
    if not event.reminder_at:
        Reminder.objects.filter(event=event).delete()
        return
    Reminder.objects.update_or_create(
        event=event,
        defaults={
            "owner": event.owner,
            "scheduled_for": event.reminder_at,
            "internal": True,
            "email": event.email_reminder,
            "status": Reminder.Status.PENDING,
            "sent_at": None,
            "last_error": "",
        },
    )
