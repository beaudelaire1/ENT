from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from formations.models import (
    Competency,
    LearningPath,
    LearningUnit,
    MetricDefinition,
    MetricValue,
    Period,
    ProgressRecord,
)
from formations.services import build_tracking_grid, ensure_progress_records, tracked_records


class TrackingGridTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.unit = LearningUnit.objects.create(period=self.period, title="TOPOLOGIE", order=1)
        self.competencies = [
            Competency.objects.create(unit=self.unit, title="Espaces métriques et topologiques", order=1),
            Competency.objects.create(unit=self.unit, title="Compacité et connexité", order=2),
        ]
        coefficient = MetricDefinition.objects.create(path=self.path, key="coefficient", label="Coefficient")
        MetricValue.objects.create(definition=coefficient, unit=self.unit, value=Decimal("5"))

    def url(self):
        return reverse("formations:tracking", args=[self.path.pk])

    def test_grid_creates_one_record_per_competency(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProgressRecord.objects.filter(owner=self.user).count(), 2)

    def test_grid_shows_units_competencies_and_metrics(self):
        response = self.client.get(self.url())
        self.assertContains(response, "TOPOLOGIE")
        self.assertContains(response, "Espaces métriques et topologiques")
        self.assertContains(response, "Semestre 5")

    def test_visiting_twice_does_not_duplicate_records(self):
        self.client.get(self.url())
        self.client.get(self.url())
        self.assertEqual(ProgressRecord.objects.filter(owner=self.user).count(), 2)

    def test_saving_the_grid_persists_every_row(self):
        self.client.get(self.url())
        records = list(tracked_records(self.user, self.path))
        data = {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "2",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        for index, record in enumerate(records):
            data[f"form-{index}-id"] = str(record.pk)
            data[f"form-{index}-planned_hours"] = "10"
            data[f"form-{index}-actual_hours"] = "4"
            data[f"form-{index}-mastery_level"] = "3"
            data[f"form-{index}-notes"] = "Revoir les exercices"

        response = self.client.post(self.url(), data)

        self.assertRedirects(response, self.url())
        saved = ProgressRecord.objects.filter(owner=self.user)
        self.assertEqual(saved.count(), 2)
        for record in saved:
            self.assertEqual(record.mastery_level, 3)
            self.assertEqual(record.planned_hours, Decimal("10"))
            self.assertEqual(record.actual_hours, Decimal("4"))
            self.assertEqual(record.notes, "Revoir les exercices")

    def test_an_invalid_level_is_rejected(self):
        self.client.get(self.url())
        record = tracked_records(self.user, self.path).first()
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": str(record.pk),
            "form-0-planned_hours": "0",
            "form-0-actual_hours": "0",
            "form-0-mastery_level": "9",
            "form-0-notes": "",
        }
        response = self.client.post(self.url(), data)
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.mastery_level, 0)

    def test_totals_are_computed_from_the_competencies(self):
        self.client.get(self.url())
        records = list(tracked_records(self.user, self.path))
        records[0].mastery_level = 4
        records[0].planned_hours = Decimal("10")
        records[0].actual_hours = Decimal("6")
        records[0].save()
        records[1].mastery_level = 2
        records[1].planned_hours = Decimal("5")
        records[1].save()

        response = self.client.get(self.url())
        grid = build_tracking_grid(self.path, response.context["formset"])
        unit_totals = grid[0]["units"][0]["totals"]

        self.assertEqual(unit_totals["planned"], Decimal("15"))
        self.assertEqual(unit_totals["actual"], Decimal("6"))
        self.assertEqual(unit_totals["percent"], 75)
        self.assertEqual(grid[0]["totals"]["percent"], 75)

    def test_the_grid_follows_the_declared_order_not_the_alphabet(self):
        LearningUnit.objects.create(period=self.period, title="ALGÈBRE", order=2)
        Competency.objects.create(unit=self.unit, title="Axiomes", order=3)

        response = self.client.get(self.url())
        grid = build_tracking_grid(self.path, response.context["formset"])
        units = [unit["unit"].title for unit in grid[0]["units"]]
        titles = [row["competency"].title for row in grid[0]["units"][0]["rows"]]

        self.assertEqual(units, ["TOPOLOGIE", "ALGÈBRE"])
        self.assertEqual(titles, ["Espaces métriques et topologiques", "Compacité et connexité", "Axiomes"])

    def test_a_unit_without_competency_still_appears(self):
        LearningUnit.objects.create(period=self.period, title="CALCUL SCIENTIFIQUE", order=2)
        response = self.client.get(self.url())
        self.assertContains(response, "CALCUL SCIENTIFIQUE")

    def test_another_users_path_is_not_reachable(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign = LearningPath.objects.create(owner=bob, title="Privé")
        self.assertEqual(self.client.get(reverse("formations:tracking", args=[foreign.pk])).status_code, 404)

    def test_records_are_never_created_for_another_user(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        ensure_progress_records(bob, self.path)
        self.assertEqual(ProgressRecord.objects.filter(owner=self.user).count(), 0)
        self.assertEqual(ProgressRecord.objects.filter(owner=bob).count(), 2)
