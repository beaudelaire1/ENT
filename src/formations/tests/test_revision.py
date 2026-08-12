"""La boucle de reprise : ce qui ramène vers une compétence, et ce qu'un résultat propose."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.models import (
    Assessment,
    AssessmentResult,
    Competency,
    LearningPath,
    LearningUnit,
    Period,
    ProgressRecord,
)
from formations.progression import level_from_result
from formations.revision import suggest_from_result, to_revisit


class RevisionTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("etudiant", password="motdepasse")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="Licence")
        self.period = Period.objects.create(path=self.path, title="Semestre 5")
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie")
        self.competency = Competency.objects.create(
            path=self.path, period=self.period, title="Rédiger une démonstration"
        )

    def record(self, **fields):
        return ProgressRecord.objects.create(owner=self.user, competency=self.competency, **fields)

    def assessment(self, *, days, competencies=True, **fields):
        assessment = Assessment.objects.create(
            owner=self.user,
            unit=self.unit,
            title="Partiel de topologie",
            scheduled_for=timezone.now() + timedelta(days=days),
            **fields,
        )
        if competencies:
            assessment.competencies.add(self.competency)
        return assessment


class ToRevisitTests(RevisionTestCase):
    def test_nothing_to_say_about_an_untouched_formation(self):
        self.record()
        self.assertEqual(to_revisit(self.user, self.path), [])

    def test_a_mastered_competency_is_never_recalled(self):
        self.record(mastery_level=ProgressRecord.Mastery.MASTERED)
        self.assertEqual(to_revisit(self.user, self.path), [])

    def test_a_missed_target_comes_back(self):
        self.record(
            mastery_level=ProgressRecord.Mastery.DISCOVERED,
            target_level=ProgressRecord.Mastery.ACQUIRED,
            target_date=timezone.localdate() - timedelta(days=2),
        )
        found = to_revisit(self.user, self.path)
        self.assertEqual(len(found), 1)
        self.assertIn("dépassé", found[0].reason)

    def test_an_approaching_assessment_brings_back_what_is_not_acquired(self):
        self.record(mastery_level=ProgressRecord.Mastery.IN_PROGRESS)
        self.assessment(days=3)
        found = to_revisit(self.user, self.path)
        self.assertEqual(len(found), 1)
        self.assertIn("dans 3 jours", found[0].reason)

    def test_an_acquired_competency_is_left_alone_before_an_assessment(self):
        self.record(mastery_level=ProgressRecord.Mastery.ACQUIRED)
        self.assessment(days=3)
        self.assertEqual(to_revisit(self.user, self.path), [])

    def test_a_distant_assessment_does_not_crowd_the_list(self):
        """Plus tôt, la liste serait pleine de choses dont on ne peut rien faire aujourd'hui."""
        self.record(mastery_level=ProgressRecord.Mastery.IN_PROGRESS)
        self.assessment(days=60)
        self.assertEqual(to_revisit(self.user, self.path), [])

    def test_a_stale_self_assessment_comes_back(self):
        record = self.record()
        record = ProgressRecord.objects.get(pk=record.pk)
        record.mastery_level = ProgressRecord.Mastery.ACQUIRED
        record.save()
        ProgressRecord.objects.filter(pk=record.pk).update(assessed_at=timezone.now() - timedelta(weeks=10))
        found = to_revisit(self.user, self.path)
        self.assertEqual(len(found), 1)
        self.assertIn("10 semaines", found[0].reason)

    def test_a_recent_self_assessment_is_left_alone(self):
        record = ProgressRecord.objects.get(pk=self.record().pk)
        record.mastery_level = ProgressRecord.Mastery.ACQUIRED
        record.save()
        self.assertEqual(to_revisit(self.user, self.path), [])

    def test_the_most_pressing_reason_comes_first(self):
        other = Competency.objects.create(path=self.path, period=self.period, title="Calculer une intégrale")
        ProgressRecord.objects.create(
            owner=self.user,
            competency=other,
            mastery_level=ProgressRecord.Mastery.DISCOVERED,
            target_level=ProgressRecord.Mastery.ACQUIRED,
            target_date=timezone.localdate() - timedelta(days=2),
        )
        self.record(mastery_level=ProgressRecord.Mastery.IN_PROGRESS)
        self.assessment(days=2)
        found = to_revisit(self.user, self.path)
        self.assertEqual(
            [revision.competency.title for revision in found], ["Calculer une intégrale", "Rédiger une démonstration"]
        )

    def test_a_competency_outside_the_period_is_filtered_out(self):
        elsewhere = Period.objects.create(path=self.path, title="Semestre 6")
        self.record(
            mastery_level=ProgressRecord.Mastery.DISCOVERED,
            target_level=ProgressRecord.Mastery.ACQUIRED,
            target_date=timezone.localdate() - timedelta(days=2),
        )
        self.assertEqual(to_revisit(self.user, self.path, elsewhere), [])

    def test_another_account_sees_nothing(self):
        intruse = get_user_model().objects.create_user("intruse", password="motdepasse")
        self.record(
            mastery_level=ProgressRecord.Mastery.DISCOVERED,
            target_level=ProgressRecord.Mastery.ACQUIRED,
            target_date=timezone.localdate() - timedelta(days=2),
        )
        self.assertEqual(to_revisit(intruse, self.path), [])


