from django.urls import path

from . import views

app_name = "formations"
urlpatterns = [
    path("", views.path_list, name="list"),
    path("new/", views.path_edit, name="new"),
    path("<int:pk>/", views.path_detail, name="detail"),
    path("<int:pk>/suivi/", views.path_tracking, name="tracking"),
    path("<int:pk>/edit/", views.path_edit, name="edit"),
    path("<int:pk>/delete/", views.path_delete, name="delete"),
    # Chaque objet structurant se crée depuis son parent et se modifie depuis lui-même.
    path("<int:path_pk>/periods/new/", views.period_edit, name="period_new"),
    path("periods/<int:pk>/edit/", views.period_edit, name="period_edit"),
    path("periods/<int:pk>/delete/", views.period_delete, name="period_delete"),
    path("<int:path_pk>/metrics/new/", views.metric_definition_edit, name="metric_new"),
    path("metrics/<int:pk>/edit/", views.metric_definition_edit, name="metric_edit"),
    path("metrics/<int:pk>/delete/", views.metric_definition_delete, name="metric_delete"),
    path("periods/<int:period_pk>/groups/new/", views.group_edit, name="group_new"),
    path("groups/<int:pk>/edit/", views.group_edit, name="group_edit"),
    path("groups/<int:pk>/delete/", views.group_delete, name="group_delete"),
    path("periods/<int:period_pk>/units/new/", views.unit_edit, name="unit_new"),
    path("units/<int:pk>/", views.unit_detail, name="unit"),
    path("units/<int:pk>/competencies/", views.unit_competencies, name="unit_competencies"),
    path("links/<int:pk>/edit/", views.link_edit, name="link_edit"),
    path("units/<int:pk>/edit/", views.unit_edit, name="unit_edit"),
    path("units/<int:pk>/delete/", views.unit_delete, name="unit_delete"),
    path("units/<int:pk>/resources/", views.unit_resources, name="unit_resources"),
    path("units/<int:unit_pk>/competencies/new/", views.competency_edit, name="competency_new"),
    path("competencies/<int:pk>/", views.competency_detail, name="competency"),
    path("competencies/<int:pk>/resources/", views.competency_resources, name="competency_resources"),
    path("competencies/<int:pk>/edit/", views.competency_edit, name="competency_edit"),
    path("competencies/<int:pk>/delete/", views.competency_delete, name="competency_delete"),
    path("competencies/<int:competency_pk>/progress/", views.progress_edit, name="progress"),
    # Les évaluations vivent au niveau du compte : une épreuve peut être transversale, et
    # la liste sert d'abord à voir ce qui arrive, toutes formations confondues.
    path("evaluations/", views.assessment_list, name="assessments"),
    path("evaluations/new/", views.assessment_edit, name="assessment_new"),
    path("evaluations/<int:pk>/", views.assessment_detail, name="assessment"),
    path("evaluations/<int:pk>/edit/", views.assessment_edit, name="assessment_edit"),
    path("evaluations/<int:pk>/delete/", views.assessment_delete, name="assessment_delete"),
    path("evaluations/<int:pk>/result/", views.result_edit, name="result_edit"),
    path("evaluations/<int:pk>/competencies/", views.assessment_competencies, name="assessment_competencies"),
]
