from celery import shared_task
from mutagen import File as MutagenFile
from mutagen import MutagenError

from .models import AudioTrack


@shared_task(bind=True, autoretry_for=(OSError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def validate_audio_track(self, track_id: int):
    track = AudioTrack.objects.get(pk=track_id)
    try:
        with track.file.open("rb") as stream:
            metadata = MutagenFile(stream)
            if metadata is None or not getattr(metadata, "info", None):
                raise ValueError("Format audio illisible.")
            track.duration_seconds = max(1, round(metadata.info.length))
        track.status = AudioTrack.Status.READY
        track.rejection_reason = ""
    # MutagenError couvre les fichiers tronqués ou dont l'extension ment sur le contenu.
    # Sans lui, la tâche plantait au lieu de refuser la piste, qui restait alors
    # indéfiniment « en validation » — inutilisable et impossible à débloquer.
    except (ValueError, TypeError, MutagenError) as exc:
        track.status = AudioTrack.Status.REJECTED
        track.rejection_reason = str(exc)[:240] or "Fichier audio illisible."
    track.save(update_fields=["duration_seconds", "status", "rejection_reason", "updated_at"])
    return track.status
