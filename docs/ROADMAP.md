# Maturation de MyENT

## Mise en ligne initiale

- déployer une préproduction Coolify avec SMTP et deux buckets S3 privés ;
- exécuter l’import historique sur une copie PostgreSQL et valider le rapport ;
- tester une restauration complète PostgreSQL/S3 ;
- corriger les écarts observés, puis promouvoir exactement la même image en production.

## Stabilisation

- ajouter les récurrences simples d’événements et de tâches ;
- enrichir la recherche PostgreSQL (index plein texte, filtres et raccourcis) ;
- ajouter des tests navigateur automatisés aux quatre modes de Sablier ;
- suivre erreurs, latence, files Celery, quotas et succès des sauvegardes ;
- rendre l’éditeur riche autonome dans le dépôt si une politique sans CDN devient nécessaire.

## Ouverture maîtrisée

- partage explicite d’éléments de bibliothèque sans changer leur propriétaire ;
- espaces de groupes, rôles et permissions par objet ;
- quotas par invitation ou groupe et journal d’administration ;
- API versionnée, export/import personnel et PWA installable.

Les statistiques de productivité, l’historique de concentration et le couplage automatique entre Sablier et les formations restent hors périmètre tant qu’un besoin utilisateur clair ne les justifie pas.

