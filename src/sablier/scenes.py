"""Registre des univers immersifs du Sablier.

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

    @property
    def art_signature(self) -> tuple[str, tuple[str, ...], str]:
        return self.composition, self.motion, self.progression


SCENES: tuple[Scene, ...] = (
    Scene("arbre_etoiles", "Arbre des étoiles", "#7ad8ff", "#154a70", "star_tree", "#020d19", "#0c3d5d", "#061017", "#ffe7a0", "island-tree-reflecting-pool", ("water-ripples", "canopy-glow", "star-drift"), "sky-deepens-and-tree-light-warms", "Un arbre monumental sur une île d'eau noire, entre ciel étoilé et lumière dorée."),
    Scene("fontaine", "Fontaine de l’Éternité", "#57e3df", "#176c78", "eternity_fountain", "#061724", "#1f7180", "#07141a", "#dffff7", "cliff-city-canal-waterfalls", ("waterfall-mist", "canal-shimmer", "distant-birds"), "water-light-slowly-brightens", "Une cité verticale oubliée, traversée par des bassins turquoise et de longues cascades."),
    Scene("eden", "Éden", "#91e7a8", "#1f6b4a", "eden", "#061714", "#285b42", "#08130e", "#fff0a6", "garden-terraces-great-tree-stream", ("leaf-breath", "fireflies", "stream-glints"), "sunbeams-cross-the-canopy", "Un jardin primordial organisé autour d'un arbre immense, de terrasses et d'une eau claire."),
    Scene("fleuve_temps", "Fleuve du Temps", "#9dcaff", "#354e8b", "time_river", "#070d1d", "#314b76", "#090d18", "#f2d6a0", "ruins-river-arches-temporal-shards", ("river-flow", "light-shards", "mist-drift"), "ruins-cross-faintly-between-eras", "Un fleuve lumineux traverse des ruines appartenant à plusieurs époques à la fois."),
    Scene("souvenirs", "Souvenirs", "#d2b6ff", "#5c4772", "memories", "#15111d", "#55445f", "#100d14", "#f0cba2", "fog-room-frames-distant-platform", ("dust-float", "curtain-breath", "memory-flicker"), "distant-frames-appear-then-fade", "Un lieu impossible composé de fragments familiers qui émergent doucement dans la brume."),
    Scene("interstellaire", "Interstellaire", "#8eb8ff", "#283966", "interstellar", "#01040d", "#111d3c", "#03050a", "#c8dbff", "observation-deck-planet-rings-deep-space", ("star-parallax", "planet-drift", "navigation-lights"), "planet-limb-slides-across-horizon", "Une plateforme d'observation dérive près d'une planète géante et de ses anneaux."),
    Scene("galaxie", "Galaxie", "#d18aff", "#55286f", "galaxy", "#03020b", "#25133d", "#05030b", "#f2d6ff", "spiral-galaxy-nebula-starfield", ("spiral-rotation", "nebula-breath", "stellar-twinkle"), "galactic-core-pulses-more-clearly", "La scène s'affranchit de tout repère humain : une galaxie entière devient le paysage."),
    Scene("heaven", "Heaven — Hauts Cieux", "#bce7ff", "#72abc5", "heaven", "#5d91ad", "#b9ddeb", "#30495a", "#fff8d8", "floating-islands-temple-cloud-sea", ("cloud-drift", "waterfall-veils", "light-rays"), "clouds-open-toward-the-light", "Des îles et architectures suspendues dominent une mer de nuages sans horizon terrestre."),
    Scene("oasis", "Oasis des confins", "#ffd17b", "#91562c", "oasis", "#171426", "#8a573f", "#25130d", "#ffd89b", "dunes-oasis-ruins-palms-distant-mesa", ("heat-haze", "palm-breeze", "sand-veils"), "sunset-turns-to-starlight", "Une oasis isolée entre dunes, ruines anciennes et ciel de fin du monde."),
    Scene("abysses", "Sanctuaire abyssal", "#58d6d8", "#155d68", "abyss", "#021217", "#0d4b55", "#031015", "#9ff8ee", "submerged-temple-columns-surface-shafts", ("caustics", "bubbles", "bioluminescent-drift"), "surface-rays-shift-with-the-session", "Un sanctuaire englouti dort sous des rais de lumière venus d'une surface très lointaine."),
    Scene("refuge_pluie", "Refuge sous la pluie", "#d7b36c", "#42505d", "rain_refuge", "#111820", "#344756", "#15130f", "#ffd28a", "interior-window-lamp-rain-city", ("window-rain", "outside-bokeh", "lamp-breath"), "interior-warmth-increases-as-outside-darkens", "Un refuge chaud derrière une grande vitre, pendant qu'une pluie froide efface le dehors."),
    Scene("aurores", "Vallée des aurores", "#7defcf", "#28516a", "aurora_valley", "#06121e", "#17445b", "#081018", "#baffef", "mountain-valley-lake-aurora", ("aurora-ribbons", "lake-reflection", "snow-drift"), "aurora-gains-depth-with-elapsed-time", "Une vallée glacée et son lac reflètent de larges voiles d'aurore au-dessus des montagnes."),
    Scene("printemps", "Printemps", "#f0b9ce", "#6f9b72", "spring_meadow", "#8dc9d8", "#d5e6cd", "#39533a", "#fff3c3", "orchard-meadow-stream-blossom-gate", ("petal-drift", "stream-shimmer", "branch-breeze"), "blossom-light-softens-toward-evening", "Une vallée de vergers en fleurs, traversée par un ruisseau et cadrée par deux arbres en pleine floraison."),
    Scene("ete", "Été", "#ffd47e", "#9b744c", "summer_terrace", "#4e94c0", "#f3c982", "#72523a", "#fff0ae", "sunlit-stone-terrace-pergola-valley-pool", ("heat-shimmer", "vine-breeze", "pool-glints"), "afternoon-sun-turns-amber", "Une terrasse minérale suspendue au-dessus d'une vallée, sous une pergola végétale et un soleil d'été franc."),
    Scene("automne", "Automne", "#dc8a39", "#7a4632", "autumn_lake", "#6b7280", "#d49963", "#3b2b25", "#ffd39d", "amber-forest-lake-boardwalk-low-sun", ("leaf-fall", "lake-ripples", "low-mist"), "foliage-deepens-and-sun-lowers", "Un lac sombre bordé d'une forêt ambrée et d'un chemin de bois, dans une lumière basse de fin de saison."),
    Scene("hiver", "Hiver", "#d9f3ff", "#6a8597", "winter_lodge", "#4c627a", "#b4cad8", "#60747d", "#eef8ff", "alpine-peaks-snowfield-lodge-window", ("snow-fall", "chimney-drift", "window-glow"), "snow-light-cools-while-lodge-warms", "Un refuge alpin minuscule face à de hauts sommets, posé dans un champ de neige presque silencieux."),
    Scene("pluie", "Pluie", "#78b8e8", "#344b61", "rain_city", "#101923", "#263748", "#10151a", "#b7d5ea", "rainy-city-street-neon-reflections", ("street-rain", "reflection-pulse", "distant-traffic-bokeh"), "street-reflections-grow-as-sky-darkens", "Une rue urbaine nocturne sous une pluie dense, où les rares lumières se prolongent dans l'asphalte mouillé."),
    Scene("ocean", "Océan", "#74c7da", "#326677", "ocean_cliffs", "#5f8ba7", "#b2c8d0", "#31596a", "#f6e5c7", "open-ocean-cliffs-horizon-sea-cave", ("long-swell", "foam-lines", "distant-seabirds"), "horizon-clears-and-swell-slows", "Un océan ouvert vu depuis des falaises sombres, avec une houle longue et un horizon immense plutôt qu'un fond sous-marin."),
    Scene("sahara", "Sahara", "#efb76f", "#9a5a32", "sahara_observatory", "#3c3951", "#d6935c", "#7f4727", "#ffd39b", "monumental-dunes-buried-observatory-twilight", ("low-sand-veils", "heat-haze", "stars-emerge"), "twilight-crosses-from-amber-to-deep-blue", "Des dunes monumentales encerclent un ancien observatoire à demi enseveli, loin de toute oasis et de toute présence moderne."),
    Scene("foret", "Forêt", "#9bc6a4", "#29483b", "ancient_forest", "#0b1c17", "#224136", "#101c17", "#dff2bf", "towering-redwood-grove-light-shafts-moss-floor", ("spore-drift", "canopy-breath", "light-shaft-motion"), "sunshafts-migrate-between-trunks", "Une forêt ancienne de troncs gigantesques, profonde et humide, où la lumière traverse la canopée en colonnes étroites."),
    Scene("orage", "Orage", "#a8b9db", "#3c4353", "storm_cliffs", "#11131b", "#333846", "#15191d", "#dce8ff", "storm-sea-cliffs-shelf-cloud-lightning", ("wave-chop", "cloud-race", "rare-lightning"), "storm-front-moves-across-the-horizon", "Un front d'orage traverse des falaises battues par la mer, avec des éclairs rares qui éclairent toute la masse nuageuse."),
    Scene("braises", "Braises", "#ff9b4b", "#6f3927", "ember_hearth", "#120d0b", "#271713", "#090706", "#ffd083", "stone-hearth-dark-room-ember-bed", ("ember-rise", "coal-pulse", "warm-light-breath"), "embers-cool-from-gold-to-deep-red", "Un foyer de pierre presque éteint dans une pièce sombre, où les braises et leur lumière deviennent le seul paysage."),
    Scene("aurore", "Aurore", "#77f0b0", "#23556a", "polar_sky", "#02111d", "#0d3448", "#10222a", "#d9fff0", "open-tundra-vast-polar-sky", ("aurora-curtains", "star-twinkle", "snow-dust"), "aurora-curtains-expand-over-the-tundra", "Une plaine polaire presque vide laisse tout l'écran au ciel et à de grands rideaux d'aurore, sans vallée ni lac."),
    Scene("nuit", "Nuit", "#9cb9f1", "#27354f", "midnight_rooftop", "#030710", "#10192a", "#080a0d", "#e8edff", "quiet-rooftop-city-moon-stars", ("window-flicker", "star-twinkle", "distant-haze"), "city-lights-thin-as-night-deepens", "Un toit silencieux domine une ville assoupie sous la lune, avec quelques fenêtres encore allumées et un ciel profond."),
)

BY_KEY = {scene.key: scene for scene in SCENES}
CHOICES = [(scene.key, scene.label) for scene in SCENES]
DEFAULT = "arbre_etoiles"
LEGACY_REPLACED = {"concentration": "arbre_etoiles"}


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
