from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from formations.models import LearningPath, Period


def active_path(owner, title):
    path = LearningPath.objects.create(owner=owner, title=title)
    period = Period.objects.create(path=path, title=f"Semestre de {title}")
    path.current_period = period
    path.save(update_fields=["current_period"])
    return path


class PrimaryPathTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.other = get_user_model().objects.create_user("bob")
        self.client.force_login(self.user)
        # Par ordre alphabétique, « Analyse » passerait avant : c'est elle que l'accueil prenait.
        self.analyse = active_path(self.user, "Analyse")
        self.physique = active_path(self.user, "Physique")

    def profile(self):
        return UserProfile.objects.get_or_create(user=self.user)[0]

    def settings(self, **data):
        base = {"display_name": "", "theme": "system", "accent_color": "#7C6CFF", "timezone": "America/Cayenne"}
        return self.client.post(reverse("accounts:settings"), {**base, **data})

    def test_the_home_screen_follows_the_chosen_path(self):
        self.settings(primary_path=self.physique.pk)
        page = self.client.get(reverse("dashboard:home"))
        self.assertEqual(page.context["academic"]["path"], self.physique)
        self.assertContains(page, "Physique · formation principale")

    def test_without_a_choice_the_first_active_path_is_kept(self):
        page = self.client.get(reverse("dashboard:home"))
        self.assertEqual(page.context["academic"]["path"], self.analyse)
        self.assertContains(page, "Choisir la formation principale")

    def test_a_path_from_another_account_cannot_be_chosen(self):
        foreign = active_path(self.other, "Privée")
        response = self.settings(primary_path=foreign.pk)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIsNone(self.profile().primary_path_id)

    def test_a_chosen_path_no_longer_active_falls_back_and_says_so(self):
        profile = self.profile()
        profile.primary_path = self.physique
        profile.save()
        self.physique.status = LearningPath.Status.PAUSED
        self.physique.save(update_fields=["status"])
        page = self.client.get(reverse("dashboard:home"))
        self.assertEqual(page.context["academic"]["path"], self.analyse)
        self.assertContains(page, "Votre formation principale n’est pas active ou n’a pas de période en cours")

    def test_deleting_the_chosen_path_clears_the_choice(self):
        profile = self.profile()
        profile.primary_path = self.physique
        profile.save()
        self.physique.delete()
        profile.refresh_from_db()
        self.assertIsNone(profile.primary_path_id)

    def test_a_path_page_sets_itself_as_primary(self):
        page = self.client.get(reverse("formations:detail", args=[self.physique.pk]))
        self.assertContains(page, "Définir comme formation principale")
        self.client.post(reverse("formations:set_primary", args=[self.physique.pk]))
        self.assertEqual(self.profile().primary_path, self.physique)
        page = self.client.get(reverse("formations:detail", args=[self.physique.pk]))
        self.assertNotContains(page, "Définir comme formation principale")

    def test_another_accounts_path_cannot_be_set_as_primary(self):
        foreign = active_path(self.other, "Privée")
        response = self.client.post(reverse("formations:set_primary", args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)

    def test_the_choice_is_part_of_the_personal_export(self):
        self.settings(primary_path=self.physique.pk)
        payload = self.client.get(reverse("accounts:export")).json()
        self.assertEqual(payload["account"]["profile"]["primary_path"], {"id": self.physique.pk, "title": "Physique"})
