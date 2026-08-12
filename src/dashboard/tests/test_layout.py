import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import DashboardWidget
from dashboard.services import ensure_default_widgets
from formations.models import Competency, LearningPath, Period, ProgressRecord
from planner.models import Task


class DashboardLayoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("member")
        self.client.force_login(self.user)
        ensure_default_widgets(self.user)

    def test_widget_visibility_and_order_are_persisted(self):
        kinds = list(DashboardWidget.Kind.values)
        payload = {
            "widgets": [{"kind": kind, "visible": kind != DashboardWidget.Kind.FORMATIONS} for kind in reversed(kinds)]
        }
        response = self.client.post(
            reverse("dashboard:save_layout"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        widgets = list(DashboardWidget.objects.filter(owner=self.user))
        self.assertEqual([widget.kind for widget in widgets], list(reversed(kinds)))
        self.assertFalse(DashboardWidget.objects.get(owner=self.user, kind=DashboardWidget.Kind.FORMATIONS).visible)

    def test_shared_shell_and_widgets_are_keyboard_reachable(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, 'class="skip-link"')
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, "data-close-sidebar")
        self.assertContains(response, 'data-move-widget="up"')
        self.assertContains(response, 'aria-live="polite"')


class AcademicDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="Licence", academic_year="2026-2027")
        self.period = Period.objects.create(path=self.path, title="Semestre 5")
        self.path.current_period = self.period
        self.path.save(update_fields=["current_period"])
        competency = Competency.objects.create(path=self.path, period=self.period, title="Démontrer")
        ProgressRecord.objects.create(
            owner=self.user,
            competency=competency,
            mastery_level=ProgressRecord.Mastery.ACQUIRED,
        )

    def test_current_period_and_progress_are_visible(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Situation académique")
        self.assertContains(response, "Semestre 5")
        self.assertContains(response, "1 compétence(s) acquise(s) sur 1")

    def test_the_bar_follows_the_weighted_progress(self):
        """« Acquis » sur quatre niveaux vaut 75 %, et non 100 % comme le ferait un décompte."""
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, 'value="75" max="100"')

    def test_task_can_be_completed_from_dashboard(self):
        task = Task.objects.create(owner=self.user, title="Rendre le devoir")
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, reverse("planner:task_toggle", args=[task.pk]))
        self.client.post(
            reverse("planner:task_toggle", args=[task.pk]),
            {"next": reverse("dashboard:home")},
        )
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)
