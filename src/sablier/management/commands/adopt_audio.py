"""Rattache à un compte les fichiers audio déjà présents dans le stockage.

Déposer un fichier dans le bucket ne le fait pas exister pour MyENT : c'est la ligne
``AudioTrack`` qui porte le titre, la durée, l'état et le propriétaire, et rien ne la crée
toute seule. Cette commande comble l'écart après un dépôt fait directement depuis la
console Cloudflare, un transfert par ``rclone``, ou la restauration d'une sauvegarde.

Elle ne copie ni ne déplace aucun octet : elle se contente de désigner des objets qui sont
déjà là. Et elle ne touche jamais à un fichier déjà rattaché — relancer la commande deux
fois n'ajoute rien la seconde fois.

La durée et l'état ne sont pas devinés : chaque piste part en validation, exactement comme
un téléversement ordinaire, et c'est ``validate_audio_track`` qui lit le fichier pour en
tirer la durée et décider si elle est lisible.
"""

from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from core.queue import enqueue
from sablier.models import AudioTrack
from sablier.tasks import validate_audio_track

# Les formats acceptés au téléversement, et leur type MIME. Un objet d'une autre extension
# est ignoré plutôt que rattaché : le bucket peut contenir autre chose que de la musique.
MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
}


class Command(BaseCommand):
    help = "Crée les pistes manquantes pour les fichiers audio déjà présents dans le stockage."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Nom d'utilisateur propriétaire des pistes.")
        parser.add_argument(
            "--prefix",
            default="",
            help="Préfixe à parcourir. Par défaut, `users/<id>/audio/`, où les téléversements atterrissent.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Montre ce qui serait rattaché sans rien écrire.",
        )

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["user"]).first()
        if user is None:
            raise CommandError(f"Aucun compte nommé « {options['user']} ».")
        prefix = options["prefix"] or f"users/{user.pk}/audio/"

        keys = self.storage_keys(prefix)
        if not keys:
            self.stdout.write(f"Aucun fichier sous « {prefix} ».")
            return

        # Sur l'ensemble des comptes et non du seul propriétaire : un fichier déjà rattaché
        # ailleurs ne doit pas être adopté une seconde fois.
        known = set(AudioTrack.objects.values_list("file", flat=True))
        adopted, ignored, skipped = 0, 0, 0

        for key, size in keys:
            suffix = Path(key).suffix.lower()
            if suffix not in MIME_TYPES:
                ignored += 1
                continue
            if key in known:
                skipped += 1
                continue
            self.stdout.write(f"  + {key}")
            if options["dry_run"]:
                adopted += 1
                continue
            track = AudioTrack.objects.create(
                owner=user,
                title=Path(key).stem[:180],
                file=key,
                mime_type=MIME_TYPES[suffix],
                file_size=size,
                status=AudioTrack.Status.VALIDATING,
            )
            # Même chemin qu'un téléversement : la durée est lue depuis le fichier, et une
            # piste illisible est refusée avec son motif plutôt que présentée comme prête.
            enqueue(validate_audio_track, track.pk)
            adopted += 1

        verdict = "seraient rattachés" if options["dry_run"] else "rattachés"
        self.stdout.write(
            self.style.SUCCESS(
                f"{adopted} fichier(s) {verdict} à « {user.get_username()} ». "
                f"{skipped} déjà connu(s), {ignored} ignoré(s) — extension non audio."
            )
        )

    def storage_keys(self, prefix: str) -> list[tuple[str, int]]:
        """Les objets sous le préfixe, avec leur taille, quel que soit le stockage.

        ``listdir`` ne descend pas dans les sous-répertoires : le parcours est fait ici,
        pour que la commande fonctionne aussi bien sur un bucket que sur un disque local.
        """
        found: list[tuple[str, int]] = []
        to_visit = [prefix.strip("/")]
        while to_visit:
            current = to_visit.pop()
            try:
                directories, files = default_storage.listdir(current)
            except (FileNotFoundError, OSError):
                continue
            to_visit.extend(f"{current}/{name}" for name in directories)
            for name in files:
                key = f"{current}/{name}"
                try:
                    size = default_storage.size(key)
                except (FileNotFoundError, OSError):
                    size = 0
                found.append((key, size))
        return sorted(found)
