from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Invitation
from notifications.models import EmailDelivery, Notification
from notifications.tasks import send_invitation_email


class NotificationViewTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user("alice", password="secret")
        self.bob = get_user_model().objects.create_user("bob", password="secret")
        self.client.force_login(self.alice)
        self.notification = Notification.objects.create(
            owner=self.alice, title="Rappel", message="Un DM à rendre", dedupe_key="test:1", url="/tasks/"
        )

    def test_the_list_shows_only_your_own_notifications(self):
        Notification.objects.create(owner=self.bob, title="Privé de Bob", dedupe_key="test:2")

        response = self.client.get(reverse("notifications:list"))

        self.assertContains(response, "Rappel")
        self.assertNotContains(response, "Privé de Bob")

    def test_marking_one_as_read_redirects_to_its_target(self):
        response = self.client.post(reverse("notifications:read", args=[self.notification.pk]))

        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.read_at)
        self.assertRedirects(response, "/tasks/", fetch_redirect_response=False)

    def test_another_users_notification_cannot_be_marked(self):
        foreign = Notification.objects.create(owner=self.bob, title="Privé", dedupe_key="test:3")

        response = self.client.post(reverse("notifications:read", args=[foreign.pk]))

        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertIsNone(foreign.read_at)

    def test_marking_all_as_read_leaves_other_users_alone(self):
        Notification.objects.create(owner=self.bob, title="Privé", dedupe_key="test:4")

        self.client.post(reverse("notifications:read_all"))

        self.assertFalse(Notification.objects.filter(owner=self.alice, read_at__isnull=True).exists())
        self.assertTrue(Notification.objects.filter(owner=self.bob, read_at__isnull=True).exists())

    def test_the_unread_badge_counts_only_your_own(self):
        Notification.objects.create(owner=self.bob, title="Privé", dedupe_key="test:5")

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.context["unread_notifications"], 1)


class InvitationEmailTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user("staff", password="secret", is_staff=True)
        self.invitation = Invitation.objects.create(
            email="Nouveau@Example.test",
            invited_by=self.staff,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )

    def test_the_invitation_email_is_sent_once(self):
        self.assertEqual(send_invitation_email.run(self.invitation.pk), "sent")
        self.assertEqual(send_invitation_email.run(self.invitation.pk), "already-sent")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["nouveau@example.test"])
        self.assertIn(str(self.invitation.token), mail.outbox[0].body)
        self.assertIsNotNone(EmailDelivery.objects.get().sent_at)

    def test_an_expired_invitation_is_not_emailed(self):
        self.invitation.expires_at = timezone.now() - timezone.timedelta(days=1)
        self.invitation.save()

        self.assertEqual(send_invitation_email.run(self.invitation.pk), "expired")
        self.assertEqual(len(mail.outbox), 0)

    @patch("notifications.tasks.send_mail", side_effect=RuntimeError("SMTP indisponible"))
    def test_a_failed_send_is_not_marked_as_delivered(self, send_mail):
        with self.assertRaises(RuntimeError):
            send_invitation_email.run(self.invitation.pk)

        self.assertIsNone(EmailDelivery.objects.get().sent_at)
