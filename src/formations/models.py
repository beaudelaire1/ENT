from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import OwnedQuerySet, TimeStampedModel

# Bornes de stockage de MetricValue.value (max_digits=10, decimal_places=2). Une saisie
# au-delà ne serait pas rejetée par le formulaire mais par la base, en erreur 500.
METRIC_ABSOLUTE_LIMIT = Decimal("99999999.99")
# MetricValue stocke deux décimales : une définition ne peut pas en demander plus, sinon
# la valeur affichée après enregistrement ne serait pas celle qui a été saisie.
METRIC_MAX_DECIMAL_PLACES = 2


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
    """Une colonne chiffrée de la grille, avec ses règles de saisie facultatives.

    Les bornes sont facultatives et non pas positives par défaut : une métrique
    personnalisée accepte les valeurs négatives, car certaines mesurent un écart ou un
    solde. Pour l'interdire sur une colonne donnée, il faut y poser une valeur minimale
    — le formulaire propose 0 d'emblée, qui est le cas courant (coefficient, ECTS,
    heures de TD n'ont pas de sens en négatif).
    """

    path = models.ForeignKey(
        LearningPath, verbose_name="formation", on_delete=models.CASCADE, related_name="metric_definitions"
    )
    key = models.SlugField("clé", max_length=40)
    label = models.CharField("libellé", max_length=80)
    unit_label = models.CharField("unité", max_length=20, blank=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)
    min_value = models.DecimalField(
        "valeur minimale",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Laisser vide pour ne poser aucune limite basse.",
    )
    max_value = models.DecimalField(
        "valeur maximale",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Laisser vide pour ne poser aucune limite haute.",
    )
    decimal_places = models.PositiveSmallIntegerField(
        "décimales",
        default=METRIC_MAX_DECIMAL_PLACES,
        validators=[MaxValueValidator(METRIC_MAX_DECIMAL_PLACES)],
        help_text="0 pour n'accepter que des entiers (ECTS, coefficient).",
    )

    class Meta:
        verbose_name = "colonne de suivi"
        verbose_name_plural = "colonnes de suivi"
        ordering = ["order", "label"]
        constraints = [
            models.UniqueConstraint(fields=["path", "key"], name="unique_metric_key_per_path"),
            models.CheckConstraint(
                condition=models.Q(min_value__isnull=True)
                | models.Q(max_value__isnull=True)
                | models.Q(min_value__lte=models.F("max_value")),
                name="metric_bounds_ordered",
            ),
            models.CheckConstraint(
                condition=models.Q(decimal_places__lte=METRIC_MAX_DECIMAL_PLACES),
                name="metric_decimal_places_storable",
            ),
        ]

    def __str__(self):
        return self.label

    def clean(self):
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValidationError({"max_value": "La valeur maximale doit être supérieure à la valeur minimale."})

    def parse(self, raw: str) -> tuple[Decimal | None, str | None]:
        """Convertit une saisie en valeur enregistrable, ou explique pourquoi c'est non.

        Renvoie ``(valeur, None)`` ou ``(None, message)``. Le message est destiné à
        l'utilisateur et ne mentionne pas la colonne : l'appelant sait de laquelle il
        s'agit et la nomme lui-même.

        La virgule française est acceptée : c'est ce que produit un pavé numérique
        configuré en français, et la refuser serait incompréhensible.
        """
        text = (raw or "").strip().replace(",", ".")
        if not text:
            return None, None
        try:
            value = Decimal(text)
        except InvalidOperation:
            return None, f"« {raw.strip()} » n’est pas un nombre."
        if not value.is_finite():
            return None, f"« {raw.strip()} » n’est pas un nombre."
        error = self.check_value(value)
        if error:
            return None, error
        return value.quantize(Decimal(1).scaleb(-self.decimal_places)), None

    def check_value(self, value: Decimal) -> str | None:
        """Vérifie une valeur déjà convertie contre les règles de la colonne."""
        if not -METRIC_ABSOLUTE_LIMIT <= value <= METRIC_ABSOLUTE_LIMIT:
            return "valeur hors limites."
        if self.min_value is not None and value < self.min_value:
            return f"la valeur ne peut pas être inférieure à {self.min_value:f}."
        if self.max_value is not None and value > self.max_value:
            return f"la valeur ne peut pas être supérieure à {self.max_value:f}."
        if value != value.quantize(Decimal(1).scaleb(-self.decimal_places)):
            if self.decimal_places == 0:
                return "cette colonne n’accepte que des nombres entiers."
            return f"cette colonne n’accepte que {self.decimal_places} décimale(s)."
        return None


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
        if self.value is not None:
            error = self.definition.check_value(self.value)
            if error:
                raise ValidationError({"value": f"{self.definition.label} : {error}"})


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
    planned_hours = models.DecimalField(
        "travail personnel estimé (h)",
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    actual_hours = models.DecimalField(
        "temps réel (h)",
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    notes = models.TextField("commentaires", blank=True)

    class Meta:
        verbose_name = "progression"
        verbose_name_plural = "progressions"
        constraints = [
            models.UniqueConstraint(fields=["owner", "competency"], name="unique_progress_per_competency"),
            # Une durée négative n'est pas une saisie maladroite à corriger plus tard :
            # elle fausse tous les totaux de la grille. La base la refuse aussi, pour que
            # ni l'admin, ni un script, ni une future vue ne puisse en créer.
            models.CheckConstraint(condition=models.Q(planned_hours__gte=0), name="progress_planned_hours_positive"),
            models.CheckConstraint(condition=models.Q(actual_hours__gte=0), name="progress_actual_hours_positive"),
        ]

    @property
    def percent(self) -> int:
        """Progression affichée : le niveau de maîtrise rapporté à son maximum."""
        return round(self.mastery_level * 100 / 4)

    def clean(self):
        if self.competency.unit.period.path.owner_id != self.owner_id:
            raise ValidationError("La progression appartient à un autre utilisateur.")
