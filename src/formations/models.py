from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import OwnedQuerySet, TimeStampedModel

from .progression import (
    MASTERY_DESCRIPTIONS,
    accepts_automatic_level,
    hours_gap,
    pending_suggestion,
    suggested_level,
    time_ratio,
)

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
    academic_year = models.CharField(
        "année universitaire",
        max_length=20,
        blank=True,
        help_text="Exemple : 2026-2027. Laissez vide pour une formation sans année scolaire.",
    )
    description = models.TextField("description", blank=True)
    status = models.CharField("état", max_length=12, choices=Status.choices, default=Status.ACTIVE)
    current_period = models.ForeignKey(
        "formations.Period",
        verbose_name="période en cours",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="current_for_paths",
        help_text="Met cette période en avant dans la formation, le tableau de bord et les sélecteurs.",
    )
    time_suggests_level = models.BooleanField(
        "paliers de temps",
        default=True,
        help_text=(
            "Quand le temps travaillé atteint un quart du travail estimé, proposer « découvert », "
            "puis « en cours », « acquis » et « maîtrisé » aux quarts suivants. "
            "Une proposition ne remplace jamais un niveau que vous avez déclaré."
        ),
    )
    weight_metric = models.ForeignKey(
        "formations.MetricDefinition",
        verbose_name="colonne de pondération",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="weighting_for",
        help_text=(
            "La colonne qui porte le poids des matières — ECTS, coefficient. "
            "Nécessaire pour calculer une moyenne de période ; laissez vide si cela n'a pas de sens."
        ),
    )
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = "formation"
        verbose_name_plural = "formations"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.current_period_id and self.current_period.path_id != self.pk:
            raise ValidationError({"current_period": "Cette période appartient à une autre formation."})


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


class LearningGroup(TimeStampedModel):
    """Un regroupement de matières à l'intérieur d'une période : UE, bloc, domaine.

    Facultatif, et c'est le point. Une licence universitaire organise ses matières en
    unités d'enseignement ; une formation courte n'a que des périodes et des matières.
    Rendre l'UE obligatoire aurait imposé la structure de l'Université de Guyane à toute
    formation ; ne pas la prévoir aurait obligé à la simuler dans les intitulés.

    Le type est un texte libre plutôt qu'une liste fermée : personne ne peut énumérer
    d'avance les découpages de toutes les formations. Des exemples sont proposés à la
    saisie.
    """

    KIND_SUGGESTIONS = ("UE", "Bloc", "Domaine", "Parcours", "Option")

    period = models.ForeignKey(Period, verbose_name="période", on_delete=models.CASCADE, related_name="groups")
    title = models.CharField("intitulé", max_length=180)
    code = models.CharField("code", max_length=40, blank=True, help_text="Référence de la maquette, si elle en a une.")
    kind = models.CharField("type", max_length=40, blank=True, help_text="UE, bloc, domaine… Laissez vide si inutile.")
    order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "regroupement"
        verbose_name_plural = "regroupements"
        ordering = ["order", "title"]
        constraints = [models.UniqueConstraint(fields=["period", "title"], name="unique_group_per_period")]

    def __str__(self):
        return f"{self.code} · {self.title}" if self.code else self.title


