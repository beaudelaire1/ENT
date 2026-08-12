"""Bornes de saisie sur les colonnes de suivi, et durées obligatoirement positives.

Les contraintes SQL ne peuvent être posées que sur des données qui les respectent déjà :
``control_existing_hours`` ramène à zéro les durées négatives que rien n'empêchait
d'enregistrer jusqu'ici, en disant combien de lignes ont été touchées. L'opération n'est
pas réversible — la valeur d'origine n'a pas de sens à restaurer.
"""

import logging

import django.core.validators
from django.conf import settings
from django.db import migrations, models

logger = logging.getLogger(__name__)


def control_existing_hours(apps, schema_editor):
    ProgressRecord = apps.get_model("formations", "ProgressRecord")
    for field in ("planned_hours", "actual_hours"):
        repaired = ProgressRecord.objects.filter(**{f"{field}__lt": 0}).update(**{field: 0})
        if repaired:
            logger.warning("Progression : %s valeur(s) négative(s) de %s ramenée(s) à zéro.", repaired, field)


class Migration(migrations.Migration):

    dependencies = [
        ('formations', '0003_alter_competency_options_alter_learningpath_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='metricdefinition',
            name='decimal_places',
            field=models.PositiveSmallIntegerField(default=2, help_text="0 pour n'accepter que des entiers (ECTS, coefficient).", validators=[django.core.validators.MaxValueValidator(2)], verbose_name='décimales'),
        ),
        migrations.AddField(
            model_name='metricdefinition',
            name='max_value',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Laisser vide pour ne poser aucune limite haute.', max_digits=10, null=True, verbose_name='valeur maximale'),
        ),
        migrations.AddField(
            model_name='metricdefinition',
            name='min_value',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Laisser vide pour ne poser aucune limite basse.', max_digits=10, null=True, verbose_name='valeur minimale'),
        ),
        migrations.AlterField(
            model_name='progressrecord',
            name='actual_hours',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7, validators=[django.core.validators.MinValueValidator(0)], verbose_name='temps réel (h)'),
        ),
        migrations.AlterField(
            model_name='progressrecord',
            name='planned_hours',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7, validators=[django.core.validators.MinValueValidator(0)], verbose_name='travail personnel estimé (h)'),
        ),
        migrations.AddConstraint(
            model_name='metricdefinition',
            constraint=models.CheckConstraint(condition=models.Q(('min_value__isnull', True), ('max_value__isnull', True), ('min_value__lte', models.F('max_value')), _connector='OR'), name='metric_bounds_ordered'),
        ),
        migrations.AddConstraint(
            model_name='metricdefinition',
            constraint=models.CheckConstraint(condition=models.Q(('decimal_places__lte', 2)), name='metric_decimal_places_storable'),
        ),
        migrations.RunPython(control_existing_hours, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='progressrecord',
            constraint=models.CheckConstraint(condition=models.Q(('planned_hours__gte', 0)), name='progress_planned_hours_positive'),
        ),
        migrations.AddConstraint(
            model_name='progressrecord',
            constraint=models.CheckConstraint(condition=models.Q(('actual_hours__gte', 0)), name='progress_actual_hours_positive'),
        ),
    ]
