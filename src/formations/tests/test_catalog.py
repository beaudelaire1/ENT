import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from formations.catalog import CatalogError, export_catalog, guyane_catalog, import_catalog, validate_catalog
from formations.models import Competency, LearningPath, LearningUnit
from library.models import LibraryItem


def small_catalog():
    return {
        "schema": "myent.learning-path",
        "version": 1,
        "metadata": {"name": "Test"},
        "formation": {
            "title": "Licence test",
            "level_label": "L3",
            "current_period": "s5",
            "weight_metric": "ects",
        },
        "metrics": [{"key": "ects", "label": "ECTS", "decimal_places": 0, "min_value": "0"}],
        "periods": [
            {
                "key": "s5",
                "title": "Semestre 5",
                "groups": [{"key": "ue1", "title": "UE 1", "kind": "UE"}],
                "units": [
                    {
                        "key": "topologie",
                        "title": "Topologie",
                        "group": "ue1",
                        "metrics": {"ects": "5"},
                    }
                ],
            }
        ],
        "competencies": [
            {
                "key": "ouverts",
                "title": "Reconnaître un ouvert",
                "period": "s5",
                "planned_hours": "2.5",
                "units": [{"unit": "topologie", "is_primary": True}],
            }
        ],
    }


class CatalogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")

    def test_validate_returns_preview_without_writing(self):
        preview = validate_catalog(small_catalog())
        self.assertEqual(preview["units"], 1)
        self.assertEqual(preview["competencies"], 1)
        self.assertFalse(LearningPath.objects.exists())

    def test_invalid_reference_is_rejected_before_writing(self):
        data = small_catalog()
        data["competencies"][0]["units"][0]["unit"] = "absente"
        with self.assertRaises(CatalogError):
            import_catalog(data, owner=self.user)
        self.assertFalse(LearningPath.objects.exists())

    def test_import_and_export_round_trip_structure(self):
        path = import_catalog(small_catalog(), owner=self.user, academic_year="2026-2027")
        self.assertEqual(path.current_period.title, "Semestre 5")
        self.assertEqual(path.academic_year, "2026-2027")
        self.assertEqual(LearningUnit.objects.filter(period__path=path).count(), 1)
        self.assertEqual(Competency.objects.filter(path=path).count(), 1)
        competency = Competency.objects.get(path=path)
        self.assertEqual(LibraryItem.objects.filter(owner=self.user, legacy_source="curated").count(), 3)
        self.assertEqual(competency.resources.count(), 3)

        copy = import_catalog(export_catalog(path), owner=self.user, title="Copie")
        self.assertEqual(copy.periods.count(), 1)
        self.assertEqual(copy.competencies.count(), 1)
        self.assertEqual(copy.competencies.get().resources.count(), 3)
        self.assertEqual(LibraryItem.objects.filter(owner=self.user, legacy_source="curated").count(), 3)
        self.assertNotEqual(copy.pk, path.pk)

    def test_official_template_obeys_public_schema(self):
        preview = validate_catalog(guyane_catalog())
        self.assertEqual(preview["periods"], 2)
        self.assertGreater(preview["units"], 10)
        self.assertGreater(preview["competencies"], 100)


class CatalogViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)

    def test_import_requires_preview_then_confirmation(self):
        payload = json.dumps(small_catalog()).encode()
        response = self.client.post(
            reverse("formations:import"),
            {"catalog": self._file(payload)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APERÇU VALIDÉ")
        self.assertFalse(LearningPath.objects.exists())

        response = self.client.post(
            reverse("formations:import"),
            {"confirm": "1", "payload": payload.decode(), "title": "Mon import", "academic_year": "2026-2027"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LearningPath.objects.filter(owner=self.user, title="Mon import").exists())

    def test_export_of_another_user_is_hidden(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign = LearningPath.objects.create(owner=bob, title="Privée")
        self.assertEqual(self.client.get(reverse("formations:export", args=[foreign.pk])).status_code, 404)

    @staticmethod
    def _file(content):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile("formation.json", content, content_type="application/json")
