"""Ce qui devient vrai en passant, et que personne ne vient déclarer.

Une tâche créée se signale au moment où on la crée. Une échéance dépassée, elle,
n'arrive du fait de personne : il faut aller regarder. Ce module est ce regard, passé à
intervalle régulier sur les objets de chaque compte.

Deux règles tiennent l'ensemble :

* **une clé de déduplication stable par fait**, jamais horodatée. « Cette tâche est en
  retard » est un fait unique ; le repasser toutes les heures ne doit pas produire une
  notification par heure. Les faits qui se répètent légitimement — le résumé de
  révision — portent la date du jour dans leur clé, et une seule fois par jour ;
* **rien n'est notifié deux fois sous deux titres.** Une tâche qui a un rappel posé par
  l'utilisateur ne reçoit pas en plus l'alerte d'échéance : c'est le même fait, et
  l'utilisateur a déjà dit comment il voulait l'apprendre.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from .services import notify

# Ce qui mérite qu'on prévienne aujourd'hui plutôt que demain.
SOON = timedelta(hours=24)
# Une évaluation se prépare : sept jours laissent le temps d'y faire quelque chose.
ASSESSMENT_HORIZON = timedelta(days=7)


def scan_all() -> int:
    """Passe sur tous les comptes actifs. Renvoie le nombre de notifications créées."""
    created = 0
    for user in get_user_model().objects.filter(is_active=True).iterator():
        created += scan_user(user)
    return created


def scan_user(user) -> int:
    created = 0
    for produce in (
        _tasks_due_soon,
        _tasks_overdue,
        _events_soon,
        _assessments_soon,
        _progress_hours_reached,
        _progress_target_due,
        _revision_digest,
        _audio_storage,
    ):
        created += sum(1 for notification in produce(user) if notification is not None)
    return created


def _tasks_due_soon(user):
    from planner.models import Task

    now = timezone.now()
    horizon = now + SOON
    tasks = Task.objects.filter(owner=user, due_at__gt=now, due_at__lte=horizon, reminder_at__isnull=True).exclude(
        status=Task.Status.DONE
    )
    for task in tasks:
        yield notify(
            user,
            "task.due_soon",
            dedupe_key=f"task-due:{task.pk}",
            title=f"Bientôt · {task.title}",
            message=f"Échéance {timezone.localtime(task.due_at):%A %d %B à %H h %M}.",
            url="/tasks/",
        )


def _tasks_overdue(user):
    from planner.models import Task

    tasks = Task.objects.filter(owner=user, due_at__lt=timezone.now()).exclude(status=Task.Status.DONE)
    for task in tasks:
        yield notify(
            user,
            "task.overdue",
            dedupe_key=f"task-overdue:{task.pk}",
            title=f"En retard · {task.title}",
            message=f"L'échéance était le {timezone.localtime(task.due_at):%d %B à %H h %M}.",
            url="/tasks/",
        )


def _events_soon(user):
    from planner.models import CalendarEvent

    now = timezone.now()
    events = CalendarEvent.objects.filter(
        owner=user, starts_at__gt=now, starts_at__lte=now + SOON, reminder_at__isnull=True
    )
    for event in events:
        yield notify(
            user,
            "event.soon",
            dedupe_key=f"event-soon:{event.pk}",
            title=f"Bientôt · {event.title}",
            message=f"Début {timezone.localtime(event.starts_at):%A %d %B à %H h %M}.",
            url="/agenda/",
        )


def _assessments_soon(user):
    from formations.models import Assessment

    now = timezone.now()
    assessments = Assessment.objects.filter(
        owner=user,
        status=Assessment.Status.PLANNED,
        scheduled_for__gt=now,
        scheduled_for__lte=now + ASSESSMENT_HORIZON,
    ).select_related("unit")
    for assessment in assessments:
        matter = f" · {assessment.unit.title}" if assessment.unit_id else ""
        yield notify(
            user,
            "assessment.soon",
            dedupe_key=f"assessment:{assessment.pk}",
            title=f"Évaluation · {assessment.title}",
            message=f"Prévue le {timezone.localdate(assessment.scheduled_for):%d %B}{matter}.",
            url="/formations/",
        )


def _progress_hours_reached(user):
    """Le travail personnel estimé est atteint.

    Une bonne nouvelle, pas une alerte : elle n'a pas d'heure, donc pas d'email. Le seuil
    ne vaut que si un estimé a été posé — sans objectif, il n'y a rien à atteindre.
    """
    from formations.models import ProgressRecord

    records = ProgressRecord.objects.filter(owner=user, planned_hours__gt=0).select_related("competency")
    for record in records:
        if record.actual_hours < record.planned_hours:
            continue
        yield notify(
            user,
            "progress.hours_reached",
            dedupe_key=f"hours:{record.pk}",
            title=f"Objectif d'heures atteint · {record.competency.title}",
            message=(f"{record.actual_hours} h travaillées sur les {record.planned_hours} h estimées."),
            url="/formations/",
        )


def _progress_target_due(user):
    """La date que l'utilisateur s'était fixée est passée, le niveau visé pas atteint.

    `target_is_late` porte déjà cette question dans le modèle : la reposer ici, en
    filtrant à la main sur les champs, aurait fait deux définitions du même retard.
    """
    from formations.models import ProgressRecord

    today = timezone.localdate()
    records = ProgressRecord.objects.filter(
        owner=user, target_date__lte=today, target_level__isnull=False
    ).select_related("competency")
    for record in records:
        if not record.target_is_late:
            continue
        yield notify(
            user,
            "progress.target_due",
            dedupe_key=f"target:{record.pk}:{record.target_date:%Y-%m-%d}",
            title=f"Objectif à échéance · {record.competency.title}",
            message=f"La date que vous aviez fixée est arrivée ({record.target_date:%d %B}).",
            url="/formations/",
        )


def _revision_digest(user):
    """Un seul résumé par jour, et seulement s'il y a quelque chose à dire.

    `formations/revision.py` pose que ce qui relève de la relecture est « une liste que
    l'on consulte, jamais une notification qui interrompt ». Une notification par
    compétence contredirait cela ; une par jour, qui renvoie vers la liste, informe sans
    harceler — et reste extinguible comme les autres.
    """
    from formations.models import LearningPath
    from formations.revision import to_revisit

    today = timezone.localdate()
    pending = []
    for path in LearningPath.objects.filter(owner=user):
        pending.extend(to_revisit(user, path, limit=3))
    if not pending:
        return
    titles = ", ".join(revision.competency.title for revision in pending[:3])
    yield notify(
        user,
        "revision.digest",
        dedupe_key=f"revision:{today:%Y-%m-%d}",
        title=f"À reprendre aujourd'hui · {len(pending)} compétence" + ("s" if len(pending) > 1 else ""),
        message=f"{titles}…" if len(pending) > 3 else titles,
        url="/formations/",
    )


# On prévient pendant qu'il reste de la place pour agir : à ras bord, l'information
# n'apprend plus rien que le refus de téléversement n'ait déjà dit.
AUDIO_WARNING_RATIO = 0.9


def _audio_storage(user):
    """L'espace musique du Sablier approche de son quota.

    Le seuil est franchi une fois : la clé porte le palier, pas la mesure du jour. Sans
    cela, chaque piste ajoutée au-dessus de 90 % aurait produit une notification de plus.
    """
    from django.db.models import Sum

    from accounts.models import UserProfile
    from sablier.models import AudioTrack

    profile = UserProfile.objects.filter(user=user).first()
    quota_mb = profile.effective_audio_quota_mb if profile else 0
    if not quota_mb:
        return
    used = AudioTrack.objects.filter(owner=user).counted_in_quota().aggregate(total=Sum("file_size"))["total"] or 0
    used_mb = used / (1024 * 1024)
    if used_mb < quota_mb * AUDIO_WARNING_RATIO:
        return
    yield notify(
        user,
        "storage.audio",
        dedupe_key=f"audio-quota:{quota_mb}",
        title="Espace musique bientôt atteint",
        message=f"{used_mb:.0f} Mo utilisés sur {quota_mb} Mo.",
        url="/sablier/musiques/",
    )
