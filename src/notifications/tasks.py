from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailDelivery


def _send_delivery(delivery: EmailDelivery, body: str) -> str:
    """Envoie un email suivi en base et conserve la dernière erreur exploitable.

    Le statut de livraison est affiché dans l'administration des invitations et sert
    aussi au diagnostic des notifications. Une exception ne doit donc pas disparaître
    uniquement dans les journaux Celery : elle est enregistrée avant d'être relancée,
    afin que l'autoretry continue de fonctionner normalement.
    """
    if delivery.sent_at:
        return "already-sent"
    try:
        send_mail(delivery.subject, body, settings.DEFAULT_FROM_EMAIL, [delivery.recipient], fail_silently=False)
    except Exception as exc:
        delivery.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        delivery.save(update_fields=["last_error"])
        raise
    delivery.sent_at = timezone.now()
    delivery.last_error = ""
    delivery.save(update_fields=["sent_at", "last_error"])
    return "sent"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 4})
def send_event_email(self, owner_id: int, dedupe_key: str, subject: str, body: str):
    """Double par email une notification déjà créée dans l'application.

    La même clé de déduplication que la notification : un producteur périodique qui
    repasse sur le même objet ne peut pas réexpédier ce qui est déjà parti.
    """
    owner = get_user_model().objects.filter(pk=owner_id).first()
    if owner is None or not owner.email:
        return "no-recipient"
    delivery, _ = EmailDelivery.objects.get_or_create(
        owner=owner,
        dedupe_key=dedupe_key,
        defaults={"recipient": owner.email, "subject": subject[:180]},
    )
    return _send_delivery(delivery, body)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 4})
def send_invitation_email(self, invitation_id: int):
    from accounts.models import Invitation

    invitation = Invitation.objects.get(pk=invitation_id)
    if not invitation.is_valid:
        return "expired"
    url = f"{settings.SITE_URL}/accounts/invite/{invitation.token}/"
    delivery, _ = EmailDelivery.objects.get_or_create(
        owner=invitation.invited_by,
        dedupe_key=f"invitation:{invitation.pk}",
        defaults={
            "recipient": invitation.email,
            "subject": "Invitation à rejoindre MyENT",
        },
    )
    return _send_delivery(
        delivery,
        f"Vous êtes invité à créer votre espace MyENT : {url}\n\nCe lien expire dans 7 jours.",
    )


@shared_task(name="notifications.scan_for_events")
def scan_for_events():
    """Le regard périodique sur ce qui devient vrai en passant.

    Une fois par heure suffit : les faits guettés se comptent en heures — une échéance
    du lendemain, une évaluation de la semaine — et la déduplication rend une exécution
    de plus sans effet. Les rappels que l'utilisateur a posés lui-même gardent leur
    passage à la minute, dans `planner`.
    """
    from .scanning import scan_all

    return scan_all()
