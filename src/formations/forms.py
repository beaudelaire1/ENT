from decimal import Decimal

from django import forms

from core.forms import ScopedModelForm

from .models import (
    Assessment,
    AssessmentResult,
    Competency,
    LearningGroup,
    LearningPath,
    LearningUnit,
    MetricDefinition,
    Period,
    ProgressRecord,
    UnitCompetency,
)


def annotate(form, helps: dict[str, str], placeholders: dict[str, str] | None = None) -> None:
    """Pose les textes d'aide et les exemples sur un formulaire.

    Ils vivent ici et non sur le modèle : ce sont des indications d'écran, qui changent
    sans que la base ait à être migrée. Un champ dont l'intitulé suffit n'en reçoit pas —
    une aide qui répète le libellé n'aide personne.
    """
    for name, text in helps.items():
        if name in form.fields:
            form.fields[name].help_text = text
    for name, example in (placeholders or {}).items():
        if name in form.fields:
            form.fields[name].widget.attrs.setdefault("placeholder", example)


class LearningPathForm(ScopedModelForm):
    class Meta:
        model = LearningPath
        # Ordonnés par intention : ce qu'est la formation, puis comment elle se présente.
        fields = ["title", "level_label", "training_type", "description", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        annotate(
            self,
            {
                "level_label": "Le niveau tel que vous le nommez : L3, Master 1, BTS 2e année…",
                "training_type": "Universitaire, professionnelle, autoformation… Laissez vide si cela n’a pas de sens.",
                "status": "Une formation en pause ou terminée reste consultable et sort du premier plan.",
            },
            {
                "title": "Licence 3 Mathématiques",
                "level_label": "L3",
                "training_type": "Universitaire",
            },
        )


class PeriodForm(ScopedModelForm):
    class Meta:
        model = Period
        fields = ["title", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        annotate(
            self,
            {
                "title": "Semestre, année, bloc, trimestre : le découpage de votre formation.",
                "order": "Sert à ranger les périodes ; l’ordre alphabétique placerait « Semestre 10 » avant « Semestre 5 ».",
            },
            {"title": "Semestre 5"},
        )


class LearningUnitForm(ScopedModelForm):
    class Meta:
        model = LearningUnit
        fields = ["title", "description", "group", "order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user=None, period=None, **kwargs):
        super().__init__(*args, **kwargs)
        if period is not None:
            # Seuls les regroupements de la même période : une UE du semestre 6 n'a rien à
            # faire dans la liste d'une matière du semestre 5.
            self.fields["group"].queryset = LearningGroup.objects.filter(period=period)
        annotate(
            self,
            {
                "order": "Position dans la période, pour retrouver l’ordre de la maquette.",
                "group": "UE, bloc ou domaine auquel la matière appartient. Facultatif.",
            },
            {"title": "Topologie"},
        )


class LearningGroupForm(ScopedModelForm):
    class Meta:
        model = LearningGroup
        fields = ["title", "code", "kind", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        annotate(
            self,
            {
                "title": "L’intitulé du regroupement, tel qu’il figure sur la maquette.",
                "kind": "Exemples : " + ", ".join(LearningGroup.KIND_SUGGESTIONS) + ".",
            },
            {"title": "UEO Mathématiques 5", "code": "UEO5", "kind": "UE"},
        )


class CompetencyForm(ScopedModelForm):
    """Une compétence appartient à la formation ; la période est facultative."""

    class Meta:
        model = Competency
        fields = ["title", "description", "period", "order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, path=None, **kwargs):
        super().__init__(*args, **kwargs)
        if path is not None:
            self.fields["period"].queryset = Period.objects.filter(path=path)
        annotate(
            self,
            {
                "title": "Ce qui doit être maîtrisé, formulé comme un savoir-faire.",
                "description": "Ce que vous devez savoir faire précisément. Utile pour vous relire dans six mois.",
                "period": "Laissez vide pour une compétence qui traverse plusieurs périodes.",
            },
            {"title": "Déterminer si un espace est compact"},
        )


class UnitCompetencyForm(ScopedModelForm):
    """Le lien entre une matière et une compétence, et ce qui n'appartient qu'au lien."""

    class Meta:
        model = UnitCompetency
        fields = ["order", "is_primary", "local_objective"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        annotate(
            self,
            {
                "is_primary": "Décochez si la compétence est seulement rappelée ici : "
                "elle se saisira alors dans la matière où elle est principale.",
            },
        )


class MetricDefinitionForm(ScopedModelForm):
    class Meta:
        model = MetricDefinition
        fields = ["key", "label", "unit_label", "order", "min_value", "max_value", "decimal_places"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Une nouvelle colonne part d'un minimum à zéro : un coefficient, des ECTS ou des
        # heures de TD ne sont jamais négatifs. La borne reste effaçable pour les colonnes
        # qui mesurent un écart.
        if self.instance.pk is None and "min_value" not in self.data:
            self.fields["min_value"].initial = 0
        annotate(
            self,
            {
                "key": "Identifiant interne, sans espace ni accent. Il ne s’affiche pas dans la grille.",
                "label": "Le titre de la colonne, tel qu’il apparaît en haut de la grille.",
                "unit_label": "Unité affichée entre parenthèses : h, j, ECTS…",
                "order": "Position de la colonne dans la grille.",
            },
            {"key": "coefficient", "label": "Coefficient", "unit_label": "h"},
        )


# Une durée se tape avec le séparateur décimal du clavier de l'utilisateur, donc la
# virgule en français. Django ne la convertit que sur un champ localisé, et un
# `input type="number"` la refuserait quand même en vidant la case sans un mot : les
# durées se saisissent donc dans un champ texte à pavé numérique.
HOURS_WIDGET_ATTRS = {"inputmode": "decimal", "class": "cell-number"}


class HoursInput(forms.TextInput):
    """Champ de durée : virgule acceptée à la saisie, zéros inutiles absents à l'affichage.

    La localisation d'un ``DecimalField`` écrit « 25,00 » là où l'utilisateur avait tapé
    « 25 ». Sur une grille entière, ces décimales vides rendent les colonnes illisibles.
    """

    def format_value(self, value):
        if isinstance(value, Decimal):
            # `format(..., "f")` évite la notation exponentielle que `normalize()`
            # produit sur les multiples de dix (25 → 2.5E+1).
            value = Decimal(format(value.normalize(), "f"))
        return super().format_value(value)


class ProgressForm(ScopedModelForm):
    class Meta:
        model = ProgressRecord
        fields = ["mastery_level", "target_level", "target_date", "planned_hours", "actual_hours", "notes"]
        localized_fields = ("planned_hours", "actual_hours")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "planned_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
            "actual_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        annotate(
            self,
            {
                "mastery_level": "Votre appréciation, pas une note : elle sert à repérer ce qui reste à travailler.",
                "planned_hours": "Le temps que vous pensez devoir y consacrer, en heures. La virgule est acceptée.",
                "actual_hours": "Le temps déjà passé dessus.",
                "notes": "Ce qui bloque, ce qu’il reste à revoir, un renvoi vers un exercice.",
                "target_level": "Le niveau visé. Toutes les compétences ne demandent pas la maîtrise complète.",
                "target_date": "Une date d’examen, par exemple.",
            },
        )


class ProgressRowForm(forms.ModelForm):
    """Une ligne de la grille de suivi : édition en place, sans quitter le tableau."""

    class Meta:
        model = ProgressRecord
        fields = ["planned_hours", "actual_hours", "mastery_level", "notes"]
        localized_fields = ("planned_hours", "actual_hours")
        widgets = {
            "planned_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
            "actual_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
            "mastery_level": forms.Select(attrs={"class": "cell-level", "data-level-select": ""}),
            "notes": forms.TextInput(attrs={"placeholder": "Notes…", "class": "cell-notes"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le numéro reste visible dans le sélecteur : c’est lui qu’on lit en diagonale.
        self.fields["mastery_level"].choices = [
            (value, f"{value} - {label}") for value, label in ProgressRecord.Mastery.choices
        ]
        for field in self.fields.values():
            field.label = ""


ProgressRowFormSet = forms.modelformset_factory(ProgressRecord, form=ProgressRowForm, extra=0)


class AssessmentForm(ScopedModelForm):
    """Une évaluation : ce qui est évalué, quand, et avec quel poids.

    Les compétences évaluées ne se choisissent pas ici mais sur un écran dédié : une
    formation en compte plusieurs centaines, et une liste de cases n'y serait pas
    utilisable.
    """

    class Meta:
        model = Assessment
        fields = ["title", "kind", "period", "unit", "scheduled_for", "coefficient", "scale", "status", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["period"].queryset = Period.objects.filter(path__owner=user).select_related("path")
        self.fields["unit"].queryset = LearningUnit.objects.filter(period__path__owner=user).select_related("period")
        self.fields["scheduled_for"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]
        annotate(
            self,
            {
                "unit": "La matière concernée. Laissez vide pour une épreuve transversale.",
                "coefficient": "Poids dans la moyenne de la matière. 0 pour une évaluation qui ne compte pas.",
                "scale": "La note maximale : 20, 100, 5…",
                "status": "« Prévue » tant que l’épreuve n’a pas eu lieu.",
                "scheduled_for": "Sert à décompter les jours restants et à préparer la révision.",
            },
            {"title": "Partiel de topologie"},
        )

    def clean(self):
        cleaned = super().clean()
        unit, period = cleaned.get("unit"), cleaned.get("period")
        if unit and period and unit.period_id != period.pk:
            # Deux rattachements qui se contredisent produiraient une évaluation
            # introuvable : ni dans la période affichée, ni dans celle de la matière.
            self.add_error("period", "Cette matière appartient à une autre période.")
        if unit and not period:
            cleaned["period"] = unit.period
            self.instance.period = unit.period
        return cleaned


class AssessmentResultForm(ScopedModelForm):
    """Le résultat, saisi séparément de l'évaluation qu'il conclut."""

    class Meta:
        model = AssessmentResult
        fields = ["score", "scale", "absent", "published_on", "comment", "self_review"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 2}),
            "self_review": forms.Textarea(attrs={"rows": 3}),
            "published_on": forms.DateInput(attrs={"type": "date"}),
        }
        localized_fields = ("score", "scale")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        annotate(
            self,
            {
                "score": "Laissez vide en cas d’absence : elle ne sera jamais comptée comme un zéro.",
                "scale": "Repris de l’évaluation ; corrigez-le si le barème réel a différé.",
                "self_review": "Ce que vous en retenez. C’est ce qui servira à décider quoi reprendre.",
            },
        )
