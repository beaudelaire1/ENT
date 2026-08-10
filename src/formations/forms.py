from django import forms

from library.models import LibraryItem

from .models import Competency, LearningPath, LearningUnit, MetricDefinition, MetricValue, Period, ProgressRecord


class LearningPathForm(forms.ModelForm):
    class Meta:
        model = LearningPath
        fields = ["title", "training_type", "level_label", "description", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class PeriodForm(forms.ModelForm):
    class Meta:
        model = Period
        fields = ["title", "order"]


class LearningUnitForm(forms.ModelForm):
    class Meta:
        model = LearningUnit
        fields = ["title", "description", "order", "resources"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "resources": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resources"].queryset = LibraryItem.objects.filter(owner=user)


class CompetencyForm(forms.ModelForm):
    class Meta:
        model = Competency
        fields = ["title", "description", "order", "resources"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "resources": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resources"].queryset = LibraryItem.objects.filter(owner=user)


class MetricDefinitionForm(forms.ModelForm):
    class Meta:
        model = MetricDefinition
        fields = ["key", "label", "unit_label", "order"]


class MetricValueForm(forms.ModelForm):
    class Meta:
        model = MetricValue
        fields = ["definition", "value"]

    def __init__(self, *args, path=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["definition"].queryset = MetricDefinition.objects.filter(path=path)


class ProgressForm(forms.ModelForm):
    class Meta:
        model = ProgressRecord
        fields = ["mastery_level", "planned_hours", "actual_hours", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
