from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticatedPagesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("member", password="secret")
        self.client.force_login(self.user)

    def test_main_ent_modules_render(self):
        urls = [
            reverse("dashboard:home"),
            reverse("planner:agenda"),
            reverse("planner:tasks"),
            reverse("library:list"),
            reverse("formations:list"),
            reverse("sablier:home"),
            reverse("notifications:list"),
            reverse("accounts:settings"),
            reverse("search") + "?q=test",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_personal_routes_require_authentication(self):
        self.client.logout()
        for url in (reverse("dashboard:home"), reverse("library:list"), reverse("sablier:home")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:login"), response.url)
