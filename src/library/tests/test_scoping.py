from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from library.models import Folder, Tag


class ScopedUniquenessTests(TestCase):
    """Les doublons doivent produire une erreur de formulaire, jamais une erreur 500.

    Le propriétaire n’étant pas exposé dans le formulaire, Django l’excluait de la
    validation et les contraintes qui le mentionnent n’étaient appliquées que par la
    base : le doublon remontait en IntegrityError.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def test_duplicate_tag_is_a_form_error(self):
        Tag.objects.create(owner=self.user, name="cours")
        response = self.client.post(reverse("library:tag_new"), {"name": "cours", "color": "#7C6CFF"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tag.objects.filter(owner=self.user, name="cours").count(), 1)

    def test_duplicate_root_folder_is_rejected(self):
        Folder.objects.create(owner=self.user, name="dossier")
        response = self.client.post(reverse("library:folder_new"), {"name": "dossier"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Folder.objects.filter(owner=self.user, name="dossier").count(), 1)

    def test_duplicate_child_folder_is_rejected(self):
        parent = Folder.objects.create(owner=self.user, name="parent")
        Folder.objects.create(owner=self.user, parent=parent, name="enfant")
        response = self.client.post(reverse("library:folder_new"), {"name": "enfant", "parent": parent.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Folder.objects.filter(owner=self.user, parent=parent, name="enfant").count(), 1)

    def test_same_name_is_allowed_for_another_user(self):
        other = get_user_model().objects.create_user("bob", password="secret")
        Tag.objects.create(owner=other, name="cours")
        Folder.objects.create(owner=other, name="dossier")
        tag_response = self.client.post(reverse("library:tag_new"), {"name": "cours", "color": "#7C6CFF"})
        self.assertEqual(tag_response.status_code, 302)
        self.assertEqual(self.client.post(reverse("library:folder_new"), {"name": "dossier"}).status_code, 302)
