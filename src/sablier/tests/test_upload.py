from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from kombu.exceptions import OperationalError

from accounts.models import UserProfile
from sablier.forms import AudioTrackForm
from sablier.models import AudioTrack
from sablier.tasks import validate_audio_track


@override_settings(MEDIA_ROOT="/tmp/myent-test-audio")
class AudioUploadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def upload(self, name="morceau.mp3", content=b"x" * 2048):
        return self.client.post(
            reverse("sablier:audio"),
            {"title": "Essai", "artist": "Moi", "file": SimpleUploadedFile(name, content)},
        )

    def test_an_unreadable_file_is_rejected_not_crashed(self):
        """mutagen lève ses propres exceptions ; non rattrapées, la piste restait
        bloquée en « validation », comptée dans le quota et impossible à débloquer."""
        with patch.object(validate_audio_track, "delay", side_effect=OperationalError("Redis absent")):
            response = self.upload()

        self.assertEqual(response.status_code, 302)
        track = AudioTrack.objects.get(owner=self.user)
        self.assertEqual(track.status, AudioTrack.Status.REJECTED)
        self.assertTrue(track.rejection_reason)

    def test_an_unreachable_broker_does_not_break_the_upload(self):
        with patch.object(validate_audio_track, "delay", side_effect=OperationalError("Redis absent")):
            response = self.upload()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AudioTrack.objects.filter(owner=self.user).count(), 1)

    def test_a_refused_track_frees_the_quota_again(self):
        with patch.object(validate_audio_track, "delay", side_effect=OperationalError("Redis absent")):
            self.upload()

        used = AudioTrack.objects.filter(owner=self.user).counted_in_quota().count()
        self.assertEqual(used, 0)

    @override_settings(AUDIO_MAX_TRACK_MB=1024)
    def test_a_track_just_under_one_gigabyte_is_accepted(self):
        """La limite par piste est bien lue en octets et non tronquée en route."""
        from django.core.files.uploadedfile import SimpleUploadedFile as Upload

        oversized = Upload("gros.mp3", b"")
        oversized.size = 1024 * 1024 * 1024 - 1  # 1 Go moins un octet

        form = AudioTrackForm(data={"title": "Gros", "artist": ""}, files={"file": oversized}, user=self.user)
        form.is_valid()

        self.assertNotIn("file", form.errors)

    @override_settings(AUDIO_MAX_TRACK_MB=1024)
    def test_a_track_over_the_limit_is_refused_with_a_readable_size(self):
        from django.core.files.uploadedfile import SimpleUploadedFile as Upload

        oversized = Upload("gros.mp3", b"")
        oversized.size = 1024 * 1024 * 1024 + 1  # 1 Go et un octet

        form = AudioTrackForm(data={"title": "Trop gros", "artist": ""}, files={"file": oversized}, user=self.user)
        form.is_valid()

        self.assertIn("1 Go", str(form.errors["file"]))
        self.assertNotIn("1024 Mo", str(form.errors["file"]))

    def test_the_quota_message_says_what_is_left(self):
        from django.core.files.uploadedfile import SimpleUploadedFile as Upload

        UserProfile.objects.update_or_create(user=self.user, defaults={"audio_quota_mb": 100})
        AudioTrack.objects.create(
            owner=self.user,
            title="Déjà là",
            file="users/1/audio/x.mp3",
            mime_type="audio/mpeg",
            file_size=90 * 1024 * 1024,
            status=AudioTrack.Status.READY,
        )
        upload = Upload("gros.mp3", b"")
        upload.size = 20 * 1024 * 1024

        form = AudioTrackForm(data={"title": "Trop", "artist": ""}, files={"file": upload}, user=self.user)
        form.is_valid()

        self.assertIn("il reste 10 Mo", str(form.errors["file"]))

    def test_an_unsupported_extension_never_reaches_the_task(self):
        with patch.object(validate_audio_track, "delay") as delay:
            response = self.upload(name="morceau.wav")

        self.assertEqual(response.status_code, 200)
        delay.assert_not_called()
        self.assertEqual(AudioTrack.objects.count(), 0)
