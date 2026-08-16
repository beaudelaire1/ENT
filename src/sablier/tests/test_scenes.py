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

    def test_catalog_restores_every_distinct_historical_universe(self):
        expected = {
            "arbre_etoiles",
            "fontaine",
            "eden",
            "fleuve_temps",
            "souvenirs",
            "interstellaire",
            "galaxie",
            "heaven",
            "oasis",
            "abysses",
            "refuge_pluie",
            "aurores",
            "printemps",
            "ete",
            "automne",
            "hiver",
            "pluie",
            "foret",
            "ocean",
            "sahara",
            "orage",
            "braises",
            "aurore",
            "nuit",
        }
        self.assertEqual({scene.key for scene in scenes.SCENES}, expected)
        self.assertEqual(len(scenes.SCENES), 24)

    def test_only_the_pre_catalogue_concentration_alias_is_replaced(self):
        self.assertEqual(scenes.LEGACY_REPLACED, {"concentration": "arbre_etoiles"})

    def test_browser_storage_also_converges_to_the_curated_catalog(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        self.assertIn("ambienceAliases[state.ambience]||state.ambience", engine)
        self.assertIn('json_script:"ambience-alias-data"', template)


class PremiumVisualRuntimeTests(SimpleTestCase):
    GRAPHICAL_MODES = ("ring", "hourglass", "wave", "candle", "beads", "moon", "bars", "spiral", "sun")

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

    def test_all_time_objects_use_one_canonical_renderer(self):
        """Les neuf objets viennent du même moteur, dans le même lieu.

        La 2D reste un repli intégral — un dessin par mode — mais aucun mode ne
        garde de chemin de rendu privilégié : c'est ce qui avait laissé cohabiter
        des photos plates et des objets en volume dans une même série.
        """
        engine = self.read_static("sablier.js")
        premium = self.read_static("premium3d.js")
        painters = (
            "const painters={ring:drawRing,hourglass:drawHourglass,wave:drawWave,"
            "candle:drawCandle,beads:drawBeads,moon:drawMoon,bars:drawBars,"
            "spiral:drawSpiral,sun:drawSun}"
        )
        self.assertIn(painters, engine)
        for mode in self.GRAPHICAL_MODES:
            with self.subTest(mode=mode):
                self.assertIn(f'"{mode}"', premium)
        for removed in ("drawCandlePhoto", "drawHourglassPhoto", "drawWavePhoto", "#asset-data"):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, engine)

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
        # Le script refuse de rendre la main si un import sort du dossier vendu.
        self.assertIn("importe encore", script)

        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("npm run vendor", dockerfile)
        self.assertIn("/app/src/static/vendor/", dockerfile)
        self.assertNotIn("cdn", self.read_static("premium3d.js").lower())

    def test_every_universe_has_a_three_dimensional_recipe(self):
        """Chaque décor du catalogue doit exister comme lieu en volume.

        Sans cette garde, un univers ajouté au catalogue serveur retomberait
        silencieusement sur le lieu par défaut : deux ambiances différentes
        montreraient exactement le même paysage.
        """
        recipes = self.read_static("premium3d/worlds.js")
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.key):
                self.assertIn(f"\n  {scene.decor}: {{", recipes)

    def test_the_object_is_lit_by_the_place_it_stands_in(self):
        """L'objet et son univers partagent une scène, une caméra et une lumière."""
        engine = self.read_static("premium3d.js")
        self.assertIn("buildWorld", engine)
        self.assertIn("buildEnvironment", engine)
        self.assertIn("scene.environment", engine)
        self.assertIn("FogExp2", engine)
        # Le décor peint n'est plus repeint quand la scène 3D est à l'image.
        self.assertIn('app.dataset.renderer3d!=="three"', self.read_static("sablier.js"))

    def test_only_the_chosen_universe_is_built_and_the_previous_one_freed(self):
        """Un seul lieu vit à la fois, et il libère celui qu'il remplace.

        Vingt-quatre paysages en volume ne peuvent pas coexister : sans libération,
        quelques changements d'ambiance suffisaient à saturer la mémoire graphique.
        Les cartes partagées par tous les lieux doivent en revanche y survivre.
        """
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
