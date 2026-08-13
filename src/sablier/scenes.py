"""Registre des univers immersifs du Sablier.

Les clés sont volontairement les identifiants historiques déjà stockés en production.
Elles ne décrivent plus l'esthétique visible : elles servent uniquement de contrat de
persistance afin qu'une refonte artistique ne force aucune migration des préférences.

Un univers n'est pas une palette. Il décrit un lieu : composition, profondeur,
source lumineuse, mouvement et évolution pendant la session. Ces informations
servent aussi de contrat artistique aux tests de non-régression.

La musique reste volontairement absente de ce registre. Les univers ne démarrent,
ne choisissent et ne modifient jamais une piste : le lecteur personnel de Sablier
reste un système indépendant, entièrement commandé par l'utilisateur.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    selectable: bool = True

    @property
    def art_signature(self) -> tuple[str, tuple[str, ...], str]:
        """Signature structurelle : deux univers ne doivent pas être des recolorations."""
        return self.composition, self.motion, self.progression


SCENES: tuple[Scene, ...] = (
    Scene(
        "concentration",
        "Arbre des étoiles",
        "#7ad8ff",
        "#154a70",
        "star_tree",
        "#020d19",
        "#0c3d5d",
        "#061017",
        "#ffe7a0",
        "island-tree-reflecting-pool",
        ("water-ripples", "canopy-glow", "star-drift"),
        "sky-deepens-and-tree-light-warms",
        "Un arbre monumental sur une île d'eau noire, entre ciel étoilé et lumière dorée.",
    ),
    Scene(
        "printemps",
        "Éden",
        "#91e7a8",
        "#1f6b4a",
        "eden",
        "#061714",
        "#285b42",
        "#08130e",
        "#fff0a6",
        "garden-terraces-great-tree-stream",
        ("leaf-breath", "fireflies", "stream-glints"),
        "sunbeams-cross-the-canopy",
        "Un jardin primordial organisé autour d'un arbre immense, de terrasses et d'une eau claire.",
    ),
    Scene(
        "ete",
        "Oasis des confins",
        "#ffd17b",
        "#91562c",
        "oasis",
        "#171426",
        "#8a573f",
        "#25130d",
        "#ffd89b",
        "dunes-oasis-ruins-palms-distant-mesa",
        ("heat-haze", "palm-breeze", "sand-veils"),
        "sunset-turns-to-starlight",
        "Une oasis isolée entre dunes, ruines anciennes et ciel de fin du monde.",
    ),
    Scene(
        "automne",
        "Fleuve du Temps",
        "#9dcaff",
        "#354e8b",
        "time_river",
        "#070d1d",
        "#314b76",
        "#090d18",
        "#f2d6a0",
        "ruins-river-arches-temporal-shards",
        ("river-flow", "light-shards", "mist-drift"),
        "ruins-cross-faintly-between-eras",
        "Un fleuve lumineux traverse des ruines appartenant à plusieurs époques à la fois.",
    ),
    Scene(
        "hiver",
        "Vallée des aurores",
        "#7defcf",
        "#28516a",
        "aurora_valley",
        "#06121e",
        "#17445b",
        "#081018",
        "#baffef",
        "mountain-valley-lake-aurora",
        ("aurora-ribbons", "lake-reflection", "snow-drift"),
        "aurora-gains-depth-with-elapsed-time",
        "Une vallée glacée et son lac reflètent de larges voiles d'aurore au-dessus des montagnes.",
    ),
    Scene(
        "pluie",
        "Refuge sous la pluie",
        "#d7b36c",
        "#42505d",
        "rain_refuge",
        "#111820",
        "#344756",
        "#15130f",
        "#ffd28a",
        "interior-window-lamp-rain-city",
        ("window-rain", "outside-bokeh", "lamp-breath"),
        "interior-warmth-increases-as-outside-darkens",
        "Un refuge chaud derrière une grande vitre, pendant qu'une pluie froide efface le dehors.",
    ),
    Scene(
        "ocean",
        "Sanctuaire abyssal",
        "#58d6d8",
        "#155d68",
        "abyss",
        "#021217",
        "#0d4b55",
        "#031015",
        "#9ff8ee",
        "submerged-temple-columns-surface-shafts",
        ("caustics", "bubbles", "bioluminescent-drift"),
        "surface-rays-shift-with-the-session",
        "Un sanctuaire englouti dort sous des rais de lumière venus d'une surface très lointaine.",
    ),
    Scene(
        "sahara",
        "Fontaine de l’Éternité",
        "#57e3df",
        "#176c78",
        "eternity_fountain",
        "#061724",
        "#1f7180",
        "#07141a",
        "#dffff7",
        "cliff-city-canal-waterfalls",
        ("waterfall-mist", "canal-shimmer", "distant-birds"),
        "water-light-slowly-brightens",
        "Une cité verticale oubliée, traversée par des bassins turquoise et de longues cascades.",
    ),
    Scene(
        "foret",
        "Souvenirs",
        "#d2b6ff",
        "#5c4772",
        "memories",
        "#15111d",
        "#55445f",
        "#100d14",
        "#f0cba2",
        "fog-room-frames-distant-platform",
        ("dust-float", "curtain-breath", "memory-flicker"),
        "distant-frames-appear-then-fade",
        "Un lieu impossible composé de fragments familiers qui émergent doucement dans la brume.",
    ),
    Scene(
        "orage",
        "Interstellaire",
        "#8eb8ff",
        "#283966",
        "interstellar",
        "#01040d",
        "#111d3c",
        "#03050a",
        "#c8dbff",
        "observation-deck-planet-rings-deep-space",
        ("star-parallax", "planet-drift", "navigation-lights"),
        "planet-limb-slides-across-horizon",
        "Une plateforme d'observation dérive près d'une planète géante et de ses anneaux.",
    ),
    # Identifiant historique conservé uniquement pour les utilisateurs ayant enregistré
    # « Braises » avant la refonte. Il converge vers Souvenirs et n'est plus proposé.
    Scene(
        "braises",
        "Souvenirs",
        "#d2b6ff",
        "#5c4772",
        "memories",
        "#15111d",
        "#55445f",
        "#100d14",
        "#f0cba2",
        "legacy-memory-alias",
        ("legacy-alias", "no-new-art-direction"),
        "compatibility-only",
        "Compatibilité invisible avec l'ancienne préférence Braises ; aucun nouvel univers n'est dupliqué.",
        False,
    ),
    Scene(
        "aurore",
        "Heaven — Hauts Cieux",
        "#bce7ff",
        "#72abc5",
        "heaven",
        "#5d91ad",
        "#b9ddeb",
        "#30495a",
        "#fff8d8",
        "floating-islands-temple-cloud-sea",
        ("cloud-drift", "waterfall-veils", "light-rays"),
        "clouds-open-toward-the-light",
        "Des îles et architectures suspendues dominent une mer de nuages sans horizon terrestre.",
    ),
    Scene(
        "nuit",
        "Galaxie",
        "#d18aff",
        "#55286f",
        "galaxy",
        "#03020b",
        "#25133d",
        "#05030b",
        "#f2d6ff",
        "spiral-galaxy-nebula-starfield",
        ("spiral-rotation", "nebula-breath", "stellar-twinkle"),
        "galactic-core-pulses-more-clearly",
        "La scène s'affranchit de tout repère humain : une galaxie entière devient le paysage.",
    ),
)

BY_KEY = {scene.key: scene for scene in SCENES}
CHOICES = [(scene.key, scene.label) for scene in SCENES if scene.selectable]
DEFAULT = "concentration"
STORAGE_KEYS = tuple(scene.key for scene in SCENES)


def palette_css() -> str:
    """Expose séparément la couleur du minuteur et la palette du monde.

    Une couleur personnelle peut donc modifier le sablier sans repeindre le ciel,
    l'eau, les ombres et la lumière de l'univers. C'est le garde-fou principal contre
    les anciennes « ambiances » qui n'étaient que des recolorations.
    """
    return mark_safe(  # noqa: S308 — registre statique, aucune donnée utilisateur
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