class ResultSuggestionTests(RevisionTestCase):
    def result(self, score, scale=20):
        assessment = self.assessment(days=-2, status=Assessment.Status.MARKED)
        AssessmentResult.objects.create(
            assessment=assessment,
            score=None if score is None else Decimal(score),
            scale=Decimal(scale),
            absent=score is None,
        )
        assessment.refresh_from_db()
        return assessment

    def test_a_good_mark_suggests_a_level(self):
        assessment = self.result(16)
        self.assertEqual(level_from_result(assessment.result), 3)
        applied, pending = suggest_from_result(self.user, assessment)
        self.assertEqual(len(applied), 1)
        self.assertEqual(pending, [])
        stored = ProgressRecord.objects.get(owner=self.user, competency=self.competency)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.ACQUIRED)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.SUGGESTED)

    def test_a_suggestion_from_a_mark_is_not_a_self_assessment(self):
        assessment = self.result(20)
        suggest_from_result(self.user, assessment)
        self.assertIsNone(ProgressRecord.objects.get(owner=self.user, competency=self.competency).assessed_at)

    def test_an_absence_suggests_nothing(self):
        assessment = self.result(None)
        self.assertIsNone(level_from_result(assessment.result))
        self.assertEqual(suggest_from_result(self.user, assessment), ([], []))

    def test_a_bad_mark_never_demotes(self):
        """Une mauvaise note dit qu'il reste du travail, pas que ce qui était su est perdu."""
        record = ProgressRecord.objects.get(pk=self.record(mastery_level=ProgressRecord.Mastery.MASTERED).pk)
        assessment = self.result(4)
        applied, pending = suggest_from_result(self.user, assessment)
        self.assertEqual((applied, pending), ([], []))
        self.assertEqual(ProgressRecord.objects.get(pk=record.pk).mastery_level, ProgressRecord.Mastery.MASTERED)

    def test_a_declared_level_receives_a_proposal_instead_of_an_overwrite(self):
        record = ProgressRecord.objects.get(pk=self.record().pk)
        record.mastery_level = ProgressRecord.Mastery.DISCOVERED
        record.save()
        assessment = self.result(19)
        applied, pending = suggest_from_result(self.user, assessment)
        self.assertEqual(applied, [])
        self.assertEqual(len(pending), 1)
        self.assertEqual(ProgressRecord.objects.get(pk=record.pk).mastery_level, ProgressRecord.Mastery.DISCOVERED)

    def test_saving_a_result_through_the_form_triggers_the_proposal(self):
        assessment = self.assessment(days=-2)
        response = self.client.post(
            reverse("formations:result_edit", args=[assessment.pk]),
            {"score": "18", "scale": "20", "comment": "", "self_review": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        stored = ProgressRecord.objects.get(owner=self.user, competency=self.competency)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.ACQUIRED)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.SUGGESTED)
