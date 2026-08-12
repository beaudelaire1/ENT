from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0002_alter_dashboardwidget_options_and_more")]

    operations = [
        migrations.AlterField(
            model_name="dashboardwidget",
            name="kind",
            field=models.CharField(
                choices=[
                    ("today", "Aujourd’hui"),
                    ("tasks", "Tâches prioritaires"),
                    ("reminders", "Rappels"),
                    ("recent", "Contenus récents"),
                    ("formations", "Formations"),
                    ("academic", "Situation académique"),
                    ("quick_note", "Note rapide"),
                    ("sablier", "Sablier"),
                ],
                max_length=24,
                verbose_name="bloc",
            ),
        )
    ]
