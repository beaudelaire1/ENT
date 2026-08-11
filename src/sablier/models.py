from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from core.models import TimeStampedModel

color_validator = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Couleur hexadécimale invalide.")


def focus_background_path(instance, filename):
    return f"users/{instance.user_id}/sablier/backgrounds/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def audio_upload_path(instance, filename):
    return f"users/{instance.owner_id}/audio/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class FocusPreference(models.Model):
    class Mode(models.TextChoices):
        RING = "ring", "Anneau"
        HOURGLASS = "hourglass", "Sablier"
        WAVE = "wave", "Marée"
        CANDLE = "candle", "Bougie"
        BEADS = "beads", "Perles"
        MOON = "moon", "Lune"
        BARS = "bars", "Colonnes"
        SPIRAL = "spiral", "Spirale"
        SUN = "sun", "Soleil"
        DIGITAL = "digital", "Digital"
        ZEN = "zen", "Zen"

    class Decor(models.IntegerChoices):
        """Densité du décor animé, jusqu'à l'absence totale.

        Un décor qui bouge aide certains à s'installer et en distrait d'autres ; le
        choix reste à l'utilisateur plutôt qu'imposé par l'ambiance.
        """

        NONE = 0, "Aucun décor"
        LIGHT = 1, "Léger"
        NORMAL = 2, "Normal"
        DENSE = 3, "Dense"

    class Ambience(models.TextChoices):
        """Palette, décor animé et paysage sonore de chacune sont dans scenes.py.

        Les deux listes doivent rester identiques ; un test s'en assure.
        """

        CONCENTRATION = "concentration", "Concentration"
        PRINTEMPS = "printemps", "Printemps"
        ETE = "ete", "Été"
        AUTOMNE = "automne", "Automne"
        HIVER = "hiver", "Hiver"
        PLUIE = "pluie", "Pluie"
        OCEAN = "ocean", "Océan"
        SAHARA = "sahara", "Sahara"
        FORET = "foret", "Forêt"
        ORAGE = "orage", "Orage"
        BRAISES = "braises", "Braises"
        AURORE = "aurore", "Aurore"
        NUIT = "nuit", "Nuit"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="focus_preference")
    default_duration_seconds = models.PositiveIntegerField(
        "durée par défaut (s)", default=300, validators=[MinValueValidator(1), MaxValueValidator(86400)]
    )
    session_intention = models.CharField("intention", max_length=80, blank=True)
    mode = models.CharField("visualisation", max_length=16, choices=Mode.choices, default=Mode.HOURGLASS)
    ambience = models.CharField("ambiance", max_length=16, choices=Ambience.choices, default=Ambience.CONCENTRATION)
    focus_level = models.PositiveSmallIntegerField(
        "niveau de concentration", default=2, validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    warning_seconds = models.PositiveSmallIntegerField(
        "alerte finale (s)", default=60, validators=[MinValueValidator(10), MaxValueValidator(180)]
    )
    decor_density = models.PositiveSmallIntegerField("densité du décor", choices=Decor.choices, default=Decor.NORMAL)
    end_sound_enabled = models.BooleanField("son de fin", default=True)
    accent_color = models.CharField("couleur d’accent", max_length=7, default="#8878FF", validators=[color_validator])
    # Sans ce choix explicite, une couleur enregistrée écraserait celle de l'ambiance
    # et l'on retomberait sur le défaut d'origine : quatre ambiances pour un seul rendu.
    custom_accent = models.BooleanField("utiliser ma couleur plutôt que celle de l’ambiance", default=False)
    background_image = models.ImageField("image de fond", upload_to=focus_background_path, blank=True)
    # Sert d'arbitre entre le serveur et le navigateur : voir sablier.js.
    updated_at = models.DateTimeField("enregistré le", auto_now=True)

    class Meta:
        verbose_name = "préférence Sablier"
        verbose_name_plural = "préférences Sablier"

    def __str__(self):
        return f"Sablier · {self.user}"


class AudioTrackQuerySet(models.QuerySet):
    def counted_in_quota(self):
        """Seules les pistes utilisables consomment le quota.

        Une piste refusée ou dont le téléversement n'a jamais abouti n'est écoutable
        nulle part ; la compter reviendrait à retenir du quota pour rien, sans que
        l'utilisateur puisse comprendre pourquoi son espace se remplit.
        """
        return self.exclude(status__in=(AudioTrack.Status.REJECTED, AudioTrack.Status.UPLOADING))


class AudioTrack(TimeStampedModel):
    class Status(models.TextChoices):
        UPLOADING = "uploading", "Téléversement"
        VALIDATING = "validating", "Validation"
        READY = "ready", "Prête"
        REJECTED = "rejected", "Refusée"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="audio_tracks")
    title = models.CharField("titre", max_length=180)
    artist = models.CharField("artiste", max_length=180, blank=True)
    file = models.FileField("fichier", upload_to=audio_upload_path)
    mime_type = models.CharField("type MIME", max_length=80)
    file_size = models.PositiveBigIntegerField("taille", default=0)
    duration_seconds = models.PositiveIntegerField("durée (s)", default=0)
    status = models.CharField("état", max_length=12, choices=Status.choices, default=Status.VALIDATING)
    rejection_reason = models.CharField("motif du refus", max_length=240, blank=True)
    objects = AudioTrackQuerySet.as_manager()

    class Meta:
        verbose_name = "piste audio"
        verbose_name_plural = "pistes audio"
        ordering = ["title", "pk"]

    def __str__(self):
        return self.title


