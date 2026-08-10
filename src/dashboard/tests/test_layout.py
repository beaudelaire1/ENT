import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import DashboardWidget
from dashboard.services import ensure_default_widgets


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
