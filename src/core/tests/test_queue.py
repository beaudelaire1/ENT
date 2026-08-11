from unittest.mock import patch

from django.test import TestCase
from kombu.exceptions import OperationalError

from core.queue import enqueue


@patch("notifications.tasks.send_mail")
class EnqueueFallbackTests(TestCase):
    """Une tâche doit partir même sans courtier, quitte à s'exécuter sur place."""

    def test_a_reachable_broker_is_used(self, send_mail):
        from notifications.tasks import send_invitation_email

        with patch.object(send_invitation_email, "delay") as delay:
            enqueue(send_invitation_email, 1)

        delay.assert_called_once_with(1)
        send_mail.assert_not_called()

    def test_an_unreachable_broker_falls_back_to_running_inline(self, send_mail):
        from notifications.tasks import send_invitation_email

        with patch.object(send_invitation_email, "delay", side_effect=OperationalError("Redis absent")):
            with patch.object(send_invitation_email, "run", return_value="sent") as run:
                result = enqueue(send_invitation_email, 7)

        run.assert_called_once_with(7)
        self.assertEqual(result, "sent")
