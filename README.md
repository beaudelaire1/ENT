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
- Sablier web avec huit visualisations (anneau, sablier, marée, bougie, perles, lune, digital, zen), neuf ambiances qui colorent la scène et l'animent d'un décor — pétales, lucioles, feuilles, neige, pluie, vagues, sable, étoiles —, plein écran et reprise exacte après actualisation ;
- bibliothèque audio privée, téléversement de plusieurs pistes en une fois, et playlists indépendantes du minuteur ;
- journal corrigeable des sessions Sablier, avec temps manuel, temps des sessions et total séparés ;
- notifications internes, emails, invitations à usage unique, réinitialisation de mot de passe, limitation des tentatives de connexion et préférences d’apparence.

Le serveur est un monolithe Django 5.2/Python 3.12. JavaScript ne gère que les interactions du navigateur, dont le moteur de Sablier. Le code Qt historique reste une référence archivée et n’est pas une dépendance de production.

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
