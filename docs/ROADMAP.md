# Maturation de MyENT

## Mise en ligne initiale

- déployer une préproduction Coolify avec SMTP et deux buckets S3 privés ;
- exécuter l’import historique sur une copie PostgreSQL et valider le rapport ;
- tester une restauration complète PostgreSQL/S3 ;
- corriger les écarts observés, puis promouvoir exactement la même image en production.

## Stabilisation

- compléter la recherche : surlignage des extraits, raccourcis clavier et suggestions ;
- ajouter des tests navigateur automatisés aux quatre modes de Sablier ;
- étendre la couverture de `sablier` (formulaires et téléversement S3), aujourd’hui la plus faible ;
- suivre erreurs, latence, files Celery, quotas et succès des sauvegardes ;
- rendre l’éditeur riche autonome dans le dépôt si une politique sans CDN devient nécessaire.

## Ouverture maîtrisée

- partage explicite d’éléments de bibliothèque sans changer leur propriétaire ;
- espaces de groupes, rôles et permissions par objet ;
- quotas par invitation ou groupe et journal d’administration ;
- API versionnée, export/import personnel et PWA installable.

Le journal des sessions Sablier existe désormais, mais uniquement pour reporter du temps sur une compétence choisie explicitement. Les statistiques de productivité, l’historique de concentration présenté comme une métrique et tout couplage automatique entre Sablier et les formations restent hors périmètre : l’outil doit rester calme, pas devenir un tableau de bord de performance.

