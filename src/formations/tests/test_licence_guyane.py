"""La maquette de la L3 : granularité, idempotence et élagage prudent."""

from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from formations.management.commands.load_licence_guyane import (
    PROGRAMME,
    declared_titles,
    expected_titles,
    readable_share,
)
from formations.models import Competency, LearningPath, LearningUnit, ProgressRecord
from formations.tests.factories import competency_in
from library.models import LibraryItem


class ProgrammeShapeTests(TestCase):
    """Un module de 50 heures découpé en trois lignes ne permet pas de se suivre."""

    def test_every_module_declares_at_least_five_competencies(self):
        for period, matieres in PROGRAMME.items():
            for titre, _ue, _h, _ects, _nature, competences in matieres:
                with self.subTest(module=f"{period} · {titre}"):
                    self.assertGreaterEqual(len(competences), 5)

    def test_a_core_module_is_split_at_the_granularity_of_a_syllabus(self):
        """Un semestre de topologie, c'est une trentaine de savoir-faire distincts.

        Le seuil vaut par heure encadrée plutôt qu'en absolu : un module de 50 heures et
        un module de 18 heures n'ont pas la même étendue à couvrir.
        """
        for period, matieres in PROGRAMME.items():
            for titre, _ue, hours, _ects, _nature, competences in matieres:
                if hours < 36:
                    continue
                with self.subTest(module=f"{period} · {titre}", heures=hours):
                    self.assertGreaterEqual(len(competences), hours // 3)

    def test_no_module_repeats_a_competency(self):
        for period, matieres in PROGRAMME.items():
            for titre, _ue, _h, _ects, _nature, competences in matieres:
                with self.subTest(module=f"{period} · {titre}"):
                    self.assertEqual(len(competences), len(set(competences)))

    def test_a_competency_is_worded_as_a_know_how(self):
        """Un intitulé nommant un chapitre ne dit pas ce qu'il faut savoir faire."""
        for matieres in PROGRAMME.values():
            for titre, _ue, _h, _ects, _nature, competences in matieres:
                for competence in competences:
                    with self.subTest(module=titre, competence=competence):
                        self.assertGreater(len(competence.split()), 2)


class ReadableShareTests(TestCase):
    """« 2 h 30 » se retient ; « 2,25 h » se lit même de travers, comme 2 h 25.

    Le total dépasse alors l'estimation du module, et c'est le compromis voulu : une durée
    qu'on lit d'un coup d'œil vaut mieux qu'une division exacte au centième d'heure.
    """

    def test_a_share_is_rounded_up_to_the_half_hour(self):
        self.assertEqual(readable_share(Decimal("47"), 20), Decimal("2.5"))  # 2 h 21 → 2 h 30
        self.assertEqual(readable_share(Decimal("75"), 34), Decimal("2.5"))  # 2 h 12 → 2 h 30
        self.assertEqual(readable_share(Decimal("75"), 29), Decimal("3"))  # 2 h 35 → 3 h
        self.assertEqual(readable_share(Decimal("9"), 8), Decimal("1.5"))  # 1 h 07 → 1 h 30

    def test_an_exact_half_hour_is_left_alone(self):
        self.assertEqual(readable_share(Decimal("12"), 8), Decimal("1.5"))
        self.assertEqual(readable_share(Decimal("12"), 4), Decimal("3"))

    def test_a_share_is_never_rounded_down(self):
        for hours in (9, 18, 24, 36, 50, 56, 75, 84):
            for count in range(3, 35):
                with self.subTest(hours=hours, count=count):
                    self.assertGreaterEqual(readable_share(Decimal(hours), count), Decimal(hours) / count)


class LoadCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")

    def load(self, **options):
        out = StringIO()
        call_command("load_licence_guyane", username="alice", stdout=out, **options)
        return out.getvalue()

    def test_the_programme_is_loaded_with_its_full_granularity(self):
        self.load()
        path = LearningPath.objects.get(owner=self.user)
        topology = LearningUnit.objects.get(period__path=path, title="Topologie")
        self.assertGreaterEqual(topology.competencies.count(), 10)
        self.assertEqual(
            Competency.objects.filter(path=path).count(),
            # Un intitulé déclaré par deux modules ne compte qu'une fois : c'est le
            # principe même de la compétence transversale.
            len(declared_titles()),
        )

    def test_a_competency_declared_by_two_modules_exists_once(self):
        """Les oraux reviennent aux deux semestres : un seul savoir-faire, deux matières."""
        self.load()
        shared = Competency.objects.get(title="Rédiger une démonstration au tableau, lisiblement")

        self.assertEqual(shared.units.count(), 2)
        self.assertEqual(sorted(unit.period.title for unit in shared.units.all()), ["Semestre 5", "Semestre 6"])
        # Transversale : elle n'est enfermée dans aucune période.
        self.assertIsNone(shared.period)

    def test_a_shared_competency_has_a_single_progress_record(self):
        self.load()
        shared = Competency.objects.get(title="Construire un plan progressif")
        self.assertEqual(ProgressRecord.objects.filter(owner=self.user, competency=shared).count(), 1)

    def test_the_units_carry_the_declared_unit_of_teaching(self):
        self.load()
        topology = LearningUnit.objects.get(title="Topologie")
        self.assertIsNotNone(topology.group)
        self.assertEqual(topology.group.title, "UEO Mathématiques 5")
        self.assertEqual(topology.group.kind, "UE")

    def test_loading_twice_does_not_duplicate_anything(self):
        self.load()
        before = Competency.objects.count()
        self.load()
        self.assertEqual(Competency.objects.count(), before)

    def test_loading_again_keeps_the_progress_already_entered(self):
        self.load()
        competency = Competency.objects.filter(units__title="Topologie").first()
        ProgressRecord.objects.filter(owner=self.user, competency=competency).update(
            mastery_level=3, actual_hours=Decimal("7.5"), notes="Revoir Heine"
        )

        self.load()

        record = ProgressRecord.objects.get(owner=self.user, competency=competency)
        self.assertEqual(record.mastery_level, 3)
        self.assertEqual(record.actual_hours, Decimal("7.5"))
        self.assertEqual(record.notes, "Revoir Heine")

    def test_the_output_says_the_breakdown_is_not_official(self):
        self.assertIn("proposition pédagogique", self.load())

    def test_without_prune_an_older_breakdown_survives(self):
        self.load()
        unit = LearningUnit.objects.get(title="Topologie")
        competency_in(unit, title="Ancien chapitre", order=99)

        self.load()

        self.assertTrue(Competency.objects.filter(title="Ancien chapitre").exists())

    def test_prune_removes_a_competency_absent_from_the_programme(self):
        self.load()
        unit = LearningUnit.objects.get(title="Topologie")
        competency_in(unit, title="Ancien chapitre", order=99)

        output = self.load(prune=True)

        self.assertFalse(Competency.objects.filter(title="Ancien chapitre").exists())
        self.assertIn("1 retirées", output)

    def test_prune_keeps_a_competency_where_work_was_recorded(self):
        self.load()
        unit = LearningUnit.objects.get(title="Topologie")
        worked = competency_in(unit, title="Chapitre travaillé", order=98)
        ProgressRecord.objects.create(owner=self.user, competency=worked, mastery_level=2)

        self.load(prune=True)

        self.assertTrue(Competency.objects.filter(pk=worked.pk).exists())

    def test_prune_keeps_a_competency_with_a_linked_resource(self):
        self.load()
        unit = LearningUnit.objects.get(title="Topologie")
        kept = competency_in(unit, title="Chapitre documenté", order=97)
        resource = LibraryItem.objects.create(owner=self.user, kind=LibraryItem.Kind.NOTE, title="Fiche", note_text="x")
        kept.resources.add(resource)

        self.load(prune=True)

        self.assertTrue(Competency.objects.filter(pk=kept.pk).exists())

    def test_prune_keeps_a_competency_carrying_only_a_comment(self):
        self.load()
        unit = LearningUnit.objects.get(title="Topologie")
        kept = competency_in(unit, title="Chapitre annoté", order=96)
        ProgressRecord.objects.create(owner=self.user, competency=kept, notes="à revoir avant le partiel")

        self.load(prune=True)

        self.assertTrue(Competency.objects.filter(pk=kept.pk).exists())

    def test_prune_never_touches_what_the_programme_declares(self):
        self.load()
        expected = expected_titles()
        self.load(prune=True)
        for unit in LearningUnit.objects.all():
            for title in expected[unit.title]:
                with self.subTest(unit=unit.title, title=title):
                    self.assertTrue(Competency.objects.filter(units=unit, title=title).exists())

    def test_personal_hours_are_spread_over_every_competency(self):
        self.load()
        unit = LearningUnit.objects.get(title="Topologie")
        records = ProgressRecord.objects.filter(owner=self.user, competency__units=unit)
        self.assertEqual(records.count(), unit.competencies.count())
        for record in records:
            self.assertGreater(record.planned_hours, 0)

    def test_every_estimate_falls_on_a_readable_half_hour(self):
        self.load()
        for record in ProgressRecord.objects.filter(owner=self.user):
            with self.subTest(competency=record.competency.title):
                self.assertEqual(record.planned_hours % Decimal("0.5"), 0)

    def test_the_output_admits_the_redistribution_exceeds_the_estimate(self):
        output = self.load()
        self.assertIn("Réparti par demi-heures", output)

    def test_an_estimate_already_present_is_kept_by_default(self):
        self.load()
        record = ProgressRecord.objects.filter(owner=self.user).first()
        ProgressRecord.objects.filter(pk=record.pk).update(planned_hours=Decimal("42"))

        self.load()

        self.assertEqual(ProgressRecord.objects.get(pk=record.pk).planned_hours, Decimal("42"))

    def test_reset_hours_rewrites_the_estimate_but_not_the_work(self):
        self.load()
        record = ProgressRecord.objects.filter(owner=self.user).first()
        ProgressRecord.objects.filter(pk=record.pk).update(
            planned_hours=Decimal("42"), actual_hours=Decimal("3"), mastery_level=2
        )

        self.load(reset_hours=True)

        refreshed = ProgressRecord.objects.get(pk=record.pk)
        self.assertNotEqual(refreshed.planned_hours, Decimal("42"))
        self.assertEqual(refreshed.actual_hours, Decimal("3"))
        self.assertEqual(refreshed.mastery_level, 2)
