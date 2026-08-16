// Éclairage d'ambiance du Sablier.
//
// C'est le module qui décide de quoi un objet a l'air. Un sablier éclairé par deux
// lampes fixes est une maquette ; le même sablier éclairé par le ciel qui l'entoure —
// bleu au zénith, chaud à l'horizon, avec la dune ou la canopée qui renvoie sa couleur —
// devient un objet posé quelque part. Chaque univers produit donc sa propre carte
// d'environnement, utilisée à la fois comme fond visible et comme source de lumière.
//
// Deux chemins : un ciel à diffusion atmosphérique pour les mondes de plein jour, une
// carte équirectangulaire calculée pour les nuits, les crépuscules et les intérieurs.
import { Sky } from "../../vendor/three-addons/objects/Sky.js";

const DEGREES = Math.PI / 180;

function color(THREE, hex) {
  return new THREE.Color(hex).convertSRGBToLinear();
}

// Direction cartésienne d'un couple (élévation, azimut) exprimé en degrés.
export function sunDirection(THREE, elevation, azimuth) {
  const phi = (90 - elevation) * DEGREES;
  const theta = azimuth * DEGREES;
  return new THREE.Vector3().setFromSphericalCoords(1, phi, theta);
}

// ── Ciel diffusant ───────────────────────────────────────────────────────────────
// Modèle de Preetham fourni par Three.js : la couleur du ciel découle de la position du
// soleil et de la turbidité de l'air, pas d'un dégradé choisi à la main. C'est ce qui
// donne l'or rasant du Sahara et le bleu franc d'un après-midi d'été.

function buildSky(THREE, config) {
  const sky = new Sky();
  // Le dôme doit tenir dans le champ de la caméra de la scène. À l'échelle d'exemple
  // de Three.js (45 000), il tombe au-delà du plan lointain et disparaît : le ciel
  // devient noir et tout l'univers de plein jour avec lui. Il reste donc largement
  // au-delà du relief — neuf cents unités de côté — mais en deçà du plan lointain.
  sky.scale.setScalar(2400);
  const uniforms = sky.material.uniforms;
  uniforms.turbidity.value = config.turbidity ?? 6;
  uniforms.rayleigh.value = config.rayleigh ?? 2;
  uniforms.mieCoefficient.value = config.mie ?? 0.006;
  uniforms.mieDirectionalG.value = config.mieG ?? 0.8;
  uniforms.sunPosition.value.copy(sunDirection(THREE, config.elevation, config.azimuth));
  return sky;
}

// ── Carte calculée ───────────────────────────────────────────────────────────────
// Écrite en demi-flottants : la lumière du soleil ou de la Lune y dépasse largement 1,
// ce qu'un canvas 8 bits ne sait pas représenter. Sans cette dynamique, les reflets
// spéculaires du verre et du chrome s'écrasent et la scène redevient plate.

// Valeurs de repli pour les univers de plein jour, qui décrivent leur ciel par ses
// paramètres atmosphériques plutôt que par des couleurs. Une recette peut redéfinir
// chaque teinte : le sous-bois renvoie du vert, la dune de l'ocre, la neige du bleu.
const DAYLIGHT = {
  zenith: "#4d7fbe",
  horizon: "#d6e4ee",
  ground: "#6d6455",
  intensity: 9,
  size: 2.4,
  haze: 0.45,
};

