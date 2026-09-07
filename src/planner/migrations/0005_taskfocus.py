import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0004_taskseries_academic_links"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskFocus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "scope",
                    models.CharField(
                        choices=[("day", "Aujourd’hui"), ("week", "Cette semaine"), ("month", "Ce mois")],
                        max_length=8,
                        verbose_name="horizon",
                    ),
                ),
                ("period_start", models.DateField(db_index=True, verbose_name="début de période")),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_focuses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="focus_selections",
                        to="planner.task",
                    ),
                ),
            ],
            options={
                "verbose_name": "priorité temporelle",
                "verbose_name_plural": "priorités temporelles",
                "ordering": ["-period_start", "scope"],
            },
        ),
        migrations.AddConstraint(
            model_name="taskfocus",
            constraint=models.UniqueConstraint(
                fields=("owner", "scope", "period_start"),
                name="task_focus_one_per_owner_scope_period",
            ),
        ),
    ]
