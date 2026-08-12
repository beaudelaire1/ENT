from django.urls import path

from . import views

app_name = "library"
urlpatterns = [
    path("", views.item_list, name="list"),
    path("new/", views.item_edit, name="new"),
    path("folders/new/", views.folder_edit, name="folder_new"),
    path("folders/<int:pk>/edit/", views.folder_edit, name="folder_edit"),
    path("folders/<int:pk>/delete/", views.folder_delete, name="folder_delete"),
    path("tags/new/", views.tag_edit, name="tag_new"),
    path("tags/<int:pk>/edit/", views.tag_edit, name="tag_edit"),
    path("tags/<int:pk>/delete/", views.tag_delete, name="tag_delete"),
    path("<int:pk>/", views.item_detail, name="detail"),
    path("<int:pk>/edit/", views.item_edit, name="edit"),
    path("<int:pk>/delete/", views.item_delete, name="delete"),
    path("<int:pk>/download/", views.download, name="download"),
]
