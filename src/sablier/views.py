from __future__ import annotations

import json
import uuid
from datetime import timedelta
from pathlib import Path

import boto3
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Sum
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.models import UserProfile
from core.deletion import confirm_delete
from core.formatting import human_mb
from core.queue import enqueue
from formations.models import Competency

from . import scenes
from .forms import AddTrackForm, AudioUploadForm, FocusPreferenceForm, PlaylistForm
from .models import AudioTrack, FocusPreference, Playlist, PlaylistTrack
from .services import record_session
from .tasks import validate_audio_track


def sablier_asset_version() -> str:
    """Empreinte des ressources de Sablier : la date de la plus récente."""
    folder = settings.BASE_DIR / "static" / "sablier"
    stamps = [path.stat().st_mtime for path in folder.glob("*.*") if path.suffix in {".js", ".css"}]
    return str(int(max(stamps))) if stamps else "0"


@login_required
@never_cache
def home(request):
    # Page entièrement personnelle, et dont les ressources changent souvent : la laisser
    # en cache renvoyait un écran périmé qu'il fallait actualiser pour voir ses réglages.
    preference, _ = FocusPreference.objects.get_or_create(user=request.user)
    form = FocusPreferenceForm(request.POST or None, request.FILES or None, instance=preference)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Ambiance enregistrée.")
        return redirect("sablier:home")
    playlists = Playlist.objects.filter(owner=request.user).prefetch_related("playlist_tracks__track")
    playlist_payload = [
        {
            "id": playlist.pk,
            "title": playlist.title,
            "tracks": [
                {
                    "id": entry.track_id,
                    "title": entry.track.title,
                    "artist": entry.track.artist,
                    "url": f"/sablier/audio/{entry.track_id}/stream/",
                }
                for entry in playlist.playlist_tracks.all()
                if entry.track.status == AudioTrack.Status.READY
            ],
        }
        for playlist in playlists
    ]
    # Rattacher une session à une compétence reste facultatif : Sablier fonctionne
    # entièrement sans le module Formations.
    competencies = (
        Competency.objects.filter(path__owner=request.user)
        .select_related("path", "period")
        .prefetch_related("unit_links__unit")
    )
    return render(
        request,
        "sablier/home.html",
        {
            "preference": preference,
            "form": form,
            "playlists": playlists,
            "playlist_payload": playlist_payload,
            "ambience_choices": FocusPreference.Ambience.choices,
            "palette_css": scenes.palette_css(),
            "decors": {scene.key: scene.decor for scene in scenes.SCENES},
            # Les feuilles et scripts de Sablier changent souvent : sans cette empreinte,
            # le navigateur servirait l'ancienne version après chaque correction.
            "asset_version": sablier_asset_version(),
            # À la seconde près, un enregistrement survenu dans la même seconde que
            # le chargement serait indétectable côté navigateur.
            "saved_at": f"{preference.updated_at.timestamp():.6f}",
            "competencies": competencies,
            "recent_sessions": request.user.focus_sessions.select_related("competency")[:5],
        },
    )


@login_required
def audio_library(request):
    form = AudioUploadForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        tracks = form.save()
        for track in tracks:
            enqueue(validate_audio_track, track.pk)
        messages.success(
            request,
            f"{len(tracks)} piste{'s' if len(tracks) > 1 else ''} téléversée{'s' if len(tracks) > 1 else ''} "
            "et mise en validation."
            if len(tracks) > 1
            else "Piste téléversée et mise en validation.",
        )
        return redirect("sablier:audio")
    used = (
        AudioTrack.objects.filter(owner=request.user).counted_in_quota().aggregate(total=Sum("file_size"))["total"] or 0
    )
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    used_mb = used / 1024 / 1024
    return render(
        request,
        "sablier/audio.html",
        {
            "form": form,
            "tracks": AudioTrack.objects.filter(owner=request.user),
            "used": human_mb(used_mb),
            "quota": human_mb(profile.audio_quota_mb),
            "remaining": human_mb(max(0, profile.audio_quota_mb - used_mb)),
            "max_track": human_mb(settings.AUDIO_MAX_TRACK_MB),
            "used_percent": min(100, round(used_mb * 100 / profile.audio_quota_mb)) if profile.audio_quota_mb else 0,
        },
    )


@login_required
def audio_stream(request, pk):
    track = get_object_or_404(AudioTrack, owner=request.user, pk=pk, status=AudioTrack.Status.READY)
    if not track.file:
        raise Http404
    storage = track.file.storage
    if hasattr(storage, "bucket"):
        return redirect(track.file.url)
    response = FileResponse(track.file.open("rb"), content_type=track.mime_type)
    response["Accept-Ranges"] = "bytes"
    return response


@login_required
def track_delete(request, pk):
    track = get_object_or_404(AudioTrack, owner=request.user, pk=pk)
    return confirm_delete(request, track, redirect_to=reverse("sablier:audio"), title="Supprimer cette piste")


