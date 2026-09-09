"""Prépare quatre matériaux CC0 Poly Haven pour le service local (pas d'API en production)."""
import json
from hashlib import md5, sha256
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'src/static/sablier/materials'
OUTPUT.mkdir(parents=True, exist_ok=True)

def get(url):
    with urlopen(Request(url, headers={'User-Agent': 'MyENT-local-art-review/1.0'}), timeout=60) as response:
        return response.read()

manifest = []
for asset in ['forest_floor', 'wood_table_worn', 'rock_face_03', 'bark_brown_02']:
    files = json.loads(get('https://api.polyhaven.com/files/' + asset))
    info = json.loads(get('https://api.polyhaven.com/info/' + asset))
    for channel, field in [('diff', 'Diffuse'), ('normal', 'nor_gl')]:
        source = files[field]['1k']['jpg']
        raw = get(source['url'])
        if md5(raw).hexdigest() != source['md5']:
            raise ValueError('Empreinte de téléchargement incorrecte : ' + asset)
        image = Image.open(BytesIO(raw)).convert('RGB')
        image.thumbnail((1024, 1024))
        path = OUTPUT / f'{asset}-{channel}.webp'
        image.save(path, 'WEBP', quality=90 if channel == 'diff' else 95, method=6)
        manifest.append({'asset': asset, 'channel': channel, 'file': path.name,
                         'source': 'https://polyhaven.com/a/' + asset, 'download': source['url'],
                         'authors': info.get('authors', {}), 'license': 'CC0-1.0',
                         'license_url': 'https://polyhaven.com/license', 'source_md5': source['md5'],
                         'sha256': sha256(path.read_bytes()).hexdigest(), 'dimensions': image.size,
                         'bytes': path.stat().st_size, 'processing': '1024 px maximum, WebP RGB, normale OpenGL'})
        print(path.name, path.stat().st_size)
(OUTPUT / 'provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
