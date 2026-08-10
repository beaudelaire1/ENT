from .models import DashboardWidget


def ensure_default_widgets(user):
    existing = set(DashboardWidget.objects.filter(owner=user).values_list("kind", flat=True))
    missing = [kind for kind, _ in DashboardWidget.Kind.choices if kind not in existing]
    start = DashboardWidget.objects.filter(owner=user).count()
    DashboardWidget.objects.bulk_create(
        [DashboardWidget(owner=user, kind=kind, position=start + index) for index, kind in enumerate(missing)]
    )
    return DashboardWidget.objects.filter(owner=user)