class LearningUnit(TimeStampedModel):
    period = models.ForeignKey(Period, verbose_name="période", on_delete=models.CASCADE, related_name="units")
    group = models.ForeignKey(
        LearningGroup,
        verbose_name="regroupement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="units",
        help_text="Facultatif : une formation sans UE laisse ce champ vide.",
    )
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
    """Ce qui doit être maîtrisé. Rattaché au parcours, travaillé dans une ou plusieurs matières.

    Le rattachement exclusif à une matière rendait impossible ce qui est courant : une
    même compétence travaillée dans deux matières. « Rédiger une démonstration au
    tableau » est un seul savoir-faire, exercé aux deux semestres ; le modèle en faisait
    deux compétences distinctes, avec deux suivis à tenir en parallèle et aucun moyen de
    savoir qu'il s'agissait de la même chose.

    La période reste facultative : elle situe une compétence dans le temps quand cela a
    un sens, sans l'y enfermer.
    """

    path = models.ForeignKey(
        LearningPath, verbose_name="formation", on_delete=models.CASCADE, related_name="competencies"
    )
    period = models.ForeignKey(
        Period,
        verbose_name="période",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="competencies",
        help_text="Facultatif : une compétence peut traverser plusieurs périodes.",
    )
    units = models.ManyToManyField(
        LearningUnit,
        verbose_name="matières",
        through="UnitCompetency",
        related_name="competencies",
        blank=True,
    )
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
        constraints = [models.UniqueConstraint(fields=["path", "title"], name="unique_competency_per_path")]

    def __str__(self):
        return self.title

    @property
    def primary_unit(self):
        """La matière où la compétence se travaille d'abord, s'il y en a une.

        Sert à la placer dans la grille de suivi : une compétence partagée n'y apparaît
        qu'une fois en saisie, sous cette matière, et se lit ailleurs.
        """
        link = self.unit_links.order_by("-is_primary", "unit__period__order", "order", "pk").first()
        return link.unit if link else None

    def clean(self):
        if self.period_id and self.period.path_id != self.path_id:
            raise ValidationError({"period": "Cette période appartient à une autre formation."})


class Assessment(TimeStampedModel):
    """Un devoir, un partiel, un oral : ce qui est évalué et quand.

    Séparé de son résultat, même dans un espace strictement personnel. On prépare un
    examen avant de connaître sa note : l'évaluation doit exister — avec sa date, ses
    compétences visées et ses ressources de révision — pendant tout le temps où il n'y a
    précisément rien à y inscrire.
    """

    class Kind(models.TextChoices):
        HOMEWORK = "homework", "Devoir maison"
        TEST = "test", "Contrôle"
        MIDTERM = "midterm", "Partiel"
        ORAL = "oral", "Oral"
        PROJECT = "project", "Projet"
        EXAM = "exam", "Examen"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        PLANNED = "planned", "Prévue"
        TAKEN = "taken", "Passée"
        MARKED = "marked", "Corrigée"
        CANCELLED = "cancelled", "Annulée"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessments")
    period = models.ForeignKey(
        Period, verbose_name="période", null=True, blank=True, on_delete=models.SET_NULL, related_name="assessments"
    )
    unit = models.ForeignKey(
        LearningUnit,
        verbose_name="matière",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assessments",
        help_text="Facultatif : un examen transversal n'en concerne aucune en particulier.",
    )
    title = models.CharField("intitulé", max_length=200)
    kind = models.CharField("type", max_length=10, choices=Kind.choices, default=Kind.TEST)
    scheduled_for = models.DateTimeField("date et heure", null=True, blank=True)
    coefficient = models.DecimalField(
        "coefficient",
        max_digits=6,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Poids de l'évaluation dans la moyenne de la matière.",
    )
    scale = models.DecimalField(
        "barème",
        max_digits=6,
        decimal_places=2,
        default=20,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="La note maximale possible : 20, 100, 5…",
    )
    status = models.CharField("état", max_length=10, choices=Status.choices, default=Status.PLANNED)
    description = models.TextField("description", blank=True)
    resources = models.ManyToManyField(
        "library.LibraryItem", verbose_name="ressources de préparation", blank=True, related_name="assessments"
    )
    competencies = models.ManyToManyField(
        Competency, verbose_name="compétences évaluées", blank=True, related_name="assessments"
    )

    class Meta:
        verbose_name = "évaluation"
        verbose_name_plural = "évaluations"
        ordering = ["-scheduled_for", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(coefficient__gte=0), name="assessment_coefficient_positive"),
            models.CheckConstraint(condition=models.Q(scale__gt=0), name="assessment_scale_positive"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.unit_id and self.unit.period.path.owner_id != self.owner_id:
            raise ValidationError({"unit": "Cette matière appartient à un autre utilisateur."})
        if self.period_id and self.period.path.owner_id != self.owner_id:
            raise ValidationError({"period": "Cette période appartient à un autre utilisateur."})

    @property
    def is_upcoming(self) -> bool:
        return bool(self.scheduled_for and self.status == self.Status.PLANNED and self.scheduled_for >= timezone.now())

    @property
    def days_left(self) -> int | None:
        if not self.scheduled_for:
            return None
        return (self.scheduled_for.date() - timezone.localdate()).days


class AssessmentResult(TimeStampedModel):
    """La note obtenue, séparée de l'évaluation qui l'a produite.

    Le barème est recopié au moment du résultat : changer le barème d'une évaluation
    passée ne doit pas réécrire une note déjà obtenue.
    """

    assessment = models.OneToOneField(
        Assessment, verbose_name="évaluation", on_delete=models.CASCADE, related_name="result"
    )
    score = models.DecimalField(
        "note obtenue",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Laissez vide en cas d'absence.",
    )
    scale = models.DecimalField(
        "barème appliqué",
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Repris de l'évaluation ; modifiable si le barème réel a différé.",
    )
    absent = models.BooleanField("absence", default=False)
    comment = models.TextField("commentaire du correcteur", blank=True)
    published_on = models.DateField("publiée le", null=True, blank=True)
    self_review = models.TextField(
        "mon appréciation",
        blank=True,
        help_text="Ce que vous en retenez : ce qui a manqué, ce qui a bien marché.",
    )

    class Meta:
        verbose_name = "résultat"
        verbose_name_plural = "résultats"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__isnull=True) | models.Q(score__gte=0), name="result_score_positive"
            ),
            models.CheckConstraint(condition=models.Q(scale__gt=0), name="result_scale_positive"),
        ]

    def __str__(self):
        if self.absent or self.score is None:
            return f"{self.assessment} · absent"
        return f"{self.assessment} · {self.score:f}/{self.scale:f}"

    def clean(self):
        if self.absent and self.score is not None:
            raise ValidationError({"score": "Une absence n'a pas de note. Décochez l'absence ou videz la note."})
        if self.score is not None and self.scale and self.score > self.scale:
            raise ValidationError({"score": f"La note dépasse le barème ({self.scale:f})."})

    @property
    def ratio(self) -> Decimal | None:
        """La note ramenée à une fraction de 1, ou ``None`` si elle n'existe pas."""
        if self.absent or self.score is None or not self.scale:
            return None
        return (self.score / self.scale).quantize(Decimal("0.0001"))

    @property
    def out_of_twenty(self) -> Decimal | None:
        ratio = self.ratio
        return None if ratio is None else (ratio * 20).quantize(Decimal("0.01"))


