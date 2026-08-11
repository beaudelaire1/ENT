from __future__ import annotations

from pathlib import Path

from django import forms
from django.conf import settings
from django.db.models import Sum

from accounts.models import UserProfile
from core.formatting import human_mb
from core.forms import ScopedModelForm

from .models import AudioTrack, FocusPreference, Playlist


class FocusPreferenceForm(forms.ModelForm):
    class Meta:
        model = FocusPreference
        fields = [
            "default_duration_seconds",
            "session_intention",
            "mode",
            "ambience",
            "focus_level",
            "warning_seconds",
            "decor_density",
            "end_sound_enabled",
            "custom_accent",
            "accent_color",
            "background_image",
        ]
        widgets = {
            "accent_color": forms.TextInput(attrs={"type": "color"}),
            "default_duration_seconds": forms.HiddenInput(),
        }

    def clean_background_image(self):
        image = self.cleaned_data.get("background_image")
        if image and getattr(image, "size", 0) > 8 * 1024 * 1024:
            raise forms.ValidationError("L’image dépasse 8 Mo.")
        return image


FORMATS = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".ogg": "audio/ogg"}


class MultipleFileInput(forms.ClearableFileInput):
    """Django refuse `multiple` sur un FileField ordinaire, faute de savoir quoi faire
    d'une liste. Ce widget et le champ ci-dessous assument ce choix explicitement."""

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True, "accept": "audio/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        uploads = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(upload, initial) for upload in uploads if upload]


class AudioUploadForm(forms.Form):
    """Téléversement de plusieurs pistes en une fois.

    Le titre de chaque piste vient du nom de son fichier : imposer une saisie par
    morceau reviendrait à rendre l'envoi groupé aussi lent que l'envoi un par un.
    """

    files = MultipleFileField(label="fichiers audio")
    artist = forms.CharField(label="artiste", max_length=180, required=False)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_files(self):
        uploads = self.cleaned_data.get("files") or []
        max_bytes = settings.AUDIO_MAX_TRACK_MB * 1024 * 1024
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        used = (
            AudioTrack.objects.filter(owner=self.user).counted_in_quota().aggregate(total=Sum("file_size"))["total"]
            or 0
        )
        quota = profile.audio_quota_mb * 1024 * 1024

        erreurs, cumul = [], 0
        for upload in uploads:
            suffix = Path(upload.name).suffix.lower()
            if suffix not in FORMATS:
                erreurs.append(f"{upload.name} : formats acceptés MP3, M4A/AAC et OGG.")
                continue
            if upload.size > max_bytes:
                erreurs.append(f"{upload.name} dépasse {human_mb(settings.AUDIO_MAX_TRACK_MB)}.")
                continue
            # Le quota se vérifie sur l'ensemble de la sélection, pas fichier par fichier :
            # dix pistes acceptables séparément peuvent le dépasser ensemble.
            if used + cumul + upload.size > quota:
                reste = max(0, quota - used - cumul) / 1024 / 1024
                erreurs.append(f"{upload.name} : quota dépassé, il reste {human_mb(reste)}.")
                continue
            cumul += upload.size
            upload.detected_mime = FORMATS[suffix]

        if erreurs:
            raise forms.ValidationError(erreurs)
        return uploads

    def save(self):
        """Crée une piste par fichier et renvoie la liste, pour mise en validation."""
        artist = self.cleaned_data.get("artist", "")
        tracks = []
        for upload in self.cleaned_data["files"]:
            tracks.append(
                AudioTrack.objects.create(
                    owner=self.user,
                    title=Path(upload.name).stem[:180],
                    artist=artist,
                    file=upload,
                    file_size=upload.size,
                    mime_type=upload.detected_mime,
                    status=AudioTrack.Status.VALIDATING,
                )
            )
        return tracks


class PlaylistForm(ScopedModelForm):
    class Meta:
        model = Playlist
        fields = ["title", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class AddTrackForm(forms.Form):
    track = forms.ModelChoiceField(queryset=AudioTrack.objects.none(), label="Piste")

    def __init__(self, *args, user=None, playlist=None, **kwargs):
        super().__init__(*args, **kwargs)
        existing = playlist.tracks.values_list("pk", flat=True) if playlist else []
        self.fields["track"].queryset = AudioTrack.objects.filter(owner=user, status=AudioTrack.Status.READY).exclude(
            pk__in=existing
        )
