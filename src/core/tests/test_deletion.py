from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.deletion import cascade_summary
from formations.models import Competency, LearningPath, LearningUnit, Period, ProgressRecord
from library.models import Folder, LibraryItem, Tag
from planner.models import Task


class CascadeSummaryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.path = LearningPath.objects.create(owner=self.user, title="L3")
        period = Period.objects.create(path=self.path, title="Semestre 5")
        unit = LearningUnit.objects.create(period=period, title="TOPOLOGIE")
        for title in ("Compacité", "Connexité"):
            competency = Competency.objects.create(unit=unit, title=title)
            ProgressRecord.objects.create(owner=self.user, competency=competency)

    def test_the_summary_counts_what_will_disappear(self):
        summary = dict(cascade_summary(self.path))

        self.assertEqual(summary["période"], 1)
        self.assertEqual(summary["module"], 1)
        self.assertEqual(summary["compétences"], 2)
        self.assertEqual(summary["progressions"], 2)

    def test_an_object_without_children_has_an_empty_summary(self):
        tag = Tag.objects.create(owner=self.user, name="cours")
        self.assertEqual(cascade_summary(tag), [])


class DeletionViewTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user("alice", password="secret")
        self.bob = get_user_model().objects.create_user("bob", password="secret")
        self.client.force_login(self.alice)

    def test_a_get_only_asks_for_confirmation(self):
        task = Task.objects.create(owner=self.alice, title="À supprimer")

        response = self.client.get(reverse("planner:task_delete", args=[task.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "définitive")
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_a_post_deletes(self):
        task = Task.objects.create(owner=self.alice, title="À supprimer")

        response = self.client.post(reverse("planner:task_delete", args=[task.pk]))

        self.assertRedirects(response, reverse("planner:tasks"))
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_another_users_object_cannot_be_deleted(self):
        foreign = Task.objects.create(owner=self.bob, title="Privé")

        self.assertEqual(self.client.get(reverse("planner:task_delete", args=[foreign.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("planner:task_delete", args=[foreign.pk])).status_code, 404)
        self.assertTrue(Task.objects.filter(pk=foreign.pk).exists())

    def test_deleting_a_folder_keeps_its_items(self):
        folder = Folder.objects.create(owner=self.alice, name="Cours")
        item = LibraryItem.objects.create(
            owner=self.alice, folder=folder, kind=LibraryItem.Kind.LINK, title="Lien", url="https://example.com"
        )

        self.client.post(reverse("library:folder_delete", args=[folder.pk]))

        item.refresh_from_db()
        self.assertIsNone(item.folder)

    def test_deleting_a_formation_removes_its_whole_tree(self):
        path = LearningPath.objects.create(owner=self.alice, title="L3")
        period = Period.objects.create(path=path, title="S5")
        unit = LearningUnit.objects.create(period=period, title="Module")
        Competency.objects.create(unit=unit, title="Compétence")

        self.client.post(reverse("formations:delete", args=[path.pk]))

        self.assertEqual(LearningPath.objects.count(), 0)
        self.assertEqual(Competency.objects.count(), 0)


@override_settings(MEDIA_ROOT="/tmp/myent-test-media")
class FileCleanupTests(TestCase):
    def test_deleting_an_item_removes_its_file_from_storage(self):
        user = get_user_model().objects.create_user("alice", password="secret")
        item = LibraryItem.objects.create(
            owner=user,
            kind=LibraryItem.Kind.FILE,
            title="Document",
            file=SimpleUploadedFile("notes.txt", b"contenu"),
        )
        storage, name = item.file.storage, item.file.name
        self.assertTrue(storage.exists(name))

        item.delete()

        self.assertFalse(storage.exists(name))
