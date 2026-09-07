"""Pourquoi je ne reçois rien : la réponse en une commande.

Une notification qui n'arrive pas peut l'être pour des raisons très différentes — le
code n'est pas déployé, le planificateur ne tourne pas, l'email part dans la console,
la famille a été éteinte. Aucune ne se voit depuis l'écran : elles se ressemblent
toutes, et elles ressemblent aussi à un défaut du code.

Cette commande les distingue, sur le déploiement où on la lance.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from notifications.catalog import EVENTS, FAMILIES
from notifications.models import EmailDelivery, Notification, NotificationPreference


class Command(BaseCommand):
    help = "Vérifie la chaîne de notification : planificateur, email, préférences, volumes."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Nom d'utilisateur à inspecter en détail.")
        parser.add_argument(
            "--scan",
            action="store_true",
            help="Lance le balayage immédiatement pour cet utilisateur, sans attendre l'heure.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Catalogue"))
        self.stdout.write(f"  {len(EVENTS)} événements dans {len(FAMILIES)} familles.")

        self.stdout.write(self.style.MIGRATE_HEADING("Planificateur"))
        self._report_schedule()

        self.stdout.write(self.style.MIGRATE_HEADING("Email"))
        self._report_email()

        self.stdout.write(self.style.MIGRATE_HEADING("Volumes"))
        self.stdout.write(f"  {Notification.objects.count()} notifications, {EmailDelivery.objects.count()} envois.")

        username = options.get("user")
        if username:
            self._report_user(username, scan=options.get("scan", False))

    def _report_schedule(self):
        from config.celery import app as celery_app

        # `autodiscover_tasks` est paresseux : sans ce chargement, les tâches des
        # applications paraissent absentes alors qu'un worker les trouve très bien.
        celery_app.loader.import_default_modules()
        for entry in settings.CELERY_BEAT_SCHEDULE.values():
            known = entry["task"] in celery_app.tasks
            mark = self.style.SUCCESS("enregistrée") if known else self.style.ERROR("INTROUVABLE")
            self.stdout.write(f"  {entry['task']} · toutes les {entry['schedule']:.0f} s · {mark}")
        self.stdout.write(
            "  Ces tâches ne partent que si le service « beat » tourne, et ne sont exécutées\n"
            "  que si un worker tourne. Sans eux, seules les notifications de création arrivent."
        )

    def _report_email(self):
        backend = settings.EMAIL_BACKEND
        if "console" in backend:
            self.stdout.write(
                self.style.WARNING(
                    "  Backend « console » : les emails sont écrits dans les journaux du conteneur\n"
                    "  et ne partent nulle part. Renseignez EMAIL_HOST pour qu'ils soient expédiés."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"  {backend} via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}"))
        self.stdout.write(f"  Expéditeur : {settings.DEFAULT_FROM_EMAIL}")
        if not os.getenv("EMAIL_HOST"):
            self.stdout.write("  EMAIL_HOST n'est pas défini dans l'environnement.")

    def _report_user(self, username: str, *, scan: bool):
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            self.stdout.write(self.style.ERROR(f"Utilisateur « {username} » introuvable."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f"Compte {username}"))
        self.stdout.write(f"  Adresse : {user.email or self.style.WARNING('aucune — aucun email ne peut partir')}")

        silenced = [
            preference.family
            for preference in NotificationPreference.objects.filter(owner=user)
            if not preference.enabled
        ]
        if silenced:
            self.stdout.write(self.style.WARNING(f"  Familles éteintes : {', '.join(silenced)}"))
        else:
            self.stdout.write("  Aucune famille éteinte : tout est accepté.")

        if scan:
            from notifications.scanning import scan_user

            created = scan_user(user)
            self.stdout.write(self.style.SUCCESS(f"  Balayage immédiat : {created} notification(s) créée(s)."))

        recent = Notification.objects.filter(owner=user)[:5]
        self.stdout.write(f"  {Notification.objects.filter(owner=user).count()} notifications, dont les dernières :")
        for note in recent:
            state = "lue" if note.read_at else "non lue"
            self.stdout.write(f"    • [{state}] {note.title}")
        if not recent:
            self.stdout.write("    (aucune)")
