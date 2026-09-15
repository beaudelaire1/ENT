"""Import map des modules de la scène immersive.

`decor.js` importe `premium3d.js` avec l'empreinte `?v=`, mais `premium3d.js` importe
ses modules par des chemins relatifs, et la résolution relative abandonne la chaîne de
requête : `./premium3d/worlds.js` redevient une adresse nue, que le navigateur garde en
cache — soixante secondes derrière WhiteNoise pour les copies non hachées, une durée
heuristique sous `runserver`, qui n'envoie aucun `Cache-Control`. Le 15 septembre 2026,
un `worlds.js` neuf a ainsi rencontré un `photo-world.js` ancien : l'import de
`particles` a échoué et seule la vue fixe s'est affichée.

Réécrire les imports dans chaque fichier ne tiendrait pas : un import statique n'accepte
pas d'expression. L'import map, elle, s'applique à l'adresse *résolue* : chaque module du
dossier, quel que soit le fichier qui l'importe, est redirigé vers l'adresse que
`{% static %}` produit — empreintée par le manifeste en production — suivie de la même
version que le reste du Sablier. Tout le graphe change donc d'adresse en même temps.

La politique de sécurité n'autorise aucun script inline : la map y est admise par son
empreinte sha256, calculée ici sur le texte exact que le gabarit écrit.
"""

from __future__ import annotations

import base64
import hashlib
import json

from django.conf import settings
from django.templatetags.static import static

PREMIUM_FOLDER = "sablier/premium3d"


def premium_modules() -> list[str]:
    """Les modules du dossier, en noms de fichiers statiques, dans un ordre stable."""
    folder = settings.BASE_DIR / "static" / PREMIUM_FOLDER
    return sorted(f"{PREMIUM_FOLDER}/{path.relative_to(folder).as_posix()}" for path in folder.rglob("*.js"))


def premium_import_map(version: str) -> str:
    """Le texte JSON de l'import map, prêt à être écrit tel quel dans la page."""
    # La clé est l'adresse nue, celle que la résolution relative produit ; la valeur est
    # l'adresse réellement servie. Sans manifeste les deux ne diffèrent que par `?v=`.
    imports = {f"{settings.STATIC_URL}{name}": f"{static(name)}?v={version}" for name in premium_modules()}
    text = json.dumps({"imports": imports}, sort_keys=True, separators=(",", ":"))
    # Comme `json_script` : un `</script>` dans une adresse fermerait l'élément.
    return text.replace("<", "\\u003C").replace(">", "\\u003E").replace("&", "\\u0026")


def script_hash(text: str) -> str:
    """La source CSP qui autorise ce script inline précis, et aucun autre."""
    digest = base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")
    return f"'sha256-{digest}'"
