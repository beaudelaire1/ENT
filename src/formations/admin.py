from django.contrib import admin

from .models import (
    Competency,
    LearningGroup,
    LearningPath,
    LearningUnit,
    MetricDefinition,
    MetricValue,
    Period,
    ProgressRecord,
    UnitCompetency,
)


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


@admin.register(LearningGroup)
class LearningGroupAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "kind", "period", "order")
    list_filter = ("period__path", "kind")
    search_fields = ("title", "code")


@admin.register(LearningUnit)
class LearningUnitAdmin(admin.ModelAdmin):
    list_display = ("title", "period", "group", "order")
    list_filter = ("period__path",)
    search_fields = ("title",)


class UnitCompetencyInline(admin.TabularInline):
    model = UnitCompetency
    extra = 0
    autocomplete_fields = ("unit",)


@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ("title", "path", "period", "order")
    list_filter = ("path",)
    search_fields = ("title",)
    inlines = (UnitCompetencyInline,)


@admin.register(UnitCompetency)
class UnitCompetencyAdmin(admin.ModelAdmin):
    list_display = ("competency", "unit", "is_primary", "order")
    list_filter = ("is_primary", "unit__period__path")
    search_fields = ("competency__title", "unit__title")


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
