from django.test import TestCase
from django.urls import reverse


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
