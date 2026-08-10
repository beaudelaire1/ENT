from django.contrib import admin

from .models import EmailDelivery, Notification

admin.site.register(Notification)
admin.site.register(EmailDelivery)
