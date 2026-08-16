"""La sauvegarde, et surtout ce qu'elle refuse de faire en silence."""

from __future__ import annotations

import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.management.commands.backup_database import Command

ENVIRONMENT = {
    "DATABASE_URL": "postgresql://myent:secret@postgres:5432/myent",
    "BACKUP_S3_BUCKET": "myent-backups",
    "AWS_STORAGE_BUCKET_NAME": "myent-media",
}


class FakeS3:
    """Un bucket en mémoire : on vérifie ce qui monte et ce qui est purgé."""

    def __init__(self, existing=None):
        self.uploaded: list[tuple[str, str]] = []
        self.deleted: list[str] = []
        self.existing = existing or []

    def upload_file(self, path, bucket, key):
        self.uploaded.append((bucket, key))

    def get_paginator(self, _operation):
        return self

    def paginate(self, Bucket, Prefix):  # noqa: N803 — signature imposée par boto3
        yield {"Contents": [item for item in self.existing if item["Key"].startswith(Prefix)]}

    def delete_objects(self, Bucket, Delete):  # noqa: N803 — signature imposée par boto3
        self.deleted.extend(item["Key"] for item in Delete["Objects"])


# Un mercredi quelconque. La commande ne monte les paliers hebdomadaire et mensuel que
# le dimanche et le premier du mois : laisser l'horloge réelle décider faisait dépendre
# les clés produites du jour où la suite tournait, et les tests écrits pour le seul
# palier quotidien tombaient chaque dimanche. Les paliers eux-mêmes restent couverts par
# `RetentionTests`, avec leurs dates explicites.
WEEKDAY = datetime(2026, 8, 12, 4, 30, tzinfo=timezone.utc)


def frozen_clock(instant):
    """Horloge figée : la commande lit l'heure elle-même, au moment du transfert."""

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz is None else instant.astimezone(tz)

    return Clock


def run(client, *, options=None, when=WEEKDAY, **environment):
    """Exécute la commande avec un pg_dump simulé, un S3 en mémoire et une horloge figée.

    Une variable passée à ``None`` est vidée plutôt que supprimée : la commande teste la
    valeur, et une chaîne vide est le cas réel d'un secret déclaré mais laissé vide.
    """
    values = {key: value or "" for key, value in {**ENVIRONMENT, **environment}.items()}

    def dump(_self, _url, destination):
        Path(destination).write_bytes(b"dump")

    with (
        mock.patch.dict("os.environ", values, clear=False),
        mock.patch.object(Command, "client", staticmethod(lambda: client)),
        mock.patch.object(Command, "dump_database", dump),
        mock.patch("core.management.commands.backup_database.datetime", frozen_clock(when)),
    ):
        call_command("backup_database", **(options or {}))


class GuardTests(SimpleTestCase):
    def test_refuses_a_non_postgresql_database(self):
        with self.assertRaises(CommandError):
            run(FakeS3(), DATABASE_URL="sqlite:///db.sqlite3")

    def test_refuses_without_a_backup_bucket(self):
        with self.assertRaises(CommandError):
            run(FakeS3(), BACKUP_S3_BUCKET=None)

    def test_refuses_when_the_backup_bucket_is_the_media_bucket(self):
        """Un même bucket compromis emporterait les données et leur copie."""
        with self.assertRaises(CommandError):
            run(FakeS3(), BACKUP_S3_BUCKET="myent-media")


class RetentionTests(SimpleTestCase):
    def test_a_weekday_only_writes_the_daily_tier(self):
        self.assertEqual([tier for tier, _ in Command.tiers(datetime(2026, 8, 12, tzinfo=timezone.utc))], ["daily"])

    def test_sunday_adds_the_weekly_tier(self):
        tiers = [tier for tier, _ in Command.tiers(datetime(2026, 8, 16, tzinfo=timezone.utc))]
        self.assertEqual(tiers, ["daily", "weekly"])

    def test_the_first_of_the_month_adds_the_monthly_tier(self):
        tiers = [tier for tier, _ in Command.tiers(datetime(2026, 9, 1, tzinfo=timezone.utc))]
        self.assertEqual(tiers, ["daily", "monthly"])

    def test_pruning_keeps_the_most_recent_and_deletes_the_rest(self):
        client = FakeS3(
            existing=[
                {"Key": f"database/daily/myent-{day}.dump", "LastModified": datetime(2026, 8, day, tzinfo=timezone.utc)}
                for day in range(1, 6)
            ]
        )
        Command.prune(client, "myent-backups", "database/daily/", keep=2)
        self.assertEqual(
            sorted(client.deleted),
            ["database/daily/myent-1.dump", "database/daily/myent-2.dump", "database/daily/myent-3.dump"],
        )


