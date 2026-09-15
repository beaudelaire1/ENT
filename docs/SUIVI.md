# Suivi des travaux de MyENT

Liste active, établie le 15 septembre 2026 à partir du code. Elle remplace, comme référence
de ce qui reste à faire, l'[audit du 5 septembre](AUDIT_2026-09-05.md) et les plans
d'amélioration, conservés pour l'historique. Les grandes orientations restent dans la
[feuille de maturation](ROADMAP.md).

Chaque point porte trois états, parce qu'ils ne se prouvent pas de la même façon :

- **Implémenté** — le code existe et la suite automatisée le couvre ;
- **Navigateur** — le comportement a été constaté dans un vrai navigateur ;
- **Préproduction** — vérifié avec les vrais services (PostgreSQL, SMTP, S3, proxy).

**État vérifié le 15 septembre 2026 :** 668 tests Django, `ruff check` et
`ruff format --check` réussis ; 15 tests Node (`npm test`) réussis.

## 1. Avant l'ouverture en production — bloquant

Aucun de ces points ne se prouve dans le code. La marche à suivre est celle des
[contrôles avant production](DEPLOYMENT.md#contrôles-avant-production).

| Point | Implémenté | Navigateur | Préproduction |
|---|---|---|---|
| Restauration complète : base **et** archive média dans un environnement vide, puis ouverture d'un fichier privé | oui (sauvegarde, rétention) | — | **non** |
| Alerte sur l'échec de la sauvegarde nocturne | configuration Coolify | — | **non** |
| Envoi d'e-mails réel (invitation, rappel sans doublon) | oui | non | **non** |
| Objets S3 privés, jamais publics | oui | — | **non** |
| Refus de démarrer sans `DATABASE_URL` | oui | — | **non** |
| Piste audio écoutée en entier sans immobiliser de worker ; emplacement interne du proxy injoignable de l'extérieur | oui | — | **non** |
| `check --deploy`, en-têtes de sécurité, `/healthz/` | oui | — | **non** |

## 2. Corrigé depuis l'audit du 5 septembre

| Point de l'audit | Implémenté | Navigateur |
|---|---|---|
| A — progression calculée sur toutes les compétences du périmètre | oui | non |
| B — niveau suggéré distinct du niveau confirmé dans les synthèses et les reprises | oui | non |
| C — agenda classé dans le fuseau du compte ; événements sur tous les jours traversés | oui | non |
| D — sessions Sablier sans perte ni doublon (file locale, identifiant stable) | oui | oui (`tests/browser/reliability.spec.cjs`) |
| E — disposition de l'accueil validée d'un bloc, erreur signalée | oui | non |
| F — redirections limitées au site (`safe_next`) | oui | non |
| G — export personnel fidèle | oui | — |
| Tests dépendant de la date ; formatage bloquant la CI | oui | — |

## 3. Lot « Aujourd'hui » — à faire

Le contenu détaillé et les cinq parcours de recette sont dans l'audit, section
« Le contenu précis du lot Aujourd'hui ».

| Livrable | État |
|---|---|
| Accueil par échéance : en retard, du jour, sans date ; Reporter, Terminer, Planifier, avec annulation | implémenté (`planner/today.py`, `planner/undo.py`) ; vu dans le navigateur sur ordinateur et téléphone |
| Formation principale choisie et enregistrée | implémenté (`UserProfile.primary_path`, réglages, fiche de formation, export) ; vu dans le navigateur |
| Capture rapide d'une tâche ou d'un lien ; transformer une note en tâche | implémenté (« + Capturer » dans l'en-tête, `dashboard:capture`, `library:note_to_task`, `Task.resources`) ; vu dans le navigateur sur ordinateur et téléphone |
| Recherche : raccourci clavier, extraits surlignés, filtres de type | non commencé |
| Continuité depuis une tâche : ressources, créneau d'agenda, lancement de Sablier | non commencé — le lancement depuis une compétence existe |

## 4. Robustesse

| Point | État |
|---|---|
| Recette sur téléphone et au clavier des parcours critiques | non faite |
| Mesure sur un compte chargé ; pagination de la liste des tâches | non faite |
| Dépendances Python verrouillées, procédure de mise à jour | non fait |
| Suivi des erreurs, de la latence, des files Celery, des quotas et des sauvegardes | non fait |

## 5. Sablier

| Point | Implémenté | Navigateur |
|---|---|---|
| Objets posés sur les supports de chaque univers, par règles | oui | oui pour les objets photographiés ; **non** pour perles, colonnes et spirale en volume |
| Test Playwright du placement (pied de l'objet sur son support, sans chevaucher le temps) | **non** | — |
| Sur téléphone, objets petits et proches du bord dans une dizaine d'univers | à améliorer | — |
| Chargement : Three.js (2 Mo) et 31 modules en requêtes séparées, à regrouper | non | — |
| Fleuve du Temps : encore bâti en volume ; placement approximatif sur téléphone | non | — |
| `tools/sablier-plates.py` écrase les vues fixes des univers photographiques | à protéger | — |
| Disque de musique hors du bouton de pause | oui | oui, disque affiché à la main ; pas avec une lecture réelle |

## 6. Rangement

- `tools/.probe-panorama.cjs` et `tools/sablier-photo-plates.py` : non suivis par git, jamais
  branchés — à supprimer.
