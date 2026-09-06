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

    def test_catalog_keeps_only_universes_built_as_distinct_places(self):
        """Chaque univers doit être un lieu, pas une teinte.

        Le catalogue promettait vingt-quatre univers alors que le décor n'en
        construisait que huit : les seize autres étaient la même scène recolorée. Ce
        test fixe la contrepartie de la réduction — aucun univers ne peut revenir sans
        que son décor existe réellement.
        """
        expected = {
            "arbre_etoiles",
            "refuge_pluie",
            "foret",
            "ocean",
            "sahara",
            "aurores",
            "galaxie",
            "fleuve_temps",
            "abysses",
        }
        self.assertEqual({scene.key for scene in scenes.SCENES}, expected)
        self.assertEqual(len(scenes.SCENES), 9)

    def test_every_retired_universe_redirects_to_the_place_it_came_from(self):
        """Une préférence enregistrée ne doit jamais pointer dans le vide."""
        for retired, replacement in scenes.LEGACY_REPLACED.items():
            with self.subTest(retired=retired):
                self.assertNotIn(retired, scenes.BY_KEY)
                self.assertIn(replacement, scenes.BY_KEY)
        self.assertEqual(scenes.LEGACY_REPLACED["concentration"], "arbre_etoiles")

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
    # Les objets validés par l'utilisateur, avec le repère de leur image dans le manifeste.
    PHOTO_MODES = {
        "ring": "7cfca4f4",
        "hourglass": "7073fefb",
        "wave": "dbb9148a",
        "candle": "9d0bd271",
        "moon": "1b9b150c",
        "sun": "52c57cf0",
    }
    # Les objets sans photographie de référence : ceux-là, et seuls ceux-là, sont bâtis
    # en volume dans le lieu.
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
        """Point 3 du contrat : un mode, un rendu. La partition doit être exacte.

        Un mode qui appartiendrait aux deux familles verrait sa photographie et son
        objet en volume dessinés dans le même cadre. Un mode qui n'appartiendrait à
        aucune n'aurait aucun rendu du tout.
        """
        photo = set(self.PHOTO_MODES)
        volumetric = set(self.VOLUMETRIC_MODES)
        self.assertEqual(photo & volumetric, set())
        self.assertEqual(photo | volumetric, set(self.GRAPHICAL_MODES))

    def test_each_photographic_object_keeps_its_validated_image(self):
        """Les six objets validés par l'utilisateur s'affichent tels qu'il les connaît.

        Chacun a son image sur le disque, son entrée dans le manifeste et son peintre
        dans la table. Ces visuels-là ne sont pas à réinterpréter : les remplacer par un
        équivalent en volume, même meilleur techniquement, retire à l'utilisateur ce
        qu'il avait choisi.
        """
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

        # Aucune image orpheline : tout ce qui est livré est référencé, et inversement.
        self.assertEqual(len(images), len(self.PHOTO_MODES), sorted(images))

    def test_only_the_objects_without_a_photograph_are_built_in_volume(self):
        """Point 2 du contrat, et son unique levier.

        `SUPPORTED` décide seul qui est bâti en volume. S'il recoupait la table des
        peintres photographiques, deux rendus se disputeraient le même cadre — c'est
        exactement ce qui avait fait cohabiter des photos plates et des objets éclairés
        par leur lieu dans une même série de visualisations.
        """
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
        """Point 4 du contrat : un seul basculement visible.

        Bâtir un lieu en volume prend une à deux secondes. Peindre le décor 2D pendant
        ce temps le rendait visible, puis le remplaçait : l'utilisateur voyait « les
        anciennes vues revenir » à chaque ouverture de page. L'état `booting` existe pour
        que cet intervalle ne montre rien du tout, et le repli ne se peint que lorsqu'il
        est réellement en charge.
        """
        loader = self.read_static("decor.js")
        engine = self.read_static("sablier.js")
        css = self.read_static("sablier.css")

        self.assertIn('app.dataset.renderer3d = "booting"', loader)
        # Un démarrage muet ne doit pas pouvoir durer indéfiniment.
        self.assertIn('giveUp("slow-start")', loader)
        # Le décor peint n'est peint que dans l'état de repli…
        self.assertIn('const painted=app.dataset.renderer3d==="fallback"', engine)
        # …et n'est visible que là, par le CSS et non par un script.
        self.assertIn('.focus-app:not([data-renderer3d="fallback"]) .decor-canvas { opacity:0; }', css)
        self.assertNotIn("decorCanvas.style", self.read_static("premium3d.js"))

    def test_the_object_canvas_never_betrays_its_own_rectangle(self):
        """Rien de ce que peint le canvas ne doit révéler ses bords.

        Deux façons de se trahir, toutes deux invisibles sur l'ancien décor peint et
        flagrantes sur un paysage en volume :

        * un dégradé tronqué par un bord cesse d'être une lumière et devient une arête.
          `glow` borne donc son rayon à la distance du bord le plus proche ;
        * un filtre de canvas — `contrast()`, `brightness()` — a un terme constant : sur
          une image à fond transparent il colore les pixels vides et remplit tout le
          rectangle de dessin, qu'un découpage circulaire ne suffit pas à contenir. La
          teinte de l'astre passe donc par `source-atop`, qui ne peint que là où l'image
          est déjà opaque : la transparence est préservée par construction.
        """
        engine = self.read_static("sablier.js")
        self.assertIn("const radius=Math.min(r,x,y,extent.w-x,extent.h-y);", engine)
        self.assertIn("extent.w=rect.width;extent.h=rect.height;", engine)

        sun = engine[engine.index("function drawSunPhoto(") : engine.index("function drawRingPhoto(")]
        self.assertIn('ctx.globalCompositeOperation="source-atop"', sun)
        self.assertNotIn("ctx.filter", sun)

    def test_the_place_publishes_its_horizon_for_the_objects_that_need_one(self):
        """Un soleil se couche sur l'horizon du lieu, pas sur une ligne inventée.

        L'horizon est compté depuis le haut de la scène et non de la fenêtre : publié en
        coordonnées de fenêtre, il devenait faux au premier défilement et l'astre
        disparaissait sous un horizon hors cadre.
        """
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

