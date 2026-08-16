// Cartes de matière du Sablier.
//
// Chaque matière reçoit ici son relief, sa rugosité et sa couleur. Une matière PBR sans
// carte est lisse partout : le verre devient du plastique, le sable une pâte orange, le
// métal un miroir de synthèse. Les cartes sont calculées une seule fois puis mises en
// cache — elles ne dépendent ni de l'univers ni de la durée de la session.
import { fbm, ridged, worley, surface, heightField, normalMap, grayscale } from "./noise.js";

const cache = new Map();

function once(key, build) {
  if (!cache.has(key)) cache.set(key, build());
  return cache.get(key);
}

function texture(THREE, canvas, { repeat = 1, srgb = false, anisotropy = 8 } = {}) {
  const map = new THREE.CanvasTexture(canvas);
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.repeat.set(repeat, repeat);
  map.anisotropy = anisotropy;
  if (srgb) map.colorSpace = THREE.SRGBColorSpace;
  map.needsUpdate = true;
  return map;
}

const clamp01 = (value) => Math.max(0, Math.min(1, value));

// ── Sable ────────────────────────────────────────────────────────────────────────
// Deux échelles : le grain individuel, et les ondulations laissées par l'écoulement.

function sandField(size) {
  return heightField(size, (u, v) => {
    // Le grain domine, mais un bruit cellulaire seul dessine des cloisons — un sol de
    // vase craquelée plutôt qu'un sable. On l'adoucit sous un bruit fractal plus fin.
    const grain = 1 - worley(u * size * 0.5, v * size * 0.5, 0.95);
    const fine = fbm(u * 46, v * 46, 4) * 0.5 + 0.5;
    const ripple = fbm(u * 9, v * 9, 4) * 0.5 + 0.5;
    return clamp01(grain * 0.34 + fine * 0.46 + ripple * 0.2);
  });
}

export function sandMaps(THREE) {
  return once("sand", () => {
    const size = 256;
    const field = sandField(size);
    const albedo = surface(size, (data) => {
      for (let i = 0; i < size * size; i += 1) {
        // Le sable n'a pas une couleur mais une population de couleurs : quelques grains
        // sombres et quelques grains blancs suffisent à casser l'aplat.
        const value = field[i];
        const warm = 0.55 + value * 0.45;
        data[i * 4] = 226 * warm + 22;
        data[i * 4 + 1] = 176 * warm + 16;
        data[i * 4 + 2] = 112 * warm + 8;
        data[i * 4 + 3] = 255;
      }
    });
    return {
      map: texture(THREE, albedo, { repeat: 3, srgb: true }),
      normalMap: texture(THREE, normalMap(field, size, 3.1), { repeat: 3 }),
      roughnessMap: texture(THREE, grayscale(field, size, 0.62, 0.94), { repeat: 3 }),
    };
  });
}

// ── Verre ────────────────────────────────────────────────────────────────────────
// Un verre parfaitement propre n'existe pas. Poussière, traces de doigts et micro-ondes
// de soufflage donnent au reflet ses ruptures — sans elles, la transmission paraît vide.

export function glassMaps(THREE) {
  return once("glass", () => {
    const size = 256;
    const field = heightField(size, (u, v) => {
      const blown = fbm(u * 3.4, v * 1.6, 3) * 0.5 + 0.5;
      const dust = Math.pow(clamp01(fbm(u * 26, v * 26, 3) * 0.5 + 0.5), 6);
      const smudge = Math.pow(clamp01(fbm(u * 7 + 40, v * 7, 2) * 0.5 + 0.5), 3);
      return clamp01(blown * 0.35 + dust * 0.45 + smudge * 0.3);
    });
    return {
      normalMap: texture(THREE, normalMap(field, size, 0.42), { repeat: 1 }),
      roughnessMap: texture(THREE, grayscale(field, size, 0.01, 0.16), { repeat: 1 }),
    };
  });
}

// ── Métal brossé ─────────────────────────────────────────────────────────────────
// Le brossage est anisotrope : des rayures très allongées dans un sens. C'est ce qui
// fait la différence entre du chrome tourné et une bille de mercure.

export function metalMaps(THREE) {
  return once("metal", () => {
    const size = 256;
    const field = heightField(size, (u, v) => {
      const brushed = fbm(u * 220, v * 2.2, 3) * 0.5 + 0.5;
      const scratches = Math.pow(clamp01(fbm(u * 60 + 11, v * 6, 2) * 0.5 + 0.5), 8);
      return clamp01(brushed * 0.78 + scratches * 0.22);
    });
    return {
      normalMap: texture(THREE, normalMap(field, size, 0.55), { repeat: 2 }),
      roughnessMap: texture(THREE, grayscale(field, size, 0.08, 0.34), { repeat: 2 }),
    };
  });
}

