"""Index de recherche unifié.

Chaque modèle consultable déclare ici comment il se projette dans une ligne de
``SearchEntry`` : titre, corps, adresse. Les signaux tiennent l’index à jour, et la
vue de recherche interroge une seule table indexée plutôt que d’enchaîner un
``LIKE '%…%'`` par modèle — un balayage séquentiel qu’aucun index ne peut servir.

Ajouter un modèle à la recherche globale consiste à ajouter une entrée à ``SOURCES``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.apps import apps
from django.db import connections, router
from django.db.models import F, Q, QuerySet
from django.urls import reverse

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
        body=lambda o: _joined(o.description, o.note_text, o.provider_name, o.source_category),
        url=lambda o: reverse("library:detail", args=[o.pk]),
    ),
    "task": SearchSource(
        label="Tâches",
        model_label="planner.Task",
        owner=lambda o: o.owner,
        title=lambda o: o.title,
        body=lambda o: _joined(o.description, o.get_status_display()),
        url=lambda o: reverse("planner:task_edit", args=[o.pk]),
    ),
    "event": SearchSource(
        label="Agenda",
        model_label="planner.CalendarEvent",
        owner=lambda o: o.owner,
        title=lambda o: o.title,
        body=lambda o: _joined(o.description, o.location),
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


def index_instance(instance) -> None:
    from core.models import SearchEntry

    key, source = source_for(instance)
    if source is None:
        return
    try:
        owner = source.owner(instance)
    except Exception:  # noqa: BLE001 — un parent supprimé ne doit jamais casser un save()
        return
    if owner is None:
        return
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
    refresh_vectors(SearchEntry.objects.filter(pk=entry.pk))


def unindex_instance(instance) -> None:
    from core.models import SearchEntry

    key, source = source_for(instance)
    if source is None:
        return
    SearchEntry.objects.filter(object_type=key, object_id=instance.pk).delete()


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
    if supports_full_text(SearchEntry):
        from django.contrib.postgres.search import SearchQuery, SearchRank

        # `websearch` accepte la syntaxe que les utilisateurs connaissent déjà :
        # guillemets pour une expression exacte, `-` pour exclure, `or` pour alterner.
        search_query = SearchQuery(query, config=SEARCH_CONFIG, search_type="websearch")
        # `F(...)` est indispensable : passé sous forme de chaîne, SearchRank ré-encoderait
        # la colonne avec `to_tsvector()` et perdrait la pondération déjà stockée.
        return (
            entries.filter(search_vector=search_query)
            .annotate(rank=SearchRank(F("search_vector"), search_query))
            .order_by("-rank", "-updated_at")
        )
    return entries.filter(Q(title__icontains=query) | Q(body__icontains=query)).order_by("-updated_at")


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
