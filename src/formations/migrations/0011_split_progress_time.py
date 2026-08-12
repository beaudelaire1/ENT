from decimal import Decimal

from django.db import migrations, models
import django.core.validators


def split_existing_time(apps, schema_editor):
    ProgressRecord = apps.get_model("formations", "ProgressRecord")
    FocusSession = apps.get_model("sablier", "FocusSession")
    totals = {}
    for session in FocusSession.objects.filter(counted_at__isnull=False, competency__isnull=False):
        key = (session.owner_id, session.competency_id)
        hours = (Decimal(session.seconds) / Decimal(3600)).quantize(Decimal("0.01"))
        totals[key] = totals.get(key, Decimal(0)) + hours
    for record in ProgressRecord.objects.all():
        session_hours = min(record.actual_hours, totals.get((record.owner_id, record.competency_id), Decimal(0)))
        record.session_hours = session_hours
        record.manual_hours = max(Decimal(0), record.actual_hours - session_hours)
        record.save(update_fields=["session_hours", "manual_hours"])


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0010_learningpath_academic_year_current_period"),
        ("sablier", "0007_focuspreference_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="progressrecord",
            name="manual_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7, validators=[django.core.validators.MinValueValidator(0)], verbose_name="temps saisi manuellement (h)"),
        ),
        migrations.AddField(
            model_name="progressrecord",
            name="session_hours",
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=7, validators=[django.core.validators.MinValueValidator(0)], verbose_name="temps des sessions Sablier (h)"),
        ),
        migrations.AlterField(
            model_name="progressrecord",
            name="actual_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7, validators=[django.core.validators.MinValueValidator(0)], verbose_name="temps total (h)"),
        ),
        migrations.RunPython(split_existing_time, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="progressrecord", constraint=models.CheckConstraint(condition=models.Q(("manual_hours__gte", 0)), name="progress_manual_hours_positive")),
        migrations.AddConstraint(model_name="progressrecord", constraint=models.CheckConstraint(condition=models.Q(("session_hours__gte", 0)), name="progress_session_hours_positive")),
    ]
