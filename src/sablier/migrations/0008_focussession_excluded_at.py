from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0011_split_progress_time"),
        ("sablier", "0007_focuspreference_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="focussession",
            name="excluded_at",
            field=models.DateTimeField(blank=True, help_text="Une session exclue reste dans l'historique mais ne compte plus dans le temps de la compétence.", null=True, verbose_name="exclue du suivi le"),
        )
    ]
