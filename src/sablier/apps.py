from django.apps import AppConfig


class SablierConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sablier"

    def ready(self):
        from core.files import discard_files_on_delete

        from .models import AudioTrack, FocusPreference

        discard_files_on_delete(AudioTrack, "file")
        discard_files_on_delete(FocusPreference, "background_image")
