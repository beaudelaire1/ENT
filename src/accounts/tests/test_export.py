from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from formations.models import LearningPath
from library.models import LibraryItem
from planner.models import Recurrence, Task, TaskFocus, TaskSeries
from sablier.models import AudioTrack, Playlist, PlaylistTrack


class AccountExportTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user(
            "alice", email="alice@example.com", password="not-exported-secret"
        )
        self.bob = get_user_model().objects.create_user("bob", password="private")
        LearningPath.objects.create(owner=self.alice, title="Licence Alice")
        LibraryItem.objects.create(owner=self.alice, kind="note", title="Note Alice", note_text="contenu")
        LibraryItem.objects.create(owner=self.bob, kind="note", title="Secret Bob", note_text="privé")
        self.client.force_login(self.alice)

    def test_export_is_personal_and_contains_no_authentication_secret(self):
        response = self.client.get(reverse("accounts:export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        payload = response.json()
        rendered = response.content.decode()
        self.assertEqual(payload["schema"], "myent.account-export")
        self.assertEqual(payload["version"], 2)
        self.assertIn("Licence Alice", rendered)
        self.assertIn("Note Alice", rendered)
        self.assertNotIn("Secret Bob", rendered)
        self.assertNotIn("not-exported-secret", rendered)
        self.assertNotIn("password", rendered.lower())

    def test_export_preserves_task_series_focus_and_audio_playlist_structure(self):
        series = TaskSeries.objects.create(
            owner=self.alice,
            recurrence=Recurrence.WEEKLY,
            repeat_until=date(2026, 12, 31),
        )
        task = Task.objects.create(
            owner=self.alice,
            series=series,
            series_position=2,
            title="Réviser l’algèbre",
        )
        TaskFocus.objects.create(
            owner=self.alice,
            task=task,
            scope=TaskFocus.Scope.WEEK,
            period_start=date(2026, 9, 7),
        )
        track = AudioTrack.objects.create(
            owner=self.alice,
            title="Concentration",
            artist="Artiste",
            file="users/1/audio/concentration.mp3",
            mime_type="audio/mpeg",
            file_size=1234,
            duration_seconds=180,
            status=AudioTrack.Status.READY,
        )
        playlist = Playlist.objects.create(owner=self.alice, title="Travail")
        PlaylistTrack.objects.create(playlist=playlist, track=track, position=4)

        payload = self.client.get(reverse("accounts:export")).json()

        self.assertEqual(payload["planner"]["task_series"][0]["recurrence"], Recurrence.WEEKLY)
        self.assertEqual(payload["planner"]["tasks"][0]["series_position"], 2)
        self.assertEqual(payload["planner"]["task_focuses"][0]["scope"], TaskFocus.Scope.WEEK)
        self.assertEqual(payload["sablier"]["audio_tracks"][0]["title"], "Concentration")
        self.assertEqual(payload["sablier"]["playlist_tracks"][0]["position"], 4)
        self.assertEqual(payload["sablier"]["playlist_tracks"][0]["track_id"], track.pk)

    def test_export_requires_authentication(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("accounts:export")).status_code, 302)
