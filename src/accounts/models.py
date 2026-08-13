from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

accent_validator = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Utilisez une couleur hexadécimale, par ex. #7C6CFF.")


class UserProfile(models.Model):
    class Theme(models.TextChoices):
        SYSTEM = "system", "Système"
        LIGHT = "light", "Clair"
        DARK = "dark", "Sombre"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField("nom affiché", max_length=120, blank=True)
    theme = models.CharField("thème", max_length=10, choices=Theme.choices, default=Theme.SYSTEM)
    accent_color = models.CharField("couleur d’accent", max_length=7, default="#7C6CFF", validators=[accent_validator])
    timezone = models.CharField("fuseau horaire", max_length=64, default="America/Cayenne")
    audio_quota_mb = models.PositiveIntegerField(
        "quota audio (Mo)",
        default=settings.AUDIO_DEFAULT_QUOTA_MB,
        help_text=(
            "Un compte administrateur bénéficie au minimum de AUDIO_ADMIN_QUOTA_MB, "
            "quelle que soit la valeur inscrite ici."
        ),
    )
    email_verified_at = models.DateTimeField("email vérifié le", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "profil"
        verbose_name_plural = "profils"

    def __str__(self):
        return self.display_name or self.user.get_username()

    @property
    def effective_audio_quota_mb(self) -> int:
        """Le quota réellement appliqué, plancher administrateur compris.

        Un compte administrateur dépose la musique de l'établissement, pas seulement la
        sienne : le quota ordinaire n'a pas de sens pour lui. Le plancher est appliqué au
        calcul plutôt qu'écrit dans la colonne, pour deux raisons — un compte promu
        administrateur en bénéficie aussitôt sans qu'on pense à modifier son profil, et un
        compte rétrogradé retrouve le quota commun sans qu'il reste une valeur oubliée.

        `max` et non un remplacement : un quota relevé à la main pour un administrateur
        particulier ne doit pas être rabaissé au plancher.
        """
        floor = getattr(settings, "AUDIO_ADMIN_QUOTA_MB", 0) if self.user.is_superuser else 0
        return max(self.audio_quota_mb, floor)


class Invitation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField("adresse email", db_index=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="invité par", on_delete=models.CASCADE, related_name="sent_invitations"
    )
    expires_at = models.DateTimeField("expire le")
    accepted_at = models.DateTimeField("acceptée le", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "invitation"
        verbose_name_plural = "invitations"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return self.accepted_at is None and self.expires_at > timezone.now()
