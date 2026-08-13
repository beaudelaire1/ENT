from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.settings import addressing_style
from core.serving import serve_private_file, signed_url


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


class FakeBucketFile:
    """Un fichier de bucket : `url` accepte les en-têtes à imposer, comme S3Storage."""

    class Storage:
        # `serve_private_file` reconnaît un stockage objet à cet attribut.
        bucket = "myent-media"

        def url(self, name, parameters=None):
            query = "&".join(f"{key}={value}" for key, value in sorted((parameters or {}).items()))
            return f"https://exemple.r2.cloudflarestorage.com/myent-media/{name}?X-Amz-Signature=abc" + (
                f"&{query}" if query else ""
            )

    def __init__(self, name):
        self.name = name
        self.storage = self.Storage()

    @property
    def url(self):
        return self.storage.url(self.name)


class SignedAddressTests(SimpleTestCase):
    """Ce que la vue décide doit survivre à la redirection vers le stockage.

    Une piste déposée dans le bucket autrement que par MyENT — console du fournisseur,
    `rclone`, restauration — porte le type MIME posé à ce moment-là, souvent
    `application/octet-stream`. Le navigateur, redirigé droit sur le stockage, ne voit que
    celui-là : il refuse de décoder une piste pourtant intacte et marquée prête, alors
    qu'en développement, où Django sert le fichier et pose l'en-tête, elle se lit.
    """

    def test_the_declared_type_travels_with_the_address(self):
        url = signed_url(FakeBucketFile("users/2/audio/piste.mp3"), as_attachment=False, content_type="audio/mpeg")
        self.assertIn("ResponseContentType=audio/mpeg", url)

    def test_a_download_keeps_its_name(self):
        """`as_attachment` était perdu de la même façon : le fichier s'ouvrait dans l'onglet."""
        url = signed_url(FakeBucketFile("users/2/library/résumé du cours.pdf"), as_attachment=True, content_type=None)
        self.assertIn("ResponseContentDisposition=attachment; filename*=UTF-8''r%C3%A9sum%C3%A9%20du%20cours.pdf", url)

    def test_nothing_to_impose_leaves_the_ordinary_address(self):
        url = signed_url(FakeBucketFile("users/2/audio/piste.mp3"), as_attachment=False, content_type=None)
        self.assertNotIn("Response", url)

    def test_the_redirection_carries_the_type(self):
        response = serve_private_file(FakeBucketFile("users/2/audio/piste.mp3"), content_type="audio/mpeg")
        self.assertEqual(response.status_code, 302)
        self.assertIn("ResponseContentType=audio/mpeg", response["Location"])

    def test_the_host_stays_the_one_the_policy_allows(self):
        """Imposer un en-tête ne doit pas déplacer le fichier hors de ce que la CSP autorise."""
        response = serve_private_file(FakeBucketFile("users/2/audio/piste.mp3"), content_type="audio/mpeg")
        self.assertTrue(response["Location"].startswith("https://exemple.r2.cloudflarestorage.com/"))
