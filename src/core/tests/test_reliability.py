"""Régressions reproduites par l'audit : données fiables et écritures répétables."""

import json
import uuid
from datetime import datetime, timedelta
from datetime import timezone as utc
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from dashboard.models import DashboardWidget
from dashboard.services import ensure_default_widgets
from formations.history import level_timeline
from formations.models import Competency, LearningPath, Period, ProgressRecord
from formations.revision import to_revisit
from planner.models import CalendarEvent, Task
from sablier.models import FocusSession


class ReliabilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("reliability")
        self.client.force_login(self.user)
        UserProfile.objects.update_or_create(user=self.user, defaults={"timezone": "America/Cayenne"})
        self.path = LearningPath.objects.create(owner=self.user, title="Formation")
        self.period = Period.objects.create(path=self.path, title="Période")
        self.path.current_period = self.period
        self.path.save()
        self.competency = Competency.objects.create(path=self.path, period=self.period, title="Compétence")

    def post_json(self, name, payload):
        return self.client.post(reverse(name), json.dumps(payload), content_type="application/json")

    def test_untracked_competencies_count_in_the_denominator(self):
        ProgressRecord.objects.create(owner=self.user, competency=self.competency, mastery_level=4)
        Competency.objects.create(path=self.path, period=self.period, title="Non renseignée")
        academic = self.client.get(reverse("dashboard:home")).context["academic"]
        self.assertEqual((academic["competencies"], academic["acquired"], academic["progress_percent"]), (2, 1, 50))

    def test_suggestion_needs_confirmation_in_all_summaries(self):
        record = ProgressRecord.objects.create(
            owner=self.user,
            competency=self.competency,
            planned_hours=Decimal(1),
            manual_hours=Decimal(1),
        )
        academic = self.client.get(reverse("dashboard:home")).context["academic"]
        self.assertEqual((academic["acquired"], academic["progress_percent"], academic["suggested"]), (0, 0, 1))
        self.assertIn("confirmer", to_revisit(self.user, self.path)[0].reason)
        self.assertEqual(level_timeline(self.user, self.path)[-1].acquired, 0)
        record.refresh_from_db()
        record.adopt_suggested_level()
        self.assertEqual(level_timeline(self.user, self.path)[-1].acquired, 1)
        self.assertEqual(to_revisit(self.user, self.path), [])
        academic = self.client.get(reverse("dashboard:home")).context["academic"]
        self.assertEqual((academic["acquired"], academic["progress_percent"]), (1, 100))

    def event(self, starts, ends, **kwargs):
        return CalendarEvent.objects.create(
            owner=self.user, title="Événement", starts_at=starts, ends_at=ends, **kwargs
        )

    def test_late_evening_event_and_task_belong_to_local_monday(self):
        start = datetime(2026, 9, 8, 2, 30, tzinfo=utc.utc)
        event = self.event(start, start + timedelta(minutes=20))
        task = Task.objects.create(owner=self.user, title="À faire", due_at=start)
        days = self.client.get(reverse("planner:agenda"), {"view": "week", "date": "2026-09-07"}).context["days"]
        self.assertEqual(days[0]["events"], [event])
        self.assertEqual(days[0]["tasks"], [task])
        self.assertEqual(days[1]["events"], [])

    def test_multiday_events_include_continuations_and_exclude_end_midnight(self):
        zone = ZoneInfo("America/Cayenne")
        event = self.event(datetime(2026, 9, 6, 20, tzinfo=zone), datetime(2026, 9, 9, tzinfo=zone))
        days = self.client.get(reverse("planner:agenda"), {"view": "week", "date": "2026-09-07"}).context["days"]
        self.assertEqual([day["date"].day for day in days if event in day["events"]], [7, 8])
        with patch("django.utils.timezone.now", return_value=datetime(2026, 9, 7, 12, tzinfo=zone)):
            self.assertIn(event, self.client.get(reverse("dashboard:home")).context["events_today"])

    def test_dst_day_and_all_day_event(self):
        self.user.profile.timezone = "Europe/Paris"
        self.user.profile.save()
        zone = ZoneInfo("Europe/Paris")
        event = self.event(datetime(2026, 3, 29, tzinfo=zone), datetime(2026, 3, 30, tzinfo=zone), all_day=True)
        late = Task.objects.create(
            owner=self.user, title="Dimanche soir", due_at=datetime(2026, 3, 29, 23, 30, tzinfo=zone)
        )
        days = self.client.get(reverse("planner:agenda"), {"view": "week", "date": "2026-03-29"}).context["days"]
        self.assertEqual(days[-1]["events"], [event])
        self.assertEqual(days[-1]["tasks"], [late])

    def test_layout_validation_is_atomic(self):
        ensure_default_widgets(self.user)
        before = list(DashboardWidget.objects.filter(owner=self.user).values("kind", "position", "visible"))
        valid = {"kind": before[0]["kind"], "visible": False}
        for payload in (
            None,
            [],
            {"widgets": [None]},
            {"widgets": [valid, {"kind": "unknown"}]},
            {"widgets": [valid, valid]},
            {"widgets": [{"kind": before[0]["kind"], "visible": "false"}]},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.post_json("dashboard:save_layout", payload).status_code, 400)
                self.assertEqual(
                    list(DashboardWidget.objects.filter(owner=self.user).values("kind", "position", "visible")), before
                )

    def test_external_redirects_are_rejected(self):
        task = Task.objects.create(owner=self.user, title="Tâche")
        session = FocusSession.objects.create(owner=self.user, seconds=60, started_at=timezone.now())
        for action, pk, target in (
            ("planner:task_toggle", task.pk, "planner:tasks"),
            ("sablier:session_toggle_excluded", session.pk, "sablier:sessions"),
        ):
            response = self.client.post(reverse(action, args=[pk]), {"next": "https://example.com/"})
            self.assertEqual(response["Location"], reverse(target))

    def session_payload(self):
        end = timezone.now() - timedelta(hours=1)
        return {
            "session_id": str(uuid.uuid4()),
            "owner": self.user.pk,
            "seconds": 600,
            "started_at": (end - timedelta(minutes=20)).isoformat(),
            "ended_at": end.isoformat(),
            "competency": self.competency.pk,
            "intention": "Travailler",
        }

    def test_retried_session_counts_once_and_keeps_real_dates(self):
        payload = self.session_payload()
        first = self.post_json("sablier:log_session", payload)
        second = self.post_json("sablier:log_session", payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(FocusSession.objects.count(), 1)
        session = FocusSession.objects.get()
        self.assertEqual(session.started_at.isoformat(), payload["started_at"])
        self.assertEqual(session.ended_at.isoformat(), payload["ended_at"])
        self.assertEqual(ProgressRecord.objects.get().session_hours, Decimal("0.17"))
        self.competency.delete()
        self.assertEqual(self.post_json("sablier:log_session", payload).status_code, 200)
        self.assertEqual(FocusSession.objects.count(), 1)

    def test_wrong_account_cannot_receive_a_pending_session(self):
        payload = self.session_payload()
        self.client.force_login(get_user_model().objects.create_user("other-account"))
        self.assertEqual(self.post_json("sablier:log_session", payload).status_code, 403)
        self.assertFalse(FocusSession.objects.exists())

    def test_invalid_session_metadata_is_rejected(self):
        for changes in (
            {"session_id": "invalid"},
            {"started_at": "2026-01-01"},
            {"seconds": 99999999999999},
            {"seconds": True},
            {"seconds": 1.5},
            {"competency": "broken"},
            {"ended_at": "2020-01-01T00:00:00Z"},
        ):
            with self.subTest(changes=changes):
                payload = self.session_payload() | changes
                self.assertEqual(self.post_json("sablier:log_session", payload).status_code, 400)
        self.assertFalse(FocusSession.objects.exists())
