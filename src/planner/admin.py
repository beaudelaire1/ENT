from django.contrib import admin

from .models import CalendarEvent, Reminder, Task

admin.site.register(Task)
admin.site.register(CalendarEvent)
admin.site.register(Reminder)
