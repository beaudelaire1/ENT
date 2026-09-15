// Ciels photographiques du Sablier.
//
// Un dégradé calculé ne trompe personne : le ciel réel n'est jamais lisse. Il porte une
// couche nuageuse qui se creuse vers l'horizon, un halo dissymétrique autour de l'astre,
// une bande d'aérosols plus chaude que le zénith, et — la nuit — la lueur d'une ville
// posée quelque part derrière la crête. C'est cette texture-là qui manque aux univers
// quand ils ont l'air dessinés.
//
// Chaque lieu reçoit donc une capture panoramique réelle, préparée hors ligne par
// `tools/vendor-sablier-panoramas.py`, et servie en deux fichiers qui ne font pas le même
// métier : une image 4096 × 2048 pour ce que l'œil voit, une carte 512 × 256 en flottants
// pour ce que les matières reçoivent. Séparer les deux est ce qui rend l'ensemble léger :
// le fond a besoin de définition et pas de dynamique, l'éclairage exactement l'inverse.
//
// Trois mesures accompagnent chaque capture et remplacent autant de réglages écrits à la
// main : la direction réelle de l'astre — l'ombre portée tombe alors du même côté que la
// lumière visible dans le ciel —, la luminance moyenne de la voûte, qui donne le temps de
// pose, et la couleur de la bande d'horizon, qui donne celle de la brume.
import { RGBELoader } from "../../vendor/three-addons/loaders/RGBELoader.js";

const BASE = new URL("../panoramas/", import.meta.url);

// Cible du gris moyen après exposition. Chaque univers est ramené à ce niveau à partir de
// la luminance mesurée de son ciel : c'est ce qui permet de changer un panorama sans
// rouvrir la recette. L'exposant garde aux nuits leur obscurité — une normalisation
// exacte rendrait le clair de lune aussi lumineux qu'un plein midi.
const GREY = 0.5;
const CONTRAST = 0.82;

let catalogue = null;

function manifest() {
  if (!catalogue) {
    catalogue = fetch(new URL("panoramas.json", BASE).href)
      .then(response => (response.ok ? response.json() : Promise.reject(new Error(String(response.status)))))
      .then(list => new Map(list.map(entry => [entry.panorama, entry])))
      .catch(error => {
        console.warn("Sablier : catalogue des ciels indisponible", error);
        return new Map();
      });
  }
  return catalogue;
}

// Le compteur que la page expose déjà pour les matières : tant qu'il n'est pas retombé à
// zéro, la scène n'est pas complète. Les captures de contrôle s'y fient pour ne pas
// photographier un univers dont le ciel n'est pas encore arrivé.
function pending(delta) {
  const app = document.querySelector("#focus-app");
  if (app) app.dataset.materialLoads = String(Math.max(0, Number(app.dataset.materialLoads || 0) + delta));
}

function radians(degrees) {
  return (degrees * Math.PI) / 180;
}

// Couleur de la bande d'horizon, lue dans la carte d'éclairage. La brume d'un lieu n'a pas
// de raison d'avoir une autre couleur que le ciel qu'elle dilue : mesurée ici, elle suit
// le panorama au lieu d'être redite dans chaque recette.
function horizonColour(THREE, texture) {
  const { data, width, height } = texture.image;
  const band = Math.max(1, Math.round(height * 0.03));
  const middle = Math.round(height / 2);
  const sum = [0, 0, 0];
  let count = 0;
  for (let y = middle - band; y < middle + band; y += 1) {
    if (y < 0 || y >= height) continue;
    for (let x = 0; x < width; x += 1) {
      const index = (y * width + x) * 4;
      sum[0] += data[index];
      sum[1] += data[index + 1];
      sum[2] += data[index + 2];
      count += 1;
    }
  }
  if (!count) return null;
  return new THREE.Color().setRGB(sum[0] / count, sum[1] / count, sum[2] / count, THREE.LinearSRGBColorSpace);
}

/**
 * Charge le ciel d'un univers. Rend `null` si la recette n'en demande pas, ou si le
 * fichier manque : l'appelant garde alors son ciel calculé, qui reste une image valable.
 *
 * L'objet rendu suit le contrat de `buildEnvironment`, augmenté de la rotation à appliquer
 * au fond et à l'éclairage, de l'intensité qui rétablit l'échelle photométrique du fond,
 * du temps de pose mesuré et de la couleur de brume.
 */
export async function loadPanorama(THREE, renderer, config) {
  if (!config?.panorama) return null;
  const entry = (await manifest()).get(config.panorama);
  if (!entry) return null;

  pending(1);
  try {
    const [sky, light] = await Promise.all([
      new THREE.TextureLoader().loadAsync(new URL(entry.sky, BASE).href),
      new RGBELoader().setDataType(THREE.FloatType).loadAsync(new URL(entry.light, BASE).href),
    ]);

    sky.mapping = THREE.EquirectangularReflectionMapping;
    sky.colorSpace = THREE.SRGBColorSpace;
    sky.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    sky.minFilter = THREE.LinearMipmapLinearFilter;
    sky.magFilter = THREE.LinearFilter;
    sky.generateMipmaps = true;
    sky.needsUpdate = true;

    light.mapping = THREE.EquirectangularReflectionMapping;
    const horizon = horizonColour(THREE, light);

    const pmrem = new THREE.PMREMGenerator(renderer);
    pmrem.compileEquirectangularShader();
    const target = pmrem.fromEquirectangular(light);
    pmrem.dispose();
    light.dispose();

    // L'astre est replacé là où la composition l'attend : la scène a été bâtie autour
    // d'une direction d'éclairage, et c'est le ciel qui tourne, pas le relief. La
    // rotation s'applique au fond et à l'environnement d'un seul geste, si bien que le
    // reflet dans le verre reste celui du ciel que l'on voit.
    const spin = config.spin ?? (config.azimuth ?? entry.sun.azimuth) - entry.sun.azimuth;
    const rotation = new THREE.Euler(0, radians(spin), 0);
    const direction = new THREE.Vector3(...entry.sun.direction).applyEuler(rotation).normalize();

    return {
      panorama: entry.panorama,
      environment: target.texture,
      background: sky,
      rotation,
      // Le fond a été encodé divisé par son blanc de référence : on le rétablit ici, ce
      // qui remet le ciel et l'éclairage sur la même échelle photométrique.
      backgroundIntensity: entry.white,
      exposure: config.photoExposure ?? GREY / Math.max(entry.average, 1e-5) ** CONTRAST,
      horizon,
      sun: {
        direction,
        // La couleur mesurée dans la capture prime sur celle de la recette : une
        // lumière directe plus froide ou plus chaude que le ciel qui la produit se
        // voit immédiatement sur une matière claire.
        color: config.sunColor ?? entry.sun.color,
        intensity: config.directIntensity ?? (entry.sun.elevation > 0 ? 3 : 1),
      },
      dispose() {
        target.dispose();
        sky.dispose();
      },
    };
  } catch (error) {
    console.warn("Sablier : ciel photographique indisponible", config.panorama, error);
    return null;
  } finally {
    pending(-1);
  }
}
