"""Les paliers de temps : ce qu'ils proposent, et ce qu'ils s'interdisent."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.models import Competency, LearningPath, LearningUnit, Period, ProgressRecord
from formations.progression import level_for_ratio


class ThresholdTests(TestCase):
    """La règle nue, sans base de données."""

    def test_each_quarter_raises_the_level(self):
        expected = {
            "0": 0,
            "0.24": 0,
            "0.25": 1,
            "0.49": 1,
            "0.50": 2,
            "0.74": 2,
            "0.75": 3,
            "0.99": 3,
            "1": 4,
        }
        for ratio, level in expected.items():
            with self.subTest(ratio=ratio):
                self.assertEqual(level_for_ratio(Decimal(ratio)), level)

    def test_beyond_the_estimate_the_level_is_capped(self):
        self.assertEqual(level_for_ratio(Decimal("3")), 4)


class ProgressRecordTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("etudiant", password="motdepasse")
        self.path = LearningPath.objects.create(owner=self.user, title="Licence")
        period = Period.objects.create(path=self.path, title="Semestre 5")
        LearningUnit.objects.create(period=period, title="Topologie")
        self.competency = Competency.objects.create(path=self.path, title="Rédiger une démonstration")

    def record(self, **fields):
        return ProgressRecord.objects.create(owner=self.user, competency=self.competency, **fields)

    def reload(self, record):
        return ProgressRecord.objects.select_related("competency__path").get(pk=record.pk)


class AutomaticLevelTests(ProgressRecordTestCase):
    def test_without_an_estimate_nothing_moves(self):
        """Pas de dénominateur, pas de palier : une compétence non estimée reste au repos."""
        record = self.record(planned_hours=Decimal(0), manual_hours=Decimal(10))
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.NOT_STARTED)

    def test_a_quarter_of_the_estimate_marks_the_competency_as_discovered(self):
        record = self.record(planned_hours=Decimal(12), manual_hours=Decimal(3))
        stored = self.reload(record)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.DISCOVERED)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.SUGGESTED)

    def test_just_below_a_quarter_does_not(self):
        record = self.record(planned_hours=Decimal(12), manual_hours=Decimal("2.9"))
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.NOT_STARTED)

    def test_the_following_quarters_raise_the_level(self):
        record = self.record(planned_hours=Decimal(12))
        for hours, level in (
            (6, ProgressRecord.Mastery.IN_PROGRESS),
            (9, ProgressRecord.Mastery.ACQUIRED),
            (12, ProgressRecord.Mastery.MASTERED),
        ):
            with self.subTest(hours=hours):
                record.manual_hours = Decimal(hours)
                record.save()
                self.assertEqual(self.reload(record).mastery_level, level)

    def test_working_far_beyond_the_estimate_stops_at_mastered(self):
        record = self.record(planned_hours=Decimal(2), manual_hours=Decimal(40))
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.MASTERED)

    def test_a_suggestion_does_not_pretend_to_be_a_self_assessment(self):
        """`assessed_at` signifie « dernière autoévaluation » : personne n'a rien évalué."""
        record = self.record(planned_hours=Decimal(12), manual_hours=Decimal(6))
        self.assertIsNone(self.reload(record).assessed_at)

    def test_raising_the_estimate_never_demotes(self):
        """Découvrir qu'un chapitre est plus long ne doit pas défaire ce qui est travaillé."""
        record = self.record(planned_hours=Decimal(4), manual_hours=Decimal(4))
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.MASTERED)
        record = self.reload(record)
        record.planned_hours = Decimal(40)
        record.save()
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.MASTERED)

    def test_the_switch_on_the_path_disables_the_whole_mechanism(self):
        self.path.time_suggests_level = False
        self.path.save(update_fields=["time_suggests_level"])
        record = self.record(planned_hours=Decimal(12), manual_hours=Decimal(12))
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.NOT_STARTED)

    def test_the_switch_is_read_from_the_stored_path(self):
        """La lecture passe par la formation liée, pas par une valeur restée en mémoire."""
        record = self.reload(self.record(planned_hours=Decimal(12)))
        LearningPath.objects.filter(pk=self.path.pk).update(time_suggests_level=False)
        record = self.reload(record)
        record.manual_hours = Decimal(12)
        record.save()
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.NOT_STARTED)


