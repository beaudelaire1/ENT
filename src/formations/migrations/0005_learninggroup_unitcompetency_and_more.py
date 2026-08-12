"""Regroupements facultatifs, et compétences détachées d'une matière unique.

Une compétence était rattachée à exactement une matière. Ce qui est courant devenait
impossible : « Rédiger une démonstration au tableau » se travaille aux deux semestres,
et le modèle en faisait deux compétences distinctes, avec deux suivis parallèles et
aucun moyen de savoir qu'il s'agissait de la même chose.

L'ordre des opérations importe. La reprise des données a besoin de l'ancienne clé
étrangère : elle est donc supprimée en dernier, et la contrainte d'unicité par parcours
n'est posée qu'après la fusion des doublons — sinon la migration échouerait sur la
première formation qui déclare le même intitulé dans deux matières, c'est-à-dire
précisément le cas qui motive ce changement.

La fusion additionne les durées et retient le niveau le plus élevé. C'est un choix, pas
une évidence : deux suivis d'un même savoir-faire n'en font qu'un, et rien ne permet de
deviner lequel des deux niveaux l'étudiant considérerait comme vrai. Retenir le plus
élevé ne perd pas de travail ; retenir le plus faible en aurait effacé.
"""

import logging

import django.db.models.deletion
from django.db import migrations, models

logger = logging.getLogger(__name__)


def attach_to_path(apps, schema_editor):
    """Rattache chaque compétence à son parcours et crée son lien de matière."""
    Competency = apps.get_model("formations", "Competency")
    UnitCompetency = apps.get_model("formations", "UnitCompetency")

    links = []
    for competency in Competency.objects.select_related("unit__period").all():
        competency.path_id = competency.unit.period.path_id
        competency.period_id = competency.unit.period_id
        competency.save(update_fields=["path", "period"])
        links.append(
            UnitCompetency(
                unit_id=competency.unit_id,
                competency_id=competency.pk,
                order=competency.order,
                is_primary=True,
            )
        )
    if links:
        UnitCompetency.objects.bulk_create(links)
        logger.info("Compétences : %s lien(s) matière créé(s).", len(links))


def merge_duplicates(apps, schema_editor):
    """Fusionne les compétences de même intitulé dans un même parcours.

    C'est ici que la transversalité prend effet : les deux « Rédiger une démonstration au
    tableau » du semestre 5 et du semestre 6 deviennent une compétence unique, liée aux
    deux matières.
    """
    Competency = apps.get_model("formations", "Competency")
    UnitCompetency = apps.get_model("formations", "UnitCompetency")
    ProgressRecord = apps.get_model("formations", "ProgressRecord")
    FocusSession = apps.get_model("sablier", "FocusSession")

    groups: dict[tuple[int, str], list[int]] = {}
    for pk, path_id, title in Competency.objects.values_list("pk", "path_id", "title").order_by("pk"):
        groups.setdefault((path_id, title), []).append(pk)

    merged = 0
    for (_path_id, title), pks in groups.items():
        if len(pks) < 2:
            continue
        keeper, duplicates = pks[0], pks[1:]

        # Les liens de matière des doublons passent au gardien : c'est ce qui rend la
        # compétence transversale plutôt que dupliquée.
        for link in UnitCompetency.objects.filter(competency_id__in=duplicates):
            if UnitCompetency.objects.filter(unit_id=link.unit_id, competency_id=keeper).exists():
                link.delete()
            else:
                link.competency_id = keeper
                link.save(update_fields=["competency"])

        for owner_id in set(
            ProgressRecord.objects.filter(competency_id__in=[keeper, *duplicates]).values_list("owner_id", flat=True)
        ):
            records = list(
                ProgressRecord.objects.filter(owner_id=owner_id, competency_id__in=[keeper, *duplicates]).order_by(
                    "competency_id"
                )
            )
            target = next((r for r in records if r.competency_id == keeper), None)
            others = [r for r in records if r.pk != (target.pk if target else None)]
            if target is None:
                target = others.pop(0)
                target.competency_id = keeper
            for other in others:
                target.mastery_level = max(target.mastery_level, other.mastery_level)
                target.planned_hours += other.planned_hours
                target.actual_hours += other.actual_hours
                notes = [part for part in (target.notes.strip(), other.notes.strip()) if part]
                target.notes = "\n".join(dict.fromkeys(notes))
            target.save()
            ProgressRecord.objects.filter(pk__in=[other.pk for other in others]).delete()

        # Ressources et sessions suivent la compétence conservée.
        keeper_object = Competency.objects.get(pk=keeper)
        for duplicate in Competency.objects.filter(pk__in=duplicates).prefetch_related("resources"):
            keeper_object.resources.add(*duplicate.resources.all())
        FocusSession.objects.filter(competency_id__in=duplicates).update(competency_id=keeper)

        Competency.objects.filter(pk__in=duplicates).delete()
        merged += len(duplicates)
        logger.info("Compétence « %s » : %s doublon(s) fusionné(s).", title, len(duplicates))

    if merged:
        logger.warning("Compétences : %s doublon(s) fusionné(s) au total.", merged)


