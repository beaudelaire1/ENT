from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from kombu.exceptions import OperationalError

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

    def test_an_unsupported_extension_never_reaches_the_task(self):
        with patch.object(validate_audio_track, "delay") as delay:
            response = self.upload(name="morceau.wav")

        self.assertEqual(response.status_code, 200)
        delay.assert_not_called()
        self.assertEqual(AudioTrack.objects.count(), 0)
