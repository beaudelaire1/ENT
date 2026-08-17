"""Ce dont l'ENT informe, et à quel titre.

Une seule liste, ici. Les producteurs y puisent leur clé, les préférences y puisent
leurs cases à cocher, les tests y puisent ce qu'ils vérifient : rien ne peut être
notifié sans être déclaré, ni déclaré sans être réglable.

Deux notions, et pas une de plus :

* la **famille** est ce que l'utilisateur reconnaît et règle — « mes tâches »,
  « mes formations ». C'est l'unité des préférences ;
* l'**urgence** dit si l'email suit. Elle appartient à l'événement, pas à la famille :
  une tâche créée n'a pas à sonner dans une boîte mail, une échéance dépassée si.

La règle de conception du projet — « l'outil doit rester calme » (ROADMAP), et pour les
révisions « une liste que l'on consulte, jamais une notification qui interrompt »
(`formations/revision.py`) — n'est pas contredite : ce qui relève de la relecture est
groupé en un résumé quotidien, jamais éclaté en une alerte par compétence.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Family:
    key: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class Event:
    key: str
    family: str
    label: str
    # L'email ne suit que ce qui a une heure : ce qu'on manquerait en ne regardant pas
    # l'application aujourd'hui. Le reste attend sagement dans la cloche.
    urgent: bool = False


FAMILIES: tuple[Family, ...] = (
    Family("tasks", "Tâches", "Créations, échéances proches et retards de votre liste de tâches."),
    Family("agenda", "Agenda", "Événements qui approchent et rappels que vous avez posés."),
    Family("formations", "Formations", "Nouveaux parcours, matières et compétences ; évaluations qui approchent."),
    Family("progress", "Progression", "Objectifs d'heures atteints et dates d'objectif arrivées à terme."),
    Family("revision", "Révisions", "Un résumé quotidien de ce qu'il y aurait lieu de reprendre."),
    Family("library", "Bibliothèque et stockage", "Documents ajoutés, et espace musique bientôt atteint."),
)

EVENTS: tuple[Event, ...] = (
    # ── Tâches ────────────────────────────────────────────────────────────────────
    Event("task.created", "tasks", "Tâche créée"),
    Event("task.due_soon", "tasks", "Échéance dans moins de 24 heures", urgent=True),
    Event("task.overdue", "tasks", "Échéance dépassée", urgent=True),
    # ── Agenda ────────────────────────────────────────────────────────────────────
    Event("event.soon", "agenda", "Événement dans moins de 24 heures", urgent=True),
    Event("reminder", "agenda", "Rappel que vous avez posé", urgent=True),
    # ── Formations ────────────────────────────────────────────────────────────────
    Event("formation.created", "formations", "Nouveau parcours, matière ou compétence"),
    Event("assessment.soon", "formations", "Évaluation dans moins de sept jours", urgent=True),
    # ── Progression ───────────────────────────────────────────────────────────────
    Event("progress.hours_reached", "progress", "Travail personnel estimé atteint"),
    Event("progress.target_due", "progress", "Date d'objectif arrivée à terme", urgent=True),
    # ── Révisions ─────────────────────────────────────────────────────────────────
    Event("revision.digest", "revision", "Ce qu'il y aurait lieu de reprendre"),
    # ── Bibliothèque ──────────────────────────────────────────────────────────────
    Event("library.added", "library", "Document ajouté"),
    # Le seul quota réel de l'ENT est celui de la musique du Sablier. L'annoncer sous le
    # nom d'un « espace de stockage » général aurait promis une surveillance qui n'existe
    # pas : la bibliothèque, elle, n'a qu'un plafond par fichier.
    Event("storage.audio", "library", "Espace musique bientôt atteint", urgent=True),
)

FAMILY_BY_KEY = {family.key: family for family in FAMILIES}
EVENT_BY_KEY = {event.key: event for event in EVENTS}


def event(key: str) -> Event:
    """L'événement déclaré sous cette clé, ou une erreur franche.

    Notifier sous une clé inconnue échouerait autrement en silence : la notification
    partirait sans préférence associée, donc sans moyen de l'éteindre.
    """
    try:
        return EVENT_BY_KEY[key]
    except KeyError:
        raise KeyError(f"événement de notification non déclaré : {key!r}") from None
