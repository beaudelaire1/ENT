"""La description de chaque lieu, sur laquelle les objets sont posés.

`static/sablier/placement.js` n'applique que des règles : il fait confiance à ces
données. Un point hors de l'image, une surface inconnue ou un type mal orthographié
ferait tomber l'objet dans un cas par défaut sans que rien ne le signale.
"""

import re

from django.conf import settings
from django.test import SimpleTestCase

from sablier import scenes

TYPES = {"exterieur", "interieur", "espace", "sous-marin"}
KINDS = {"table", "rebord", "sol"}


def rules():
    return (settings.BASE_DIR / "static" / "sablier" / "placement.js").read_text(encoding="utf-8")


def in_image(value):
    return isinstance(value, (int, float)) and 0 <= value <= 1


class PlaceCatalogTests(SimpleTestCase):
    def surfaces(self):
        block = re.search(r"const SHADOW = \{(.*?)\n  \};", rules(), re.DOTALL).group(1)
        return set(re.findall(r'^\s*"?([a-zé]+)"?:', block, re.MULTILINE))

    def test_every_universe_describes_its_place(self):
        for scene in scenes.SCENES:
            with self.subTest(scene=scene.decor):
                self.assertIsInstance(scene.place, dict)
                self.assertIn(scene.place["type"], TYPES)
                self.assertEqual(len(scene.place["focus"]), 2)
                self.assertTrue(all(in_image(value) for value in scene.place["focus"]))
                self.assertTrue(0 <= scene.place["drift"] <= 0.1)

    def test_supports_are_segments_of_the_image_with_known_kinds_and_surfaces(self):
        surfaces = self.surfaces()
        self.assertIn("bois", surfaces)
        for scene in scenes.SCENES:
            for index, support in enumerate(scene.place["supports"]):
                with self.subTest(scene=scene.decor, support=index):
                    self.assertIn(support["kind"], KINDS)
                    self.assertIn(support["surface"], surfaces)
                    self.assertEqual(len(support["line"]), 2)
                    for point in support["line"]:
                        self.assertTrue(all(in_image(value) for value in point))
                    # Une profondeur, ou une par extrémité pour un support qui s'enfonce dans l'image.
                    depths = support["depth"] if isinstance(support["depth"], list) else [support["depth"]]
                    self.assertIn(len(depths), (1, 2))
                    self.assertTrue(all(in_image(depth) for depth in depths))

    def test_sky_window_and_floating_point_stay_inside_the_image(self):
        for scene in scenes.SCENES:
            place = scene.place
            with self.subTest(scene=scene.decor):
                for area in [place["sky"]["area"] if place["sky"] else None, place["window"]]:
                    if area is None:
                        continue
                    self.assertTrue(all(in_image(value) for value in area))
                    self.assertLess(area[0], area[2])
                    self.assertLess(area[1], area[3])
                if place["sky"] and place["sky"]["horizon"] is not None:
                    self.assertTrue(in_image(place["sky"]["horizon"]))
                if place["float"] is not None:
                    self.assertTrue(all(in_image(value) for value in place["float"]))

    def test_a_place_without_surface_says_where_the_object_floats(self):
        """Sans support, les règles font flotter l'objet : un lieu d'espace le déclare."""
        for scene in scenes.SCENES:
            place = scene.place
            with self.subTest(scene=scene.decor):
                if place["type"] == "espace":
                    self.assertIsNotNone(place["float"])
                else:
                    self.assertTrue(place["supports"], "un lieu habitable doit offrir au moins un support")
