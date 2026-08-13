import json

from django.conf import settings
from django.test import SimpleTestCase

from sablier import scenes
from sablier.models import FocusPreference


class SceneRegistryTests(SimpleTestCase):
    def test_model_and_catalog_are_aligned(self):
        self.assertEqual(
            [(scene.key, scene.label) for scene in scenes.SCENES],
            list(FocusPreference.Ambience.choices),
        )

    def test_every_universe_has_a_complete_art_direction(self):
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.key):
                colors = (
                    scene.accent,
                    scene.tint,
                    scene.sky,
                    scene.horizon,
                    scene.ground,
                    scene.light,
                )
                for color in colors:
                    self.assertRegex(color, r"^#[0-9a-f]{6}$")
                self.assertTrue(scene.decor)
                self.assertTrue(scene.composition)
                self.assertGreaterEqual(len(scene.motion), 2)
                self.assertTrue(scene.progression)
                self.assertGreaterEqual(len(scene.description), 30)

    def test_artistic_signatures_are_unique(self):
        signatures = [scene.art_signature for scene in scenes.SCENES]
        renderers = [scene.decor for scene in scenes.SCENES]
        self.assertEqual(len(signatures), len(set(signatures)))
        self.assertEqual(len(renderers), len(set(renderers)))

    def test_historical_universes_are_preserved(self):
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


class PremiumVisualRuntimeTests(SimpleTestCase):
    def read_static(self, relative_path):
        path = settings.BASE_DIR / "static" / "sablier" / relative_path
        return path.read_text(encoding="utf-8")

    def test_premium_runtime_protects_the_five_material_visualisations(self):
        engine = self.read_static("premium3d.js")
        for mode in ("hourglass", "candle", "beads", "moon", "sun"):
            self.assertIn('"' + mode + '"', engine)
        for module in ("hourglass.js", "candle.js", "beads.js", "celestial.js"):
            path = settings.BASE_DIR / "static" / "sablier" / "premium3d" / module
            self.assertTrue(path.is_file())

    def test_canvas_visualisations_remain_as_a_webgl_fallback(self):
        engine = self.read_static("sablier.js")
        for function in ("drawHourglass", "drawCandle", "drawBeads", "drawMoon", "drawSun"):
            self.assertIn(f"function {function}", engine)
        premium = self.read_static("premium3d.js")
        self.assertIn('app.dataset.renderer3d = "fallback"', premium)
        self.assertIn("webglcontextlost", premium)
        self.assertIn("fallbackCanvas.style.visibility", premium)

    def test_visual_runtime_never_controls_the_users_music(self):
        files = [
            "decor-core.js",
            "seasonal-worlds.js",
            "premium3d.js",
            "premium3d/hourglass.js",
            "premium3d/candle.js",
            "premium3d/beads.js",
            "premium3d/celestial.js",
        ]
        engine = "".join(self.read_static(path) for path in files)
        forbidden_fragments = (
            "new Audio(",
            ".play(",
            ".pause(",
            "#playlist-audio",
            "player-volume",
            "soundscape",
        )
        for forbidden in forbidden_fragments:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, engine)

    def test_three_is_pinned_and_vendored_locally(self):
        package_path = settings.BASE_DIR.parent / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"]["three"], "0.184.0")
        dockerfile = (settings.BASE_DIR.parent / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("node_modules/three/build/three.module.js", dockerfile)
        self.assertIn("/app/src/static/vendor/three.module.js", dockerfile)
        self.assertNotIn("cdn", self.read_static("premium3d.js").lower())

    def test_decor_loader_boots_seasonal_worlds_before_3d(self):
        loader = self.read_static("decor.js")
        self.assertIn(
            'load("decor-core.js").then(() => load("seasonal-worlds.js"))',
            loader,
        )
        self.assertIn(
            'import(new URL("premium3d.js" + version, here).href)',
            loader,
        )
