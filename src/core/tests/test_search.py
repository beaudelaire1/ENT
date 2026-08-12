from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import SearchEntry
from core.search import reindex_all, search
from formations.models import LearningPath, LearningUnit, Period
from formations.tests.factories import competency_in
from library.models import LibraryItem
from planner.models import CalendarEvent, Task


class SearchIndexTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user("alice", password="secret")
        self.bob = get_user_model().objects.create_user("bob", password="secret")

    def test_saving_an_object_indexes_it(self):
        item = LibraryItem.objects.create(
            owner=self.alice, kind=LibraryItem.Kind.LINK, title="Manuel", url="https://example.com"
        )
        entry = SearchEntry.objects.get(object_type="library", object_id=item.pk)
        self.assertEqual(entry.owner, self.alice)
        self.assertEqual(entry.title, "Manuel")
        self.assertEqual(entry.url, reverse("library:detail", args=[item.pk]))

    def test_updating_an_object_updates_its_entry(self):
        item = LibraryItem.objects.create(
            owner=self.alice, kind=LibraryItem.Kind.LINK, title="Ancien", url="https://example.com"
        )
        item.title = "Nouveau"
        item.save()
        entries = SearchEntry.objects.filter(object_type="library", object_id=item.pk)
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.get().title, "Nouveau")

    def test_deleting_an_object_removes_its_entry(self):
        item = LibraryItem.objects.create(
            owner=self.alice, kind=LibraryItem.Kind.LINK, title="Éphémère", url="https://example.com"
        )
        item.delete()
        self.assertFalse(SearchEntry.objects.filter(object_type="library", object_id=item.pk).exists())

    def test_competency_is_indexed_for_the_owner_of_its_path(self):
        path = LearningPath.objects.create(owner=self.alice, title="Licence")
        period = Period.objects.create(path=path, title="Semestre")
        unit = LearningUnit.objects.create(period=period, title="Module")
        competency = competency_in(unit, title="Démontrer une récurrence")
        entry = SearchEntry.objects.get(object_type="competency", object_id=competency.pk)
        self.assertEqual(entry.owner, self.alice)


class SearchQueryTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user("alice", password="secret")
        self.bob = get_user_model().objects.create_user("bob", password="secret")
        LibraryItem.objects.create(
            owner=self.alice, kind=LibraryItem.Kind.LINK, title="Topologie", url="https://example.com"
        )
        Task.objects.create(owner=self.alice, title="Réviser la topologie")
        CalendarEvent.objects.create(
            owner=self.alice,
            title="Examen",
            description="topologie",
            starts_at=timezone.now(),
            ends_at=timezone.now(),
        )
        LibraryItem.objects.create(
            owner=self.bob, kind=LibraryItem.Kind.LINK, title="Topologie", url="https://example.com"
        )

    def test_results_span_every_module(self):
        found = {entry.object_type for entry in search(self.alice, "topologie")}
        self.assertEqual(found, {"library", "task", "event"})

    def test_results_are_limited_to_their_owner(self):
        self.assertEqual(search(self.bob, "topologie").count(), 1)

    def test_type_filter_narrows_results(self):
        results = search(self.alice, "topologie", "task")
        self.assertEqual([entry.object_type for entry in results], ["task"])

    def test_empty_query_returns_nothing(self):
        self.assertEqual(search(self.alice, "   ").count(), 0)

    def test_view_renders_results(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse("search"), {"q": "topologie"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Réviser la topologie")

    def test_view_hides_another_users_content(self):
        LibraryItem.objects.create(
            owner=self.bob, kind=LibraryItem.Kind.NOTE, title="Secret de Bob", note_text="topologie"
        )
        self.client.force_login(self.alice)
        response = self.client.get(reverse("search"), {"q": "topologie"})
        self.assertNotContains(response, "Secret de Bob")


class ReindexTests(TestCase):
    def test_reindex_rebuilds_a_lost_index(self):
        alice = get_user_model().objects.create_user("alice", password="secret")
        LibraryItem.objects.create(owner=alice, kind=LibraryItem.Kind.LINK, title="Manuel", url="https://example.com")
        Task.objects.create(owner=alice, title="Réviser")
        SearchEntry.objects.all().delete()

        counts = reindex_all()

        self.assertEqual(counts["library"], 1)
        self.assertEqual(counts["task"], 1)
        self.assertEqual(SearchEntry.objects.count(), 2)
        self.assertEqual(search(alice, "Manuel").count(), 1)

    def test_management_command_runs(self):
        call_command("reindex_search")
