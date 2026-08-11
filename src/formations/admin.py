from django.contrib import admin

from .models import Competency, LearningPath, LearningUnit, MetricDefinition, MetricValue, Period, ProgressRecord


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "level_label", "status")
    list_filter = ("status",)
    search_fields = ("title", "training_type", "level_label")


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ("title", "path", "order")
    list_filter = ("path",)
    search_fields = ("title",)


@admin.register(LearningUnit)
class LearningUnitAdmin(admin.ModelAdmin):
    list_display = ("title", "period", "order")
    list_filter = ("period__path",)
    search_fields = ("title",)


@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ("title", "unit", "order")
    list_filter = ("unit__period__path",)
    search_fields = ("title",)


@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "unit_label", "path", "order")
    list_filter = ("path",)
    search_fields = ("label", "key")


@admin.register(MetricValue)
class MetricValueAdmin(admin.ModelAdmin):
    list_display = ("definition", "unit", "value")
    list_filter = ("definition__path",)


@admin.register(ProgressRecord)
class ProgressRecordAdmin(admin.ModelAdmin):
    list_display = ("competency", "owner", "mastery_level", "planned_hours", "actual_hours")
    list_filter = ("mastery_level", "owner")
    search_fields = ("competency__title", "notes")
