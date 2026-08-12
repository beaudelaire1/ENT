"""Le journal des niveaux et la courbe qu'il alimente."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.history import level_timeline, sparkline
from formations.models import Competency, LearningPath, Period, ProgressEvent, ProgressRecord


class JournalTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("etudiant", password="motdepasse")
        self.path = LearningPath.objects.create(owner=self.user, title="Licence")
        self.period = Period.objects.create(path=self.path, title="Semestre 5")
        self.competency = Competency.objects.create(path=self.path, title="Rédiger une démonstration")

    def record(self, **fields):
        return ProgressRecord.objects.create(owner=self.user, competency=self.competency, **fields)

    def reload(self, record):
        return ProgressRecord.objects.select_related("competency__path").get(pk=record.pk)


class LevelJournalTests(JournalTestCase):
    def test_a_record_at_rest_writes_nothing(self):
        """Une ligne créée d'office par la grille n'est pas un événement de progression."""
        self.record()
        self.assertEqual(ProgressEvent.objects.count(), 0)

    def test_a_declared_level_is_journalled(self):
        record = self.reload(self.record())
        record.mastery_level = ProgressRecord.Mastery.ACQUIRED
        record.save()
        event = ProgressEvent.objects.get()
        self.assertEqual(event.previous_level, ProgressRecord.Mastery.NOT_STARTED)
        self.assertEqual(event.level, ProgressRecord.Mastery.ACQUIRED)
        self.assertEqual(event.origin, ProgressRecord.Origin.MANUAL)

    def test_a_suggested_level_is_journalled_with_its_origin(self):
        self.record(planned_hours=Decimal(12), manual_hours=Decimal(6))
        event = ProgressEvent.objects.get()
        self.assertEqual(event.level, ProgressRecord.Mastery.IN_PROGRESS)
        self.assertEqual(event.origin, ProgressRecord.Origin.SUGGESTED)
        self.assertTrue(event.is_suggested)

    def test_each_step_leaves_its_own_line(self):
        record = self.record(planned_hours=Decimal(12))
        for hours in (3, 6, 9, 12):
            record = self.reload(record)
            record.manual_hours = Decimal(hours)
            record.save()
        self.assertEqual(ProgressEvent.objects.count(), 4)
        self.assertEqual(
            list(ProgressEvent.objects.order_by("pk").values_list("level", flat=True)),
            [1, 2, 3, 4],
        )

    def test_a_level_that_does_not_move_writes_nothing(self):
        record = self.reload(self.record(planned_hours=Decimal(12), manual_hours=Decimal(3)))
        record.notes = "Revoir le chapitre 2"
        record.save()
        self.assertEqual(ProgressEvent.objects.count(), 1)

    def test_a_correction_downwards_is_kept_too(self):
        """Un retour en arrière fait partie du chemin : l'effacer donnerait une courbe fausse."""
        record = self.reload(self.record(planned_hours=Decimal(4), manual_hours=Decimal(4)))
        record.mastery_level = ProgressRecord.Mastery.DISCOVERED
        record.save()
        last = ProgressEvent.objects.first()
        self.assertEqual(last.previous_level, ProgressRecord.Mastery.MASTERED)
        self.assertEqual(last.level, ProgressRecord.Mastery.DISCOVERED)
        self.assertFalse(last.is_rise)

    def test_deleting_the_record_takes_its_history(self):
        record = self.reload(self.record(planned_hours=Decimal(12), manual_hours=Decimal(12)))
        record.delete()
        self.assertEqual(ProgressEvent.objects.count(), 0)


class TimelineTests(JournalTestCase):
    def test_no_history_gives_no_curve(self):
        self.record()
        self.assertEqual(level_timeline(self.user, self.path), [])

    def test_a_path_without_competencies_gives_no_curve(self):
        empty = LearningPath.objects.create(owner=self.user, title="Vide")
        self.assertEqual(level_timeline(self.user, empty), [])

    def test_the_curve_counts_acquired_competencies_month_by_month(self):
        record = self.reload(self.record())
        record.mastery_level = ProgressRecord.Mastery.ACQUIRED
        record.save()
        points = level_timeline(self.user, self.path, months=3)
        self.assertEqual(len(points), 3)
        self.assertEqual(points[-1].acquired, 1)
        self.assertEqual(points[-1].total, 1)
        self.assertEqual(points[-1].percent, 100)

    def test_an_older_month_does_not_see_a_later_rise(self):
        record = self.reload(self.record())
        record.mastery_level = ProgressRecord.Mastery.ACQUIRED
        record.save()
        points = level_timeline(self.user, self.path, months=3)
        self.assertEqual(points[0].acquired, 0)

    def test_a_rise_below_acquired_does_not_count(self):
        record = self.reload(self.record())
        record.mastery_level = ProgressRecord.Mastery.IN_PROGRESS
        record.save()
        self.assertEqual(level_timeline(self.user, self.path, months=2)[-1].acquired, 0)

    def test_another_account_history_is_not_counted(self):
        intruse = get_user_model().objects.create_user("intruse", password="motdepasse")
        record = self.reload(self.record())
        record.mastery_level = ProgressRecord.Mastery.ACQUIRED
        record.save()
        self.assertEqual(level_timeline(intruse, self.path, months=2), [])

    def test_an_event_from_a_past_month_is_already_counted(self):
        record = self.reload(self.record())
        record.mastery_level = ProgressRecord.Mastery.MASTERED
        record.save()
        ProgressEvent.objects.update(created_at=timezone.now() - timedelta(days=70))
        points = level_timeline(self.user, self.path, months=4)
        self.assertEqual(points[-1].acquired, 1)
        self.assertEqual(points[0].acquired, 0)


class SparklineTests(TestCase):
    def test_a_single_point_draws_nothing(self):
        from formations.history import Point

        self.assertEqual(sparkline([Point("août 2026", 1, 4)]), {})

    def test_coordinates_stay_inside_the_frame(self):
        from formations.history import Point

        points = [Point("juin", 0, 4), Point("juill.", 2, 4), Point("août", 4, 4)]
        drawing = sparkline(points, width=100, height=50)
        coordinates = [tuple(float(value) for value in pair.split(",")) for pair in drawing["line"].split()]
        self.assertEqual(len(coordinates), 3)
        for x, y in coordinates:
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x, 100)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(y, 50)

    def test_a_full_score_sits_at_the_top(self):
        from formations.history import Point

        drawing = sparkline([Point("juin", 0, 4), Point("août", 4, 4)], width=100, height=50)
        self.assertEqual(drawing["last"][1], 6.0)


class TrackingPageTests(JournalTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_the_curve_is_absent_before_any_progress(self):
        self.record()
        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        self.assertNotContains(response, "Compétences acquises dans le temps")

    def test_the_curve_appears_once_something_moved(self):
        record = self.reload(self.record())
        record.mastery_level = ProgressRecord.Mastery.ACQUIRED
        record.save()
        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        self.assertContains(response, "Compétences acquises dans le temps")
        self.assertContains(response, "timeline-line")

    def test_the_competency_page_shows_the_path_travelled(self):
        record = self.reload(self.record())
        record.mastery_level = ProgressRecord.Mastery.ACQUIRED
        record.save()
        response = self.client.get(reverse("formations:competency", args=[self.competency.pk]))
        self.assertContains(response, "Chemin parcouru")
        self.assertContains(response, "déclaré")
