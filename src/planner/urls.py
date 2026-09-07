from django.urls import path

from . import focus_views, views

app_name = "planner"
urlpatterns = [
    path("agenda/", views.agenda, name="agenda"),
    path("agenda/new/", views.event_edit, name="event_new"),
    path("agenda/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("agenda/<int:pk>/delete/", views.event_delete, name="event_delete"),
    path("agenda/<int:pk>/series/delete/", views.event_series_delete, name="event_series_delete"),
    path("tasks/", views.task_list, name="tasks"),
    path("tasks/new/", views.task_edit, name="task_new"),
    path("tasks/<int:pk>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:pk>/series/delete/", views.task_series_delete, name="task_series_delete"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),
    path("tasks/<int:pk>/focus/<str:scope>/", focus_views.set_task_focus, name="task_focus"),
    path("tasks/focus/<str:scope>/clear/", focus_views.clear_task_focus, name="task_focus_clear"),
]
