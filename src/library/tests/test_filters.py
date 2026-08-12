from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from formations.models import Competency, LearningPath, LearningUnit, Period, UnitCompetency
from library.forms import LibraryItemForm
from library.models import Folder, LibraryItem, Tag


class LibraryFiltersTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.parent = Folder.objects.create(owner=self.user, name="Mathématiques")
        self.child = Folder.objects.create(owner=self.user, parent=self.parent, name="Topologie")
        self.tag = Tag.objects.create(owner=self.user, name="partiel")
        self.path = LearningPath.objects.create(owner=self.user, title="L3")
        self.period = Period.objects.create(path=self.path, title="S5")
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie")
        self.competency = Competency.objects.create(path=self.path, period=self.period, title="Compacité")
        UnitCompetency.objects.create(unit=self.unit, competency=self.competency)
        self.item = LibraryItem.objects.create(
            owner=self.user,
            folder=self.child,
            kind=LibraryItem.Kind.FILE,
            purpose=LibraryItem.Purpose.PAST_PAPER,
            title="Partiel de compacité",
            file="users/1/library/partiel.pdf",
        )
        self.item.tags.add(self.tag)
        self.item.learning_units.add(self.unit)
        self.item.competencies.add(self.competency)

    def test_filters_are_cumulative(self):
        response = self.client.get(
            reverse("library:list"),
            {
                "q": "compacité",
                "folder": self.parent.pk,
                "tag": self.tag.pk,
                "kind": "file",
                "purpose": "past_paper",
                "unit": self.unit.pk,
                "competency": self.competency.pk,
            },
        )
        self.assertEqual(list(response.context["items"]), [self.item])
        self.assertContains(response, "1 ressource trouvée")

    def test_parent_folder_includes_descendants(self):
        response = self.client.get(reverse("library:list"), {"folder": self.parent.pk})
        self.assertContains(response, self.item.title)
        self.assertContains(response, self.child.name)

    def test_list_is_paginated_and_keeps_filters(self):
        for index in range(25):
            LibraryItem.objects.create(
                owner=self.user, kind=LibraryItem.Kind.NOTE, title=f"Note {index:02}", note_text="contenu"
            )
        response = self.client.get(reverse("library:list"), {"kind": "note"})
        self.assertEqual(len(response.context["items"]), 24)
        self.assertContains(response, "kind=note&amp;page=2")


class FolderHierarchyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.root = Folder.objects.create(owner=self.user, name="Racine")
        self.child = Folder.objects.create(owner=self.user, parent=self.root, name="Enfant")
        self.grandchild = Folder.objects.create(owner=self.user, parent=self.child, name="Petit-enfant")

    def test_indirect_cycle_is_rejected(self):
        self.root.parent = self.grandchild
        with self.assertRaises(ValidationError):
            self.root.full_clean()

    def test_ancestors_are_ordered_from_root(self):
        self.assertEqual(self.grandchild.ancestors(), [self.root, self.child])


class DependentLibraryFormTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")

    def test_irrelevant_url_is_cleared_for_a_note(self):
        item = LibraryItem.objects.create(
            owner=self.user, kind=LibraryItem.Kind.LINK, title="Ancien lien", url="https://example.com"
        )
        form = LibraryItemForm(
            data={
                "kind": "note",
                "purpose": "course",
                "title": "Maintenant une note",
                "url": "https://example.com/stale",
                "note_delta_json": '{"ops":[{"insert":"Contenu"}]}',
                "note_text_input": "Contenu",
                "note_html_input": "<p>Contenu</p>",
            },
            instance=item,
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.url, "")
        self.assertEqual(saved.note_text, "Contenu")
