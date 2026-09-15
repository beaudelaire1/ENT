"""Le branchement des règles de placement dans le Sablier.

Les règles (`placement.js`) et les descriptions de lieux sont testées ailleurs ; ici, on
vérifie que la page les transmet, que la photo et l'objet cadrent sur la même donnée, et
qu'aucune exception par univers ne subsiste dans le moteur.
"""

import json
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from sablier import scenes


def read_static(relative_path):
    return (settings.BASE_DIR / "static" / "sablier" / relative_path).read_text(encoding="utf-8")


class PlacementPageTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("placement", password="unused"))

    def test_the_page_hands_every_place_to_the_rules(self):
        html = self.client.get(reverse("sablier:home")).content.decode()
        payload = re.search(r'<script id="place-data" type="application/json">(.*?)</script>', html, re.DOTALL)
        places = json.loads(payload.group(1))
        self.assertEqual(set(places), {scene.decor for scene in scenes.SCENES})
        self.assertTrue(places["ancient_forest"]["photo"])
        # Le Fleuve du Temps est une scène en volume : il occupe l'écran entier, sans point focal à rogner.
        self.assertFalse(places["time_river"]["photo"])

    def test_the_rules_load_before_the_scripts_that_use_them(self):
        html = self.client.get(reverse("sablier:home")).content.decode()
        rules = html.index("sablier/placement.js")
        self.assertLess(rules, html.index("sablier/gallery.js"))
        self.assertLess(rules, html.index("sablier/sablier.js"))


class PlacementWiringTests(SimpleTestCase):
    def test_the_photo_and_the_object_frame_on_the_same_window(self):
        module = read_static("premium3d/photo-world.js")
        self.assertIn("globalThis.SablierPlacement.frame({ imageAspect, view, focus, zoom, pan })", module)
        recipes = read_static("premium3d/worlds.js")
        # Le cadrage est écrit une seule fois, dans la description du lieu.
        self.assertNotIn("focus: [", recipes)
        self.assertIn("focus:place.focus,drift:place.drift", recipes)

    def test_the_engine_poses_volumetric_objects_where_the_rules_say(self):
        engine = read_static("premium3d.js")
        self.assertIn("const placed = window.SablierObjectPlacement;", engine)
        self.assertIn("frame: () => currentWorld?.frame?.() || null", engine)
        # Plus d'exception écrite pour un univers : le support vient de l'image.
        self.assertNotIn("rain_refuge", engine)

    def test_the_timer_places_its_object_instead_of_shifting_it_to_a_supposed_ground(self):
        timer = read_static("sablier.js")
        self.assertIn("placeObject(mode);", timer)
        self.assertIn("window.SablierObjectPlacement=placed;", timer)
        self.assertNotIn("app.dataset.worldFoot", timer)
        self.assertIn("if(placed?.horizon!=null)return placed.horizon-placed.box.top;", timer)

    def test_the_fixed_view_is_framed_like_the_scene(self):
        gallery = read_static("gallery.js")
        self.assertIn("window.SablierPlacement.frame({imageAspect:16/9", gallery)
        self.assertIn("fallback.style.objectPosition=", gallery)
