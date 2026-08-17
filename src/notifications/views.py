from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .catalog import EVENTS, FAMILIES
from .models import Notification, NotificationPreference


@login_required
def notification_list(request):
    return render(
        request, "notifications/list.html", {"notifications": Notification.objects.filter(owner=request.user)[:100]}
    )


@login_required
@require_POST
def mark_read(request, pk):
    notification = get_object_or_404(Notification, owner=request.user, pk=pk)
    notification.read_at = timezone.now()
    notification.save(update_fields=["read_at"])
    return redirect(notification.url or "notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(owner=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return redirect("notifications:list")


@login_required
def preferences(request):
    """Ce que vous acceptez de recevoir, famille par famille.

    Les cases sont construites à partir du catalogue, jamais listées à la main : une
    famille ajoutée au code apparaît ici sans qu'on y pense, et une famille retirée
    disparaît sans laisser un réglage sans effet.
    """
    existing = {
        preference.family: preference for preference in NotificationPreference.objects.filter(owner=request.user)
    }

    if request.method == "POST":
        for family in FAMILIES:
            NotificationPreference.objects.update_or_create(
                owner=request.user,
                family=family.key,
                defaults={
                    "enabled": f"{family.key}:enabled" in request.POST,
                    "email": f"{family.key}:email" in request.POST,
                },
            )
        messages.success(request, "Préférences de notification enregistrées.")
        return redirect("notifications:preferences")

    rows = []
    for family in FAMILIES:
        preference = existing.get(family.key)
        rows.append(
            {
                "family": family,
                # Sans ligne enregistrée, tout est accepté : on est informé de tout tant
                # qu'on n'a rien éteint.
                "enabled": preference.enabled if preference else True,
                "email": preference.email if preference else True,
                "events": [event for event in EVENTS if event.family == family.key],
                # Une famille sans événement urgent ne peut rien envoyer par email :
                # afficher la case laisserait croire à un réglage sans effet.
                "has_urgent": any(event.urgent for event in EVENTS if event.family == family.key),
            }
        )
    return render(request, "notifications/preferences.html", {"rows": rows})
