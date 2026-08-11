from django.conf import settings
from django.db import models

from core.models import OwnedQuerySet


class DashboardWidget(models.Model):
    class Kind(models.TextChoices):
        TODAY = "today", "Aujourd’hui"
        TASKS = "tasks", "Tâches prioritaires"
        REMINDERS = "reminders", "Rappels"
        RECENT = "recent", "Contenus récents"
        FORMATIONS = "formations", "Formations"
        QUICK_NOTE = "quick_note", "Note rapide"
        SABLIER = "sablier", "Sablier"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_widgets")
    kind = models.CharField("bloc", max_length=24, choices=Kind.choices)
    position = models.PositiveSmallIntegerField("position", default=0)
    visible = models.BooleanField("visible", default=True)
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = "bloc du tableau de bord"
        verbose_name_plural = "blocs du tableau de bord"
        ordering = ["position", "pk"]
        constraints = [models.UniqueConstraint(fields=["owner", "kind"], name="unique_widget_per_user")]

    def __str__(self):
        return self.get_kind_display()
