"""Réglages dont une erreur ne se voit pas à l'exécution."""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import build_middleware, database_config

WHITENOISE = "whitenoise.middleware.WhiteNoiseMiddleware"
POSTGRES_URL = "postgresql://myent:secret@postgres:5432/myent"


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


class DatabaseConfigurationTests(SimpleTestCase):
    """Le repli SQLite est un confort de développement, pas une base de production."""

    def test_postgresql_url_is_used_in_both_modes(self):
        for debug in (True, False):
            config = database_config(POSTGRES_URL, debug=debug)
            self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
            self.assertEqual(config["NAME"], "myent")

    def test_missing_url_falls_back_to_sqlite_in_development(self):
        config = database_config(None, debug=True)
        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")

    def test_missing_url_refuses_to_start_in_production(self):
        """Sinon l'application démarre sur une base jetable et perd tout au redéploiement."""
        with self.assertRaises(ImproperlyConfigured):
            database_config(None, debug=False)
        with self.assertRaises(ImproperlyConfigured):
            database_config("", debug=False)
