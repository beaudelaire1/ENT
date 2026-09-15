"""Planche de contrôle du placement des objets dans les univers du Sablier.

Pour chaque univers, applique les règles de `src/static/sablier/placement.js` (exécutées
par Node, pour juger le vrai code) à la description du lieu dans `scenes_catalog.json`,
sur un écran d'ordinateur et un téléphone, puis pose les silhouettes sur l'image :

* le sablier, là où les règles le posent ;
* la lune, là où elles placent un astre ;
* les lignes de support relevées (cyan), les zones d'interface (rouge).

C'est cette planche qu'on relit avant de brancher un relevé : un support mal placé s'y
voit d'un coup d'œil, alors qu'aucun test ne le détecte.

Dépendances de préparation : Node, Pillow.
Usage : .venv/Scripts/python.exe tools/sablier-placement-sheet.py sortie/
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/static/sablier"
CATALOG = ROOT / "src/sablier/scenes_catalog.json"
VIEWS = {"ordinateur": (1280, 800), "téléphone": (390, 844)}
# Zones d'interface de l'immersion, mesurées dans le navigateur (temps, bouton de pause et
# disque de musique relevés à 1024 × 768 et 375 × 812, rapportés à ces vues) : bande du
# statut en haut, temps et pause en bas au centre, disque en bas à droite. Une marge de
# douze pixels les entoure — un objet collé au temps se lirait comme un défaut.
UI = {
    "ordinateur": [[0, 0, 1280, 64], [520, 620, 760, 790], [945, 735, 1270, 795]],
    "téléphone": [[0, 0, 390, 64], [111, 686, 280, 834], [275, 775, 385, 842]],
}
TILE_HEIGHT = 360

RESOLVE = r"""
const placement = require(process.argv[1]);
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = [];
for (const job of input) {
  const view = {w: job.view[0], h: job.view[1]};
  const fr = job.photo ? placement.frame({imageAspect: 16 / 9, view, focus: job.place.focus}) : {ox: 0, oy: 0, sx: 1, sy: 1};
  const ui = job.ui.map(([l, t, r, b]) => ({l, t, r, b}));
  out.push({...job, frame: fr,
    hourglass: placement.resolve({place: job.place, mode: 'hourglass', frame: fr, view, ui}),
    moon: placement.resolve({place: job.place, mode: 'moon', frame: fr, view, ui})});
}
process.stdout.write(JSON.stringify(out));
"""


def asset(prefix: str) -> Image.Image:
    path = next((STATIC / "img").glob(f"{prefix}*"))
    return Image.open(path).convert("RGBA")


def main() -> None:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / ".dist/sablier-placement")
    output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    jobs = []
    for scene in catalog:
        if not scene.get("place"):
            continue
        photo = (STATIC / "photos" / f"{scene['decor']}.webp").is_file()
        for name, size in VIEWS.items():
            jobs.append({"decor": scene["decor"], "label": scene["label"], "view": size, "device": name,
                         "place": scene["place"], "photo": photo, "ui": UI[name]})
    result = subprocess.run(["node", "-e", RESOLVE, str(STATIC / "placement.js")], input=json.dumps(jobs),
                            capture_output=True, text=True, encoding="utf-8", check=True)
    placed = json.loads(result.stdout)

    hourglass, moon = asset("7073fefb"), asset("1b9b150c")
    tiles = {}
    for job in placed:
        w, h = job["view"]
        fr = job["frame"]
        if job["photo"]:
            with Image.open(STATIC / "photos" / f"{job['decor']}.webp") as source:
                iw, ih = source.size
                crop = source.convert("RGB").crop((round(fr["ox"] * iw), round(fr["oy"] * ih),
                                                   round((fr["ox"] + fr["sx"]) * iw), round((fr["oy"] + fr["sy"]) * ih)))
        else:
            with Image.open(STATIC / "thumbnails" / f"{job['decor']}-wide.webp") as source:
                crop = source.convert("RGB")
        canvas = crop.resize((w, h), Image.LANCZOS).convert("RGBA")
        draw = ImageDraw.Draw(canvas, "RGBA")
        for l, t, r, b in job["ui"]:
            draw.rectangle((l, t, r, b), fill=(255, 40, 40, 60))
        for support in job["place"]["supports"]:
            (u0, v0), (u1, v1) = support["line"]
            to = lambda u, v: ((u - fr["ox"]) / fr["sx"] * w, (v - fr["oy"]) / fr["sy"] * h)
            draw.line([to(u0, v0), to(u1, v1)], fill=(0, 230, 255, 220), width=3)
        spot = job["hourglass"]
        side = spot["box"]["size"]
        ih_ = 0.86 * side
        iw_ = ih_ * hourglass.width / hourglass.height * 1.16
        sprite = hourglass.resize((max(1, round(iw_)), max(1, round(ih_))))
        canvas.alpha_composite(sprite, (round(spot["box"]["left"] + side / 2 - iw_ / 2), round(spot["box"]["top"] + 0.04 * side)))
        draw.ellipse((spot["anchor"]["x"] - 5, spot["anchor"]["y"] - 5, spot["anchor"]["x"] + 5, spot["anchor"]["y"] + 5), fill=(255, 210, 0, 255))
        sky = job["moon"]
        d = 0.74 * sky["box"]["size"]
        canvas.alpha_composite(moon.resize((max(1, round(d)), max(1, round(d)))),
                               (round(sky["anchor"]["x"] - d / 2), round(sky["anchor"]["y"] - d / 2)))
        caption = f"{job['label']} · {job['device']} · sablier : {spot['reason']} · lune : {sky['reason']}"
        draw.rectangle((0, h - 34, w, h), fill=(0, 0, 0, 170))
        draw.text((8, h - 26), caption, fill=(255, 255, 255, 255))
        scale = TILE_HEIGHT / h
        tiles.setdefault(job["decor"], []).append(canvas.convert("RGB").resize((round(w * scale), TILE_HEIGHT), Image.LANCZOS))

    rows = list(tiles.values())
    per_sheet = 8
    for index in range(0, len(rows), per_sheet):
        chunk = rows[index:index + per_sheet]
        width = max(sum(tile.width for tile in row) + 10 * (len(row) - 1) for row in chunk)
        sheet = Image.new("RGB", (width, len(chunk) * (TILE_HEIGHT + 10)), "#111111")
        for y, row in enumerate(chunk):
            x = 0
            for tile in row:
                sheet.paste(tile, (x, y * (TILE_HEIGHT + 10)))
                x += tile.width + 10
        path = output / f"placement-{index // per_sheet + 1}.jpg"
        sheet.save(path, quality=84)
        print(path)
    (output / "placement.json").write_text(json.dumps(placed, ensure_ascii=False, indent=1), encoding="utf-8")
    # Résumé lisible : sur la planche réduite, les légendes ne se lisent plus.
    summary = {}
    for job in placed:
        spot = job["hourglass"]
        summary.setdefault(job["decor"], {})[job["device"]] = (
            f"{spot['role']}/{spot['reason']} h={round(spot['objectHeight'])} "
            f"pied=({round(spot['anchor']['x'])},{round(spot['anchor']['y'])}) lune={job['moon']['reason']}"
        )
    for decor, devices in summary.items():
        print(f"{decor:20} | " + " | ".join(f"{name}: {text}" for name, text in devices.items()))


if __name__ == "__main__":
    main()
