from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import OwnedQuerySet, TimeStampedModel


class Task(TimeStampedModel):
    class Status(models.TextChoices):
        TODO = "todo", "À faire"
        IN_PROGRESS = "in_progress", "En cours"
        DONE = "done", "Terminée"

    class Priority(models.IntegerChoices):
        LOW = 3, "Basse"
        NORMAL = 2, "Normale"
        HIGH = 1, "Haute"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TODO)
    priority = models.PositiveSmallIntegerField(choices=Priority.choices, default=Priority.NORMAL)
    due_at = models.DateTimeField(null=True, blank=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    email_reminder = models.BooleanField(default=True)
    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["status", "priority", "due_at", "title"]

    def __str__(self):
        return self.title


class CalendarEvent(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_events")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=180, blank=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    email_reminder = models.BooleanField(default=True)
    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["starts_at"]

    def clean(self):
        if self.ends_at and self.starts_at and self.ends_at < self.starts_at:
            raise ValidationError({"ends_at": "La fin doit être postérieure au début."})

    def __str__(self):
        return self.title


class Reminder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PROCESSING = "processing", "En cours"
        SENT = "sent", "Envoyé"
        FAILED = "failed", "Échec"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reminders")
    task = models.OneToOneField(Task, null=True, blank=True, on_delete=models.CASCADE, related_name="reminder")
    event = models.OneToOneField(
        CalendarEvent, null=True, blank=True, on_delete=models.CASCADE, related_name="reminder"
    )
    scheduled_for = models.DateTimeField(db_index=True)
    internal = models.BooleanField(default=True)
    email = models.BooleanField(default=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_for"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(task__isnull=False, event__isnull=True) | models.Q(task__isnull=True, event__isnull=False)
                ),
                name="reminder_exactly_one_target",
            )
        ]

    @property
    def target(self):
        return self.task or self.event

    def __str__(self):
        return f"{self.target} · {self.scheduled_for}"
