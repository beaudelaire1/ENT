"""Registre des univers immersifs du Sablier.

La direction artistique vit dans ``scenes_catalog.json`` : le code ne mélange donc
plus les données de composition avec la logique d'exécution. La musique reste hors
de ce registre et sous le contrôle exclusif de l'utilisateur.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.utils.safestring import mark_safe


@dataclass(frozen=True)
class Scene:
    key: str
    label: str
    accent: str
    tint: str
    decor: str
    sky: str
    horizon: str
    ground: str
    light: str
    composition: str
    motion: tuple[str, ...]
    progression: str
    description: str

    @property
    def art_signature(self) -> tuple[str, tuple[str, ...], str]:
        return self.composition, self.motion, self.progression


def _load_catalog() -> tuple[Scene, ...]:
    path = Path(__file__).with_name("scenes_catalog.json")
    entries = json.loads(path.read_text(encoding="utf-8"))
    return tuple(Scene(**{**entry, "motion": tuple(entry["motion"])}) for entry in entries)


SCENES = _load_catalog()
BY_KEY = {scene.key: scene for scene in SCENES}
CHOICES = [(scene.key, scene.label) for scene in SCENES]
DEFAULT = "arbre_etoiles"

# Univers retirés du catalogue et le lieu vers lequel chacun redirige.
#
# Ils partageaient tous leur construction avec un univers conservé : seule la teinte
# du ciel changeait. Plutôt que de les supprimer sèchement — ce qui laisserait une
# préférence enregistrée pointer vers un univers inexistant — chacun renvoie vers le
# lieu dont il était la variante colorée.
LEGACY_REPLACED = {
    "concentration": "arbre_etoiles",
    "nuit": "arbre_etoiles",
    "eden": "foret",
    "printemps": "foret",
    "ete": "foret",
    "automne": "foret",
    "hiver": "aurores",
    "heaven": "aurores",
    "aurore": "aurores",
    "orage": "ocean",
    "pluie": "refuge_pluie",
    "braises": "refuge_pluie",
    "souvenirs": "refuge_pluie",
    "oasis": "sahara",
    "interstellaire": "galaxie",
    "fontaine": "fleuve_temps",
}


def palette_css() -> str:
    return mark_safe(
        "".join(
            f'[data-ambience="{scene.key}"]{{'
            f"--focus-accent:var(--focus-user-accent,{scene.accent});"
            f"--focus-tint:{scene.tint};"
            f"--world-sky:{scene.sky};"
            f"--world-horizon:{scene.horizon};"
            f"--world-ground:{scene.ground};"
            f"--world-light:{scene.light};}}"
            for scene in SCENES
        )
    )
