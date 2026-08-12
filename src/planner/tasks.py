from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from notifications.models import EmailDelivery, Notification

from .models import Reminder


@shared_task(name="planner.dispatch_due_reminders")
def dispatch_due_reminders():
    ids = list(
        Reminder.objects.filter(status=Reminder.Status.PENDING, scheduled_for__lte=timezone.now()).values_list(
            "pk", flat=True
        )[:200]
    )
    for reminder_id in ids:
        deliver_reminder.delay(reminder_id)
    return len(ids)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 4})
def deliver_reminder(self, reminder_id: int):
    with transaction.atomic():
        # Seul `owner` est préchargé. `task` et `event` sont facultatifs : les précharger
        # produisait des jointures externes, et PostgreSQL refuse de poser un verrou sur
        # le côté nullable d'une telle jointure — « FOR UPDATE cannot be applied to the
        # nullable side of an outer join ». La remise des rappels échouait donc à chaque
        # fois en production, sans que rien ne le montre : SQLite ignore purement et
        # simplement `select_for_update`, et c'est sur SQLite que tournaient les tests.
        # La cible est lue juste après, hors du verrou, pour une requête de plus.
        reminder = Reminder.objects.select_for_update().select_related("owner").get(pk=reminder_id)
        if reminder.status == Reminder.Status.SENT:
            return "already-sent"
        reminder.status = Reminder.Status.PROCESSING
        reminder.attempts += 1
        reminder.save(update_fields=["status", "attempts"])
    try:
        target = reminder.target
        title = f"Rappel · {target.title}"
        message = target.description or "Une échéance de votre ENT arrive."
        url = "/tasks/" if reminder.task_id else "/agenda/"
        if reminder.internal:
            Notification.objects.get_or_create(
                owner=reminder.owner,
                dedupe_key=f"reminder:{reminder.pk}",
                defaults={"title": title, "message": message, "url": url, "kind": Notification.Kind.REMINDER},
            )
        if reminder.email and reminder.owner.email:
            delivery, created = EmailDelivery.objects.get_or_create(
                owner=reminder.owner,
                dedupe_key=f"reminder:{reminder.pk}",
                defaults={"subject": title, "recipient": reminder.owner.email},
            )
            if created or not delivery.sent_at:
                send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [reminder.owner.email], fail_silently=False)
                delivery.sent_at = timezone.now()
                delivery.last_error = ""
                delivery.save(update_fields=["sent_at", "last_error"])
        reminder.status = Reminder.Status.SENT
        reminder.sent_at = timezone.now()
        reminder.last_error = ""
        reminder.save(update_fields=["status", "sent_at", "last_error"])
        return "sent"
    except Exception as exc:
        Reminder.objects.filter(pk=reminder.pk).update(status=Reminder.Status.FAILED, last_error=str(exc)[:1000])
        raise
