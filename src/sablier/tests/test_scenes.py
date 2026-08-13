from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sablier import scenes
from sablier.models import FocusPreference


class SceneRegistryTests(TestCase):
    """Garde-fous structurels du moteur et de la direction artistique."""

    def test_the_model_and_the_registry_list_the_same_universes(self):
        self.assertEqual(
            [(scene.key, scene.label) for scene in scenes.SCENES],
            list(FocusPreference.Ambience.choices),
        )

    def test_every_universe_carries_a_complete_art_direction(self):
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.key):
                for color in (scene.accent, scene.tint, scene.sky, scene.horizon, scene.ground, scene.light):
                    self.assertRegex(color, r"^#[0-9a-f]{6}$")
                self.assertTrue(scene.decor)
                self.assertTrue(scene.composition)
                self.assertGreaterEqual(len(scene.motion), 2)
                self.assertTrue(scene.progression)
                self.assertGreaterEqual(len(scene.description), 30)

    def test_no_two_universes_share_an_art_signature(self):
        """Une recoloration ne peut pas passer pour un nouvel univers."""
        signatures = [scene.art_signature for scene in scenes.SCENES]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_no_two_universes_share_the_same_renderer(self):
        renderers = [scene.decor for scene in scenes.SCENES]
        self.assertEqual(len(renderers), len(set(renderers)))

    def test_requested_imaginary_worlds_are_present(self):
        keys = {scene.key for scene in scenes.SCENES}
        self.assertTrue(
            {
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
                "arbre_etoiles",
            }.issubset(keys)
        )

    def test_the_browser_engine_implements_every_universe(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "decor.js").read_text(encoding="utf-8")
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.key):
                self.assertRegex(engine, rf"\n    {scene.decor}: \{{ static:")

    def test_static_immersion_keeps_the_world_but_stops_motion(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "decor.js").read_text(encoding="utf-8")
        self.assertIn("0: { detail: 0.78, motion: 0 }", engine)
        self.assertIn("WORLDS[name].static", engine)
        self.assertIn("if (motion > 0) WORLDS[name].motion", engine)
        self.assertNotIn("if (!decor) return", engine)

    def test_world_rendering_has_a_mobile_pixel_budget(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "decor.js").read_text(encoding="utf-8")
        self.assertIn("mobile ? 1.25 : 1.65", engine)
        self.assertIn('const cache = document.createElement("canvas")', engine)
        self.assertIn("ctx.drawImage(cache", engine)

    def test_world_engine_never_controls_the_users_music(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "decor.js").read_text(encoding="utf-8")
        for forbidden in ("new Audio(", ".play(", ".pause(", "#playlist-audio", "player-volume", "soundscape"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, engine)

    def test_legacy_ambiences_have_a_deterministic_destination(self):
        self.assertEqual(
            set(scenes.LEGACY_REPLACED),
            {
                "concentration",
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
            },
        )
        self.assertTrue(set(scenes.LEGACY_REPLACED.values()).issubset(scenes.BY_KEY))

    def test_palette_rules_stay_less_specific_than_the_alert_states(self):
        css = scenes.palette_css()
        for scene in scenes.SCENES:
            self.assertIn(f'[data-ambience="{scene.key}"]{{', css)
            self.assertIn("--world-sky:", css)
            self.assertIn("--world-light:", css)
        self.assertNotIn(".focus-app[data-ambience", css)


class SceneRenderingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.client.force_login(self.user)

    def test_the_page_publishes_the_palettes_and_the_universe_table(self):
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
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        self.assertIn("function litColumn(", engine)
        self.assertIn("function limb(", engine)
        self.assertGreaterEqual(engine.count("limb("), 8)

    def test_hourglass_beads_and_candle_remain_first_class_visualisations(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        self.assertIn("function drawHourglass", engine)
        self.assertIn("function drawBeads", engine)
        self.assertIn("function drawCandle", engine)
        painters = engine[engine.index("const painters=") : engine.index("if(painters[mode])")]
        for mode in ("hourglass:drawHourglass", "candle:drawCandle", "beads:drawBeads"):
            self.assertIn(mode, painters)

    def test_the_candle_and_the_moon_fill_their_stage(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        candle = engine[engine.index("function drawCandle") : engine.index("function drawBeads")]
        moon = engine[engine.index("function drawMoon") : engine.index("function drawBars")]
        self.assertIn("bodyW=Math.min(w,h)*.27", candle)
        self.assertIn("full=h*.6", candle)
        self.assertIn("r=Math.min(w,h)*.37", moon)

    def test_the_moon_phase_is_carved_with_an_opaque_shadow(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        moon = engine[engine.index("function drawMoon") : engine.index("function drawBars")]
        erase = moon.index('globalCompositeOperation="destination-out"')
        self.assertIn('ctx.fillStyle="#000"', moon[erase : erase + 200])

    def test_the_moon_keeps_its_dark_side_visible(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        moon = engine[engine.index("function drawMoon") : engine.index("function drawBars")]
        self.assertIn('globalCompositeOperation="destination-over"', moon)
        self.assertLess(
            moon.index('globalCompositeOperation="destination-out"'),
            moon.index('globalCompositeOperation="destination-over"'),
        )

    def test_the_candle_still_shows_what_has_already_burned(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        candle = engine[engine.index("function drawCandle") : engine.index("function drawBeads")]
        self.assertIn("setLineDash", candle)
        self.assertIn("ceiling", candle)

    def test_the_playlist_remains_an_independent_user_control(self):
        engine = (settings.BASE_DIR / "static" / "sablier" / "sablier.js").read_text(encoding="utf-8")
        template = (settings.BASE_DIR / "templates" / "sablier" / "home.html").read_text(encoding="utf-8")
        self.assertIn('id="playlist-select"', template)
        self.assertIn('id="player-toggle"', template)
        self.assertIn('id="player-volume"', template)
        self.assertIn('$("#playlist-select").addEventListener', engine)
        self.assertIn('$("#player-volume").addEventListener', engine)

    def test_no_ambient_sound_is_left_behind(self):
        page = self.client.get(reverse("sablier:home")).content.decode()
        self.assertNotIn("soundscape", page)
        self.assertIn("finished.wav", page)


class InstantSettingsTests(TestCase):
    """Les réglages enregistrés doivent primer sur la copie locale du navigateur."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.client.force_login(self.user)

    def test_the_page_publishes_when_preferences_were_saved(self):
        page = self.client.get(reverse("sablier:home")).content.decode()
        self.assertIn("data-saved-at=", page)

    def test_the_stamp_moves_when_preferences_change(self):
        first = self.client.get(reverse("sablier:home")).content.decode()

        preference = FocusPreference.objects.get(user=self.user)
        preference.ambience = FocusPreference.Ambience.INTERSTELLAIRE
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

        self.assertIn('role="group" aria-label="Niveau d’immersion"', page)
        self.assertEqual(page.count('type="button" data-decor='), len(FocusPreference.Decor.values))
        self.assertIn(".decor-levels button.active", stylesheet)
