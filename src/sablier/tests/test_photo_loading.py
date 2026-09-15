"""L'ordre de chargement d'un lieu photographié.

La scène restait vide jusqu'à une minute sur une connexion lente : la photo du lieu ne
partait qu'après Three.js et ses modules, en concurrence avec un ciel panoramique que
personne ne voyait, et la vue fixe ne se montrait qu'en repli.
"""

import re

from django.conf import settings
from django.test import SimpleTestCase

from sablier import scenes


def read_static(relative_path):
    return (settings.BASE_DIR / "static" / "sablier" / relative_path).read_text(encoding="utf-8")


class PhotoLoadingOrderTests(SimpleTestCase):
    def test_the_view_of_the_place_shows_from_page_open_beneath_the_scene(self):
        css = read_static("sablier.css")
        self.assertIn(
            '.focus-app:not([data-renderer3d="fallback"]) .focus-stage .world-fallback[src] '
            "{ display:block; z-index:0!important; }",
            css,
        )
        gallery = read_static("gallery.js")
        # L'adresse est posée à chaque état, et plus seulement quand la 3D a renoncé.
        self.assertIn("if(fallback.getAttribute('src')!==url)fallback.src=url;", gallery)
        self.assertNotIn("if(!status.hidden){", gallery)

    def test_the_gallery_knows_exactly_which_places_have_no_photo(self):
        """La photo en paysage n'est demandée que si elle existe : sinon, une erreur 404."""
        gallery = read_static("gallery.js")
        declared = set(re.findall(r"'([a-z_]+)'", re.search(r"WITHOUT_PHOTO=new Set\(\[(.*?)\]\)", gallery).group(1)))
        recipes = read_static("premium3d/worlds.js")
        imaged = set(re.findall(r'photo: \{src: "([a-z_]+)\.webp"', recipes))
        self.assertEqual(declared, {scene.decor for scene in scenes.SCENES} - imaged)

    def test_the_photo_is_requested_at_the_address_the_scene_will_use(self):
        """Deux adresses différentes feraient télécharger la même photo deux fois."""
        gallery = read_static("gallery.js")
        module = read_static("premium3d/photo-world.js")
        self.assertIn("replace(/thumbnails\\/$/,'photos/')}${decor}.webp`", gallery)
        self.assertIn('const BASE = new URL("../photos/", import.meta.url);', module)

    def test_a_photographed_place_does_not_download_a_sky_nobody_sees(self):
        engine = read_static("premium3d.js")
        self.assertIn("if (currentWorld.photo && !SUPPORTED.has(state.mode)) return;", engine)
        # Choisir un objet en volume dans un lieu photographié doit encore allumer son ciel.
        set_mode = engine[engine.index("function setMode(mode)") : engine.index("function syncFallback()")]
        self.assertIn("requestPanorama();", set_mode)