class Playlist(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists")
    title = models.CharField("titre", max_length=160)
    description = models.TextField("description", blank=True)
    tracks = models.ManyToManyField(
        AudioTrack, verbose_name="pistes", through="PlaylistTrack", related_name="playlists"
    )

    class Meta:
        verbose_name = "playlist"
        verbose_name_plural = "playlists"
        ordering = ["title"]
        constraints = [models.UniqueConstraint(fields=["owner", "title"], name="unique_playlist_title_per_user")]

    def __str__(self):
        return self.title


class FocusSession(TimeStampedModel):
    """Une session de concentration terminée.

    Le minuteur vivait jusqu'ici dans le seul `localStorage` du navigateur : fermer
    l'onglet effaçait la séance. Le journal existe pour une raison précise — reporter
    le temps réellement travaillé sur la compétence visée, plutôt que de le ressaisir
    de mémoire dans la grille de suivi.

    Il ne sert pas à noter l'utilisateur : aucune statistique n'en est tirée.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="focus_sessions")
    competency = models.ForeignKey(
        "formations.Competency",
        verbose_name="compétence",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="focus_sessions",
    )
    intention = models.CharField("intention", max_length=80, blank=True)
    started_at = models.DateTimeField("début")
    seconds = models.PositiveIntegerField("durée (s)", validators=[MinValueValidator(1), MaxValueValidator(86400)])
    counted_at = models.DateTimeField("reportée le", null=True, blank=True)

    class Meta:
        verbose_name = "session de concentration"
        verbose_name_plural = "sessions de concentration"
        ordering = ["-started_at"]

    @property
    def hours(self) -> Decimal:
        """Durée en heures, arrondie au centième — l'unité de la grille de suivi."""
        return (Decimal(self.seconds) / Decimal(3600)).quantize(Decimal("0.01"))

    @property
    def minutes(self) -> int:
        return round(self.seconds / 60)

    def __str__(self):
        return f"{self.intention or 'Session'} · {self.seconds // 60} min"


class PlaylistTrack(models.Model):
    playlist = models.ForeignKey(
        Playlist, verbose_name="playlist", on_delete=models.CASCADE, related_name="playlist_tracks"
    )
    track = models.ForeignKey(
        AudioTrack, verbose_name="piste", on_delete=models.CASCADE, related_name="playlist_entries"
    )
    position = models.PositiveSmallIntegerField("position", default=0)

    class Meta:
        verbose_name = "piste de playlist"
        verbose_name_plural = "pistes de playlist"
        ordering = ["position", "pk"]
        constraints = [models.UniqueConstraint(fields=["playlist", "track"], name="unique_track_per_playlist")]

    def __str__(self):
        return f"{self.playlist} · {self.track}"