// ── Cire ─────────────────────────────────────────────────────────────────────────

export function waxMaps(THREE) {
  return once("wax", () => {
    const size = 256;
    const field = heightField(size, (u, v) => {
      const pour = fbm(u * 3.1, v * 12, 4) * 0.5 + 0.5;      // stries verticales de coulée
      const bloom = fbm(u * 16, v * 16, 3) * 0.5 + 0.5;      // fleur blanche de la paraffine
      return clamp01(pour * 0.68 + bloom * 0.32);
    });
    return {
      normalMap: texture(THREE, normalMap(field, size, 1.15), { repeat: 1 }),
      roughnessMap: texture(THREE, grayscale(field, size, 0.28, 0.62), { repeat: 1 }),
    };
  });
}

// ── Nacre ────────────────────────────────────────────────────────────────────────
// Les couches de nacre sont concentriques ; c'est leur interférence qui produit les
// reflets colorés d'une perle.

export function pearlMaps(THREE) {
  return once("pearl", () => {
    const size = 256;
    const field = heightField(size, (u, v) => {
      const dx = u - 0.5, dy = v - 0.5;
      const rings = Math.sin(Math.hypot(dx, dy) * 190 + fbm(u * 5, v * 5, 3) * 6) * 0.5 + 0.5;
      const grain = fbm(u * 40, v * 40, 2) * 0.5 + 0.5;
      return clamp01(rings * 0.6 + grain * 0.4);
    });
    return {
      normalMap: texture(THREE, normalMap(field, size, 0.34), { repeat: 1 }),
      roughnessMap: texture(THREE, grayscale(field, size, 0.05, 0.22), { repeat: 1 }),
    };
  });
}

// ── Régolithe lunaire ────────────────────────────────────────────────────────────
// Mers sombres, hautes terres claires, cratères. Sans cette carte, la Lune est une bille.

export function lunarMaps(THREE) {
  return once("lunar", () => {
    const size = 512;
    const field = heightField(size, (u, v) => {
      const craters = worley(u * 13, v * 13, 1) * 0.55 + worley(u * 34 + 7, v * 34, 1) * 0.3;
      const rough = fbm(u * 60, v * 60, 4) * 0.5 + 0.5;
      return clamp01(craters * 0.7 + rough * 0.3);
    });
    const maria = heightField(size, (u, v) => clamp01(fbm(u * 2.6 + 19, v * 2.6, 4) * 0.5 + 0.5));
    const albedo = surface(size, (data) => {
      for (let i = 0; i < size * size; i += 1) {
        const sea = Math.pow(maria[i], 2.4);            // les mers occupent peu de surface
        const base = 214 - sea * 96;
        const detail = (field[i] - 0.5) * 34;
        data[i * 4] = clamp01((base + detail) / 255) * 255;
        data[i * 4 + 1] = clamp01((base - 4 + detail) / 255) * 255;
        data[i * 4 + 2] = clamp01((base - 14 + detail) / 255) * 255;
        data[i * 4 + 3] = 255;
      }
    });
    return {
      map: texture(THREE, albedo, { repeat: 1, srgb: true }),
      normalMap: texture(THREE, normalMap(field, size, 2.9), { repeat: 1 }),
    };
  });
}

// ── Roche et écorce ──────────────────────────────────────────────────────────────

export function rockMaps(THREE) {
  return once("rock", () => {
    const size = 256;
    const field = heightField(size, (u, v) => {
      const strata = ridged(u * 4, v * 9, 5) * 0.6;
      const chips = (1 - worley(u * 18, v * 18, 1)) * 0.4;
      return clamp01(strata + chips);
    });
    return {
      normalMap: texture(THREE, normalMap(field, size, 2.2), { repeat: 4 }),
      roughnessMap: texture(THREE, grayscale(field, size, 0.68, 0.98), { repeat: 4 }),
    };
  });
}

export function barkMaps(THREE) {
  return once("bark", () => {
    const size = 256;
    const field = heightField(size, (u, v) => {
      const fibre = ridged(u * 22, v * 2.4, 4);
      const knots = (1 - worley(u * 6, v * 3, 1)) * 0.3;
      return clamp01(fibre * 0.75 + knots);
    });
    return {
      normalMap: texture(THREE, normalMap(field, size, 2.6), { repeat: 3 }),
      roughnessMap: texture(THREE, grayscale(field, size, 0.7, 0.99), { repeat: 3 }),
    };
  });
}

// ── Eau ──────────────────────────────────────────────────────────────────────────
// Deux trains de vagues croisés : la carte défile en boucle, ce qui suffit à animer une
// surface d'eau sans simulation.

