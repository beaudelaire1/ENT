from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from formations.models import Competency, LearningPath, LearningUnit, MetricDefinition, Period
from formations.tests.factories import competency_in


class FormationsScopingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="Licence 3")
        self.period = Period.objects.create(path=self.path, title="Semestre 5")
        self.unit = LearningUnit.objects.create(period=self.period, title="Algorithmique")

    def test_path_is_attached_to_its_owner(self):
        response = self.client.post(reverse("formations:new"), {"title": "Master 1", "status": "active"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LearningPath.objects.get(title="Master 1").owner, self.user)

    def test_duplicate_period_is_a_form_error(self):
        response = self.client.post(
            reverse("formations:period_new", args=[self.path.pk]), {"title": "Semestre 5", "order": 0}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Period.objects.filter(path=self.path, title="Semestre 5").count(), 1)

    def test_duplicate_unit_is_a_form_error(self):
        response = self.client.post(
            reverse("formations:unit_new", args=[self.period.pk]), {"title": "Algorithmique", "order": 0}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LearningUnit.objects.filter(period=self.period, title="Algorithmique").count(), 1)

    def test_duplicate_competency_is_a_form_error(self):
        competency_in(self.unit, title="Trier une liste")
        response = self.client.post(
            reverse("formations:competency_new", args=[self.unit.pk]), {"title": "Trier une liste", "order": 0}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Competency.objects.filter(units=self.unit, title="Trier une liste").count(), 1)

    def test_duplicate_metric_key_is_a_form_error(self):
        MetricDefinition.objects.create(path=self.path, key="heures", label="Heures")
        response = self.client.post(
            reverse("formations:metric_new", args=[self.path.pk]),
            {"key": "heures", "label": "Heures travaillées", "order": 0},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MetricDefinition.objects.filter(path=self.path, key="heures").count(), 1)

    def test_another_users_path_is_not_reachable(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign = LearningPath.objects.create(owner=bob, title="Privé")
        self.assertEqual(self.client.get(reverse("formations:detail", args=[foreign.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("formations:period_new", args=[foreign.pk]), {}).status_code, 404)
