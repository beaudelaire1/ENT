"""Objectifs restitués, niveaux qualifiés, progression pondérée."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.models import Competency, LearningPath, LearningUnit, Period, ProgressRecord, UnitCompetency
from formations.progression import MASTERY_DESCRIPTIONS, weighted_progress


class TargetTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("etudiant", password="motdepasse")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="Licence")
        self.period = Period.objects.create(path=self.path, title="Semestre 5")
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie")
        self.competency = Competency.objects.create(path=self.path, title="Rédiger une démonstration")


class TargetTests(TargetTestCase):
    def record(self, **fields):
        return ProgressRecord.objects.create(owner=self.user, competency=self.competency, **fields)

    def test_a_target_without_a_level_reports_nothing(self):
        self.assertIsNone(self.record().reaches_target)

    def test_a_reached_target_is_reported(self):
        record = self.record(
            mastery_level=ProgressRecord.Mastery.ACQUIRED, target_level=ProgressRecord.Mastery.ACQUIRED
        )
        self.assertTrue(record.reaches_target)
        self.assertFalse(record.target_is_late)

    def test_a_passed_date_below_the_target_is_late(self):
        record = self.record(
            mastery_level=ProgressRecord.Mastery.DISCOVERED,
            target_level=ProgressRecord.Mastery.ACQUIRED,
            target_date=timezone.localdate() - timedelta(days=3),
        )
        self.assertTrue(record.target_is_late)
        self.assertEqual(record.days_to_target, -3)

    def test_a_passed_date_at_the_target_is_not_late(self):
        record = self.record(
            mastery_level=ProgressRecord.Mastery.MASTERED,
            target_level=ProgressRecord.Mastery.ACQUIRED,
            target_date=timezone.localdate() - timedelta(days=3),
        )
        self.assertFalse(record.target_is_late)

    def test_the_competency_page_shows_the_target(self):
        self.record(
            target_level=ProgressRecord.Mastery.ACQUIRED,
            target_date=timezone.localdate() + timedelta(days=10),
        )
        response = self.client.get(reverse("formations:competency", args=[self.competency.pk]))
        self.assertContains(response, "Objectif")
        self.assertContains(response, "dans 10 jour(s)")

    def test_the_dashboard_lists_a_missed_target(self):
        self.path.current_period = self.period
        self.path.save(update_fields=["current_period"])
        self.competency.period = self.period
        self.competency.save(update_fields=["period"])
        self.record(
            mastery_level=ProgressRecord.Mastery.NOT_STARTED,
            target_level=ProgressRecord.Mastery.ACQUIRED,
            target_date=timezone.localdate() - timedelta(days=1),
        )
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "À reprendre")
        self.assertContains(response, "Rédiger une démonstration")
        self.assertContains(response, "dépassé")


class DescriptionTests(TargetTestCase):
    def test_every_level_has_an_observable_criterion(self):
        for value, _label in ProgressRecord.Mastery.choices:
            with self.subTest(level=value):
                self.assertTrue(MASTERY_DESCRIPTIONS.get(value))

    def test_the_record_exposes_the_criterion_of_its_level(self):
        record = ProgressRecord.objects.create(
            owner=self.user, competency=self.competency, mastery_level=ProgressRecord.Mastery.ACQUIRED
        )
        self.assertEqual(record.mastery_description, MASTERY_DESCRIPTIONS[3])

    def test_the_grid_legend_carries_the_criteria(self):
        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        self.assertContains(response, MASTERY_DESCRIPTIONS[3])
        self.assertContains(response, MASTERY_DESCRIPTIONS[4])


class WeightedProgressTests(TargetTestCase):
    created = 0

    def rows(self, *levels):
        """Un jeu de progressions aux niveaux voulus, aux intitulés jamais réutilisés."""
        records = []
        for level in levels:
            WeightedProgressTests.created += 1
            competency = Competency.objects.create(path=self.path, title=f"Compétence {self.created}")
            records.append(ProgressRecord.objects.create(owner=self.user, competency=competency, mastery_level=level))
        return records

    def test_nothing_started_is_zero(self):
        self.assertEqual(weighted_progress(self.rows(0, 0), set()), 0)

    def test_everything_mastered_is_one_hundred(self):
        self.assertEqual(weighted_progress(self.rows(4, 4), set()), 100)

    def test_an_intermediate_level_counts_for_what_it_is_worth(self):
        """« Acquis » n'est pas « rien » : un décompte binaire le comptait pour zéro."""
        self.assertEqual(weighted_progress(self.rows(3), set()), 75)

    def test_a_primary_competency_weighs_double(self):
        """Mêmes compétences, mêmes niveaux : seule la pondération change d'un appel à l'autre."""
        maitrisee, non_abordee = self.rows(4, 0)
        records = [maitrisee, non_abordee]
        # La maîtrisée est principale : 2×4 sur 2×4 + 1×4.
        self.assertEqual(weighted_progress(records, {maitrisee.competency_id}), 67)
        # La non abordée est principale : 1×4 sur 1×4 + 2×4.
        self.assertEqual(weighted_progress(records, {non_abordee.competency_id}), 33)
        # Aucune n'est principale : les deux pèsent pareil.
        self.assertEqual(weighted_progress(records, set()), 50)

    def test_no_record_gives_zero_rather_than_an_error(self):
        self.assertEqual(weighted_progress([], set()), 0)

    def test_the_dashboard_weighs_by_the_primary_link(self):
        UnitCompetency.objects.create(unit=self.unit, competency=self.competency, is_primary=True)
        self.path.current_period = self.period
        self.path.save(update_fields=["current_period"])
        ProgressRecord.objects.create(
            owner=self.user, competency=self.competency, mastery_level=ProgressRecord.Mastery.IN_PROGRESS
        )
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, 'value="50" max="100"')


class HoursGapTests(TargetTestCase):
    def gap(self, planned, actual):
        record = ProgressRecord.objects.create(
            owner=self.user,
            competency=self.competency,
            planned_hours=Decimal(planned),
            manual_hours=Decimal(actual),
        )
        return ProgressRecord.objects.get(pk=record.pk).hours_comment

    def test_no_estimate_no_comment(self):
        self.assertEqual(self.gap(0, 10), "")

    def test_no_time_spent_no_comment(self):
        self.assertEqual(self.gap(10, 0), "")

    def test_a_close_estimate_stays_silent(self):
        """Une estimation à peu près juste n'appelle aucun commentaire."""
        self.assertEqual(self.gap(10, 9), "")

    def test_a_large_overrun_is_stated_without_judgement(self):
        comment = self.gap(6, 11)
        self.assertIn("6 h", comment)
        self.assertIn("11 h", comment)

    def test_being_well_behind_says_what_remains(self):
        self.assertIn("8 h", self.gap(10, 2))
