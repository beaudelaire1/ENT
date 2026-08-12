"""Matérialisation des recommandations dans la bibliothèque personnelle.

Le catalogue éditorial décrit les bonnes ressources une seule fois. Ce service en fait
des ``LibraryItem`` ordinaires et les rattache aux compétences : une recommandation
devient ainsi réellement disponible dans « Ma bibliothèque », classable et réutilisable.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from library.models import LibraryItem

from .curated_resources import CuratedResource, recommendations_for

# Les trois premières recommandations de géométrie décrivaient par erreur les courbes et
# surfaces. Réutiliser leurs lignes de bibliothèque évite trois doublons et garantit que
# les liens obsolètes disparaissent lors de la prochaine synchronisation.
CURATED_KEY_ALIASES = {
    "geometry_affine_course_lyon": ("geometry_course_exercises_saclay",),
    "geometry_affine_practice_lyon": ("geometry_interactive_unisciel",),
    "geometry_affine_summary_lyon": ("geometry_advanced_ens",),
}


@dataclass
class ResourceSyncResult:
    created: int = 0
    updated: int = 0
    attached: int = 0
    detached: int = 0

    def add(self, other: "ResourceSyncResult") -> None:
        self.created += other.created
        self.updated += other.updated
        self.attached += other.attached
        self.detached += other.detached


def _managed_defaults(resource: CuratedResource) -> dict:
    return {
        "kind": LibraryItem.Kind.LINK,
        "purpose": resource.purpose,
        "title": resource.title,
        "description": resource.description,
        "url": resource.url,
        "provider_name": resource.provider,
        "source_category": f"Parcours recommandé · {resource.role_label} · {resource.language_label}",
        "legacy_source": "curated",
        "legacy_id": resource.key,
    }


def _get_or_create_item(owner, resource: CuratedResource) -> tuple[LibraryItem, bool, bool]:
    """Retourne l'élément canonique sans écraser un lien personnel trouvé par URL."""
    known_keys = (resource.key, *CURATED_KEY_ALIASES.get(resource.key, ()))
    item = LibraryItem.objects.filter(
        owner=owner,
        legacy_source="curated",
        legacy_id__in=known_keys,
    ).first()
    if item is not None:
        defaults = _managed_defaults(resource)
        changed = any(getattr(item, field) != value for field, value in defaults.items())
        if changed:
            for field, value in defaults.items():
                setattr(item, field, value)
            item.save(update_fields=[*defaults, "updated_at"])
        return item, False, changed

    # Un étudiant peut avoir enregistré le même lien lui-même. Dans ce cas on le
    # réutilise tel quel : son titre, son classement et sa description lui appartiennent.
    personal = LibraryItem.objects.filter(owner=owner, url=resource.url).first()
    if personal is not None:
        return personal, False, False

    return LibraryItem.objects.create(owner=owner, **_managed_defaults(resource)), True, False


@transaction.atomic
def attach_curated_recommendations(*, owner, competency, replace_managed: bool = False) -> ResourceSyncResult:
    """Crée et rattache le parcours conseillé d'une compétence, sans doublons."""
    unit_titles = list(competency.units.values_list("title", flat=True))
    recommendations = recommendations_for(competency.title, unit_titles)
    result = ResourceSyncResult()
    desired_ids: set[int] = set()

    for recommendation in recommendations:
        item, created, updated = _get_or_create_item(owner, recommendation)
        desired_ids.add(item.pk)
        result.created += int(created)
        result.updated += int(updated)
        if not competency.resources.filter(pk=item.pk).exists():
            competency.resources.add(item)
            result.attached += 1

    if replace_managed:
        obsolete = list(
            competency.resources.filter(owner=owner, legacy_source="curated")
            .exclude(pk__in=desired_ids)
            .values_list("pk", flat=True)
        )
        if obsolete:
            competency.resources.remove(*obsolete)
            result.detached += len(obsolete)
    return result


@transaction.atomic
def sync_path_curated_resources(*, owner, path, competency_titles: set[str] | None = None) -> ResourceSyncResult:
    """Alimente bibliothèque et rattachements pour tout le périmètre actif d'un parcours."""
    competencies = path.competencies.prefetch_related("unit_links__unit").all()
    if competency_titles is not None:
        competencies = competencies.filter(title__in=competency_titles)

    competencies = list(competencies)
    total = ResourceSyncResult()
    recommendations_by_competency: dict[int, list[CuratedResource]] = {}
    resources_by_key: dict[str, CuratedResource] = {}
    for competency in competencies:
        unit_titles = [link.unit.title for link in competency.unit_links.all()]
        recommendations = recommendations_for(competency.title, unit_titles)
        recommendations_by_competency[competency.pk] = recommendations
        resources_by_key.update((resource.key, resource) for resource in recommendations)

    items_by_key: dict[str, LibraryItem] = {}
    for key, resource in resources_by_key.items():
        item, created, updated = _get_or_create_item(owner, resource)
        items_by_key[key] = item
        total.created += int(created)
        total.updated += int(updated)

    desired_pairs = {
        (competency_id, items_by_key[resource.key].pk)
        for competency_id, recommendations in recommendations_by_competency.items()
        for resource in recommendations
    }
    competency_ids = [competency.pk for competency in competencies]
    through = type(competencies[0]).resources.through if competencies else None
    if through is None:
        return total

    present_pairs = set(
        through.objects.filter(competency_id__in=competency_ids).values_list("competency_id", "libraryitem_id")
    )
    missing_pairs = desired_pairs - present_pairs
    if missing_pairs:
        through.objects.bulk_create(
            [through(competency_id=competency_id, libraryitem_id=item_id) for competency_id, item_id in missing_pairs],
            ignore_conflicts=True,
        )
        total.attached = len(missing_pairs)

    managed_ids = set(LibraryItem.objects.filter(owner=owner, legacy_source="curated").values_list("pk", flat=True))
    obsolete_pairs = (present_pairs - desired_pairs) & {
        (competency_id, item_id) for competency_id, item_id in present_pairs if item_id in managed_ids
    }
    if obsolete_pairs:
        obsolete_pks = [
            pk
            for pk, competency_id, item_id in through.objects.filter(
                competency_id__in=competency_ids,
                libraryitem_id__in=managed_ids,
            ).values_list("pk", "competency_id", "libraryitem_id")
            if (competency_id, item_id) in obsolete_pairs
        ]
        through.objects.filter(pk__in=obsolete_pks).delete()
        total.detached = len(obsolete_pks)
    return total
