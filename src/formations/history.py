"""Reconstruction de l'état passé d'une formation à partir du journal des niveaux.

Le journal enregistre des changements, pas des états : pour savoir où en était une
formation à une date, il faut rejouer ses changements jusque-là. C'est fait en mémoire, en
une seule lecture ordonnée — l'alternative, une requête par point de la courbe, coûterait
douze requêtes pour douze mois et dirait exactement la même chose.

Une compétence sans aucun changement n'a jamais quitté « non abordé » : elle compte dans le
total et jamais dans les acquis, ce qui est précisément ce qu'une courbe honnête doit
montrer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from .models import Competency, ProgressEvent, ProgressRecord

ACQUIRED = ProgressRecord.Mastery.ACQUIRED


@dataclass(frozen=True, slots=True)
class Point:
    label: str
    acquired: int
    total: int

    @property
    def percent(self) -> int:
        return round(self.acquired * 100 / self.total) if self.total else 0


MONTHS = (
    "janv.",
    "févr.",
    "mars",
    "avril",
    "mai",
    "juin",
    "juill.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)


def _month_ends(today: date, count: int) -> list[date]:
    """Le dernier jour de chacun des `count` derniers mois, le mois courant compris."""
    ends = []
    year, month = today.year, today.month
    for _ in range(count):
        following = date(year + month // 12, month % 12 + 1, 1)
        ends.append(min(following.toordinal() - 1, today.toordinal()))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return [date.fromordinal(value) for value in reversed(ends)]


def level_timeline(user, path, *, months: int = 12) -> list[Point]:
    """L'évolution du nombre de compétences acquises, mois par mois.

    Rend une liste vide quand la formation n'a aucune compétence, ou quand rien n'a jamais
    bougé : une courbe plate à zéro n'apprend rien et occupe l'écran d'un débutant qui a
    surtout besoin de commencer.
    """
    total = Competency.objects.filter(path=path).count()
    if not total:
        return []
    events = list(
        ProgressEvent.objects.filter(record__owner=user, record__competency__path=path)
        .order_by("created_at", "pk")
        .values_list("record_id", "level", "created_at")
    )
    if not events:
        return []

    boundaries = _month_ends(timezone.localdate(), months)
    levels: dict[int, int] = {}
    points: list[Point] = []
    index = 0
    for boundary in boundaries:
        while index < len(events) and timezone.localtime(events[index][2]).date() <= boundary:
            record_id, level, _moment = events[index]
            levels[record_id] = level
            index += 1
        acquired = sum(1 for level in levels.values() if level >= ACQUIRED)
        points.append(Point(label=f"{MONTHS[boundary.month - 1]} {boundary.year}", acquired=acquired, total=total))
    return points


def sparkline(points: list[Point], *, width: int = 320, height: int = 72) -> dict:
    """Les coordonnées de la courbe, calculées côté serveur.

    Le tracé est un SVG écrit dans le gabarit : aucun script, donc rien à autoriser dans
    la politique de sécurité, et la courbe reste lisible sans JavaScript.
    """
    if len(points) < 2:
        return {}
    padding = 6
    span = width - 2 * padding
    usable = height - 2 * padding
    step = span / (len(points) - 1)
    ceiling = max((point.total for point in points), default=1) or 1
    coordinates = [
        (
            round(padding + index * step, 1),
            round(height - padding - (point.acquired / ceiling) * usable, 1),
        )
        for index, point in enumerate(points)
    ]
    line = " ".join(f"{x},{y}" for x, y in coordinates)
    return {
        "width": width,
        "height": height,
        "line": line,
        "area": f"{padding},{height - padding} {line} {round(padding + (len(points) - 1) * step, 1)},{height - padding}",
        "last": coordinates[-1],
    }
