from django.urls import path

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.home, name="home"),
    path("layout/", views.save_layout, name="save_layout"),
    path("quick-note/", views.quick_note, name="quick_note"),
]
