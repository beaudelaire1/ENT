"""Évaluations, résultats, et moyennes qui disent comment elles sont calculées."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.academics import period_average, struggling_competencies, unit_average
from formations.models import (
    Assessment,
    AssessmentResult,
    LearningPath,
    LearningUnit,
    MetricDefinition,
    MetricValue,
    Period,
    ProgressRecord,
)
from formations.tests.factories import competency_in


class AssessmentBase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie", order=1)
        self.competency = competency_in(self.unit, title="Établir la compacité")

    def assessment(self, **kwargs):
        defaults = {
            "owner": self.user,
            "period": self.period,
            "unit": self.unit,
            "title": "Partiel de topologie",
            "kind": Assessment.Kind.MIDTERM,
            "coefficient": Decimal("2"),
            "scale": Decimal("20"),
        }
        return Assessment.objects.create(**{**defaults, **kwargs})


class AssessmentLifecycleTests(AssessmentBase):
    def test_an_assessment_exists_before_its_result(self):
        """On prépare un examen avant de connaître sa note."""
        assessment = self.assessment(scheduled_for=timezone.now() + timedelta(days=7))
        self.assertFalse(hasattr(assessment, "result"))
        response = self.client.get(reverse("formations:assessment", args=[assessment.pk]))
        self.assertContains(response, "Pas encore de résultat")
        self.assertContains(response, "Dans 7 jours")

    def test_an_upcoming_assessment_leads_the_list(self):
        past = self.assessment(title="Contrôle passé", scheduled_for=timezone.now() - timedelta(days=3))
        soon = self.assessment(title="Partiel proche", scheduled_for=timezone.now() + timedelta(days=2))

        response = self.client.get(reverse("formations:assessments"))

        self.assertEqual([a.pk for a in response.context["upcoming"]], [soon.pk])
        self.assertEqual([a.pk for a in response.context["past"]], [past.pk])

    def test_saving_a_result_marks_the_assessment_as_corrected(self):
        assessment = self.assessment(scheduled_for=timezone.now() - timedelta(days=1))

        self.client.post(
            reverse("formations:result_edit", args=[assessment.pk]),
            {"score": "14", "scale": "20", "published_on": "", "comment": "", "self_review": ""},
        )

        assessment.refresh_from_db()
        self.assertEqual(assessment.status, Assessment.Status.MARKED)
        self.assertEqual(assessment.result.score, Decimal("14"))

    def test_the_result_form_starts_from_the_declared_scale(self):
        assessment = self.assessment(scale=Decimal("100"))
        response = self.client.get(reverse("formations:result_edit", args=[assessment.pk]))
        self.assertEqual(response.context["form"].initial["scale"], Decimal("100"))

    def test_changing_the_scale_of_the_assessment_leaves_the_result_alone(self):
        assessment = self.assessment()
        result = AssessmentResult.objects.create(assessment=assessment, score=Decimal("15"), scale=Decimal("20"))

        Assessment.objects.filter(pk=assessment.pk).update(scale=Decimal("100"))

        result.refresh_from_db()
        self.assertEqual(result.scale, Decimal("20"))
        self.assertEqual(result.out_of_twenty, Decimal("15.00"))

    def test_an_absence_carries_no_score(self):
        assessment = self.assessment()
        result = AssessmentResult(assessment=assessment, score=Decimal("10"), scale=Decimal("20"), absent=True)
        with self.assertRaises(ValidationError):
            result.full_clean()

    def test_a_score_above_the_scale_is_refused(self):
        assessment = self.assessment()
        result = AssessmentResult(assessment=assessment, score=Decimal("25"), scale=Decimal("20"))
        with self.assertRaises(ValidationError):
            result.full_clean()

    def test_the_database_refuses_a_scale_of_zero(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.assessment(scale=Decimal("0"))

    def test_a_unit_from_another_period_is_a_form_error(self):
        other = Period.objects.create(path=self.path, title="Semestre 6", order=6)
        response = self.client.post(
            reverse("formations:assessment_new"),
            {
                "title": "Partiel",
                "kind": Assessment.Kind.MIDTERM,
                "period": other.pk,
                "unit": self.unit.pk,
                "scheduled_for": "",
                "coefficient": "1",
                "scale": "20",
                "status": Assessment.Status.PLANNED,
                "description": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "appartient à une autre période")

    def test_the_period_is_deduced_from_the_unit(self):
        response = self.client.post(
            reverse("formations:assessment_new"),
            {
                "title": "Partiel",
                "kind": Assessment.Kind.MIDTERM,
                "period": "",
                "unit": self.unit.pk,
                "scheduled_for": "",
                "coefficient": "1",
                "scale": "20",
                "status": Assessment.Status.PLANNED,
                "description": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Assessment.objects.get(title="Partiel").period, self.period)

    def test_another_users_assessment_is_out_of_reach(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign = Assessment.objects.create(owner=bob, title="Privé")
        for name in ("assessment", "assessment_edit", "result_edit", "assessment_competencies"):
            with self.subTest(vue=name):
                self.assertEqual(self.client.get(reverse(f"formations:{name}", args=[foreign.pk])).status_code, 404)


class AssessmentCompetencyTests(AssessmentBase):
    def test_competencies_are_declared_by_search(self):
        assessment = self.assessment()
        self.client.post(
            reverse("formations:assessment_competencies", args=[assessment.pk]),
            {"competencies": [self.competency.pk]},
        )
        self.assertEqual(list(assessment.competencies.all()), [self.competency])

    def test_without_a_search_only_the_units_competencies_are_offered(self):
        other_unit = LearningUnit.objects.create(period=self.period, title="Algèbre", order=2)
        elsewhere = competency_in(other_unit, title="Diagonaliser une matrice")
        assessment = self.assessment()

        response = self.client.get(reverse("formations:assessment_competencies", args=[assessment.pk]))

        offered = list(response.context["candidates"])
        self.assertIn(self.competency, offered)
        self.assertNotIn(elsewhere, offered)

    def test_a_search_reaches_the_whole_path(self):
        other_unit = LearningUnit.objects.create(period=self.period, title="Algèbre", order=2)
        elsewhere = competency_in(other_unit, title="Diagonaliser une matrice")
        assessment = self.assessment()

        response = self.client.get(
            reverse("formations:assessment_competencies", args=[assessment.pk]), {"q": "diagonaliser"}
        )

        self.assertEqual(list(response.context["candidates"]), [elsewhere])

    def test_removing_a_competency_keeps_it_in_the_path(self):
        assessment = self.assessment()
        assessment.competencies.add(self.competency)

        self.client.post(
            reverse("formations:assessment_competencies", args=[assessment.pk]), {"remove": self.competency.pk}
        )

        self.assertFalse(assessment.competencies.exists())
        self.assertTrue(self.competency.pk)

    def test_the_preparation_lists_what_is_not_acquired(self):
        assessment = self.assessment(scheduled_for=timezone.now() + timedelta(days=5))
        acquired = competency_in(self.unit, title="Calculer une adhérence", order=2)
        assessment.competencies.add(self.competency, acquired)
        ProgressRecord.objects.create(owner=self.user, competency=acquired, mastery_level=3)
        ProgressRecord.objects.create(owner=self.user, competency=self.competency, mastery_level=1)

        weak = struggling_competencies(self.user, assessment)

        self.assertEqual([row["competency"] for row in weak], [self.competency])

    def test_the_screen_offers_sablier_on_a_weak_competency(self):
        assessment = self.assessment(scheduled_for=timezone.now() + timedelta(days=5))
        assessment.competencies.add(self.competency)
        response = self.client.get(reverse("formations:assessment", args=[assessment.pk]))
        self.assertContains(response, f"{reverse('sablier:home')}?competency={self.competency.pk}")
        self.assertContains(response, "À travailler d’abord")

    def test_after_a_result_the_same_list_becomes_what_to_take_up_again(self):
        assessment = self.assessment(scheduled_for=timezone.now() - timedelta(days=1))
        assessment.competencies.add(self.competency)
        AssessmentResult.objects.create(assessment=assessment, score=Decimal("6"), scale=Decimal("20"))

        response = self.client.get(reverse("formations:assessment", args=[assessment.pk]))

        self.assertContains(response, "À reprendre")
        self.assertContains(response, "rien n’est déduit de la note")

    def test_a_low_mark_never_changes_the_declared_level(self):
        """Le niveau reste une autoévaluation : une note ne le réécrit pas."""
        assessment = self.assessment()
        assessment.competencies.add(self.competency)
        record = ProgressRecord.objects.create(owner=self.user, competency=self.competency, mastery_level=3)

        AssessmentResult.objects.create(assessment=assessment, score=Decimal("2"), scale=Decimal("20"))

        record.refresh_from_db()
        self.assertEqual(record.mastery_level, 3)


class AverageTests(AssessmentBase):
    def result(self, *, score, scale=Decimal("20"), coefficient=Decimal("1"), absent=False, title="Épreuve"):
        assessment = self.assessment(title=title, coefficient=coefficient, scale=scale)
        return AssessmentResult.objects.create(assessment=assessment, score=score, scale=scale, absent=absent)

    def test_a_weighted_average_is_computed_on_twenty(self):
        self.result(score=Decimal("12"), coefficient=Decimal("1"), title="A")
        self.result(score=Decimal("16"), coefficient=Decimal("3"), title="B")

        average = unit_average(self.user, self.unit)

        self.assertEqual(average.value, Decimal("15.00"))
        self.assertEqual(average.counted, 2)
        self.assertIn("Moyenne pondérée de 2 note(s)", average.method)

    def test_a_different_scale_is_brought_back_to_twenty(self):
        self.result(score=Decimal("80"), scale=Decimal("100"), title="Sur cent")
        average = unit_average(self.user, self.unit)
        self.assertEqual(average.value, Decimal("16.00"))

    def test_the_equivalent_out_of_twenty_appears_only_when_it_informs(self):
        """« 7,5/20 soit 7,5/20 » ne renseigne personne."""
        on_twenty = self.result(score=Decimal("7.5"), title="Sur vingt")
        response = self.client.get(reverse("formations:assessment", args=[on_twenty.assessment_id]))
        self.assertNotContains(response, "soit 7,5")

        on_hundred = self.result(score=Decimal("80"), scale=Decimal("100"), title="Sur cent")
        response = self.client.get(reverse("formations:assessment", args=[on_hundred.assessment_id]))
        self.assertContains(response, "soit 16")

    def test_an_absence_is_never_counted_as_a_zero(self):
        self.result(score=Decimal("14"), title="Notée")
        absent_assessment = self.assessment(title="Manquée")
        AssessmentResult.objects.create(assessment=absent_assessment, scale=Decimal("20"), absent=True)

        average = unit_average(self.user, self.unit)

        self.assertEqual(average.value, Decimal("14.00"))
        self.assertTrue(any("absence" in warning for warning in average.warnings))

    def test_a_zero_coefficient_is_excluded_and_said(self):
        self.result(score=Decimal("14"), coefficient=Decimal("1"), title="Comptée")
        self.result(score=Decimal("2"), coefficient=Decimal("0"), title="Blanche")

        average = unit_average(self.user, self.unit)

        self.assertEqual(average.value, Decimal("14.00"))
        self.assertTrue(any("coefficient nul" in warning for warning in average.warnings))

    def test_an_assessment_without_result_is_announced(self):
        self.result(score=Decimal("14"), title="Notée")
        self.assessment(title="À venir", scheduled_for=timezone.now() + timedelta(days=4))

        average = unit_average(self.user, self.unit)

        self.assertEqual(average.value, Decimal("14.00"))

    def test_a_unit_without_any_result_says_so_rather_than_showing_zero(self):
        self.assessment(title="Prévue")
        average = unit_average(self.user, self.unit)
        self.assertIsNone(average.value)
        self.assertIn("aucun résultat saisi", average.method)

    def test_the_method_is_always_available_next_to_the_value(self):
        self.result(score=Decimal("11"), title="Une")
        response = self.client.get(reverse("formations:assessment", args=[Assessment.objects.first().pk]))
        self.assertContains(response, "Moyenne pondérée")

    def test_a_period_average_needs_a_declared_weighting_column(self):
        self.result(score=Decimal("14"))
        average = period_average(self.user, self.period)
        self.assertIsNone(average.value)
        self.assertIn("Aucune colonne de pondération", average.method)

    def test_a_period_average_uses_the_declared_column(self):
        ects = MetricDefinition.objects.create(path=self.path, key="ects", label="ECTS")
        LearningPath.objects.filter(pk=self.path.pk).update(weight_metric=ects)
        self.path.refresh_from_db()
        algebra = LearningUnit.objects.create(period=self.period, title="Algèbre", order=2)
        MetricValue.objects.create(definition=ects, unit=self.unit, value=Decimal("5"))
        MetricValue.objects.create(definition=ects, unit=algebra, value=Decimal("1"))
        self.result(score=Decimal("10"), title="Topo")
        second = Assessment.objects.create(owner=self.user, period=self.period, unit=algebra, title="Alg", scale=20)
        AssessmentResult.objects.create(assessment=second, score=Decimal("18"), scale=Decimal("20"))

        average = period_average(self.user, self.period)

        # (10 × 5 + 18 × 1) / 6
        self.assertEqual(average.value, Decimal("11.33"))
        self.assertIn("pondérée par ECTS", average.method)
        self.assertIn("Aucune compensation", average.method)

    def test_a_unit_without_weight_is_excluded_and_named(self):
        ects = MetricDefinition.objects.create(path=self.path, key="ects", label="ECTS")
        LearningPath.objects.filter(pk=self.path.pk).update(weight_metric=ects)
        self.path.refresh_from_db()
        MetricValue.objects.create(definition=ects, unit=self.unit, value=Decimal("5"))
        algebra = LearningUnit.objects.create(period=self.period, title="Algèbre", order=2)
        self.result(score=Decimal("10"), title="Topo")
        second = Assessment.objects.create(owner=self.user, period=self.period, unit=algebra, title="Alg", scale=20)
        AssessmentResult.objects.create(assessment=second, score=Decimal("18"), scale=Decimal("20"))

        average = period_average(self.user, self.period)

        self.assertEqual(average.value, Decimal("10.00"))
        self.assertTrue(any("Algèbre" in warning for warning in average.warnings))

    def test_nothing_ever_concludes_on_a_diploma(self):
        """Aucun calcul ne prononce de validation : c'est le rôle d'un jury."""
        self.result(score=Decimal("2"), title="Ratée")
        average = unit_average(self.user, self.unit)
        for forbidden in ("validé", "non validé", "admis", "ajourné", "redoubl"):
            with self.subTest(mot=forbidden):
                self.assertNotIn(forbidden, average.method.lower())
