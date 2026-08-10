from django.contrib import admin

from .models import Invitation, UserProfile

admin.site.register(UserProfile)
admin.site.register(Invitation)
