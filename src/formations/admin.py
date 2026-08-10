from django.contrib import admin

from .models import Competency, LearningPath, LearningUnit, MetricDefinition, MetricValue, Period, ProgressRecord

for model in [LearningPath, Period, LearningUnit, Competency, MetricDefinition, MetricValue, ProgressRecord]:
    admin.site.register(model)
