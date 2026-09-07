from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class DiagnosticCommandTests(TestCase):
    def test_it_reports_the_schedule_the_email_backend_and_the_account(self):
        get_user_model().objects.create_user("bob", email="bob@example.test", password="x")
        out = StringIO()

        call_command("check_notifications", user="bob", stdout=out)

        report = out.getvalue()
        self.assertIn("notifications.scan_for_events", report)
        self.assertIn("EMAIL_HOST", report)
        self.assertIn("bob@example.test", report)

    def test_it_says_so_when_the_account_does_not_exist(self):
        out = StringIO()
        call_command("check_notifications", user="fantome", stdout=out)
        self.assertIn("introuvable", out.getvalue())
