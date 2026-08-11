from django.contrib import admin

from .models import CalendarEvent, Reminder, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "priority", "due_at")
    list_filter = ("status", "priority", "owner")
    search_fields = ("title", "description")
    date_hierarchy = "due_at"


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "starts_at", "ends_at", "location", "series")
    list_filter = ("owner", "all_day")
    search_fields = ("title", "description", "location")
    date_hierarchy = "starts_at"


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "owner", "status", "scheduled_for", "attempts", "sent_at")
    list_filter = ("status", "owner")
    date_hierarchy = "scheduled_for"
