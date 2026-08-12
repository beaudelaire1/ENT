"""Sauvegarde de la base et des fichiers vers un bucket distinct.

La base seule ne suffit pas. Avec `USE_S3=false` — le mode par défaut — les fichiers de
bibliothèque et les pistes audio vivent dans le volume Docker `private_media`, que rien
ne sauvegardait : une restauration rendait une application complète avec des liens vers
des fichiers disparus. Depuis, le même passage archive aussi le média, sauf quand S3 le
détient déjà et le versionne.

Le bucket de sauvegarde doit rester distinct du bucket média : un même bucket compromis
emporterait les données et leur copie.
"""

from __future__ import annotations

import os
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sauvegarde PostgreSQL et fichiers privés dans un bucket S3 distinct, avec rétention."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-media",
            action="store_true",
            help="N'archiver que la base. À n'utiliser que si le média est sauvegardé autrement.",
        )

    def handle(self, *args, **options):
        database_url = os.getenv("DATABASE_URL")
        bucket = os.getenv("BACKUP_S3_BUCKET")
        media_bucket = os.getenv("AWS_STORAGE_BUCKET_NAME")
        if not database_url or not database_url.startswith(("postgres://", "postgresql://")):
            raise CommandError("DATABASE_URL PostgreSQL est obligatoire.")
        if not bucket:
            raise CommandError("BACKUP_S3_BUCKET est obligatoire.")
        if media_bucket and bucket == media_bucket:
            raise CommandError("Le bucket de sauvegarde doit être distinct du bucket média.")

        client = self.client()
        now = datetime.now(timezone.utc)
        stamp = f"{now:%Y%m%dT%H%M%SZ}"
        tiers = self.tiers(now)

        with tempfile.TemporaryDirectory(prefix="myent-backup-") as directory:
            dump = Path(directory) / f"myent-{stamp}.dump"
            self.dump_database(database_url, dump)
            self.upload(client, bucket, dump, "database", tiers)

            archive = None if options["skip_media"] else self.archive_media(Path(directory), stamp)
            if archive is not None:
                self.upload(client, bucket, archive, "media", tiers)

        self.stdout.write(self.style.SUCCESS("Sauvegarde terminée."))

    @staticmethod
    def client():
        return boto3.client(
            "s3",
            endpoint_url=os.getenv("AWS_S3_ENDPOINT_URL") or None,
            region_name=os.getenv("AWS_S3_REGION_NAME") or None,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
        )

    @staticmethod
    def tiers(now) -> list[tuple[str, int]]:
        """Les paliers de rétention actifs ce jour-là : quotidien, plus hebdomadaire ou mensuel."""
        targets = [("daily", int(os.getenv("BACKUP_DAILY_RETENTION", "14")))]
        if now.weekday() == 6:
            targets.append(("weekly", int(os.getenv("BACKUP_WEEKLY_RETENTION", "8"))))
        if now.day == 1:
            targets.append(("monthly", int(os.getenv("BACKUP_MONTHLY_RETENTION", "12"))))
        return targets

    def dump_database(self, database_url: str, destination: Path) -> None:
        try:
            subprocess.run(
                ["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file", str(destination), database_url],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            raise CommandError(f"Échec de pg_dump : {detail.strip()}") from exc

    def archive_media(self, directory: Path, stamp: str) -> Path | None:
        """Archive `MEDIA_ROOT`, ou explique pourquoi il n'y a rien à archiver.

        Sous S3, les fichiers sont déjà dans un bucket : les retélécharger pour les
        renvoyer ailleurs coûterait deux transferts et ne protégerait de rien de plus
        que le versionnement du bucket. La sauvegarde se limite alors à la base, et le
        dit — un silence se lirait comme une couverture complète.
        """
        if getattr(settings, "USE_S3", False):
            self.stdout.write("Média sur S3 : archivage local ignoré, le versionnement du bucket en tient lieu.")
            return None
        root = Path(settings.MEDIA_ROOT)
        if not root.is_dir() or not any(root.iterdir()):
            self.stdout.write("Aucun fichier privé à archiver.")
            return None
        archive = directory / f"myent-media-{stamp}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(root, arcname="media")
        self.stdout.write(f"Média archivé : {archive.stat().st_size / 1024 / 1024:.1f} Mo")
        return archive

    def upload(self, client, bucket: str, path: Path, kind: str, tiers: list[tuple[str, int]]) -> None:
        for tier, retention in tiers:
            key = f"{kind}/{tier}/{path.name}"
            client.upload_file(str(path), bucket, key)
            self.prune(client, bucket, f"{kind}/{tier}/", retention)
            self.stdout.write(f"s3://{bucket}/{key}")

    @staticmethod
    def prune(client, bucket, prefix, keep):
        paginator = client.get_paginator("list_objects_v2")
        objects = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            objects.extend(page.get("Contents", []))
        objects.sort(key=lambda item: item["LastModified"], reverse=True)
        stale = objects[max(keep, 0) :]
        for offset in range(0, len(stale), 1000):
            chunk = stale[offset : offset + 1000]
            if chunk:
                client.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": item["Key"]} for item in chunk]})
