"""Export personnel lisible et structurellement fidèle, sans secret ni binaire volumineux."""

from __future__ import annotations

from django.utils import timezone

from formations.catalog import export_catalog


def _rows(queryset, *fields):
    return list(queryset.values(*fields))


def export_account(user):
    from formations.models import Assessment, AssessmentResult, LearningPath, ProgressEvent, ProgressRecord
    from library.models import Folder, LibraryItem, Tag
    from notifications.models import Notification
    from planner.models import CalendarEvent, Task, TaskFocus, TaskSeries
    from sablier.models import AudioTrack, FocusPreference, FocusSession, Playlist, PlaylistTrack

    profile = getattr(user, "profile", None)
    formation_rows = []
    for path in LearningPath.objects.filter(owner=user):
        formation_rows.append(
            {
                "structure": export_catalog(path),
                "progress": _rows(
                    ProgressRecord.objects.filter(owner=user, competency__path=path),
                    "competency_id",
                    "competency__title",
                    "mastery_level",
                    "planned_hours",
                    "manual_hours",
                    "session_hours",
                    "actual_hours",
                    "notes",
                    "target_level",
                    "target_date",
                    "assessed_at",
                    "level_origin",
                ),
                "level_history": _rows(
                    ProgressEvent.objects.filter(record__owner=user, record__competency__path=path),
                    "record__competency_id",
                    "record__competency__title",
                    "previous_level",
                    "level",
                    "origin",
                    "created_at",
                ),
            }
        )

    assessments = Assessment.objects.filter(owner=user)
    items = LibraryItem.objects.filter(owner=user).prefetch_related("tags")
    audio_tracks = AudioTrack.objects.filter(owner=user)
    playlists = Playlist.objects.filter(owner=user)

    return {
        "schema": "myent.account-export",
        "version": 2,
        "exported_at": timezone.now(),
        "notice": (
            "Les fichiers de bibliothèque, images de fond et pistes audio ne sont pas inclus en binaire. "
            "Leur nom, leur clé de stockage et leurs métadonnées sont exportés afin que l'archive décrive "
            "fidèlement les relations du compte."
        ),
        "account": {
            "username": user.get_username(),
            "email": user.email,
            "date_joined": user.date_joined,
            "profile": (
                {
                    "display_name": profile.display_name,
                    "theme": profile.theme,
                    "accent_color": profile.accent_color,
                    "timezone": profile.timezone,
                    "email_verified_at": profile.email_verified_at,
                }
                if profile
                else None
            ),
        },
        "formations": formation_rows,
        "assessments": _rows(
            assessments,
            "id",
            "period_id",
            "unit_id",
            "title",
            "kind",
            "scheduled_for",
            "coefficient",
            "scale",
            "status",
            "description",
        ),
        "results": _rows(
            AssessmentResult.objects.filter(assessment__owner=user),
            "assessment_id",
            "score",
            "scale",
            "absent",
            "comment",
            "published_on",
            "self_review",
        ),
        "library": {
            "folders": _rows(Folder.objects.filter(owner=user), "id", "parent_id", "name"),
            "tags": _rows(Tag.objects.filter(owner=user), "id", "name", "color"),
            "items": [
                {
                    "id": item.pk,
                    "folder_id": item.folder_id,
                    "tags": list(item.tags.values_list("name", flat=True)),
                    "kind": item.kind,
                    "purpose": item.purpose,
                    "title": item.title,
                    "description": item.description,
                    "url": item.url,
                    "file_name": item.file.name if item.file else "",
                    "file_size": item.file_size,
                    "mime_type": item.mime_type,
                    "note_delta": item.note_delta,
                    "note_text": item.note_text,
                    "note_html": item.note_html,
                    "provider_name": item.provider_name,
                    "source_category": item.source_category,
                }
                for item in items
            ],
        },
        "planner": {
            "task_series": _rows(
                TaskSeries.objects.filter(owner=user),
                "id",
                "recurrence",
                "repeat_until",
            ),
            "tasks": _rows(
                Task.objects.filter(owner=user),
                "id",
                "series_id",
                "series_position",
                "title",
                "description",
                "status",
                "priority",
                "due_at",
                "reminder_at",
                "email_reminder",
                "unit_id",
                "competency_id",
                "assessment_id",
            ),
            "task_focuses": _rows(
                TaskFocus.objects.filter(owner=user),
                "task_id",
                "scope",
                "period_start",
            ),
            "events": _rows(
                CalendarEvent.objects.filter(owner=user),
                "id",
                "series_id",
                "title",
                "description",
                "starts_at",
                "ends_at",
                "all_day",
                "location",
                "reminder_at",
                "email_reminder",
                "unit_id",
                "competency_id",
                "assessment_id",
            ),
        },
        "sablier": {
            "preferences": _rows(
                FocusPreference.objects.filter(user=user),
                "default_duration_seconds",
                "session_intention",
                "mode",
                "ambience",
                "focus_level",
                "warning_seconds",
                "decor_density",
                "end_sound_enabled",
                "accent_color",
                "custom_accent",
                "background_image",
            ),
            "sessions": _rows(
                FocusSession.objects.filter(owner=user),
                "client_id",
                "competency_id",
                "intention",
                "started_at",
                "ended_at",
                "seconds",
                "counted_at",
                "excluded_at",
            ),
            "audio_tracks": _rows(
                audio_tracks,
                "id",
                "title",
                "artist",
                "file",
                "mime_type",
                "file_size",
                "duration_seconds",
                "status",
                "rejection_reason",
                "created_at",
                "updated_at",
            ),
            "playlists": _rows(playlists, "id", "title", "description", "created_at", "updated_at"),
            "playlist_tracks": _rows(
                PlaylistTrack.objects.filter(playlist__owner=user),
                "playlist_id",
                "track_id",
                "position",
            ),
        },
        "notifications": _rows(
            Notification.objects.filter(owner=user), "kind", "title", "message", "url", "read_at", "created_at"
        ),
    }
