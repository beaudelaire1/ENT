from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailDelivery


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
    if delivery.sent_at:
        return "already-sent"
    send_mail(
        delivery.subject,
        f"Vous êtes invité à créer votre espace MyENT : {url}\n\nCe lien expire dans 7 jours.",
        settings.DEFAULT_FROM_EMAIL,
        [delivery.recipient],
        fail_silently=False,
    )
    delivery.sent_at = timezone.now()
    delivery.last_error = ""
    delivery.save(update_fields=["sent_at", "last_error"])
    return "sent"
