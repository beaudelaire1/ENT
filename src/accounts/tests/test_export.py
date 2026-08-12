from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from formations.models import LearningPath
from library.models import LibraryItem


class AccountExportTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user(
            "alice", email="alice@example.com", password="not-exported-secret"
        )
        self.bob = get_user_model().objects.create_user("bob", password="private")
        LearningPath.objects.create(owner=self.alice, title="Licence Alice")
        LibraryItem.objects.create(owner=self.alice, kind="note", title="Note Alice", note_text="contenu")
        LibraryItem.objects.create(owner=self.bob, kind="note", title="Secret Bob", note_text="privé")
        self.client.force_login(self.alice)

    def test_export_is_personal_and_contains_no_authentication_secret(self):
        response = self.client.get(reverse("accounts:export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        payload = response.json()
        rendered = response.content.decode()
        self.assertEqual(payload["schema"], "myent.account-export")
        self.assertIn("Licence Alice", rendered)
        self.assertIn("Note Alice", rendered)
        self.assertNotIn("Secret Bob", rendered)
        self.assertNotIn("not-exported-secret", rendered)
        self.assertNotIn("password", rendered.lower())

    def test_export_requires_authentication(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("accounts:export")).status_code, 302)
