from django import forms

from .models import CalendarEvent, Task


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%dT%H:%M")
        super().__init__(*args, **kwargs)


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "status", "priority", "due_at", "reminder_at", "email_reminder"]
        widgets = {
            "due_at": DateTimeLocalInput(),
            "reminder_at": DateTimeLocalInput(),
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class CalendarEventForm(forms.ModelForm):
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