export function waterNormal(THREE) {
  return once("water", () => {
    const size = 256;
    const field = heightField(size, (u, v) => {
      const swell = Math.sin(u * Math.PI * 4 + fbm(u * 3, v * 3, 3) * 3) * 0.5 + 0.5;
      const cross = Math.sin(v * Math.PI * 6 + fbm(u * 5 + 9, v * 5, 3) * 4) * 0.5 + 0.5;
      return clamp01(swell * 0.55 + cross * 0.45);
    });
    return texture(THREE, normalMap(field, size, 1.5), { repeat: 6 });
  });
}

// ── Sprites ──────────────────────────────────────────────────────────────────────
// Points lumineux et particules : un dégradé radial dessiné au canvas 2D, plus lisible
// qu'un carré et bien moins coûteux qu'une géométrie.

export function radialSprite(THREE, stops, size = 128) {
  const key = `sprite:${size}:${stops.map(stop => stop.join("@")).join("|")}`;
  return once(key, () => {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = size;
    const context = canvas.getContext("2d");
    const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    for (const [color, offset] of stops) gradient.addColorStop(offset, color);
    context.fillStyle = gradient;
    context.fillRect(0, 0, size, size);
    const map = new THREE.CanvasTexture(canvas);
    map.colorSpace = THREE.SRGBColorSpace;
    map.needsUpdate = true;
    return map;
  });
}

// Flamme : un cœur bleuté, un manteau jaune, une pointe orange qui s'éteint.
export function flameSprite(THREE) {
  return once("flame", () => {
    const width = 128, height = 256;
    const canvas = document.createElement("canvas");
    canvas.width = width; canvas.height = height;
    const context = canvas.getContext("2d");
    const halo = context.createRadialGradient(64, 156, 4, 64, 156, 78);
    halo.addColorStop(0, "rgba(255,246,196,1)");
    halo.addColorStop(0.26, "rgba(255,181,58,.9)");
    halo.addColorStop(0.66, "rgba(255,92,14,.3)");
    halo.addColorStop(1, "rgba(255,60,0,0)");
    context.fillStyle = halo;
    context.beginPath();
    context.ellipse(64, 156, 50, 100, 0, 0, Math.PI * 2);
    context.fill();
    const core = context.createLinearGradient(0, 62, 0, 214);
    core.addColorStop(0, "rgba(255,255,238,0)");
    core.addColorStop(0.3, "rgba(255,252,214,.95)");
    core.addColorStop(0.68, "rgba(255,176,60,.95)");
    core.addColorStop(0.9, "rgba(120,150,255,.5)");
    core.addColorStop(1, "rgba(60,105,255,.12)");
    context.fillStyle = core;
    context.beginPath();
    context.moveTo(64, 46);
    context.bezierCurveTo(102, 100, 90, 180, 64, 220);
    context.bezierCurveTo(38, 180, 26, 100, 64, 46);
    context.fill();
    const map = new THREE.CanvasTexture(canvas);
    map.colorSpace = THREE.SRGBColorSpace;
    map.needsUpdate = true;
    return map;
  });
}

// Silhouette de feuillage : un amas de disques irréguliers, découpé en alpha. Un arbre
// dessiné avec des sphères pleines se voit immédiatement ; découpé, il reste crédible
// même en avant-plan.
export function foliageSprite(THREE, color, seed = 3) {
  return once(`foliage:${color}:${seed}`, () => {
    const size = 128;
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = size;
    const context = canvas.getContext("2d");
    context.clearRect(0, 0, size, size);
    let random = seed * 9781;
    const next = () => {
      random = (random * 1103515245 + 12345) & 0x7fffffff;
      return (random % 1000) / 1000;
    };
    for (let i = 0; i < 260; i += 1) {
      const angle = next() * Math.PI * 2;
      const radius = Math.pow(next(), 0.55) * size * 0.46;
      const x = size / 2 + Math.cos(angle) * radius;
      const y = size / 2 + Math.sin(angle) * radius * 0.82;
      const leaf = size * (0.016 + next() * 0.032);
      context.globalAlpha = 0.45 + next() * 0.55;
      context.fillStyle = color;
      context.beginPath();
      context.ellipse(x, y, leaf, leaf * (0.5 + next() * 0.5), next() * Math.PI, 0, Math.PI * 2);
      context.fill();
    }
    context.globalAlpha = 1;
    const map = new THREE.CanvasTexture(canvas);
    map.colorSpace = THREE.SRGBColorSpace;
    map.needsUpdate = true;
    return map;
  });
}

export function disposeTextures() {
  for (const entry of cache.values()) {
    if (entry?.isTexture) entry.dispose();
    else if (entry) for (const value of Object.values(entry)) value?.dispose?.();
  }
  cache.clear();
}
