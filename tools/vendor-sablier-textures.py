"""Prépare les matières CC0 Poly Haven pour le service local (pas d'API en production).

Une couleur unie posée sur un cube reste un cube coloré, quelle que soit la qualité de la
lumière qui l'éclaire : c'est l'autre moitié de ce qui donne aux univers leur air dessiné.
Chaque matière est donc servie en trois cartes, et non plus en une seule teinte :

* ``-diff``   la couleur mesurée du matériau ;
* ``-normal`` son relief, qui accroche la lumière rasante ;
* ``-arm``    occlusion, rugosité et métallicité empaquetées dans les trois composantes
  d'une même image — la convention glTF, que Three lit telle quelle. C'est elle qui fait
  la différence entre une pierre et un plastique gris : sans variation de rugosité, toute
  surface renvoie le ciel de la même façon sur toute son étendue.

Usage : .venv/Scripts/python.exe tools/vendor-sablier-textures.py [matière ...]
"""

import json
import sys
from hashlib import md5, sha256
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'src/static/sablier/materials'

# Les matières que les compositions savent nommer. La clé est le mot employé dans le code
# des lieux ; la valeur, la ressource Poly Haven qui le rend.
ASSETS = {
    'rock': 'rock_face_03',
    'soil': 'forest_floor',
    'bark': 'bark_brown_02',
    'wood': 'wood_table_worn',
    'stone': 'large_sandstone_blocks_01',
    'sand': 'sandy_gravel_02',
    'snow': 'snow_02',
    'marble': 'marble_01',
    'paving': 'cobblestone_floor_04',
    'concrete': 'concrete_floor_worn_001',
    'grass': 'aerial_grass_rock',
    'metal': 'metal_plate',
}

CHANNELS = [('diff', 'Diffuse', 90), ('normal', 'nor_gl', 95), ('arm', 'arm', 92)]


def get(url):
    with urlopen(Request(url, headers={'User-Agent': 'MyENT-local-art-review/1.0'}), timeout=120) as response:
        return response.read()


def main(argv):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    wanted = set(argv)
    manifest_path = OUTPUT / 'provenance.json'
    manifest = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    fresh = []
    rebuilt = set()

    for kind, asset in ASSETS.items():
        if wanted and asset not in wanted and kind not in wanted:
            continue
        files = json.loads(get('https://api.polyhaven.com/files/' + asset))
        info = json.loads(get('https://api.polyhaven.com/info/' + asset))
        for channel, field, quality in CHANNELS:
            if field not in files:
                print(f'{asset} : canal {field} absent, ignoré')
                continue
            source = files[field]['1k']['jpg']
            raw = get(source['url'])
            if md5(raw).hexdigest() != source['md5']:
                raise ValueError('Empreinte de téléchargement incorrecte : ' + asset)
            image = Image.open(BytesIO(raw)).convert('RGB')
            image.thumbnail((1024, 1024))
            path = OUTPUT / f'{asset}-{channel}.webp'
            image.save(path, 'WEBP', quality=quality, method=6)
            rebuilt.add(asset)
            fresh.append({'kind': kind, 'asset': asset, 'channel': channel, 'file': path.name,
                         'source': 'https://polyhaven.com/a/' + asset, 'download': source['url'],
                         'authors': info.get('authors', {}), 'license': 'CC0-1.0',
                         'license_url': 'https://polyhaven.com/license', 'source_md5': source['md5'],
                         'sha256': sha256(path.read_bytes()).hexdigest(), 'dimensions': image.size,
                         'bytes': path.stat().st_size,
                         'processing': '1024 px maximum, WebP RGB, normale OpenGL, ARM empaqueté'})
            print(f'{path.name:44} {path.stat().st_size // 1024:5d} Kio', flush=True)
    # Les cartes non reconstruites gardent leur provenance : relancer le script pour une
    # seule matière ne doit pas effacer la traçabilité des autres.
    keep = [entry for entry in manifest
            if entry['asset'] in ASSETS.values() and entry['asset'] not in rebuilt] + fresh
    manifest_path.write_text(json.dumps(keep, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(keep)} cartes, {sum(entry["bytes"] for entry in keep) // 1024 // 1024} Mio.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
