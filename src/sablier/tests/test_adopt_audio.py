"""Rattachement des fichiers déjà présents dans le stockage."""

from __future__ import annotations

import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from sablier.models import AudioTrack


class AdoptAudioTests(TestCase):
    def setUp(self):
        self.media = Path(tempfile.mkdtemp(prefix="myent-adopt-"))
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.user = get_user_model().objects.create_user("masterjay", password="motdepasse")
        self.prefix = f"users/{self.user.pk}/audio"

    def deposer(self, name, contenu=b"des octets"):
        with override_settings(MEDIA_ROOT=self.media):
            default_storage.save(f"{self.prefix}/{name}", ContentFile(contenu))

    def adopter(self, **options):
        sortie = StringIO()
        with override_settings(MEDIA_ROOT=self.media):
            call_command("adopt_audio", user="masterjay", stdout=sortie, **options)
        return sortie.getvalue()

    def test_an_unknown_account_is_refused(self):
        with self.assertRaises(CommandError):
            call_command("adopt_audio", user="fantome", stdout=StringIO())

    def test_a_deposited_file_becomes_a_track(self):
        self.deposer("morceau.mp3")
        self.adopter()
        track = AudioTrack.objects.get()
        self.assertEqual(track.owner, self.user)
        self.assertEqual(track.title, "morceau")
        self.assertEqual(track.mime_type, "audio/mpeg")

    def test_the_size_is_read_from_the_storage(self):
        self.deposer("morceau.mp3", b"x" * 4096)
        self.adopter()
        self.assertEqual(AudioTrack.objects.get().file_size, 4096)

    def test_every_accepted_format_is_recognised(self):
        for name in ("un.mp3", "deux.m4a", "trois.aac", "quatre.ogg"):
            self.deposer(name)
        self.adopter()
        self.assertEqual(AudioTrack.objects.count(), 4)

    def test_a_non_audio_file_is_left_alone(self):
        """Le bucket peut contenir autre chose que de la musique."""
        self.deposer("notes.txt")
        sortie = self.adopter()
        self.assertEqual(AudioTrack.objects.count(), 0)
        self.assertIn("1 ignoré", sortie)

    def test_running_twice_adopts_nothing_more(self):
        self.deposer("morceau.mp3")
        self.adopter()
        sortie = self.adopter()
        self.assertEqual(AudioTrack.objects.count(), 1)
        self.assertIn("1 déjà connu", sortie)

    def test_a_dry_run_writes_nothing(self):
        self.deposer("morceau.mp3")
        sortie = self.adopter(dry_run=True)
        self.assertEqual(AudioTrack.objects.count(), 0)
        self.assertIn("seraient rattachés", sortie)

    def test_subdirectories_are_visited(self):
        self.deposer("albums/nuit/morceau.mp3")
        self.adopter()
        self.assertEqual(AudioTrack.objects.count(), 1)

    def test_an_empty_prefix_says_so(self):
        sortie = self.adopter()
        self.assertIn("Aucun fichier", sortie)