class UnitCompetency(models.Model):
    """Le lien entre une matière et une compétence, avec ce qui n'appartient qu'au lien.

    L'ordre dans la matière, le caractère principal ou secondaire et l'objectif local
    dépendent du couple, non de la compétence : « Rédiger une démonstration » est
    centrale au module d'oraux et secondaire ailleurs.
    """

    unit = models.ForeignKey(
        LearningUnit, verbose_name="matière", on_delete=models.CASCADE, related_name="competency_links"
    )
    competency = models.ForeignKey(
        Competency, verbose_name="compétence", on_delete=models.CASCADE, related_name="unit_links"
    )
    order = models.PositiveSmallIntegerField("ordre dans la matière", default=0)
    is_primary = models.BooleanField(
        "principale dans cette matière",
        default=True,
        help_text="Une compétence secondaire est rappelée sans être saisie ici.",
    )
    local_objective = models.CharField(
        "objectif local",
        max_length=240,
        blank=True,
        help_text="Ce qui est attendu dans cette matière en particulier, s'il y a une nuance.",
    )

    class Meta:
        verbose_name = "compétence de matière"
        verbose_name_plural = "compétences de matière"
        ordering = ["order", "competency__title"]
        constraints = [models.UniqueConstraint(fields=["unit", "competency"], name="unique_competency_per_unit_link")]

    def __str__(self):
        return f"{self.unit} · {self.competency}"

    def clean(self):
        if self.unit.period.path_id != self.competency.path_id:
            raise ValidationError("La matière et la compétence doivent appartenir à la même formation.")


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
    """La situation d'un étudiant sur une compétence — distincte de la compétence elle-même.

    ``Competency`` décrit ce qui doit être maîtrisé ; cet objet décrit où en est une
    personne. La séparation est maintenue exprès : la maquette ne change pas parce qu'un
    étudiant progresse.

    Le niveau n'est jamais déduit du temps travaillé. Avoir passé dix heures sur une notion
    ne prouve pas qu'on la maîtrise, et l'inverse est vrai aussi ; le calculer
    automatiquement produirait un chiffre faux dont l'étudiant ne pourrait rien faire.
    """

    class Origin(models.TextChoices):
        """D'où vient le niveau affiché.

        Un niveau proposé par l'application — par exemple à partir d'un résultat
        d'évaluation — ne doit pas se confondre avec celui que l'étudiant a posé lui-même.
        """

        MANUAL = "manual", "Déclaré par moi"
        SUGGESTED = "suggested", "Suggéré, à confirmer"

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
        "temps total (h)",
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    manual_hours = models.DecimalField(
        "temps saisi manuellement (h)",
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    session_hours = models.DecimalField(
        "temps des sessions Sablier (h)",
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        editable=False,
    )
    notes = models.TextField("commentaires", blank=True)
    assessed_at = models.DateTimeField(
        "dernière autoévaluation",
        null=True,
        blank=True,
        help_text="Renseignée automatiquement quand le niveau change.",
    )
    level_origin = models.CharField(
        "origine du niveau",
        max_length=10,
        choices=Origin.choices,
        default=Origin.MANUAL,
        help_text="Un niveau suggéré reste une proposition tant qu'il n'est pas confirmé.",
    )
    target_level = models.PositiveSmallIntegerField(
        "objectif de maîtrise",
        null=True,
        blank=True,
        choices=Mastery.choices,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text="Le niveau que vous visez, s'il diffère de la maîtrise complète.",
    )
    target_date = models.DateField("à atteindre le", null=True, blank=True, help_text="Une date d'examen, par exemple.")

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
            models.CheckConstraint(condition=models.Q(manual_hours__gte=0), name="progress_manual_hours_positive"),
            models.CheckConstraint(condition=models.Q(session_hours__gte=0), name="progress_session_hours_positive"),
        ]

    # Les valeurs retenues à la lecture, pour savoir plus tard ce qui a bougé.
    TRACKED_ON_LOAD = ("mastery_level", "actual_hours", "manual_hours", "session_hours")

    @classmethod
    def from_db(cls, db, field_names, values):
        """Retient les valeurs lues en base, sans jamais en réclamer d'autres.

        Les valeurs sont prises dans ``values`` et non sur l'instance : lire un attribut
        différé déclenche un rechargement, qui rappelle ``from_db``, qui relit l'attribut.
        Django diffère précisément les champs qu'il n'utilise pas — au ramassage d'une
        suppression en cascade, par exemple — et la lecture par attribut y partait en
        récursion infinie.

        Un champ absent ne laisse aucune valeur retenue, ce que ``save()`` interprète
        déjà comme « on ne sait pas ce qu'il valait ».
        """
        instance = super().from_db(db, field_names, values)
        # `strict` : Django appaire toujours les deux listes ; un écart serait un défaut
        # de la couche d'accès, à faire remonter plutôt qu'à tronquer en silence.
        loaded = dict(zip(field_names, values, strict=True))
        for name in cls.TRACKED_ON_LOAD:
            if name in loaded:
                setattr(instance, f"_loaded_{name}", loaded[name])
        return instance

    def save(self, *args, **kwargs):
        """Horodate l'autoévaluation quand, et seulement quand, le niveau change, puis
        laisse le temps travaillé proposer un palier.

        Une ligne créée d'office par la grille part à « non abordé » : rien n'a été évalué,
        la date reste vide. Sans cette nuance, toutes les compétences d'une formation
        paraîtraient évaluées le jour où l'on ouvre la grille pour la première fois.

        L'ordre compte. Le niveau déclaré est traité d'abord : il date l'autoévaluation et
        marque l'origine comme personnelle, ce qui ferme d'emblée la porte au palier. Le
        palier ne s'écrit donc que là où rien n'a été déclaré, et sans jamais toucher à
        ``assessed_at`` — voir ``formations.progression``.
        """
        previous = getattr(self, "_loaded_mastery_level", None)
        # Une écriture posée par `suggest_level()` vient d'une source extérieure — un
        # résultat d'évaluation — et non de l'étudiant : la traiter comme une déclaration
        # la daterait comme une autoévaluation et la mettrait à l'abri des paliers, ce
        # qu'aucune des deux n'a le droit de faire à la place de la personne.
        suggesting = getattr(self, "_suggested_write", False)
        changed = (previous != self.mastery_level if previous is not None else bool(self.mastery_level)) and (
            not suggesting
        )
        loaded_actual = getattr(self, "_loaded_actual_hours", None)
        loaded_manual = getattr(self, "_loaded_manual_hours", None)
        loaded_session = getattr(self, "_loaded_session_hours", None)
        direct_total_edit = (
            loaded_actual is not None
            and self.actual_hours != loaded_actual
            and self.manual_hours == loaded_manual
            and self.session_hours == loaded_session
        )
        if (
            self._state.adding and self.actual_hours and not self.manual_hours and not self.session_hours
        ) or direct_total_edit:
            # Compatibilité des scripts et imports historiques qui écrivent encore le
            # total : la part Sablier reste intacte, la différence devient manuelle.
            self.manual_hours = max(Decimal(0), self.actual_hours - self.session_hours)
        else:
            self.actual_hours = self.manual_hours + self.session_hours
        if changed:
            # Un niveau posé à la main est une appréciation personnelle : elle date
            # l'autoévaluation et reprend l'origine au palier, qui l'aurait sinon
            # réécrite à la session suivante.
            self.assessed_at = timezone.now()
            self.level_origin = self.Origin.MANUAL
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list({*update_fields, "assessed_at", "level_origin"})
        if accepts_automatic_level(self):
            proposed = suggested_level(self)
            if proposed is not None:
                self.mastery_level = proposed
                self.level_origin = self.Origin.SUGGESTED
                update_fields = kwargs.get("update_fields")
                if update_fields is not None:
                    kwargs["update_fields"] = list({*update_fields, "mastery_level", "level_origin"})
        # Le niveau qui précède l'écriture, retenu pour le journal. `previous` vaut None sur
        # une ligne neuve, où le point de départ est « non abordé ».
        departure = previous if previous is not None else self.Mastery.NOT_STARTED
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and ({"manual_hours", "session_hours", "actual_hours"} & set(update_fields)):
            kwargs["update_fields"] = list({*update_fields, "manual_hours", "actual_hours"})
        super().save(*args, **kwargs)
        if self.mastery_level != departure:
            # Après l'écriture seulement : un journal qui mentionnerait un niveau que la
            # transaction n'a pas retenu serait pire que pas de journal du tout.
            ProgressEvent.objects.create(
                record=self,
                previous_level=departure,
                level=self.mastery_level,
                origin=self.level_origin,
            )
        self._suggested_write = False
        self._loaded_mastery_level = self.mastery_level
        self._loaded_actual_hours = self.actual_hours
        self._loaded_manual_hours = self.manual_hours
        self._loaded_session_hours = self.session_hours

    @property
    def percent(self) -> int:
        """Progression affichée : le niveau de maîtrise rapporté à son maximum."""
        return round(self.mastery_level * 100 / 4)

    @property
    def reaches_target(self) -> bool | None:
        """L'objectif est-il atteint ? ``None`` quand aucun objectif n'est fixé."""
        if self.target_level is None:
            return None
        return self.mastery_level >= self.target_level

    @property
    def is_suggested(self) -> bool:
        """Le niveau affiché vient-il d'un palier de temps plutôt que d'une appréciation ?"""
        return self.level_origin == self.Origin.SUGGESTED

    @property
    def mastery_description(self) -> str:
        """Le critère observable du niveau courant, et non son seul nom."""
        return MASTERY_DESCRIPTIONS.get(self.mastery_level, "")

    @property
    def target_label(self) -> str:
        return dict(self.Mastery.choices).get(self.target_level, "") if self.target_level is not None else ""

    @property
    def days_to_target(self) -> int | None:
        """Jours restants avant la date visée, négatif une fois la date passée."""
        if self.target_date is None:
            return None
        return (self.target_date - timezone.localdate()).days

    @property
    def target_is_late(self) -> bool:
        """L'objectif est-il manqué : une date dépassée, un niveau pas encore atteint ?"""
        days = self.days_to_target
        return bool(self.target_level is not None and days is not None and days < 0 and not self.reaches_target)

    @property
    def hours_comment(self) -> str:
        """Le retour sur l'écart entre le temps estimé et le temps réellement passé."""
        return hours_gap(self)

    @property
    def pending_level(self) -> int | None:
        """Le niveau que le temps propose sans pouvoir l'écrire, faute d'y être autorisé."""
        return pending_suggestion(self)

    @property
    def pending_level_label(self) -> str:
        pending = self.pending_level
        return dict(self.Mastery.choices).get(pending, "") if pending is not None else ""

    @property
    def time_percent(self) -> int | None:
        """La part du temps estimé qui est écoulée, en pourcentage, ou ``None`` sans estimation."""
        ratio = time_ratio(self)
        return None if ratio is None else round(ratio * 100)

    def suggest_level(self, level: int) -> bool:
        """Pose un niveau proposé par une source extérieure — aujourd'hui un résultat.

        Mêmes garde-fous que les paliers de temps : ne fait que monter, ne s'écrit que là
        où rien n'a été déclaré, et n'horodate pas l'autoévaluation. Rend ``False`` quand
        la proposition n'a pas lieu d'être, à charge pour l'appelant de l'afficher.
        """
        if level <= self.mastery_level or not accepts_automatic_level(self):
            return False
        self._suggested_write = True
        self.mastery_level = level
        self.level_origin = self.Origin.SUGGESTED
        self.save(update_fields=["mastery_level", "level_origin", "updated_at"])
        return True

    def adopt_suggested_level(self) -> bool:
        """Fait sien le niveau proposé : il devient une appréciation personnelle et datée.

        Sert aux deux cas visibles à l'écran — confirmer un palier déjà appliqué, et
        adopter une proposition restée en attente parce qu'un niveau avait été déclaré.
        """
        proposed = suggested_level(self) if accepts_automatic_level(self) else self.pending_level
        target = max(self.mastery_level, proposed or 0)
        if target == self.mastery_level and self.level_origin == self.Origin.MANUAL:
            return False
        self.mastery_level = target
        self.level_origin = self.Origin.MANUAL
        self.assessed_at = timezone.now()
        self.save(update_fields=["mastery_level", "level_origin", "assessed_at", "updated_at"])
        return True

    def clean(self):
        if self.competency.path.owner_id != self.owner_id:
            raise ValidationError("La progression appartient à un autre utilisateur.")


