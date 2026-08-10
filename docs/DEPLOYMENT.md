# Déploiement OVHcloud avec Coolify

## Préproduction

1. Créer un VPS Linux OVHcloud, installer Docker puis Coolify.
2. Créer deux buckets S3 privés : un pour les médias, un autre pour les sauvegardes.
3. Dans Coolify, créer une ressource « Docker Compose » depuis ce dépôt et sélectionner `docker-compose.yml`.
4. Associer le domaine de préproduction au service `web`, port `8000`. Aucun autre service ne doit recevoir de domaine ni de port public.
5. Copier les variables de `.env.example` dans les secrets Coolify. Utiliser `DJANGO_DEBUG=false`, un secret Django aléatoire, le domaine HTTPS dans les hôtes/CSRF et les identifiants SMTP/S3.
6. Déployer. Le service `migrate` doit finir avec le code 0 avant le démarrage de `web`, `worker` et `beat`.
7. Créer l’administrateur : `python manage.py createsuperuser` dans le conteneur `web`.
8. Ajouter une tâche planifiée Coolify nocturne exécutant `docker compose --profile ops run --rm backup` depuis le projet.

## Contrôles avant production

- ouvrir `/healthz/` et vérifier `{"status":"ok"}` ;
- accepter une invitation de test et vérifier l’isolation avec un second compte ;
- téléverser puis télécharger un fichier privé et une piste audio ;
- tester un rappel interne/email et vérifier l’absence de doublon ;
- lancer Sablier, mettre l’onglet en arrière-plan puis l’actualiser ;
- exécuter une sauvegarde et restaurer le `.dump` dans une base PostgreSQL vide avec `pg_restore` ;
- vérifier que les objets S3 ne sont pas publics.

Après validation, reproduire les secrets dans un projet Coolify de production distinct et promouvoir la même image Git. Ne jamais partager les volumes ou bases entre préproduction et production.

