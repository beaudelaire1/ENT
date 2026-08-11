from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from kombu.exceptions import OperationalError

from accounts.models import UserProfile
from sablier.forms import AudioUploadForm
from sablier.models import AudioTrack
from sablier.tasks import validate_audio_track


def fichier(nom="morceau.mp3", octets=2048):
    return SimpleUploadedFile(nom, b"x" * octets)


@override_settings(MEDIA_ROOT="/tmp/myent-test-audio")
class AudioUploadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def envoyer(self, *fichiers, artist=""):
        with patch.object(validate_audio_track, "delay", side_effect=OperationalError("Redis absent")):
            return self.client.post(reverse("sablier:audio"), {"files": list(fichiers), "artist": artist})

    def test_several_tracks_arrive_in_one_go(self):
        response = self.envoyer(fichier("un.mp3"), fichier("deux.mp3"), fichier("trois.ogg"), artist="Moi")

        self.assertEqual(response.status_code, 302)
        pistes = AudioTrack.objects.filter(owner=self.user)
        self.assertEqual(pistes.count(), 3)
        self.assertEqual({p.title for p in pistes}, {"un", "deux", "trois"})
        self.assertTrue(all(p.artist == "Moi" for p in pistes))

    def test_a_single_track_still_works(self):
        self.assertEqual(self.envoyer(fichier("seul.mp3")).status_code, 302)
        self.assertEqual(AudioTrack.objects.get(owner=self.user).title, "seul")

    def test_one_bad_file_blocks_the_whole_batch(self):
        """Sinon l'utilisateur croit tout envoyé alors qu'une partie manque."""
        response = self.envoyer(fichier("bon.mp3"), fichier("mauvais.txt"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mauvais.txt")
        self.assertEqual(AudioTrack.objects.count(), 0)

    def test_the_quota_is_measured_across_the_whole_selection(self):
        """Dix pistes acceptables séparément peuvent dépasser le quota ensemble."""
        UserProfile.objects.update_or_create(user=self.user, defaults={"audio_quota_mb": 1})
        gros = 400 * 1024

        response = self.envoyer(fichier("a.mp3", gros), fichier("b.mp3", gros), fichier("c.mp3", gros))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quota")
        self.assertEqual(AudioTrack.objects.count(), 0)

    def test_an_unreadable_file_is_rejected_not_crashed(self):
        """mutagen lève ses propres exceptions ; non rattrapées, la piste restait
        bloquée en « validation », comptée dans le quota et impossible à débloquer."""
        self.envoyer(fichier("faux.mp3"))

        track = AudioTrack.objects.get(owner=self.user)
        self.assertEqual(track.status, AudioTrack.Status.REJECTED)
        self.assertTrue(track.rejection_reason)

    def test_a_refused_track_frees_the_quota_again(self):
        self.envoyer(fichier("faux.mp3"))
        self.assertEqual(AudioTrack.objects.filter(owner=self.user).counted_in_quota().count(), 0)

    @override_settings(AUDIO_MAX_TRACK_MB=1024)
    def test_a_track_just_under_one_gigabyte_is_accepted(self):
        gros = fichier("gros.mp3", 1)
        gros.size = 1024 * 1024 * 1024 - 1

        form = AudioUploadForm(data={"artist": ""}, files={"files": [gros]}, user=self.user)

        self.assertTrue(form.is_valid(), form.errors)

    @override_settings(AUDIO_MAX_TRACK_MB=1024)
    def test_a_track_over_the_limit_is_refused_with_a_readable_size(self):
        gros = fichier("gros.mp3", 1)
        gros.size = 1024 * 1024 * 1024 + 1

        form = AudioUploadForm(data={"artist": ""}, files={"files": [gros]}, user=self.user)
        form.is_valid()

        self.assertIn("1 Go", str(form.errors))
        self.assertNotIn("1024 Mo", str(form.errors))

    def test_an_unreachable_broker_does_not_break_the_upload(self):
        self.assertEqual(self.envoyer(fichier("un.mp3"), fichier("deux.mp3")).status_code, 302)
        self.assertEqual(AudioTrack.objects.count(), 2)
