from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from planner.models import Reminder, Task
from planner.today import task_agenda
from planner.undo import SESSION_KEY

CAYENNE = ZoneInfo("America/Cayenne")
PARIS = ZoneInfo("Europe/Paris")


def keys(groups):
    return {group["key"]: [task.title for task in group["tasks"]] for group in groups}


class TaskAgendaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")

    def task(self, title, due=None, **extra):
        return Task.objects.create(owner=self.user, title=title, due_at=due, **extra)

    def test_tasks_are_grouped_by_local_day_near_midnight(self):
        day = date(2026, 9, 15)
        with timezone.override(CAYENNE):
            # 23 h 30 à Cayenne est déjà le 16 en temps universel : la tâche reste du jour.
            self.task("Ce soir", datetime(2026, 9, 15, 23, 30, tzinfo=CAYENNE))
            self.task("Hier", datetime(2026, 9, 14, 18, 0, tzinfo=CAYENNE))
            self.task("Jeudi", datetime(2026, 9, 17, 9, 0, tzinfo=CAYENNE))
            self.task("Dans un mois", datetime(2026, 10, 15, 9, 0, tzinfo=CAYENNE))
            self.task("Un jour")
            self.task("Déjà faite", datetime(2026, 9, 15, 10, 0, tzinfo=CAYENNE), status=Task.Status.DONE)
            groups = keys(task_agenda(self.user, day))
        self.assertEqual(groups["overdue"], ["Hier"])
        self.assertEqual(groups["today"], ["Ce soir"])
        self.assertEqual(groups["upcoming"], ["Jeudi"])
        self.assertEqual(groups["undated"], ["Un jour"])

    def test_the_same_instant_falls_on_the_next_day_in_paris(self):
        moment = datetime(2026, 9, 15, 23, 30, tzinfo=CAYENNE)
        self.task("Ce soir", moment)
        with timezone.override(PARIS):
            groups = keys(task_agenda(self.user, date(2026, 9, 16)))
        self.assertEqual(groups["today"], ["Ce soir"])

    def test_a_close_deadline_is_not_hidden_behind_distant_priorities(self):
        with timezone.override(CAYENNE):
            now = timezone.now()
            for index in range(8):
                self.task(f"Important {index}", now + timedelta(days=20), priority=Task.Priority.HIGH)
            self.task("Ce soir", now + timedelta(minutes=30), priority=Task.Priority.LOW)
            groups = task_agenda(self.user, timezone.localdate())
        today = next(group for group in groups if group["key"] == "today")
        self.assertIn("Ce soir", [task.title for task in today["tasks"]])

    def test_groups_are_bounded_and_report_what_they_hide(self):
        for index in range(9):
            self.task(f"Sans date {index}")
        undated = next(group for group in task_agenda(self.user) if group["key"] == "undated")
        self.assertEqual(len(undated["tasks"]), 6)
        self.assertEqual(undated["more"], 3)


class PostponeAndUndoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.other = get_user_model().objects.create_user("bob")
        self.client.force_login(self.user)
        self.due = timezone.make_aware(datetime.combine(timezone.localdate() - timedelta(days=3), datetime.min.time()))
        self.due = self.due.replace(hour=18, minute=30)
        self.task = Task.objects.create(
            owner=self.user, title="Rapport", due_at=self.due, reminder_at=self.due - timedelta(hours=2)
        )

    def postpone(self, **data):
        return self.client.post(reverse("planner:task_postpone", args=[self.task.pk]), data)

    def test_tomorrow_starts_from_today_and_keeps_the_time_and_reminder_advance(self):
        self.postpone(to="tomorrow")
        self.task.refresh_from_db()
        local = timezone.localtime(self.task.due_at)
        self.assertEqual(local.date(), timezone.localdate() + timedelta(days=1))
        self.assertEqual((local.hour, local.minute), (18, 30))
        self.assertEqual(self.task.due_at - self.task.reminder_at, timedelta(hours=2))
        self.assertEqual(Reminder.objects.get(task=self.task).scheduled_for, self.task.reminder_at)

    def test_a_chosen_date_in_the_past_is_refused(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self.postpone(to="date", date=yesterday.isoformat())
        self.task.refresh_from_db()
        self.assertEqual(self.task.due_at, self.due)

    def test_another_accounts_task_cannot_be_postponed(self):
        foreign = Task.objects.create(owner=self.other, title="Privée", due_at=self.due)
        response = self.client.post(reverse("planner:task_postpone", args=[foreign.pk]), {"to": "week"})
        self.assertEqual(response.status_code, 404)

    def test_postponing_returns_only_inside_the_site(self):
        response = self.postpone(to="week", next="https://example.com/ailleurs")
        self.assertEqual(response["Location"], reverse("planner:tasks"))

    def test_undo_restores_a_postponed_task_once(self):
        self.postpone(to="week")
        self.client.post(reverse("planner:task_undo"))
        self.task.refresh_from_db()
        self.assertEqual(self.task.due_at, self.due)
        self.assertEqual(self.task.reminder_at, self.due - timedelta(hours=2))
        # L'emplacement est vidé : un second clic ne rétablit rien.
        self.client.post(reverse("planner:task_toggle", args=[self.task.pk]))
        self.client.post(reverse("planner:task_undo"))
        self.client.post(reverse("planner:task_undo"))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)

    def test_undo_reopens_a_task_finished_by_mistake(self):
        self.client.post(reverse("planner:task_toggle", args=[self.task.pk]))
        page = self.client.get(reverse("dashboard:home"))
        self.assertContains(page, "« Rapport » est terminée.")
        self.client.post(reverse("planner:task_undo"))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)

    def test_undo_expires_after_ten_minutes(self):
        self.client.post(reverse("planner:task_toggle", args=[self.task.pk]))
        later = timezone.now() + timedelta(minutes=11)
        with mock.patch("planner.undo.timezone.now", return_value=later):
            self.client.post(reverse("planner:task_undo"))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)

    def test_a_session_cannot_restore_another_accounts_task(self):
        foreign = Task.objects.create(owner=self.other, title="Privée", status=Task.Status.DONE)
        session = self.client.session
        session[SESSION_KEY] = {
            "task": foreign.pk,
            "status": Task.Status.TODO,
            "due_at": None,
            "reminder_at": None,
            "label": "piège",
            "expires": (timezone.now() + timedelta(minutes=5)).isoformat(),
        }
        session.save()
        self.client.post(reverse("planner:task_undo"))
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, Task.Status.DONE)


class TodayDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.client.force_login(self.user)

    def test_the_home_screen_groups_tasks_and_offers_their_actions(self):
        overdue = Task.objects.create(owner=self.user, title="Oubliée", due_at=timezone.now() - timedelta(days=2))
        page = self.client.get(reverse("dashboard:home"))
        self.assertContains(page, "En retard")
        self.assertContains(page, reverse("planner:task_postpone", args=[overdue.pk]))
        self.assertContains(page, f"{reverse('planner:event_new')}?task={overdue.pk}")

    def test_planning_from_a_task_prefills_the_event(self):
        task = Task.objects.create(owner=self.user, title="Réviser la compacité")
        page = self.client.get(reverse("planner:event_new"), {"task": task.pk})
        self.assertContains(page, 'value="Réviser la compacité"')
        foreign = Task.objects.create(owner=get_user_model().objects.create_user("bob"), title="Privée")
        page = self.client.get(reverse("planner:event_new"), {"task": foreign.pk})
        self.assertNotContains(page, 'value="Privée"')
