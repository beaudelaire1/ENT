from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import OwnedQuerySet, TimeStampedModel


class Recurrence(models.TextChoices):
    """Répétitions courantes d'un emploi du temps.

    Volontairement limité : un semestre se décrit avec « chaque semaine », pas avec une
    règle iCalendar complète. Ce qui ne rentre pas dans ces cas se saisit à la main.
    """

    NONE = "none", "Ne se répète pas"
    DAILY = "daily", "Chaque jour"
    WEEKDAYS = "weekdays", "Du lundi au vendredi"
    WEEKLY = "weekly", "Chaque semaine"
    BIWEEKLY = "biweekly", "Une semaine sur deux"
    MONTHLY = "monthly", "Chaque mois"


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
    title = models.CharField("intitulé", max_length=180)
    description = models.TextField("description", blank=True)
    status = models.CharField("état", max_length=16, choices=Status.choices, default=Status.TODO)
    priority = models.PositiveSmallIntegerField("priorité", choices=Priority.choices, default=Priority.NORMAL)
    due_at = models.DateTimeField("échéance", null=True, blank=True)
    reminder_at = models.DateTimeField("rappel le", null=True, blank=True)
    email_reminder = models.BooleanField("rappel par email", default=True)
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = "tâche"
        verbose_name_plural = "tâches"
        ordering = ["status", "priority", "due_at", "title"]

    def __str__(self):
        return self.title


class CalendarEvent(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_events")
    title = models.CharField("intitulé", max_length=180)
    description = models.TextField("description", blank=True)
    starts_at = models.DateTimeField("début")
    ends_at = models.DateTimeField("fin")
    all_day = models.BooleanField("journée entière", default=False)
    location = models.CharField("lieu", max_length=180, blank=True)
    reminder_at = models.DateTimeField("rappel le", null=True, blank=True)
    email_reminder = models.BooleanField("rappel par email", default=True)
    # Une série est matérialisée : chaque séance est un événement à part entière, qu'on
    # peut déplacer ou annuler seule. `series` désigne la première, qui porte la règle.
    series = models.ForeignKey(
        "self",
        verbose_name="série",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="occurrences",
    )
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = "événement"
        verbose_name_plural = "événements"
        ordering = ["starts_at"]

    @property
    def is_series_head(self) -> bool:
        return self.series_id is None and self.occurrences.exists()

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
    scheduled_for = models.DateTimeField("prévu pour", db_index=True)
    internal = models.BooleanField("notification interne", default=True)
    email = models.BooleanField("envoi par email", default=True)
    status = models.CharField("état", max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField("tentatives", default=0)
    sent_at = models.DateTimeField("envoyé le", null=True, blank=True)
    last_error = models.TextField("dernière erreur", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "rappel"
        verbose_name_plural = "rappels"
        ordering = ["scheduled_for"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(task__isnull=False, event__isnull=True) | models.Q(task__isnull=True, event__isnull=False)
                ),
                name="reminder_exactly_one_target",
            )
        ]

    def __str__(self):
        return f"{self.target} · {self.scheduled_for}"

    @property
    def target(self):
        return self.task or self.event
