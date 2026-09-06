from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self):
        """Branche les notifications de création sur `post_save`.

        Le crochet est ici plutôt que dans chaque vue : un objet naît aussi d'un import,
        d'une répétition de série, de l'administration. Passer par la vue n'en aurait
        couvert qu'une partie, et la couverture aurait varié avec le temps sans que rien
        ne le signale.

        `created` seul est retenu : une modification n'est pas une nouvelle.
        """
        from django.db.models.signals import post_save

        from .creation import ANNOUNCED, announce

        for label in ANNOUNCED:
            post_save.connect(announce, sender=label, dispatch_uid=f"notify_created_{label}", weak=False)