def unmerge_impossible(apps, schema_editor):
    """La fusion n'est pas réversible : une compétence unifiée ne se rescinde pas."""
    raise migrations.exceptions.IrreversibleError(
        "La fusion des compétences homonymes ne peut pas être défaite : restaurez une sauvegarde."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0004_metricdefinition_decimal_places_and_more"),
        ("library", "0004_libraryitem_purpose"),
        # La reprise déplace les sessions de concentration des doublons.
        ("sablier", "0003_focussession"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=180, verbose_name="intitulé")),
                (
                    "code",
                    models.CharField(
                        blank=True,
                        help_text="Référence de la maquette, si elle en a une.",
                        max_length=40,
                        verbose_name="code",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        blank=True,
                        help_text="UE, bloc, domaine… Laissez vide si inutile.",
                        max_length=40,
                        verbose_name="type",
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ordre")),
            ],
            options={
                "verbose_name": "regroupement",
                "verbose_name_plural": "regroupements",
                "ordering": ["order", "title"],
            },
        ),
        migrations.CreateModel(
            name="UnitCompetency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ordre dans la matière")),
                (
                    "is_primary",
                    models.BooleanField(
                        default=True,
                        help_text="Une compétence secondaire est rappelée sans être saisie ici.",
                        verbose_name="principale dans cette matière",
                    ),
                ),
                (
                    "local_objective",
                    models.CharField(
                        blank=True,
                        help_text="Ce qui est attendu dans cette matière en particulier, s'il y a une nuance.",
                        max_length=240,
                        verbose_name="objectif local",
                    ),
                ),
            ],
            options={
                "verbose_name": "compétence de matière",
                "verbose_name_plural": "compétences de matière",
                "ordering": ["order", "competency__title"],
            },
        ),
        migrations.AddField(
            model_name="learninggroup",
            name="period",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="groups",
                to="formations.period",
                verbose_name="période",
            ),
        ),
        migrations.AddField(
            model_name="learningunit",
            name="group",
            field=models.ForeignKey(
                blank=True,
                help_text="Facultatif : une formation sans UE laisse ce champ vide.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="units",
                to="formations.learninggroup",
                verbose_name="regroupement",
            ),
        ),
        migrations.AddField(
            model_name="unitcompetency",
            name="competency",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="unit_links",
                to="formations.competency",
                verbose_name="compétence",
            ),
        ),
        migrations.AddField(
            model_name="unitcompetency",
            name="unit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="competency_links",
                to="formations.learningunit",
                verbose_name="matière",
            ),
        ),
        migrations.AddField(
            model_name="competency",
            name="path",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="competencies",
                to="formations.learningpath",
                verbose_name="formation",
            ),
        ),
        migrations.AddField(
            model_name="competency",
            name="period",
            field=models.ForeignKey(
                blank=True,
                help_text="Facultatif : une compétence peut traverser plusieurs périodes.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="competencies",
                to="formations.period",
                verbose_name="période",
            ),
        ),
        # 1. Reprise des données, tant que `unit` existe encore.
        migrations.RunPython(attach_to_path, migrations.RunPython.noop),
        # 2. Fusion des homonymes, avant toute contrainte d'unicité par parcours.
        migrations.RunPython(merge_duplicates, unmerge_impossible),
        # 3. L'ancienne clé étrangère et sa contrainte peuvent partir.
        migrations.RemoveConstraint(model_name="competency", name="unique_competency_per_unit"),
        migrations.RemoveField(model_name="competency", name="unit"),
        migrations.AddField(
            model_name="competency",
            name="units",
            field=models.ManyToManyField(
                blank=True,
                related_name="competencies",
                through="formations.UnitCompetency",
                to="formations.learningunit",
                verbose_name="matières",
            ),
        ),
        migrations.AddConstraint(
            model_name="competency",
            constraint=models.UniqueConstraint(fields=("path", "title"), name="unique_competency_per_path"),
        ),
        migrations.AddConstraint(
            model_name="learninggroup",
            constraint=models.UniqueConstraint(fields=("period", "title"), name="unique_group_per_period"),
        ),
        migrations.AddConstraint(
            model_name="unitcompetency",
            constraint=models.UniqueConstraint(fields=("unit", "competency"), name="unique_competency_per_unit_link"),
        ),
    ]
