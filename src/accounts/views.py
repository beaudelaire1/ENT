from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import InvitationAcceptForm, InvitationForm, ProfileForm
from .models import Invitation, UserProfile


@login_required
def settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Préférences enregistrées.")
        return redirect("accounts:settings")
    return render(request, "accounts/settings.html", {"form": form})


@staff_member_required
def invitations(request):
    form = InvitationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        invitation = form.save(commit=False)
        invitation.invited_by = request.user
        invitation.expires_at = timezone.now() + timedelta(days=7)
        invitation.save()
        from notifications.tasks import send_invitation_email

        send_invitation_email.delay(invitation.pk)
        messages.success(request, "Invitation créée et mise en file d’envoi.")
        return redirect("accounts:invitations")
    return render(
        request,
        "accounts/invitations.html",
        {"form": form, "invitations": Invitation.objects.select_related("invited_by")[:100]},
    )


def accept_invitation(request, token):
    invitation = get_object_or_404(Invitation, token=token)
    if not invitation.is_valid:
        return render(request, "accounts/invitation_invalid.html", status=410)
    form = InvitationAcceptForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
            if not invitation.is_valid:
                return render(request, "accounts/invitation_invalid.html", status=410)
            user = get_user_model().objects.create_user(
                username=form.cleaned_data["username"],
                email=invitation.email,
                password=form.cleaned_data["password1"],
            )
            UserProfile.objects.create(
                user=user,
                display_name=form.cleaned_data["display_name"],
                email_verified_at=timezone.now(),
            )
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["accepted_at"])
        login(request, user)
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, "accounts/accept_invitation.html", {"form": form, "invitation": invitation})
