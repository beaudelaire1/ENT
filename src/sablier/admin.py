from django.contrib import admin

from .models import AudioTrack, FocusPreference, Playlist, PlaylistTrack

admin.site.register(FocusPreference)
admin.site.register(AudioTrack)
admin.site.register(Playlist)
admin.site.register(PlaylistTrack)
