"""Repères de navigation : où l'on est, et où l'on retourne."""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.context_processors import nav_section
from core.navigation import safe_next


class SafeNextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, method="get", **params):
        return getattr(self.factory, method)("/x/", params)

    def test_an_internal_path_is_kept(self):
        self.assertEqual(safe_next(self.request(next="/formations/1/"), "/repli/"), "/formations/1/")

    def test_a_path_with_its_filter_is_kept(self):
        target = "/library/?folder=3&kind=note"
        self.assertEqual(safe_next(self.request(next=target), "/repli/"), target)

    def test_an_external_address_is_refused(self):
        self.assertEqual(safe_next(self.request(next="https://ailleurs.test/"), "/repli/"), "/repli/")

    def test_a_protocol_relative_address_is_refused(self):
        self.assertEqual(safe_next(self.request(next="//ailleurs.test/"), "/repli/"), "/repli/")

    def test_a_missing_address_falls_back(self):
        self.assertEqual(safe_next(self.request(), "/repli/"), "/repli/")

    def test_the_post_body_is_read_too(self):
        """Un envoi rejeté doit conserver sa page de retour, portée par un champ caché."""
        self.assertEqual(safe_next(self.request("post", next="/formations/"), "/repli/"), "/formations/")


class ActiveSectionTests(TestCase):
    """Agenda et Tâches partagent une application : la rubrique se distingue par l'URL."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def test_each_page_marks_its_own_section(self):
        cases = {
            reverse("dashboard:home"): "dashboard",
            reverse("planner:agenda"): "agenda",
            reverse("planner:tasks"): "tasks",
            reverse("library:list"): "library",
            reverse("formations:list"): "formations",
            reverse("sablier:home"): "sablier",
            reverse("accounts:settings"): "settings",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.context["nav_section"], expected)
                self.assertContains(response, 'aria-current="page"')

    def test_a_request_without_resolved_url_has_no_section(self):
        self.assertEqual(nav_section(RequestFactory().get("/")), "")

    def test_a_task_form_keeps_the_tasks_section_active(self):
        response = self.client.get(reverse("planner:task_new"))
        self.assertEqual(response.context["nav_section"], "tasks")
