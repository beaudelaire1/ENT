"""Les commandes posées sur la scène ne doivent pas se recouvrir.

Le disque de musique déclarait `position:absolute` au coin de la scène, mais une règle
plus spécifique remettait tous les enfants de la scène dans le flux : il retombait au
centre, sur le bouton de pause de l'immersion.
"""

from django.conf import settings
from django.test import SimpleTestCase


def stylesheet():
    return (settings.BASE_DIR / "static" / "sablier" / "sablier.css").read_text(encoding="utf-8")


class StageControlsLayoutTests(SimpleTestCase):
    def test_the_music_disc_stays_in_the_corner_of_the_stage(self):
        css = stylesheet()
        generic = ".focus-stage > *:not(.decor-canvas):not(.stage-3d-canvas) { position:relative;"
        pinned = ".focus-app .focus-stage > .stage-disc { position:absolute; }"
        self.assertIn(generic, css)
        self.assertIn(pinned, css)
        # À spécificité égale (trois classes), c'est la règle écrite après qui s'applique.
        self.assertGreater(css.index(pinned), css.index(generic))

    def test_the_pause_button_and_the_disc_share_the_bottom_of_the_stage_without_overlap(self):
        css = stylesheet()
        # Le bouton est centré en bas, le disque ancré à droite : deux zones distinctes.
        self.assertIn("bottom:22px;left:50%;transform:translateX(-50%);min-width:140px;", css)
        self.assertIn("right:16px;\n  bottom:14px;", css)
