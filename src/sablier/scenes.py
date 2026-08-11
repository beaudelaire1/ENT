"""Les ambiances de Sablier, décrites une seule fois.

Une ambiance porte sa palette et son décor animé, définis ensemble pour ne pas
dériver l'un de l'autre — une couleur ajoutée sans décor, un décor sans couleur.

Les ambiances n'ont pas de fond sonore : la playlist personnelle le couvrirait de
toute façon. Seul le carillon de fin subsiste, indépendant de l'ambiance.

Ce module ne dépend de rien : il est importé par les modèles et les gabarits.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.utils.safestring import mark_safe


@dataclass(frozen=True)
class Scene:
    key: str
    label: str
    accent: str  # sable, anneau, accents de l'interface
    tint: str  # teinte du fond de scène
    decor: str  # effet animé, interprété par le navigateur


SCENES: tuple[Scene, ...] = (
    Scene("concentration", "Concentration", "#8878ff", "#5b4bd6", "motes"),
    Scene("printemps", "Printemps", "#ff8fb1", "#b8467a", "petals"),
    Scene("ete", "Été", "#ffc93d", "#d98a10", "fireflies"),
    Scene("automne", "Automne", "#ff8a3d", "#a34b12", "leaves"),
    Scene("hiver", "Hiver", "#8fd4ff", "#2f6f9e", "snow"),
    Scene("pluie", "Pluie", "#6fa8dc", "#24506e", "rain"),
    Scene("ocean", "Océan", "#3fb9c9", "#1f7d8c", "waves"),
    Scene("sahara", "Sahara", "#f0a860", "#8a4b1c", "sand"),
    Scene("foret", "Forêt", "#6fcf8a", "#1f6b3f", "spores"),
    Scene("orage", "Orage", "#9aa8d8", "#1b2440", "storm"),
    Scene("braises", "Braises", "#ff7043", "#8c2f12", "embers"),
    Scene("aurore", "Aurore", "#5fe0c0", "#1c4f6b", "aurora"),
    Scene("nuit", "Nuit", "#6f7ee0", "#2b3577", "stars"),
)

BY_KEY = {scene.key: scene for scene in SCENES}
CHOICES = [(scene.key, scene.label) for scene in SCENES]
DEFAULT = SCENES[0].key

# Les ambiances abstraites d'origine deviennent les décors qui leur ressemblent le plus.
REPLACED = {"calm": "ocean", "energy": "ete", "night": "nuit"}


def palette_css() -> str:
    """Règles de palette, une par ambiance.

    Volontairement peu spécifiques (0-1-0) : `.focus-app[data-warning]` et
    `[data-finished]` (0-2-0) doivent continuer à l'emporter, pour que l'alerte
    finale et la fin du décompte se voient quelle que soit l'ambiance.

    Le résultat est marqué sûr : sans cela Django échappe les guillemets des
    sélecteurs, la feuille devient invalide et plus aucune ambiance ne s'applique.
    Aucune donnée utilisateur n'entre ici — tout vient du registre ci-dessus.
    """
    return mark_safe(  # noqa: S308 — contenu entièrement statique, défini dans ce module
        "".join(
            f'[data-ambience="{scene.key}"]{{'
            f"--focus-accent:var(--focus-user-accent,{scene.accent});"
            f"--focus-tint:{scene.tint};}}"
            for scene in SCENES
        )
    )
