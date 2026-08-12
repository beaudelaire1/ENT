from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models import OwnedQuerySet, TimeStampedModel


class LibraryItemQuerySet(OwnedQuerySet):
    def search(self, query):
        """Recherche sur tout ce qui identifie une ressource, étiquettes comprises.

        L'étiquette manquait : une ressource rangée sous « annale » ne se retrouvait pas
        en tapant « annale », alors que c'est précisément le mot qu'on avait choisi pour
        la désigner.
        """
        return self.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(note_text__icontains=query)
            | Q(provider_name__icontains=query)
            | Q(source_category__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()


class Folder(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library_folders")
    parent = models.ForeignKey(
        "self", verbose_name="dossier parent", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    name = models.CharField("nom", max_length=120)

    class Meta:
        verbose_name = "dossier"
        verbose_name_plural = "dossiers"
        ordering = ["name"]
        constraints = [
            # Deux contraintes sont nécessaires : `parent IS NULL` n’entre jamais en
            # conflit avec lui-même en SQL, la première laisserait donc passer autant de
            # dossiers homonymes que voulu à la racine.
            models.UniqueConstraint(
                fields=["owner", "parent", "name"],
                condition=Q(parent__isnull=False),
                name="unique_folder_name_per_parent",
            ),
            models.UniqueConstraint(
                fields=["owner", "name"],
                condition=Q(parent__isnull=True),
                name="unique_root_folder_name_per_owner",
            ),
        ]

    def clean(self):
        if self.parent and self.parent.owner_id != self.owner_id:
            raise ValidationError({"parent": "Le dossier parent appartient à un autre utilisateur."})
        if self.pk and self.parent_id == self.pk:
            raise ValidationError({"parent": "Un dossier ne peut pas être son propre parent."})
        ancestor = self.parent
        seen = set()
        while ancestor is not None and ancestor.pk not in seen:
            if self.pk and ancestor.pk == self.pk:
                raise ValidationError({"parent": "Ce choix créerait une boucle dans l’arborescence."})
            seen.add(ancestor.pk)
            ancestor = ancestor.parent

    def ancestors(self):
        """Parents de la racine au parent direct, pour les fils d'Ariane."""
        result, current, seen = [], self.parent, set()
        while current is not None and current.pk not in seen:
            seen.add(current.pk)
            result.append(current)
            current = current.parent
        return list(reversed(result))

    def descendant_ids(self):
        """Tous les descendants, sans dépendre d'une profondeur maximale."""
        result, frontier = [], [self.pk]
        while frontier:
            children = list(
                Folder.objects.filter(owner=self.owner, parent_id__in=frontier).values_list("pk", flat=True)
            )
            result.extend(children)
            frontier = children
        return result

    def __str__(self):
        return self.name


class Tag(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library_tags")
    name = models.CharField("nom", max_length=64)
    color = models.CharField("couleur", max_length=7, default="#7C6CFF")

    class Meta:
        verbose_name = "étiquette"
        verbose_name_plural = "étiquettes"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_tag_name_per_user")]

    def __str__(self):
        return self.name


def library_upload_path(instance, filename):
    clean_name = Path(filename).name
    return f"users/{instance.owner_id}/library/{clean_name}"


class LibraryItem(TimeStampedModel):
    class Kind(models.TextChoices):
        """Le type technique : sous quelle forme la ressource est stockée."""

        LINK = "link", "Lien"
        FILE = "file", "Fichier"
        NOTE = "note", "Note"

    class Purpose(models.TextChoices):
        """La nature pédagogique : à quoi la ressource sert.

        Distincte du type technique, et non un modèle de plus. Une annale est
        techniquement un fichier ; un corrigé peut être un lien. Chercher « les annales de
        topologie » n'a rien à voir avec chercher « les fichiers PDF », et confondre les
        deux obligeait à deviner la nature d'une ressource depuis son titre.
        """

        COURSE = "course", "Cours"
        SHEET = "sheet", "Fiche"
        EXERCISE = "exercise", "Exercices"
        SOLUTION = "solution", "Corrigé"
        PAST_PAPER = "past_paper", "Annale"
        VIDEO = "video", "Vidéo"
        NOTEBOOK = "notebook", "Notebook"
        TOOL = "tool", "Outil numérique"
        EXTERNAL = "external", "Lien externe"
        OTHER = "other", "Autre"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library_items")
    folder = models.ForeignKey(
        Folder, verbose_name="dossier", null=True, blank=True, on_delete=models.SET_NULL, related_name="items"
    )
    tags = models.ManyToManyField(Tag, verbose_name="étiquettes", blank=True, related_name="items")
    kind = models.CharField("type", max_length=8, choices=Kind.choices)
    purpose = models.CharField("nature", max_length=12, choices=Purpose.choices, default=Purpose.OTHER)
    title = models.CharField("titre", max_length=200)
    description = models.TextField("description", blank=True)
    url = models.URLField("adresse", max_length=1000, blank=True)
    file = models.FileField("fichier", upload_to=library_upload_path, blank=True)
    file_size = models.PositiveBigIntegerField("taille", default=0)
    mime_type = models.CharField("type MIME", max_length=120, blank=True)
    note_delta = models.JSONField(default=dict, blank=True)
    note_text = models.TextField("texte de la note", blank=True)
    note_html = models.TextField(blank=True)
    provider_name = models.CharField("source", max_length=160, blank=True)
    source_category = models.CharField("catégorie", max_length=160, blank=True)
    legacy_source = models.CharField(max_length=80, blank=True)
    legacy_id = models.CharField(max_length=80, blank=True)
    objects = LibraryItemQuerySet.as_manager()

    class Meta:
        verbose_name = "élément"
        verbose_name_plural = "éléments"
        ordering = ["-updated_at"]

    def clean(self):
        if self.folder and self.folder.owner_id != self.owner_id:
            raise ValidationError({"folder": "Ce dossier appartient à un autre utilisateur."})
        if self.kind == self.Kind.LINK and not self.url:
            raise ValidationError({"url": "Une adresse est requise pour un lien."})
        if self.kind == self.Kind.FILE and not self.file:
            raise ValidationError({"file": "Un fichier est requis."})
        if self.kind == self.Kind.NOTE and not (self.note_text or self.note_delta):
            raise ValidationError("La note ne peut pas être vide.")

    def __str__(self):
        return self.title
