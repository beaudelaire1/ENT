from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import OwnedQuerySet, TimeStampedModel


class LearningPath(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "En pause"
        COMPLETED = "completed", "Terminée"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_paths")
    title = models.CharField("intitulé", max_length=180)
    training_type = models.CharField("type de formation", max_length=120, blank=True)
    level_label = models.CharField("niveau", max_length=120, blank=True)
    description = models.TextField("description", blank=True)
    status = models.CharField("état", max_length=12, choices=Status.choices, default=Status.ACTIVE)
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = "formation"
        verbose_name_plural = "formations"
        ordering = ["title"]

    def __str__(self):
        return self.title


class Period(TimeStampedModel):
    path = models.ForeignKey(LearningPath, verbose_name="formation", on_delete=models.CASCADE, related_name="periods")
    title = models.CharField("intitulé", max_length=140)
    order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "période"
        verbose_name_plural = "périodes"
        ordering = ["order", "title"]
        constraints = [models.UniqueConstraint(fields=["path", "title"], name="unique_period_per_path")]

    def __str__(self):
        return self.title


class LearningUnit(TimeStampedModel):
    period = models.ForeignKey(Period, verbose_name="période", on_delete=models.CASCADE, related_name="units")
    title = models.CharField("intitulé", max_length=180)
    description = models.TextField("description", blank=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)
    resources = models.ManyToManyField(
        "library.LibraryItem", verbose_name="ressources", blank=True, related_name="learning_units"
    )

    class Meta:
        verbose_name = "module"
        verbose_name_plural = "modules"
        ordering = ["order", "title"]
        constraints = [models.UniqueConstraint(fields=["period", "title"], name="unique_unit_per_period")]

    def __str__(self):
        return self.title


class Competency(TimeStampedModel):
    unit = models.ForeignKey(LearningUnit, verbose_name="module", on_delete=models.CASCADE, related_name="competencies")
    title = models.CharField("intitulé", max_length=220)
    description = models.TextField("description", blank=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)
    resources = models.ManyToManyField(
        "library.LibraryItem", verbose_name="ressources", blank=True, related_name="competencies"
    )

    class Meta:
        verbose_name = "compétence"
        verbose_name_plural = "compétences"
        ordering = ["order", "title"]
        constraints = [models.UniqueConstraint(fields=["unit", "title"], name="unique_competency_per_unit")]

    def __str__(self):
        return self.title


class MetricDefinition(models.Model):
    path = models.ForeignKey(
        LearningPath, verbose_name="formation", on_delete=models.CASCADE, related_name="metric_definitions"
    )
    key = models.SlugField("clé", max_length=40)
    label = models.CharField("libellé", max_length=80)
    unit_label = models.CharField("unité", max_length=20, blank=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "colonne de suivi"
        verbose_name_plural = "colonnes de suivi"
        ordering = ["order", "label"]
        constraints = [models.UniqueConstraint(fields=["path", "key"], name="unique_metric_key_per_path")]

    def __str__(self):
        return self.label


class MetricValue(models.Model):
    definition = models.ForeignKey(
        MetricDefinition, verbose_name="colonne", on_delete=models.CASCADE, related_name="values"
    )
    unit = models.ForeignKey(
        LearningUnit, verbose_name="module", on_delete=models.CASCADE, related_name="metric_values"
    )
    value = models.DecimalField("valeur", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "valeur de suivi"
        verbose_name_plural = "valeurs de suivi"
        constraints = [models.UniqueConstraint(fields=["definition", "unit"], name="unique_metric_value_per_unit")]

    def __str__(self):
        return f"{self.definition} · {self.unit} = {self.value}"

    def clean(self):
        if self.definition.path_id != self.unit.period.path_id:
            raise ValidationError("La métrique et l’unité doivent appartenir au même parcours.")


class ProgressRecord(TimeStampedModel):
    class Mastery(models.IntegerChoices):
        NOT_STARTED = 0, "Non abordé"
        DISCOVERED = 1, "Découvert"
        IN_PROGRESS = 2, "En cours"
        ACQUIRED = 3, "Acquis"
        MASTERED = 4, "Maîtrisé"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress_records")
    competency = models.ForeignKey(
        Competency, verbose_name="compétence", on_delete=models.CASCADE, related_name="progress_records"
    )
    mastery_level = models.PositiveSmallIntegerField(
        "niveau de maîtrise",
        choices=Mastery.choices,
        default=Mastery.NOT_STARTED,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
    )
    planned_hours = models.DecimalField("travail personnel estimé (h)", max_digits=7, decimal_places=2, default=0)
    actual_hours = models.DecimalField("temps réel (h)", max_digits=7, decimal_places=2, default=0)
    notes = models.TextField("commentaires", blank=True)

    class Meta:
        verbose_name = "progression"
        verbose_name_plural = "progressions"
        constraints = [models.UniqueConstraint(fields=["owner", "competency"], name="unique_progress_per_competency")]

    @property
    def percent(self) -> int:
        """Progression affichée : le niveau de maîtrise rapporté à son maximum."""
        return round(self.mastery_level * 100 / 4)

    def clean(self):
        if self.competency.unit.period.path.owner_id != self.owner_id:
            raise ValidationError("La progression appartient à un autre utilisateur.")
