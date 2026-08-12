"""Le rattachement d'une compétence à sa formation devient obligatoire.

La migration précédente l'a renseigné pour chaque ligne existante. Une vérification
précède l'ALTER : si une compétence était restée orpheline, la base refuserait la
contrainte avec un message illisible, et il vaut mieux dire exactement ce qui manque.
"""

import django.db.models.deletion
from django.db import migrations, models


def check_every_competency_has_a_path(apps, schema_editor):
    Competency = apps.get_model("formations", "Competency")
    orphans = list(Competency.objects.filter(path__isnull=True).values_list("pk", "title")[:20])
    if orphans:
        details = ", ".join(f"#{pk} « {title} »" for pk, title in orphans)
        raise RuntimeError(
            f"{Competency.objects.filter(path__isnull=True).count()} compétence(s) sans formation : {details}. "
            "Rattachez-les ou supprimez-les avant de rejouer cette migration."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0005_learninggroup_unitcompetency_and_more"),
    ]

    operations = [
        migrations.RunPython(check_every_competency_has_a_path, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="competency",
            name="path",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="competencies",
                to="formations.learningpath",
                verbose_name="formation",
            ),
        ),
    ]
