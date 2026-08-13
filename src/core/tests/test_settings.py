"""Réglages dont une erreur ne se voit pas à l'exécution."""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import DATABASE_FREE_COMMANDS, build_middleware, database_config, force_https, optional_bool

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

    def test_the_fallback_is_allowed_where_nothing_is_served(self):
        """Tests et construction de l'image : `collectstatic` tourne sans base, avant tout secret.

        Sans cette dérogation, le garde-fou ferait échouer la construction de l'image
        Docker elle-même — bien avant qu'il soit question de servir quoi que ce soit.
        """
        config = database_config(None, debug=False, allow_fallback=True)
        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")

    def test_the_database_free_commands_cover_the_image_build(self):
        """Les commandes de la dérogation sont bien celles que le Dockerfile exécute."""
        dockerfile = (Path(__file__).resolve().parents[3] / "Dockerfile").read_text(encoding="utf-8")
        for command in ("generate_chime", "collectstatic"):
            self.assertIn(command, dockerfile)
            self.assertIn(command, DATABASE_FREE_COMMANDS)


class OptionalBoolTests(SimpleTestCase):
    """Un booléen à trois états, pour distinguer « faux » de « pas posé »."""

    def test_unset_is_none(self):
        self.assertIsNone(optional_bool(None))
        self.assertIsNone(optional_bool(""))
        self.assertIsNone(optional_bool("   "))

    def test_recognized_spellings(self):
        for value in ("1", "true", "True", "yes", "on"):
            self.assertIs(optional_bool(value), True)
        for value in ("0", "false", "False", "no", "off"):
            self.assertIs(optional_bool(value), False)


class ForceHttpsTests(SimpleTestCase):
    """HTTPS est exigé en production et interdit sous les tests, sauf dérogation explicite.

    Le client de test parle en clair : avec la redirection active, chaque requête
    recevait un 301 avant d'atteindre sa vue, et la suite entière tombait — mais
    seulement en intégration continue, où `DJANGO_DEBUG` vaut false.
    """

    def test_production_requires_https(self):
        self.assertTrue(force_https(debug=False, running_tests=False, override=None))

    def test_development_does_not(self):
        self.assertFalse(force_https(debug=True, running_tests=False, override=None))

    def test_the_test_suite_never_requires_it(self):
        self.assertFalse(force_https(debug=False, running_tests=True, override=None))
        self.assertFalse(force_https(debug=True, running_tests=True, override=None))

    def test_an_explicit_override_wins_in_production(self):
        """Le cas visé : un domaine de test sans certificat valable, DEBUG resté à false."""
        self.assertFalse(force_https(debug=False, running_tests=False, override=False))

    def test_an_explicit_override_wins_in_development_too(self):
        self.assertTrue(force_https(debug=True, running_tests=False, override=True))
