from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.models import Competency, LearningPath, LearningUnit, Period
from planner.models import CalendarEvent, Recurrence, Task, TaskSeries
from planner.services import expand_task_series


class AcademicPlanningTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="Licence")
        self.period = Period.objects.create(path=self.path, title="S5")
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie")
        self.competency = Competency.objects.create(path=self.path, period=self.period, title="Compacité")

    def test_task_can_be_linked_to_academic_context(self):
        response = self.client.post(
            reverse("planner:task_new"),
            {
                "title": "Réviser",
                "status": "todo",
                "priority": 2,
                "unit": self.unit.pk,
                "competency": self.competency.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user)
        self.assertEqual(task.unit, self.unit)
        self.assertEqual(task.competency, self.competency)

    def test_foreign_academic_context_is_rejected(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign_path = LearningPath.objects.create(owner=bob, title="Privée")
        foreign_period = Period.objects.create(path=foreign_path, title="S1")
        foreign_unit = LearningUnit.objects.create(period=foreign_period, title="Privée")
        response = self.client.post(
            reverse("planner:task_new"),
            {"title": "Intrusion", "status": "todo", "priority": 2, "unit": foreign_unit.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.exists())

    def test_week_view_is_bounded_and_filterable(self):
        monday = timezone.make_aware(timezone.datetime(2026, 9, 7, 10, 0))
        CalendarEvent.objects.create(
            owner=self.user,
            title="Cours lié",
            starts_at=monday,
            ends_at=monday + timedelta(hours=2),
            unit=self.unit,
        )
        CalendarEvent.objects.create(
            owner=self.user,
            title="Hors semaine",
            starts_at=monday + timedelta(days=9),
            ends_at=monday + timedelta(days=9, hours=1),
            unit=self.unit,
        )
        response = self.client.get(
            reverse("planner:agenda"), {"view": "week", "date": "2026-09-09", "path": self.path.pk}
        )
        self.assertContains(response, "Cours lié")
        self.assertNotContains(response, "Hors semaine")
        self.assertEqual(len(response.context["days"]), 7)


class TaskSeriesLifecycleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.due = timezone.make_aware(timezone.datetime(2026, 9, 7, 18, 0))

    def test_same_title_does_not_merge_unrelated_series(self):
        first = Task.objects.create(owner=self.user, title="Exercices", due_at=self.due)
        second = Task.objects.create(owner=self.user, title="Exercices", due_at=self.due + timedelta(hours=1))
        expand_task_series(first, Recurrence.WEEKLY, (self.due + timedelta(weeks=2)).date())
        expand_task_series(second, Recurrence.WEEKLY, (self.due + timedelta(weeks=2)).date())
        self.assertEqual(TaskSeries.objects.count(), 2)
        self.assertEqual(first.series.tasks.count(), 3)
        self.assertEqual(second.series.tasks.count(), 3)

    def test_whole_series_can_be_deleted_explicitly(self):
        task = Task.objects.create(owner=self.user, title="Exercices", due_at=self.due)
        expand_task_series(task, Recurrence.WEEKLY, (self.due + timedelta(weeks=2)).date())
        response = self.client.post(reverse("planner:task_series_delete", args=[task.pk]))
        self.assertRedirects(response, reverse("planner:tasks"))
        self.assertFalse(Task.objects.exists())
        self.assertFalse(TaskSeries.objects.exists())