class ProgressEvent(models.Model):
    """Un changement de niveau, conservé après coup.

    ``ProgressRecord`` ne garde que l'état courant : chaque écriture écrase la précédente.
    On ne pouvait donc ni tracer une courbe, ni répondre à « où j'en étais il y a un mois »,
    ni distinguer une compétence qui monte d'une qui stagne — alors que voir son propre
    progrès est ce qui soutient l'effort le plus sûrement.

    L'origine est conservée avec le niveau : une montée proposée par le temps et une montée
    déclarée après un exercice ne racontent pas la même chose, et les confondre dans une
    seule courbe la rendrait trompeuse.
    """

    record = models.ForeignKey(
        ProgressRecord, verbose_name="progression", on_delete=models.CASCADE, related_name="events"
    )
    previous_level = models.PositiveSmallIntegerField("niveau précédent", choices=ProgressRecord.Mastery.choices)
    level = models.PositiveSmallIntegerField("niveau atteint", choices=ProgressRecord.Mastery.choices)
    origin = models.CharField("origine", max_length=10, choices=ProgressRecord.Origin.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "changement de niveau"
        verbose_name_plural = "changements de niveau"
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["record", "created_at"], name="progress_event_record_idx")]

    def __str__(self):
        return f"{self.record.competency} : {self.previous_level} → {self.level}"

    @property
    def is_rise(self) -> bool:
        return self.level > self.previous_level

    @property
    def is_suggested(self) -> bool:
        return self.origin == ProgressRecord.Origin.SUGGESTED