function buildEquirect(THREE, config, width = 512) {
  const height = width / 2;
  const data = new Uint16Array(width * height * 4);
  const zenith = color(THREE, config.zenith);
  const horizon = color(THREE, config.horizon);
  const ground = color(THREE, config.ground);
  const glowColor = color(THREE, config.glow ?? config.horizon);
  const light = color(THREE, config.light ?? "#ffffff");
  const direction = sunDirection(THREE, config.elevation ?? 12, config.azimuth ?? 160);
  const intensity = config.intensity ?? 8;
  const angularSize = Math.cos((config.size ?? 2.2) * DEGREES);
  const haze = config.haze ?? 0.35;
  const half = THREE.DataUtils.toHalfFloat;

  for (let y = 0; y < height; y += 1) {
    const theta = (y + 0.5) / height * Math.PI;
    const sinTheta = Math.sin(theta), cosTheta = Math.cos(theta);
    for (let x = 0; x < width; x += 1) {
      const phi = (x + 0.5) / width * Math.PI * 2;
      const dx = sinTheta * Math.cos(phi), dy = cosTheta, dz = sinTheta * Math.sin(phi);
      let r, g, b;
      if (dy >= 0) {
        // Le ciel se réchauffe en approchant de l'horizon : la lumière y traverse plus
        // d'atmosphère. Un simple dégradé linéaire donne un fond de papier peint.
        const t = Math.pow(1 - dy, 2.6);
        r = zenith.r + (horizon.r - zenith.r) * t;
        g = zenith.g + (horizon.g - zenith.g) * t;
        b = zenith.b + (horizon.b - zenith.b) * t;
      } else {
        // Sous l'horizon, le sol renvoie sa propre couleur vers l'objet : c'est ce
        // rebond qui pose le sablier sur du sable plutôt que dans le vide.
        const t = Math.pow(1 + dy, 0.8);
        r = horizon.r + (ground.r - horizon.r) * t;
        g = horizon.g + (ground.g - horizon.g) * t;
        b = horizon.b + (ground.b - horizon.b) * t;
      }
      const facing = dx * direction.x + dy * direction.y + dz * direction.z;
      if (facing > 0) {
        // Halo autour de l'astre, puis le disque lui-même, bien plus lumineux.
        const bloom = Math.pow(facing, 42) * haze;
        r += glowColor.r * bloom * intensity * 0.14;
        g += glowColor.g * bloom * intensity * 0.14;
        b += glowColor.b * bloom * intensity * 0.14;
        if (facing >= angularSize) {
          r += light.r * intensity;
          g += light.g * intensity;
          b += light.b * intensity;
        }
      }
      const index = (y * width + x) * 4;
      data[index] = half(r);
      data[index + 1] = half(g);
      data[index + 2] = half(b);
      data[index + 3] = half(1);
    }
  }

  const map = new THREE.DataTexture(data, width, height, THREE.RGBAFormat, THREE.HalfFloatType);
  map.mapping = THREE.EquirectangularReflectionMapping;
  map.magFilter = THREE.LinearFilter;
  map.minFilter = THREE.LinearFilter;
  map.generateMipmaps = false;
  map.needsUpdate = true;
  return map;
}

// Construit l'éclairage d'un univers. Rend `{ environment, background, sun, dispose }` :
// `environment` sert d'IBL aux matières, `background` de fond visible, `sun` donne la
// direction et la couleur de la lumière directe à installer dans la scène.
//
// L'éclairage vient toujours de la carte calculée, jamais du ciel diffusant. Celui-ci
// n'est borné par rien : au zénith d'un jour d'été il dépasse la portée des demi-flottants
// et la convolution du PMREM en tire des NaN. La carte d'environnement devenait alors
// invalide et *toutes* les matières PBR de la scène tombaient au noir — un ciel radieux
// au-dessus d'un paysage entièrement éteint. Le ciel diffusant reste donc ce qu'il fait
// le mieux : un fond visible.
export function buildEnvironment(THREE, renderer, config) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();
  const disposals = [];

  const lighting = config.kind === "day" ? { ...DAYLIGHT, ...config } : config;
  const equirect = buildEquirect(THREE, lighting);
  const target = pmrem.fromEquirectangular(equirect);
  const environment = target.texture;
  disposals.push(() => {
    target.dispose();
    equirect.dispose();
  });

  let background;
  if (config.kind === "day") {
    background = buildSky(THREE, config);
    disposals.push(() => {
      background.geometry.dispose();
      background.material.dispose();
    });
  } else {
    background = equirect;
  }

  pmrem.dispose();

  const direction = sunDirection(THREE, config.elevation ?? 12, config.azimuth ?? 160);
  return {
    environment,
    background,
    sun: {
      direction,
      color: config.light ?? "#ffffff",
      intensity: config.directIntensity ?? (config.kind === "day" ? 3.4 : 1.1),
    },
    dispose() {
      for (const disposal of disposals) disposal();
    },
  };
}
