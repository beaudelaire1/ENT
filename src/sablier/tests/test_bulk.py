"""Sélection multiple de pistes, et quota des comptes administrateurs."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from sablier.models import AudioTrack, Playlist, PlaylistTrack


class BulkTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("etudiant", password="motdepasse")
        self.client.force_login(self.user)
        self.url = reverse("sablier:audio_bulk")

    def track(self, title):
        return AudioTrack.objects.create(
            owner=self.user, title=title, mime_type="audio/mpeg", file_size=1024, status=AudioTrack.Status.READY
        )


class BulkPlaylistTests(BulkTestCase):
    def setUp(self):
        super().setUp()
        self.playlist = Playlist.objects.create(owner=self.user, title="Révisions")

    def test_several_tracks_land_in_the_playlist(self):
        first, second = self.track("Une"), self.track("Deux")
        response = self.client.post(
            self.url, {"action": "playlist", "playlist": self.playlist.pk, "tracks": [first.pk, second.pk]}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.playlist.tracks.count(), 2)

    def test_positions_follow_one_another(self):
        first, second = self.track("Une"), self.track("Deux")
        self.client.post(
            self.url, {"action": "playlist", "playlist": self.playlist.pk, "tracks": [first.pk, second.pk]}
        )
        positions = list(self.playlist.playlist_tracks.order_by("position").values_list("position", flat=True))
        self.assertEqual(positions, [0, 1])

    def test_adding_after_an_existing_track_does_not_collide(self):
        existing = self.track("Déjà là")
        PlaylistTrack.objects.create(playlist=self.playlist, track=existing, position=0)
        response = self.client.post(
            self.url, {"action": "playlist", "playlist": self.playlist.pk, "tracks": [self.track("Neuve").pk]}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.playlist.tracks.count(), 2)

    def test_a_track_already_there_is_not_added_twice(self):
        """La contrainte d'unicité la refuserait, et c'est un contresens de le dire en échec."""
        existing = self.track("Déjà là")
        PlaylistTrack.objects.create(playlist=self.playlist, track=existing, position=0)
        self.client.post(self.url, {"action": "playlist", "playlist": self.playlist.pk, "tracks": [existing.pk]})
        self.assertEqual(self.playlist.tracks.count(), 1)

    def test_another_account_playlist_is_refused(self):
        intruse = get_user_model().objects.create_user("intruse", password="motdepasse")
        elsewhere = Playlist.objects.create(owner=intruse, title="Ailleurs")
        response = self.client.post(
            self.url, {"action": "playlist", "playlist": elsewhere.pk, "tracks": [self.track("Une").pk]}
        )
        self.assertEqual(response.status_code, 404)


class BulkDeleteTests(BulkTestCase):
    def test_a_first_post_only_asks_for_confirmation(self):
        first, second = self.track("Une"), self.track("Deux")
        response = self.client.post(self.url, {"action": "delete", "tracks": [first.pk, second.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Supprimer définitivement")
        self.assertEqual(AudioTrack.objects.count(), 2)

    def test_the_confirmation_names_every_track(self):
        first, second = self.track("Une"), self.track("Deux")
        response = self.client.post(self.url, {"action": "delete", "tracks": [first.pk, second.pk]})
        self.assertContains(response, "Une")
        self.assertContains(response, "Deux")

    def test_the_confirmation_warns_about_playlists(self):
        """Une piste rangée dans une playlist en disparaît aussi : le dire avant."""
        track = self.track("Une")
        playlist = Playlist.objects.create(owner=self.user, title="Révisions")
        PlaylistTrack.objects.create(playlist=playlist, track=track, position=0)
        response = self.client.post(self.url, {"action": "delete", "tracks": [track.pk]})
        self.assertContains(response, "Révisions")

    def test_confirming_deletes_them(self):
        first, second = self.track("Une"), self.track("Deux")
        response = self.client.post(self.url, {"action": "delete", "confirm": "1", "tracks": [first.pk, second.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AudioTrack.objects.count(), 0)

    def test_only_the_selection_is_deleted(self):
        kept, removed = self.track("Gardée"), self.track("Retirée")
        self.client.post(self.url, {"action": "delete", "confirm": "1", "tracks": [removed.pk]})
        self.assertEqual(list(AudioTrack.objects.values_list("pk", flat=True)), [kept.pk])

    def test_another_account_tracks_are_untouched(self):
        intruse = get_user_model().objects.create_user("intruse", password="motdepasse")
        theirs = AudioTrack.objects.create(owner=intruse, title="La leur", mime_type="audio/mpeg", file_size=1)
        response = self.client.post(self.url, {"action": "delete", "confirm": "1", "tracks": [theirs.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AudioTrack.objects.filter(pk=theirs.pk).exists())


class BulkGuardTests(BulkTestCase):
    def test_an_empty_selection_is_refused(self):
        response = self.client.post(self.url, {"action": "delete"}, follow=True)
        self.assertContains(response, "Sélectionnez au moins une piste")

    def test_an_unknown_action_changes_nothing(self):
        track = self.track("Une")
        response = self.client.post(self.url, {"action": "danser", "tracks": [track.pk]}, follow=True)
        self.assertContains(response, "Action inconnue")
        self.assertEqual(AudioTrack.objects.count(), 1)

    def test_a_get_is_refused(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_the_library_offers_the_checkboxes(self):
        self.track("Une")
        response = self.client.get(reverse("sablier:audio"))
        self.assertContains(response, 'name="tracks"')
        self.assertContains(response, "Tout")


@override_settings(AUDIO_DEFAULT_QUOTA_MB=10240, AUDIO_ADMIN_QUOTA_MB=51200)
class AdminQuotaTests(TestCase):
    """Un administrateur dépose la musique de l'établissement, pas seulement la sienne."""

    def profile(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    def test_an_ordinary_account_keeps_its_quota(self):
        user = get_user_model().objects.create_user("etudiant", password="motdepasse")
        self.assertEqual(self.profile(user).effective_audio_quota_mb, 10240)

    def test_an_administrator_gets_the_floor(self):
        admin = get_user_model().objects.create_superuser("chef", "chef@example.test", "motdepasse")
        self.assertEqual(self.profile(admin).effective_audio_quota_mb, 51200)

    def test_a_higher_quota_is_never_lowered_to_the_floor(self):
        admin = get_user_model().objects.create_superuser("chef", "chef@example.test", "motdepasse")
        profile = self.profile(admin)
        profile.audio_quota_mb = 102400
        self.assertEqual(profile.effective_audio_quota_mb, 102400)

    def test_promotion_applies_at_once(self):
        """Le plancher est calculé, jamais écrit : promouvoir suffit, sans toucher au profil."""
        user = get_user_model().objects.create_user("etudiant", password="motdepasse")
        profile = self.profile(user)
        self.assertEqual(profile.effective_audio_quota_mb, 10240)
        user.is_superuser = True
        self.assertEqual(profile.effective_audio_quota_mb, 51200)

    def test_the_library_shows_the_effective_quota(self):
        admin = get_user_model().objects.create_superuser("chef", "chef@example.test", "motdepasse")
        self.client.force_login(admin)
        response = self.client.get(reverse("sablier:audio"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "50")
