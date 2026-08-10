from django.urls import path

from . import views

app_name = "formations"
urlpatterns = [
    path("", views.path_list, name="list"),
    path("new/", views.path_edit, name="new"),
    path("<int:pk>/", views.path_detail, name="detail"),
    path("<int:pk>/edit/", views.path_edit, name="edit"),
    path("<int:path_pk>/periods/new/", views.period_new, name="period_new"),
    path("<int:path_pk>/metrics/new/", views.metric_definition_new, name="metric_new"),
    path("periods/<int:period_pk>/units/new/", views.unit_new, name="unit_new"),
    path("units/<int:pk>/", views.unit_detail, name="unit"),
    path("units/<int:unit_pk>/competencies/new/", views.competency_new, name="competency_new"),
    path("units/<int:unit_pk>/metrics/new/", views.metric_value_new, name="metric_value_new"),
    path("competencies/<int:competency_pk>/progress/", views.progress_edit, name="progress"),
]
