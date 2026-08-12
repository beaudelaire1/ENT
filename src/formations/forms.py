import json
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


class FormationTemplateForm(forms.Form):
    title = forms.CharField(label="Titre de votre formation", max_length=180)
    academic_year = forms.CharField(label="Année universitaire", max_length=20, required=False)

    def __init__(self, *args, initial_title="", **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].initial = initial_title
        self.fields["academic_year"].widget.attrs["placeholder"] = "2026-2027"


class FormationImportForm(forms.Form):
    catalog = forms.FileField(
        label="Fichier de formation (.json)",
        help_text="Export MyENT au format JSON, 2 Mo au maximum.",
    )

    def clean_catalog(self):
        uploaded = self.cleaned_data["catalog"]
        if uploaded.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Ce fichier dépasse la limite de 2 Mo.")
        try:
            return json.loads(uploaded.read().decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise forms.ValidationError("Ce fichier n'est pas un document JSON valide.") from exc


class FormationImportConfirmForm(forms.Form):
    payload = forms.CharField(widget=forms.HiddenInput)
    title = forms.CharField(label="Titre de votre formation", max_length=180)
    academic_year = forms.CharField(label="Année universitaire", max_length=20, required=False)

    def clean_payload(self):
        try:
            return json.loads(self.cleaned_data["payload"])
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("L'aperçu a expiré : sélectionnez de nouveau le fichier.") from exc


class FormationDuplicateForm(forms.Form):
    title = forms.CharField(label="Titre de la copie", max_length=180)


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
        fields = [
            "title",
            "level_label",
            "training_type",
            "academic_year",
            "current_period",
            "description",
            "status",
            "time_suggests_level",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["current_period"].queryset = (
            Period.objects.filter(path=self.instance).order_by("order", "title")
            if self.instance.pk
            else Period.objects.none()
        )
        annotate(
            self,
            {
                "level_label": "Le niveau tel que vous le nommez : L3, Master 1, BTS 2e année…",
                "training_type": "Universitaire, professionnelle, autoformation… Laissez vide si cela n’a pas de sens.",
                "academic_year": "L’année de référence, au format 2026-2027. Facultative.",
                "current_period": "La période affichée en priorité. Vous pourrez la choisir après avoir créé les périodes.",
                "status": "Une formation en pause ou terminée reste consultable et sort du premier plan.",
                "time_suggests_level": (
                    "Décochez si l’estimation horaire n’a pas de sens dans cette formation : "
                    "aucun niveau ne sera plus proposé à partir du temps travaillé."
                ),
            },
            {
                "title": "Licence 3 Mathématiques",
                "level_label": "L3",
                "training_type": "Universitaire",
                "academic_year": "2026-2027",
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
        fields = ["mastery_level", "target_level", "target_date", "planned_hours", "manual_hours", "notes"]
        localized_fields = ("planned_hours", "manual_hours")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "planned_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
            "manual_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        args, kwargs = _accept_legacy_actual_hours(args, kwargs)
        super().__init__(*args, **kwargs)
        _repair_legacy_time_initial(self)
        annotate(
            self,
            {
                "mastery_level": "Votre appréciation, pas une note : elle sert à repérer ce qui reste à travailler.",
                "planned_hours": "Le temps que vous pensez devoir y consacrer, en heures. La virgule est acceptée.",
                "manual_hours": "Le temps saisi par vous. Les sessions Sablier sont comptées séparément.",
                "notes": "Ce qui bloque, ce qu’il reste à revoir, un renvoi vers un exercice.",
                "target_level": "Le niveau visé. Toutes les compétences ne demandent pas la maîtrise complète.",
                "target_date": "Une date d’examen, par exemple.",
            },
        )


class ProgressRowForm(forms.ModelForm):
    """Une ligne de la grille de suivi : édition en place, sans quitter le tableau."""

    class Meta:
        model = ProgressRecord
        fields = ["planned_hours", "manual_hours", "mastery_level", "notes"]
        localized_fields = ("planned_hours", "manual_hours")
        widgets = {
            "planned_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
            "manual_hours": HoursInput(attrs=HOURS_WIDGET_ATTRS),
            "mastery_level": forms.Select(attrs={"class": "cell-level", "data-level-select": ""}),
            "notes": forms.TextInput(attrs={"placeholder": "Notes…", "class": "cell-notes"}),
        }

    def __init__(self, *args, **kwargs):
        args, kwargs = _accept_legacy_actual_hours(args, kwargs)
        super().__init__(*args, **kwargs)
        _repair_legacy_time_initial(self)
        # Le numéro reste visible dans le sélecteur : c’est lui qu’on lit en diagonale.
        self.fields["mastery_level"].choices = [
            (value, f"{value} - {label}") for value, label in ProgressRecord.Mastery.choices
        ]
        for field in self.fields.values():
            field.label = ""


def _accept_legacy_actual_hours(args, kwargs):
    """Transition douce des anciens POST ``actual_hours`` vers ``manual_hours``."""
    data = args[0] if args else kwargs.get("data")
    if data is None:
        return args, kwargs
    prefix = kwargs.get("prefix")
    old_name = f"{prefix}-actual_hours" if prefix else "actual_hours"
    new_name = f"{prefix}-manual_hours" if prefix else "manual_hours"
    if old_name not in data or new_name in data:
        return args, kwargs
    copied = data.copy()
    copied[new_name] = data.get(old_name)
    if args:
        args = (copied, *args[1:])
    else:
        kwargs["data"] = copied
    return args, kwargs


def _repair_legacy_time_initial(form):
    """Rend lisible une ligne écrite par un ancien ``QuerySet.update(actual_hours=…)``."""
    instance = form.instance
    expected = instance.manual_hours + instance.session_hours
    if instance.actual_hours != expected and instance.actual_hours >= instance.session_hours:
        form.initial["manual_hours"] = instance.actual_hours - instance.session_hours


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
