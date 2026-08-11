from django import forms

from core.forms import ScopedModelForm

from .models import CalendarEvent, Recurrence, Task


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%dT%H:%M")
        super().__init__(*args, **kwargs)


class RecurrenceMixin(forms.Form):
    """Champs de répétition, communs aux tâches et aux événements.

    La règle n'est pas stockée sur l'objet : elle sert une fois, à la création des
    occurrences. Chaque séance reste ensuite modifiable indépendamment.
    """

    repeat = forms.ChoiceField(label="Répétition", choices=Recurrence.choices, initial=Recurrence.NONE, required=False)
    repeat_until = forms.DateField(
        label="Répéter jusqu’au",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Laissez vide pour ne pas répéter.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Répéter ne veut rien dire sur une séance déjà créée : on modifierait une date
        # existante tout en en générant d'autres à partir d'elle.
        if getattr(self.instance, "pk", None):
            self.fields.pop("repeat", None)
            self.fields.pop("repeat_until", None)

    def clean(self):
        cleaned = super().clean()
        rule = cleaned.get("repeat") or Recurrence.NONE
        until = cleaned.get("repeat_until")
        if rule != Recurrence.NONE and not until:
            self.add_error("repeat_until", "Indiquez jusqu’à quand la répétition doit aller.")
        if until and rule == Recurrence.NONE:
            self.add_error("repeat", "Choisissez une répétition, ou effacez la date de fin.")
        return cleaned

    @property
    def recurrence(self):
        """(règle, date de fin) une fois le formulaire validé."""
        return self.cleaned_data.get("repeat") or Recurrence.NONE, self.cleaned_data.get("repeat_until")


class TaskForm(RecurrenceMixin, ScopedModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "status", "priority", "due_at", "reminder_at", "email_reminder"]
        widgets = {
            "due_at": DateTimeLocalInput(),
            "reminder_at": DateTimeLocalInput(),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("repeat") not in (None, "", Recurrence.NONE) and not cleaned.get("due_at"):
            self.add_error("due_at", "Une tâche qui se répète a besoin d’une échéance.")
        return cleaned


class CalendarEventForm(RecurrenceMixin, ScopedModelForm):
    class Meta:
        model = CalendarEvent
        fields = [
            "title",
            "description",
            "starts_at",
            "ends_at",
            "all_day",
            "location",
            "reminder_at",
            "email_reminder",
        ]
        widgets = {
            "starts_at": DateTimeLocalInput(),
            "ends_at": DateTimeLocalInput(),
            "reminder_at": DateTimeLocalInput(),
            "description": forms.Textarea(attrs={"rows": 4}),
        }
