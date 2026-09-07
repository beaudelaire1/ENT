import json
import re

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

    def test_catalog_offers_every_place_the_decor_can_actually_build(self):
        """Un univers vaut par son lieu, pas par sa teinte.

        Le catalogue avait été ramené à neuf au motif que les quinze autres étaient la
        même scène recolorée. `premium3d/worlds.js` prouve le contraire : chacun y a sa
        propre recette — ciel, heure, relief, eau, végétation, particules. Ce test fixe
        la contrepartie de leur retour : un univers ne peut figurer au catalogue que si
        son décor existe vraiment, et aucun décor construit ne doit rester inaccessible.
        """
        recipes = (settings.BASE_DIR / "static" / "sablier" / "premium3d" / "worlds.js").read_text(encoding="utf-8")
        built = set(re.findall(r"^  ([a-z_]+): \{$", recipes, re.MULTILINE))
        self.assertEqual({scene.decor for scene in scenes.SCENES}, built)
        self.assertEqual(len(scenes.SCENES), 24)
        for saison in ("printemps", "ete", "automne", "hiver"):
            with self.subTest(saison=saison):
                self.assertIn(saison, scenes.BY_KEY)

    def test_browser_storage_also_converges_to_the_curated_catalog(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        self.assertIn("ambienceAliases[state.ambience]||state.ambience", engine)
        self.assertIn('json_script:"ambience-alias-data"', template)


class PremiumVisualRuntimeTests(SimpleTestCase):
    """Le contrat de rendu du Sablier, tenu par des tests plutôt que par la vigilance.

    Le lieu appartient à la 3D ; l'objet appartient à l'utilisateur. Six objets ont une
    photographie qu'il a validée et ce sont elles qui s'affichent ; trois n'en ont jamais
    eu et sont construits en volume. Un mode a un rendu, jamais deux.
    """

    GRAPHICAL_MODES = ("ring", "hourglass", "wave", "candle", "beads", "moon", "bars", "spiral", "sun")
    PHOTO_MODES = {
        "ring": "7cfca4f4",
        "hourglass": "7073fefb",
        "wave": "dbb9148a",
        "candle": "9d0bd271",
        "moon": "1b9b150c",
        "sun": "52c57cf0",
    }
    VOLUMETRIC_MODES = ("beads", "bars", "spiral")

    def read_static(self, relative_path):
        path = settings.BASE_DIR / "static" / "sablier" / relative_path
        return path.read_text(encoding="utf-8")

    def test_canonical_runtime_protects_all_graphical_visualisations(self):
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
            "noise.js",
            "textures.js",
            "environment.js",
            "world-kit.js",
            "worlds.js",
            "postfx.js",
            "native-modes.css",
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
        self.assertIn("renderer3dReason", premium)

    def test_the_two_families_of_objects_cover_every_mode_without_overlap(self):
        photo = set(self.PHOTO_MODES)
        volumetric = set(self.VOLUMETRIC_MODES)
        self.assertEqual(photo & volumetric, set())
        self.assertEqual(photo | volumetric, set(self.GRAPHICAL_MODES))

    def test_each_photographic_object_keeps_its_validated_image(self):
        engine = self.read_static("sablier.js")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        folder = settings.BASE_DIR / "static" / "sablier" / "img"
        images = [path.name for path in folder.glob("*.jpg")]

        for mode, fingerprint in self.PHOTO_MODES.items():
            with self.subTest(mode=mode):
                painter = f"draw{mode.capitalize()}Photo"
                self.assertIn(f"function {painter}(", engine)
                self.assertIn(f"{mode}:{painter}", engine)
                self.assertIn(f'"{mode}":"{{{{ static_prefix }}}}sablier/img/{fingerprint}', template)
                self.assertTrue([name for name in images if name.startswith(fingerprint)], fingerprint)

        self.assertEqual(len(images), len(self.PHOTO_MODES), sorted(images))

    def test_only_the_objects_without_a_photograph_are_built_in_volume(self):
        premium = self.read_static("premium3d.js")
        supported = next(line for line in premium.splitlines() if line.startswith("const SUPPORTED"))
        for mode in self.VOLUMETRIC_MODES:
            with self.subTest(mode=mode):
                self.assertIn(f'"{mode}"', supported)
        for mode in self.PHOTO_MODES:
            with self.subTest(mode=mode):
                self.assertNotIn(f'"{mode}"', supported)
        for native in ("digital", "zen"):
            with self.subTest(mode=native):
                self.assertNotIn(f'"{native}"', supported)

    def test_nothing_of_the_place_is_shown_before_a_renderer_is_in_charge(self):
        loader = self.read_static("decor.js")
        engine = self.read_static("sablier.js")
        css = self.read_static("sablier.css")

        self.assertIn('app.dataset.renderer3d = "booting"', loader)
        self.assertIn('giveUp("slow-start")', loader)
        self.assertIn('const painted=app.dataset.renderer3d==="fallback"', engine)
        self.assertIn('.focus-app:not([data-renderer3d="fallback"]) .decor-canvas { opacity:0; }', css)
        self.assertNotIn("decorCanvas.style", self.read_static("premium3d.js"))

    def test_the_object_canvas_never_betrays_its_own_rectangle(self):
        engine = self.read_static("sablier.js")
        self.assertIn("const radius=Math.min(r,x,y,extent.w-x,extent.h-y);", engine)
        self.assertIn("extent.w=rect.width;extent.h=rect.height;", engine)

        sun = engine[engine.index("function drawSunPhoto(") : engine.index("function drawRingPhoto(")]
        self.assertIn('ctx.globalCompositeOperation="source-atop"', sun)
        self.assertNotIn("ctx.filter", sun)

    def test_the_place_publishes_its_horizon_for_the_objects_that_need_one(self):
        premium = self.read_static("premium3d.js")
        engine = self.read_static("sablier.js")
        self.assertIn("app.dataset.worldHorizon", premium)
        self.assertIn("skyline.set(0, camera.position.y, -1e6).project(camera)", premium)
        self.assertIn("((1 - skyline.y) / 2) * height", premium)
        self.assertIn("function horizonLine(ratio)", engine)
        self.assertIn("horizonLine(.62)", engine)
        self.assertIn("stage.getBoundingClientRect().top", engine)

    def test_digital_and_zen_remain_native_non_webgl_modes(self):
        engine = self.read_static("premium3d.js")
        supported = next(line for line in engine.splitlines() if line.startswith("const SUPPORTED"))
        self.assertNotIn('"digital"', supported)
        self.assertNotIn('"zen"', supported)
        css = self.read_static("premium3d/native-modes.css")
        self.assertIn('.visual-wrap[data-mode="digital"] .digital-visual', css)
        self.assertIn('.visual-wrap[data-mode="zen"] .zen-rings', css)
        loader = self.read_static("decor.js")
        self.assertIn("premium3d/native-modes.css", loader)

    def test_nested_premium_assets_participate_in_cache_versioning(self):
        views = (settings.BASE_DIR / "sablier" / "views.py").read_text(encoding="utf-8")
        self.assertIn('folder.rglob("*")', views)

    def test_visual_runtime_never_controls_the_users_music(self):
        files = [
            "decor-core.js",
            "seasonal-worlds.js",
            "premium3d.js",
            "premium3d/material-kit.js",
            "premium3d/noise.js",
            "premium3d/textures.js",
            "premium3d/environment.js",
            "premium3d/world-kit.js",
            "premium3d/worlds.js",
            "premium3d/postfx.js",
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

    def test_three_is_pinned_and_vendored_in_full(self):
        """Le moteur 3D doit être copié en entier, pas seulement son point d'entrée.

        Depuis la version 0.16x, ``three.module.js`` réexporte ``three.core.js`` :
        ne copier que le premier laissait un import mort. Le navigateur échouait en
        silence, la scène immersive basculait en repli, et le Sablier ne montrait
        plus que son dessin 2D — sans qu'aucune vérification ne le signale.
        """
        root = settings.BASE_DIR.parent
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"]["three"], "0.184.0")
        self.assertEqual(package["scripts"]["vendor"], "node tools/vendor-three.mjs")

        script = (root / "tools" / "vendor-three.mjs").read_text(encoding="utf-8")
        for required in ("three.module.js", "three.core.js", "objects/Sky.js"):
            self.assertIn(required, script)
        self.assertIn("importe encore", script)

        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("npm run vendor", dockerfile)
        self.assertIn("/app/src/static/vendor/", dockerfile)
        self.assertNotIn("cdn", self.read_static("premium3d.js").lower())

    def test_every_universe_has_a_three_dimensional_recipe(self):
        recipes = self.read_static("premium3d/worlds.js")
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.key):
                self.assertIn(f"\n  {scene.decor}: {{", recipes)

    def test_the_place_is_rendered_in_volume_with_its_own_light(self):
        engine = self.read_static("premium3d.js")
        for fragment in ("buildWorld", "buildEnvironment", "scene.environment", "FogExp2"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, engine)

    def test_only_the_chosen_universe_is_built_and_the_previous_one_freed(self):
        engine = self.read_static("premium3d.js")
        self.assertIn("if (state.world === key) return;", engine)
        self.assertIn("dispose(currentWorld.object);", engine)
        self.assertIn("currentWorld = buildWorld(THREE, key, { mobile });", engine)
        self.assertIn("userData?.shared !== true", engine)

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
