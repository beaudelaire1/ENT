"""Le seul chemin par lequel une notification arrive à quelqu'un.

Tout producteur passe par `notify`. C'est ce qui garantit qu'une notification est
toujours déclarée au catalogue, toujours réglable, toujours dédupliquée — et que
l'email ne suit que ce qui a une heure.

La déduplication n'est pas un détail : les producteurs périodiques repassent sur les
mêmes objets à chaque exécution. Sans clé stable, une échéance dépassée depuis trois
jours produirait une notification par minute.
"""

from __future__ import annotations

from .catalog import event as declared_event
from .models import Notification, NotificationPreference


def notify(
    owner, event_key: str, *, dedupe_key: str, title: str, message: str = "", url: str = ""
) -> Notification | None:
    """Informe `owner`, si la famille de cet événement est acceptée.

    Renvoie la notification créée, ou `None` si elle existait déjà ou si l'utilisateur a
    éteint la famille. L'appelant n'a rien à vérifier : c'est ici que la règle vit.
    """
    event = declared_event(event_key)
    preference = NotificationPreference.objects.filter(owner=owner, family=event.family).first()
    if preference is not None and not preference.enabled:
        return None

    notification, created = Notification.objects.get_or_create(
        owner=owner,
        dedupe_key=dedupe_key,
        defaults={
            "title": title,
            "message": message,
            "url": url,
            "kind": Notification.Kind.REMINDER if event.urgent else Notification.Kind.SYSTEM,
        },
    )
    if not created:
        return None

    if event.urgent and (preference is None or preference.email):
        _queue_email(owner, dedupe_key=dedupe_key, subject=title, body=message or title)
    return notification


def _queue_email(owner, *, dedupe_key: str, subject: str, body: str) -> None:
    """Confie l'email à la file, sans jamais faire échouer la notification.

    La notification dans l'application est déjà créée quand on arrive ici : la perdre
    parce qu'un serveur SMTP est injoignable, ce serait perdre l'information elle-même
    pour en sauver la copie.
    """
    if not getattr(owner, "email", ""):
        return
    from core.queue import enqueue

    from .tasks import send_event_email

    enqueue(send_event_email, owner.pk, dedupe_key, subject, body)
