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

    def test_canonical_runtime_protects_all_graphical_visualisations(self):
        engine = self.read_static("sablier.js")
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

    def test_physical_materials_receive_a_procedural_studio_environment(self):
        engine = self.read_static("premium3d.js")
        for fragment in (
            "new THREE.PMREMGenerator(renderer)",
            "scene.environment = studioEnvironment.texture",
            "scene.environmentIntensity",
            "createStudioBackdrop(THREE)",
            'app.dataset.renderer3dEnvironment = "studio"',
        ):
            self.assertIn(fragment, engine)

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
            "world3d.js",
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

    def test_sahara_reference_world_uses_a_temporal_webgl_scene(self):
        world = self.read_static("world3d.js")
        loader = self.read_static("decor.js")
        css = self.read_static("sablier.css")
        for fragment in (
            "new THREE.WebGLRenderer",
            "new THREE.ShaderMaterial",
            "new THREE.MeshPhysicalMaterial",
            "new THREE.InstancedMesh",
            "new THREE.FogExp2",
            'app.dataset.ambience === "sahara"',
            "date.getHours()",
            'matchMedia("(prefers-reduced-motion: reduce)")',
            'canvas.addEventListener("webglcontextlost"',
        ):
            self.assertIn(fragment, world)
        self.assertIn('import(new URL("world3d.js" + version, here).href)', loader)
        self.assertIn('[data-world3d="ready"][data-ambience="sahara"]', css)
        self.assertIn('[data-world3d-active="true"]', css)
        self.assertNotIn("cdn", world.lower())

    def test_beads_are_a_dynamic_glass_chronometer_not_a_photo_sprite(self):
        beads = self.read_static("premium3d/beads-realistic.js")
        fallback = self.read_static("sablier.js")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        for fragment in (
            "new THREE.InstancedMesh",
            "new THREE.LatheGeometry",
            "transmission: 0.34",
            "makePearl(THREE)",
            "transferred = (1 - progress) * count",
            "pearls.instanceMatrix.needsUpdate = true",
        ):
            self.assertIn(fragment, beads)
        self.assertNotIn("drawBeadsPhoto", fallback)
        self.assertNotIn('"pearl":', template)

    def test_candle_uses_the_original_photo_without_a_renderer_swap(self):
        fallback = self.read_static("sablier.js")
        loader = self.read_static("decor.js")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        for fragment in (
            "function drawCandlePhoto(progress)",
            "candle:drawCandlePhoto",
            'ready("candle")',
            "ctx.drawImage(img,0,topSrc,img.naturalWidth,srcH,dx,dy,iw,dh)",
        ):
            self.assertIn(fragment, fallback)
        self.assertIn('"candle":"{{ static_prefix }}sablier/img/9d0bd271', template)
        self.assertNotIn('if(!ready("candle")){drawCandle', fallback)
        self.assertIn("SablierPremium3DReady = Promise.resolve(null)", loader)
        self.assertNotIn('import(new URL("premium3d.js"', loader)

    def test_hourglass_keeps_its_canonical_image_with_a_readable_shape(self):
        engine = self.read_static("sablier.js")
        css = self.read_static("sablier.css")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        self.assertIn("hourglass:drawHourglassPhoto", engine)
        self.assertIn("const shapeWidth=1.34", engine)
        self.assertIn("function getHourglassGrainPattern()", engine)
        self.assertIn("for(let i=0;i<1650;i++)", engine)
        self.assertIn("for(let i=0;i<18;i++)", engine)
        self.assertIn(".visual-wrap .canvas-time { bottom:-4px; }", css)
        self.assertIn('"hourglass":"{{ static_prefix }}sablier/img/7073fefb', template)

    def test_all_time_objects_use_one_canonical_renderer(self):
        engine = self.read_static("sablier.js")
        loader = self.read_static("decor.js")
        expected = (
            "ring:drawRingPhoto,hourglass:drawHourglassPhoto,wave:drawWavePhoto,candle:drawCandlePhoto,"
            "beads:drawBeads,moon:drawMoonPhoto,bars:drawBars,spiral:drawSpiral,sun:drawSunPhoto"
        )
        self.assertIn(expected, engine)
        self.assertIn("SablierPremium3DReady = Promise.resolve(null)", loader)
        self.assertNotIn('import(new URL("premium3d.js"', loader)

    def test_heavy_sahara_world_is_lazily_created(self):
        world = self.read_static("world3d.js")
        self.assertIn('if (app.dataset.ambience === "sahara")', world)
        self.assertIn("const start = async () =>", world)
        self.assertIn("new MutationObserver(maybeStart)", world)
        self.assertLess(world.index('if (app.dataset.ambience === "sahara")'), world.index("await start();"))

    def test_three_is_pinned_and_vendored_locally(self):
        package_path = settings.BASE_DIR.parent / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"]["three"], "0.184.0")
        dockerfile = (settings.BASE_DIR.parent / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("node_modules/three/build/three.module.js", dockerfile)
        self.assertIn("/app/src/static/vendor/three.module.js", dockerfile)
        self.assertNotIn("cdn", self.read_static("premium3d.js").lower())

    def test_canonical_timer_is_independent_from_decor_worlds(self):
        loader = self.read_static("decor.js")
        self.assertIn("window.SablierPremium3DReady = Promise.resolve(null)", loader)
        self.assertIn(
            'window.SablierDecorReady = load("decor-core.js").then(() => load("seasonal-worlds.js"))',
            loader,
        )
        self.assertLess(loader.index("SablierPremium3DReady"), loader.index("SablierDecorReady ="))
        self.assertNotIn('import(new URL("premium3d.js"', loader)
