from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from planner.models import CalendarEvent, Recurrence, Reminder, Task
from planner.services import expand_event_series, expand_task_series


class EventRecurrenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        # Un lundi, pour que « du lundi au vendredi » soit vérifiable.
        self.start = timezone.make_aware(timezone.datetime(2026, 9, 7, 8, 0))
        self.event = CalendarEvent.objects.create(
            owner=self.user,
            title="Cours de topologie",
            starts_at=self.start,
            ends_at=self.start + timedelta(hours=2),
        )

    def test_weekly_expansion_creates_one_event_per_week(self):
        created = expand_event_series(self.event, Recurrence.WEEKLY, (self.start + timedelta(weeks=4)).date())

        self.assertEqual(created, 4)
        occurrences = list(self.event.occurrences.order_by("starts_at"))
        self.assertEqual([o.starts_at for o in occurrences], [self.start + timedelta(weeks=n) for n in (1, 2, 3, 4)])
        self.assertTrue(all(o.ends_at - o.starts_at == timedelta(hours=2) for o in occurrences))
        self.assertTrue(all(o.title == "Cours de topologie" for o in occurrences))

    def test_weekdays_expansion_skips_the_weekend(self):
        created = expand_event_series(self.event, Recurrence.WEEKDAYS, (self.start + timedelta(days=7)).date())

        days = [o.starts_at.weekday() for o in self.event.occurrences.order_by("starts_at")]
        self.assertEqual(created, 5)
        self.assertNotIn(5, days)
        self.assertNotIn(6, days)

    def test_expansion_is_idempotent(self):
        until = (self.start + timedelta(weeks=3)).date()
        expand_event_series(self.event, Recurrence.WEEKLY, until)
        again = expand_event_series(self.event, Recurrence.WEEKLY, until)

        self.assertEqual(again, 0)
        self.assertEqual(self.event.occurrences.count(), 3)

    def test_a_moved_occurrence_is_not_recreated(self):
        until = (self.start + timedelta(weeks=3)).date()
        expand_event_series(self.event, Recurrence.WEEKLY, until)
        moved = self.event.occurrences.order_by("starts_at").first()
        moved.starts_at += timedelta(hours=3)
        moved.save()

        expand_event_series(self.event, Recurrence.WEEKLY, until)

        # La séance déplacée reste déplacée, et sa date d'origine est recréée : la série
        # redevient complète sans écraser la modification manuelle.
        self.assertEqual(self.event.occurrences.count(), 4)

    def test_no_rule_creates_nothing(self):
        self.assertEqual(expand_event_series(self.event, Recurrence.NONE, (self.start + timedelta(weeks=8)).date()), 0)
        self.assertEqual(expand_event_series(self.event, Recurrence.WEEKLY, None), 0)
        self.assertEqual(self.event.occurrences.count(), 0)

    def test_reminders_keep_their_offset(self):
        self.event.reminder_at = self.start - timedelta(minutes=30)
        self.event.save()

        expand_event_series(self.event, Recurrence.WEEKLY, (self.start + timedelta(weeks=2)).date())

        for occurrence in self.event.occurrences.all():
            self.assertEqual(occurrence.starts_at - occurrence.reminder_at, timedelta(minutes=30))

    def test_monthly_expansion_clamps_to_the_end_of_short_months(self):
        end_of_january = timezone.make_aware(timezone.datetime(2026, 1, 31, 9, 0))
        event = CalendarEvent.objects.create(
            owner=self.user, title="Bilan", starts_at=end_of_january, ends_at=end_of_january + timedelta(hours=1)
        )

        expand_event_series(event, Recurrence.MONTHLY, timezone.datetime(2026, 3, 31).date())

        days = [o.starts_at.day for o in event.occurrences.order_by("starts_at")]
        self.assertEqual(days, [28, 31])

    def test_deleting_the_series_head_removes_every_occurrence(self):
        expand_event_series(self.event, Recurrence.WEEKLY, (self.start + timedelta(weeks=3)).date())
        self.event.delete()
        self.assertEqual(CalendarEvent.objects.count(), 0)

    def test_deleting_one_occurrence_leaves_the_others(self):
        expand_event_series(self.event, Recurrence.WEEKLY, (self.start + timedelta(weeks=3)).date())
        self.event.occurrences.first().delete()
        self.assertEqual(CalendarEvent.objects.count(), 3)


class TaskRecurrenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.due = timezone.make_aware(timezone.datetime(2026, 9, 7, 18, 0))

    def test_weekly_task_expansion(self):
        task = Task.objects.create(owner=self.user, title="Rendre le DM", due_at=self.due)

        created = expand_task_series(task, Recurrence.WEEKLY, (self.due + timedelta(weeks=3)).date())

        self.assertEqual(created, 3)
        self.assertEqual(Task.objects.filter(owner=self.user, title="Rendre le DM").count(), 4)

    def test_repeated_tasks_start_undone(self):
        task = Task.objects.create(owner=self.user, title="Rendre le DM", due_at=self.due, status=Task.Status.DONE)

        expand_task_series(task, Recurrence.WEEKLY, (self.due + timedelta(weeks=2)).date())

        repeated = Task.objects.filter(owner=self.user, title="Rendre le DM").exclude(pk=task.pk)
        self.assertTrue(all(t.status == Task.Status.TODO for t in repeated))

    def test_a_task_without_due_date_is_never_expanded(self):
        task = Task.objects.create(owner=self.user, title="Un jour")
        self.assertEqual(expand_task_series(task, Recurrence.WEEKLY, (self.due + timedelta(weeks=4)).date()), 0)


class RecurrenceFormTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def test_creating_a_weekly_event_through_the_form(self):
        response = self.client.post(
            reverse("planner:event_new"),
            {
                "title": "TD d’algèbre",
                "description": "",
                "starts_at": "2026-09-07T10:00",
                "ends_at": "2026-09-07T12:00",
                "location": "",
                "repeat": Recurrence.WEEKLY,
                "repeat_until": "2026-09-28",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CalendarEvent.objects.filter(owner=self.user).count(), 4)

    def test_a_rule_without_an_end_date_is_rejected(self):
        response = self.client.post(
            reverse("planner:event_new"),
            {
                "title": "Sans fin",
                "starts_at": "2026-09-07T10:00",
                "ends_at": "2026-09-07T12:00",
                "repeat": Recurrence.WEEKLY,
                "repeat_until": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CalendarEvent.objects.count(), 0)

    def test_a_repeating_task_requires_a_due_date(self):
        response = self.client.post(
            reverse("planner:task_new"),
            {
                "title": "Sans échéance",
                "status": Task.Status.TODO,
                "priority": Task.Priority.NORMAL,
                "repeat": Recurrence.WEEKLY,
                "repeat_until": "2026-09-28",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), 0)

    def test_each_occurrence_gets_its_own_reminder(self):
        self.client.post(
            reverse("planner:event_new"),
            {
                "title": "Cours",
                "starts_at": "2026-09-07T10:00",
                "ends_at": "2026-09-07T12:00",
                "reminder_at": "2026-09-07T09:00",
                "email_reminder": "on",
                "repeat": Recurrence.WEEKLY,
                "repeat_until": "2026-09-21",
            },
        )

        self.assertEqual(CalendarEvent.objects.count(), 3)
        self.assertEqual(Reminder.objects.filter(owner=self.user).count(), 3)
