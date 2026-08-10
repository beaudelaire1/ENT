from django.urls import path

from . import views

app_name = "sablier"
urlpatterns = [
    path("", views.home, name="home"),
    path("audio/", views.audio_library, name="audio"),
    path("audio/presign/", views.presign_audio, name="presign_audio"),
    path("audio/<int:pk>/confirm/", views.confirm_audio, name="confirm_audio"),
    path("audio/<int:pk>/stream/", views.audio_stream, name="audio_stream"),
    path("playlists/", views.playlist_list, name="playlists"),
    path("playlists/new/", views.playlist_edit, name="playlist_new"),
    path("playlists/<int:pk>/", views.playlist_detail, name="playlist_detail"),
    path("playlists/<int:pk>/edit/", views.playlist_edit, name="playlist_edit"),
    path("playlists/<int:pk>/tracks/<int:entry_pk>/remove/", views.playlist_remove_track, name="playlist_remove_track"),
]
