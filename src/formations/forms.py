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
        fields = ["key", "label", "unit_label", "order"]


class ProgressForm(ScopedModelForm):
    class Meta:
        model = ProgressRecord
        fields = ["mastery_level", "planned_hours", "actual_hours", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class ProgressRowForm(forms.ModelForm):
    """Une ligne de la grille de suivi : édition en place, sans quitter le tableau."""

    class Meta:
        model = ProgressRecord
        fields = ["planned_hours", "actual_hours", "mastery_level", "notes"]
        widgets = {
            "planned_hours": forms.NumberInput(attrs={"min": 0, "step": "0.5", "class": "cell-number"}),
            "actual_hours": forms.NumberInput(attrs={"min": 0, "step": "0.5", "class": "cell-number"}),
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
