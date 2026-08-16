# MyENT

MyENT est un environnement numérique personnel modulaire. Il réunit organisation, contenus, outils de travail et concentration ; le module Formations reste disponible sans structurer le reste de l’application.

## Socle disponible

- tableau de bord personnalisable et responsive ;
- agenda en vues mois et semaine, tâches reliables aux études, rappels, et séries explicites dont chaque occurrence reste modifiable ;
- suppression confirmée de tout objet, annonçant ce qui disparaîtra en cascade ;
- bibliothèque filtrable et paginée de liens, fichiers privés et notes riches assainies, avec éditeur local sans CDN ;
- recherche globale indexée : une entrée par objet dans `core.SearchEntry`, tenue à jour par signaux, interrogée en plein texte PostgreSQL (configuration `french`, titre pondéré au-dessus du corps, syntaxe `websearch`) avec repli `icontains` sous SQLite ;
- formations génériques : catalogue, import/export, année, période courante, regroupements, matières, compétences et métriques libres ;
- grille de suivi de compétences : une ligne par matière avec ses chiffres saisissables sur place, une ligne par compétence avec niveau de maîtrise, heures estimées et réelles, commentaires ; totaux par matière et par période calculés, tout s’enregistre en un seul envoi ;
- Sablier web avec onze visualisations (anneau, sablier, marée, bougie, perles, lune, colonnes, spirale, soleil, digital, zen) et vingt-quatre univers, plein écran et reprise exacte après actualisation ;
- scène immersive rendue en WebGL : le sablier, la bougie, les perles, la Lune et le Soleil sont des objets en volume, à matières physiques et à cartes de relief calculées, posés dans un lieu qui existe vraiment autour d'eux — relief, eau, végétation, brume, colonnes de lumière. Le ciel de l'univers choisi éclaire l'objet et son ombre tombe sur son sol ; le dessin 2D reste le repli exact quand WebGL est indisponible ;
- bibliothèque audio privée, téléversement de plusieurs pistes en une fois, et playlists indépendantes du minuteur ;
- journal corrigeable des sessions Sablier, avec temps manuel, temps des sessions et total séparés ;
- notifications internes, emails, invitations à usage unique, réinitialisation de mot de passe, limitation des tentatives de connexion et préférences d’apparence.

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
npm run vendor          # copie Three.js dans src/static/vendor ; sans elle, le Sablier retombe sur son dessin 2D
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

Consulter [le déploiement Coolify](docs/DEPLOYMENT.md), [la migration de l’existant](docs/MIGRATION.md) et [la feuille de maturation](docs/ROADMAP.md). Les sources historiques se trouvent dans [oldVersion](oldVersion/README.md).
