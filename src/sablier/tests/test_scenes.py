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
    GRAPHICAL_MODES = ("ring", "hourglass", "wave", "candle", "beads", "moon", "bars", "spiral", "sun")

    def read_static(self, relative_path):
        path = settings.BASE_DIR / "static" / "sablier" / relative_path
        return path.read_text(encoding="utf-8")

    def test_premium_runtime_protects_all_graphical_visualisations(self):
        engine = self.read_static("premium3d.js")
        for mode in self.GRAPHICAL_MODES:
            self.assertIn(f"{mode}:", engine)

        expected = (
            "ring.js",
            "ring-realistic.js",
            "hourglass.js",
            "hourglass-realistic.js",
            "wave.js",
            "wave-realistic.js",
            "candle.js",
            "candle-realistic.js",
            "beads.js",
            "beads-realistic.js",
            "bars.js",
            "bars-realistic.js",
            "spiral.js",
            "spiral-realistic.js",
            "celestial.js",
            "celestial-realistic.js",
            "material-kit.js",
            "flame-texture.js",
        )
        for module in expected:
            path = settings.BASE_DIR / "static" / "sablier" / "premium3d" / module
            self.assertTrue(path.is_file(), module)

    def test_graphical_visualisations_delegate_to_realistic_renderers(self):
        delegates = {
            "ring.js": "ring-realistic.js",
            "hourglass.js": "hourglass-realistic.js",
            "wave.js": "wave-realistic.js",
            "candle.js": "candle-realistic.js",
            "beads.js": "beads-realistic.js",
            "bars.js": "bars-realistic.js",
            "spiral.js": "spiral-realistic.js",
            "celestial.js": "celestial-realistic.js",
        }
        for entry, target in delegates.items():
            with self.subTest(entry=entry):
                self.assertIn(target, self.read_static(f"premium3d/{entry}"))

    def test_canvas_visualisations_remain_as_a_webgl_fallback(self):
        engine = self.read_static("sablier.js")
        for function in (
            "drawRing",
            "drawHourglass",
            "drawWave",
            "drawCandle",
            "drawBeads",
            "drawMoon",
            "drawBars",
            "drawSpiral",
            "drawSun",
        ):
            self.assertIn(f"function {function}", engine)
        premium = self.read_static("premium3d.js")
        self.assertIn('app.dataset.renderer3d = "fallback"', premium)
        self.assertIn("webglcontextlost", premium)
        self.assertIn("fallbackCanvas.style.visibility", premium)

    def test_digital_and_zen_remain_native_non_webgl_modes(self):
        engine = self.read_static("premium3d.js")
        self.assertNotIn('"digital", "zen"', engine)
        css = self.read_static("sablier.css")
        self.assertIn('.visual-wrap[data-mode="digital"] .digital-visual', css)
        self.assertIn('.visual-wrap[data-mode="zen"] .zen-visual', css)

    def test_visual_runtime_never_controls_the_users_music(self):
        files = [
            "decor-core.js",
            "seasonal-worlds.js",
            "premium3d.js",
            "premium3d/material-kit.js",
            "premium3d/flame-texture.js",
            "premium3d/ring-realistic.js",
            "premium3d/hourglass-realistic.js",
            "premium3d/wave-realistic.js",
            "premium3d/candle-realistic.js",
            "premium3d/beads-realistic.js",
            "premium3d/bars-realistic.js",
            "premium3d/spiral-realistic.js",
            "premium3d/celestial-realistic.js",
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

    def test_premium_runtime_boot_is_independent_from_decor_worlds(self):
        loader = self.read_static("decor.js")
        self.assertIn(
            'window.SablierPremium3DReady = import(new URL("premium3d.js" + version, here).href)',
            loader,
        )
        self.assertIn(
            'window.SablierDecorReady = load("decor-core.js").then(() => load("seasonal-worlds.js"))',
            loader,
        )
        self.assertLess(loader.index("SablierPremium3DReady"), loader.index("SablierDecorReady ="))
        self.assertNotIn('.then(() => import(new URL("premium3d.js" + version, here).href))', loader)
