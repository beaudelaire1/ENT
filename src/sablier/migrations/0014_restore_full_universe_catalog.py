"""Rouvre le catalogue aux vingt-quatre univers.

La migration 0011 avait retiré quinze univers au motif qu'ils n'étaient que la même
scène reteintée, et réécrit les préférences vers le lieu dont chacun passait pour la
variante. `premium3d/worlds.js` porte pourtant une recette entière pour chacun d'eux :
l'été n'y est pas « la forêt en jaune », c'est une autre terrasse, une autre heure.

Seules les valeurs permises changent ici. Les préférences déjà réécrites par 0011 le
restent : rien ne dit vers quel univers chacune pointait avant, et deviner à leur place
serait pire que de les laisser choisir à nouveau.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sablier', '0013_reliable_sessions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='focuspreference',
            name='ambience',
            field=models.CharField(choices=[('arbre_etoiles', 'Arbre des étoiles'), ('fontaine', 'Fontaine de l’Éternité'), ('eden', 'Éden'), ('fleuve_temps', 'Fleuve du Temps'), ('souvenirs', 'Souvenirs'), ('interstellaire', 'Interstellaire'), ('galaxie', 'Odyssée stellaire'), ('heaven', 'Heaven — Hauts Cieux'), ('oasis', 'Oasis des confins'), ('abysses', 'Sanctuaire abyssal'), ('refuge_pluie', 'Refuge sous la pluie'), ('aurores', 'Vallée des aurores'), ('printemps', 'Printemps'), ('ete', 'Été'), ('automne', 'Automne'), ('hiver', 'Hiver'), ('pluie', 'Pluie'), ('ocean', "Falaises de l'infini"), ('sahara', 'Observatoire des sables'), ('foret', 'Forêt des origines'), ('orage', 'Orage'), ('braises', 'Braises'), ('aurore', 'Aurore'), ('nuit', 'Nuit')], default='arbre_etoiles', max_length=16, verbose_name='univers'),
        ),
    ]
