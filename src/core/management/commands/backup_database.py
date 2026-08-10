from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sauvegarde PostgreSQL dans un bucket S3 distinct avec rétention."

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

        client = boto3.client(
            "s3",
            endpoint_url=os.getenv("AWS_S3_ENDPOINT_URL") or None,
            region_name=os.getenv("AWS_S3_REGION_NAME") or None,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
        )
        now = datetime.now(timezone.utc)
        filename = f"myent-{now:%Y%m%dT%H%M%SZ}.dump"
        with tempfile.TemporaryDirectory(prefix="myent-backup-") as directory:
            dump = Path(directory) / filename
            try:
                subprocess.run(
                    ["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file", str(dump), database_url],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except (OSError, subprocess.CalledProcessError) as exc:
                detail = getattr(exc, "stderr", "") or str(exc)
                raise CommandError(f"Échec de pg_dump : {detail.strip()}") from exc

            targets = [("daily", int(os.getenv("BACKUP_DAILY_RETENTION", "14")))]
            if now.weekday() == 6:
                targets.append(("weekly", int(os.getenv("BACKUP_WEEKLY_RETENTION", "8"))))
            if now.day == 1:
                targets.append(("monthly", int(os.getenv("BACKUP_MONTHLY_RETENTION", "12"))))
            for tier, retention in targets:
                key = f"database/{tier}/{filename}"
                client.upload_file(str(dump), bucket, key)
                self.prune(client, bucket, f"database/{tier}/", retention)
                self.stdout.write(f"s3://{bucket}/{key}")

        self.stdout.write(self.style.SUCCESS("Sauvegarde PostgreSQL terminée."))

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
