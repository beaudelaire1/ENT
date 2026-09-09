# Direction des univers Sablier

Les identifiants sont conservés. Les valeurs ci-dessous décrivent les compositions livrées ; elles ne constituent pas une validation visuelle. Ce que le code vérifie de lui-même — que chaque univers se construise, se libère et reste dans ses ressources — tient dans `npm run test:worlds`.

Chaque univers est aussi livré en vues fixes (`src/static/sablier/thumbnails/`), servies au poste sans WebGL et à la galerie. Elles sortent du moteur lui-même, par `npm run plates` puis `tools/sablier-plates.py` : une illustration dessinée à côté aurait fini par montrer autre chose que le lieu.

Les scènes restent stables pendant le décompte : aucune transformation narrative non implémentée n’est annoncée. Les mouvements sont des cycles locaux, indépendants de la durée. Statique et la préférence de réduction des animations les figent.

| Univers | Point de vue | Plans de profondeur | Élément principal | Matières | Lumières | Mouvements |
|---|---|---|---|---|---|---|
| Arbre des étoiles | Rive nocturne, arbre de trois quarts | roche proche / île / lac et ciel | arbre solitaire, lanternes aux branches | écorce, feuillage découpé, eau calme | lanternes chaudes, ciel bleu | ondulations du lac ; caméra fixe |
| Fontaine de l’Éternité | Parvis au pied de la falaise | bassin / terrasses / cité adossée au roc | bassins en cascade et maisons superposées | pierre claire, eau turquoise | ciel et ouvertures lumineuses | chute et circulation de l’eau |
| Éden | Entrée ouverte du jardin | ruisseau / terrasses / arbre monumental | jardin à plusieurs niveaux | pierre, herbe et feuillage | soleil haut diffus | courant du ruisseau |
| Fleuve du Temps | Berge à hauteur humaine | rive / méandres et arches / brume | fleuve sinueux | pierre érodée, eau sombre | ciel crépusculaire, rares fragments | courant et fragments discrets |
| Souvenirs | Pièce intime, face au mur de souvenirs | mobilier / cadres / rideaux | cadres, commode, table et fauteuil | bois, tissu et enduit | lumière chaude latérale | mouvement faible des rideaux |
| Interstellaire | Intérieur de la station | sol et consoles / baie / planète | grande baie structurelle | métal satiné et verre | écrans bleus, astre lointain | ciel stable ; caméra fixe |
| Odyssée stellaire | Vue cosmique sans architecture | étoiles / bras spiraux / nébuleuses | galaxie inclinée | points lumineux et gaz diffus | noyau et étoiles | composition stable |
| Heaven — Hauts Cieux | Balcon sur le vide | bord de plateforme / îles étagées / nuages | îles suspendues avec pavillons | pierre claire et métal pâle | soleil, rebond des nuages | dérive lente des nuages |
| Oasis des confins | Bord du bassin | eau et plantes / palmiers / dunes | bassin ovale entouré de palmes | sable, eau, troncs fibreux | soleil rasant | rides de l’eau |
| Sanctuaire abyssal | Fond marin, horizon noyé | coraux / architecture engloutie / sédiments | arche brisée sous l’eau | pierre colonisée, sable, coraux | lumière filtrée bleue | banc de poissons et sédiments rares |
| Refuge sous la pluie | Assis devant la fenêtre | bureau et lampe / vitre / ville | véritable bureau intérieur | bois, laiton, verre | lampe chaude et ville froide | gouttes glissant sur la vitre |
| Vallée des aurores | Bord du lac gelé | glace fissurée / montagnes latérales / aurores | vallée encaissée | neige, glace et roche | aurores vertes et bleues | ondulation des rideaux lumineux |
| Printemps | Au bord du ruisseau | branche / verger / arbres lointains | verger en fleurs | écorce, fleurs et eau | soleil de printemps | courant et quelques pétales |
| Été | Sous la pergola | dalles et table / poutres / vallée | terrasse habitée | pierre claire et bois | soleil et ombres des poutres | composition stable |
| Automne | Sur le ponton | planches et feuilles / arbres / lac | chemin de bois au bord de l’eau | bois patiné, feuilles et eau | soleil bas | feuilles rares et rides du lac |
| Hiver | Devant le refuge | neige / chalet / massif alpin | chalet sous une toiture enneigée | bois, neige épaisse et roche | fenêtres chaudes, lumière froide | chute de neige |
| Pluie | Piéton dans la rue | chaussée et flaques / façades / perspective | rue entre façades proches | asphalte, enduit et eau | fenêtres reflétées en fragments | pluie et rides des flaques |
| Falaises de l'infini | Promontoire élevé | bord rocheux / aiguilles / océan | falaise et océan ouvert | roche stratifiée, eau | soleil maritime | houle géométrique |
| Observatoire des sables | Au pied des dunes | sable et strates / observatoire / grandes dunes | observatoire partiellement enfoui | sable, pierre et métal | soleil rasant | voile de sable discret |
| Forêt des origines | Au ras du sous-bois | racines et fougères / troncs / canopée | sous-bois fermé | écorce, bois mort et feuilles | lumière filtrée par la canopée | composition stable |
| Orage | Face au front météorologique | rocher / mer agitée / front nuageux | météo dominant la mer | eau et roche mouillée | ciel couvert ; éclair facultatif | houle forte, pluie et nuages |
| Braises | Proche du foyer | pierre / charbon et cendre / fond du foyer | braises dans un foyer de pierre | charbon, cendre, pierre | incandescence chaude | variation lente de l’incandescence |
| Aurore | Plaine à horizon bas | neige / plaine / grand ciel | aurores sur une plaine ouverte | neige et atmosphère | aurores vertes | ondulation des rideaux lumineux |
| Nuit | Sur un toit-terrasse | banc et sol / parapet / ville | terrasse au-dessus de la ville | pierre, bois et métal | fenêtres rares, ciel nocturne | composition stable |
