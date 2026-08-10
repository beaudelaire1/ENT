from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class OwnedQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(owner=user)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SearchEntry(models.Model):
    """Projection consultable d’un objet, alimentée par ``core.search``.

    Une seule table pour toute l’application : la recherche globale devient une requête
    indexée et classée par pertinence, au lieu d’un ``LIKE`` par modèle.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_entries")
    object_type = models.CharField(max_length=32)
    object_id = models.PositiveBigIntegerField()
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=300)
    search_vector = SearchVectorField(null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "entrée de recherche"
        verbose_name_plural = "entrées de recherche"
        constraints = [
            models.UniqueConstraint(fields=["object_type", "object_id"], name="unique_search_entry_per_object")
        ]
        indexes = [
            models.Index(fields=["owner", "object_type"], name="search_owner_type_idx"),
            # Index GIN : créé uniquement sous PostgreSQL, cf. la migration 0002.
            GinIndex(fields=["search_vector"], name="search_vector_gin_idx"),
        ]

    @property
    def type_label(self):
        from core.search import SOURCES

        source = SOURCES.get(self.object_type)
        return source.label if source else self.object_type

    def __str__(self):
        return self.title
