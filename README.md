# MyENT

MyENT est un environnement numérique personnel modulaire. Il réunit organisation, contenus, outils de travail et concentration ; le module Formations reste disponible sans structurer le reste de l’application.

## Socle disponible

- tableau de bord personnalisable et responsive ;
- agenda en vues mois et semaine, tâches reliables aux études, rappels et séries explicites dont chaque occurrence reste modifiable ;
- priorités de tâches à deux niveaux distincts : importance intrinsèque (`Haute`, `Normale`, `Basse`) et cap choisi pour aujourd’hui, la semaine et le mois ;
- suppression confirmée de tout objet, annonçant ce qui disparaîtra en cascade ;
- bibliothèque filtrable et paginée de liens, fichiers privés et notes riches assainies, avec éditeur local sans CDN ;
- recherche globale indexée : une entrée par objet dans `core.SearchEntry`, tenue à jour par signaux, interrogée en plein texte PostgreSQL (configuration `french`, titre pondéré au-dessus du corps, syntaxe `websearch`) avec repli `icontains` sous SQLite ;
- formations génériques : catalogue, import/export, année, période courante, regroupements, matières, compétences et métriques libres ;
- grille de suivi de compétences : une ligne par matière avec ses chiffres saisissables sur place, une ligne par compétence avec niveau de maîtrise, heures estimées et réelles, commentaires ; totaux par matière et par période calculés, tout s’enregistre en un seul envoi ;
- Sablier web avec onze visualisations (anneau, sablier, marée, bougie, perles, lune, colonnes, spirale, soleil, digital, zen) et vingt-quatre univers réellement distincts, plein écran et reprise exacte après actualisation ;
- scène immersive rendue en WebGL : chacun des vingt-quatre univers est un lieu en volume — sa propre heure, son relief, son eau, sa végétation, ses particules. Les six objets disposant d’un visuel validé (anneau, sablier, marée, bougie, lune, soleil) sont composés sur ce lieu avec fond transparent ; perles, colonnes et spirale restent des objets volumétriques. Le dessin 2D reste le repli quand WebGL est indisponible ;
- bibliothèque audio privée, téléversement de plusieurs pistes en une fois, et playlists indépendantes du minuteur ;
- journal corrigeable des sessions Sablier, avec synchronisation différée en cas de perte réseau, temps manuel, temps des sessions et total séparés ;
- notifications internes et emails dédupliqués, préférences par famille, invitations à usage unique, réinitialisation de mot de passe, limitation des tentatives de connexion et préférences d’apparence ;
- export personnel versionné incluant les relations nécessaires des tâches, séries, priorités temporelles, formations, bibliothèque, sessions, pistes audio et playlists ; les fichiers binaires restent volontairement hors de l’export JSON.

Le serveur est un monolithe Django 5.2/Python 3.12. JavaScript ne gère que les interactions du navigateur, dont le moteur de Sablier. Le code Qt historique reste une référence archivée et n’est pas une dépendance de production.

Rien n’est chargé depuis un CDN : Three.js est copié dans `src/static/vendor` par `npm run vendor`, qui vend l’arbre complet — moteur, noyau et modules d’exemple — et refuse de rendre la main si un import sort du dossier. Aucune texture n’est téléchargée non plus : le grain du sable, la nacre, le métal brossé, le régolithe et les reliefs des paysages sont calculés au chargement par bruit fractal et cellulaire.

## Démarrage local avec Docker

```powershell
Copy-Item .env.example .env
# Adapter DJANGO_SECRET_KEY, POSTGRES_PASSWORD et DATABASE_URL dans .env.
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
docker compose exec web python manage.py createsuperuser
```

L’application est alors disponible sur `http://localhost:8000`. PostgreSQL et Redis ne publient aucun port hôte.

## Démarrage Python pour le développement

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
npm install --ignore-scripts
npm run vendor          # copie Three.js dans src/static/vendor ; sans elle, Sablier utilise ses vues fixes locales
python src/manage.py migrate
python src/manage.py generate_chime
python src/manage.py runserver
```

Sans `DATABASE_URL`, Django utilise uniquement une base SQLite locale de développement. PostgreSQL est obligatoire en production.

## Vérification

```powershell
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
python src/manage.py test accounts.tests core.tests dashboard.tests formations.tests library.tests notifications.tests planner.tests sablier.tests
coverage run src/manage.py test accounts.tests core.tests dashboard.tests formations.tests library.tests notifications.tests planner.tests sablier.tests && coverage report
```

Les vingt-quatre univers du Sablier se vérifient dans un vrai navigateur, avec un GPU logiciel :
la recette dure plusieurs minutes et reste donc hors du passage courant.

```powershell
npm run test:browser    # parcours fonctionnels
npm run test:worlds     # les 24 univers, la galerie et le repli sans WebGL
```

Les vues fixes servies aux postes sans WebGL sortent du moteur qu’elles remplacent. Elles sont
versionnées ; on ne les régénère qu’après avoir changé un univers :

```powershell
.venv\Scripts\python.exe tests\browser\server.py   # dans un autre terminal
npm run plates
python tools/sablier-plates.py
```

Sur un déploiement réel, la chaîne de notifications peut être diagnostiquée sans attendre le prochain passage de Celery Beat :

```powershell
python src/manage.py check_notifications --user <nom_utilisateur> --scan
```

La commande distingue notamment l’absence de worker/beat, un backend email console, l’absence de `EMAIL_HOST`, les préférences désactivées et les dernières notifications du compte.

Consulter [le déploiement Coolify](docs/DEPLOYMENT.md), [la migration de l’existant](docs/MIGRATION.md) et [la feuille de maturation](docs/ROADMAP.md). Les sources historiques se trouvent dans [oldVersion](oldVersion/README.md).