class MediaArchiveTests(SimpleTestCase):
    def archive(self, root: Path):
        with tempfile.TemporaryDirectory() as directory:
            with override_settings(MEDIA_ROOT=root, USE_S3=False):
                return Command().archive_media(Path(directory), "20260812T000000Z"), Path(directory)

    def test_media_files_are_archived(self):
        with tempfile.TemporaryDirectory() as media:
            root = Path(media)
            (root / "users" / "2").mkdir(parents=True)
            (root / "users" / "2" / "cours.pdf").write_bytes(b"contenu")
            with tempfile.TemporaryDirectory() as directory:
                with override_settings(MEDIA_ROOT=root, USE_S3=False):
                    archive = Command().archive_media(Path(directory), "20260812T000000Z")
                self.assertIsNotNone(archive)
                with tarfile.open(archive) as tar:
                    self.assertIn("media/users/2/cours.pdf", tar.getnames())

    def test_an_empty_media_root_produces_no_archive(self):
        with tempfile.TemporaryDirectory() as media:
            archive, _ = self.archive(Path(media))
            self.assertIsNone(archive)

    def test_s3_media_is_left_to_the_bucket(self):
        """Retélécharger un bucket pour le renvoyer ailleurs ne protège de rien de plus."""
        with tempfile.TemporaryDirectory() as media:
            root = Path(media)
            (root / "cours.pdf").write_bytes(b"contenu")
            with tempfile.TemporaryDirectory() as directory:
                with override_settings(MEDIA_ROOT=root, USE_S3=True):
                    self.assertIsNone(Command().archive_media(Path(directory), "20260812T000000Z"))


class FullRunTests(SimpleTestCase):
    def test_database_and_media_are_both_uploaded(self):
        client = FakeS3()
        with tempfile.TemporaryDirectory() as media:
            root = Path(media)
            (root / "cours.pdf").write_bytes(b"contenu")
            with override_settings(MEDIA_ROOT=root, USE_S3=False):
                run(client)
        kinds = {key.split("/")[0] for _bucket, key in client.uploaded}
        self.assertEqual(kinds, {"database", "media"})

    def test_skip_media_only_uploads_the_database(self):
        client = FakeS3()
        with tempfile.TemporaryDirectory() as media:
            root = Path(media)
            (root / "cours.pdf").write_bytes(b"contenu")
            with override_settings(MEDIA_ROOT=root, USE_S3=False):
                run(client, options={"skip_media": True})
        self.assertTrue(client.uploaded)
        kinds = {key.split("/")[0] for _bucket, key in client.uploaded}
        self.assertEqual(kinds, {"database"})

    def test_database_keys_keep_their_historical_prefix(self):
        """Les sauvegardes déjà en place restent dans le même préfixe."""
        client = FakeS3()
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=Path(media), USE_S3=False):
                run(client)
        self.assertTrue(all(key.startswith("database/daily/myent-") for _bucket, key in client.uploaded))

    def test_a_sunday_run_also_writes_the_weekly_copy(self):
        """Le dimanche, la même sauvegarde part aussi sous le palier hebdomadaire.

        Ce jour-là, la commande produit deux clés pour un seul transfert : c'est ce
        que l'ancien contrôle de préfixe, écrit pour le seul palier quotidien,
        n'avait pas prévu — la suite tombait donc tous les dimanches.
        """
        client = FakeS3()
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=Path(media), USE_S3=False):
                run(client, when=datetime(2026, 8, 16, 4, 30, tzinfo=timezone.utc))
        keys = [key for _bucket, key in client.uploaded]
        self.assertEqual(
            sorted(key.split("/")[1] for key in keys if key.startswith("database/")),
            ["daily", "weekly"],
        )
