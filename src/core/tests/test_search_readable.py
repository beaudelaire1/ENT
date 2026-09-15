from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.search import count_by_type, highlight_excerpt, query_terms
from library.models import LibraryItem
from planner.models import Task


class HighlightTests(SimpleTestCase):
    def test_html_is_escaped_and_every_term_is_marked(self):
        excerpt = highlight_excerpt("<script>alert(1)</script> La compacité et la Topologie", "compacité topologie")
        self.assertIn("&lt;script&gt;", excerpt)
        self.assertNotIn("<script>", excerpt)
        self.assertIn("<mark>compacité</mark>", excerpt)
        self.assertIn("<mark>Topologie</mark>", excerpt)

    def test_a_term_that_looks_like_html_cannot_inject_markup(self):
        excerpt = highlight_excerpt("Balise <b> dans une note", "<b>")
        self.assertIn("<mark>&lt;b&gt;</mark>", excerpt)
        self.assertNotIn("<b>", excerpt.replace("<mark>", "").replace("</mark>", ""))

    def test_quoted_phrases_stay_whole_and_exclusions_are_never_marked(self):
        self.assertEqual(query_terms('"espace compact" -topologie or suite'), ["espace compact", "suite"])
        excerpt = highlight_excerpt("Un espace compact en topologie", '"espace compact" -topologie')
        self.assertIn("<mark>espace compact</mark>", excerpt)
        self.assertNotIn("<mark>topologie</mark>", excerpt)

    def test_the_excerpt_is_cut_around_the_first_occurrence(self):
        text = "début " + "remplissage " * 80 + "le théorème de Heine " + "suite " * 80
        excerpt = highlight_excerpt(text, "Heine")
        self.assertTrue(excerpt.startswith("…"))
        self.assertTrue(excerpt.endswith("…"))
        self.assertIn("<mark>Heine</mark>", excerpt)
        self.assertLess(len(excerpt), 260)

    def test_without_any_occurrence_the_excerpt_starts_at_the_beginning(self):
        self.assertEqual(highlight_excerpt("Court texte", "absent"), "Court texte")


class SearchCountsTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user("alice")
        bob = get_user_model().objects.create_user("bob")
        Task.objects.create(owner=self.alice, title="Réviser la compacité")
        Task.objects.create(owner=self.alice, title="Exercices", description="compacité des fermés bornés")
        LibraryItem.objects.create(
            owner=self.alice, kind=LibraryItem.Kind.NOTE, title="Fiche", note_text="La compacité en résumé"
        )
        Task.objects.create(owner=bob, title="compacité privée")
        self.client.force_login(self.alice)

    def test_counts_per_type_belong_to_the_account(self):
        self.assertEqual(count_by_type(self.alice, "compacité"), {"task": 2, "library": 1})
        self.assertEqual(count_by_type(self.alice, "  "), {})

    def test_filters_keep_their_counts_while_one_type_is_selected(self):
        page = self.client.get(reverse("search"), {"q": "compacité", "type": "task"})
        self.assertContains(page, 'Tout <span class="chip-count">3</span>')
        self.assertContains(page, 'Tâches <span class="chip-count">2</span>')
        self.assertContains(page, 'Bibliothèque <span class="chip-count">1</span>')
        self.assertNotContains(page, "Agenda <span")

    def test_results_show_highlighted_excerpts(self):
        page = self.client.get(reverse("search"), {"q": "compacité"})
        self.assertContains(page, "<mark>compacité</mark> des fermés bornés")


class SearchShortcutTests(TestCase):
    def test_the_header_search_announces_its_shortcut(self):
        user = get_user_model().objects.create_user("alice")
        self.client.force_login(user)
        page = self.client.get(reverse("search"))
        self.assertContains(page, 'aria-keyshortcuts="/ Control+K Meta+K"')
        self.assertContains(page, "data-global-search")
        self.assertContains(page, "<kbd>/</kbd>")
        script = (settings.BASE_DIR / "static" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("[data-global-search]", script)
