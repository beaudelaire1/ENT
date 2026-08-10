from django.urls import path

from . import views

app_name = "planner"
urlpatterns = [
    path("agenda/", views.agenda, name="agenda"),
    path("agenda/new/", views.event_edit, name="event_new"),
    path("agenda/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("tasks/", views.task_list, name="tasks"),
    path("tasks/new/", views.task_edit, name="task_new"),
    path("tasks/<int:pk>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),
]
