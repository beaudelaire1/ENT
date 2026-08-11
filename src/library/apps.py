from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "library"

    def ready(self):
        from core.files import discard_files_on_delete

        from .models import LibraryItem

        discard_files_on_delete(LibraryItem, "file")
