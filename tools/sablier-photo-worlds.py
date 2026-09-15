"""Prépare les univers photographiques du Sablier : l'image du lieu et ses vues fixes.

Un lieu bâti dans le code — cylindres, plans de feuillage peints, rochers à facettes —
reste un dessin, quel que soit l'éclairage posé dessus. Un univers photographique
remplace ce lieu par une image : une photographie libre ou une image générée. Le moteur
n'y ajoute que du mouvement (``premium3d/photo-world.js``).

Les originaux sont décrits dans ``sablier-photo-sources.json`` (fichier, empreinte,
auteur ou outil, licence) et rangés dans ``.dist/photos``, hors du dépôt. Pour chaque
univers, le script :

* télécharge l'original s'il manque et qu'il a une adresse (photographie libre) ; une
  image générée doit déjà être dans ``.dist/photos`` ;
* refuse tout original dont l'empreinte diffère de celle consignée — une image remplacée
  n'entre pas sans relecture ;
* écrit ``photos/<univers>.webp``, l'image servie à la scène ;
* réécrit les trois vues fixes de l'univers (vignette, repli paysage, repli portrait) à
  partir de la même image : la galerie et le poste sans WebGL montrent le même lieu ;
* consigne la provenance de chaque fichier.

Le point gardé au centre quand un cadre rogne l'image (``focus``) est lu dans
``premium3d/worlds.js`` : la scène et les vues fixes cadrent au même endroit.

Aucune image n'est jamais agrandie : une vue plus grande que la zone disponible dans
l'original est produite à la taille de cette zone.

``sablier-plates.py`` réécrit toutes les vues fixes à partir des rendus du moteur : le
relancer ensuite, pour rétablir celles des univers photographiques.

Dépendance de préparation uniquement : Pillow.
Usage : .venv/Scripts/python.exe tools/sablier-photo-worlds.py [--repin] [univers ...]
"""

from __future__ import annotations

import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCES = Path(__file__).with_name("sablier-photo-sources.json")
CACHE = ROOT / ".dist/photos"
STATIC = ROOT / "src/static/sablier"
RECIPES = STATIC / "premium3d/worlds.js"
PHOTOS_DIR = STATIC / "photos"
THUMBNAILS = STATIC / "thumbnails"

# Largeur maximale servie à la scène. En 1920, un écran large agrandissait déjà la photo et
# la rendait molle ; au-delà de 2560, le poids croît sans gain visible sur un portable.
PHOTO_WIDTH = 2560
PHOTO_QUALITY = 86

# Mêmes tailles et qualités que ``sablier-plates.py`` : la galerie et le repli ne
# distinguent pas une vue photographiée d'une vue rendue.
VIEWS = {"": ((320, 200), 76), "-wide": ((1280, 800), 78), "-mobile": ((720, 1571), 78)}

# Champs de provenance recopiés tels quels de la source vers les manifestes.
CREDIT = ("kind", "title", "author", "source", "generator", "generated_on", "prompt", "license", "license_url")


def focuses() -> dict[str, tuple[float, float]]:
    """Le point focal de chaque univers photographique, lu dans sa recette."""
    recipes = RECIPES.read_text(encoding="utf-8")
    found = re.findall(r'photo: \{src: "([a-z_]+)\.webp", focus: \[([\d.]+), ([\d.]+)\]', recipes)
    return {world: (float(x), float(y)) for world, x, y in found}


def original(entry: dict, *, repin: bool = False) -> Path:
    """L'original vérifié. ``repin`` consigne l'empreinte d'une image générée remplacée.

    Réservé aux images locales, et seulement une fois la nouvelle version regardée : une
    photographie téléchargée garde toujours son empreinte d'origine.
    """
    path = CACHE / entry["file"]
    if not path.is_file():
        if not entry.get("url"):
            raise SystemExit(f"{entry['file']} : original absent de .dist/photos.")
        CACHE.mkdir(parents=True, exist_ok=True)
        request = Request(entry["url"], headers={"User-Agent": "MyENT-Sablier/1.0 (outil de préparation)"})
        with urlopen(request, timeout=60) as response:
            path.write_bytes(response.read())
    digest = sha256(path.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        if not repin or entry.get("url"):
            raise SystemExit(f"{entry['file']} : empreinte inattendue ({digest}) — relire l'original avant de l'employer.")
        print(f"{entry['file']} : nouvelle empreinte consignée ({entry['sha256'][:12]} -> {digest[:12]})", flush=True)
        entry["sha256"] = digest
    return path


def crop(source: Image.Image, size: tuple[int, int], focus: tuple[float, float]) -> Image.Image:
    """Recadre autour du point focal selon le rapport demandé, puis réduit — jamais d'agrandissement."""
    width, height = size
    ratio = width / height
    crop_width = min(source.width, round(source.height * ratio))
    crop_height = min(source.height, round(source.width / ratio))
    left = min(max(0, round(source.width * focus[0] - crop_width / 2)), source.width - crop_width)
    top = min(max(0, round(source.height * focus[1] - crop_height / 2)), source.height - crop_height)
    cropped = source.crop((left, top, left + crop_width, top + crop_height))
    scale = min(1, crop_width / width)
    target = (round(width * scale), round(height * scale))
    return cropped.resize(target, Image.LANCZOS) if cropped.size != target else cropped


def encode(image: Image.Image, path: Path, quality: int) -> dict:
    image.save(path, "WEBP", quality=quality, method=6)
    print(path.name, image.size, path.stat().st_size, flush=True)
    return {
        "dimensions": list(image.size),
        "quality": quality,
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }


def main() -> None:
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    points = focuses()
    missing = sorted(set(points) - set(sources))
    if missing:
        raise SystemExit(f"Univers photographiques sans source : {', '.join(missing)}")
    repin = "--repin" in sys.argv[1:]
    selected = [name for name in sys.argv[1:] if name != "--repin"] or sorted(points)

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    photo_manifest_path = PHOTOS_DIR / "provenance.json"
    photos = {
        item["file"]: item
        for item in (json.loads(photo_manifest_path.read_text(encoding="utf-8")) if photo_manifest_path.is_file() else [])
    }
    views = {}
    for world in selected:
        entry = sources[world]
        with Image.open(original(entry, repin=repin)) as opened:
            source = opened.convert("RGB")
        credit = {key: entry[key] for key in CREDIT if entry.get(key)}
        size = (min(PHOTO_WIDTH, source.width), round(min(PHOTO_WIDTH, source.width) * source.height / source.width))
        served = source if size == source.size else source.resize(size, Image.LANCZOS)
        name = f"{world}.webp"
        photos[name] = {
            "world": world,
            "file": name,
            **credit,
            "original": {"file": entry["file"], "url": entry.get("url"), "sha256": entry["sha256"], "dimensions": list(source.size)},
            **encode(served, PHOTOS_DIR / name, PHOTO_QUALITY),
        }
        for suffix, (view_size, quality) in VIEWS.items():
            view = f"{world}{suffix}.webp"
            views[view] = {
                "world": world,
                "file": view,
                **credit,
                "source_dimensions": list(source.size),
                **encode(crop(source, view_size, points[world]), THUMBNAILS / view, quality),
            }
    if repin:
        SOURCES.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ordered = [photos[name] for name in sorted(photos)]
    photo_manifest_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Les vues fixes des autres univers restent celles du moteur : seules les entrées
    # réécrites ici changent, à leur place.
    manifest_path = THUMBNAILS / "provenance.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = [views.pop(item["file"], item) for item in manifest] + list(views.values())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
