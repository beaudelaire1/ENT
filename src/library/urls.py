from django.urls import path

from . import views

app_name = "library"
urlpatterns = [
    path("", views.item_list, name="list"),
    path("new/", views.item_edit, name="new"),
    path("folders/new/", views.folder_new, name="folder_new"),
    path("tags/new/", views.tag_new, name="tag_new"),
    path("<int:pk>/", views.item_detail, name="detail"),
    path("<int:pk>/edit/", views.item_edit, name="edit"),
    path("<int:pk>/download/", views.download, name="download"),
]
