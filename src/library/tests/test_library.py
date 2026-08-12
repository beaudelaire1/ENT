from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from library.forms import LibraryItemForm
from library.models import LibraryItem


class LibrarySecurityTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user("alice", password="secret")
        self.bob = get_user_model().objects.create_user("bob", password="secret")
        self.private_item = LibraryItem.objects.create(
            owner=self.bob, kind=LibraryItem.Kind.LINK, title="Privé", url="https://example.com"
        )

    def test_another_users_item_is_not_visible(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("library:detail", args=[self.private_item.pk])).status_code, 404)
        response = self.client.get(reverse("library:list"))
        self.assertNotContains(response, "Privé")

    def test_rich_note_html_is_sanitized(self):
        form = LibraryItemForm(
            data={
                "kind": LibraryItem.Kind.NOTE,
                "title": "Note sûre",
                "description": "",
                "url": "",
                "note_delta_json": '{"ops":[{"insert":"Bonjour"}]}',
                "note_text_input": "Bonjour",
                "note_html_input": '<p>Bonjour</p><script>alert(1)</script><a href="javascript:alert(2)">x</a>',
            },
            user=self.alice,
        )
        self.assertTrue(form.is_valid(), form.errors)
        item = form.save()
        self.assertNotIn("<script", item.note_html)
        self.assertNotIn("javascript:", item.note_html)

    def test_note_editor_has_no_remote_runtime_dependency(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse("library:new"), {"kind": "note"})
        self.assertContains(response, "library/editor.js")
        self.assertContains(response, "library/editor.css")
        self.assertNotContains(response, "cdn.jsdelivr")
