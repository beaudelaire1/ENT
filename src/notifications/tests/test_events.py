"""Ce dont l'ENT informe, et ce qu'il refuse de faire.

Le défaut d'origine n'était pas un bogue : la plomberie fonctionnait, mais un seul
événement — un rappel posé à la main — produisait une notification. Ces tests tiennent
l'inverse : chaque famille déclarée a un producteur, et chaque producteur est réglable.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.models import Competency, LearningPath, ProgressRecord
from notifications.catalog import EVENTS, FAMILIES, FAMILY_BY_KEY
from notifications.models import Notification, NotificationPreference
from notifications.scanning import scan_user
from notifications.services import notify
from planner.models import Task


class CatalogTests(TestCase):
    def test_every_event_belongs_to_a_declared_family(self):
        """Un événement sans famille serait notifié sans pouvoir être éteint."""
        for event in EVENTS:
            with self.subTest(event=event.key):
                self.assertIn(event.family, FAMILY_BY_KEY)

    def test_every_family_carries_at_least_one_event(self):
        """Une famille sans événement offrirait un réglage sans effet."""
        for family in FAMILIES:
            with self.subTest(family=family.key):
                self.assertTrue([event for event in EVENTS if event.family == family.key])

    def test_every_declared_event_has_a_producer(self):
        """Déclarer sans produire, c'est promettre à l'écran ce qui n'arrivera jamais.

        La page de préférences est construite à partir du catalogue : un événement
        déclaré y apparaît, avec sa case, et l'utilisateur attend légitimement d'en être
        informé. J'ai commis exactement cette erreur — un « espace de stockage bientôt
        atteint » annoncé alors que rien ne le surveillait — et rien ne l'a signalé.
        """
        from pathlib import Path

        import notifications
        from planner import tasks as planner_tasks

        roots = [Path(notifications.__file__).parent, Path(planner_tasks.__file__)]
        sources = []
        for root in roots:
            paths = root.rglob("*.py") if root.is_dir() else [root]
            sources += [
                path.read_text(encoding="utf-8")
                for path in paths
                if "tests" not in path.parts and path.name != "catalog.py"
            ]
        produced = "".join(sources)
        for event in EVENTS:
            with self.subTest(event=event.key):
                self.assertIn(f'"{event.key}"', produced)

    def test_notifying_under_an_undeclared_key_fails_loudly(self):
        user = get_user_model().objects.create_user("alice", password="x")
        with self.assertRaises(KeyError):
            notify(user, "inventé.par.erreur", dedupe_key="k", title="T")


class DeliveryRulesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", email="alice@example.test", password="x")

    def test_a_non_urgent_event_stays_in_the_app(self):
        notify(self.user, "task.created", dedupe_key="t:1", title="Nouvelle tâche")
        self.assertEqual(Notification.objects.filter(owner=self.user).count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_an_urgent_event_is_also_sent_by_email(self):
        notify(self.user, "task.overdue", dedupe_key="t:2", title="En retard", message="Depuis hier.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("En retard", mail.outbox[0].subject)

    def test_the_same_fact_is_never_announced_twice(self):
        """Les producteurs périodiques repassent : la clé, elle, ne bouge pas."""
        for _ in range(3):
            notify(self.user, "task.overdue", dedupe_key="t:3", title="En retard")
        self.assertEqual(Notification.objects.filter(owner=self.user, dedupe_key="t:3").count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_a_disabled_family_produces_nothing_at_all(self):
        NotificationPreference.objects.create(owner=self.user, family="tasks", enabled=False)
        notify(self.user, "task.overdue", dedupe_key="t:4", title="En retard")
        self.assertFalse(Notification.objects.filter(owner=self.user).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_email_can_be_silenced_while_keeping_the_bell(self):
        NotificationPreference.objects.create(owner=self.user, family="tasks", enabled=True, email=False)
        notify(self.user, "task.overdue", dedupe_key="t:5", title="En retard")
        self.assertTrue(Notification.objects.filter(owner=self.user).exists())
        self.assertEqual(len(mail.outbox), 0)


class CreationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="x")

    def test_creating_a_task_informs_its_owner(self):
        Task.objects.create(owner=self.user, title="Réviser la topologie")
        self.assertTrue(Notification.objects.filter(owner=self.user, title__contains="Réviser la topologie").exists())

    def test_editing_a_task_announces_nothing(self):
        """Une modification n'est pas une nouvelle."""
        task = Task.objects.create(owner=self.user, title="Réviser")
        Notification.objects.all().delete()
        task.title = "Réviser deux fois"
        task.save()
        self.assertFalse(Notification.objects.exists())

    def test_a_competency_is_attributed_through_its_path(self):
        """Une compétence n'a pas de propriétaire à elle : il faut remonter au parcours."""
        path = LearningPath.objects.create(owner=self.user, title="Licence")
        Notification.objects.all().delete()
        Competency.objects.create(path=path, title="Rédiger une démonstration")
        self.assertTrue(Notification.objects.filter(owner=self.user, title__contains="Rédiger").exists())


class ScanningTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", email="alice@example.test", password="x")

    def test_an_overdue_task_is_reported_once_and_only_once(self):
        Task.objects.create(owner=self.user, title="Rendre le rapport", due_at=timezone.now() - timedelta(days=2))
        Notification.objects.all().delete()
        scan_user(self.user)
        scan_user(self.user)
        self.assertEqual(Notification.objects.filter(owner=self.user, title__startswith="En retard").count(), 1)

    def test_a_task_with_its_own_reminder_is_left_alone(self):
        """L'utilisateur a déjà dit comment il voulait l'apprendre : deux fois serait une de trop."""
        Task.objects.create(
            owner=self.user,
            title="Rendre le mémoire",
            due_at=timezone.now() + timedelta(hours=3),
            reminder_at=timezone.now() + timedelta(hours=1),
        )
        Notification.objects.all().delete()
        scan_user(self.user)
        self.assertFalse(Notification.objects.filter(title__startswith="Bientôt").exists())

    def test_reaching_the_estimated_hours_is_announced(self):
        path = LearningPath.objects.create(owner=self.user, title="Licence")
        competency = Competency.objects.create(path=path, title="Analyse")
        record, _ = ProgressRecord.objects.get_or_create(owner=self.user, competency=competency)
        record.planned_hours = Decimal("10")
        record.manual_hours = Decimal("10")
        record.save()
        Notification.objects.all().delete()
        scan_user(self.user)
        self.assertTrue(Notification.objects.filter(title__startswith="Objectif d'heures atteint").exists())

    def test_hours_below_the_estimate_say_nothing(self):
        path = LearningPath.objects.create(owner=self.user, title="Licence")
        competency = Competency.objects.create(path=path, title="Analyse")
        record, _ = ProgressRecord.objects.get_or_create(owner=self.user, competency=competency)
        record.planned_hours = Decimal("10")
        record.manual_hours = Decimal("4")
        record.save()
        Notification.objects.all().delete()
        scan_user(self.user)
        self.assertFalse(Notification.objects.filter(title__startswith="Objectif d'heures").exists())


class PreferencePageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret-1234")
        self.client.force_login(self.user)

    def test_the_page_lists_every_declared_family(self):
        response = self.client.get(reverse("notifications:preferences"))
        self.assertEqual(response.status_code, 200)
        for family in FAMILIES:
            with self.subTest(family=family.key):
                self.assertContains(response, family.label)

    def test_unchecking_a_family_silences_it(self):
        self.client.post(reverse("notifications:preferences"), {"tasks:enabled": "on"})
        saved = {p.family: p for p in NotificationPreference.objects.filter(owner=self.user)}
        self.assertTrue(saved["tasks"].enabled)
        self.assertFalse(saved["agenda"].enabled)
        self.assertFalse(saved["tasks"].email)

    def test_a_user_who_never_chose_receives_everything(self):
        """L'absence de réglage vaut consentement : personne ne devient muet par migration."""
        self.assertFalse(NotificationPreference.objects.filter(owner=self.user).exists())
        notify(self.user, "task.created", dedupe_key="x:1", title="Nouvelle tâche")
        self.assertTrue(Notification.objects.filter(owner=self.user).exists())
