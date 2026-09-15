"""Prépare les univers photographiques du Sablier : la photographie du lieu et ses vues fixes.

Un lieu bâti dans le code — cylindres, plans de feuillage peints, rochers à facettes —
reste un dessin, quel que soit l'éclairage posé dessus. Un univers photographique
remplace ce lieu par une vraie photographie ; le moteur n'y ajoute que du mouvement
(``premium3d/photo-world.js``).

Pour chaque univers de ``PHOTOS``, le script :

* télécharge l'original dans ``.dist/photos`` s'il manque, et refuse tout fichier dont
  l'empreinte diffère de celle inscrite ici — une image remplacée en amont n'entre pas
  sans relecture ;
* écrit ``photos/<univers>.webp``, la photographie servie à la scène ;
* réécrit les trois vues fixes de l'univers (vignette, repli paysage, repli portrait) à
  partir de la même image : la galerie et le poste sans WebGL montrent le même lieu ;
* consigne la provenance de chaque fichier.

``sablier-plates.py`` réécrit toutes les vues fixes à partir des rendus du moteur : le
relancer ensuite, pour rétablir celles des univers photographiques.

Dépendance de préparation uniquement : Pillow.
Usage : .venv/Scripts/python.exe tools/sablier-photo-worlds.py
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".dist/photos"
STATIC = ROOT / "src/static/sablier"
PHOTOS_DIR = STATIC / "photos"
THUMBNAILS = STATIC / "thumbnails"

# Largeur servie à la scène. En 1920, un écran large agrandissait déjà la photo et la
# rendait molle ; au-delà de 2560, le poids croît sans gain visible sur un portable.
PHOTO_WIDTH = 2560
PHOTO_QUALITY = 84

# Mêmes tailles et qualités que ``sablier-plates.py`` : la galerie et le repli ne
# distinguent pas une vue photographiée d'une vue rendue.
VIEWS = {"": ((320, 200), 76), "-wide": ((1280, 800), 78), "-mobile": ((720, 1571), 78)}

PHOTOS = {
    "ancient_forest": {
        "title": "Sun's rays in a dense forest",
        "author": "Filip Varga",
        "page": "https://commons.wikimedia.org/wiki/File:Sun%27s_rays_in_a_dense_forest_(Unsplash).jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/db/Sun%27s_rays_in_a_dense_forest_%28Unsplash%29.jpg",
        "sha256": "6b656e04f6cb3a499f0b0f2e38ca100a7b1216ce2be6934789d69d234a32af74",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        # Point gardé au centre quand le cadre rogne l'image (x, y depuis le haut) : le
        # jeune sapin et la colonne de lumière. Le même que ``focus`` dans ``worlds.js``.
        "focus": (0.5, 0.58),
    },
}


def original(world: str, entry: dict) -> Path:
    path = CACHE / f"{world}.jpg"
    if not path.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        request = Request(entry["url"], headers={"User-Agent": "MyENT-Sablier/1.0 (outil de préparation)"})
        with urlopen(request, timeout=60) as response:
            path.write_bytes(response.read())
    digest = sha256(path.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        raise SystemExit(f"{world} : empreinte inattendue ({digest}) — relire l'original avant de l'employer.")
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
    return cropped.resize(size, Image.LANCZOS) if cropped.size != size else cropped


def encode(image: Image.Image, path: Path, quality: int) -> dict:
    image.save(path, "WEBP", quality=quality, method=6)
    print(path.name, path.stat().st_size, flush=True)
    return {"quality": quality, "sha256": sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


def main() -> None:
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    photos = []
    views = {}
    for world, entry in PHOTOS.items():
        with Image.open(original(world, entry)) as opened:
            source = opened.convert("RGB")
        credit = {
            "source": entry["page"],
            "author": entry["author"],
            "license": entry["license"],
            "license_url": entry["license_url"],
        }
        size = (PHOTO_WIDTH, round(PHOTO_WIDTH * source.height / source.width))
        photos.append(
            {
                "world": world,
                "file": f"{world}.webp",
                "dimensions": list(size),
                "title": entry["title"],
                **credit,
                "original": {"url": entry["url"], "sha256": entry["sha256"], "dimensions": [source.width, source.height]},
                **encode(source.resize(size, Image.LANCZOS), PHOTOS_DIR / f"{world}.webp", PHOTO_QUALITY),
            }
        )
        for suffix, (view_size, quality) in VIEWS.items():
            name = f"{world}{suffix}.webp"
            views[name] = {
                "world": world,
                "file": name,
                "dimensions": list(view_size),
                **credit,
                "source_dimensions": [source.width, source.height],
                **encode(crop(source, view_size, entry["focus"]), THUMBNAILS / name, quality),
            }
    (PHOTOS_DIR / "provenance.json").write_text(json.dumps(photos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Les vues fixes des autres univers restent celles du moteur : seules les entrées
    # réécrites ici changent, à leur place.
    manifest_path = THUMBNAILS / "provenance.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = [views.pop(item["file"], item) for item in manifest] + list(views.values())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
