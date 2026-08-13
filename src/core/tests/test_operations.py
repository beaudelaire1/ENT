from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.settings import addressing_style


class HealthAndSecurityHeadersTests(TestCase):
    def test_liveness_and_readiness_are_distinct(self):
        self.assertEqual(self.client.get(reverse("live")).json(), {"status": "ok"})
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"], {"database": "ok", "cache": "ok"})

    def test_responses_forbid_remote_scripts_and_frames(self):
        response = self.client.get(reverse("live"), HTTP_X_REQUEST_ID="probe-123")
        self.assertEqual(response["X-Request-ID"], "probe-123")
        policy = response["Content-Security-Policy"]
        self.assertIn("script-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertNotIn("https://cdn", policy)
        self.assertIn("camera=()", response["Permissions-Policy"])

    def test_untrusted_request_id_is_not_reflected(self):
        response = self.client.get(reverse("live"), HTTP_X_REQUEST_ID="bad header value\n")
        self.assertNotEqual(response["X-Request-ID"], "bad header value\n")
        self.assertEqual(len(response["X-Request-ID"]), 32)


class ObjectStorageHostTests(SimpleTestCase):
    """L'hôte des fichiers doit être celui que la politique de sécurité autorise.

    Chacun des deux réglages était défendable seul ; c'est leur désaccord qui bloquait
    tout. boto3 place par défaut le nom du bucket en sous-domaine du point de terminaison,
    alors que `SecurityHeadersMiddleware` n'autorise que le point de terminaison nu — et
    une politique CSP ne couvre pas les sous-domaines implicitement. Chaque piste audio
    était refusée par le navigateur, sans aucune erreur côté serveur.
    """

    ENDPOINT = "https://exemple.r2.cloudflarestorage.com"

    def csp_media_sources(self):
        from core.middleware import SecurityHeadersMiddleware

        return SecurityHeadersMiddleware.external_sources()

    @override_settings(AWS_S3_ENDPOINT_URL=ENDPOINT, CSP_EXTERNAL_MEDIA_SOURCES=[])
    def test_the_policy_allows_the_bare_endpoint(self):
        self.assertIn(self.ENDPOINT, self.csp_media_sources())

    @override_settings(AWS_S3_ENDPOINT_URL=ENDPOINT, CSP_EXTERNAL_MEDIA_SOURCES=[])
    def test_the_policy_does_not_cover_a_bucket_subdomain(self):
        """Ce que la CSP refuse — et donc ce que l'adressage ne doit jamais produire."""
        self.assertNotIn("https://mon-bucket.exemple.r2.cloudflarestorage.com", self.csp_media_sources())

    def test_a_custom_endpoint_forces_path_addressing(self):
        self.assertEqual(addressing_style(self.ENDPOINT, None), "path")

    def test_amazon_keeps_the_subdomain_form(self):
        """Sans point de terminaison imposé, l'adressage historique d'AWS reste correct."""
        self.assertEqual(addressing_style(None, None), "virtual")

    def test_an_explicit_choice_wins(self):
        self.assertEqual(addressing_style(self.ENDPOINT, "virtual"), "virtual")
