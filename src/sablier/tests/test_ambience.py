from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sablier.models import FocusPreference


class AmbiencePaletteTests(TestCase):
    """Le monde et la visualisation du temps doivent garder leurs couleurs indépendantes.

    Une couleur personnelle peut recolorer le sablier, les perles ou la bougie sans
    repeindre le ciel, l'eau et la lumière de l'univers. L'alerte finale doit elle aussi
    pouvoir reprendre la main sur la couleur de la visualisation.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.client.force_login(self.user)

    def page(self):
        return self.client.get(reverse("sablier:home")).content.decode()

    def scene_style(self):
        """L'attribut `style` de la scène, seul endroit où une couleur peut tout écraser."""
        page = self.page()
        return page.split('id="focus-app"', 1)[1].split(">", 1)[0]

    def test_the_accent_is_never_forced_inline_by_default(self):
        self.assertNotIn("--focus-accent", self.scene_style())

    def test_the_chosen_universe_reaches_the_markup(self):
        FocusPreference.objects.update_or_create(user=self.user, defaults={"ambience": FocusPreference.Ambience.OASIS})
        self.assertIn('data-ambience="oasis"', self.page())

    def test_a_custom_colour_is_published_under_its_own_variable(self):
        FocusPreference.objects.update_or_create(
            user=self.user, defaults={"custom_accent": True, "accent_color": "#11AA22"}
        )
        style = self.scene_style()

        self.assertIn("--focus-user-accent:#11AA22", style)
        self.assertNotIn("--focus-accent:", style)

    def test_without_the_option_the_stored_colour_never_reaches_the_scene(self):
        FocusPreference.objects.update_or_create(
            user=self.user, defaults={"custom_accent": False, "accent_color": "#11AA22"}
        )
        style = self.scene_style()

        self.assertNotIn("--focus-user-accent", style)
        self.assertNotIn("--focus-accent", style)

    def test_world_palette_is_published_separately_from_the_timer_accent(self):
        page = self.page()
        self.assertIn("--world-sky:", page)
        self.assertIn("--world-horizon:", page)
        self.assertIn("--world-ground:", page)
        self.assertIn("--world-light:", page)

    def test_the_template_leaves_no_stray_comment_in_the_markup(self):
        self.assertNotIn("{#", self.page())
