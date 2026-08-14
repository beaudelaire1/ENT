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

    def test_generated_three_vendor_files_are_not_versioned_inputs(self):
        gitignore = self.repo_text(".gitignore")
        for path in (
            "/src/static/vendor/three.module.js",
            "/src/static/vendor/three.core.js",
        ):
            with self.subTest(path=path):
                self.assertIn(path, gitignore)

    def test_vendor_command_generates_complete_three_module_graph(self):
        package = json.loads(self.repo_text("package.json"))
        vendor = package["scripts"]["vendor"]
        self.assertIn("three.module.js", vendor)
        self.assertIn("three.core.js", vendor)

        workflow = self.repo_text(".github/workflows/ci.yml")
        self.assertIn("test -s src/static/vendor/three.module.js", workflow)
        self.assertIn("test -s src/static/vendor/three.core.js", workflow)
        self.assertIn("import('./src/static/vendor/three.module.js')", workflow)
