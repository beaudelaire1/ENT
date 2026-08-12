"""Ce que la base refuse, quoi qu'il arrive.

Les formulaires filtrent les saisies ; ces tests vérifient la ligne de défense suivante.
Une durée négative ou une métrique hors bornes ne doit pas pouvoir entrer par l'admin,
par un script d'import ou par une vue écrite plus tard.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
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


class IntegrityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.unit = LearningUnit.objects.create(period=self.period, title="TOPOLOGIE", order=1)
        self.competency = Competency.objects.create(unit=self.unit, title="Compacité", order=1)
        self.coefficient = MetricDefinition.objects.create(path=self.path, key="coefficient", label="Coefficient")

    def record(self, **kwargs):
        return ProgressRecord(owner=self.user, competency=self.competency, **kwargs)

    def test_the_database_refuses_negative_planned_hours(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.record(planned_hours=Decimal("-1")).save()

    def test_the_database_refuses_negative_actual_hours(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.record(actual_hours=Decimal("-0.25")).save()

    def test_zero_hours_remain_valid(self):
        self.record(planned_hours=Decimal("0"), actual_hours=Decimal("0")).save()
        self.assertEqual(ProgressRecord.objects.count(), 1)

    def test_model_validation_refuses_negative_hours(self):
        with self.assertRaises(ValidationError) as raised:
            self.record(planned_hours=Decimal("-3")).full_clean()
        self.assertIn("planned_hours", raised.exception.error_dict)

    def test_the_database_refuses_bounds_in_the_wrong_order(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            MetricDefinition.objects.create(
                path=self.path, key="ects", label="ECTS", min_value=Decimal("10"), max_value=Decimal("2")
            )

    def test_model_validation_explains_bounds_in_the_wrong_order(self):
        definition = MetricDefinition(
            path=self.path, key="ects", label="ECTS", min_value=Decimal("10"), max_value=Decimal("2")
        )
        with self.assertRaises(ValidationError) as raised:
            definition.full_clean()
        self.assertIn("max_value", raised.exception.error_dict)

    def test_the_database_refuses_more_decimals_than_it_can_store(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            MetricDefinition.objects.create(path=self.path, key="precis", label="Précis", decimal_places=5)

    def test_a_metric_value_outside_the_declared_bounds_is_refused(self):
        MetricDefinition.objects.filter(pk=self.coefficient.pk).update(min_value=0, max_value=20)
        self.coefficient.refresh_from_db()
        value = MetricValue(definition=self.coefficient, unit=self.unit, value=Decimal("25"))
        with self.assertRaises(ValidationError):
            value.full_clean()

    def test_a_metric_value_from_another_path_is_refused(self):
        other = LearningPath.objects.create(owner=self.user, title="DU Statistique")
        other_period = Period.objects.create(path=other, title="Bloc 1")
        other_unit = LearningUnit.objects.create(period=other_period, title="R")
        value = MetricValue(definition=self.coefficient, unit=other_unit, value=Decimal("1"))
        with self.assertRaises(ValidationError):
            value.full_clean()

    def test_a_metric_may_accept_negative_values_when_no_minimum_is_declared(self):
        """Décision explicite : une colonne sans borne basse accepte un écart négatif."""
        self.assertIsNone(self.coefficient.min_value)
        value, error = self.coefficient.parse("-4")
        self.assertIsNone(error)
        self.assertEqual(value, Decimal("-4.00"))


class MetricDeletionReachableTests(TestCase):
    """La pastille d'une colonne de suivi portait un « × » impossible à cliquer.

    ``.chip.static`` neutralisait les événements de pointeur sur tout le conteneur, donc
    aussi sur le lien qu'il contient. Le lien existait, la vue répondait, mais aucune
    souris ne pouvait l'atteindre.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.metric = MetricDefinition.objects.create(path=self.path, key="coefficient", label="Coefficient")

    def test_the_delete_link_is_offered_next_to_the_column(self):
        response = self.client.get(reverse("formations:detail", args=[self.path.pk]))
        self.assertContains(response, reverse("formations:metric_delete", args=[self.metric.pk]))

    def test_the_column_container_does_not_disable_pointer_events(self):
        from django.conf import settings

        css = (settings.BASE_DIR / "static" / "css" / "app.css").read_text(encoding="utf-8")
        static_rule = next(line for line in css.splitlines() if line.startswith(".chip.static {"))
        self.assertNotIn("pointer-events", static_rule)

    def test_deleting_a_column_works_and_keeps_the_path(self):
        response = self.client.post(reverse("formations:metric_delete", args=[self.metric.pk]))
        self.assertRedirects(response, reverse("formations:detail", args=[self.path.pk]))
        self.assertFalse(MetricDefinition.objects.filter(pk=self.metric.pk).exists())
        self.assertTrue(LearningPath.objects.filter(pk=self.path.pk).exists())

    def test_another_users_column_cannot_be_deleted(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign_path = LearningPath.objects.create(owner=bob, title="Privé")
        foreign = MetricDefinition.objects.create(path=foreign_path, key="k", label="K")
        response = self.client.post(reverse("formations:metric_delete", args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(MetricDefinition.objects.filter(pk=foreign.pk).exists())
