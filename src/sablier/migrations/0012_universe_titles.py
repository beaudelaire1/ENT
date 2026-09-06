"""Rend aux univers des titres de paysage plutôt que des descriptions.

« Futaie ancienne » dit exactement ce que l'on voit, et c'est bien le problème : le
catalogue est une invitation au voyage, pas une légende de planche botanique. Les
titres reprennent le registre évocateur d'origine. Seuls les libellés changent — les
clés, elles, restent celles enregistrées dans les préférences.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sablier", "0011_distinct_universes")]

    operations = [
        migrations.AlterField(
            model_name="focuspreference",
            name="ambience",
            field=models.CharField(
                choices=[
                    ("arbre_etoiles", "Arbre des étoiles"),
                    ("refuge_pluie", "Refuge sous la pluie"),
                    ("foret", "Forêt des origines"),
                    ("ocean", "Falaises de l'infini"),
                    ("sahara", "Observatoire des sables"),
                    ("aurores", "Vallée des aurores"),
                    ("galaxie", "Odyssée stellaire"),
                    ("fleuve_temps", "Fleuve du Temps"),
                    ("abysses", "Sanctuaire abyssal"),
                ],
                default="arbre_etoiles",
                max_length=16,
                verbose_name="univers",
            ),
        ),
    ]
