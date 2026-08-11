import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formations.models import Competency, LearningPath, LearningUnit, Period, ProgressRecord
from sablier.models import FocusSession
from sablier.services import record_session


class FocusSessionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        path = LearningPath.objects.create(owner=self.user, title="L3")
        period = Period.objects.create(path=path, title="Semestre 5")
        unit = LearningUnit.objects.create(period=period, title="TOPOLOGIE")
        self.competency = Competency.objects.create(unit=unit, title="Compacité")

    def test_a_session_without_competency_is_only_logged(self):
        session = record_session(self.user, seconds=1800, started_at=timezone.now())

        self.assertEqual(FocusSession.objects.count(), 1)
        self.assertIsNone(session.competency)
        self.assertIsNone(session.counted_at)
        self.assertEqual(ProgressRecord.objects.count(), 0)

    def test_a_session_reports_its_time_on_the_competency(self):
        record_session(self.user, seconds=1800, started_at=timezone.now(), competency=self.competency)

        record = ProgressRecord.objects.get(owner=self.user, competency=self.competency)
        self.assertEqual(record.actual_hours, Decimal("0.50"))
        self.assertIsNotNone(FocusSession.objects.get().counted_at)

    def test_sessions_accumulate_instead_of_overwriting(self):
        record_session(self.user, seconds=1800, started_at=timezone.now(), competency=self.competency)
        record_session(self.user, seconds=900, started_at=timezone.now(), competency=self.competency)

        record = ProgressRecord.objects.get(owner=self.user, competency=self.competency)
        self.assertEqual(record.actual_hours, Decimal("0.75"))

    def test_manual_entry_is_never_overwritten(self):
        ProgressRecord.objects.create(
            owner=self.user, competency=self.competency, actual_hours=Decimal("4.00"), mastery_level=2
        )

        record_session(self.user, seconds=3600, started_at=timezone.now(), competency=self.competency)

        record = ProgressRecord.objects.get(owner=self.user, competency=self.competency)
        self.assertEqual(record.actual_hours, Decimal("5.00"))
        self.assertEqual(record.mastery_level, 2)

    def test_the_endpoint_records_a_session(self):
        response = self.client.post(
            reverse("sablier:log_session"),
            data=json.dumps({"seconds": 1500, "intention": "Réviser", "competency": self.competency.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["competency"], "Compacité")
        self.assertEqual(FocusSession.objects.get().intention, "Réviser")

    def test_the_endpoint_refuses_another_users_competency(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        other_path = LearningPath.objects.create(owner=bob, title="Privé")
        other_period = Period.objects.create(path=other_path, title="S1")
        other_unit = LearningUnit.objects.create(period=other_period, title="Module")
        foreign = Competency.objects.create(unit=other_unit, title="Interdit")

        response = self.client.post(
            reverse("sablier:log_session"),
            data=json.dumps({"seconds": 600, "competency": foreign.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FocusSession.objects.count(), 0)

    def test_the_endpoint_rejects_impossible_durations(self):
        for seconds in (0, -10, 90000):
            response = self.client.post(
                reverse("sablier:log_session"),
                data=json.dumps({"seconds": seconds}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(FocusSession.objects.count(), 0)

    def test_deleting_a_competency_keeps_the_session(self):
        record_session(self.user, seconds=1800, started_at=timezone.now(), competency=self.competency)
        self.competency.delete()

        session = FocusSession.objects.get()
        self.assertIsNone(session.competency)
        self.assertEqual(session.seconds, 1800)
