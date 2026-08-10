from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from core.search import SOURCES, index_instance, unindex_instance

        def on_save(sender, instance, **kwargs):
            index_instance(instance)

        def on_delete(sender, instance, **kwargs):
            unindex_instance(instance)

        for key, source in SOURCES.items():
            post_save.connect(on_save, sender=source.model_label, dispatch_uid=f"search_index_{key}", weak=False)
            post_delete.connect(on_delete, sender=source.model_label, dispatch_uid=f"search_unindex_{key}", weak=False)
