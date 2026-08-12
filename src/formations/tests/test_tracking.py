from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from formations.forms import ProgressRowFormSet
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
        self.coefficient = MetricDefinition.objects.create(
            path=self.path, key="coefficient", label="Coefficient", order=1
        )
        MetricValue.objects.create(definition=self.coefficient, unit=self.unit, value=Decimal("5"))

    def url(self):
        return reverse("formations:tracking", args=[self.path.pk])

    def payload(self, *, mastery_level="0", planned_hours="0", actual_hours="0", notes="", metrics=None):
        """Un envoi complet de la grille, tel que le navigateur le produit."""
        records = list(tracked_records(self.user, self.path))
        data = {
            "form-TOTAL_FORMS": str(len(records)),
            "form-INITIAL_FORMS": str(len(records)),
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        for index, record in enumerate(records):
            data |= {
                f"form-{index}-id": str(record.pk),
                f"form-{index}-planned_hours": planned_hours,
                f"form-{index}-actual_hours": actual_hours,
                f"form-{index}-mastery_level": mastery_level,
                f"form-{index}-notes": notes,
            }
        for definition, raw in (metrics or {}).items():
            data[f"metric_{self.unit.pk}_{definition.pk}"] = raw
        return data

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
        unit_totals = grid["periods"][0]["units"][0]["totals"]

        self.assertEqual(unit_totals["planned"], Decimal("15"))
        self.assertEqual(unit_totals["actual"], Decimal("6"))
        self.assertEqual(unit_totals["percent"], 75)
        self.assertEqual(grid["periods"][0]["totals"]["percent"], 75)

    def test_columns_are_the_metrics_the_path_declares(self):
        MetricDefinition.objects.create(path=self.path, key="stage", label="Jours de stage", unit_label="j", order=2)
        MetricValue.objects.create(
            definition=MetricDefinition.objects.get(path=self.path, key="stage"),
            unit=self.unit,
            value=Decimal("12"),
        )

        response = self.client.get(self.url())
        grid = response.context["grid"]

        self.assertEqual([d.key for d in grid["definitions"]], ["coefficient", "stage"])
        self.assertEqual(grid["metric_count"], 2)
        self.assertEqual(grid["column_count"], 8)
        self.assertEqual(
            [cell["value"] for cell in grid["periods"][0]["units"][0]["cells"]], [Decimal("5"), Decimal("12")]
        )
        self.assertContains(response, "Jours de stage (j)")

    def test_a_path_without_metric_renders_only_the_fixed_columns(self):
        MetricValue.objects.all().delete()
        MetricDefinition.objects.all().delete()

        response = self.client.get(self.url())
        grid = response.context["grid"]

        self.assertEqual(grid["definitions"], [])
        self.assertEqual(grid["column_count"], 6)
        self.assertEqual(grid["periods"][0]["units"][0]["cells"], [])
        self.assertNotContains(response, "Coefficient")
        self.assertNotContains(response, 'colspan="0"')

    def test_a_metric_left_empty_for_a_unit_shows_a_placeholder(self):
        LearningUnit.objects.create(period=self.period, title="ALGÈBRE", order=2)
        response = self.client.get(self.url())
        grid = response.context["grid"]
        self.assertEqual([cell["value"] for cell in grid["periods"][0]["units"][1]["cells"]], [None])

    def test_the_grid_follows_the_declared_order_not_the_alphabet(self):
        LearningUnit.objects.create(period=self.period, title="ALGÈBRE", order=2)
        Competency.objects.create(unit=self.unit, title="Axiomes", order=3)

        response = self.client.get(self.url())
        grid = build_tracking_grid(self.path, response.context["formset"])
        units = [unit["unit"].title for unit in grid["periods"][0]["units"]]
        titles = [row["competency"].title for row in grid["periods"][0]["units"][0]["rows"]]

        self.assertEqual(units, ["TOPOLOGIE", "ALGÈBRE"])
        self.assertEqual(titles, ["Espaces métriques et topologiques", "Compacité et connexité", "Axiomes"])

    def test_a_unit_without_competency_still_appears(self):
        LearningUnit.objects.create(period=self.period, title="CALCUL SCIENTIFIQUE", order=2)
        response = self.client.get(self.url())
        self.assertContains(response, "CALCUL SCIENTIFIQUE")

    def test_metrics_are_saved_from_the_grid(self):
        self.client.get(self.url())
        records = list(tracked_records(self.user, self.path))
        data = {
            "form-TOTAL_FORMS": str(len(records)),
            "form-INITIAL_FORMS": str(len(records)),
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            f"metric_{self.unit.pk}_{self.coefficient.pk}": "7",
        }
        for index, record in enumerate(records):
            data |= {
                f"form-{index}-id": str(record.pk),
                f"form-{index}-planned_hours": "0",
                f"form-{index}-actual_hours": "0",
                f"form-{index}-mastery_level": "0",
                f"form-{index}-notes": "",
            }

        response = self.client.post(self.url(), data)

        self.assertRedirects(response, self.url())
        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("7.00"))

    def test_clearing_a_metric_removes_it(self):
        self.client.get(self.url())
        records = list(tracked_records(self.user, self.path))
        data = {
            "form-TOTAL_FORMS": str(len(records)),
            "form-INITIAL_FORMS": str(len(records)),
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            f"metric_{self.unit.pk}_{self.coefficient.pk}": "",
        }
        for index, record in enumerate(records):
            data |= {
                f"form-{index}-id": str(record.pk),
                f"form-{index}-planned_hours": "0",
                f"form-{index}-actual_hours": "0",
                f"form-{index}-mastery_level": "0",
                f"form-{index}-notes": "",
            }

        self.client.post(self.url(), data)

        self.assertFalse(MetricValue.objects.filter(definition=self.coefficient, unit=self.unit).exists())

    def test_a_non_numeric_metric_blocks_the_whole_save(self):
        self.client.get(self.url())
        records = list(tracked_records(self.user, self.path))
        data = {
            "form-TOTAL_FORMS": str(len(records)),
            "form-INITIAL_FORMS": str(len(records)),
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            f"metric_{self.unit.pk}_{self.coefficient.pk}": "beaucoup",
        }
        for index, record in enumerate(records):
            data |= {
                f"form-{index}-id": str(record.pk),
                f"form-{index}-planned_hours": "0",
                f"form-{index}-actual_hours": "0",
                f"form-{index}-mastery_level": "4",
                f"form-{index}-notes": "",
            }

        response = self.client.post(self.url(), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "n’est pas un nombre")
        # Le niveau de maîtrise ne doit pas non plus avoir été enregistré : soit tout
        # passe, soit rien, pour que l'utilisateur sache où il en est.
        self.assertEqual(tracked_records(self.user, self.path).first().mastery_level, 0)
        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("5"))

    def test_a_valid_send_saves_both_sets_together(self):
        self.client.get(self.url())
        response = self.client.post(self.url(), self.payload(mastery_level="3", metrics={self.coefficient: "6"}))

        self.assertRedirects(response, self.url())
        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("6.00"))
        for record in ProgressRecord.objects.filter(owner=self.user):
            self.assertEqual(record.mastery_level, 3)

    def test_one_invalid_metric_cancels_the_metrics_that_precede_it(self):
        """Le cas qui laissait un état partiel : la première case passait, la seconde non."""
        stage = MetricDefinition.objects.create(path=self.path, key="stage", label="Jours de stage", order=2)
        self.client.get(self.url())

        response = self.client.post(self.url(), self.payload(metrics={self.coefficient: "9", stage: "beaucoup"}))

        self.assertEqual(response.status_code, 200)
        # Le coefficient garde sa valeur d'origine : il n'a pas été écrit « en attendant ».
        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("5"))
        self.assertFalse(MetricValue.objects.filter(definition=stage, unit=self.unit).exists())

    def test_an_emptied_cell_is_not_deleted_when_another_cell_is_invalid(self):
        """Vider une case supprime la valeur ; encore faut-il que l'envoi aboutisse."""
        stage = MetricDefinition.objects.create(path=self.path, key="stage", label="Jours de stage", order=2)
        MetricValue.objects.create(definition=stage, unit=self.unit, value=Decimal("12"))
        self.client.get(self.url())

        self.client.post(self.url(), self.payload(metrics={self.coefficient: "", stage: "beaucoup"}))

        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("5"))
        self.assertEqual(MetricValue.objects.get(definition=stage, unit=self.unit).value, Decimal("12"))

    def test_an_invalid_progress_row_also_cancels_the_metrics(self):
        self.client.get(self.url())

        response = self.client.post(self.url(), self.payload(mastery_level="9", metrics={self.coefficient: "7"}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("5"))

    def test_nothing_is_written_if_the_rows_fail_at_the_last_moment(self):
        """Garantie « tout ou rien » : les deux écritures partagent une transaction.

        C'est ce qui protège aussi de deux envois simultanés : chacun est indivisible, et
        les valeurs visées sont verrouillées le temps de l'écrire.
        """
        self.client.get(self.url())
        payload = self.payload(mastery_level="4", metrics={self.coefficient: "8"})

        with mock.patch.object(ProgressRowFormSet, "save", side_effect=RuntimeError("base indisponible")):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url(), payload)

        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("5"))
        self.assertEqual(tracked_records(self.user, self.path).first().mastery_level, 0)

    def test_existing_values_are_locked_while_writing(self):
        from formations.services import apply_metric_values, validate_metric_values

        edits, errors = validate_metric_values(self.path, {f"metric_{self.unit.pk}_{self.coefficient.pk}": "3"})
        self.assertEqual(errors, [])

        with mock.patch("formations.services.connection") as fake:
            fake.features.has_select_for_update = True
            with mock.patch.object(MetricValue.objects, "select_for_update") as locked:
                locked.return_value.filter.return_value.values_list.return_value = []
                apply_metric_values(self.path, edits)

        locked.assert_called_once_with()

    def test_an_invalid_entry_stays_in_the_form(self):
        """Corriger une saisie suppose de la revoir : la grille ne la remplace pas."""
        self.client.get(self.url())

        response = self.client.post(self.url(), self.payload(mastery_level="2", metrics={self.coefficient: "12,5,3"}))

        self.assertContains(response, 'value="12,5,3"')
        self.assertContains(response, "Rien n’a été enregistré")
        # Aucune ligne n'est fautive ici : ne pas envoyer l'utilisateur en chercher une.
        self.assertNotContains(response, "lignes signalées en rouge")
        # Le niveau saisi est lui aussi conservé, alors que la base porte encore 0.
        self.assertContains(response, '<option value="2" selected>')
        self.assertEqual(tracked_records(self.user, self.path).first().mastery_level, 0)

    def test_a_stored_value_is_displayed_without_rounding(self):
        MetricValue.objects.filter(definition=self.coefficient).update(value=Decimal("7.25"))
        response = self.client.get(self.url())
        self.assertContains(response, 'value="7.25"')

    def test_hours_are_displayed_without_their_empty_decimals(self):
        self.client.get(self.url())
        tracked_records(self.user, self.path).update(planned_hours=Decimal("25.00"), actual_hours=Decimal("1.50"))

        response = self.client.get(self.url())

        self.assertContains(response, 'value="25"')
        self.assertContains(response, 'value="1,5"')
        self.assertNotContains(response, 'value="25,00"')

    def test_a_french_decimal_comma_is_accepted(self):
        self.client.get(self.url())

        response = self.client.post(self.url(), self.payload(planned_hours="10,5", metrics={self.coefficient: "3,5"}))

        self.assertRedirects(response, self.url())
        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("3.50"))
        self.assertEqual(tracked_records(self.user, self.path).first().planned_hours, Decimal("10.5"))

    def test_negative_hours_are_refused_by_the_form(self):
        self.client.get(self.url())

        response = self.client.post(self.url(), self.payload(planned_hours="-4"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(tracked_records(self.user, self.path).first().planned_hours, Decimal("0"))

    def test_a_metric_below_the_declared_minimum_is_refused(self):
        MetricDefinition.objects.filter(pk=self.coefficient.pk).update(min_value=Decimal("0"))
        self.client.get(self.url())

        response = self.client.post(self.url(), self.payload(metrics={self.coefficient: "-2"}))

        self.assertContains(response, "ne peut pas être inférieure à 0")
        self.assertEqual(MetricValue.objects.get(definition=self.coefficient, unit=self.unit).value, Decimal("5"))

    def test_a_metric_above_the_declared_maximum_is_refused(self):
        MetricDefinition.objects.filter(pk=self.coefficient.pk).update(max_value=Decimal("10"))
        self.client.get(self.url())

        response = self.client.post(self.url(), self.payload(metrics={self.coefficient: "11"}))

        self.assertContains(response, "ne peut pas être supérieure à 10")

    def test_a_metric_declared_integer_refuses_decimals(self):
        MetricDefinition.objects.filter(pk=self.coefficient.pk).update(decimal_places=0)
        self.client.get(self.url())

        response = self.client.post(self.url(), self.payload(metrics={self.coefficient: "2.5"}))

        self.assertContains(response, "que des nombres entiers")

    def test_another_users_path_is_not_reachable(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign = LearningPath.objects.create(owner=bob, title="Privé")
        self.assertEqual(self.client.get(reverse("formations:tracking", args=[foreign.pk])).status_code, 404)

    def test_records_are_never_created_for_another_user(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        ensure_progress_records(bob, self.path)
        self.assertEqual(ProgressRecord.objects.filter(owner=self.user).count(), 0)
        self.assertEqual(ProgressRecord.objects.filter(owner=bob).count(), 2)
