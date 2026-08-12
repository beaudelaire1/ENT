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


class TaskSeries(TimeStampedModel):
    """L'identité durable d'une série, distincte du titre de ses occurrences."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_series")
    recurrence = models.CharField("répétition", max_length=12, choices=Recurrence.choices)
    repeat_until = models.DateField("jusqu’au")

    class Meta:
        verbose_name = "série de tâches"
        verbose_name_plural = "séries de tâches"
        ordering = ["-created_at"]

    def __str__(self):
        first = self.tasks.order_by("series_position", "due_at").first()
        return first.title if first else self.get_recurrence_display()


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
    series = models.ForeignKey(
        TaskSeries,
        verbose_name="série",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    series_position = models.PositiveSmallIntegerField("position dans la série", default=0)
    title = models.CharField("intitulé", max_length=180)
    description = models.TextField("description", blank=True)
    status = models.CharField("état", max_length=16, choices=Status.choices, default=Status.TODO)
    priority = models.PositiveSmallIntegerField("priorité", choices=Priority.choices, default=Priority.NORMAL)
    due_at = models.DateTimeField("échéance", null=True, blank=True)
    reminder_at = models.DateTimeField("rappel le", null=True, blank=True)
    email_reminder = models.BooleanField("rappel par email", default=True)
    unit = models.ForeignKey(
        "formations.LearningUnit",
        verbose_name="matière",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    competency = models.ForeignKey(
        "formations.Competency",
        verbose_name="compétence",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    assessment = models.ForeignKey(
        "formations.Assessment",
        verbose_name="évaluation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = "tâche"
        verbose_name_plural = "tâches"
        ordering = ["status", "priority", "due_at", "title"]

    def __str__(self):
        return self.title

    def clean(self):
        _validate_academic_links(self)


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
    unit = models.ForeignKey(
        "formations.LearningUnit",
        verbose_name="matière",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calendar_events",
    )
    competency = models.ForeignKey(
        "formations.Competency",
        verbose_name="compétence",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calendar_events",
    )
    assessment = models.ForeignKey(
        "formations.Assessment",
        verbose_name="évaluation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calendar_events",
    )
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
        _validate_academic_links(self)

    def __str__(self):
        return self.title


def _validate_academic_links(item):
    """Tous les rattachements doivent appartenir au propriétaire et à une même formation."""
    paths = set()
    if item.unit_id:
        if item.unit.period.path.owner_id != item.owner_id:
            raise ValidationError({"unit": "Cette matière appartient à un autre utilisateur."})
        paths.add(item.unit.period.path_id)
    if item.competency_id:
        if item.competency.path.owner_id != item.owner_id:
            raise ValidationError({"competency": "Cette compétence appartient à un autre utilisateur."})
        paths.add(item.competency.path_id)
    if item.assessment_id:
        if item.assessment.owner_id != item.owner_id:
            raise ValidationError({"assessment": "Cette évaluation appartient à un autre utilisateur."})
        if item.assessment.unit_id:
            paths.add(item.assessment.unit.period.path_id)
        elif item.assessment.period_id:
            paths.add(item.assessment.period.path_id)
    if len(paths) > 1:
        raise ValidationError("La matière, la compétence et l’évaluation doivent appartenir à la même formation.")


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