@login_required
def playlist_delete(request, pk):
    playlist = get_object_or_404(Playlist, owner=request.user, pk=pk)
    return confirm_delete(
        request,
        playlist,
        redirect_to=reverse("sablier:playlists"),
        title="Supprimer cette playlist",
        back_to=reverse("sablier:playlist_detail", args=[playlist.pk]),
    )


@login_required
def playlist_list(request):
    return render(request, "sablier/playlists.html", {"playlists": Playlist.objects.filter(owner=request.user)})


@login_required
def playlist_edit(request, pk=None):
    playlist = get_object_or_404(Playlist, owner=request.user, pk=pk) if pk else None
    form = PlaylistForm(request.POST or None, instance=playlist, scope={"owner": request.user})
    if request.method == "POST" and form.is_valid():
        playlist = form.save()
        return redirect("sablier:playlist_detail", pk=playlist.pk)
    return render(request, "sablier/playlist_form.html", {"form": form, "playlist": playlist})


@login_required
def playlist_detail(request, pk):
    playlist = get_object_or_404(Playlist.objects.prefetch_related("playlist_tracks__track"), owner=request.user, pk=pk)
    add_form = AddTrackForm(request.POST or None, user=request.user, playlist=playlist)
    if request.method == "POST" and add_form.is_valid():
        position = (playlist.playlist_tracks.aggregate(max=Max("position"))["max"] or -1) + 1
        PlaylistTrack.objects.create(playlist=playlist, track=add_form.cleaned_data["track"], position=position)
        return redirect("sablier:playlist_detail", pk=playlist.pk)
    return render(request, "sablier/playlist_detail.html", {"playlist": playlist, "add_form": add_form})


@login_required
@require_POST
def playlist_remove_track(request, pk, entry_pk):
    playlist = get_object_or_404(Playlist, owner=request.user, pk=pk)
    get_object_or_404(PlaylistTrack, playlist=playlist, pk=entry_pk).delete()
    return redirect("sablier:playlist_detail", pk=playlist.pk)


@login_required
@require_POST
def presign_audio(request):
    if not settings.USE_S3:
        return JsonResponse({"error": "Le téléversement direct S3 n’est actif qu’en production."}, status=400)
    try:
        data = json.loads(request.body)
        filename = Path(data["filename"]).name
        size = int(data["size"])
        mime = data["content_type"]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return JsonResponse({"error": "Requête invalide."}, status=400)
    allowed = {"audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/aac": ".aac", "audio/ogg": ".ogg"}
    if mime not in allowed or size > settings.AUDIO_MAX_TRACK_MB * 1024 * 1024:
        return JsonResponse({"error": "Format ou taille refusé."}, status=400)
    used = (
        AudioTrack.objects.filter(owner=request.user).counted_in_quota().aggregate(total=Sum("file_size"))["total"] or 0
    )
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    quota = profile.audio_quota_mb * 1024 * 1024
    if used + size > quota:
        return JsonResponse({"error": "Quota audio dépassé."}, status=400)
    key = f"users/{request.user.pk}/audio/{uuid.uuid4().hex}{allowed[mime]}"
    track = AudioTrack.objects.create(
        owner=request.user,
        title=Path(filename).stem[:180],
        file=key,
        mime_type=mime,
        file_size=size,
        status=AudioTrack.Status.UPLOADING,
    )
    client = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    post = client.generate_presigned_post(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Fields={"Content-Type": mime},
        Conditions=[{"Content-Type": mime}, ["content-length-range", 1, settings.AUDIO_MAX_TRACK_MB * 1024 * 1024]],
        ExpiresIn=900,
    )
    return JsonResponse({"track_id": track.pk, "upload": post})


@login_required
@require_POST
def log_session(request):
    """Enregistre une session terminée, envoyée par le minuteur."""
    try:
        data = json.loads(request.body)
        seconds = int(data["seconds"])
        intention = str(data.get("intention") or "")
        competency_id = data.get("competency")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return JsonResponse({"error": "Requête invalide."}, status=400)
    if not 1 <= seconds <= 86400:
        return JsonResponse({"error": "Durée hors limites."}, status=400)

    competency = None
    if competency_id:
        competency = Competency.objects.filter(pk=competency_id, path__owner=request.user).first()
        if competency is None:
            return JsonResponse({"error": "Compétence inconnue."}, status=400)

    session = record_session(
        request.user,
        seconds=seconds,
        started_at=timezone.now() - timedelta(seconds=seconds),
        intention=intention,
        competency=competency,
    )
    return JsonResponse(
        {
            "ok": True,
            "hours": str(session.hours),
            "competency": competency.title if competency else None,
        }
    )


@login_required
@require_POST
def confirm_audio(request, pk):
    track = get_object_or_404(AudioTrack, owner=request.user, pk=pk, status=AudioTrack.Status.UPLOADING)
    track.status = AudioTrack.Status.VALIDATING
    track.save(update_fields=["status", "updated_at"])
    enqueue(validate_audio_track, track.pk)
    return JsonResponse({"ok": True})
