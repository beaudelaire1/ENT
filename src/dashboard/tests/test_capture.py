from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from library.models import LibraryItem
from planner.models import Task


class CaptureTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.other = get_user_model().objects.create_user("bob")
        self.client.force_login(self.user)

    def capture(self, **data):
        return self.client.post(reverse("dashboard:capture"), {"next": reverse("planner:tasks"), **data})

    def test_a_title_alone_creates_a_task_without_any_formation(self):
        response = self.capture(title="Rappeler le secrétariat")
        task = Task.objects.get(owner=self.user)
        self.assertEqual(task.title, "Rappeler le secrétariat")
        self.assertIsNone(task.due_at)
        self.assertIsNone(task.unit_id)
        self.assertIsNone(task.competency_id)
        self.assertEqual(response["Location"], reverse("planner:tasks"))

    def test_a_task_can_carry_a_due_date(self):
        self.capture(title="Rendre le devoir", due="2026-09-20T18:30")
        due = timezone.localtime(Task.objects.get(owner=self.user).due_at)
        self.assertEqual((due.year, due.month, due.day, due.hour, due.minute), (2026, 9, 20, 18, 30))

    def test_an_empty_title_creates_nothing(self):
        self.capture(title="   ")
        self.assertFalse(Task.objects.exists())
        self.assertFalse(LibraryItem.objects.exists())

    def test_a_link_needs_a_complete_address(self):
        self.capture(title="Cours en ligne", kind="link", url="exemple.org/cours")
        self.assertFalse(LibraryItem.objects.exists())
        self.capture(title="Cours en ligne", kind="link", url="https://exemple.org/cours")
        link = LibraryItem.objects.get(owner=self.user)
        self.assertEqual((link.kind, link.url), (LibraryItem.Kind.LINK, "https://exemple.org/cours"))

    def test_a_note_is_made_like_the_quick_note(self):
        self.capture(title="Idée d'exposé", kind="note")
        self.client.post(reverse("dashboard:quick_note"), {"text": "Idée d'exposé"})
        notes = LibraryItem.objects.filter(owner=self.user, kind=LibraryItem.Kind.NOTE)
        self.assertEqual(notes.count(), 2)
        first, second = notes
        self.assertEqual(
            (first.title, first.note_text, first.note_html), (second.title, second.note_text, second.note_html)
        )

    def test_capture_returns_only_inside_the_site(self):
        response = self.client.post(reverse("dashboard:capture"), {"title": "X", "next": "https://example.com/"})
        self.assertEqual(response["Location"], reverse("dashboard:home"))

    def test_the_capture_button_is_on_every_page(self):
        page = self.client.get(reverse("planner:tasks"))
        self.assertContains(page, 'class="quick-capture"')
        self.assertContains(page, f'action="{reverse("dashboard:capture")}"')
        self.assertContains(page, 'aria-label="Capturer une tâche, une note ou un lien"')


class NoteToTaskTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.client.force_login(self.user)
        self.note = LibraryItem.objects.create(
            owner=self.user, kind=LibraryItem.Kind.NOTE, title="Plan du mémoire", note_text="Trois parties."
        )

    def test_a_note_becomes_a_task_that_keeps_it_as_a_resource(self):
        response = self.client.post(reverse("library:note_to_task", args=[self.note.pk]))
        task = Task.objects.get(owner=self.user)
        self.assertEqual(task.title, "Plan du mémoire")
        self.assertEqual(list(task.resources.all()), [self.note])
        self.assertTrue(response["Location"].startswith(reverse("planner:task_edit", args=[task.pk])))
        self.note.refresh_from_db()
        self.assertEqual(self.note.note_text, "Trois parties.")

    def test_only_a_note_of_the_account_can_become_a_task(self):
        foreign = LibraryItem.objects.create(
            owner=get_user_model().objects.create_user("bob"), kind=LibraryItem.Kind.NOTE, title="Privée"
        )
        link = LibraryItem.objects.create(owner=self.user, kind=LibraryItem.Kind.LINK, title="Lien", url="https://a.b")
        for item in (foreign, link):
            with self.subTest(item=item.title):
                self.assertEqual(self.client.post(reverse("library:note_to_task", args=[item.pk])).status_code, 404)
        self.assertFalse(Task.objects.exists())

    def test_the_note_page_offers_the_conversion(self):
        page = self.client.get(reverse("library:detail", args=[self.note.pk]))
        self.assertContains(page, reverse("library:note_to_task", args=[self.note.pk]))
