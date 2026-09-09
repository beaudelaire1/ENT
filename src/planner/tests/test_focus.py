from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planner.focus import period_start
from planner.models import Task, TaskFocus


class FocusPeriodTests(TestCase):
    def test_period_starts_are_calendar_based(self):
        day = date(2026, 9, 9)  # mercredi
        self.assertEqual(period_start(TaskFocus.Scope.DAY, day), date(2026, 9, 9))
        self.assertEqual(period_start(TaskFocus.Scope.WEEK, day), date(2026, 9, 7))
        self.assertEqual(period_start(TaskFocus.Scope.MONTH, day), date(2026, 9, 1))

    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            period_start("quarter", date(2026, 9, 9))


class TaskFocusViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.other = get_user_model().objects.create_user("bob", password="secret")
        self.first = Task.objects.create(owner=self.user, title="Algèbre")
        self.second = Task.objects.create(owner=self.user, title="Analyse")
        self.client.force_login(self.user)

    @mock.patch("planner.focus.timezone.localdate", return_value=date(2026, 9, 9))
    def test_a_scope_has_exactly_one_choice_for_the_current_period(self, _localdate):
        self.client.post(reverse("planner:task_focus", args=[self.first.pk, "week"]))
        self.client.post(reverse("planner:task_focus", args=[self.second.pk, "week"]))

        selections = TaskFocus.objects.filter(owner=self.user, scope=TaskFocus.Scope.WEEK)
        self.assertEqual(selections.count(), 1)
        self.assertEqual(selections.get().task, self.second)
        self.assertEqual(selections.get().period_start, date(2026, 9, 7))

    @mock.patch("planner.focus.timezone.localdate", return_value=date(2026, 9, 9))
    def test_day_week_and_month_are_independent(self, _localdate):
        for scope in TaskFocus.Scope.values:
            self.client.post(reverse("planner:task_focus", args=[self.first.pk, scope]))

        self.assertEqual(TaskFocus.objects.filter(owner=self.user).count(), 3)
        self.assertEqual(
            set(TaskFocus.objects.values_list("period_start", flat=True)),
            {date(2026, 9, 9), date(2026, 9, 7), date(2026, 9, 1)},
        )

    def test_another_users_task_cannot_be_selected(self):
        foreign = Task.objects.create(owner=self.other, title="Privée")
        response = self.client.post(reverse("planner:task_focus", args=[foreign.pk, "day"]))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(TaskFocus.objects.exists())

    def test_a_completed_task_cannot_be_selected(self):
        self.first.status = Task.Status.DONE
        self.first.save(update_fields=["status", "updated_at"])
        response = self.client.post(reverse("planner:task_focus", args=[self.first.pk, "day"]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TaskFocus.objects.exists())

    @mock.patch("planner.focus.timezone.localdate", return_value=date(2026, 9, 9))
    def test_clearing_only_removes_the_current_period(self, _localdate):
        TaskFocus.objects.create(
            owner=self.user,
            task=self.first,
            scope=TaskFocus.Scope.DAY,
            period_start=date(2026, 9, 8),
        )
        TaskFocus.objects.create(
            owner=self.user,
            task=self.second,
            scope=TaskFocus.Scope.DAY,
            period_start=date(2026, 9, 9),
        )

        self.client.post(reverse("planner:task_focus_clear", args=["day"]))

        self.assertTrue(TaskFocus.objects.filter(period_start=date(2026, 9, 8)).exists())
        self.assertFalse(TaskFocus.objects.filter(period_start=date(2026, 9, 9)).exists())

    def test_a_task_opens_a_session_and_the_session_knows_where_to_come_back(self):
        """Choisir une priorité puis chercher le Sablier dans le menu, c'est deux gestes
        pour une seule intention — et rien, au retour, ne ramenait à la liste.

        Le lien porte donc les deux bouts : ce qu'on va travailler, et d'où l'on vient.
        Sans l'adresse de retour, le Sablier ouvre bien la session mais laisse l'étudiant
        en sortir par l'accueil, c'est-à-dire nulle part près de sa tâche.
        """
        tasks = reverse("planner:tasks")
        response = self.client.get(tasks)
        self.assertContains(response, f"{reverse('sablier:home')}?intention=Alg%C3%A8bre")
        self.assertContains(response, f"next={tasks}")

        session = self.client.get(reverse("sablier:home"), {"intention": "Algèbre", "duration": "25", "next": tasks})
        self.assertContains(session, "Algèbre")
        self.assertContains(session, f'id="return-after-session" href="{tasks}"')
