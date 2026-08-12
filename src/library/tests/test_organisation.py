"""Dossiers et étiquettes : renommer sans perdre ce qu'ils rangent.

Un dossier mal orthographié ne se corrigeait pas. Le supprimer détachait ses ressources
— `folder` est mis à NULL, pas supprimé — mais le rangement était perdu, et une étiquette
supprimée disparaissait de tous les éléments qui la portaient.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from library.models import Folder, LibraryItem, Tag


class FolderAndTagEditingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.folder = Folder.objects.create(owner=self.user, name="Mathematiques")
        self.tag = Tag.objects.create(owner=self.user, name="analyse")
        self.item = LibraryItem.objects.create(
            owner=self.user, kind=LibraryItem.Kind.NOTE, title="Fiche", note_text="x", folder=self.folder
        )
        self.item.tags.add(self.tag)

    def test_a_folder_can_be_renamed_and_keeps_its_items(self):
        response = self.client.post(reverse("library:folder_edit", args=[self.folder.pk]), {"name": "Mathématiques"})

        self.assertRedirects(response, f"{reverse('library:list')}?folder={self.folder.pk}")
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, "Mathématiques")
        self.item.refresh_from_db()
        self.assertEqual(self.item.folder_id, self.folder.pk)

    def test_a_tag_can_be_renamed_and_stays_attached(self):
        response = self.client.post(
            reverse("library:tag_edit", args=[self.tag.pk]), {"name": "Analyse réelle", "color": "#123456"}
        )

        self.assertRedirects(response, f"{reverse('library:list')}?tag={self.tag.pk}")
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, "Analyse réelle")
        self.assertEqual(list(self.item.tags.all()), [self.tag])

    def test_a_duplicate_folder_name_is_a_form_error(self):
        Folder.objects.create(owner=self.user, name="Physique")
        response = self.client.post(reverse("library:folder_edit", args=[self.folder.pk]), {"name": "Physique"})
        self.assertEqual(response.status_code, 200)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, "Mathematiques")

    def test_a_folder_cannot_become_its_own_parent(self):
        response = self.client.post(
            reverse("library:folder_edit", args=[self.folder.pk]),
            {"name": "Mathematiques", "parent": self.folder.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "son propre parent")

    def test_the_list_offers_an_edit_link_for_each_folder_and_tag(self):
        response = self.client.get(reverse("library:list"))
        self.assertContains(response, reverse("library:folder_edit", args=[self.folder.pk]))
        self.assertContains(response, reverse("library:tag_edit", args=[self.tag.pk]))

    def test_another_users_folder_and_tag_are_out_of_reach(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign_folder = Folder.objects.create(owner=bob, name="Privé")
        foreign_tag = Tag.objects.create(owner=bob, name="privé")
        self.assertEqual(self.client.get(reverse("library:folder_edit", args=[foreign_folder.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("library:tag_edit", args=[foreign_tag.pk])).status_code, 404)

    def test_an_item_page_shows_its_folder_in_the_trail(self):
        response = self.client.get(reverse("library:detail", args=[self.item.pk]))
        self.assertContains(response, "Fil d’Ariane")
        self.assertContains(response, f"{reverse('library:list')}?folder={self.folder.pk}")
