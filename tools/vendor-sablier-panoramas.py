"""Prépare les ciels photographiques du Sablier à partir des panoramas CC0 de Poly Haven.

Un ciel calculé — un dégradé du zénith vers l'horizon, un disque pour l'astre — reste un
dégradé : il n'a ni couche nuageuse, ni bande de pollution lumineuse, ni la dissymétrie
que l'atmosphère réelle impose toujours. C'est ce qui donne aux univers leur air de dessin.
Une capture panoramique porte au contraire une lumière mesurée, et cette lumière sert ici
deux fois : comme fond visible et comme source d'éclairage de toutes les matières.

Le script produit, pour chaque panorama retenu :

* ``<nom>-sky.webp`` — le fond visible, en 4096 × 2048. L'image est encodée en sRGB après
  division par un facteur d'échelle inscrit au manifeste ; le moteur le réapplique par
  ``backgroundIntensity``. On garde ainsi une image légère sans perdre les rapports de
  luminance : seul l'astre lui-même est écrêté, exactement comme sur une photographie.
* ``<nom>-light.hdr`` — la carte d'éclairage, en 512 × 256, en flottants RGBE. C'est elle
  qui porte la dynamique complète : sans elle, le verre et le chrome perdent leurs reflets.
* ``panoramas.json`` — l'échelle, la direction et la couleur mesurées de l'astre, et la
  provenance complète de chaque fichier.

Usage : .venv/Scripts/python.exe tools/vendor-sablier-panoramas.py [nom ...]
"""

from __future__ import annotations

import json
import math
import sys
from hashlib import md5, sha256
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src/static/sablier/panoramas"

# Résolution du fond visible et de la carte d'éclairage. Le champ de la caméra couvre
# environ un sixième du tour d'horizon : 4096 pixels y laissent près de sept cents pixels
# de large, ce que le léger voile atmosphérique de chaque lieu suffit à rendre net.
SKY_SIZE = (4096, 2048)
LIGHT_SIZE = (512, 256)

# Le blanc de référence du fond. Au-delà, l'image écrête — c'est le disque solaire et son
# halo immédiat, que le tonemapping écraserait de toute façon.
WHITE_PERCENTILE = 99.85

# ── Le choix des lieux ───────────────────────────────────────────────────────────────
# Chaque univers reçoit un ciel réel de même heure, de même météo et de même hauteur
# d'astre que sa composition. Les panoramas « puresky » ne portent que le ciel : le sol
# capturé en a été retiré, il ne peut donc pas contredire le relief que la scène construit
# elle-même. Les deux univers absents de cette table gardent leur ciel calculé : l'abysse
# n'a pas d'horizon, et l'âtre est un intérieur que sa propre flamme éclaire.
PANORAMAS = {
    "star_tree": "moonless_golf",
    "eternity_fountain": "kloppenheim_02_puresky",
    "eden": "qwantani_mid_morning_puresky",
    "time_river": "qwantani_moonrise_puresky",
    "memories": "belfast_sunset_puresky",
    "interstellar": "rogland_clear_night",
    "galaxy": "satara_night_no_lamps",
    "heaven": "kloppenheim_06_puresky",
    "oasis": "syferfontein_0d_clear_puresky",
    "rain_refuge": "kloppenheim_07_puresky",
    "aurora_valley": "qwantani_night_puresky",
    "spring_meadow": "qwantani_morning_puresky",
    "summer_terrace": "kloofendal_48d_partly_cloudy_puresky",
    "autumn_lake": "evening_road_01_puresky",
    "winter_lodge": "snow_field_2_puresky",
    "rain_city": "neuer_zollhof",
    "ocean_cliffs": "table_mountain_2_puresky",
    "sahara_observatory": "mpumalanga_veld_puresky",
    "ancient_forest": "kloofendal_misty_morning_puresky",
    "storm_cliffs": "kloppenheim_01_puresky",
    "polar_sky": "qwantani_moon_noon_puresky",
    "midnight_rooftop": "rooftop_night",
}


def get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "MyENT-local-art-review/1.0"})
    with urlopen(request, timeout=300) as response:
        return response.read()


# ── Radiance RGBE ────────────────────────────────────────────────────────────────────
# Le format tient en quelques lignes : un en-tête textuel, une ligne de résolution, puis
# des lignes de balayage compressées composante par composante. Three est le lecteur du
# navigateur ; ici il faut savoir lire *et* réécrire, la carte d'éclairage étant produite
# par réduction de la capture d'origine.


