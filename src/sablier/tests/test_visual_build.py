import json

from django.conf import settings
from django.test import SimpleTestCase


class VisualRuntimeBuildTests(SimpleTestCase):
    def repo_text(self, relative_path):
        return (settings.BASE_DIR.parent / relative_path).read_text(encoding="utf-8")

    def test_three_dependency_is_locked_exactly(self):
        package = json.loads(self.repo_text("package.json"))
        lock = json.loads(self.repo_text("package-lock.json"))

        self.assertEqual(package["dependencies"]["three"], "0.184.0")
        self.assertEqual(lock["lockfileVersion"], 3)
        self.assertEqual(lock["packages"][""]["dependencies"]["three"], "0.184.0")
        self.assertEqual(lock["packages"]["node_modules/three"]["version"], "0.184.0")

    def test_ci_and_docker_use_clean_lockfile_install(self):
        dockerfile = self.repo_text("Dockerfile")
        workflow = self.repo_text(".github/workflows/ci.yml")

        self.assertIn("COPY package.json package-lock.json ./", dockerfile)
        self.assertIn("npm ci --ignore-scripts --no-audit --no-fund", dockerfile)
        self.assertNotIn("npm install --ignore-scripts", dockerfile)

        self.assertIn("npm ci --ignore-scripts --no-audit --no-fund", workflow)
        self.assertNotIn("npm install --ignore-scripts", workflow)
        self.assertIn("cache-dependency-path: package-lock.json", workflow)

    def test_generated_three_vendor_tree_is_not_a_versioned_input(self):
        """Le dossier vendu est un produit de compilation, jamais une source.

        Il contient désormais un arbre entier — noyau, modules d'exemple, shaders —
        et non plus deux fichiers : l'ignorer au fichier près laissait rentrer dans
        l'historique tout ce qui n'était pas nommé.
        """
        gitignore = self.repo_text(".gitignore")
        self.assertIn("/src/static/vendor/", gitignore)
