from django.db import migrations, models


LEGACY = {
    "concentration": "arbre_etoiles",
    "printemps": "eden",
    "ete": "oasis",
    "automne": "fleuve_temps",
    "hiver": "aurores",
    "pluie": "refuge_pluie",
    "ocean": "abysses",
    "sahara": "oasis",
    "foret": "eden",
    "orage": "interstellaire",
    "braises": "souvenirs",
    "aurore": "heaven",
    "nuit": "galaxie",
}


def migrate_ambiences(apps, schema_editor):
    preference = apps.get_model("sablier", "FocusPreference")
    for item in preference.objects.all().iterator():
        replacement = LEGACY.get(item.ambience)
        if replacement:
            item.ambience = replacement
            item.save(update_fields=["ambience"])


class Migration(migrations.Migration):
    dependencies = [("sablier", "0008_focussession_excluded_at")]

    operations = [
        migrations.RunPython(migrate_ambiences, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="focuspreference",
            name="ambience",
            field=models.CharField(
                choices=[
                    ("arbre_etoiles", "Arbre des étoiles"),
                    ("fontaine", "Fontaine de l’Éternité"),
                    ("eden", "Éden"),
                    ("fleuve_temps", "Fleuve du Temps"),
                    ("souvenirs", "Souvenirs"),
                    ("interstellaire", "Interstellaire"),
                    ("galaxie", "Galaxie"),
                    ("heaven", "Heaven — Hauts Cieux"),
                    ("oasis", "Oasis des confins"),
                    ("abysses", "Sanctuaire abyssal"),
                    ("refuge_pluie", "Refuge sous la pluie"),
                    ("aurores", "Vallée des aurores"),
                ],
                default="arbre_etoiles",
                max_length=16,
                verbose_name="univers",
            ),
        ),
        migrations.AlterField(
            model_name="focuspreference",
            name="custom_accent",
            field=models.BooleanField(default=False, verbose_name="utiliser ma couleur pour la visualisation"),
        ),
        migrations.AlterField(
            model_name="focuspreference",
            name="decor_density",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Statique"), (1, "Léger"), (2, "Immersif"), (3, "Cinématique")],
                default=2,
                verbose_name="niveau d’immersion",
            ),
        ),
    ]
