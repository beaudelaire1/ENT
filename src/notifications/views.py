from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


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
