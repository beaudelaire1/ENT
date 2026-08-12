from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("formations", "0009_path_weight_metric")]

    operations = [
        migrations.AddField(
            model_name="learningpath",
            name="academic_year",
            field=models.CharField(
                blank=True,
                help_text="Exemple : 2026-2027. Laissez vide pour une formation sans année scolaire.",
                max_length=20,
                verbose_name="année universitaire",
            ),
        ),
        migrations.AddField(
            model_name="learningpath",
            name="current_period",
            field=models.ForeignKey(
                blank=True,
                help_text="Met cette période en avant dans la formation, le tableau de bord et les sélecteurs.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="current_for_paths",
                to="formations.period",
                verbose_name="période en cours",
            ),
        ),
    ]
