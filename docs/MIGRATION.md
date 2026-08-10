# Migration de l’ancienne version

Les sources originales sont conservées dans `oldVersion/`. Elles ne sont ni montées dans l’image Docker ni modifiées par l’import.

```powershell
python src/manage.py createsuperuser
python src/manage.py import_legacy --username votre_compte --report migration-report.json
```

La commande peut être relancée. Les liens et documents utilisent des identifiants hérités, les formations utilisent des clés métier stables. Le rapport indique les comptes historiques à vérifier, les quantités importées, les parties tronquées des prototypes et l’absence éventuelle de `topo25.pdf`.

Avant toute suppression de l’ancienne base : comparer les quantités, ouvrir un échantillon de ressources, vérifier la formation L3, restaurer une sauvegarde PostgreSQL dans un environnement isolé et conserver une copie hors VPS de `oldVersion/`.

