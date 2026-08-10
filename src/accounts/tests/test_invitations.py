from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Invitation
from notifications.models import EmailDelivery
from notifications.tasks import send_invitation_email


class InvitationTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user("admin", is_staff=True)
        self.invitation = Invitation.objects.create(
            email="Invitee@Example.com",
            invited_by=self.staff,
            expires_at=timezone.now() + timedelta(days=1),
        )

    def test_invitation_is_single_use_and_verifies_email(self):
        url = reverse("accounts:accept_invitation", args=[self.invitation.token])
        response = self.client.post(
            url,
            {
                "username": "invitee",
                "display_name": "Invitée",
                "password1": "A-long-random-password-391!",
                "password2": "A-long-random-password-391!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:home"))
        user = get_user_model().objects.get(username="invitee")
        self.assertEqual(user.email, "invitee@example.com")
        self.assertIsNotNone(user.profile.email_verified_at)
        self.assertEqual(self.client.get(url).status_code, 410)

    def test_expired_invitation_is_rejected(self):
        self.invitation.expires_at = timezone.now() - timedelta(seconds=1)
        self.invitation.save(update_fields=["expires_at"])
        self.assertEqual(
            self.client.get(reverse("accounts:accept_invitation", args=[self.invitation.token])).status_code,
            410,
        )

    @patch("notifications.tasks.send_mail")
    def test_invitation_email_is_idempotent(self, send_mail):
        self.assertEqual(send_invitation_email.run(self.invitation.pk), "sent")
        self.assertEqual(send_invitation_email.run(self.invitation.pk), "already-sent")
        self.assertEqual(EmailDelivery.objects.count(), 1)
        send_mail.assert_called_once()
