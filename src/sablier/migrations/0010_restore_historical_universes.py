from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sablier", "0009_focuspreference_universes")]

    operations = [
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
                    ("printemps", "Printemps"),
                    ("ete", "Été"),
                    ("automne", "Automne"),
                    ("hiver", "Hiver"),
                    ("pluie", "Pluie"),
                    ("ocean", "Océan"),
                    ("sahara", "Sahara"),
                    ("foret", "Forêt"),
                    ("orage", "Orage"),
                    ("braises", "Braises"),
                    ("aurore", "Aurore"),
                    ("nuit", "Nuit"),
                ],
                default="arbre_etoiles",
                max_length=16,
                verbose_name="univers",
            ),
        ),
    ]
