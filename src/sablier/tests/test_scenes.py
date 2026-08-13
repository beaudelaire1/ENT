from django.test import SimpleTestCase

from sablier import scenes
from sablier.models import FocusPreference


class SceneRegistryTests(SimpleTestCase):
    def test_model_and_catalog_are_aligned(self):
        self.assertEqual(
            [(scene.key, scene.label) for scene in scenes.SCENES],
            list(FocusPreference.Ambience.choices),
        )

    def test_artistic_signatures_are_unique(self):
        signatures = [scene.art_signature for scene in scenes.SCENES]
        renderers = [scene.decor for scene in scenes.SCENES]
        self.assertEqual(len(signatures), len(set(signatures)))
        self.assertEqual(len(renderers), len(set(renderers)))

    def test_historical_univers_are_preserved(self):
        expected = {
            "printemps",
            "ete",
            "automne",
            "hiver",
            "pluie",
            "ocean",
            "sahara",
            "foret",
            "orage",
            "braises",
            "aurore",
            "nuit",
        }
        self.assertTrue(expected.issubset({scene.key for scene in scenes.SCENES}))

    def test_only_generic_concentration_is_legacy(self):
        self.assertEqual(scenes.LEGACY_REPLACED, {"concentration": "arbre_etoiles"})
