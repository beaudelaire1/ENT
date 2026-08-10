from django.contrib import admin
from .models import Course, Module, Resource


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'provider')
    list_filter = ('category', 'provider')
    search_fields = ('title', 'description')
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'resource_type', 'created_at')
    list_filter = ('course', 'resource_type')
    search_fields = ('title', 'description')
