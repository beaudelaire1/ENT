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
            "soundscape_enabled",
            "end_sound_enabled",
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


class AudioTrackForm(ScopedModelForm):
    class Meta:
        model = AudioTrack
        fields = ["title", "artist", "file"]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        kwargs.setdefault("scope", {"owner": user})
        super().__init__(*args, **kwargs)

    def clean_file(self):
        upload = self.cleaned_data.get("file")
        if not upload:
            return upload
        max_bytes = settings.AUDIO_MAX_TRACK_MB * 1024 * 1024
        if upload.size > max_bytes:
            raise forms.ValidationError(f"La piste dépasse {human_mb(settings.AUDIO_MAX_TRACK_MB)}.")
        suffix = Path(upload.name).suffix.lower()
        allowed = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".ogg": "audio/ogg"}
        if suffix not in allowed:
            raise forms.ValidationError("Formats acceptés : MP3, M4A/AAC et OGG.")
        used = (
            AudioTrack.objects.filter(owner=self.user).counted_in_quota().aggregate(total=Sum("file_size"))["total"]
            or 0
        )
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        quota_mb = profile.audio_quota_mb
        if used + upload.size > quota_mb * 1024 * 1024:
            remaining = max(0, quota_mb * 1024 * 1024 - used) / 1024 / 1024
            raise forms.ValidationError(
                f"Le quota audio de {human_mb(quota_mb)} serait dépassé : il reste {human_mb(remaining)}."
            )
        upload.detected_mime = allowed[suffix]
        return upload

    def save(self, commit=True):
        track = super().save(commit=False)
        upload = self.cleaned_data["file"]
        track.file_size = upload.size
        track.mime_type = upload.detected_mime
        track.status = AudioTrack.Status.VALIDATING
        if commit:
            track.save()
        return track


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
