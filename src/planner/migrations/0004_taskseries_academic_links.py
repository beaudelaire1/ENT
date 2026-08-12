import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0010_learningpath_academic_year_current_period"),
        ("planner", "0003_calendarevent_series"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskSeries",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("recurrence", models.CharField(choices=[("none", "Ne se répète pas"), ("daily", "Chaque jour"), ("weekdays", "Du lundi au vendredi"), ("weekly", "Chaque semaine"), ("biweekly", "Une semaine sur deux"), ("monthly", "Chaque mois")], max_length=12, verbose_name="répétition")),
                ("repeat_until", models.DateField(verbose_name="jusqu’au")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="task_series", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "série de tâches", "verbose_name_plural": "séries de tâches", "ordering": ["-created_at"]},
        ),
        migrations.AddField(model_name="task", name="series_position", field=models.PositiveSmallIntegerField(default=0, verbose_name="position dans la série")),
        migrations.AddField(model_name="task", name="series", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="planner.taskseries", verbose_name="série")),
        migrations.AddField(model_name="task", name="unit", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tasks", to="formations.learningunit", verbose_name="matière")),
        migrations.AddField(model_name="task", name="competency", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tasks", to="formations.competency", verbose_name="compétence")),
        migrations.AddField(model_name="task", name="assessment", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tasks", to="formations.assessment", verbose_name="évaluation")),
        migrations.AddField(model_name="calendarevent", name="unit", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="calendar_events", to="formations.learningunit", verbose_name="matière")),
        migrations.AddField(model_name="calendarevent", name="competency", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="calendar_events", to="formations.competency", verbose_name="compétence")),
        migrations.AddField(model_name="calendarevent", name="assessment", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="calendar_events", to="formations.assessment", verbose_name="évaluation")),
    ]