class DeclaredLevelTests(ProgressRecordTestCase):
    def declared(self, level=ProgressRecord.Mastery.IN_PROGRESS):
        record = self.record(planned_hours=Decimal(12))
        record = self.reload(record)
        record.mastery_level = level
        record.save()
        return self.reload(record)

    def test_declaring_a_level_dates_it_and_claims_it(self):
        record = self.declared()
        self.assertEqual(record.level_origin, ProgressRecord.Origin.MANUAL)
        self.assertIsNotNone(record.assessed_at)

    def test_a_declared_level_is_never_overwritten_by_time(self):
        """Sinon la correction de l'étudiant serait défaite à la session suivante."""
        record = self.declared()
        record.manual_hours = Decimal(12)
        record.save()
        stored = self.reload(record)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.IN_PROGRESS)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.MANUAL)

    def test_the_proposal_is_then_offered_instead_of_applied(self):
        record = self.declared()
        record.manual_hours = Decimal(12)
        record.save()
        self.assertEqual(self.reload(record).pending_level, ProgressRecord.Mastery.MASTERED)

    def test_no_proposal_when_time_is_behind_the_declared_level(self):
        record = self.declared(ProgressRecord.Mastery.MASTERED)
        record.manual_hours = Decimal(3)
        record.save()
        self.assertIsNone(self.reload(record).pending_level)

    def test_correcting_a_suggested_level_downwards_holds(self):
        """Le cas qui donne son sens à « l'utilisateur pourra toujours modifier »."""
        record = self.record(planned_hours=Decimal(12), manual_hours=Decimal(12))
        record = self.reload(record)
        self.assertEqual(record.mastery_level, ProgressRecord.Mastery.MASTERED)
        record.mastery_level = ProgressRecord.Mastery.DISCOVERED
        record.save()
        record = self.reload(record)
        record.manual_hours = Decimal(24)
        record.save()
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.DISCOVERED)


class AdoptionTests(ProgressRecordTestCase):
    def test_confirming_a_suggested_level_makes_it_personal(self):
        record = self.reload(self.record(planned_hours=Decimal(12), manual_hours=Decimal(6)))
        self.assertTrue(record.adopt_suggested_level())
        stored = self.reload(record)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.IN_PROGRESS)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.MANUAL)
        self.assertIsNotNone(stored.assessed_at)

    def test_adopting_a_pending_proposal_raises_the_level(self):
        record = self.reload(self.record(planned_hours=Decimal(12)))
        record.mastery_level = ProgressRecord.Mastery.DISCOVERED
        record.save()
        record = self.reload(record)
        record.manual_hours = Decimal(12)
        record.save()
        record = self.reload(record)
        self.assertTrue(record.adopt_suggested_level())
        self.assertEqual(self.reload(record).mastery_level, ProgressRecord.Mastery.MASTERED)

    def test_nothing_to_adopt_reports_it(self):
        record = self.reload(self.record(planned_hours=Decimal(12)))
        record.mastery_level = ProgressRecord.Mastery.MASTERED
        record.save()
        self.assertFalse(self.reload(record).adopt_suggested_level())

    def test_an_adopted_level_survives_more_time(self):
        record = self.reload(self.record(planned_hours=Decimal(12), manual_hours=Decimal(3)))
        record.adopt_suggested_level()
        stamped = self.reload(record).assessed_at
        record = self.reload(record)
        record.manual_hours = Decimal(12)
        record.save()
        stored = self.reload(record)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.DISCOVERED)
        self.assertEqual(stored.assessed_at, stamped)


class AdoptionViewTests(ProgressRecordTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.url = reverse("formations:progress_adopt", args=[self.competency.pk])

    def test_adopting_from_the_page_makes_the_level_personal(self):
        self.record(planned_hours=Decimal(12), manual_hours=Decimal(6))
        response = self.client.post(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        stored = ProgressRecord.objects.get(owner=self.user, competency=self.competency)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.MANUAL)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.IN_PROGRESS)

    def test_a_get_is_refused(self):
        """Une adoption modifie une donnée : elle ne se déclenche pas en suivant un lien."""
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_another_account_cannot_adopt(self):
        other = get_user_model().objects.create_user("intruse", password="motdepasse")
        self.client.force_login(other)
        self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_the_competency_page_offers_the_confirmation(self):
        self.record(planned_hours=Decimal(12), manual_hours=Decimal(6))
        response = self.client.get(reverse("formations:competency", args=[self.competency.pk]))
        self.assertContains(response, "Confirmer ce niveau")
        self.assertContains(response, "suggéré par le temps")

    def test_the_page_stays_silent_without_a_suggestion(self):
        self.record(planned_hours=Decimal(0), manual_hours=Decimal(6))
        response = self.client.get(reverse("formations:competency", args=[self.competency.pk]))
        self.assertNotContains(response, "Confirmer ce niveau")


