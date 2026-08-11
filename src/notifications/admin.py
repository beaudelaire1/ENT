from django.contrib import admin

from .models import EmailDelivery, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "kind", "created_at", "read_at")
    list_filter = ("kind", "owner")
    search_fields = ("title", "message")
    date_hierarchy = "created_at"


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ("subject", "recipient", "owner", "sent_at")
    list_filter = ("owner",)
    search_fields = ("subject", "recipient", "last_error")
    date_hierarchy = "created_at"
