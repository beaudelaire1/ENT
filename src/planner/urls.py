from django.urls import path

from . import views

app_name = "planner"
urlpatterns = [
    path("agenda/", views.agenda, name="agenda"),
    path("agenda/new/", views.event_edit, name="event_new"),
    path("agenda/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("agenda/<int:pk>/delete/", views.event_delete, name="event_delete"),
    path("tasks/", views.task_list, name="tasks"),
    path("tasks/new/", views.task_edit, name="task_new"),
    path("tasks/<int:pk>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),
]