def read_hdr(raw: bytes) -> np.ndarray:
    if not raw.startswith(b"#?"):
        raise ValueError("En-tête Radiance absent.")
    cursor = raw.index(b"\n") + 1
    while True:
        end = raw.index(b"\n", cursor)
        line = raw[cursor:end]
        cursor = end + 1
        if not line.strip():
            break
    end = raw.index(b"\n", cursor)
    axis = raw[cursor:end].split()
    cursor = end + 1
    if axis[0] != b"-Y" or axis[2] != b"+X":
        raise ValueError(f"Orientation non prise en charge : {axis!r}")
    height, width = int(axis[1]), int(axis[3])

    data = np.frombuffer(raw, dtype=np.uint8, offset=cursor)
    rgbe = np.empty((height, width, 4), dtype=np.uint8)
    offset = 0
    for y in range(height):
        head = data[offset:offset + 4]
        if not (head[0] == 2 and head[1] == 2 and (int(head[2]) << 8 | int(head[3])) == width):
            # Lignes brutes : quatre octets par pixel, sans compression.
            rgbe[y] = data[offset:offset + width * 4].reshape(width, 4)
            offset += width * 4
            continue
        offset += 4
        for channel in range(4):
            x = 0
            while x < width:
                count = int(data[offset])
                offset += 1
                if count > 128:
                    run = count - 128
                    rgbe[y, x:x + run, channel] = data[offset]
                    offset += 1
                    x += run
                else:
                    rgbe[y, x:x + count, channel] = data[offset:offset + count]
                    offset += count
                    x += count
    exponent = rgbe[..., 3].astype(np.int32)
    scale = np.where(exponent == 0, 0.0, np.ldexp(1.0, exponent - 136))
    return rgbe[..., :3].astype(np.float32) * scale[..., None].astype(np.float32)


def write_hdr(path: Path, image: np.ndarray) -> None:
    height, width, _ = image.shape
    peak = np.max(image, axis=2)
    mantissa, exponent = np.frexp(np.maximum(peak, 0.0))
    lit = peak > 1e-32
    factor = np.where(lit, mantissa * 256.0 / np.where(lit, peak, 1.0), 0.0)
    rgbe = np.zeros((height, width, 4), dtype=np.uint8)
    rgbe[..., :3] = np.clip(image * factor[..., None], 0, 255).astype(np.uint8)
    rgbe[..., 3] = np.where(lit, np.clip(exponent + 128, 0, 255), 0).astype(np.uint8)
    header = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y %d +X %d\n" % (height, width)
    path.write_bytes(header + rgbe.tobytes())


# ── Mesures ──────────────────────────────────────────────────────────────────────────


