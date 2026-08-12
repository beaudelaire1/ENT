"""Modifier ce qu'on a créé.

La moitié des objets structurants n'avaient pas d'écran de modification : corriger le
libellé d'une période supposait de la supprimer — donc de perdre ses matières, ses
compétences et leur progression — puis de tout recréer.
"""

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
from library.models import LibraryItem


class EditingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.unit = LearningUnit.objects.create(period=self.period, title="TOPOLOGIE", order=1)
        self.competency = Competency.objects.create(unit=self.unit, title="Compacité", order=1)
        self.metric = MetricDefinition.objects.create(path=self.path, key="ects", label="ECTS")

    # ------------------------------------------------------------------ périodes

    def test_a_period_can_be_renamed(self):
        response = self.client.post(
            reverse("formations:period_edit", args=[self.period.pk]), {"title": "Semestre 6", "order": 6}
        )
        self.assertRedirects(response, reverse("formations:detail", args=[self.path.pk]))
        self.period.refresh_from_db()
        self.assertEqual(self.period.title, "Semestre 6")

    def test_renaming_a_period_keeps_its_units_and_progress(self):
        ProgressRecord.objects.create(owner=self.user, competency=self.competency, mastery_level=3)
        self.client.post(reverse("formations:period_edit", args=[self.period.pk]), {"title": "Semestre 6", "order": 6})

        self.assertEqual(LearningUnit.objects.filter(period=self.period).count(), 1)
        self.assertEqual(Competency.objects.filter(unit=self.unit).count(), 1)
        self.assertEqual(ProgressRecord.objects.get(competency=self.competency).mastery_level, 3)

    def test_a_duplicate_period_title_is_a_form_error_not_a_crash(self):
        Period.objects.create(path=self.path, title="Semestre 6", order=6)
        response = self.client.post(
            reverse("formations:period_edit", args=[self.period.pk]), {"title": "Semestre 6", "order": 5}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "existe déjà")
        self.period.refresh_from_db()
        self.assertEqual(self.period.title, "Semestre 5")

    # ------------------------------------------------------------------ matières

    def test_a_unit_can_be_edited_without_losing_its_metrics(self):
        MetricValue.objects.create(definition=self.metric, unit=self.unit, value=Decimal("6"))
        response = self.client.post(
            reverse("formations:unit_edit", args=[self.unit.pk]),
            {"title": "Topologie générale", "description": "", "order": 1},
        )
        self.assertRedirects(response, reverse("formations:unit", args=[self.unit.pk]))
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.title, "Topologie générale")
        self.assertEqual(MetricValue.objects.get(unit=self.unit).value, Decimal("6"))

    def test_editing_a_unit_keeps_its_linked_resources(self):
        resource = LibraryItem.objects.create(owner=self.user, kind=LibraryItem.Kind.NOTE, title="Fiche", note_text="x")
        self.unit.resources.add(resource)
        self.client.post(
            reverse("formations:unit_edit", args=[self.unit.pk]),
            {"title": "Topologie", "description": "", "order": 1, "resources": [resource.pk]},
        )
        self.assertEqual(list(self.unit.resources.all()), [resource])

    # --------------------------------------------------------------- compétences

    def test_a_competency_can_be_edited(self):
        response = self.client.post(
            reverse("formations:competency_edit", args=[self.competency.pk]),
            {"title": "Compacité et connexité", "description": "Bolzano-Weierstrass", "order": 1},
        )
        self.assertRedirects(response, reverse("formations:competency", args=[self.competency.pk]))
        self.competency.refresh_from_db()
        self.assertEqual(self.competency.title, "Compacité et connexité")

    def test_editing_a_competency_keeps_the_progress_record(self):
        ProgressRecord.objects.create(
            owner=self.user, competency=self.competency, mastery_level=2, actual_hours=Decimal("4")
        )
        self.client.post(
            reverse("formations:competency_edit", args=[self.competency.pk]),
            {"title": "Compacité (revu)", "description": "", "order": 1},
        )
        record = ProgressRecord.objects.get(competency=self.competency)
        self.assertEqual(record.mastery_level, 2)
        self.assertEqual(record.actual_hours, Decimal("4"))

    # ------------------------------------------------------------ colonnes de suivi

    def test_a_metric_definition_can_be_edited(self):
        response = self.client.post(
            reverse("formations:metric_edit", args=[self.metric.pk]),
            {"key": "ects", "label": "Crédits ECTS", "unit_label": "", "order": 1, "decimal_places": 0},
        )
        self.assertRedirects(response, reverse("formations:detail", args=[self.path.pk]))
        self.metric.refresh_from_db()
        self.assertEqual(self.metric.label, "Crédits ECTS")
        self.assertEqual(self.metric.decimal_places, 0)

    def test_editing_a_metric_keeps_the_values_already_entered(self):
        MetricValue.objects.create(definition=self.metric, unit=self.unit, value=Decimal("6"))
        self.client.post(
            reverse("formations:metric_edit", args=[self.metric.pk]),
            {"key": "ects", "label": "Crédits", "unit_label": "", "order": 1, "decimal_places": 2},
        )
        self.assertEqual(MetricValue.objects.get(definition=self.metric).value, Decimal("6"))

    def test_a_new_metric_starts_with_a_minimum_of_zero(self):
        response = self.client.get(reverse("formations:metric_new", args=[self.path.pk]))
        self.assertEqual(response.context["form"].fields["min_value"].initial, 0)

    # -------------------------------------------------------------- isolation

    def test_another_users_objects_are_not_editable(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign_path = LearningPath.objects.create(owner=bob, title="Privé")
        foreign_period = Period.objects.create(path=foreign_path, title="Bloc")
        foreign_unit = LearningUnit.objects.create(period=foreign_period, title="Unité")
        foreign_competency = Competency.objects.create(unit=foreign_unit, title="Compétence")
        foreign_metric = MetricDefinition.objects.create(path=foreign_path, key="k", label="K")

        for url in (
            reverse("formations:period_edit", args=[foreign_period.pk]),
            reverse("formations:unit_edit", args=[foreign_unit.pk]),
            reverse("formations:competency_edit", args=[foreign_competency.pk]),
            reverse("formations:competency", args=[foreign_competency.pk]),
            reverse("formations:metric_edit", args=[foreign_metric.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    # ----------------------------------------------------------- retour contextuel

    def test_the_edit_screen_offers_a_way_out(self):
        response = self.client.get(reverse("formations:period_edit", args=[self.period.pk]))
        self.assertContains(response, "Annuler")
        self.assertContains(response, reverse("formations:detail", args=[self.path.pk]))

    def test_saving_returns_to_the_page_that_asked(self):
        origin = reverse("formations:tracking", args=[self.path.pk])
        response = self.client.post(
            f"{reverse('formations:period_edit', args=[self.period.pk])}?next={origin}",
            {"title": "Semestre 5 bis", "order": 5, "next": origin},
        )
        self.assertRedirects(response, origin)

    def test_an_external_return_address_is_ignored(self):
        """`next` vient de l'extérieur : il ne doit pas servir de tremplin."""
        response = self.client.post(
            reverse("formations:period_edit", args=[self.period.pk]),
            {"title": "Semestre 5 ter", "order": 5, "next": "https://exemple-malveillant.test/piege"},
        )
        self.assertRedirects(response, reverse("formations:detail", args=[self.path.pk]))

    # ------------------------------------------------------------- fil d'Ariane

    def test_a_unit_page_shows_where_it_belongs(self):
        response = self.client.get(reverse("formations:unit", args=[self.unit.pk]))
        self.assertContains(response, "Fil d’Ariane")
        self.assertContains(response, "L3 Mathématiques")
        self.assertContains(response, "Semestre 5")

    def test_a_competency_page_leads_back_to_its_unit_and_path(self):
        response = self.client.get(reverse("formations:competency", args=[self.competency.pk]))
        self.assertContains(response, reverse("formations:unit", args=[self.unit.pk]))
        self.assertContains(response, reverse("formations:detail", args=[self.path.pk]))

    def test_a_competency_without_resource_says_where_to_find_one(self):
        response = self.client.get(reverse("formations:competency", args=[self.competency.pk]))
        self.assertContains(response, "Aucune ressource associée")
        self.assertContains(response, reverse("library:list"))

    def test_the_unit_page_lists_each_competency_with_its_level(self):
        ProgressRecord.objects.create(owner=self.user, competency=self.competency, mastery_level=3)
        response = self.client.get(reverse("formations:unit", args=[self.unit.pk]))
        self.assertContains(response, "3 - Acquis")
        self.assertContains(response, reverse("formations:competency", args=[self.competency.pk]))
