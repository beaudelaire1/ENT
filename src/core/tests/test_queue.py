from unittest.mock import patch

from django.test import TestCase
from kombu.exceptions import OperationalError

from core.queue import broker_is_resting, enqueue, forget_broker_failure


@patch("notifications.tasks.send_mail")
class EnqueueFallbackTests(TestCase):
    """Une tâche doit partir même sans courtier, quitte à s'exécuter sur place."""

    def setUp(self):
        # La panne est retenue dans une variable de module : sans remise à zéro, un test
        # hériterait du courtier tombé chez le précédent.
        forget_broker_failure()
        self.addCleanup(forget_broker_failure)

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


@patch("notifications.tasks.send_mail")
class BrokerCooldownTests(TestCase):
    """Une panne constatée ne doit pas être repayée à chaque mise en file.

    Une tentative vers un courtier absent coûte son délai d'attente. La réindexation en
    produit une par enregistrement : sans mémoire de la panne, l'application entière
    s'arrête sur un Redis éteint.
    """

    def setUp(self):
        forget_broker_failure()
        self.addCleanup(forget_broker_failure)

    def test_the_broker_is_not_retried_after_a_failure(self, send_mail):
        from notifications.tasks import send_invitation_email

        with patch.object(send_invitation_email, "delay", side_effect=OperationalError("Redis absent")) as delay:
            with patch.object(send_invitation_email, "run", return_value="sent"):
                enqueue(send_invitation_email, 1)
                enqueue(send_invitation_email, 2)
                enqueue(send_invitation_email, 3)

        delay.assert_called_once_with(1)
        self.assertTrue(broker_is_resting())

    def test_the_tasks_still_run_while_the_broker_rests(self, send_mail):
        from notifications.tasks import send_invitation_email

        with patch.object(send_invitation_email, "delay", side_effect=OperationalError("Redis absent")):
            with patch.object(send_invitation_email, "run", return_value="sent") as run:
                enqueue(send_invitation_email, 1)
                enqueue(send_invitation_email, 2)

        self.assertEqual(run.call_count, 2)

    def test_a_success_clears_the_memory_of_the_failure(self, send_mail):
        from notifications.tasks import send_invitation_email

        with patch.object(send_invitation_email, "delay") as delay:
            enqueue(send_invitation_email, 1)

        delay.assert_called_once()
        self.assertFalse(broker_is_resting())
