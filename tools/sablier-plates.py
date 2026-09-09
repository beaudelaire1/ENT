"""Encode les vues fixes des univers à partir des rendus de ``sablier-plates.cjs``.

Trois tailles par univers, parce que trois usages : la vignette de la galerie, qui se
charge vingt-quatre fois d'affilée ; la vue de repli en paysage ; la même en portrait.
Une seule taille aurait forcé à choisir entre une galerie lourde et un repli flou.

Dépendance de préparation uniquement : Pillow. Aucun appel réseau.
"""

import json
from hashlib import sha256
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".dist/sablier-plates"
OUTPUT = ROOT / "src/static/sablier/thumbnails"
# La vue de repli est agrandie par ``object-fit: cover`` : elle n'a pas à être native,
# elle a à rester lisible. La vignette, elle, est affichée à 150 px de large.
SIZES = {"": ("desktop", (320, 200), 76), "-wide": ("desktop", (1280, 800), 78), "-mobile": ("mobile", (720, 1571), 78)}


def render(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Recadre au centre selon le rapport demandé, puis réduit — jamais d'agrandissement."""
    width, height = size
    ratio = width / height
    crop_width = min(source.width, round(source.height * ratio))
    crop_height = min(source.height, round(source.width / ratio))
    left, top = (source.width - crop_width) // 2, (source.height - crop_height) // 2
    cropped = source.crop((left, top, left + crop_width, top + crop_height))
    return cropped.resize(size, Image.LANCZOS) if cropped.size != size else cropped


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = json.loads((SOURCE / "report.json").read_text(encoding="utf-8"))
    worlds = sorted({entry["world"] for entry in report})
    manifest = []
    for world in worlds:
        for suffix, (device, size, quality) in SIZES.items():
            plate = SOURCE / f"{device}-{world}.png"
            with Image.open(plate) as source:
                native = list(source.size)
                image = render(source.convert("RGB"), size)
            path = OUTPUT / f"{world}{suffix}.webp"
            image.save(path, "WEBP", quality=quality, method=6)
            manifest.append(
                {
                    "world": world,
                    "file": path.name,
                    "dimensions": list(size),
                    "source": f"rendu local du moteur premium3d ({device})",
                    "source_dimensions": native,
                    "quality": quality,
                    "sha256": sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                }
            )
            print(path.name, path.stat().st_size, flush=True)
    (OUTPUT / "provenance.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
