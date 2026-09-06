"""Ramène le catalogue à neuf univers réellement distincts.

Quinze des vingt-quatre univers partageaient leur construction avec un autre et ne
s'en distinguaient que par la teinte du ciel. Ils sont retirés, et les préférences
déjà enregistrées sont réécrites vers le lieu dont chacun était la variante colorée :
sans cela une préférence pointerait vers un univers que le catalogue ne connaît plus.
"""

from django.db import migrations, models

REDIRECTIONS = {
    "nuit": "arbre_etoiles",
    "eden": "foret",
    "printemps": "foret",
    "ete": "foret",
    "automne": "foret",
    "hiver": "aurores",
    "heaven": "aurores",
    "aurore": "aurores",
    "orage": "ocean",
    "pluie": "refuge_pluie",
    "braises": "refuge_pluie",
    "souvenirs": "refuge_pluie",
    "oasis": "sahara",
    "interstellaire": "galaxie",
    "fontaine": "fleuve_temps",
}


def redirect_retired_universes(apps, schema_editor):
    FocusPreference = apps.get_model("sablier", "FocusPreference")
    for retired, replacement in REDIRECTIONS.items():
        FocusPreference.objects.filter(ambience=retired).update(ambience=replacement)


def noop(apps, schema_editor):
    """Les univers retirés ne peuvent pas être rétablis : leur décor n'existe plus."""


class Migration(migrations.Migration):
    dependencies = [("sablier", "0010_restore_historical_universes")]

    operations = [
        migrations.RunPython(redirect_retired_universes, noop),
        migrations.AlterField(
            model_name="focuspreference",
            name="ambience",
            field=models.CharField(
                choices=[
                    ("arbre_etoiles", "Arbre des étoiles"),
                    ("refuge_pluie", "Refuge sous la pluie"),
                    ("foret", "Futaie ancienne"),
                    ("ocean", "Falaise océane"),
                    ("sahara", "Sahara"),
                    ("aurores", "Vallée des aurores"),
                    ("galaxie", "Pont des galaxies"),
                    ("fleuve_temps", "Fleuve du Temps"),
                    ("abysses", "Sanctuaire abyssal"),
                ],
                default="arbre_etoiles",
                max_length=16,
                verbose_name="univers",
            ),
        ),
    ]
