from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notifications.models import EmailDelivery, Notification
from planner.models import Reminder, Task
from planner.services import sync_task_reminder
from planner.tasks import deliver_reminder


class ReminderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", email="alice@example.com")
        self.task = Task.objects.create(
            owner=self.user,
            title="Échéance",
            reminder_at=timezone.now(),
            email_reminder=True,
        )
        sync_task_reminder(self.task)

    @patch("planner.tasks.send_mail")
    def test_delivery_is_idempotent(self, send_mail):
        # Le compte porte sur la notification du rappel, et non sur le total : la
        # création de la tâche en produit une elle aussi, et compter tout ferait de ce
        # test l'otage de tout ce que l'ENT apprend à signaler.
        reminder = Reminder.objects.get(task=self.task)
        self.assertEqual(deliver_reminder.run(reminder.pk), "sent")
        self.assertEqual(deliver_reminder.run(reminder.pk), "already-sent")
        self.assertEqual(Notification.objects.filter(dedupe_key=f"reminder:{reminder.pk}").count(), 1)
        self.assertEqual(EmailDelivery.objects.count(), 1)
        send_mail.assert_called_once()

    def test_rescheduling_rearms_existing_reminder(self):
        reminder = Reminder.objects.get(task=self.task)
        reminder.status = Reminder.Status.SENT
        reminder.save(update_fields=["status"])
        self.task.reminder_at = timezone.now()
        sync_task_reminder(self.task)
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, Reminder.Status.PENDING)

    def test_completing_task_removes_pending_reminder(self):
        self.task.status = Task.Status.DONE
        self.task.save(update_fields=["status"])
        sync_task_reminder(self.task)
        self.assertFalse(Reminder.objects.filter(task=self.task).exists())

    @patch("planner.tasks.send_mail", side_effect=RuntimeError("SMTP indisponible"))
    def test_failure_is_recorded_before_retry(self, send_mail):
        reminder = Reminder.objects.get(task=self.task)
        with self.assertRaises(RuntimeError):
            deliver_reminder.run(reminder.pk)
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, Reminder.Status.FAILED)
        self.assertIn("SMTP indisponible", reminder.last_error)
