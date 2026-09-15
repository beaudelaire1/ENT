"""Index de recherche unifié.

Chaque modèle consultable déclare ici comment il se projette dans une ligne de
``SearchEntry`` : titre, corps, adresse. Les signaux tiennent l’index à jour, et la
vue de recherche interroge une seule table indexée plutôt que d’enchaîner un
``LIKE '%…%'`` par modèle — un balayage séquentiel qu’aucun index ne peut servir.

Ajouter un modèle à la recherche globale consiste à ajouter une entrée à ``SOURCES``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from django.apps import apps
from django.db import connections, router
from django.db.models import Count, F, Q, QuerySet
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

# Configuration textuelle de PostgreSQL : lemmatise et écarte les mots vides français,
# afin que « révisions » trouve « révision ».
SEARCH_CONFIG = "french"


@dataclass(frozen=True)
class SearchSource:
    """Projection d’un modèle vers l’index."""

    label: str
    model_label: str
    owner: Callable[[object], object | None]
    title: Callable[[object], str]
    body: Callable[[object], str]
    url: Callable[[object], str]

    @property
    def model(self):
        return apps.get_model(self.model_label)


def _joined(*values) -> str:
    return "\n".join(str(value) for value in values if value)


SOURCES: dict[str, SearchSource] = {
    "library": SearchSource(
        label="Bibliothèque",
        model_label="library.LibraryItem",
        owner=lambda o: o.owner,
        title=lambda o: o.title,
        body=lambda o: _joined(
            o.description, o.note_text, o.provider_name, o.source_category, *o.tags.values_list("name", flat=True)
        ),
        url=lambda o: reverse("library:detail", args=[o.pk]),
    ),
    "task": SearchSource(
        label="Tâches",
        model_label="planner.Task",
        owner=lambda o: o.owner,
        title=lambda o: o.title,
        body=lambda o: _joined(
            o.description,
            o.get_status_display(),
            o.unit.title if o.unit_id else "",
            o.competency.title if o.competency_id else "",
            o.assessment.title if o.assessment_id else "",
        ),
        url=lambda o: reverse("planner:task_edit", args=[o.pk]),
    ),
    "event": SearchSource(
        label="Agenda",
        model_label="planner.CalendarEvent",
        owner=lambda o: o.owner,
        title=lambda o: o.title,
        body=lambda o: _joined(
            o.description,
            o.location,
            o.unit.title if o.unit_id else "",
            o.competency.title if o.competency_id else "",
            o.assessment.title if o.assessment_id else "",
        ),
        url=lambda o: reverse("planner:event_edit", args=[o.pk]),
    ),
    "path": SearchSource(
        label="Formations",
        model_label="formations.LearningPath",
        owner=lambda o: o.owner,
        title=lambda o: o.title,
        body=lambda o: _joined(o.description, o.training_type, o.level_label),
        url=lambda o: reverse("formations:detail", args=[o.pk]),
    ),
    "unit": SearchSource(
        label="Matières",
        model_label="formations.LearningUnit",
        owner=lambda o: o.period.path.owner,
        title=lambda o: o.title,
        body=lambda o: _joined(o.description, o.period.title, o.period.path.title, o.group.title if o.group else ""),
        url=lambda o: reverse("formations:unit", args=[o.pk]),
    ),
    "competency": SearchSource(
        label="Compétences",
        model_label="formations.Competency",
        owner=lambda o: o.path.owner,
        title=lambda o: o.title,
        # Les matières où elle se travaille entrent dans le corps : chercher « topologie »
        # doit ramener ses compétences, même si l'intitulé ne contient pas le mot.
        body=lambda o: _joined(
            o.description,
            o.period.title if o.period_id else "",
            o.path.title,
            *[link.unit.title for link in o.unit_links.select_related("unit")],
        ),
        # La compétence a sa propre page : la recherche y mène directement, au lieu de
        # renvoyer vers sa matière et de laisser l'utilisateur la retrouver dans une liste.
        url=lambda o: reverse("formations:competency", args=[o.pk]),
    ),
    "group": SearchSource(
        label="Regroupements",
        model_label="formations.LearningGroup",
        owner=lambda o: o.period.path.owner,
        title=lambda o: str(o),
        body=lambda o: _joined(o.kind, o.period.title, o.period.path.title),
        url=lambda o: f"{reverse('formations:detail', args=[o.period.path_id])}#periode-{o.period_id}",
    ),
    "assessment": SearchSource(
        label="Évaluations",
        model_label="formations.Assessment",
        owner=lambda o: o.owner,
        title=lambda o: o.title,
        body=lambda o: _joined(
            o.get_kind_display(),
            o.get_status_display(),
            o.description,
            o.period.title if o.period_id else "",
            o.unit.title if o.unit_id else "",
            o.unit.period.path.title if o.unit_id else (o.period.path.title if o.period_id else ""),
            *o.competencies.values_list("title", flat=True),
        ),
        url=lambda o: reverse("formations:assessment", args=[o.pk]),
    ),
    "result": SearchSource(
        label="Résultats",
        model_label="formations.AssessmentResult",
        owner=lambda o: o.assessment.owner,
        title=lambda o: f"Résultat · {o.assessment.title}",
        body=lambda o: _joined(
            "Absent" if o.absent else (f"{o.score:f} sur {o.scale:f}" if o.score is not None else "Sans note"),
            o.comment,
            o.self_review,
            o.assessment.unit.title if o.assessment.unit_id else "",
            o.assessment.period.title if o.assessment.period_id else "",
            (
                o.assessment.unit.period.path.title
                if o.assessment.unit_id
                else (o.assessment.period.path.title if o.assessment.period_id else "")
            ),
        ),
        url=lambda o: reverse("formations:assessment", args=[o.assessment_id]),
    ),
}


def source_for(instance) -> tuple[str, SearchSource] | tuple[None, None]:
    label = instance._meta.label
    for key, source in SOURCES.items():
        if source.model_label == label:
            return key, source
    return None, None


def supports_full_text(model) -> bool:
    """PostgreSQL fournit tsvector ; SQLite (développement local) retombe sur ``icontains``."""
    return connections[router.db_for_read(model) or "default"].vendor == "postgresql"


def index_instance(instance, *, refresh: bool = True) -> int | None:
    """Projette un objet dans l'index. Rend la clé de l'entrée écrite, ou ``None``.

    ``refresh=False`` diffère le calcul du vecteur : quand on réindexe une famille
    entière, un seul ``UPDATE`` groupé remplace autant de requêtes qu'il y avait
    d'objets.
    """
    from core.models import SearchEntry

    key, source = source_for(instance)
    if source is None:
        return None
    try:
        owner = source.owner(instance)
    except Exception:  # noqa: BLE001 — un parent supprimé ne doit jamais casser un save()
        return None
    if owner is None:
        return None
    entry, _ = SearchEntry.objects.update_or_create(
        object_type=key,
        object_id=instance.pk,
        defaults={
            "owner": owner,
            "title": source.title(instance) or "",
            "body": source.body(instance) or "",
            "url": source.url(instance),
        },
    )
    if refresh:
        refresh_vectors(SearchEntry.objects.filter(pk=entry.pk))
    return entry.pk


def unindex_instance(instance) -> None:
    from core.models import SearchEntry

    key, source = source_for(instance)
    if source is None:
        return
    SearchEntry.objects.filter(object_type=key, object_id=instance.pk).delete()


def has_dependents(instance) -> bool:
    """L'objet a-t-il une descendance à réindexer ?

    Défini à côté de ``reindex_dependents`` pour que les deux listes ne divergent pas.
    Sert à ne pas mettre en file une tâche qui n'aurait rien à faire : la plupart des
    enregistrements — une ressource, une tâche, un résultat — ne portent le contexte de
    personne, et une file pleine de tâches vides coûte plus qu'elle ne rapporte.
    """
    from formations.models import Assessment, Competency, LearningGroup, LearningPath, LearningUnit, Period
    from library.models import Tag

    return isinstance(instance, (LearningPath, Period, LearningGroup, LearningUnit, Competency, Assessment, Tag))


def reindex_dependents(instance) -> int:
    """Répercute un changement de contexte dans les projections de ses descendants.

    Les entrées écrites sont collectées, puis leurs vecteurs recalculés en un seul
    ``UPDATE``. Auparavant chaque objet en coûtait un : renommer une formation de deux
    cents compétences produisait quatre cents requêtes là où il en faut désormais une
    par objet, plus une pour tout le monde.
    """
    from core.models import SearchEntry
    from formations.models import (
        Assessment,
        AssessmentResult,
        Competency,
        LearningGroup,
        LearningPath,
        LearningUnit,
        Period,
    )
    from library.models import Tag

    touched: list[int] = []

    def project(objects) -> None:
        for obj in objects:
            written = index_instance(obj, refresh=False)
            if written is not None:
                touched.append(written)

    def with_results(assessments) -> None:
        project(assessments)
        project(AssessmentResult.objects.filter(assessment__in=assessments))

    if isinstance(instance, LearningPath):
        project(LearningGroup.objects.filter(period__path=instance))
        project(LearningUnit.objects.filter(period__path=instance))
        project(instance.competencies.all())
        with_results(Assessment.objects.filter(Q(period__path=instance) | Q(unit__period__path=instance)).distinct())
    elif isinstance(instance, Period):
        project(instance.groups.all())
        project(instance.units.all())
        project(Competency.objects.filter(Q(period=instance) | Q(units__period=instance)).distinct())
        with_results(Assessment.objects.filter(Q(period=instance) | Q(unit__period=instance)).distinct())
    elif isinstance(instance, LearningGroup):
        project(instance.units.all())
    elif isinstance(instance, LearningUnit):
        project(instance.competencies.all())
        with_results(instance.assessments.all())
    elif isinstance(instance, Competency):
        with_results(instance.assessments.all())
    elif isinstance(instance, Assessment):
        if hasattr(instance, "result"):
            project([instance.result])
    elif isinstance(instance, Tag):
        project(instance.items.all())

    if touched:
        refresh_vectors(SearchEntry.objects.filter(pk__in=touched))
    return len(touched)


def refresh_vectors(queryset: QuerySet) -> None:
    """Recalcule le vecteur pondéré : le titre pèse plus lourd que le corps."""
    from core.models import SearchEntry

    if not supports_full_text(SearchEntry):
        return
    from django.contrib.postgres.search import SearchVector

    queryset.update(
        search_vector=SearchVector("title", weight="A", config=SEARCH_CONFIG)
        + SearchVector("body", weight="B", config=SEARCH_CONFIG)
    )


def search(user, query: str, object_type: str | None = None) -> QuerySet:
    from core.models import SearchEntry

    entries = SearchEntry.objects.filter(owner=user)
    if object_type in SOURCES:
        entries = entries.filter(object_type=object_type)
    query = (query or "").strip()
    if not query:
        return entries.none()
    matches, search_query = _matching(entries, query)
    if search_query is None:
        return matches.order_by("-updated_at")
    from django.contrib.postgres.search import SearchRank

    # `F(...)` est indispensable : passé sous forme de chaîne, SearchRank ré-encoderait
    # la colonne avec `to_tsvector()` et perdrait la pondération déjà stockée.
    return matches.annotate(rank=SearchRank(F("search_vector"), search_query)).order_by("-rank", "-updated_at")


def _matching(entries: QuerySet, query: str):
    """Les entrées qui répondent à la requête, sans classement, et la requête plein texte
    quand la base en dispose — le classement et le décompte partent du même filtre."""
    from core.models import SearchEntry

    if supports_full_text(SearchEntry):
        from django.contrib.postgres.search import SearchQuery

        # `websearch` accepte la syntaxe que les utilisateurs connaissent déjà :
        # guillemets pour une expression exacte, `-` pour exclure, `or` pour alterner.
        search_query = SearchQuery(query, config=SEARCH_CONFIG, search_type="websearch")
        return entries.filter(search_vector=search_query), search_query
    return entries.filter(Q(title__icontains=query) | Q(body__icontains=query)), None


def count_by_type(user, query: str) -> dict[str, int]:
    """Le nombre de résultats de chaque type, pour les filtres : une seule agrégation, sans
    le calcul de pertinence, et indépendante du filtre de type en cours."""
    from core.models import SearchEntry

    query = (query or "").strip()
    if not query:
        return {}
    matches, _ = _matching(SearchEntry.objects.filter(owner=user), query)
    return dict(
        matches.order_by().values("object_type").annotate(total=Count("pk")).values_list("object_type", "total")
    )


EXCERPT_WIDTH = 220
# Un mot, ou une expression entre guillemets, éventuellement précédés du `-` qui exclut.
_QUERY_TOKEN = re.compile(r'-?"[^"]*"?|\S+')


def query_terms(query: str) -> list[str]:
    """Les termes à surligner : ceux que la recherche cherche vraiment.

    Une expression entre guillemets reste entière ; un terme exclu par `-` et l'opérateur
    `or` ne sont jamais marqués, puisque les résultats ne les contiennent pas pour cela.
    Les plus longs d'abord, pour qu'« espace compact » l'emporte sur « espace ».
    """
    seen: set[str] = set()
    terms: list[str] = []
    for token in _QUERY_TOKEN.findall(query or ""):
        if token.startswith("-") or token.casefold() == "or":
            continue
        term = " ".join(token.strip('"').split()).strip(".,;:!?()[]{}«»'")
        if len(term) >= 2 and term.casefold() not in seen:
            seen.add(term.casefold())
            terms.append(term)
    return sorted(terms, key=len, reverse=True)


def highlight_excerpt(text: str, query: str, width: int = EXCERPT_WIDTH) -> SafeString:
    """Un extrait d'environ `width` caractères autour de la première occurrence, les termes
    marqués en `<mark>`.

    Le même rendu sous PostgreSQL et SQLite : on travaille sur le texte brut de l'index, on
    cherche sur le texte non échappé puis on échappe chaque morceau — jamais l'inverse, qui
    casserait les correspondances et laisserait passer du HTML. Les variantes trouvées par
    la lemmatisation de PostgreSQL (« révisions » pour « révision ») ne sont pas marquées :
    l'extrait les montre sans les surligner.
    """
    text = " ".join((text or "").split())
    terms = query_terms(query)
    pattern = re.compile("|".join(re.escape(term) for term in terms), re.IGNORECASE) if terms else None
    first = pattern.search(text) if pattern else None

    start = 0
    if first and first.start() > width // 3:
        cut = first.start() - width // 3
        space = text.find(" ", cut, first.start())
        start = space + 1 if space != -1 else cut
    end = min(len(text), start + width)
    if end < len(text):
        space = text.rfind(" ", start, end)
        if space > start and (first is None or space >= first.end()):
            end = space

    snippet = text[start:end]
    parts: list[str] = []
    position = 0
    if pattern:
        for match in pattern.finditer(snippet):
            parts.append(escape(snippet[position : match.start()]))
            parts.append(f"<mark>{escape(match.group())}</mark>")
            position = match.end()
    parts.append(escape(snippet[position:]))
    return mark_safe(("…" if start else "") + "".join(parts) + ("…" if end < len(text) else ""))


def reindex_all() -> dict[str, int]:
    """Reconstruit l’index de bout en bout. À exécuter après ``import_legacy``."""
    from core.models import SearchEntry

    counts: dict[str, int] = {}
    for key, source in SOURCES.items():
        SearchEntry.objects.filter(object_type=key).delete()
        indexed = 0
        for instance in source.model.objects.all().iterator():
            index_instance(instance)
            indexed += 1
        counts[key] = indexed
    return counts
