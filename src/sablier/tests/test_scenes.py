from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sablier import scenes
from sablier.models import FocusPreference


class SceneRegistryTests(TestCase):
    def test_the_model_and_the_registry_list_the_same_ambiences(self):
        """Les deux listes sont écrites séparément ; rien ne doit les laisser diverger."""
        self.assertEqual(
            [(scene.key, scene.label) for scene in scenes.SCENES],
            list(FocusPreference.Ambience.choices),
        )

    def test_every_ambience_carries_a_palette_and_a_decor(self):
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.key):
                self.assertRegex(scene.accent, r"^#[0-9a-f]{6}$")
                self.assertRegex(scene.tint, r"^#[0-9a-f]{6}$")
                self.assertTrue(scene.decor)

    def test_the_decors_all_exist_in_the_browser_engine(self):
        """Une ambiance dont le décor n'existe pas côté navigateur s'afficherait nue."""
        engine = (settings.BASE_DIR / "static" / "sablier" / "decor.js").read_text(encoding="utf-8")
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.key):
                self.assertRegex(engine, rf"\n    {scene.decor}: {{")

    def test_palette_rules_stay_less_specific_than_the_alert_states(self):
        css = scenes.palette_css()
        for scene in scenes.SCENES:
            self.assertIn(f'[data-ambience="{scene.key}"]{{', css)
        # Un sélecteur de classe rendrait l'ambiance prioritaire sur .focus-app[data-warning]
        # et masquerait l'alerte finale.
        self.assertNotIn(".focus-app[data-ambience", css)


class SceneRenderingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def test_the_page_publishes_the_palettes_and_the_decor_table(self):
        page = self.client.get(reverse("sablier:home")).content.decode()

        for scene in scenes.SCENES:
            self.assertIn(f'[data-ambience="{scene.key}"]', page)
            self.assertIn(scene.decor, page)

    def test_assets_carry_a_version_that_follows_the_files(self):
        page = self.client.get(reverse("sablier:home")).content.decode()

        self.assertNotIn("?v=20260810", page)
        self.assertIn("sablier/decor.js?v=", page)

    def test_the_eight_visualisations_are_offered(self):
        page = self.client.get(reverse("sablier:home")).content.decode()

        for mode in FocusPreference.Mode.values:
            self.assertIn(f'data-mode="{mode}"', page)
        self.assertEqual(len(FocusPreference.Mode.choices), 8)

    def test_no_ambient_sound_is_left_behind(self):
        page = self.client.get(reverse("sablier:home")).content.decode()

        self.assertNotIn("soundscape", page)
        # Le carillon de fin, lui, reste : il ne dépend pas de l'ambiance.
        self.assertIn("finished.wav", page)
