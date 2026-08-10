from __future__ import annotations

import uuid
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
        DIGITAL = "digital", "Digital"
        ZEN = "zen", "Zen"

    class Ambience(models.TextChoices):
        CONCENTRATION = "concentration", "Concentration"
        CALM = "calm", "Calme"
        ENERGY = "energy", "Énergie"
        NIGHT = "night", "Nocturne"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="focus_preference")
    default_duration_seconds = models.PositiveIntegerField(
        default=300, validators=[MinValueValidator(1), MaxValueValidator(86400)]
    )
    session_intention = models.CharField(max_length=80, blank=True)
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.HOURGLASS)
    ambience = models.CharField(max_length=16, choices=Ambience.choices, default=Ambience.CONCENTRATION)
    focus_level = models.PositiveSmallIntegerField(default=2, validators=[MinValueValidator(1), MaxValueValidator(3)])
    warning_seconds = models.PositiveSmallIntegerField(
        default=60, validators=[MinValueValidator(10), MaxValueValidator(180)]
    )
    soundscape_enabled = models.BooleanField(default=False)
    end_sound_enabled = models.BooleanField(default=True)
    accent_color = models.CharField(max_length=7, default="#8878FF", validators=[color_validator])
    background_image = models.ImageField(upload_to=focus_background_path, blank=True)

    def __str__(self):
        return f"Sablier · {self.user}"


class AudioTrack(TimeStampedModel):
    class Status(models.TextChoices):
        UPLOADING = "uploading", "Téléversement"
        VALIDATING = "validating", "Validation"
        READY = "ready", "Prête"
        REJECTED = "rejected", "Refusée"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="audio_tracks")
    title = models.CharField(max_length=180)
    artist = models.CharField(max_length=180, blank=True)
    file = models.FileField(upload_to=audio_upload_path)
    mime_type = models.CharField(max_length=80)
    file_size = models.PositiveBigIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.VALIDATING)
    rejection_reason = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["title", "pk"]

    def __str__(self):
        return self.title


class Playlist(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    tracks = models.ManyToManyField(AudioTrack, through="PlaylistTrack", related_name="playlists")

    class Meta:
        ordering = ["title"]
        constraints = [models.UniqueConstraint(fields=["owner", "title"], name="unique_playlist_title_per_user")]

    def __str__(self):
        return self.title


class PlaylistTrack(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="playlist_tracks")
    track = models.ForeignKey(AudioTrack, on_delete=models.CASCADE, related_name="playlist_entries")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [models.UniqueConstraint(fields=["playlist", "track"], name="unique_track_per_playlist")]
