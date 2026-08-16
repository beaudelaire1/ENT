import json

from django.conf import settings
from django.test import SimpleTestCase


class ThreeVendorGraphTests(SimpleTestCase):
    """Le moteur 3D doit être vendu avec la totalité de son graphe d'imports.

    Un module manquant ne casse rien de visible côté serveur : le navigateur
    échoue à l'import, la scène immersive bascule sur son dessin 2D, et la
    régression ne se lit que sur l'écran de l'utilisateur.
    """

    def setUp(self):
        self.root = settings.BASE_DIR.parent
        self.package = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        self.dockerfile = (self.root / "Dockerfile").read_text(encoding="utf-8")
        self.workflow = (self.root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.script = (self.root / "tools" / "vendor-three.mjs").read_text(encoding="utf-8")

    def test_vendoring_is_a_script_not_a_hand_written_file_list(self):
        """Copier fichier par fichier avait fini par oublier ``three.core.js``.

        Le script suit les imports : il copie le point d'entrée, son noyau et les
        modules d'exemple, puis réécrit les spécificateurs nus vers le dossier vendu.
        """
        self.assertEqual(self.package["scripts"]["vendor"], "node tools/vendor-three.mjs")
        for required in ("three.module.js", "three.core.js", "objects/Sky.js"):
            with self.subTest(required=required):
                self.assertIn(required, self.script)
        for addon in ("EffectComposer.js", "RenderPass.js", "UnrealBloomPass.js", "OutputPass.js"):
            with self.subTest(addon=addon):
                self.assertIn(addon, self.script)

    def test_vendor_script_refuses_to_leave_a_dangling_import(self):
        """Le script échoue plutôt que de livrer un dossier incomplet."""
        self.assertIn("importe encore", self.script)
        self.assertIn("process.exit(1)", self.script)

    def test_runtime_image_builds_the_vendor_tree_instead_of_copying_files(self):
        self.assertIn("COPY package.json package-lock.json ./", self.dockerfile)
        self.assertIn("COPY tools/vendor-three.mjs", self.dockerfile)
        self.assertIn("npm run vendor", self.dockerfile)
        self.assertIn("/app/src/static/vendor/", self.dockerfile)

    def test_ci_resolves_the_whole_module_graph_offline(self):
        self.assertIn("npm run vendor", self.workflow)
        for artefact in (
            "src/static/vendor/three.module.js",
            "src/static/vendor/three.core.js",
            "src/static/vendor/three-addons/objects/Sky.js",
        ):
            with self.subTest(artefact=artefact):
                self.assertIn(f"test -s {artefact}", self.workflow)
        self.assertIn("import('./src/static/vendor/three.module.js')", self.workflow)
        self.assertIn("THREE.WebGLRenderer", self.workflow)
        self.assertIn("three-addons/postprocessing/EffectComposer.js", self.workflow)

    def test_ci_checks_every_premium_module_and_not_only_the_entrypoint(self):
        self.assertIn("src/static/sablier/premium3d/*.js", self.workflow)
        self.assertIn("node --input-type=module --check", self.workflow)
