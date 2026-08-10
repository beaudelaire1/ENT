from django.contrib import admin
from .models import Progress


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'mastery_level', 'estimated_hours', 'actual_hours', 'updated_at')
    list_filter = ('mastery_level',)
    search_fields = ('course__title', 'user__username')
