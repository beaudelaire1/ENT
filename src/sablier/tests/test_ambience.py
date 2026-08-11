from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sablier.models import FocusPreference


class AmbiencePaletteTests(TestCase):
    """L'ambiance doit pouvoir colorer la scène, et l'alerte finale doit pouvoir la couvrir.

    Le gabarit posait la couleur en style inline, qui l'emporte sur toute règle de
    feuille de style : ni les quatre ambiances, ni l'ambre de l'alerte, ni le rouge de
    fin ne pouvaient s'appliquer.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def page(self):
        return self.client.get(reverse("sablier:home")).content.decode()

    def test_the_accent_is_never_forced_inline_by_default(self):
        self.assertNotIn("--focus-accent:", self.page())

    def test_the_chosen_ambience_reaches_the_markup(self):
        FocusPreference.objects.update_or_create(user=self.user, defaults={"ambience": FocusPreference.Ambience.ENERGY})
        self.assertIn('data-ambience="energy"', self.page())

    def test_a_custom_colour_is_published_under_its_own_variable(self):
        FocusPreference.objects.update_or_create(
            user=self.user, defaults={"custom_accent": True, "accent_color": "#11AA22"}
        )
        page = self.page()

        # Sous sa propre variable, la couleur sert de valeur par défaut aux palettes
        # sans empêcher l'alerte finale de reprendre la main.
        self.assertIn("--focus-user-accent:#11AA22", page)
        self.assertNotIn("--focus-accent:", page)

    def test_without_the_option_the_stored_colour_never_reaches_the_scene(self):
        FocusPreference.objects.update_or_create(
            user=self.user, defaults={"custom_accent": False, "accent_color": "#11AA22"}
        )
        page = self.page()

        # La couleur reste visible dans le sélecteur du panneau de préférences ; ce qui
        # compte est qu'elle ne soit appliquée à la scène sous aucune forme.
        self.assertNotIn("--focus-user-accent", page)
        self.assertNotIn("--focus-accent", page)

    def test_the_template_leaves_no_stray_comment_in_the_markup(self):
        self.assertNotIn("{#", self.page())
        self.assertNotIn("n’est plus posée en inline", self.page())

    def test_every_ambience_has_its_own_palette(self):
        css = (settings.BASE_DIR / "static" / "sablier" / "sablier.css").read_text(encoding="utf-8")
        for ambience in FocusPreference.Ambience.values:
            self.assertIn(f'[data-ambience="{ambience}"]', css)