def resize(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Moyenne de blocs en lumière linéaire : la seule réduction qui conserve l'énergie."""
    width, height = size
    source_height, source_width, _ = image.shape
    if source_width % width or source_height % height:
        raise ValueError("La capture doit être un multiple exact de la taille demandée.")
    block = (height, source_height // height, width, source_width // width, 3)
    return image.reshape(block).mean(axis=(1, 3))


def luminance(image: np.ndarray) -> np.ndarray:
    return image @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def directions(height: int, width: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Direction cartésienne de chaque pixel, dans la convention équirectangulaire de Three."""
    theta = (np.arange(height, dtype=np.float64) + 0.5) / height * math.pi
    phi = ((np.arange(width, dtype=np.float64) + 0.5) / width - 0.5) * 2 * math.pi
    y = np.repeat(np.cos(theta)[:, None], width, axis=1)
    radius = np.sin(theta)[:, None]
    return radius * np.cos(phi)[None, :], y, radius * np.sin(phi)[None, :]


def measure_sun(image: np.ndarray) -> dict:
    """Direction, couleur et part d'énergie de la source dominante.

    Le fond photographique n'a de sens que si l'ombre portée par la scène tombe du même
    côté que la lumière visible dans le ciel. On relit donc l'astre dans la capture au
    lieu de le déclarer à la main.
    """
    small = resize(image, (1024, 512))
    lit = luminance(small)
    x, y, z = directions(*lit.shape)
    sky = y > -0.02
    peak = float(lit[sky].max())
    mask = sky & (lit >= peak * 0.5)
    solid = np.sin((np.arange(lit.shape[0]) + 0.5) / lit.shape[0] * math.pi)[:, None]
    weight = lit * mask * solid
    total = float(weight.sum()) or 1.0
    direction = np.array([float((weight * axis).sum()) / total for axis in (x, y, z)])
    norm = float(np.linalg.norm(direction)) or 1.0
    direction /= norm
    color = np.array([float((small[..., c] * mask).sum()) for c in range(3)])
    color = color / (color.max() or 1.0)
    return {
        "direction": [round(float(v), 5) for v in direction],
        "elevation": round(math.degrees(math.asin(max(-1.0, min(1.0, float(direction[1]))))), 2),
        "azimuth": round(math.degrees(math.atan2(float(direction[0]), float(direction[2]))) % 360, 2),
        "color": "#%02x%02x%02x" % tuple(int(round(255 * v ** (1 / 2.2))) for v in color),
        "share": round(float((lit * mask).sum() / (lit.sum() or 1.0)), 4),
    }


def encode_sky(image: np.ndarray, white: float) -> Image.Image:
    normalised = np.clip(image / white, 0.0, 1.0)
    srgb = np.where(normalised <= 0.0031308, normalised * 12.92,
                    1.055 * np.power(normalised, 1 / 2.4) - 0.055)
    # Un ciel n'est fait que de dégradés lents : arrondir au plus proche des 256 niveaux
    # y dessine des bandes concentriques bien visibles. Un bruit triangulaire d'un demi
    # niveau, ajouté avant l'arrondi, rend la transition continue pour un coût nul.
    noise = np.random.default_rng(7).triangular(-1.0, 0.0, 1.0, srgb.shape)
    return Image.fromarray(np.clip(srgb * 255 + 0.5 + noise * 0.5, 0, 255).astype(np.uint8), "RGB")


# ── Fabrication ──────────────────────────────────────────────────────────────────────


def build(slug: str, universes: list[str]) -> dict:
    files = json.loads(get("https://api.polyhaven.com/files/" + slug))
    info = json.loads(get("https://api.polyhaven.com/info/" + slug))
    source = files["hdri"]["4k"]["hdr"]
    raw = get(source["url"])
    if md5(raw).hexdigest() != source["md5"]:
        raise ValueError("Empreinte de téléchargement incorrecte : " + slug)
    image = read_hdr(raw)
    if image.shape[:2] != (SKY_SIZE[1], SKY_SIZE[0]):
        raise ValueError(f"Capture de taille inattendue pour {slug} : {image.shape}")

    lit = luminance(image)
    white = max(float(np.percentile(lit, WHITE_PERCENTILE)), 1e-4)
    sky = lit[:lit.shape[0] // 2]
    solid = np.sin((np.arange(sky.shape[0]) + 0.5) / lit.shape[0] * math.pi)[:, None]
    average = max(float((sky * solid).sum() / solid.sum() / sky.shape[1]), 1e-6)
    sky_path = OUTPUT / f"{slug}-sky.webp"
    encode_sky(image, white).save(sky_path, "WEBP", quality=86, method=6)

    light_path = OUTPUT / f"{slug}-light.hdr"
    write_hdr(light_path, resize(image, LIGHT_SIZE))

    record = {
        "panorama": slug,
        "universes": universes,
        "sky": sky_path.name,
        "light": light_path.name,
        # Le fond est encodé divisé par ce blanc : le moteur le rétablit en intensité.
        "white": round(white, 6),
        # Luminance moyenne de la voûte, pondérée par l'angle solide. C'est la mesure qui
        # permet au moteur de choisir seul son temps de pose : une nuit sans lune et un
        # plein midi diffèrent ici d'un facteur mille, et aucune exposition unique ne peut
        # convenir aux deux. Le réglage cesse ainsi d'être un chiffre écrit à la main.
        "average": round(average, 6),
        "sun": measure_sun(image),
        "source": "https://polyhaven.com/a/" + slug,
        "download": source["url"],
        "authors": info.get("authors", {}),
        "license": "CC0-1.0",
        "license_url": "https://polyhaven.com/license",
        "source_md5": source["md5"],
        "sky_sha256": sha256(sky_path.read_bytes()).hexdigest(),
        "light_sha256": sha256(light_path.read_bytes()).hexdigest(),
        "bytes": [sky_path.stat().st_size, light_path.stat().st_size],
        "processing": "fond 4096×2048 WebP sRGB divisé par le blanc, éclairage 512×256 RGBE",
    }
    print(f"{slug:38} blanc {white:9.4f} moyenne {average:8.4f}  astre {record['sun']['elevation']:6.1f}° "
          f"{record['sun']['azimuth']:6.1f}°  {sky_path.stat().st_size // 1024:5d} Kio + "
          f"{light_path.stat().st_size // 1024:4d} Kio", flush=True)
    return record


def main(argv: list[str]) -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    wanted = set(argv)
    by_slug: dict[str, list[str]] = {}
    for universe, slug in PANORAMAS.items():
        by_slug.setdefault(slug, []).append(universe)

    manifest_path = OUTPUT / "panoramas.json"
    manifest = {}
    if manifest_path.exists():
        manifest = {entry["panorama"]: entry for entry in json.loads(manifest_path.read_text("utf-8"))}
    for slug, universes in by_slug.items():
        if wanted and slug not in wanted and not wanted & set(universes):
            continue
        manifest[slug] = build(slug, universes)
    ordered = [manifest[slug] for slug in by_slug if slug in manifest]
    manifest_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(ordered)} panoramas, {sum(sum(e['bytes']) for e in ordered) // 1024 // 1024} Mio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