<<<<<<< HEAD
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
        self.assertIn(".visual-wrap .canvas-time { bottom:-18px; }", css)
        self.assertIn(".focus-stage .stage-message { display:none; }", css)
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

    def test_validated_visuals_remain_locked_to_their_existing_sources(self):
        engine = self.read_static("sablier.js")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        for fragment in (
            "ring:drawRingPhoto",
            "hourglass:drawHourglassPhoto",
            "candle:drawCandlePhoto",
            "moon:drawMoonPhoto",
            'id="digital-time"',
            '"ring":"{{ static_prefix }}sablier/img/7cfca4f4',
            '"hourglass":"{{ static_prefix }}sablier/img/7073fefb',
            '"candle":"{{ static_prefix }}sablier/img/9d0bd271',
            '"moon":"{{ static_prefix }}sablier/img/1b9b150c',
        ):
            self.assertIn(fragment, engine if "draw" in fragment else template)

    def test_reworked_visuals_keep_material_depth_and_visible_tide_water(self):
        engine = self.read_static("sablier.js")
        css = self.read_static("sablier.css")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        for fragment in (
            "function drawWavePhoto(progress)",
            'ctx.globalCompositeOperation="destination-out"',
            "ctx.globalAlpha=.42",
            "journey=1-progress",
            "Math.sin(Math.PI*journey)",
            "ctx.filter=",
            "brightness(${74+38*daylight}%)",
            "const pearl=(x,y,active,index,scale=1)=>",
            "une banque de tubes de verre gradués",
            "un ressort d'horlogerie sous verre",
        ):
            self.assertIn(fragment, engine)
        self.assertIn('"wave":"{{ static_prefix }}sablier/img/dbb9148a', template)
        self.assertNotIn("function drawTide", engine)
        sun_start = engine.index("function drawSunPhoto(progress)")
        sun_end = engine.index("function drawRingPhoto(progress)")
        sun = engine[sun_start:sun_end]
        self.assertNotIn("setLineDash", sun)
        self.assertNotIn("sunHalo", sun)
        self.assertNotIn("horizonGlow", sun)
        self.assertNotIn("drawSun(progress)", sun)
        self.assertNotIn("fillRect", sun)
        self.assertNotIn("destination-in", sun)
        self.assertIn("canvas transparent", sun)
        self.assertIn("ctx.rect(0,0,w,horizon+unit*.018);ctx.clip()", sun)
        self.assertNotIn('if(!ready("wave")){drawWave', engine)
        self.assertIn("ctx.drawImage(img,x-r,y-r,d,d)", sun)
        self.assertIn("@keyframes zen-breathe", css)
        self.assertIn(".zen-rings span,.zen-visual p { display:none; }", css)

    def test_heavy_worlds_are_created_only_when_selected(self):
        world = self.read_static("world3d.js")
        self.assertIn("if (!packs.has(key))", world)
        self.assertIn("BUILDERS[key](THREE, mobile, environmentTexture)", world)
        self.assertIn("const start = async () =>", world)
        self.assertIn("WORLD_KEYS.has(app.dataset.ambience)", world)
        self.assertIn("const packs = new Map()", world)

    def test_three_is_pinned_and_vendored_locally(self):
        package_path = settings.BASE_DIR.parent / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
=======
        Depuis la version 0.16x, ``three.module.js`` réexporte ``three.core.js`` :
        ne copier que le premier laissait un import mort. Le navigateur échouait en
        silence, la scène immersive basculait en repli, et le Sablier ne montrait
        plus que son dessin 2D — sans qu'aucune vérification ne le signale.
        """
        root = settings.BASE_DIR.parent
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
>>>>>>> 4068fa34cd11473dbb43000a41d78cdd95858ede
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

    def test_the_place_is_rendered_in_volume_with_its_own_light(self):
        """Point 1 du contrat : le lieu est rendu en volume, et il éclaire ce qu'il porte.

        Les objets bâtis dans cette scène reçoivent la lumière du ciel de l'univers, sa
        brume les enveloppe, leur ombre tombe sur son sol. C'est cette continuité qui
        distingue un lieu d'un fond.
        """
        engine = self.read_static("premium3d.js")
        for fragment in ("buildWorld", "buildEnvironment", "scene.environment", "FogExp2"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, engine)

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
