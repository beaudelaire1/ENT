from django.db import migrations, models

# Ancien quota par défaut. Les profils créés avant ce changement ont cette valeur figée
# en base : relever le réglage ne les concernerait pas, puisqu'il ne sert qu'à la
# création. Ceux qui l'ont encore sont donc remontés, et ceux dont le quota a été ajusté
# à la main sont laissés tels quels.
PREVIOUS_DEFAULT_MB = 1024
NEW_DEFAULT_MB = 10240


def raise_untouched_quotas(apps, schema_editor):
    apps.get_model("accounts", "UserProfile").objects.filter(audio_quota_mb=PREVIOUS_DEFAULT_MB).update(
        audio_quota_mb=NEW_DEFAULT_MB
    )


def lower_untouched_quotas(apps, schema_editor):
    apps.get_model("accounts", "UserProfile").objects.filter(audio_quota_mb=NEW_DEFAULT_MB).update(
        audio_quota_mb=PREVIOUS_DEFAULT_MB
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_invitation_options_alter_userprofile_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="audio_quota_mb",
            field=models.PositiveIntegerField(default=10240, verbose_name="quota audio (Mo)"),
        ),
        migrations.RunPython(raise_untouched_quotas, lower_untouched_quotas),
    ]
