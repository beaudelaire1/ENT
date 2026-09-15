"""Reprendre une tâche là où on l'avait laissée : ses ressources, d'où qu'elles viennent."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

# À passer à `prefetch_related` sur toute liste de tâches qui affiche leurs ressources :
# `task_resources` lit alors le cache au lieu d'interroger la base tâche par tâche.
RESOURCE_PREFETCH = ("resources", "unit__resources", "competency__resources", "assessment__resources")


def task_resources(task) -> list[dict]:
    """Les ressources propres à la tâche, puis celles de sa compétence, de sa matière et de
    son évaluation, sans doublon.

    Chaque entrée garde toutes ses provenances : une fiche rattachée à la fois à la tâche et
    à la compétence n'apparaît qu'une fois, en disant pourquoi elle est là. Rien n'est recopié
    sur la tâche ; changer les ressources d'une compétence change aussitôt cette liste.
    """
    found: dict[int, dict] = {}

    def add(items, source):
        for item in items:
            if item.owner_id != task.owner_id:
                continue
            entry = found.setdefault(item.pk, {"item": item, "sources": []})
            if source not in entry["sources"]:
                entry["sources"].append(source)

    add(task.resources.all(), "Tâche")
    if task.competency_id:
        add(task.competency.resources.all(), f"Compétence · {task.competency}")
    if task.unit_id:
        add(task.unit.resources.all(), f"Matière · {task.unit}")
    if task.assessment_id:
        add(task.assessment.resources.all(), f"Évaluation · {task.assessment}")
    return list(found.values())


def planning_slot(task, now=None):
    """Un créneau d'une heure pour avancer la tâche : à l'heure pleine suivante, ou juste
    avant l'échéance quand elle tombe plus tard aujourd'hui — un créneau placé après
    l'échéance ne servirait à rien."""
    now = timezone.localtime(now or timezone.now())
    starts_at = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    if task.due_at:
        due = timezone.localtime(task.due_at)
        if due.date() == now.date() and due - timedelta(hours=1) >= now:
            starts_at = due - timedelta(hours=1)
    return starts_at, starts_at + timedelta(hours=1)
