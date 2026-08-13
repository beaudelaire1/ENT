"""Le stockage des fichiers statiques tel qu'il tourne en production.

La suite s'exécute avec le stockage simple, qui ne vérifie rien : un gabarit demandant une
ressource inexistante y passait inaperçu. En production, le stockage à manifeste lève une
`ValueError` — et c'est toute la page qui rend une erreur 500. C'est exactement ce qui est
arrivé à l'administration après l'ajout de Jazzmin, dont le gabarit passe un répertoire à
``{% static %}``.

Ces tests reproduisent donc la configuration de production plutôt que celle des tests.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

PRODUCTION_STORAGE = {
    "staticfiles": {"BACKEND": "core.storage.ForgivingManifestStaticFilesStorage"},
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
}


class ManifestStorageTests(TestCase):
    """Rend les écrans avec le stockage à manifeste, comme en production."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.static_root = Path(tempfile.mkdtemp(prefix="myent-static-"))
        with override_settings(STATIC_ROOT=cls.static_root, STORAGES=PRODUCTION_STORAGE):
            call_command("collectstatic", "--noinput", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.static_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_superuser("admin", "admin@example.test", "motdepasse-de-test")

    def test_the_manifest_was_written(self):
        manifest = self.static_root / "staticfiles.json"
        self.assertTrue(manifest.exists())
        entries = json.loads(manifest.read_text(encoding="utf-8"))["paths"]
        self.assertIn("css/app.css", entries)

    def test_our_own_files_are_fingerprinted(self):
        """La contrepartie de la tolérance ne doit pas être la perte de l'empreinte."""
        manifest = json.loads((self.static_root / "staticfiles.json").read_text(encoding="utf-8"))["paths"]
        self.assertNotEqual(manifest["css/app.css"], "css/app.css")

    def test_the_admin_login_renders(self):
        with override_settings(STATIC_ROOT=self.static_root, STORAGES=PRODUCTION_STORAGE):
            response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_the_admin_index_renders(self):
        """L'écran qui rendait 500 : Jazzmin y demande un répertoire à `{% static %}`."""
        self.client.force_login(self.user)
        with override_settings(STATIC_ROOT=self.static_root, STORAGES=PRODUCTION_STORAGE):
            response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_an_unknown_name_falls_back_instead_of_raising(self):
        from django.contrib.staticfiles.storage import staticfiles_storage

        with override_settings(STATIC_ROOT=self.static_root, STORAGES=PRODUCTION_STORAGE):
            from core.storage import ForgivingManifestStaticFilesStorage

            storage = ForgivingManifestStaticFilesStorage()
            self.assertIn("vendor/bootswatch", storage.url("vendor/bootswatch"))
        self.assertIsNotNone(staticfiles_storage)
