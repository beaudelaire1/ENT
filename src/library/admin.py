from django.contrib import admin

from .models import Folder, LibraryItem, Tag


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "parent")
    list_filter = ("owner",)
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "color")
    list_filter = ("owner",)
    search_fields = ("name",)


@admin.register(LibraryItem)
class LibraryItemAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "owner", "folder", "updated_at")
    list_filter = ("kind", "owner")
    search_fields = ("title", "description", "note_text", "provider_name")
    date_hierarchy = "updated_at"
