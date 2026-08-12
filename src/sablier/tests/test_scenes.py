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

    def test_every_ambience_has_a_depth_backdrop(self):
        """Une ambiance doit évoquer un lieu, pas seulement teinter des particules."""
        engine = (settings.BASE_DIR / "static" / "sablier" / "decor.js").read_text(encoding="utf-8")
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.key):
                self.assertRegex(engine, rf"\n    {scene.decor}\(ctx, w, h, color, intensity")

    def test_density_controls_particles_and_scenery(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "decor.js").read_text(encoding="utf-8")
        for level in range(4):
            with self.subTest(level=level):
                self.assertRegex(engine, rf"{level}: {{ particles: [0-9.]+, scenery: [0-9.]+ }}")
        self.assertIn("BACKDROPS[name]?.", engine)

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

    def test_every_visualisation_is_offered(self):
        page = self.client.get(reverse("sablier:home")).content.decode()

        for mode in FocusPreference.Mode.values:
            self.assertIn(f'data-mode="{mode}"', page)
        self.assertGreaterEqual(len(FocusPreference.Mode.choices), 11)

    def test_canvas_visualisations_use_depth_and_material_helpers(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        self.assertIn("function palette()", engine)
        self.assertIn("createRadialGradient", engine)
        self.assertIn("function glow(", engine)

    def test_the_volumes_share_one_contrast_vocabulary(self):
        """Une forme dont les flancs se fondent dans le fond paraît plus petite.

        Les visuels réglaient leurs dégradés au cas par cas et finissaient en translucide
        sur les bords : d'où une bougie et une lune qu'on percevait minuscules. Le flanc
        éclairé et le liseré sont maintenant deux fonctions partagées.
        """
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        self.assertIn("function litColumn(", engine)
        self.assertIn("function limb(", engine)
        # Chaque volume referme sa silhouette : au moins un liseré par visuel de matière.
        self.assertGreaterEqual(engine.count("limb("), 8)

    def test_the_candle_and_the_moon_fill_their_stage(self):
        """Leur taille apparente était le reproche : elles occupent une part franche du canvas."""
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        candle = engine[engine.index("function drawCandle") : engine.index("function drawBeads")]
        moon = engine[engine.index("function drawMoon") : engine.index("function drawBars")]
        self.assertIn("bodyW=Math.min(w,h)*.27", candle)
        self.assertIn("full=h*.6", candle)
        self.assertIn("r=Math.min(w,h)*.37", moon)

    def test_the_moon_phase_is_carved_with_an_opaque_shadow(self):
        """`destination-out` retire de l'alpha en proportion de celle de la source.

        Le dernier `fillStyle` posé était un cratère à 20 % : l'ombre n'enlevait qu'un
        cinquième de la lumière, la lune restait un disque uniformément clair et sa phase
        ne se lisait pas. La couleur d'effacement doit donc être opaque.
        """
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        moon = engine[engine.index("function drawMoon") : engine.index("function drawBars")]
        erase = moon.index('globalCompositeOperation="destination-out"')
        self.assertIn('ctx.fillStyle="#000"', moon[erase : erase + 200])

    def test_the_moon_keeps_its_dark_side_visible(self):
        """C'est la lumière qui recule, pas la lune.

        La face nuit est repeinte derrière ce qui subsiste : peinte avant l'effacement,
        elle disparaissait avec la lumière et l'on retombait sur un croissant flottant,
        d'astre en astre plus petit.
        """
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        moon = engine[engine.index("function drawMoon") : engine.index("function drawBars")]
        self.assertIn('globalCompositeOperation="destination-over"', moon)
        self.assertLess(
            moon.index('globalCompositeOperation="destination-out"'),
            moon.index('globalCompositeOperation="destination-over"'),
            "la face nuit doit être repeinte après l'effacement, sinon elle est effacée avec",
        )

    def test_the_candle_still_shows_what_has_already_burned(self):
        """Sans repère de hauteur d'origine, la bougie ne mesure plus rien."""
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        candle = engine[engine.index("function drawCandle") : engine.index("function drawBeads")]
        self.assertIn("setLineDash", candle)
        self.assertIn("ceiling", candle)

    def test_no_ambient_sound_is_left_behind(self):
        page = self.client.get(reverse("sablier:home")).content.decode()

        self.assertNotIn("soundscape", page)
        # Le carillon de fin, lui, reste : il ne dépend pas de l'ambiance.
        self.assertIn("finished.wav", page)


class InstantSettingsTests(TestCase):
    """Les réglages enregistrés doivent primer sur la copie locale du navigateur."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def test_the_page_publishes_when_preferences_were_saved(self):
        page = self.client.get(reverse("sablier:home")).content.decode()
        self.assertIn("data-saved-at=", page)

    def test_the_stamp_moves_when_preferences_change(self):
        first = self.client.get(reverse("sablier:home")).content.decode()

        preference = FocusPreference.objects.get(user=self.user)
        preference.ambience = FocusPreference.Ambience.ORAGE
        preference.save()

        second = self.client.get(reverse("sablier:home")).content.decode()
        extract = lambda page: page.split('data-saved-at="', 1)[1].split('"', 1)[0]  # noqa: E731
        self.assertNotEqual(extract(first), extract(second))

    def test_the_page_is_never_cached(self):
        response = self.client.get(reverse("sablier:home"))
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    def test_the_density_is_adjustable_without_the_preferences_form(self):
        page = self.client.get(reverse("sablier:home")).content.decode()
        for level in FocusPreference.Decor.values:
            self.assertIn(f'data-decor="{level}"', page)

    def test_the_density_buttons_publish_their_interactive_state(self):
        page = self.client.get(reverse("sablier:home")).content.decode()
        stylesheet = (settings.BASE_DIR / "static" / "sablier" / "sablier.css").read_text(encoding="utf-8")

        self.assertIn('role="group" aria-label="Densité du décor"', page)
        self.assertEqual(page.count('type="button" data-decor='), len(FocusPreference.Decor.values))
        self.assertIn(".decor-levels button.active", stylesheet)
