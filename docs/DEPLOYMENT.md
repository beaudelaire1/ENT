# Déploiement OVHcloud avec Coolify

## Préproduction

1. Créer un VPS Linux OVHcloud, installer Docker puis Coolify.
2. Créer deux buckets S3 privés : un pour les médias, un autre pour les sauvegardes.
3. Dans Coolify, créer une ressource « Docker Compose » depuis ce dépôt et sélectionner `docker-compose.yml`.
4. Associer le domaine de préproduction au service `web`, port `8000`. Aucun autre service ne doit recevoir de domaine ni de port public.
5. Copier les variables de `.env.example` dans les secrets Coolify — elles sont déjà réglées pour la production. Renseigner un secret Django aléatoire, le domaine HTTPS dans les hôtes/CSRF, les identifiants SMTP/S3, et `DJANGO_ADMINS` pour recevoir les erreurs serveur.
6. Déployer. Le service `migrate` doit finir avec le code 0 avant le démarrage de `web`, `worker` et `beat`. Sans `DATABASE_URL`, l’application refuse désormais de démarrer plutôt que de se rabattre sur une base SQLite non persistée.
7. Créer l’administrateur : `python manage.py createsuperuser` dans le conteneur `web`.
8. Ajouter une tâche planifiée Coolify nocturne exécutant `docker compose --profile ops run --rm backup` depuis le projet, **et configurer une alerte sur son échec** : une sauvegarde qui échoue en silence équivaut à une absence de sauvegarde.

## Ce que la sauvegarde couvre

`backup_database` écrit dans le bucket `BACKUP_S3_BUCKET`, distinct du bucket média, avec trois paliers de rétention (quotidien, hebdomadaire le dimanche, mensuel le 1er) :

- `database/…` — un `pg_dump` au format custom, toujours ;
- `media/…` — une archive du volume des fichiers privés, **uniquement quand `USE_S3=false`**. Avec `USE_S3=true`, les fichiers sont déjà dans un bucket : c’est son versionnement qui en tient lieu, et il doit alors être activé explicitement.

Une restauration se vérifie donc sur les deux, jamais sur la base seule : une base restaurée sans ses fichiers rend une application complète dont tous les liens sont morts.

## Téléversements volumineux

Une piste audio peut atteindre 1 Go (`AUDIO_MAX_TRACK_MB`), pour un quota de 10 Go par compte (`AUDIO_DEFAULT_QUOTA_MB`). Trois réglages en dépendent hors de Django :

- `GUNICORN_TIMEOUT` vaut 900 s. En dessous, le worker est tué au milieu d’un envoi long : 1 Go demande une dizaine de minutes sur une connexion domestique.
- Le proxy placé devant l’application doit accepter des corps de requête de cette taille. Traefik, utilisé par Coolify, ne limite rien par défaut ; **une configuration Nginx personnalisée refuserait la requête dès 1 Mo** — il faut alors relever `client_max_body_size`.
- Le conteneur écrit le fichier reçu dans son répertoire temporaire avant de le déplacer : prévoir l’espace disque correspondant.

Avec `USE_S3=true`, le navigateur peut téléverser directement vers le bucket via une URL présignée, ce qui contourne les deux premiers points. La limite S3 d’un envoi en une seule requête est de 5 Go, bien au-delà de la limite par piste.

## Remise des fichiers privés

Gunicorn tourne avec trois processus de deux fils : six requêtes simultanées. Un fichier servi par Django occupe l’une de ces places pendant toute la durée du transfert — et une piste audio écoutée en entier l’occupe pendant toute l’écoute. Trois auditeurs mobilisent alors la moitié du serveur.

Trois remises, de la meilleure à la dernière :

1. **`USE_S3=true`** — la vue vérifie le droit d’accès puis renvoie une redirection signée ; le fichier ne passe jamais par l’application. C’est le réglage recommandé en production.
2. **`MEDIA_INTERNAL_LOCATION`** — délégation au proxy. Django vérifie le droit d’accès, rend une réponse vide portant `X-Accel-Redirect`, et le proxy envoie le fichier. L’emplacement doit être déclaré **interne** côté proxy, sans quoi il exposerait publiquement tous les fichiers privés :

   ```nginx
   location /protected/ {
       internal;
       alias /app/src/media/;
   }
   ```

   puis `MEDIA_INTERNAL_LOCATION=/protected/` dans les secrets.
3. **Sans réglage** — Django sert le fichier lui-même. Correct, et le seul mode disponible en développement, mais il immobilise un worker par téléchargement.

## Contrôles avant production

- ouvrir `/livez/` et vérifier la vivacité du processus, puis `/healthz/` et vérifier que les contrôles `database` et `cache` valent `ok` ;
- exécuter `python manage.py check --deploy` dans le conteneur avec les variables de production ;
- vérifier les en-têtes `Content-Security-Policy`, `Permissions-Policy` et `X-Request-ID` ;
- accepter une invitation de test et vérifier l’isolation avec un second compte ;
- téléverser puis télécharger un fichier privé et une piste audio ;
- tester un rappel interne/email et vérifier l’absence de doublon ;
- lancer Sablier, mettre l’onglet en arrière-plan puis l’actualiser ;
- exécuter une sauvegarde, restaurer le `.dump` dans une base PostgreSQL vide avec `pg_restore`, **et** déployer l’archive média correspondante, puis ouvrir un fichier privé depuis l’application restaurée ;
- vérifier que les objets S3 ne sont pas publics.

Après validation, reproduire les secrets dans un projet Coolify de production distinct et promouvoir la même image Git. Ne jamais partager les volumes ou bases entre préproduction et production.