class TrackingGridTests(ProgressRecordTestCase):
    """La grille signale le palier sans jamais imbriquer un formulaire dans un autre."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_a_suggested_level_is_marked_in_the_grid(self):
        self.record(planned_hours=Decimal(12), manual_hours=Decimal(6))
        response = self.client.get(reverse("formations:tracking", args=[self.path.pk]))
        self.assertContains(response, "chip static suggested")

    def test_saving_the_grid_can_raise_a_level_by_time_alone(self):
        record = self.record(planned_hours=Decimal(12))
        response = self.client.post(
            reverse("formations:tracking", args=[self.path.pk]),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": str(record.pk),
                "form-0-planned_hours": "12",
                "form-0-manual_hours": "9",
                "form-0-mastery_level": "0",
                "form-0-notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        stored = self.reload(record)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.ACQUIRED)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.SUGGESTED)
        self.assertIsNone(stored.assessed_at)

    def test_a_level_typed_in_the_grid_wins_over_the_time(self):
        record = self.record(planned_hours=Decimal(12))
        self.client.post(
            reverse("formations:tracking", args=[self.path.pk]),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": str(record.pk),
                "form-0-planned_hours": "12",
                "form-0-manual_hours": "12",
                "form-0-mastery_level": "1",
                "form-0-notes": "",
            },
        )
        stored = self.reload(record)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.DISCOVERED)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.MANUAL)
        self.assertIsNotNone(stored.assessed_at)


class DeferredLoadTests(ProgressRecordTestCase):
    """Une instance chargée sans tous ses champs ne doit pas en réclamer d'autres.

    Django diffère les champs qu'il n'utilise pas — au ramassage d'une suppression en
    cascade, notamment. Retenir les valeurs en lisant les attributs y déclenchait un
    rechargement, donc un nouvel appel de `from_db`, et la récursion n'avait pas de fin.
    """

    def test_a_deferred_record_can_be_loaded(self):
        record = self.record(planned_hours=Decimal(12), manual_hours=Decimal(6))
        partial = ProgressRecord.objects.only("pk", "owner").get(pk=record.pk)
        self.assertEqual(partial.pk, record.pk)

    def test_deleting_a_competency_cascades_without_recursion(self):
        self.record(planned_hours=Decimal(12), manual_hours=Decimal(6))
        self.competency.delete()
        self.assertEqual(ProgressRecord.objects.count(), 0)

    def test_deleting_the_path_takes_everything_with_it(self):
        self.record(planned_hours=Decimal(12), manual_hours=Decimal(12))
        self.path.delete()
        self.assertEqual(ProgressRecord.objects.count(), 0)


class SablierSessionTests(ProgressRecordTestCase):
    """Le chemin le plus fréquent : le temps arrive par une session, pas par la grille."""

    def test_a_session_crossing_a_threshold_raises_the_level(self):
        from sablier.services import record_session

        ProgressRecord.objects.create(owner=self.user, competency=self.competency, planned_hours=Decimal(4))
        record_session(
            self.user,
            seconds=3600,
            started_at=timezone.now(),
            intention="Révision",
            competency=self.competency,
        )
        stored = ProgressRecord.objects.get(owner=self.user, competency=self.competency)
        self.assertEqual(stored.session_hours, Decimal(1))
        self.assertEqual(stored.actual_hours, Decimal(1))
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.DISCOVERED)
        self.assertEqual(stored.level_origin, ProgressRecord.Origin.SUGGESTED)

    def test_a_session_does_not_overwrite_a_declared_level(self):
        from sablier.services import record_session

        record = ProgressRecord.objects.create(owner=self.user, competency=self.competency, planned_hours=Decimal(4))
        record = self.reload(record)
        record.mastery_level = ProgressRecord.Mastery.IN_PROGRESS
        record.save()
        record_session(
            self.user,
            seconds=4 * 3600,
            started_at=timezone.now(),
            intention="",
            competency=self.competency,
        )
        stored = self.reload(record)
        self.assertEqual(stored.mastery_level, ProgressRecord.Mastery.IN_PROGRESS)
        self.assertEqual(stored.pending_level, ProgressRecord.Mastery.MASTERED)
