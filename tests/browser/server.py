"""Serveur de recette local avec base et médias jetables, jamais ceux du développeur."""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
os.environ.update(DJANGO_SETTINGS_MODULE="config.settings", DJANGO_DEBUG="true", USE_S3="false")
for name in ("DATABASE_URL", "REDIS_URL", "SENTRY_DSN", "EMAIL_HOST"):
    os.environ.pop(name, None)
# Active les tâches synchrones et les réglages de test existants.
sys.argv.append("test")

import django
from django.conf import settings
from django.core.management import call_command

with tempfile.TemporaryDirectory(prefix="myent-browser-") as directory:
    settings.DATABASES["default"]["NAME"] = str(Path(directory) / "db.sqlite3")
    settings.MEDIA_ROOT = Path(directory) / "media"
    settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
    django.setup()
    call_command("migrate", verbosity=0)
    from django.contrib.auth import get_user_model
    from accounts.models import UserProfile
    from formations.models import Competency, LearningPath, Period, ProgressRecord
    from planner.models import CalendarEvent
    from sablier.models import FocusPreference

    for name in ("browser-a", "browser-b"):
        user = get_user_model().objects.create_user(name, password="browser-test-only")
        UserProfile.objects.update_or_create(user=user, defaults={"timezone": "America/Cayenne"})
        FocusPreference.objects.create(user=user, mode="digital", decor_density=0, end_sound_enabled=False)
        path = LearningPath.objects.create(owner=user, title="Formation de recette")
        period = Period.objects.create(path=path, title="Période de recette")
        path.current_period = period
        path.save()
        known = Competency.objects.create(path=path, period=period, title="Déjà maîtrisée")
        Competency.objects.create(path=path, period=period, title="À découvrir")
        ProgressRecord.objects.create(owner=user, competency=known, mastery_level=4)
        start = datetime(2026, 9, 8, 2, 30, tzinfo=timezone.utc)
        CalendarEvent.objects.create(owner=user, title="Lundi soir", starts_at=start, ends_at=start + timedelta(minutes=20))
    call_command("runserver", "127.0.0.1:8765", use_reloader=False)
