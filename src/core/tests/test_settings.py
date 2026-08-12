"""Réglages dont une erreur ne se voit pas à l'exécution."""

from django.test import SimpleTestCase

from config.settings import build_middleware

WHITENOISE = "whitenoise.middleware.WhiteNoiseMiddleware"


class MiddlewareTests(SimpleTestCase):
    def test_whitenoise_serves_static_files_in_production(self):
        self.assertIn(WHITENOISE, build_middleware(debug=False))

    def test_whitenoise_is_absent_in_development(self):
        """Sinon il sert la copie figée de STATIC_ROOT, et les modifications sont invisibles."""
        self.assertNotIn(WHITENOISE, build_middleware(debug=True))

    def test_whitenoise_stays_right_after_the_security_middleware(self):
        stack = build_middleware(debug=False)
        self.assertEqual(stack[0], "django.middleware.security.SecurityMiddleware")
        self.assertEqual(stack[1], WHITENOISE)

    def test_the_rest_of_the_stack_does_not_depend_on_the_mode(self):
        self.assertEqual([m for m in build_middleware(debug=False) if m != WHITENOISE], build_middleware(debug=True))
