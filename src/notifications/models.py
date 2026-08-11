from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        REMINDER = "reminder", "Rappel"
        SYSTEM = "system", "Système"
        INVITATION = "invitation", "Invitation"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField("type", max_length=16, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField("titre", max_length=180)
    message = models.TextField("message", blank=True)
    url = models.CharField("lien", max_length=500, blank=True)
    dedupe_key = models.CharField("clé de déduplication", max_length=120)
    read_at = models.DateTimeField("lue le", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["owner", "dedupe_key"], name="unique_notification_dedupe")]

    def __str__(self):
        return self.title


class EmailDelivery(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_deliveries")
    dedupe_key = models.CharField("clé de déduplication", max_length=120)
    recipient = models.EmailField("destinataire")
    subject = models.CharField("objet", max_length=180)
    sent_at = models.DateTimeField("envoyé le", null=True, blank=True)
    last_error = models.TextField("dernière erreur", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "envoi email"
        verbose_name_plural = "envois email"
        constraints = [models.UniqueConstraint(fields=["owner", "dedupe_key"], name="unique_email_dedupe")]

    def __str__(self):
        return f"{self.subject} → {self.recipient}"
