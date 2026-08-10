from __future__ import annotations

from .models import CalendarEvent, Reminder, Task


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
