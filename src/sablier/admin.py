from django.contrib import admin

from .models import AudioTrack, FocusPreference, FocusSession, Playlist, PlaylistTrack


@admin.register(FocusPreference)
class FocusPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "mode", "ambience", "focus_level", "default_duration_seconds")
    list_filter = ("mode", "ambience")


@admin.register(AudioTrack)
class AudioTrackAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "owner", "status", "duration_seconds", "file_size")
    list_filter = ("status", "owner")
    search_fields = ("title", "artist")


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("title", "owner")
    list_filter = ("owner",)
    search_fields = ("title", "description")


@admin.register(PlaylistTrack)
class PlaylistTrackAdmin(admin.ModelAdmin):
    list_display = ("playlist", "track", "position")
    list_filter = ("playlist",)


@admin.register(FocusSession)
class FocusSessionAdmin(admin.ModelAdmin):
    list_display = ("started_at", "owner", "minutes", "competency", "counted_at")
    list_filter = ("owner",)
    search_fields = ("intention", "competency__title")
    date_hierarchy = "started_at"
