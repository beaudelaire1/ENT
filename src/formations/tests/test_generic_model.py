"""Un modèle académique qui ne suppose pas une université en particulier.

Deux changements de fond : les matières peuvent être regroupées en UE — facultativement —
et une compétence n'appartient plus à une seule matière. « Rédiger une démonstration au
tableau » est un savoir-faire unique exercé aux deux semestres ; le modèle en faisait deux
compétences avec deux suivis parallèles.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.models import (
    Competency,
    LearningGroup,
    LearningPath,
    LearningUnit,
    Period,
    ProgressRecord,
    UnitCompetency,
)
from formations.services import build_tracking_grid, ensure_progress_records, tracked_records
from formations.tests.factories import competency_in, share_competency


class GroupTests(TestCase):
    """Les UE sont facultatives : une formation courte n'en voit jamais la trace."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)

    def test_a_unit_needs_no_group(self):
        unit = LearningUnit.objects.create(period=self.period, title="Topologie")
        self.assertIsNone(unit.group)
        response = self.client.get(reverse("formations:unit", args=[unit.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Regroupement")

    def test_a_group_can_be_created_and_shown(self):
        response = self.client.post(
            reverse("formations:group_new", args=[self.period.pk]),
            {"title": "UEO Mathématiques 5", "code": "UEO5", "kind": "UE", "order": 1},
        )
        self.assertRedirects(response, reverse("formations:detail", args=[self.path.pk]))
        group = LearningGroup.objects.get(period=self.period)
        self.assertEqual(str(group), "UEO5 · UEO Mathématiques 5")
        self.assertContains(self.client.get(reverse("formations:detail", args=[self.path.pk])), "UEO5")

    def test_a_unit_can_join_a_group(self):
        group = LearningGroup.objects.create(period=self.period, title="UEO Mathématiques 5", kind="UE")
        unit = LearningUnit.objects.create(period=self.period, title="Topologie")
        self.client.post(
            reverse("formations:unit_edit", args=[unit.pk]),
            {"title": "Topologie", "description": "", "group": group.pk, "order": 1},
        )
        unit.refresh_from_db()
        self.assertEqual(unit.group, group)

    def test_a_group_of_another_period_is_not_offered(self):
        other = Period.objects.create(path=self.path, title="Semestre 6", order=6)
        LearningGroup.objects.create(period=other, title="UEO Mathématiques 6")
        mine = LearningGroup.objects.create(period=self.period, title="UEO Mathématiques 5")
        unit = LearningUnit.objects.create(period=self.period, title="Topologie")

        response = self.client.get(reverse("formations:unit_edit", args=[unit.pk]))

        self.assertEqual(list(response.context["form"].fields["group"].queryset), [mine])

    def test_deleting_a_group_keeps_its_units(self):
        group = LearningGroup.objects.create(period=self.period, title="UEO Mathématiques 5")
        unit = LearningUnit.objects.create(period=self.period, title="Topologie", group=group)

        self.client.post(reverse("formations:group_delete", args=[group.pk]))

        unit.refresh_from_db()
        self.assertIsNone(unit.group)
        self.assertTrue(LearningUnit.objects.filter(pk=unit.pk).exists())

    def test_two_groups_cannot_share_a_title_in_one_period(self):
        LearningGroup.objects.create(period=self.period, title="UEO")
        with self.assertRaises(IntegrityError), transaction.atomic():
            LearningGroup.objects.create(period=self.period, title="UEO")

    def test_the_grid_shows_a_group_banner_only_when_groups_exist(self):
        unit = LearningUnit.objects.create(period=self.period, title="Topologie")
        competency_in(unit, title="Établir la compacité")

        without = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        self.assertNotContains(without, "group-row")

        group = LearningGroup.objects.create(period=self.period, title="UEO Mathématiques 5", kind="UE")
        LearningUnit.objects.filter(pk=unit.pk).update(group=group)

        with_group = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        self.assertContains(with_group, "group-row")
        self.assertContains(with_group, "UEO Mathématiques 5")


class TransversalCompetencyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.s5 = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.s6 = Period.objects.create(path=self.path, title="Semestre 6", order=6)
        self.oraux5 = LearningUnit.objects.create(period=self.s5, title="Oraux 5", order=4)
        self.oraux6 = LearningUnit.objects.create(period=self.s6, title="Oraux 6", order=4)

    def test_one_competency_can_serve_two_units(self):
        competency = competency_in(self.oraux5, title="Rédiger une démonstration au tableau", period=None)
        share_competency(competency, self.oraux6)

        self.assertEqual(competency.units.count(), 2)
        self.assertEqual(Competency.objects.filter(path=self.path).count(), 1)

    def test_a_shared_competency_has_a_single_progress_record(self):
        competency = competency_in(self.oraux5, title="Rédiger une démonstration", period=None)
        share_competency(competency, self.oraux6)

        ensure_progress_records(self.user, self.path)

        self.assertEqual(ProgressRecord.objects.filter(owner=self.user, competency=competency).count(), 1)

    def test_a_shared_competency_is_editable_in_only_one_unit(self):
        """Deux formulaires sur une même ligne s'écraseraient l'un l'autre."""
        competency = competency_in(self.oraux5, title="Rédiger une démonstration", period=None)
        share_competency(competency, self.oraux6)
        ensure_progress_records(self.user, self.path)

        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        grid = build_tracking_grid(self.path, response.context["formset"])
        editable = [
            (unit["unit"].title, row["editable"])
            for period in grid["periods"]
            for unit in period["units"]
            for row in unit["rows"]
        ]

        self.assertEqual(sorted(editable), [("Oraux 5", True), ("Oraux 6", False)])

    def test_the_read_only_row_says_where_it_is_entered(self):
        competency = competency_in(self.oraux5, title="Rédiger une démonstration", period=None)
        share_competency(competency, self.oraux6)

        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))

        self.assertContains(response, "Se saisit sous Oraux 5")
        self.assertContains(response, "Aussi en")

    def test_the_grid_counts_a_shared_competency_once(self):
        competency = competency_in(self.oraux5, title="Rédiger une démonstration", period=None)
        share_competency(competency, self.oraux6)
        ensure_progress_records(self.user, self.path)
        ProgressRecord.objects.filter(competency=competency).update(planned_hours=Decimal("4"))

        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        grid = build_tracking_grid(self.path, response.context["formset"])
        totals = [period["totals"]["planned"] for period in grid["periods"]]

        # Quatre heures au semestre 5, zéro au semestre 6 : le même travail n'est pas
        # additionné deux fois.
        self.assertEqual(totals, [Decimal("4"), 0])

    def test_a_competency_without_unit_still_appears_in_the_grid(self):
        loose = Competency.objects.create(path=self.path, title="Travailler régulièrement")
        ensure_progress_records(self.user, self.path)

        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        grid = build_tracking_grid(self.path, response.context["formset"])

        self.assertEqual([row["competency"] for row in grid["orphans"]], [loose])
        self.assertContains(response, "Compétences transversales")
        self.assertContains(response, "Travailler régulièrement")

    def test_a_competency_of_a_period_without_unit_appears_under_it(self):
        loose = Competency.objects.create(path=self.path, period=self.s5, title="Assister aux cours")
        ensure_progress_records(self.user, self.path)

        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        grid = build_tracking_grid(self.path, response.context["formset"])

        self.assertEqual([row["competency"] for row in grid["periods"][0]["loose"]], [loose])
        self.assertContains(response, "Sans matière rattachée")

    def test_a_competency_can_be_attached_to_another_unit_from_the_screen(self):
        competency = competency_in(self.oraux5, title="Rédiger une démonstration")

        self.client.post(
            reverse("formations:unit_competencies", args=[self.oraux6.pk]), {"competencies": [competency.pk]}
        )

        self.assertEqual(set(competency.units.values_list("pk", flat=True)), {self.oraux5.pk, self.oraux6.pk})

    def test_attaching_from_a_second_unit_marks_the_link_secondary(self):
        competency = competency_in(self.oraux5, title="Rédiger une démonstration")
        self.client.post(
            reverse("formations:unit_competencies", args=[self.oraux6.pk]), {"competencies": [competency.pk]}
        )
        link = UnitCompetency.objects.get(unit=self.oraux6, competency=competency)
        self.assertFalse(link.is_primary)

    def test_detaching_keeps_the_competency_and_its_other_links(self):
        competency = competency_in(self.oraux5, title="Rédiger une démonstration")
        share_competency(competency, self.oraux6)

        self.client.post(reverse("formations:unit_competencies", args=[self.oraux6.pk]), {"remove": competency.pk})

        self.assertTrue(Competency.objects.filter(pk=competency.pk).exists())
        self.assertEqual(list(competency.units.all()), [self.oraux5])

    def test_a_competency_of_another_path_cannot_be_attached(self):
        other = LearningPath.objects.create(owner=self.user, title="DU Statistique")
        other_period = Period.objects.create(path=other, title="Bloc")
        other_unit = LearningUnit.objects.create(period=other_period, title="R")
        foreign = competency_in(other_unit, title="Ajuster une régression")

        self.client.post(reverse("formations:unit_competencies", args=[self.oraux5.pk]), {"competencies": [foreign.pk]})

        self.assertNotIn(self.oraux5, foreign.units.all())

    def test_the_local_objective_belongs_to_the_link(self):
        competency = competency_in(self.oraux5, title="Rédiger une démonstration")
        link = UnitCompetency.objects.get(unit=self.oraux5, competency=competency)

        self.client.post(
            reverse("formations:link_edit", args=[link.pk]),
            {"order": 1, "is_primary": "on", "local_objective": "Au tableau, sans notes"},
        )

        link.refresh_from_db()
        self.assertEqual(link.local_objective, "Au tableau, sans notes")

    def test_two_competencies_cannot_share_a_title_in_one_path(self):
        competency_in(self.oraux5, title="Rédiger une démonstration")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Competency.objects.create(path=self.path, title="Rédiger une démonstration")

    def test_a_link_across_two_paths_is_refused(self):
        other = LearningPath.objects.create(owner=self.user, title="DU Statistique")
        other_period = Period.objects.create(path=other, title="Bloc")
        other_unit = LearningUnit.objects.create(period=other_period, title="R")
        competency = competency_in(self.oraux5, title="Rédiger une démonstration")

        link = UnitCompetency(unit=other_unit, competency=competency)
        with self.assertRaises(ValidationError):
            link.full_clean()

    def test_a_period_of_another_path_is_refused(self):
        other = LearningPath.objects.create(owner=self.user, title="DU Statistique")
        other_period = Period.objects.create(path=other, title="Bloc")
        competency = Competency(path=self.path, period=other_period, title="Ailleurs")
        with self.assertRaises(ValidationError):
            competency.full_clean()

    def test_the_primary_unit_is_the_one_declared_primary(self):
        competency = competency_in(self.oraux6, title="Rédiger une démonstration", is_primary=False)
        share_competency(competency, self.oraux5, is_primary=True)
        self.assertEqual(competency.primary_unit, self.oraux5)

    def test_a_transversal_competency_keeps_a_usable_trail(self):
        competency = Competency.objects.create(path=self.path, title="Travailler régulièrement")
        response = self.client.get(reverse("formations:competency", args=[competency.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "L3 Mathématiques")
        self.assertContains(response, "rattachée à aucune matière")

    def test_the_tracking_order_no_longer_depends_on_a_single_unit(self):
        first = competency_in(self.oraux5, title="A", order=1)
        second = competency_in(self.oraux6, title="B", order=2)
        ensure_progress_records(self.user, self.path)
        titles = [record.competency.title for record in tracked_records(self.user, self.path)]
        self.assertEqual(titles, [first.title, second.title])


class SelfAssessmentTests(TestCase):
    """Le suivi personnel reste distinct de la définition de la compétence."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie")
        self.competency = competency_in(self.unit, title="Établir la compacité")

    def test_a_record_created_by_the_grid_is_not_marked_as_assessed(self):
        ensure_progress_records(self.user, self.path)
        record = ProgressRecord.objects.get(competency=self.competency)
        self.assertEqual(record.mastery_level, 0)
        self.assertIsNone(record.assessed_at)

    def test_changing_the_level_stamps_the_assessment_date(self):
        ensure_progress_records(self.user, self.path)
        record = ProgressRecord.objects.get(competency=self.competency)

        record.mastery_level = 3
        record.save()

        record.refresh_from_db()
        self.assertIsNotNone(record.assessed_at)
        self.assertLess((timezone.now() - record.assessed_at).total_seconds(), 30)

    def test_saving_without_changing_the_level_keeps_the_previous_date(self):
        ensure_progress_records(self.user, self.path)
        record = ProgressRecord.objects.get(competency=self.competency)
        record.mastery_level = 2
        record.save()
        stamped = ProgressRecord.objects.get(pk=record.pk).assessed_at

        fresh = ProgressRecord.objects.get(pk=record.pk)
        fresh.notes = "Revoir Heine"
        fresh.save()

        self.assertEqual(ProgressRecord.objects.get(pk=record.pk).assessed_at, stamped)

    def test_a_level_is_declared_by_the_student_by_default(self):
        ensure_progress_records(self.user, self.path)
        record = ProgressRecord.objects.get(competency=self.competency)
        self.assertEqual(record.level_origin, ProgressRecord.Origin.MANUAL)

    def test_a_target_can_be_set_below_full_mastery(self):
        ensure_progress_records(self.user, self.path)
        response = self.client.post(
            reverse("formations:progress", args=[self.competency.pk]),
            {
                "mastery_level": 2,
                "target_level": 3,
                "target_date": "2026-01-15",
                "planned_hours": "4",
                "actual_hours": "1",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        record = ProgressRecord.objects.get(competency=self.competency)
        self.assertEqual(record.target_level, 3)
        self.assertFalse(record.reaches_target)

    def test_without_a_target_nothing_is_claimed(self):
        ensure_progress_records(self.user, self.path)
        record = ProgressRecord.objects.get(competency=self.competency)
        self.assertIsNone(record.reaches_target)

    def test_time_spent_never_changes_the_level(self):
        """Dix heures passées ne prouvent pas la maîtrise : rien n'est déduit."""
        ensure_progress_records(self.user, self.path)
        record = ProgressRecord.objects.get(competency=self.competency)
        record.actual_hours = Decimal("10")
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.mastery_level, 0)
        self.assertIsNone(record.assessed_at)
