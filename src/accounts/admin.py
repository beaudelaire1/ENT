from django.contrib import admin

from .models import Invitation, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "theme", "timezone", "audio_quota_mb")
    list_filter = ("theme",)
    search_fields = ("user__username", "display_name")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "invited_by", "created_at", "expires_at", "accepted_at")
    list_filter = ("invited_by",)
    search_fields = ("email",)
    date_hierarchy = "created_at"
