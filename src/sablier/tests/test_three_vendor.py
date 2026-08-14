import json

from django.conf import settings
from django.test import SimpleTestCase


class ThreeVendorGraphTests(SimpleTestCase):
    """Le bundle ES module de Three.js doit être vendored avec ses imports relatifs."""

    def setUp(self):
        self.root = settings.BASE_DIR.parent
        self.package = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        self.dockerfile = (self.root / "Dockerfile").read_text(encoding="utf-8")
        self.workflow = (self.root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    def test_vendor_script_copies_the_module_and_its_core_dependency(self):
        vendor = self.package["scripts"]["vendor"]
        self.assertIn("three.module.js", vendor)
        self.assertIn("three.core.js", vendor)

    def test_runtime_image_copies_the_complete_three_module_graph(self):
        for filename in ("three.module.js", "three.core.js"):
            with self.subTest(filename=filename):
                self.assertIn(f"node_modules/three/build/{filename}", self.dockerfile)
                self.assertIn(f"/app/src/static/vendor/{filename}", self.dockerfile)

    def test_ci_imports_three_instead_of_only_parsing_its_entrypoint(self):
        self.assertIn("test -s src/static/vendor/three.core.js", self.workflow)
        self.assertIn("import('./src/static/vendor/three.module.js')", self.workflow)
        self.assertIn("THREE.WebGLRenderer", self.workflow)
