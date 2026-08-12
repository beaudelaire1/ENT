from decimal import Decimal

from django import forms

from core.forms import ScopedModelForm
from library.models import LibraryItem

from .models import Competency, LearningPath, LearningUnit, MetricDefinition, Period, ProgressRecord


class LearningPathForm(ScopedModelForm):
    class Meta:
        model = LearningPath
        fields = ["title", "training_type", "level_label", "description", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class PeriodForm(ScopedModelForm):
    class Meta:
        model = Period
        fields = ["title", "order"]


class LearningUnitForm(ScopedModelForm):
    class Meta:
        model = LearningUnit
        fields = ["title", "description", "order", "resources"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "resources": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resources"].queryset = LibraryItem.objects.filter(owner=user)


class CompetencyForm(ScopedModelForm):
    class Meta:
        model = Competency
        fields = ["title", "description", "order", "resources"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "resources": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resources"].queryset = LibraryItem.objects.filter(owner=user)


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
        fields = ["mastery_level", "planned_hours", "actual_hours", "notes"]
        localized_fields = ("planned_hours", "actual_hours")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "planned_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
            "actual_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
        }


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
