// Matières scannées, servies par MyENT. Textures Poly Haven CC0 ; voir materials/provenance.json.
// Cache limité à la composition : aucun téléchargement externe pendant une session.
//
// Trois cartes par matière, et c'est la troisième qui compte le plus. La couleur situe le
// matériau, le relief accroche la lumière rasante, mais c'est la rugosité qui décide si
// une surface est de la pierre ou du plastique : une valeur constante fait renvoyer le
// ciel de la même façon partout, et rien ne trahit davantage une image de synthèse. La
// carte ARM porte, dans ses trois composantes, l'occlusion, la rugosité et la métallicité
// mesurées sur le matériau réel — la convention glTF, que Three lit sans conversion.
const ASSETS = {
  wood: 'wood_table_worn',
  bark: 'bark_brown_02',
  rock: 'rock_face_03',
  soil: 'forest_floor',
  stone: 'large_sandstone_blocks_01',
  sand: 'sandy_gravel_02',
  snow: 'snow_02',
  marble: 'marble_01',
  paving: 'cobblestone_floor_04',
  concrete: 'concrete_floor_worn_001',
  grass: 'aerial_grass_rock',
  metal: 'metal_plate',
};

// Une carte, plusieurs emplois : l'ARM alimente d'un coup l'occlusion, la rugosité et la
// métallicité. Les facteurs scalaires passent alors à 1, faute de quoi ils multiplieraient
// la mesure et l'écraseraient.
const CHANNELS = [
  ['diff', ['map']],
  ['normal', ['normalMap']],
  ['arm', ['aoMap', 'roughnessMap', 'metalnessMap']],
];

export function materialLibrary(T) {
  const cache = new Map(), loader = new T.TextureLoader(), app = document.querySelector('#focus-app');
  const pending = delta => { if (app) app.dataset.materialLoads = String(Math.max(0, Number(app.dataset.materialLoads || 0) + delta)); };
  const changed = () => { if (app) app.dataset.materialRevision = String(Number(app.dataset.materialRevision || 0) + 1); };
  const attach = (material, properties, texture) => {
    for (const property of properties) material[property] = texture;
    if (properties.includes('roughnessMap')) { material.roughness = 1; material.metalness = 1; }
    material.needsUpdate = true;
  };
  return function apply(material, kind, repeat = [2, 2]) {
    const asset = ASSETS[kind]; if (!asset) return material;
    for (const [channel, properties] of CHANNELS) {
      const key = asset + channel + repeat.join(',');
      let record = cache.get(key);
      if (!record) {
        record = { consumers: new Set(), loaded: false, texture: null }; cache.set(key, record); pending(1);
        loader.load(new URL(`../materials/${asset}-${channel}.webp`, import.meta.url).href, texture => {
          texture.wrapS = texture.wrapT = T.RepeatWrapping; texture.repeat.set(...repeat); texture.anisotropy = 8;
          if (channel === 'diff') texture.colorSpace = T.SRGBColorSpace;
          record.texture = texture; record.loaded = true;
          for (const consumer of record.consumers) attach(consumer, properties, texture);
          if (!record.consumers.size) texture.dispose(); pending(-1); changed();
        }, undefined, () => { pending(-1); changed(); console.warn('Sablier : matière indisponible', asset, channel); });
      }
      record.consumers.add(material);
      if (record.loaded) attach(material, properties, record.texture);
      material.addEventListener('dispose', () => { record.consumers.delete(material); if (!record.consumers.size) record.texture?.dispose(); });
    }
    return material;
  };
}
