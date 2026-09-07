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

    @patch("notifications.tasks.send_mail", side_effect=RuntimeError("smtp indisponible"))
    def test_invitation_email_failure_is_kept_for_diagnostics(self, _send_mail):
        with self.assertRaises(RuntimeError):
            send_invitation_email.run(self.invitation.pk)
        delivery = EmailDelivery.objects.get(dedupe_key=f"invitation:{self.invitation.pk}")
        self.assertIsNone(delivery.sent_at)
        self.assertIn("smtp indisponible", delivery.last_error)

    def test_admin_page_separates_delivery_and_acceptance_states(self):
        self.client.force_login(self.staff)
        delivery = EmailDelivery.objects.create(
            owner=self.staff,
            dedupe_key=f"invitation:{self.invitation.pk}",
            recipient=self.invitation.email,
            subject="Invitation à rejoindre MyENT",
            sent_at=timezone.now(),
        )
        response = self.client.get(reverse("accounts:invitations"))
        self.assertContains(response, "Invitation : en attente d’acceptation")
        self.assertContains(response, "Email : envoyé le")

        self.invitation.accepted_at = timezone.now()
        self.invitation.save(update_fields=["accepted_at"])
        response = self.client.get(reverse("accounts:invitations"))
        self.assertContains(response, "Invitation : acceptée")
        self.assertContains(response, "Email : envoyé le")
        self.assertEqual(delivery.recipient, "invitee@example.com")
