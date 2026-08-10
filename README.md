# MyENT

MyENT est un environnement numérique personnel modulaire. Il réunit organisation, contenus, outils de travail et concentration ; le module Formations reste disponible sans structurer le reste de l’application.

## Socle disponible

- tableau de bord personnalisable et responsive ;
- agenda, tâches ponctuelles et rappels ;
- bibliothèque de liens, fichiers privés et notes riches assainies ;
- recherche globale ;
- formations génériques : parcours, périodes, unités, compétences et métriques libres ;
- Sablier web avec quatre visualisations, quatre ambiances, trois niveaux de concentration, plein écran et reprise exacte après actualisation ;
- bibliothèque audio privée et playlists indépendantes du minuteur ;
- notifications internes, emails, invitations à usage unique et préférences d’apparence.

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
python src/manage.py generate_soundscapes
python src/manage.py runserver
```

Sans `DATABASE_URL`, Django utilise uniquement une base SQLite locale de développement. PostgreSQL est obligatoire en production.

## Vérification

```powershell
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
python src/manage.py test accounts.tests core.tests dashboard.tests library.tests planner.tests sablier.tests
```

Consulter [le déploiement Coolify](docs/DEPLOYMENT.md), [la migration de l’existant](docs/MIGRATION.md) et [la feuille de maturation](docs/ROADMAP.md). Les sources historiques se trouvent dans [oldVersion](oldVersion/README.md).
