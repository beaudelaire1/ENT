/*
  Univers 3D du Sablier.

  L'ambiance n'est pas un fond : c'est la moitié de l'image. Trois couches la portent.

  1. Le ciel. Un dégradé à trois couleurs se lit toujours comme un aplat d'illustration.
     Celui-ci part d'une diffusion atmosphérique (Rayleigh pour le bleu du zénith, Mie
     pour le halo autour du soleil) et porte de vrais nuages : un champ de bruit fractal
     éclairé par le soleil, avec une face lumineuse et une face sombre. Le soleil du ciel
     et la lumière directionnelle de la scène partagent la même direction — sans quoi
     les ombres tombent d'un côté et la lumière vient de l'autre.

  2. La matière. Chaque surface reçoit un albédo, une carte de normales et une carte de
     rugosité générés ensemble depuis un même champ de hauteur. C'est ce qui donne le
     relief : une couleur plate, même bruitée, reste du carton.

  3. L'air. Le compositeur relit la profondeur de l'image pour poser un brouillard de
     hauteur, la diffusion de la lumière du soleil dans l'air, le halo des sources vives,
     le vignetage et le grain. C'est cette couche qui fait qu'un objet posé au premier
     plan appartient au même espace que ce qui est loin derrière lui.

  La musique reste hors de ce fichier : elle appartient à l'utilisateur seul.
*/

const TAU = Math.PI * 2;
// Onze lieux, onze atmosphères. Le catalogue en comptait vingt-quatre, mais seize
// d'entre eux étaient la même construction reteintée : une forêt verte et la même
// forêt en orange ne sont pas deux univers, et l'écart de qualité se voyait d'autant
// plus qu'aucun n'était traité à fond. Deux scènes ne partagent ici une construction
// que si elles décrivent deux situations qu'on nommerait différemment — une mer
// calme et la même mer sous l'orage, un fleuve et un sanctuaire englouti.
const WORLD_KEYS = new Set([
  "arbre_etoiles", "refuge_pluie", "foret", "ocean", "sahara",
  "aurores", "galaxie", "fleuve_temps", "abysses",
]);
const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
const mix = (a, b, t) => a + (b - a) * t;
const smoothstep = (min, max, value) => {
  const t = clamp((value - min) / Math.max(0.0001, max - min));
  return t * t * (3 - 2 * t);
};

function seeded(index, salt = 1) {
  const value = Math.sin(index * 91.733 + salt * 37.719) * 43758.5453;
  return Math.abs(value - Math.floor(value));
}

// ---------------------------------------------------------------------------
// Bruit de Perlin périodique. La période vaut 256 : tant que les fréquences sont
// entières, la texture se raccorde à elle-même et aucune couture n'apparaît sur
// un sol répété vingt fois.
// ---------------------------------------------------------------------------
const PERMUTATION = new Uint8Array(512);
(() => {
  const values = new Uint8Array(256);
  for (let index = 0; index < 256; index += 1) values[index] = index;
  let seed = 0x2f6e2b1;
  for (let index = 255; index > 0; index -= 1) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const swap = seed % (index + 1);
    const held = values[index];
    values[index] = values[swap];
    values[swap] = held;
  }
  for (let index = 0; index < 512; index += 1) PERMUTATION[index] = values[index & 255];
})();

const fade = (t) => t * t * t * (t * (t * 6 - 15) + 10);
function gradientAt(hash, x, y) {
  const corner = hash & 7;
  const u = corner < 4 ? x : y;
  const v = corner < 4 ? y : x;
  return ((corner & 1) ? -u : u) + ((corner & 2) ? -2 * v : 2 * v);
}

function perlin(x, y) {
  const floorX = Math.floor(x);
  const floorY = Math.floor(y);
  const cellX = floorX & 255;
  const cellY = floorY & 255;
  const fx = x - floorX;
  const fy = y - floorY;
  const u = fade(fx);
  const v = fade(fy);
  const a = PERMUTATION[cellX] + cellY;
  const b = PERMUTATION[cellX + 1] + cellY;
  const lower = mix(gradientAt(PERMUTATION[a], fx, fy), gradientAt(PERMUTATION[b], fx - 1, fy), u);
  const upper = mix(gradientAt(PERMUTATION[a + 1], fx, fy - 1), gradientAt(PERMUTATION[b + 1], fx - 1, fy - 1), u);
  // Les gradients portent jusqu'à ±3 : sans normalisation ni borne, le résultat sort
  // de [-1, 1]. `ridged` calcule ensuite 1 - |bruit|, qui devenait négatif, et la
  // moindre puissance fractionnaire d'un nombre négatif vaut NaN — un relief entier
  // partait alors en positions invalides.
  return clamp(mix(lower, upper, v) * 0.66, -1, 1);
}

function fbm(x, y, octaves, frequency, gain = 0.5) {
  let sum = 0;
  let amplitude = 1;
  let total = 0;
  let scale = frequency;
  for (let octave = 0; octave < octaves; octave += 1) {
    sum += perlin(x * scale, y * scale) * amplitude;
    total += amplitude;
    amplitude *= gain;
    scale *= 2;
  }
  return sum / total;
}

// Bruit à crêtes : les vallées deviennent des arêtes. C'est ce qui donne aux roches
// leurs strates et aux montagnes leurs lignes de faîte, là où un fbm ordinaire ne
// produit que des bosses molles.
function ridged(x, y, octaves, frequency) {
  let sum = 0;
  let amplitude = 1;
  let total = 0;
  let scale = frequency;
  for (let octave = 0; octave < octaves; octave += 1) {
    sum += (1 - Math.abs(perlin(x * scale, y * scale))) * amplitude;
    total += amplitude;
    amplitude *= 0.52;
    scale *= 2;
  }
  // Le résultat est borné : plusieurs reliefs l'élèvent ensuite à une puissance
  // fractionnaire, qui exige une base positive.
  return clamp(sum / total, 0, 1);
}

function sessionState(app) {
  const progressValue = Number.parseFloat(
    document.querySelector("#digital-progress")?.style.getPropertyValue("--progress") || "1",
  );
  const progress = Number.isFinite(progressValue) ? clamp(progressValue) : 1;
  const date = new Date();
  const hour = date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
  const solarAngle = (hour / 24 - 0.25) * TAU;
  const solarElevation = Math.sin(solarAngle);
  const daylight = smoothstep(-0.14, 0.34, solarElevation);
  return {
    progress,
    elapsed: 1 - progress,
    daylight,
    solarAngle,
    solarElevation,
    density: clamp(Number(app.dataset.decorDensity || 2), 0, 3),
  };
}

// ---------------------------------------------------------------------------
// Matière procédurale
//
// Une seule passe produit trois cartes cohérentes entre elles depuis un même champ
// de hauteur : couleur, normales, rugosité. Générer la couleur seule — ce que faisait
// la version précédente — donne une surface qui a un motif mais pas de relief : la
// lumière glisse dessus sans jamais l'accrocher.
// ---------------------------------------------------------------------------
const SURFACE_CACHE = new Map();

const SURFACE_PRESETS = {
  stone: { relief: 1.0, roughness: [0.72, 0.96], contrast: 0.36, warm: 0.0 },
  rock: { relief: 1.35, roughness: [0.68, 0.98], contrast: 0.46, warm: 0.04 },
  cliff: { relief: 1.5, roughness: [0.7, 0.99], contrast: 0.52, warm: 0.05 },
  sand: { relief: 0.55, roughness: [0.78, 0.94], contrast: 0.2, warm: 0.1 },
  bark: { relief: 1.45, roughness: [0.82, 1.0], contrast: 0.5, warm: 0.08 },
  wood: { relief: 0.62, roughness: [0.38, 0.72], contrast: 0.34, warm: 0.12 },
  moss: { relief: 1.1, roughness: [0.86, 1.0], contrast: 0.42, warm: -0.03 },
  snow: { relief: 0.34, roughness: [0.5, 0.82], contrast: 0.1, warm: -0.02 },
  plaster: { relief: 0.5, roughness: [0.74, 0.92], contrast: 0.16, warm: 0.03 },
  metal: { relief: 0.36, roughness: [0.2, 0.52], contrast: 0.18, warm: 0.0 },
  silt: { relief: 0.8, roughness: [0.8, 0.97], contrast: 0.3, warm: -0.05 },
};

// Le champ de hauteur porte l'identité de la matière : ce sont ses accidents qui
// disent « écorce » ou « sable », bien plus que sa teinte.
function surfaceHeight(preset, u, v) {
  switch (preset) {
    case "sand": {
      // Rides de vent serrées, déformées par une houle lente. Le sable sans rides
      // reste une nappe orange, quelle que soit sa couleur.
      const drift = fbm(u, v, 4, 3) * 0.5;
      const ripple = Math.sin((v * 46 + drift * 26 + fbm(u, v, 2, 6) * 7)) * 0.5 + 0.5;
      return 0.42 + Math.pow(ripple, 1.6) * 0.34 + fbm(u, v, 5, 8) * 0.24;
    }
    case "bark": {
      // Fibres verticales très étirées, coupées de crevasses profondes.
      const fibre = ridged(u * 7, v * 0.55, 5, 6);
      const crack = Math.pow(clamp(ridged(u * 3.2, v * 0.4, 3, 3)), 5) * 1.5;
      return clamp(fibre * 0.72 + crack * 0.4 + fbm(u, v, 4, 16) * 0.16);
    }
    case "wood": {
      // Cernes : un champ radial déformé par du bruit, comme une planche débitée.
      const warp = fbm(u, v, 4, 3) * 1.4;
      const rings = Math.sin((v * 9 + warp) * TAU) * 0.5 + 0.5;
      return clamp(0.34 + Math.pow(rings, 2.2) * 0.4 + fbm(u * 2, v * 0.3, 4, 24) * 0.2);
    }
    case "moss": {
      // Touffes : du bruit haute fréquence seuillé, posé sur des bosses larges.
      const clumps = fbm(u, v, 3, 12);
      const tufts = Math.pow(clamp(fbm(u, v, 3, 32) * 0.5 + 0.5), 2.4);
      return clamp(0.36 + clumps * 0.5 + tufts * 0.34);
    }
    case "snow": {
      const drift = fbm(u, v, 4, 3);
      return clamp(0.62 + drift * 0.26 + fbm(u, v, 3, 26) * 0.1);
    }
    case "rock":
    case "cliff": {
      // Strates : des bandes horizontales fracturées, pas des bosses.
      const strata = Math.sin((v * 11 + fbm(u, v, 4, 4) * 4.4) * TAU) * 0.5 + 0.5;
      const fracture = ridged(u, v, 5, 5);
      return clamp(fracture * 0.6 + Math.pow(strata, 2.6) * 0.3 + fbm(u, v, 5, 14) * 0.2);
    }
    case "metal": {
      const brushed = fbm(u * 24, v * 0.5, 4, 8) * 0.5 + 0.5;
      return clamp(0.48 + brushed * 0.16 + fbm(u, v, 3, 18) * 0.1);
    }
    case "silt": {
      const dunes = fbm(u, v, 5, 4);
      return clamp(0.44 + dunes * 0.42 + fbm(u, v, 4, 18) * 0.2);
    }
    case "plaster":
      return clamp(0.5 + fbm(u, v, 4, 14) * 0.34 + fbm(u, v, 3, 40) * 0.14);
    default: {
      const broad = fbm(u, v, 5, 4);
      const grain = ridged(u, v, 4, 12);
      return clamp(0.4 + broad * 0.42 + grain * 0.24);
    }
  }
}

function makeSurfaceSet(THREE, preset, color, mobile, repeat = [6, 6]) {
  // La répétition ne change pas un seul pixel : c'est une propriété de la texture, pas
  // de son contenu. La faire entrer dans la clé de cache obligeait à recalculer tout le
  // champ de hauteur — cent mille pixels et quelques millions d'évaluations de bruit —
  // chaque fois qu'une même matière était posée à une autre échelle. Le contenu est
  // donc mis en cache seul, et seules les enveloppes sont dupliquées.
  const contentKey = `${preset}|${color}|${mobile}`;
  const tiledKey = `${contentKey}|${repeat[0]}x${repeat[1]}`;
  const tiled = SURFACE_CACHE.get(tiledKey);
  if (tiled) return tiled;

  const source = SURFACE_CACHE.get(contentKey);
  if (source) {
    const clone = (texture) => {
      const copy = texture.clone();
      copy.repeat.set(repeat[0], repeat[1]);
      copy.needsUpdate = true;
      return copy;
    };
    const variant = {
      map: clone(source.map),
      normalMap: clone(source.normalMap),
      roughnessMap: clone(source.roughnessMap),
    };
    SURFACE_CACHE.set(tiledKey, variant);
    return variant;
  }

  const size = mobile ? 160 : 288;
  const profile = SURFACE_PRESETS[preset] || SURFACE_PRESETS.stone;
  const heights = new Float32Array(size * size);
  const macro = new Float32Array(size * size);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const u = x / size;
      const v = y / size;
      heights[y * size + x] = surfaceHeight(preset, u, v);
      // Variation lente : sans elle, une matière répétée montre sa grille.
      macro[y * size + x] = fbm(u, v, 3, 2) * 0.5 + 0.5;
    }
  }

  const base = new THREE.Color(color);
  const albedo = new Uint8Array(size * size * 4);
  const normals = new Uint8Array(size * size * 4);
  const roughness = new Uint8Array(size * size * 4);
  const [roughLow, roughHigh] = profile.roughness;
  const sample = (x, y) => heights[((y + size) % size) * size + ((x + size) % size)];

  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const index = (y * size + x) * 4;
      const height = heights[y * size + x];
      const variation = macro[y * size + x];

      // Les creux s'assombrissent et se désaturent : c'est l'occlusion de contact,
      // celle qui fait qu'une pierre a des joints et pas seulement un motif.
      const shade = 1 + (height - 0.5) * profile.contrast * 2;
      const tint = 0.88 + variation * 0.3;
      const warmth = 1 + profile.warm * (variation - 0.5) * 2;
      albedo[index] = clamp(base.r * 255 * shade * tint * warmth, 0, 255);
      albedo[index + 1] = clamp(base.g * 255 * shade * tint, 0, 255);
      albedo[index + 2] = clamp(base.b * 255 * shade * tint / warmth, 0, 255);
      albedo[index + 3] = 255;

      // Normales par différences centrales sur le champ de hauteur.
      const dx = (sample(x + 1, y) - sample(x - 1, y)) * profile.relief * size * 0.012;
      const dy = (sample(x, y + 1) - sample(x, y - 1)) * profile.relief * size * 0.012;
      const length = Math.sqrt(dx * dx + dy * dy + 1);
      normals[index] = clamp((-dx / length * 0.5 + 0.5) * 255, 0, 255);
      normals[index + 1] = clamp((-dy / length * 0.5 + 0.5) * 255, 0, 255);
      normals[index + 2] = clamp((1 / length * 0.5 + 0.5) * 255, 0, 255);
      normals[index + 3] = 255;

      // Le fond des creux retient l'humidité : il brille un peu plus que les crêtes.
      const rough = mix(roughHigh, roughLow, clamp(height * 0.7 + variation * 0.3));
      roughness[index] = 0;
      roughness[index + 1] = clamp(rough * 255, 0, 255);
      roughness[index + 2] = 0;
      roughness[index + 3] = 255;
    }
  }

  const build = (data, colorSpace) => {
    const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
    texture.colorSpace = colorSpace;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(repeat[0], repeat[1]);
    texture.anisotropy = mobile ? 2 : 8;
    texture.generateMipmaps = true;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;
    return texture;
  };

  const set = {
    map: build(albedo, THREE.SRGBColorSpace),
    normalMap: build(normals, THREE.NoColorSpace),
    roughnessMap: build(roughness, THREE.NoColorSpace),
  };
  SURFACE_CACHE.set(contentKey, set);
  SURFACE_CACHE.set(tiledKey, set);
  return set;
}

// Matériau prêt à l'emploi : la matière arrive complète, jamais en couleur seule.
//
// La répétition se calcule à partir de la taille réelle de la surface (`span`, en
// unités de scène) et de la taille voulue d'un carreau (`tile`). Fixer la répétition
// à la main revient à étirer la même image sur un galet et sur un plateau de deux
// cents unités : la matière disparaît sur les grandes surfaces, qui redeviennent des
// aplats. C'était le défaut le plus visible du décor.
function surfaceMaterial(THREE, options) {
  const {
    preset = "stone", color = 0x808080, mobile = false, repeat, span, tile = 6,
    normalScale = 1, physical = false, ...rest
  } = options;
  const tiling = repeat || (span
    ? [Math.max(1, Math.round(span[0] / tile)), Math.max(1, Math.round(span[1] / tile))]
    : [6, 6]);
  const set = makeSurfaceSet(THREE, preset, color, mobile, tiling);
  const Material = physical ? THREE.MeshPhysicalMaterial : THREE.MeshStandardMaterial;
  return new Material({
    color: 0xffffff,
    map: set.map,
    normalMap: set.normalMap,
    normalScale: new THREE.Vector2(normalScale, normalScale),
    roughnessMap: set.roughnessMap,
    roughness: 1,
    metalness: 0,
    ...rest,
  });
}

// ---------------------------------------------------------------------------
// Ciel
// ---------------------------------------------------------------------------
const SKY_NOISE_GLSL = `
  float hash21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
  float vnoise(vec2 p){
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash21(i), b = hash21(i + vec2(1.0, 0.0));
    float c = hash21(i + vec2(0.0, 1.0)), d = hash21(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
  }
  float cloudFbm(vec2 p){
    float sum = 0.0, amp = 0.5;
    for (int i = 0; i < 6; i++) { sum += amp * vnoise(p); p = p * 2.07 + vec2(1.7, 9.2); amp *= 0.5; }
    return sum;
  }
`;

function makeSky(THREE, colors) {
  const uniforms = {
    sunDirection: { value: new THREE.Vector3(-0.4, 0.35, -0.85).normalize() },
    zenithColor: { value: new THREE.Color(colors.zenith) },
    horizonColor: { value: new THREE.Color(colors.horizon) },
    groundColor: { value: new THREE.Color(colors.ground) },
    sunColor: { value: new THREE.Color(colors.sun || 0xfff2d8) },
    // Densité, altitude, allongement et vitesse de la couche nuageuse. Un cirrus est
    // haut, étiré et ténu ; un ciel d'orage est bas, dense et compact.
    cloudCover: { value: colors.cloudCover ?? 0.42 },
    cloudSharpness: { value: colors.cloudSharpness ?? 1.4 },
    cloudStretch: { value: colors.cloudStretch ?? 1.0 },
    cloudHeight: { value: colors.cloudHeight ?? 0.11 },
    cloudLight: { value: new THREE.Color(colors.cloudLight || 0xfff4e2) },
    cloudDark: { value: new THREE.Color(colors.cloudDark || 0x59657a) },
    hazeStrength: { value: colors.haze ?? 0.5 },
    starStrength: { value: colors.stars || 0 },
    galaxyStrength: { value: colors.galaxy || 0 },
    sunDiscStrength: { value: colors.sunDisc ?? 1 },
    // En mode « capture d'environnement » le ciel rend sa lumière moyenne, sans ses
    // très hautes lumières ponctuelles : réduites à une carte de quelques pixels de
    // côté, elles reviendraient en pavés lumineux sur toute surface réfléchissante.
    envMode: { value: 0 },
    time: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms,
    vertexShader: `
      varying vec3 vDirection;
      void main() {
        vec4 worldPosition = modelMatrix * vec4(position, 1.0);
        vDirection = normalize(worldPosition.xyz - cameraPosition);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec3 vDirection;
      uniform vec3 sunDirection, zenithColor, horizonColor, groundColor, sunColor;
      uniform vec3 cloudLight, cloudDark;
      uniform float cloudCover, cloudSharpness, cloudStretch, cloudHeight;
      uniform float hazeStrength, starStrength, galaxyStrength, sunDiscStrength, envMode, time;
      ${SKY_NOISE_GLSL}

      // Densité nuageuse en un point du plan de la couche. Le décalage de deux
      // échelles produit la déformation lente qu'ont les nuages réels : sans elle,
      // le bruit reste une texture appliquée sur le ciel.
      float cloudDensity(vec2 p){
        vec2 warp = vec2(cloudFbm(p * 0.42 + time * 0.006), cloudFbm(p * 0.42 + 5.3 - time * 0.004));
        float base = cloudFbm(p + warp * 1.6 + vec2(time * 0.011, time * 0.004));
        float shaped = smoothstep(1.0 - cloudCover, 1.0 - cloudCover + 0.42 / cloudSharpness, base);
        return shaped * smoothstep(0.0, 0.34, base);
      }

      void main() {
        vec3 ray = normalize(vDirection);
        float up = ray.y;
        float cosSun = dot(ray, sunDirection);

        // Diffusion : l'épaisseur d'air traversée croît vite près de l'horizon, ce qui
        // y concentre la lumière rouge et y délave le bleu.
        float thickness = 1.0 / max(0.09, up * 0.82 + 0.18);
        float rayleighPhase = 0.75 * (1.0 + cosSun * cosSun);
        float g = 0.76;
        float miePhase = (1.0 - g * g) / pow(1.0 + g * g - 2.0 * g * cosSun, 1.5);

        float zenithMix = smoothstep(-0.02, 0.62, up);
        vec3 color = mix(horizonColor, zenithColor, zenithMix);
        color *= mix(1.0, 0.72, smoothstep(0.0, 3.4, thickness) * 0.6);
        color += horizonColor * rayleighPhase * 0.16 * smoothstep(0.0, 2.6, thickness);
        color += sunColor * miePhase * 0.055 * hazeStrength * smoothstep(0.0, 3.2, thickness);

        // Bande d'horizon : l'air chargé au ras du sol. C'est elle qui donne la
        // distance, plus qu'un dégradé.
        float horizonBand = exp(-abs(up) * 11.0) * hazeStrength;
        color = mix(color, mix(horizonColor, sunColor, 0.28), horizonBand * 0.42);

        // Voie lactée : une bande étroite de poussière, inclinée. Large ou trop
        // lumineuse, elle cesse d'être un détail du ciel et devient un voile qui
        // éclaircit toute la voûte — la nuit se met alors à ressembler au crépuscule.
        if (galaxyStrength > 0.001 && envMode < 0.5) {
          float band = exp(-pow(abs(ray.y * 3.2 - ray.x * 1.1 - 0.2) * 3.4, 2.0));
          float dust = cloudFbm(vec2(ray.x, ray.z) * 7.0 + ray.y * 4.0);
          float mottle = smoothstep(0.28, 0.85, dust);
          color += vec3(0.3, 0.31, 0.44) * band * mottle * 0.09 * galaxyStrength
                 * smoothstep(0.02, 0.3, up);
        }

        // Étoiles : une grille de cellules, au plus une étoile par cellule. Le point
        // est rond et décentré dans sa case — une cellule remplie donnerait un semis
        // de petits carrés alignés, ce qui se voit immédiatement.
        if (starStrength > 0.001 && envMode < 0.5) {
          vec2 field = (ray.xz / max(0.06, ray.y + 0.9)) * 260.0;
          vec2 cell = floor(field);
          vec2 local = fract(field) - 0.5;
          float seed = hash21(cell);
          if (seed > 0.9915) {
            vec2 jitter = vec2(hash21(cell + 7.3), hash21(cell + 13.7)) - 0.5;
            float magnitude = hash21(cell + 21.1);
            float radius = 0.055 + magnitude * 0.16;
            float point = smoothstep(radius, 0.0, length(local - jitter * 0.62));
            float twinkle = 0.68 + 0.32 * sin(time * (1.1 + magnitude * 6.0) + seed * 90.0);
            vec3 starTint = mix(vec3(0.7, 0.8, 1.0), vec3(1.0, 0.87, 0.7), hash21(cell + 3.1));
            color += starTint * point * (0.35 + magnitude * 1.5) * twinkle
                   * smoothstep(-0.02, 0.2, up) * starStrength;
          }
        }

        // Nuages : le rayon est projeté sur une couche plane. Près de l'horizon la
        // projection s'étire d'elle-même, ce qui donne la perspective de la couche.
        // Le dénominateur est borné : au ras de l'horizon la projection tendrait vers
        // l'infini et la couche se figerait en dalles géantes, que la moindre surface
        // réfléchissante renverrait ensuite en damier lumineux.
        if (cloudCover > 0.001 && up > -0.02) {
          vec2 plane = ray.xz / max(0.16, up + cloudHeight) * vec2(1.0, cloudStretch);
          float density = cloudDensity(plane * 1.35) * smoothstep(0.0, 0.13, up);
          if (density > 0.001) {
            // Auto-ombrage : on regoûte la densité un pas plus loin vers le soleil.
            // Là où le nuage est épais devant la lumière, il s'assombrit.
            vec2 towardSun = normalize(sunDirection.xz + vec2(0.001)) * 0.5;
            float shadow = cloudDensity((plane + towardSun) * 1.35);
            float lit = exp(-shadow * 2.6);
            vec3 body = mix(cloudDark, cloudLight, lit);
            // Frange lumineuse : les bords fins laissent passer le soleil.
            body += sunColor * pow(max(cosSun, 0.0), 6.0) * (1.0 - density) * 0.55;
            color = mix(color, body, clamp(density, 0.0, 1.0) * 0.92);
          }
        }

        // Disque solaire, avec assombrissement centre-bord et couronne.
        float disc = smoothstep(0.99965, 0.99992, cosSun);
        color += sunColor * disc * 5.5 * sunDiscStrength * (1.0 - envMode);
        color += sunColor * pow(max(cosSun, 0.0), 220.0) * 0.7 * sunDiscStrength * (1.0 - envMode);

        // Sous l'horizon : le sol, jamais une coupure nette.
        color = mix(color, groundColor, smoothstep(0.0, -0.16, up));

        // Tramage : sans lui, un ciel lisse montre ses paliers en aplats de bandes.
        color += (hash21(gl_FragCoord.xy * 0.71) - 0.5) * 0.0055;
        if (envMode > 0.5) color = min(color, vec3(1.6));
        gl_FragColor = vec4(color, 1.0);
      }
    `,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(120, 48, 32), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1;
  return { mesh, uniforms, material };
}

// ---------------------------------------------------------------------------
// Compositeur
//
// La scène est rendue dans une cible en virgule flottante, puis retraitée. Sans cette
// passe, une image 3D reste « propre » : pas de halo autour des sources, pas d'air
// entre les plans, pas de grain. C'est cette propreté qui la fait lire comme une image
// de synthèse plutôt que comme une prise de vue.
// ---------------------------------------------------------------------------
const FULLSCREEN_VERTEX = `
  varying vec2 vUv;
  void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

function makeComposer(THREE, renderer, mobile) {
  const quad = new THREE.BufferGeometry();
  quad.setAttribute("position", new THREE.BufferAttribute(new Float32Array([
    -1, -1, 0, 3, -1, 0, -1, 3, 0,
  ]), 3));
  quad.setAttribute("uv", new THREE.BufferAttribute(new Float32Array([0, 0, 2, 0, 0, 2]), 2));
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  const depthTexture = new THREE.DepthTexture(1, 1);
  depthTexture.type = THREE.UnsignedIntType;
  const sceneTarget = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType,
    depthTexture,
    depthBuffer: true,
    samples: mobile ? 0 : 2,
  });
  const makeTarget = () => {
    const target = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: false });
    target.texture.minFilter = THREE.LinearFilter;
    target.texture.magFilter = THREE.LinearFilter;
    return target;
  };
  const bloomA = makeTarget();
  const bloomB = makeTarget();
  const bloomC = makeTarget();
  const bloomD = makeTarget();

  const brightMaterial = new THREE.ShaderMaterial({
    uniforms: { tSource: { value: null }, threshold: { value: 1.05 }, knee: { value: 0.6 } },
    vertexShader: FULLSCREEN_VERTEX,
    fragmentShader: `
      varying vec2 vUv;
      uniform sampler2D tSource;
      uniform float threshold, knee;
      void main(){
        // Une source minuscule et très intense produit, après réduction et flou, un
        // pavé lumineux net : la valeur extrême d'un seul texel se répand sur tout son
        // voisinage. Borner l'entrée supprime ces « lucioles » sans rien retirer aux
        // halos larges, qui sont bien en deçà du plafond.
        vec3 color = min(texture2D(tSource, vUv).rgb, vec3(9.0));
        float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
        float soft = clamp((luma - threshold + knee) / max(0.0001, 2.0 * knee), 0.0, 1.0);
        float weight = max(soft * soft * knee, max(luma - threshold, 0.0)) / max(luma, 0.0001);
        gl_FragColor = vec4(color * weight, 1.0);
      }
    `,
  });

  const blurMaterial = new THREE.ShaderMaterial({
    uniforms: { tSource: { value: null }, direction: { value: new THREE.Vector2(1, 0) } },
    vertexShader: FULLSCREEN_VERTEX,
    fragmentShader: `
      varying vec2 vUv;
      uniform sampler2D tSource;
      uniform vec2 direction;
      void main(){
        vec3 sum = texture2D(tSource, vUv).rgb * 0.227;
        sum += (texture2D(tSource, vUv + direction * 1.385).rgb
              + texture2D(tSource, vUv - direction * 1.385).rgb) * 0.316;
        sum += (texture2D(tSource, vUv + direction * 3.231).rgb
              + texture2D(tSource, vUv - direction * 3.231).rgb) * 0.070;
        gl_FragColor = vec4(sum, 1.0);
      }
    `,
  });

  const compositeMaterial = new THREE.ShaderMaterial({
    uniforms: {
      tScene: { value: null },
      tBloomNear: { value: null },
      tBloomFar: { value: null },
      tDepth: { value: null },
      projectionInverse: { value: new THREE.Matrix4() },
      viewInverse: { value: new THREE.Matrix4() },
      cameraNear: { value: 0.1 },
      cameraFar: { value: 160 },
      resolution: { value: new THREE.Vector2(1, 1) },
      sunScreen: { value: new THREE.Vector3(0.5, 0.5, 0) },
      sunColor: { value: new THREE.Color(0xffe6bd) },
      fogColor: { value: new THREE.Color(0x8fa6b8) },
      fogSunColor: { value: new THREE.Color(0xffd9a6) },
      fogDensity: { value: 0.02 },
      fogHeight: { value: 6.0 },
      fogFloor: { value: -1.4 },
      bloomStrength: { value: 0.42 },
      shaftStrength: { value: 0.0 },
      exposure: { value: 1.0 },
      vignette: { value: 0.44 },
      grain: { value: 0.028 },
      chroma: { value: 0.35 },
      lift: { value: new THREE.Color(0x0a0f16) },
      gain: { value: new THREE.Color(0xfff6ec) },
      saturation: { value: 1.06 },
      time: { value: 0 },
    },
    vertexShader: FULLSCREEN_VERTEX,
    fragmentShader: `
      varying vec2 vUv;
      uniform sampler2D tScene, tBloomNear, tBloomFar, tDepth;
      uniform mat4 projectionInverse, viewInverse;
      uniform vec2 resolution;
      uniform vec3 sunScreen, sunColor, fogColor, fogSunColor, lift, gain;
      uniform float cameraNear, cameraFar, fogDensity, fogHeight, fogFloor;
      uniform float bloomStrength, shaftStrength, exposure, vignette, grain, chroma, saturation, time;

      float hash21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }

      vec3 acesFilm(vec3 x){
        const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
        return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
      }
      vec3 toSrgb(vec3 c){
        return mix(c * 12.92, 1.055 * pow(max(c, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
      }

      void main(){
        float depth = texture2D(tDepth, vUv).x;
        bool isSky = depth >= 0.999995;

        // Aberration chromatique : les canaux se séparent en bord de champ, comme
        // au travers d'une optique réelle. Au centre, rien ne bouge.
        vec2 fromCenter = vUv - 0.5;
        float edge = dot(fromCenter, fromCenter);
        vec2 shift = fromCenter * edge * chroma * 0.006;
        vec3 color;
        color.r = texture2D(tScene, vUv + shift).r;
        color.g = texture2D(tScene, vUv).g;
        color.b = texture2D(tScene, vUv - shift).b;

        // Position monde reconstruite depuis la profondeur : l'air peut alors
        // s'épaissir vers le bas et se colorer du côté du soleil.
        if (!isSky) {
          vec4 clip = vec4(vUv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
          vec4 viewPosition = projectionInverse * clip;
          viewPosition /= viewPosition.w;
          vec3 world = (viewInverse * vec4(viewPosition.xyz, 1.0)).xyz;
          float distance = length(viewPosition.xyz);
          float height = exp(-max(world.y - fogFloor, 0.0) / max(0.4, fogHeight));
          float amount = 1.0 - exp(-fogDensity * distance * height);
          vec3 toPixel = normalize((viewInverse * vec4(viewPosition.xyz, 0.0)).xyz);
          vec3 sunWorld = normalize(sunScreen.z > 0.0 ? vec3(sunScreen.xy - 0.5, 1.0) : vec3(0.0, 1.0, 0.0));
          float inscatter = pow(max(dot(toPixel, normalize(vec3(sunScreen.xy - 0.5, 0.8))), 0.0), 6.0);
          vec3 air = mix(fogColor, fogSunColor, inscatter * 0.85);
          color = mix(color, air, clamp(amount, 0.0, 0.94));
        }

        vec3 bloom = texture2D(tBloomNear, vUv).rgb * 0.62 + texture2D(tBloomFar, vUv).rgb * 0.38;
        color += bloom * bloomStrength;

        // Rais de lumière : le halo flouté est ré-échantillonné en s'éloignant du
        // soleil. Ce qui est bouché par la géométrie ne rayonne pas, ce qui suffit à
        // faire apparaître les colonnes de lumière entre les obstacles.
        if (shaftStrength > 0.001 && sunScreen.z > 0.0) {
          vec2 toSun = sunScreen.xy - vUv;
          vec3 shafts = vec3(0.0);
          float weight = 1.0;
          for (int i = 0; i < 12; i++) {
            vec2 samplePoint = vUv + toSun * (float(i) / 12.0) * 0.92;
            shafts += texture2D(tBloomFar, samplePoint).rgb * weight;
            weight *= 0.86;
          }
          float falloff = smoothstep(1.1, 0.05, length(toSun));
          color += shafts * (shaftStrength / 12.0) * falloff * sunColor;
        }

        color *= exposure;
        color = acesFilm(color);

        // Étalonnage : le noir se relève d'un souffle vers le bleu, les hautes lumières
        // se teintent. Un noir absolu est une signature de rendu, pas de photographie.
        color = lift * (1.0 - color) + gain * color;
        float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
        color = mix(vec3(luma), color, saturation);

        float radius = length(fromCenter * vec2(resolution.x / max(resolution.y, 1.0), 1.0) * 1.24);
        color *= mix(1.0, smoothstep(1.32, 0.34, radius), vignette);

        color = toSrgb(color);
        // Grain animé, appliqué après l'encodage : il vit dans l'image finale.
        float noise = hash21(gl_FragCoord.xy + fract(time) * 137.0) - 0.5;
        color += noise * grain * (1.0 - luma * 0.55);
        gl_FragColor = vec4(color, 1.0);
      }
    `,
  });

  const mesh = new THREE.Mesh(quad, brightMaterial);
  const stage = new THREE.Scene();
  stage.add(mesh);

  const draw = (material, target) => {
    mesh.material = material;
    renderer.setRenderTarget(target || null);
    renderer.render(stage, camera);
  };

  let width = 1;
  let height = 1;
  return {
    uniforms: compositeMaterial.uniforms,
    sceneTarget,
    setSize(nextWidth, nextHeight, pixelRatio) {
      width = Math.max(1, Math.round(nextWidth * pixelRatio));
      height = Math.max(1, Math.round(nextHeight * pixelRatio));
      sceneTarget.setSize(width, height);
      const halfWidth = Math.max(1, width >> 1);
      const halfHeight = Math.max(1, height >> 1);
      bloomA.setSize(halfWidth, halfHeight);
      bloomB.setSize(halfWidth, halfHeight);
      bloomC.setSize(Math.max(1, width >> 2), Math.max(1, height >> 2));
      bloomD.setSize(Math.max(1, width >> 2), Math.max(1, height >> 2));
      compositeMaterial.uniforms.resolution.value.set(width, height);
    },
    render(scene, camera3d) {
      renderer.setRenderTarget(sceneTarget);
      renderer.clear();
      renderer.render(scene, camera3d);

      brightMaterial.uniforms.tSource.value = sceneTarget.texture;
      draw(brightMaterial, bloomA);

      blurMaterial.uniforms.tSource.value = bloomA.texture;
      blurMaterial.uniforms.direction.value.set(1 / Math.max(1, width >> 1), 0);
      draw(blurMaterial, bloomB);
      blurMaterial.uniforms.tSource.value = bloomB.texture;
      blurMaterial.uniforms.direction.value.set(0, 1 / Math.max(1, height >> 1));
      draw(blurMaterial, bloomA);

      blurMaterial.uniforms.tSource.value = bloomA.texture;
      blurMaterial.uniforms.direction.value.set(2.4 / Math.max(1, width >> 2), 0);
      draw(blurMaterial, bloomC);
      blurMaterial.uniforms.tSource.value = bloomC.texture;
      blurMaterial.uniforms.direction.value.set(0, 2.4 / Math.max(1, height >> 2));
      draw(blurMaterial, bloomD);

      compositeMaterial.uniforms.tScene.value = sceneTarget.texture;
      compositeMaterial.uniforms.tBloomNear.value = bloomA.texture;
      compositeMaterial.uniforms.tBloomFar.value = bloomD.texture;
      compositeMaterial.uniforms.tDepth.value = depthTexture;
      compositeMaterial.uniforms.projectionInverse.value.copy(camera3d.projectionMatrixInverse);
      compositeMaterial.uniforms.viewInverse.value.copy(camera3d.matrixWorld);
      compositeMaterial.uniforms.cameraNear.value = camera3d.near;
      compositeMaterial.uniforms.cameraFar.value = camera3d.far;
      draw(compositeMaterial, null);
    },
    dispose() {
      for (const target of [sceneTarget, bloomA, bloomB, bloomC, bloomD]) target.dispose();
      for (const material of [brightMaterial, blurMaterial, compositeMaterial]) material.dispose();
      quad.dispose();
    },
  };
}

// ---------------------------------------------------------------------------
// Aides de scène
// ---------------------------------------------------------------------------
function configureShadow(light, mobile, extent = 26) {
  light.castShadow = true;
  light.shadow.mapSize.set(mobile ? 1024 : 1536, mobile ? 1024 : 1536);
  light.shadow.camera.near = 0.5;
  light.shadow.camera.far = 110;
  light.shadow.camera.left = -extent;
  light.shadow.camera.right = extent;
  light.shadow.camera.top = extent;
  light.shadow.camera.bottom = -extent;
  light.shadow.bias = -0.0004;
  light.shadow.normalBias = 0.035;
  light.shadow.radius = 3;
}

function shadowed(mesh, cast = true) {
  mesh.castShadow = cast;
  mesh.receiveShadow = true;
  return mesh;
}

function cylinderBetween(THREE, start, end, radius, material, radialSegments = 10) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius * 0.72, radius, length, radialSegments), material);
  mesh.position.copy(start).add(end).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  return shadowed(mesh);
}

// Occlusion de contact. Une tache radiale unique se lit comme un autocollant : le
// noyau serré et la jupe large se superposent ici comme le fait une vraie pénombre,
// dense sous l'objet et délavée sur ses bords.
function makeContactTexture(THREE) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  const paint = (radius, stops) => {
    const gradient = context.createRadialGradient(128, 128, 1, 128, 128, radius);
    for (const [stop, color] of stops) gradient.addColorStop(stop, color);
    context.fillStyle = gradient;
    context.fillRect(0, 0, 256, 256);
  };
  context.globalCompositeOperation = "source-over";
  paint(126, [[0, "rgba(0,0,0,.34)"], [0.42, "rgba(0,0,0,.2)"], [1, "rgba(0,0,0,0)"]]);
  context.globalCompositeOperation = "lighter";
  paint(66, [[0, "rgba(0,0,0,.62)"], [0.5, "rgba(0,0,0,.3)"], [1, "rgba(0,0,0,0)"]]);
  paint(30, [[0, "rgba(0,0,0,.7)"], [1, "rgba(0,0,0,0)"]]);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

function addContactShadow(THREE, pack, position, scale = [5.4, 2.7], opacity = 0.55) {
  const texture = makeContactTexture(THREE);
  pack.textures.push(texture);
  const material = new THREE.MeshBasicMaterial({
    alphaMap: texture,
    color: 0x000000,
    transparent: true,
    opacity,
    depthWrite: false,
  });
  const shadow = new THREE.Mesh(new THREE.PlaneGeometry(scale[0], scale[1]), material);
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.copy(position);
  shadow.position.y += 0.02;
  shadow.renderOrder = 3;
  pack.scene.add(shadow);
  return shadow;
}

// Faisceau lumineux tenu par l'air. Un cône en opacité constante montre son arête et
// devient un objet solide ; celui-ci se densifie là où on le voit par la tranche et
// s'éteint à ses deux extrémités, comme un volume de poussière éclairée.
function makeBeamMaterial(THREE, color, strength = 0.1) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    uniforms: {
      color: { value: new THREE.Color(color) },
      strength: { value: strength },
    },
    vertexShader: `
      varying vec2 vUv;
      varying vec3 vViewNormal;
      void main(){
        vUv = uv;
        vViewNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      varying vec3 vViewNormal;
      uniform vec3 color;
      uniform float strength;
      void main(){
        // Le rayon traverse le plus de matière au milieu du faisceau et presque rien
        // à sa silhouette. C'est donc |normal.z| qui donne l'épaisseur — l'inverse
        // dessinait un contour lumineux, c'est-à-dire un tube en verre.
        float thickness = pow(abs(vViewNormal.z), 1.5);
        float fall = smoothstep(0.0, 0.42, vUv.y) * smoothstep(1.02, 0.4, vUv.y);
        gl_FragColor = vec4(color, thickness * fall * strength);
      }
    `,
  });
}

// Caustiques : le réseau mouvant que la surface de l'eau projette sur le fond. C'est
// la signature de la lumière sous-marine ; sans elle, un fond éclairé de façon égale
// reste une image de terrain quelconque passée au filtre bleu.
function makeCausticTexture(THREE, mobile) {
  const size = mobile ? 128 : 256;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const index = (y * size + x) * 4;
      const u = x / size;
      const v = y / size;
      // Interférence de trois ondes déformées : les lignes se croisent et forment
      // les mailles claires caractéristiques.
      const warp = fbm(u * 2, v * 2, 3, 3) * 1.4;
      let value = 0;
      for (let wave = 0; wave < 3; wave += 1) {
        const angle = wave * 2.1;
        const projected = u * Math.cos(angle) + v * Math.sin(angle);
        value += Math.abs(Math.sin((projected * 9 + warp) * TAU));
      }
      const mesh = Math.pow(clamp(1 - value / 3), 5) * 255;
      data[index] = mesh;
      data[index + 1] = mesh;
      data[index + 2] = mesh;
      data[index + 3] = 255;
    }
  }
  const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  texture.colorSpace = THREE.NoColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}

// ---------------------------------------------------------------------------
// Le socle
//
// C'est la pièce la plus importante du décor : l'objet du minuteur se tient dessus,
// et c'est donc là — et nulle part ailleurs — que se joue son appartenance à la scène.
// Un cylindre nu s'y lisait comme un disque gris posé sur l'image, quand il n'était
// pas purement invisible dans les scènes sombres, l'objet flottant alors sur du noir.
//
// Trois choses le corrigent. Un profil tourné, avec chanfrein, gorge et empattement :
// la silhouette accroche la lumière au lieu de la subir. Une lumière d'appoint qui lui
// est propre, orientée comme le soleil de la scène, pour qu'il ne tombe jamais
// complètement dans l'ombre. Et une occlusion de contact au sol, qui l'y assied.
// ---------------------------------------------------------------------------
function addPedestal(THREE, pack, options) {
  const {
    position, radius = 4.7, height = 0.62, material, mobile = false,
    fillColor = 0xfff0d8, fillIntensity = 6, squash = 0.74,
    rimColor = 0xbcd6ff, rimIntensity = 2.2,
  } = options;

  const top = height / 2;
  const rimRadius = radius;
  const baseRadius = radius * 1.07;
  // Profil du tournage, ordonné du bas vers le haut.
  //
  // Le sens compte : `LatheGeometry` déduit l'orientation des faces de la progression
  // des points. Décrit du haut vers le bas, le socle sort retourné — ses normales
  // pointent vers l'intérieur, il est éliminé au tri des faces arrière et l'on ne voit
  // plus que le liseré du chanfrein, seul à flotter dans le vide.
  const profile = [
    [0, top - height],
    [baseRadius, top - height],
    [baseRadius, top - height * 0.86],
    [rimRadius * 0.945, top - height * 0.62],
    [rimRadius * 0.93, top - height * 0.46],
    [rimRadius * 0.995, top - height * 0.34],
    [rimRadius, top - height * 0.16],
    [rimRadius * 0.985, top - height * 0.07],
    [rimRadius * 0.9, top],
    [0, top],
  ].map(([x, y]) => new THREE.Vector2(x, y));

  const plinthGeometry = new THREE.LatheGeometry(profile, mobile ? 44 : 88);
  // `LatheGeometry` enroule ses coordonnées de texture autour de l'axe : la matière
  // part alors du centre en éventail et se referme sur une couture bien visible en
  // plein milieu du dessus — c'est-à-dire à l'endroit exact où se pose l'objet du
  // minuteur. Une projection à plat, vue de dessus, rend au socle une surface de
  // pierre taillée dans un seul bloc.
  const plinthPosition = plinthGeometry.attributes.position;
  const plinthUv = plinthGeometry.attributes.uv;
  const uvScale = 1 / Math.max(0.001, radius * 0.62);
  for (let index = 0; index < plinthPosition.count; index += 1) {
    plinthUv.setXY(
      index,
      plinthPosition.getX(index) * uvScale + 0.5,
      plinthPosition.getZ(index) * uvScale + 0.5,
    );
  }
  plinthUv.needsUpdate = true;
  const plinth = shadowed(new THREE.Mesh(plinthGeometry, material));
  plinth.scale.z = squash;
  plinth.position.copy(position);
  pack.scene.add(plinth);

  // Un mince liseré sur l'arête haute. C'est le trait le plus fin de la scène et
  // celui qui dit le mieux que la pierre a été taillée.
  const chamfer = new THREE.Mesh(
    new THREE.TorusGeometry(rimRadius * 0.972, height * 0.017, 8, mobile ? 60 : 120),
    new THREE.MeshStandardMaterial({
      color: 0xffffff, roughness: 0.32, metalness: 0.1,
      emissive: fillColor, emissiveIntensity: 0.1,
    }),
  );
  chamfer.rotation.x = Math.PI / 2;
  chamfer.scale.z = squash;
  chamfer.position.copy(position);
  chamfer.position.y += top - height * 0.1;
  pack.scene.add(chamfer);

  // Appoint : une lumière courte, qui ne porte que sur le socle et son voisinage.
  // Elle suit la direction du soleil pour que l'ombre reste cohérente avec le reste.
  //
  // L'intensité est compensée par le carré de la distance. Le moteur travaille en
  // photométrie physique : une source posée à sept unités avec une intensité de dix
  // n'éclaire quasiment rien, et le socle restait noir dans les scènes sombres.
  const fillOffset = new THREE.Vector3(0, radius * 0.5, radius * 0.34)
    .addScaledVector(pack.sunDirection, radius * 0.5);
  const fill = new THREE.PointLight(fillColor, fillIntensity * fillOffset.lengthSq(), radius * 3.4, 2);
  fill.position.copy(position).add(fillOffset);
  pack.scene.add(fill);

  // Contre-jour : il détache le bord du socle du sol qui se trouve derrière.
  const rimOffset = new THREE.Vector3(0, radius * 0.34, -radius * 0.55)
    .addScaledVector(pack.sunDirection, -radius * 0.4);
  const rim = new THREE.PointLight(rimColor, rimIntensity * rimOffset.lengthSq(), radius * 2.8, 2);
  rim.position.copy(position).add(rimOffset);
  pack.scene.add(rim);

  addContactShadow(
    THREE, pack,
    new THREE.Vector3(position.x, position.y - height * 0.46, position.z),
    [radius * 2.32, radius * 2.32 * squash], 0.72,
  );

  pack.pedestal = { plinth, chamfer, fill, rim, baseFill: fillIntensity, baseRim: rimIntensity };
  return plinth;
}

// Particules en volume, avec une texture douce. Des points carrés se voient comme
// des pixels ; il faut un grain qui s'éteint sur ses bords pour lire comme de la
// poussière en suspension.
let particleTexture = null;
function getParticleTexture(THREE) {
  if (particleTexture) return particleTexture;
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.3, "rgba(255,255,255,.55)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 64, 64);
  particleTexture = new THREE.CanvasTexture(canvas);
  particleTexture.colorSpace = THREE.SRGBColorSpace;
  return particleTexture;
}

function makeParticles(THREE, count, bounds, color, size, opacity, salt = 1) {
  const positions = new Float32Array(count * 3);
  const scales = new Float32Array(count);
  for (let index = 0; index < count; index += 1) {
    positions[index * 3] = bounds.x[0] + seeded(index, salt) * (bounds.x[1] - bounds.x[0]);
    positions[index * 3 + 1] = bounds.y[0] + seeded(index, salt + 7) * (bounds.y[1] - bounds.y[0]);
    positions[index * 3 + 2] = bounds.z[0] + seeded(index, salt + 13) * (bounds.z[1] - bounds.z[0]);
    scales[index] = 0.45 + seeded(index, salt + 19) * 1.4;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aScale", new THREE.BufferAttribute(scales, 1));
  const material = new THREE.PointsMaterial({
    color,
    size,
    map: getParticleTexture(THREE),
    alphaMap: getParticleTexture(THREE),
    transparent: true,
    opacity,
    depthWrite: false,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  return { points, material, count, baseOpacity: opacity };
}

// Rocher irrégulier : une icosphère dont chaque sommet est repoussé par du bruit.
// Un dodécaèdre lisse n'a ni arête ni facette — d'où l'effet « galet de dessin animé ».
function makeBoulderGeometry(THREE, detail, seed, roughness = 0.42) {
  const geometry = new THREE.IcosahedronGeometry(1, detail);
  const position = geometry.attributes.position;
  const vertex = new THREE.Vector3();
  for (let index = 0; index < position.count; index += 1) {
    vertex.fromBufferAttribute(position, index);
    const large = fbm(vertex.x * 0.5 + seed, vertex.z * 0.5 + vertex.y * 0.3, 3, 2);
    const facet = ridged(vertex.x * 1.4 + seed * 3.1, vertex.y * 1.4 - vertex.z, 3, 3);
    const push = 1 + large * roughness + (facet - 0.5) * roughness * 0.9;
    vertex.multiplyScalar(Math.max(0.55, push));
    position.setXYZ(index, vertex.x, vertex.y, vertex.z);
  }
  geometry.computeVertexNormals();
  return geometry;
}

// Aiguille marine. Une icosphère étirée en hauteur donne une pointe de diamant : les
// facettes convergent vers un sommet unique. Un fût vertical, creusé de strates
// horizontales et rongé irrégulièrement sur ses flancs, se lit au contraire comme de
// la roche taillée par la mer.
function makeSeaStackGeometry(THREE, seed, mobile) {
  const geometry = new THREE.CylinderGeometry(0.62, 1, 2, mobile ? 14 : 22, mobile ? 12 : 20, false);
  const position = geometry.attributes.position;
  const vertex = new THREE.Vector3();
  for (let index = 0; index < position.count; index += 1) {
    vertex.fromBufferAttribute(position, index);
    const height = vertex.y * 0.5 + 0.5;
    const angle = Math.atan2(vertex.z, vertex.x);
    // Strates : des bandes horizontales qui font saillie, décalées par un peu de bruit.
    const strata = Math.sin(height * 26 + fbm(angle * 0.5 + seed, height * 3, 3, 2) * 4) * 0.05;
    const erosion = fbm(Math.cos(angle) * 1.6 + seed, height * 2.4, 4, 2) * 0.34;
    const taper = 1 - Math.pow(height, 2.4) * 0.34;
    const radius = Math.hypot(vertex.x, vertex.z) * (taper + strata + erosion);
    position.setX(index, Math.cos(angle) * radius);
    position.setZ(index, Math.sin(angle) * radius);
    // Le sommet n'est jamais plat : il s'ébrèche.
    if (height > 0.94) position.setY(index, vertex.y - fbm(angle + seed, 7.3, 3, 3) * 0.24);
  }
  geometry.computeVertexNormals();
  return geometry;
}

// Terrain : un plan dont chaque sommet suit une fonction de hauteur. Les normales
// sont recalculées, faute de quoi la lumière reste celle d'un plan.
function makeTerrain(THREE, width, depth, segmentsX, segmentsZ, heightAt) {
  const geometry = new THREE.PlaneGeometry(width, depth, segmentsX, segmentsZ);
  const position = geometry.attributes.position;
  for (let index = 0; index < position.count; index += 1) {
    const x = position.getX(index);
    const z = -position.getY(index);
    position.setZ(index, heightAt(x, z));
  }
  geometry.computeVertexNormals();
  geometry.rotateX(-Math.PI / 2);
  return geometry;
}

// Ligne de crête lointaine. Empiler des blocs géants donne des silhouettes
// polygonales aux arêtes droites ; un vrai relief déplacé, posé loin derrière, ferme
// l'espace sans le trahir. Les plans successifs s'éclaircissent : c'est la perspective
// atmosphérique, et c'est elle qui crée la sensation de distance.
function addDistantRidges(THREE, scene, options) {
  const { color = 0x1a2734, layers = 3, distance = -70, spacing = 26, height = 12, seed = 1 } = options;
  const group = new THREE.Group();
  for (let layer = 0; layer < layers; layer += 1) {
    const depth = distance - layer * spacing;
    const fade = layer / Math.max(1, layers - 1);
    const geometry = makeTerrain(THREE, 260, 46, 96, 10, (x, z) => {
      const profile = ridged(x * 0.012 + seed + layer * 5.7, z * 0.02, 4, 3);
      const swell = fbm(x * 0.006 - layer * 3.1, z * 0.01, 3, 2) * 0.5 + 0.5;
      const crest = Math.pow(profile, 1.6) * swell;
      return crest * height * (1 + layer * 0.42) - height * 0.32;
    });
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color(color).lerp(new THREE.Color(0xffffff), fade * 0.16),
      fog: true,
    });
    const ridge = new THREE.Mesh(geometry, material);
    ridge.position.set(0, -3.4 - layer * 0.6, depth);
    ridge.renderOrder = -1 + layer * 0.01;
    group.add(ridge);
  }
  scene.add(group);
  return group;
}

// Eau. Une nappe lisse renvoie l'environnement comme un miroir de salle de bain :
// il faut une surface qui bouge. Deux calques de normales défilant à des vitesses et
// des échelles différentes suffisent à casser le miroir sans agiter la scène.
function makeWaterMaterial(THREE, options) {
  const { color = 0x0a1b26, mobile = false, roughness = 0.14, ripple = 0.35, repeat = [14, 14] } = options;
  const set = makeSurfaceSet(THREE, "silt", 0x808080, mobile, repeat);
  const normalMap = set.normalMap.clone();
  normalMap.needsUpdate = true;
  normalMap.wrapS = THREE.RepeatWrapping;
  normalMap.wrapT = THREE.RepeatWrapping;
  normalMap.repeat.set(repeat[0], repeat[1]);
  const material = new THREE.MeshPhysicalMaterial({
    color,
    roughness,
    metalness: 0.02,
    normalMap,
    normalScale: new THREE.Vector2(ripple, ripple),
    clearcoat: 1,
    clearcoatRoughness: 0.08,
    envMapIntensity: 1.1,
  });
  material.userData.drift = (time, motion) => {
    normalMap.offset.set(time * 0.0045 * motion, time * 0.0072 * motion);
  };
  return material;
}

// Feuillage : des croix de plans texturés. Une sphère verte lit comme un brocoli ;
// des cartes semi-transparentes laissent passer la lumière et découpent une silhouette.
const FOLIAGE_CACHE = new Map();
function getFoliageTexture(THREE, tint, kind = "leaf") {
  const cacheKey = `${tint}|${kind}`;
  const cached = FOLIAGE_CACHE.get(cacheKey);
  if (cached) return cached;
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, size, size);
  const base = new THREE.Color(tint);
  const leaves = kind === "needle" ? 90 : 46;
  for (let index = 0; index < leaves; index += 1) {
    const x = seeded(index, 11) * size;
    const y = seeded(index, 13) * size;
    const toCentre = Math.hypot(x - size / 2, y - size / 2) / (size * 0.62);
    if (toCentre > 1) continue;
    const angle = seeded(index, 17) * TAU;
    const length = (kind === "needle" ? 9 : 20) * (0.5 + seeded(index, 19));
    const breadth = (kind === "needle" ? 1.6 : 8) * (0.5 + seeded(index, 23));
    const shade = 0.55 + seeded(index, 29) * 0.7;
    const leaf = base.clone().multiplyScalar(shade);
    context.save();
    context.translate(x, y);
    context.rotate(angle);
    context.fillStyle = `rgba(${leaf.r * 255 | 0},${leaf.g * 255 | 0},${leaf.b * 255 | 0},${0.86 - toCentre * 0.42})`;
    context.beginPath();
    context.ellipse(0, 0, length, breadth, 0, 0, TAU);
    context.fill();
    context.restore();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  FOLIAGE_CACHE.set(cacheKey, texture);
  return texture;
}

function makeFoliageMaterial(THREE, tint, kind = "leaf") {
  const texture = getFoliageTexture(THREE, tint, kind);
  // Le découpage vient du canal alpha de la carte de couleur. Passer la même image en
  // `alphaMap` la ferait lire par son canal vert : un feuillage sombre disparaîtrait
  // presque entièrement, un feuillage clair resterait un carré plein.
  return new THREE.MeshStandardMaterial({
    map: texture,
    color: 0xffffff,
    transparent: true,
    alphaTest: 0.28,
    depthWrite: true,
    side: THREE.DoubleSide,
    roughness: 0.88,
    metalness: 0,
  });
}

function makeCrossCardGeometry(THREE) {
  const plane = new THREE.PlaneGeometry(1, 1);
  const second = plane.clone();
  second.rotateY(Math.PI / 2);
  const third = plane.clone();
  third.rotateX(Math.PI / 2.4);
  const merged = new THREE.BufferGeometry();
  const positions = [];
  const normals = [];
  const uvs = [];
  const indices = [];
  let offset = 0;
  for (const part of [plane, second, third]) {
    const position = part.attributes.position;
    const normal = part.attributes.normal;
    const uv = part.attributes.uv;
    for (let index = 0; index < position.count; index += 1) {
      positions.push(position.getX(index), position.getY(index), position.getZ(index));
      normals.push(normal.getX(index), normal.getY(index), normal.getZ(index));
      uvs.push(uv.getX(index), uv.getY(index));
    }
    for (const value of part.index.array) indices.push(value + offset);
    offset += position.count;
    part.dispose();
  }
  merged.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  merged.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  merged.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  merged.setIndex(indices);
  return merged;
}

// Arbre à ramification récursive. Le tronc se divise, les branches s'affinent et
// portent le feuillage à leurs extrémités : la silhouette vient de la structure, pas
// d'une boule posée sur un cylindre.
function buildTree(THREE, options) {
  const {
    height = 9, radius = 0.5, depth = 4, spread = 0.62, lean = 0,
    barkMaterial, foliageMaterial, foliageScale = 1.9, foliageCount = [], seed = 1,
    branchSegments = 7,
  } = options;
  const group = new THREE.Group();
  const tips = [];

  const grow = (start, direction, length, thickness, level, index) => {
    const end = start.clone().addScaledVector(direction, length);
    const branch = new THREE.Mesh(
      new THREE.CylinderGeometry(thickness * 0.66, thickness, length, level === 0 ? branchSegments : 6, 1, true),
      barkMaterial,
    );
    branch.position.copy(start).add(end).multiplyScalar(0.5);
    branch.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
    branch.castShadow = true;
    branch.receiveShadow = true;
    group.add(branch);
    if (level >= depth) {
      tips.push(end.clone());
      return;
    }
    // Les deux derniers niveaux portent aussi du feuillage : une couronne qui ne
    // s'accroche qu'aux extrémités laisse voir le squelette au travers.
    if (level >= depth - 2) tips.push(end.clone());
    const children = level <= 1 ? 3 : 2;
    for (let child = 0; child < children; child += 1) {
      const salt = index * 31 + child * 7 + level * 101 + seed * 13;
      const angle = seeded(salt, 3) * TAU;
      const tilt = spread * (0.55 + seeded(salt, 5) * 0.9);
      const next = direction.clone()
        .addScaledVector(new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle)), tilt)
        .addScaledVector(new THREE.Vector3(0, 1, 0), 0.12)
        .normalize();
      grow(end, next, length * (0.72 + seeded(salt, 7) * 0.16), thickness * 0.66, level + 1, salt);
    }
  };

  grow(
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(lean, 1, lean * 0.4).normalize(),
    height * 0.42,
    radius,
    0,
    seed,
  );

  // Empattement : un tronc qui sort du sol comme un tuyau ne pèse rien. L'évasement
  // de la base est ce qui donne à l'arbre son ancrage.
  const flare = new THREE.Mesh(
    new THREE.CylinderGeometry(radius * 1.04, radius * 1.62, height * 0.2, branchSegments * 2, 3, true),
    barkMaterial,
  );
  // Le pied s'évase en douceur : un cône trop court et trop large fait une pyramide.
  const flarePosition = flare.geometry.attributes.position;
  for (let index = 0; index < flarePosition.count; index += 1) {
    const y = flarePosition.getY(index);
    const t = clamp(0.5 - y / (height * 0.2));
    const pull = 1 + Math.pow(t, 2.6) * 0.5;
    const wobble = 1 + (seeded(index, 401 + seed) - 0.5) * 0.14 * t;
    flarePosition.setX(index, flarePosition.getX(index) * pull * wobble);
    flarePosition.setZ(index, flarePosition.getZ(index) * pull * wobble);
  }
  flare.geometry.computeVertexNormals();
  flare.position.y = height * 0.096;
  flare.castShadow = true;
  flare.receiveShadow = true;
  group.add(flare);

  if (foliageMaterial && tips.length) {
    const count = foliageCount.length ? foliageCount[0] : tips.length * 3;
    const clusters = new THREE.InstancedMesh(makeCrossCardGeometry(THREE), foliageMaterial, count);
    const transform = new THREE.Object3D();
    for (let index = 0; index < count; index += 1) {
      const tip = tips[index % tips.length];
      const salt = index * 17 + seed * 3;
      transform.position.set(
        tip.x + (seeded(salt, 41) - 0.5) * foliageScale * 0.9,
        tip.y + (seeded(salt, 43) - 0.5) * foliageScale * 0.7,
        tip.z + (seeded(salt, 47) - 0.5) * foliageScale * 0.9,
      );
      const scale = foliageScale * (0.6 + seeded(salt, 53) * 0.8);
      transform.scale.set(scale, scale * 0.82, scale);
      transform.rotation.set(0, seeded(salt, 59) * TAU, (seeded(salt, 61) - 0.5) * 0.5);
      transform.updateMatrix();
      clusters.setMatrixAt(index, transform.matrix);
    }
    clusters.castShadow = true;
    clusters.receiveShadow = true;
    group.add(clusters);
  }
  group.userData.tips = tips;
  return group;
}

// ---------------------------------------------------------------------------
// Assemblage d'une scène
// ---------------------------------------------------------------------------
function createPack(THREE, key, palette, mobile, environmentTexture) {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(palette.fog, palette.fogDensity);
  scene.environment = environmentTexture;
  scene.environmentIntensity = palette.environmentIntensity ?? 0.6;
  const camera = new THREE.PerspectiveCamera(mobile ? 46 : 38, 1, 0.1, 170);
  camera.position.set(0, mobile ? 4.1 : 4.6, mobile ? 14.8 : 16.4);
  const target = new THREE.Vector3(0, 1.3, -7.8);

  const sky = makeSky(THREE, palette.sky);
  scene.add(sky.mesh);

  // Le soleil de la scène et celui du ciel sont le même astre.
  const sunDirection = new THREE.Vector3().copy(palette.sun || new THREE.Vector3(-0.45, 0.42, -0.6)).normalize();
  sky.uniforms.sunDirection.value.copy(sunDirection);

  const hemisphere = new THREE.HemisphereLight(palette.sky.zenith, palette.groundLight, palette.hemisphere ?? 0.9);
  const keyLight = new THREE.DirectionalLight(palette.sky.sun || 0xfff0d6, palette.keyIntensity ?? 3.2);
  keyLight.position.copy(sunDirection).multiplyScalar(42);
  configureShadow(keyLight, mobile, palette.shadowExtent ?? 26);
  // Lumière de remplissage à contre-jour : elle détache les silhouettes du fond
  // au lieu de les y coller.
  const rimLight = new THREE.DirectionalLight(palette.rimColor || 0x9fc0e8, palette.rimIntensity ?? 0.55);
  rimLight.position.set(-sunDirection.x * 30, 12, -sunDirection.z * 30);
  scene.add(hemisphere, keyLight, keyLight.target, rimLight);

  return {
    key,
    palette,
    scene,
    camera,
    target,
    sky,
    sunDirection,
    hemisphere,
    keyLight,
    rimLight,
    textures: [],
    particles: [],
    // Réglages du compositeur propres à la scène : c'est là que se joue l'air.
    grade: {
      fogColor: new THREE.Color(palette.fog),
      fogSunColor: new THREE.Color(palette.fogSun || palette.sky.sun || 0xffd9a6),
      fogDensity: palette.airDensity ?? 0.018,
      fogHeight: palette.airHeight ?? 7,
      fogFloor: palette.airFloor ?? -1.5,
      bloomStrength: palette.bloom ?? 0.4,
      shaftStrength: palette.shafts ?? 0,
      exposure: palette.exposure ?? 1,
      vignette: palette.vignette ?? 0.46,
      grain: palette.grain ?? 0.026,
      chroma: palette.chroma ?? 0.32,
      saturation: palette.saturation ?? 1.05,
      lift: new THREE.Color(palette.lift || 0x080d14),
      gain: new THREE.Color(palette.gain || 0xfff7ee),
    },
    update: () => {},
  };
}

// L'environnement est capté depuis le ciel de la scène : les reflets d'une surface
// mouillée renvoient alors ce ciel-là, et non un studio générique. C'est un des
// points où le décor et les objets se mettent d'accord.
function captureEnvironment(THREE, renderer, pack, palette) {
  const stage = new THREE.Scene();
  const dome = new THREE.Mesh(pack.sky.mesh.geometry, pack.sky.material);
  dome.frustumCulled = false;
  stage.add(dome);
  const uniforms = pack.sky.uniforms;
  uniforms.envMode.value = 1;
  const floor = new THREE.Mesh(
    new THREE.SphereGeometry(118, 24, 12, 0, TAU, Math.PI / 2, Math.PI / 2),
    new THREE.MeshBasicMaterial({ color: palette.groundLight, side: THREE.BackSide }),
  );
  stage.add(floor);
  const generator = new THREE.PMREMGenerator(renderer);
  const target = generator.fromScene(stage, 0.05);
  generator.dispose();
  uniforms.envMode.value = 0;
  floor.geometry.dispose();
  floor.material.dispose();
  pack.environmentTarget?.dispose();
  pack.environmentTarget = target;
  pack.scene.environment = target.texture;
}

// ---------------------------------------------------------------------------
// Les univers
// ---------------------------------------------------------------------------
function buildStarTree(THREE, mobile, environmentTexture) {
  const palette = {
    fog: 0x11283a,
    fogDensity: 0.009,
    groundLight: 0x0b1a26,
    // La nuit n'est pas noire : la voûte entière éclaire faiblement. Sans cette
    // lumière d'ambiance, tout ce qui n'est pas sous la lanterne disparaît.
    hemisphere: 0.95,
    keyIntensity: 0.9,
    rimColor: 0x7fa8dc,
    rimIntensity: 0.9,
    sun: new THREE.Vector3(-0.5, 0.16, -0.75),
    environmentIntensity: 0.9,
    airDensity: 0.026,
    airHeight: 5.5,
    airFloor: -1.6,
    bloom: 0.72,
    exposure: 1.18,
    vignette: 0.56,
    grain: 0.03,
    saturation: 1.04,
    lift: 0x0a1220,
    gain: 0xf4f2ff,
    sky: {
      zenith: 0x01030a, horizon: 0x0a2033, ground: 0x02060c, sun: 0x7fa8d4,
      cloudCover: 0.26, cloudSharpness: 0.8, cloudStretch: 1.6, cloudHeight: 0.2,
      cloudLight: 0x1d2f42, cloudDark: 0x060c15,
      haze: 0.34, stars: 1.15, galaxy: 0.9, sunDisc: 0.1,
    },
  };
  const pack = createPack(THREE, "arbre_etoiles", palette, mobile, environmentTexture);
  const { scene } = pack;
  // La caméra est basse et le regard porté haut : l'horizon descend, le ciel occupe
  // la moitié supérieure et l'arbre a la place de se déployer.
  pack.camera.position.set(0, mobile ? 2.9 : 3.2, mobile ? 15.0 : 16.6);
  pack.target.set(0.4, 3.4, -12);

  // Le bassin : une eau presque immobile, très réfléchissante. C'est elle qui double
  // le ciel et qui donne à la scène sa profondeur.
  const waterMaterial = makeWaterMaterial(THREE, {
    color: 0x061119, mobile, roughness: 0.1, ripple: 0.22, repeat: [26, 26],
  });
  const water = new THREE.Mesh(new THREE.PlaneGeometry(220, 220, 1, 1), waterMaterial);
  water.rotation.x = -Math.PI / 2;
  water.position.set(0, -1.45, -34);
  water.receiveShadow = true;
  scene.add(water);

  const stoneMaterial = surfaceMaterial(THREE, {
    preset: "rock", color: 0x1c2a28, mobile, span: [30, 22], tile: 3.4, normalScale: 1.5,
  });
  // L'île émerge à peine : une berge basse, mangée par la brume, qui pose l'arbre sur
  // quelque chose de solide sans découper une plate-forme géométrique dans l'eau.
  const island = shadowed(new THREE.Mesh(
    makeTerrain(THREE, 30, 22, 56, 44, (x, z) => {
      const toCentre = Math.hypot(x * 0.46, (z + 1) * 0.58) / 6.4;
      const dome = Math.pow(clamp(1.05 - toCentre), 1.9) * 1.9;
      const relief = fbm(x * 0.13 + 4, z * 0.13, 4, 2) * 0.5 * clamp(1.3 - toCentre);
      return dome + relief - 1.58;
    }),
    stoneMaterial,
  ), false);
  island.position.set(2.4, 0, -18);
  scene.add(island);

  addDistantRidges(THREE, scene, {
    color: 0x0c1a27, layers: 3, distance: -76, spacing: 28, height: 11, seed: 3.4,
  });

  const slabMaterial = surfaceMaterial(THREE, {
    preset: "stone", color: 0x2b3238, mobile, repeat: [3, 3], normalScale: 0.8,
    physical: true, clearcoat: 0.2, clearcoatRoughness: 0.6,
  });
  addPedestal(THREE, pack, {
    position: new THREE.Vector3(0, -0.74, -3.4), radius: 4.75, height: 0.66,
    material: slabMaterial, mobile,
    fillColor: 0xffcf92, fillIntensity: 6, rimColor: 0x9fc2ee, rimIntensity: 3.0,
  });

  const barkMaterial = surfaceMaterial(THREE, {
    preset: "bark", color: 0x2a1d14, mobile, repeat: [2, 4], normalScale: 1.8,
  });
  const foliageMaterial = makeFoliageMaterial(THREE, 0x3d5a44);
  const tree = buildTree(THREE, {
    height: 13.5, radius: 0.62, depth: 5, spread: 0.74, lean: 0.05,
    barkMaterial, foliageMaterial, foliageScale: 2.9, foliageCount: [mobile ? 150 : 340], seed: 7,
  });
  tree.position.set(2.9, 0.5, -17.5);
  scene.add(tree);

  // Les étoiles de l'arbre : de vraies sources ponctuelles suspendues au feuillage,
  // reprises par le halo du compositeur.
  const lanternGeometry = new THREE.SphereGeometry(0.075, 8, 6);
  const lanternMaterial = new THREE.MeshBasicMaterial({ color: 0xffe0a8 });
  const tips = tree.userData.tips || [];
  const lanterns = new THREE.InstancedMesh(lanternGeometry, lanternMaterial, mobile ? 60 : 130);
  const transform = new THREE.Object3D();
  for (let index = 0; index < lanterns.count; index += 1) {
    const tip = tips[index % Math.max(1, tips.length)] || new THREE.Vector3();
    transform.position.set(
      tree.position.x + tip.x + (seeded(index, 71) - 0.5) * 2.4,
      tree.position.y + tip.y + (seeded(index, 73) - 0.5) * 1.9,
      tree.position.z + tip.z + (seeded(index, 79) - 0.5) * 2.4,
    );
    const scale = 0.6 + seeded(index, 83) * 1.1;
    transform.scale.setScalar(scale);
    transform.updateMatrix();
    lanterns.setMatrixAt(index, transform.matrix);
  }
  scene.add(lanterns);

  const canopyLight = new THREE.PointLight(0xffca7d, 46, 34, 2);
  canopyLight.position.set(3.0, 6.6, -17);
  scene.add(canopyLight);
  const moonFill = new THREE.DirectionalLight(0x9fc2ee, 1.6);
  moonFill.position.set(-18, 16, -6);
  scene.add(moonFill);
  // La lune elle-même, posée dans le champ : une source visible ancre la lumière
  // au lieu de la faire venir de nulle part.
  const moon = new THREE.Mesh(
    new THREE.SphereGeometry(2.2, 32, 20),
    new THREE.MeshBasicMaterial({ color: 0xdce8ff }),
  );
  moon.position.set(-34, 17, -74);
  scene.add(moon);

  // Brume sur l'eau : elle sépare l'île de son reflet et empêche la nappe noire.
  const mist = makeParticles(THREE, mobile ? 120 : 280, { x: [-26, 26], y: [-1.3, 1.4], z: [-46, -4] }, 0x9fc6dd, 0.55, 0.1, 71);
  scene.add(mist.points);
  pack.particles.push(mist);
  const fireflies = makeParticles(THREE, mobile ? 60 : 150, { x: [-14, 16], y: [-0.6, 8], z: [-26, -2] }, 0xffd9a0, 0.11, 0.5, 97);
  scene.add(fireflies.points);
  pack.particles.push(fireflies);

  pack.update = (time, state, motion) => {
    // La nuit s'approfondit avec la session : le ciel se ferme, l'arbre s'allume.
    const deepening = state.elapsed;
    pack.sky.uniforms.time.value = time;
    pack.sky.uniforms.starStrength.value = 1.0 + deepening * 0.5;
    pack.sky.uniforms.galaxyStrength.value = 0.75 + deepening * 0.55;
    pack.sky.uniforms.cloudCover.value = 0.32 - deepening * 0.14;
    canopyLight.intensity = 20 + deepening * 22;
    lanternMaterial.color.setRGB(1, 0.86 - deepening * 0.06, 0.64 + deepening * 0.08);
    pack.grade.bloomStrength = 0.66 + deepening * 0.3;
    pack.grade.fogDensity = 0.024 + deepening * 0.012;
    waterMaterial.userData.drift(time, motion);
    mist.points.position.x = Math.sin(time * 0.04) * 1.6 * motion;
    fireflies.points.position.y = Math.sin(time * 0.19) * 0.28 * motion;
    fireflies.points.rotation.y = time * 0.008 * motion;
  };
  return pack;
}

// Pluie sur une vitre. Les gouttes se forment, grossissent, puis dévalent en laissant
// une traînée : c'est ce cycle qui rend une pluie crédible, bien plus que des traits
// qui défilent.
function makeRainMaterial(THREE) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: {
      time: { value: 0 },
      strength: { value: 0.7 },
    },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      varying vec2 vUv;
      uniform float time;
      uniform float strength;
      float hash21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }

      // Une colonne de cellules : chaque cellule porte une goutte qui descend à sa
      // propre vitesse et laisse derrière elle une traînée qui s'estompe. La goutte
      // reste petite — une perle large et ronde ne lit plus comme de la pluie mais
      // comme de la neige collée au carreau.
      float drops(vec2 uv, vec2 grid, float speed, float seedOffset, float size){
        vec2 cell = floor(uv * grid);
        vec2 local = fract(uv * grid);
        float seed = hash21(cell + seedOffset);
        if (seed < 0.84) return 0.0;
        float pace = speed * (0.5 + seed * 1.1);
        float fall = fract(seed * 7.3 - time * pace);
        vec2 centre = vec2(0.25 + seed * 0.5, fall);
        vec2 offset = (local - centre) * vec2(1.0, 2.6);
        float bead = smoothstep(size, size * 0.2, length(offset));
        // La traînée part de la goutte et remonte : c'est le chemin déjà parcouru.
        float above = local.y - centre.y;
        float trail = smoothstep(size * 0.7, 0.0, abs(local.x - centre.x))
                    * smoothstep(0.0, 0.05, above) * smoothstep(0.62, 0.06, above);
        return max(bead, trail * 0.5);
      }

      void main(){
        float water = drops(vUv, vec2(37.0, 19.0), 0.20, 0.0, 0.17) * 0.9
                    + drops(vUv, vec2(23.0, 11.0), 0.11, 17.0, 0.21) * 1.0
                    + drops(vUv, vec2(71.0, 34.0), 0.31, 41.0, 0.2) * 0.5
                    + drops(vUv, vec2(44.0, 21.0), 0.16, 83.0, 0.15) * 0.7;
        float alpha = clamp(water, 0.0, 1.0) * strength;
        gl_FragColor = vec4(vec3(0.78, 0.86, 0.94), alpha);
      }
    `,
  });
}

function buildRainRefuge(THREE, mobile, environmentTexture) {
  const palette = {
    fog: 0x1a222c,
    fogDensity: 0.006,
    groundLight: 0x1a120c,
    hemisphere: 0.5,
    keyIntensity: 0.35,
    rimColor: 0x8fb0cc,
    rimIntensity: 0.4,
    sun: new THREE.Vector3(-0.3, 0.3, -0.9),
    environmentIntensity: 0.55,
    fogSun: 0xffc98a,
    airDensity: 0.012,
    airHeight: 9,
    airFloor: -2,
    bloom: 0.5,
    exposure: 1.42,
    vignette: 0.6,
    grain: 0.03,
    saturation: 1.02,
    lift: 0x0d1219,
    gain: 0xfff3e4,
    sky: {
      zenith: 0x0d151f, horizon: 0x2b3a49, ground: 0x0a0d11, sun: 0x8fa6bb,
      cloudCover: 0.86, cloudSharpness: 0.6, cloudStretch: 1.2, cloudHeight: 0.24,
      cloudLight: 0x3b4a5b, cloudDark: 0x141b24,
      haze: 0.85, stars: 0, galaxy: 0, sunDisc: 0,
    },
  };
  const pack = createPack(THREE, "refuge_pluie", palette, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 3.4 : 3.8, mobile ? 13.6 : 15.0);
  pack.target.set(0, 2.6, -8);

  const wallMaterial = surfaceMaterial(THREE, {
    preset: "plaster", color: 0x2a2a2c, mobile, repeat: [3, 3], normalScale: 0.7,
  });
  for (const [x, y, width, height] of [
    [-10.4, 5.1, 3.0, 17], [11.35, 5.1, 1.9, 17],
    [0.8, 12.4, 19, 4.0], [0.8, -1.5, 19, 3.0],
  ]) {
    const section = shadowed(new THREE.Mesh(new THREE.BoxGeometry(width, height, 0.45), wallMaterial), false);
    section.position.set(x, y, -13.2);
    scene.add(section);
  }
  const sideWall = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.6, 18, 30), wallMaterial), false);
  sideWall.position.set(-11.9, 4.7, -1.5);
  scene.add(sideWall);
  const ceiling = shadowed(new THREE.Mesh(new THREE.BoxGeometry(26, 0.6, 30), wallMaterial), false);
  ceiling.position.set(0, 11.4, -1.5);
  scene.add(ceiling);
  // Plancher : il attrape la lumière de la lampe et renvoie la fenêtre. Sans sol, la
  // pièce n'a pas de bas et le bureau flotte.
  const floorMaterial = surfaceMaterial(THREE, {
    preset: "wood", color: 0x2c1b11, mobile, span: [30, 34], tile: 3.2, normalScale: 0.8,
    physical: true, clearcoat: 0.4, clearcoatRoughness: 0.55, envMapIntensity: 0.5,
  });
  const floor = shadowed(new THREE.Mesh(new THREE.PlaneGeometry(30, 34), floorMaterial), false);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, -4.6, -2);
  scene.add(floor);

  // La ville : des volumes de profondeurs variées, avalés par la pluie. Une rangée de
  // boîtes alignées à la même distance se lit comme un décor peint.
  const cityMaterial = new THREE.MeshStandardMaterial({ color: 0x141c24, roughness: 0.95, metalness: 0 });
  const windowMaterials = [0xffb865, 0xe8964a, 0xffd79a, 0x8fc4e2, 0x6d9ab8].map(
    (color, index) => new THREE.MeshBasicMaterial({
      color, transparent: true, opacity: 0.16 + index * 0.06, depthWrite: false,
    }),
  );
  for (let index = 0; index < (mobile ? 20 : 34); index += 1) {
    const width = 1.4 + seeded(index, 83) * 3.2;
    const height = 3 + seeded(index, 89) * 12;
    const depth = -15 - seeded(index, 91) * 26;
    const building = new THREE.Mesh(new THREE.BoxGeometry(width, height, width * 0.9), cityMaterial);
    building.position.set(-17 + seeded(index, 93) * 34, -3.4 + height / 2, depth);
    scene.add(building);
    const floors = Math.max(2, Math.round(height / 1.5));
    for (let level = 0; level < floors; level += 1) {
      if (seeded(index * 31 + level, 97) < 0.62) continue;
      const columns = 2 + Math.round(seeded(index * 7 + level, 103) * 2);
      for (let column = 0; column < columns; column += 1) {
        if (seeded(index * 53 + level * 11 + column, 107) < 0.45) continue;
        const pane = new THREE.Mesh(
          new THREE.PlaneGeometry(width * 0.13, 0.26),
          windowMaterials[Math.floor(seeded(index * 17 + level * 5 + column, 101) * windowMaterials.length)],
        );
        pane.position.set(
          building.position.x + (column / (columns - 1 || 1) - 0.5) * width * 0.62,
          -3.2 + level * 1.5 + 0.4,
          depth + width * 0.46,
        );
        scene.add(pane);
      }
    }
  }

  const windowGlass = new THREE.Mesh(
    new THREE.PlaneGeometry(19, 11.5),
    new THREE.MeshPhysicalMaterial({
      color: 0x9ab3c0,
      transparent: true,
      opacity: 0.1,
      transmission: 0.24,
      roughness: 0.16,
      metalness: 0.05,
      clearcoat: 1,
      depthWrite: false,
    }),
  );
  windowGlass.position.set(0.8, 5.4, -11.65);
  scene.add(windowGlass);
  const rainMaterial = makeRainMaterial(THREE);
  const rain = new THREE.Mesh(new THREE.PlaneGeometry(19, 11.5), rainMaterial);
  rain.position.set(0.8, 5.4, -11.5);
  rain.renderOrder = 2;
  scene.add(rain);

  const frameMaterial = new THREE.MeshPhysicalMaterial({ color: 0x121314, metalness: 0.7, roughness: 0.34, clearcoat: 0.4 });
  for (const [x, y, width, height] of [
    [-8.8, 5.4, 0.34, 12.1], [10.4, 5.4, 0.34, 12.1], [0.8, 5.4, 0.28, 12.1],
    [0.8, 11.1, 19.5, 0.36], [0.8, -0.3, 19.5, 0.36], [0.8, 5.4, 19.5, 0.26],
  ]) {
    const frame = shadowed(new THREE.Mesh(new THREE.BoxGeometry(width, height, 0.3), frameMaterial));
    frame.position.set(x, y, -11.32);
    scene.add(frame);
  }
  // Tablette de fenêtre : la lumière du dehors y meurt, ce qui pose la profondeur
  // du mur et distingue l'intérieur de l'extérieur.
  const sill = shadowed(new THREE.Mesh(new THREE.BoxGeometry(20, 0.4, 1.3), wallMaterial));
  sill.position.set(0.8, -0.6, -11);
  scene.add(sill);

  const deskMaterial = surfaceMaterial(THREE, {
    preset: "wood", color: 0x4a2c1a, mobile, repeat: [5, 2], normalScale: 0.6,
    physical: true, clearcoat: 0.45, clearcoatRoughness: 0.34, envMapIntensity: 0.7,
  });
  const desk = shadowed(new THREE.Mesh(new THREE.BoxGeometry(17.5, 0.5, 8.5), deskMaterial));
  desk.position.set(0, -0.45, -2.7);
  scene.add(desk);
  for (const x of [-6.7, 6.7]) {
    const leg = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.6, 4.1, 1.0), deskMaterial));
    leg.position.set(x, -2.55, -2.9);
    scene.add(leg);
  }
  addContactShadow(THREE, pack, new THREE.Vector3(0, -0.18, -3), [7.6, 3.4], 0.62);

  // Un bureau habité : quelques volumes discrets, jamais au centre. Une pièce vide
  // n'est pas calme, elle est inhabitée.
  const paperMaterial = new THREE.MeshStandardMaterial({ color: 0xbfb098, roughness: 0.94 });
  const bookMaterials = [0x5c3524, 0x2f4636, 0x3c3550, 0x6a4a22].map(
    (color) => new THREE.MeshStandardMaterial({ color, roughness: 0.88 }),
  );
  const stack = new THREE.Group();
  for (let index = 0; index < 4; index += 1) {
    const book = shadowed(new THREE.Mesh(
      new THREE.BoxGeometry(1.9 - index * 0.1, 0.26, 1.4 - index * 0.06),
      bookMaterials[index % bookMaterials.length],
    ));
    book.position.set(6.1 + (seeded(index, 107) - 0.5) * 0.18, -0.06 + index * 0.27, -3.6);
    book.rotation.y = (seeded(index, 109) - 0.5) * 0.24;
    stack.add(book);
  }
  scene.add(stack);
  const sheets = shadowed(new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.05, 1.9), paperMaterial));
  sheets.position.set(-3.2, -0.17, -1.4);
  sheets.rotation.y = 0.16;
  scene.add(sheets);
  const mug = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.34, 0.62, 20), new THREE.MeshStandardMaterial({ color: 0x2a3438, roughness: 0.52 })));
  mug.position.set(-5.4, 0.11, -1.2);
  scene.add(mug);

  const metal = new THREE.MeshPhysicalMaterial({ color: 0x6d5230, metalness: 0.8, roughness: 0.32, clearcoat: 0.4 });
  const stem = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.13, 3.7, 16), metal));
  stem.position.set(-5.25, 1.75, -4.1);
  scene.add(stem);
  const shade = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(0.66, 1.3, 1.1, 28, 1, true),
    new THREE.MeshPhysicalMaterial({
      color: 0x6b4429, roughness: 0.6, side: THREE.DoubleSide,
      emissive: 0xffb768, emissiveIntensity: 0.08,
    }),
  ));
  shade.position.set(-5.25, 3.5, -4.1);
  scene.add(shade);
  const lamp = new THREE.PointLight(0xffbd72, 40, 20, 2);
  lamp.position.set(-5.25, 2.95, -3.55);
  lamp.castShadow = true;
  lamp.shadow.mapSize.set(mobile ? 512 : 1024, mobile ? 512 : 1024);
  lamp.shadow.bias = -0.002;
  scene.add(lamp);
  // Le cône de lumière lui-même, tenu par la poussière. C'est ce volume visible qui
  // fait qu'une lampe éclaire une pièce au lieu de poser une tache sur une table.
  // Le cône n'a pas de contour : il s'éteint sur ses bords et vers le bas. Une
  // opacité constante montre l'arête du volume, et le faisceau devient un objet
  // solide posé sous la lampe.
  const beamMaterial = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    uniforms: {
      color: { value: new THREE.Color(0xffc880) },
      strength: { value: 0.07 },
    },
    vertexShader: `
      varying vec2 vUv;
      varying vec3 vViewNormal;
      void main(){
        vUv = uv;
        vViewNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      varying vec3 vViewNormal;
      uniform vec3 color;
      uniform float strength;
      void main(){
        // L'épaisseur d'air traversée est maximale au cœur du faisceau.
        float thickness = pow(abs(vViewNormal.z), 1.4);
        float fall = smoothstep(0.0, 0.5, vUv.y) * smoothstep(1.05, 0.55, vUv.y);
        gl_FragColor = vec4(color, thickness * fall * strength);
      }
    `,
  });
  const beam = new THREE.Mesh(new THREE.ConeGeometry(3.1, 4.4, 32, 12, true), beamMaterial);
  beam.position.set(-5.25, 1.5, -4.0);
  beam.renderOrder = 2;
  scene.add(beam);

  const dust = makeParticles(THREE, mobile ? 150 : 340, { x: [-9, 6], y: [-0.4, 7], z: [-9, 2] }, 0xffdcb0, 0.06, 0.42, 103);
  scene.add(dust.points);
  pack.particles.push(dust);

  pack.update = (time, state, motion) => {
    // La session avance : le dehors s'éteint, la lampe prend toute la pièce.
    const evening = state.elapsed;
    pack.sky.uniforms.time.value = time;
    pack.sky.uniforms.cloudCover.value = 0.82 + evening * 0.12;
    pack.keyLight.intensity = 0.4 - evening * 0.22;
    pack.hemisphere.intensity = 0.55 - evening * 0.28;
    lamp.intensity = 34 + evening * 22 + Math.sin(time * 1.3) * 0.5 * motion;
    beamMaterial.uniforms.strength.value = 0.06 + evening * 0.07;
    shade.material.emissiveIntensity = 0.07 + evening * 0.1;
    rainMaterial.uniforms.time.value = time * motion;
    rainMaterial.uniforms.strength.value = 0.4 + state.density * 0.18;
    pack.grade.exposure = 1.42 - evening * 0.1;
    pack.grade.fogDensity = 0.011 + evening * 0.006;
    dust.points.rotation.y = time * 0.012 * motion;
    dust.points.position.y = Math.sin(time * 0.15) * 0.14 * motion;
  };
  return pack;
}

// Forêt. Une seule construction porte cinq états : la futaie ancienne et les quatre
// saisons. Les différences sont réelles — densité, feuillage, sol, lumière, ce qui
// tombe dans l'air — et non un simple changement de teinte du ciel.
const FOREST_SEASONS = {
  foret: {
    trunkColor: 0x30231a, groundColor: 0x223020, groundPreset: "moss",
    foliage: 0x24401f, foliageDensity: 1, trunkScale: 1.45, trunkCount: 1,
    litter: 0x18241a, understory: 0x27412a,
    sky: {
      zenith: 0x3f7ba8, horizon: 0xc4cfae, ground: 0x1b2a18, sun: 0xfff2cc,
      cloudCover: 0.44, cloudSharpness: 1.4, cloudStretch: 1.1, cloudHeight: 0.14,
      cloudLight: 0xfffbee, cloudDark: 0x8d9a8c, haze: 0.6, stars: 0, sunDisc: 0.7,
    },
    sun: [-0.42, 0.34, -0.86], fog: 0x5a6b56, fogDensity: 0.0075, air: 0.0105,
    key: 6.2, hemi: 0.92, shafts: 1.5, exposure: 0.9, saturation: 1.1,
    particleColor: 0xd8ecb4, particleSize: 0.07, particleOpacity: 0.28,
  },
};

function buildForest(THREE, mobile, environmentTexture, key = "foret") {
  const season = FOREST_SEASONS[key] || FOREST_SEASONS.foret;
  const ancient = key === "foret";
  const palette = {
    fog: season.fog,
    fogDensity: season.fogDensity,
    groundLight: season.groundColor,
    hemisphere: season.hemi,
    keyIntensity: season.key,
    rimColor: 0xcfe4ff,
    rimIntensity: 0.7,
    sun: new THREE.Vector3(...season.sun),
    environmentIntensity: 0.7,
    fogSun: season.sky.sun,
    airDensity: season.air,
    airHeight: ancient ? 9 : 7,
    airFloor: -1.4,
    bloom: 0.4,
    shafts: season.shafts,
    exposure: season.exposure,
    vignette: 0.58,
    grain: 0.026,
    saturation: season.saturation,
    shadowExtent: 30,
    sky: season.sky,
  };
  const pack = createPack(THREE, key, palette, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 3.4 : 3.8, mobile ? 15.0 : 16.4);
  pack.target.set(0, ancient ? 4.6 : 3.2, -10);

  const groundMaterial = surfaceMaterial(THREE, {
    preset: season.groundPreset, color: season.groundColor, mobile,
    span: [90, 110], tile: 3.4, normalScale: 1.3,
  });
  const ground = shadowed(new THREE.Mesh(
    makeTerrain(THREE, 90, 110, 90, 100, (x, z) => (
      fbm(x * 0.055, z * 0.055, 4, 2) * 1.5
      + ridged(x * 0.02 + 3, z * 0.02, 3, 2) * 0.9
      - 1.5
    )),
    groundMaterial,
  ), false);
  ground.position.set(0, 0, -22);
  scene.add(ground);

  const slabMaterial = surfaceMaterial(THREE, {
    preset: "stone", color: ancient ? 0x3b4740 : 0x50554e, mobile, repeat: [3, 3],
    normalScale: 0.9, physical: true, clearcoat: 0.18, clearcoatRoughness: 0.6,
  });
  addPedestal(THREE, pack, {
    position: new THREE.Vector3(0, -0.78, -3.4), radius: 4.75, height: 0.64,
    material: slabMaterial, mobile,
    fillColor: 0xfff0c8, fillIntensity: 7, rimColor: 0xa8c9a0, rimIntensity: 2.4,
  });

  const barkMaterial = surfaceMaterial(THREE, {
    preset: "bark", color: season.trunkColor, mobile, repeat: [3, 13], normalScale: 2.2,
  });
  const foliageMaterial = makeFoliageMaterial(THREE, season.foliage, ancient ? "needle" : "leaf");
  const trunkCount = Math.round((mobile ? 12 : 20) * season.trunkCount);
  for (let index = 0; index < trunkCount; index += 1) {
    const side = index % 2 ? 1 : -1;
    const x = side * (5.2 + seeded(index, 121) * 17);
    const z = 2 - seeded(index, 127) * 52;
    const near = z > -22;
    const scale = season.trunkScale * (near ? 1 : 0.82);
    const tree = buildTree(THREE, {
      height: (ancient ? 30 : 17) * scale * (0.75 + seeded(index, 131) * 0.5),
      radius: (ancient ? 1.15 : 0.5) * scale * (0.7 + seeded(index, 137) * 0.6),
      depth: ancient ? 3 : 4,
      spread: ancient ? 0.34 : 0.72,
      lean: (seeded(index, 139) - 0.5) * 0.07,
      barkMaterial,
      foliageMaterial: season.foliageDensity > 0.05 ? foliageMaterial : null,
      foliageScale: (ancient ? 4.6 : 3.0) * scale,
      foliageCount: [Math.max(6, Math.round((mobile ? 26 : 54) * season.foliageDensity))],
      seed: index + 3,
      branchSegments: 12,
    });
    tree.position.set(x, -1.3 + fbm(x * 0.055, (z + 22) * 0.055, 4, 2) * 1.5, z);
    scene.add(tree);
  }

  // Sous-bois : fougères, herbes, buissons. Un sol nu sous des troncs est un plateau
  // de tournage ; c'est la strate basse qui fait la forêt.
  const understoryMaterial = makeFoliageMaterial(THREE, season.understory, "leaf");
  const understory = new THREE.InstancedMesh(
    makeCrossCardGeometry(THREE), understoryMaterial, mobile ? 130 : 300,
  );
  const transform = new THREE.Object3D();
  for (let index = 0; index < understory.count; index += 1) {
    const side = index % 2 ? 1 : -1;
    const x = side * (4.4 + seeded(index, 149) * 20);
    const z = 3 - seeded(index, 151) * 50;
    transform.position.set(x, -1.5 + fbm(x * 0.055, (z + 22) * 0.055, 4, 2) * 1.5, z);
    const scale = 0.8 + seeded(index, 157) * 1.9;
    transform.scale.set(scale, scale * 0.85, scale);
    transform.rotation.set(0, seeded(index, 163) * TAU, 0);
    transform.updateMatrix();
    understory.setMatrixAt(index, transform.matrix);
  }
  understory.castShadow = false;
  understory.receiveShadow = true;
  scene.add(understory);

  const rockMaterial = surfaceMaterial(THREE, {
    preset: "rock", color: ancient ? 0x333d36 : 0x494f48, mobile, repeat: [2, 2], normalScale: 1.5,
  });
  const rocks = new THREE.InstancedMesh(makeBoulderGeometry(THREE, 2, 1.9, 0.46), rockMaterial, mobile ? 20 : 38);
  for (let index = 0; index < rocks.count; index += 1) {
    const side = index % 2 ? 1 : -1;
    const x = side * (4.6 + seeded(index, 167) * 18);
    const z = 2 - seeded(index, 173) * 42;
    transform.position.set(x, -1.5 + fbm(x * 0.055, (z + 22) * 0.055, 4, 2) * 1.5, z);
    const scale = 0.4 + seeded(index, 179) * 1.6;
    transform.scale.set(scale * 1.3, scale * 0.72, scale);
    transform.rotation.set(seeded(index, 181) * 0.6, seeded(index, 191) * TAU, seeded(index, 193) * 0.5);
    transform.updateMatrix();
    rocks.setMatrixAt(index, transform.matrix);
  }
  rocks.castShadow = true;
  rocks.receiveShadow = true;
  scene.add(rocks);

  const motes = makeParticles(
    THREE, mobile ? 180 : 460,
    { x: [-24, 24], y: [-1.2, 16], z: [-48, 4] },
    season.particleColor, season.particleSize, season.particleOpacity, 181,
  );
  scene.add(motes.points);
  pack.particles.push(motes);

  const falling = key === "automne" || key === "hiver";
  pack.update = (time, state, motion) => {
    pack.sky.uniforms.time.value = time;
    // Le soleil descend au fil de la session : les ombres s'allongent et la lumière
    // se réchauffe. C'est le même astre qui bouge dans le ciel et dans la scène.
    const descent = state.elapsed;
    const elevation = season.sun[1] * (1 - descent * 0.72);
    pack.sunDirection.set(season.sun[0] - descent * 0.22, Math.max(0.03, elevation), season.sun[2]).normalize();
    pack.sky.uniforms.sunDirection.value.copy(pack.sunDirection);
    pack.keyLight.position.copy(pack.sunDirection).multiplyScalar(46);
    pack.keyLight.intensity = season.key * (1 - descent * 0.42);
    pack.keyLight.color.setRGB(1, 0.94 - descent * 0.12, 0.84 - descent * 0.26);
    pack.hemisphere.intensity = season.hemi * (1 - descent * 0.3);
    scene.fog.density = season.fogDensity * (1 + descent * 0.5);
    pack.grade.fogDensity = season.air * (1 + descent * 0.45);
    pack.grade.shaftStrength = season.shafts * (0.6 + descent * 0.7);
    pack.grade.saturation = season.saturation - descent * 0.06;

    if (falling) {
      // Feuilles et flocons tombent réellement, en dérivant sur le côté.
      motes.points.position.y = -((time * (key === "hiver" ? 0.26 : 0.34) * motion) % 6);
      motes.points.position.x = Math.sin(time * 0.16) * 1.4 * motion;
      motes.points.rotation.y = time * 0.01 * motion;
    } else {
      motes.points.position.y = Math.sin(time * 0.14) * 0.3 * motion;
      motes.points.rotation.y = time * 0.005 * motion;
    }
  };
  return pack;
}

// Mer. Le déplacement se fait au sommet, l'écume et le miroitement au pixel. Une
// nappe bleue ridée de sinus se lit comme du plastique gaufré : il faut des crêtes
// qui blanchissent, un chemin de soleil et une profondeur qui assombrit les creux.
function makeOceanMaterial(THREE, colors) {
  return new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 },
      motion: { value: 1 },
      swell: { value: colors.swell ?? 1 },
      foamAmount: { value: colors.foam ?? 0.4 },
      deepColor: { value: new THREE.Color(colors.deep) },
      surfaceColor: { value: new THREE.Color(colors.surface) },
      skyColor: { value: new THREE.Color(colors.sky) },
      lightColor: { value: new THREE.Color(colors.light) },
      sunDirection: { value: new THREE.Vector3(-0.4, 0.4, -0.8).normalize() },
    },
    vertexShader: `
      uniform float time, motion, swell;
      varying float vHeight;
      varying vec3 vWorld;
      varying vec3 vNormal;
      varying vec2 vRipple;

      // Chaque houle rend sa hauteur et sa pente. Dériver la normale de la géométrie
      // interpolée donnerait une facette par triangle — la mer se verrait alors comme
      // une tôle pliée. Ici la pente est exacte en tout point.
      vec3 wave(vec2 p, vec2 direction, float frequency, float speed, float amplitude){
        float phase = dot(p, direction) * frequency + time * speed;
        return vec3(
          sin(phase) * amplitude,
          cos(phase) * amplitude * frequency * direction.x,
          cos(phase) * amplitude * frequency * direction.y
        );
      }

      void main(){
        vec3 p = position;
        vec3 sum = wave(p.xy, normalize(vec2(1.0, 0.35)), 0.15, 0.62, 1.0)
                 + wave(p.xy, normalize(vec2(-0.4, 1.0)), 0.26, 0.51, 0.5)
                 + wave(p.xy, normalize(vec2(0.7, -0.6)), 0.44, 0.83, 0.24)
                 + wave(p.xy, normalize(vec2(-1.0, -0.2)), 0.83, 1.24, 0.1);
        float scale = 0.46 * motion * swell;
        p.z += sum.x * scale;
        vHeight = sum.x;
        vNormal = normalize(vec3(-sum.y * scale, -sum.z * scale, 1.0));
        vRipple = p.xy;
        vec4 world = modelMatrix * vec4(p, 1.0);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }
    `,
    fragmentShader: `
      varying float vHeight;
      varying vec3 vWorld;
      varying vec3 vNormal;
      varying vec2 vRipple;
      uniform float time, foamAmount;
      uniform vec3 deepColor, surfaceColor, skyColor, lightColor, sunDirection;
      float hash21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
      float vnoise(vec2 p){
        vec2 i = floor(p), f = fract(p);
        f = f * f * (3.0 - 2.0 * f);
        return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), f.x),
                   mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), f.x), f.y);
      }

      void main(){
        vec3 viewDirection = normalize(cameraPosition - vWorld);
        // Le plan est couché : la normale de la houle passe en repère monde.
        vec3 normal = normalize(vec3(vNormal.x, vNormal.z, -vNormal.y));

        // Clapot fin. L'échelle est calée sur la distance : de près on voit le détail,
        // de loin il se moyenne, faute de quoi l'horizon se met à grouiller.
        float distance = length(cameraPosition - vWorld);
        float detail = smoothstep(90.0, 18.0, distance);
        vec2 chop = vRipple * 0.5;
        float ripple = (vnoise(chop + time * 0.22) - 0.5)
                     + (vnoise(chop * 2.7 - time * 0.4) - 0.5) * 0.5;
        normal = normalize(normal + vec3(ripple, 0.0, ripple * 0.8) * 0.32 * detail);

        // Fresnel : de face on voit le fond, de biais on voit le ciel. C'est cette
        // bascule qui donne à l'eau son épaisseur.
        float fresnel = pow(1.0 - max(dot(viewDirection, normal), 0.0), 3.2);
        vec3 color = mix(deepColor, surfaceColor, smoothstep(-1.3, 1.5, vHeight) * 0.5 + 0.22);
        color = mix(color, skyColor, clamp(fresnel, 0.0, 1.0) * 0.86);

        // Chemin de soleil : un reflet spéculaire large, éclaté par le clapot.
        vec3 halfway = normalize(sunDirection + viewDirection);
        float specular = max(dot(normal, halfway), 0.0);
        color += lightColor * (pow(specular, 260.0) * 3.2 + pow(specular, 26.0) * 0.14);

        // Écume : uniquement sur les crêtes, et texturée. Une ligne blanche continue
        // se voit comme un trait de peinture.
        float crest = smoothstep(1.0, 1.75, vHeight);
        float lace = smoothstep(0.36, 0.74, vnoise(vRipple * 1.6 + time * 0.3));
        color = mix(color, vec3(0.9, 0.95, 0.98), crest * lace * foamAmount);

        gl_FragColor = vec4(color, 1.0);
      }
    `,
  });
}

function buildOcean(THREE, mobile, environmentTexture) {
  const key = "ocean";
  const palette = {
    fog: 0x93b0c2,
    fogDensity: 0.0042,
    groundLight: 0x3c5460,
    hemisphere: 1.15,
    keyIntensity: 4.4,
    rimColor: 0xbfe0ff,
    rimIntensity: 0.7,
    sun: new THREE.Vector3(-0.55, 0.34, -0.8),
    environmentIntensity: 0.72,
    fogSun: 0xffdcb0,
    airDensity: 0.0085,
    airHeight: 7,
    airFloor: -2.6,
    bloom: 0.46,
    shafts: 1.1,
    exposure: 1.0,
    vignette: 0.44,
    grain: 0.024,
    saturation: 1.06,
    shadowExtent: 30,
    sky: {
      zenith: 0x2d6ea8, horizon: 0xcbd8d4, ground: 0x2f5568, sun: 0xffeec9,
      cloudCover: 0.42, cloudSharpness: 1.6, cloudStretch: 1.1, cloudHeight: 0.12,
      cloudLight: 0xfffdf6, cloudDark: 0x8298ab, haze: 0.78, stars: 0, sunDisc: 1,
    },
  };
  const pack = createPack(THREE, key, palette, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 6.0 : 6.8, mobile ? 15.4 : 17.2);
  pack.target.set(0, 1.0, -18);

  const oceanMaterial = makeOceanMaterial(THREE, {
    deep: 0x073040, surface: 0x2f7f96, sky: 0x9fc4d4, light: 0xfff0d2, swell: 1.15, foam: 0.5,
  });
  oceanMaterial.uniforms.sunDirection.value.copy(pack.sunDirection);
  const ocean = new THREE.Mesh(
    new THREE.PlaneGeometry(240, 240, mobile ? 110 : 190, mobile ? 110 : 190),
    oceanMaterial,
  );
  ocean.rotation.x = -Math.PI / 2;
  ocean.position.set(0, -11.5, -80);
  scene.add(ocean);

  // La corniche : un vrai relief rocheux, strié, et non une boîte. C'est le premier
  // plan qui doit tenir le regard et porter l'objet.
  const rockMaterial = surfaceMaterial(THREE, {
    preset: "cliff", color: 0x554e46, mobile, span: [70, 46], tile: 4.5, normalScale: 1.15,
  });
  const ledge = shadowed(new THREE.Mesh(
    makeTerrain(THREE, 70, 46, 92, 62, (x, z) => {
      // Un plateau presque plat, puis une falaise franche. La rupture doit être nette :
      // c'est elle qui dit la hauteur, et donc l'échelle de toute la scène.
      const strata = ridged(x * 0.07, z * 0.1, 4, 3) * 0.5;
      const cliff = smoothstep(-4.0, -13.0, z) * 15.0;
      const notch = fbm(x * 0.06 + 9, z * 0.03, 3, 2) * 3.4 * smoothstep(-3.0, -11.0, z);
      return strata + fbm(x * 0.04, z * 0.04, 3, 2) * 0.4 - cliff - notch - 0.5;
    }),
    rockMaterial,
  ), false);
  ledge.position.set(0, -0.9, -5);
  scene.add(ledge);

  const slabMaterial = surfaceMaterial(THREE, {
    preset: "stone", color: 0x5b6167, mobile, repeat: [3, 3],
    normalScale: 0.9, physical: true, clearcoat: 0.24, clearcoatRoughness: 0.4,
  });
  addPedestal(THREE, pack, {
    position: new THREE.Vector3(0, -0.34, -3.0), radius: 4.65, height: 0.6,
    material: slabMaterial, mobile,
    fillColor: 0xffe9c4, fillIntensity: 6, rimColor: 0xbfe0ff, rimIntensity: 2.6,
  });

  // Aiguilles marines. Elles ne partagent pas toutes la même forme : trois moules
  // différents suffisent à casser la répétition, que l'œil repère immédiatement.
  const transform = new THREE.Object3D();
  for (let variant = 0; variant < 3; variant += 1) {
    const count = mobile ? 6 : 10;
    const stacks = new THREE.InstancedMesh(makeSeaStackGeometry(THREE, variant * 3.7 + 1.3, mobile), rockMaterial, count);
    for (let index = 0; index < count; index += 1) {
      const salt = index + variant * 29;
      const side = salt % 2 ? 1 : -1;
      const distant = index > count * 0.4;
      const x = side * (distant ? 22 + seeded(salt, 193) * 46 : 14 + seeded(salt, 197) * 11);
      const z = distant ? -44 - seeded(salt, 199) * 62 : -14 - seeded(salt, 211) * 18;
      const scale = distant ? 4.2 + seeded(salt, 223) * 7 : 2.2 + seeded(salt, 227) * 2.8;
      transform.position.set(x, -12.6 + scale * 0.9, z);
      transform.scale.set(scale * 0.9, scale * 1.5, scale * 0.95);
      transform.rotation.set(0, seeded(salt, 233) * TAU, (seeded(salt, 239) - 0.5) * 0.1);
      transform.updateMatrix();
      stacks.setMatrixAt(index, transform.matrix);
    }
    stacks.castShadow = true;
    stacks.receiveShadow = true;
    scene.add(stacks);
  }

  const spray = makeParticles(
    THREE, mobile ? 130 : 340,
    { x: [-40, 40], y: [-11, -3], z: [-80, -14] },
    0xdfeeee, 0.12, 0.2, 241,
  );
  scene.add(spray.points);
  pack.particles.push(spray);

  pack.update = (time, state, motion) => {
    pack.sky.uniforms.time.value = time;
    oceanMaterial.uniforms.time.value = time;
    oceanMaterial.uniforms.motion.value = 0.42 + motion * 0.72;
    oceanMaterial.uniforms.sunDirection.value.copy(pack.sunDirection);

    // Le soleil descend vers l'horizon : la mer passe du turquoise à l'or, les
    // ombres de la falaise s'allongent et l'air s'épaissit au ras de l'eau.
    const descent = state.elapsed;
    const elevation = Math.max(0.02, 0.34 - descent * 0.31);
    pack.sunDirection.set(-0.55 + descent * 0.5, elevation, -0.8).normalize();
    pack.sky.uniforms.sunDirection.value.copy(pack.sunDirection);
    pack.keyLight.position.copy(pack.sunDirection).multiplyScalar(50);
    pack.keyLight.intensity = 4.4 - descent * 2.0;
    pack.keyLight.color.setRGB(1, 0.93 - descent * 0.18, 0.82 - descent * 0.36);
    pack.sky.uniforms.horizonColor.value.setRGB(
      0.8 + descent * 0.2, 0.85 - descent * 0.3, 0.83 - descent * 0.45,
    );
    pack.sky.uniforms.zenithColor.value.setRGB(0.17 - descent * 0.1, 0.43 - descent * 0.28, 0.66 - descent * 0.4);
    oceanMaterial.uniforms.lightColor.value.setRGB(1, 0.94 - descent * 0.2, 0.82 - descent * 0.4);
    pack.hemisphere.intensity = 1.15 - descent * 0.5;
    pack.grade.fogDensity = 0.0085 + descent * 0.006;
    pack.grade.shaftStrength = 1.1 + descent * 0.9;
    spray.points.position.x = Math.sin(time * 0.05) * 1.8 * motion;
  };
  return pack;
}

function buildSahara(THREE, mobile, environmentTexture) {
  const palette = {
    fog: 0xc08a5e,
    fogDensity: 0.012,
    groundLight: 0x6b4028,
    hemisphere: 1.5,
    keyIntensity: 5.4,
    rimColor: 0x9fbede,
    rimIntensity: 0.5,
    sun: new THREE.Vector3(-0.7, 0.26, -0.66),
    environmentIntensity: 1.0,
    fogSun: 0xffc887,
    airDensity: 0.02,
    airHeight: 9,
    airFloor: -1.2,
    bloom: 0.52,
    shafts: 0.8,
    exposure: 1.0,
    vignette: 0.46,
    grain: 0.028,
    saturation: 1.08,
    shadowExtent: 62,
    sky: {
      zenith: 0x2f6ba0, horizon: 0xe8b47e, ground: 0x8a5433, sun: 0xffe3b0,
      cloudCover: 0.36, cloudSharpness: 2.4, cloudStretch: 2.6, cloudHeight: 0.08,
      cloudLight: 0xfff2df, cloudDark: 0xc0a08c, haze: 0.82, stars: 0, sunDisc: 1,
    },
  };
  const pack = createPack(THREE, "sahara", palette, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0.2, mobile ? 3.6 : 4.0, mobile ? 14.6 : 16.0);
  pack.target.set(0.4, 1.4, -14);

  // Les dunes : de vraies formes de vent — longue montée au vent, rupture sous le
  // vent. Le relief porte en plus ses rides, par la carte de normales.
  const duneHeight = (x, z) => {
    const long = Math.sin(x * 0.062 + z * 0.04) * 2.1;
    const cross = Math.sin(x * 0.038 - z * 0.082 + 1.7) * 1.1;
    const crest = Math.pow(0.5 + 0.5 * Math.sin(x * 0.1 + z * 0.055 + 0.8), 3.4) * 2.2;
    return long + cross + crest + fbm(x * 0.035, z * 0.035, 4, 2) * 1.1 - 1.4;
  };
  const sandMaterial = surfaceMaterial(THREE, {
    preset: "sand", color: 0xc78a4e, mobile, span: [180, 210], tile: 9, normalScale: 1.0,
    physical: true, clearcoat: 0.05, sheen: 0.4, sheenColor: new THREE.Color(0xffd9a0),
  });
  const dunes = shadowed(new THREE.Mesh(
    makeTerrain(THREE, 180, 210, mobile ? 110 : 190, mobile ? 130 : 220, duneHeight),
    sandMaterial,
  ), false);
  dunes.position.z = -50;
  scene.add(dunes);
  // Hauteur du sable sous un point exprimé dans le repère de la scène. Le maillage est
  // décalé de cinquante unités : sans cette conversion, tout ce qu'on y pose se
  // retrouve enfoui ou en lévitation.
  const sandHeight = (x, z) => duneHeight(x, z + 50);

  const stoneMaterial = surfaceMaterial(THREE, {
    preset: "rock", color: 0x6d5340, mobile, repeat: [3, 3], normalScale: 1.5,
  });
  addPedestal(THREE, pack, {
    position: new THREE.Vector3(0, sandHeight(0, -3.1) + 0.16, -3.1), radius: 4.6, height: 0.58,
    material: stoneMaterial, mobile,
    fillColor: 0xffd9a0, fillIntensity: 5, rimColor: 0x9fbede, rimIntensity: 2.0,
  });

  // L'observatoire : à demi enseveli, et lisible de loin par sa silhouette.
  const bronze = new THREE.MeshPhysicalMaterial({ color: 0x6b4529, metalness: 0.9, roughness: 0.34, clearcoat: 0.5 });
  const glass = new THREE.MeshPhysicalMaterial({
    color: 0x6f9aa4, roughness: 0.14, metalness: 0.24, transmission: 0.12, thickness: 1.4,
    transparent: true, opacity: 0.9, clearcoat: 1, clearcoatRoughness: 0.08,
    envMapIntensity: 1.6, side: THREE.DoubleSide,
  });
  // L'observatoire est le sujet du lieu : c'est lui qui dit qu'on a été là avant nous.
  // Une bulle de verre posée sur le sable n'est qu'une bulle — il lui faut un tambour
  // de pierre appareillé, une fente d'observation, une armature, et des blocs tombés
  // qu'ensable le vent.
  const observatory = new THREE.Group();
  observatory.position.set(11, sandHeight(11, -26) + 0.9, -26);
  const drum = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(4.4, 4.9, 3.2, 40), stoneMaterial));
  drum.position.y = 0.2;
  const steps = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(5.6, 6.5, 0.9, 40), stoneMaterial));
  steps.position.y = -1.6;
  observatory.add(steps, drum);
  // Assises de pierre : le tambour est bâti, pas moulé d'une pièce.
  for (let course = 0; course < 3; course += 1) {
    const band = shadowed(new THREE.Mesh(
      new THREE.TorusGeometry(4.52 + course * 0.04, 0.1, 8, 48), stoneMaterial,
    ));
    band.rotation.x = Math.PI / 2;
    band.position.y = -0.9 + course * 1.1;
    observatory.add(band);
  }
  const dome = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(4.35, 48, 24, 0, TAU, 0, Math.PI / 2), glass,
  ));
  dome.position.y = 1.8;
  observatory.add(dome);
  // Fente d'observation : deux volets de bronze séparés par une ouverture sombre.
  for (const side of [-1, 1]) {
    const shutter = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(4.4, 32, 18, side > 0 ? 0.16 : Math.PI - 0.16, Math.PI - 0.32, 0, Math.PI / 2),
      bronze,
    ));
    shutter.position.y = 1.8;
    observatory.add(shutter);
  }
  const collar = shadowed(new THREE.Mesh(new THREE.TorusGeometry(4.38, 0.16, 10, 72), bronze));
  collar.rotation.x = Math.PI / 2;
  collar.position.y = 1.82;
  observatory.add(collar);
  // Cercle méridien : un arc épais, doublé d'une entretoise. Un simple fil de fer
  // ne pèse rien et se lit comme un trait de dessin.
  const meridian = shadowed(new THREE.Mesh(new THREE.TorusGeometry(6.1, 0.3, 12, 90, Math.PI * 1.55), bronze));
  meridian.position.y = 2.4;
  meridian.rotation.z = -0.24;
  const brace = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 11.4, 12), bronze));
  brace.position.y = 2.4;
  brace.rotation.z = Math.PI / 2 - 0.24;
  observatory.add(meridian, brace);
  scene.add(observatory);

  // Blocs tombés, à demi ensablés : la ruine a une histoire et le sable la reprend.
  const rubble = new THREE.InstancedMesh(makeBoulderGeometry(THREE, 1, 6.3, 0.3), stoneMaterial, mobile ? 10 : 18);
  const rubbleTransform = new THREE.Object3D();
  for (let index = 0; index < rubble.count; index += 1) {
    const angle = seeded(index, 601) * TAU;
    const distance = 7 + seeded(index, 607) * 9;
    const x = 11 + Math.cos(angle) * distance;
    const z = -26 + Math.sin(angle) * distance * 0.7;
    rubbleTransform.position.set(x, sandHeight(x, z) - 0.25, z);
    const scale = 0.7 + seeded(index, 613) * 1.5;
    rubbleTransform.scale.set(scale * 1.4, scale * 0.7, scale * 1.1);
    rubbleTransform.rotation.set(seeded(index, 617) * 0.5, seeded(index, 619) * TAU, seeded(index, 631) * 0.4);
    rubbleTransform.updateMatrix();
    rubble.setMatrixAt(index, rubbleTransform.matrix);
  }
  rubble.castShadow = true;
  rubble.receiveShadow = true;
  scene.add(rubble);
  const observatoryLight = new THREE.PointLight(0xffa751, 6, 22, 2);
  observatoryLight.position.set(11, sandHeight(11, -24) + 2.4, -23);
  scene.add(observatoryLight);

  // Le sable qui court au ras des crêtes : c'est le vent rendu visible.
  const drift = makeParticles(THREE, mobile ? 260 : 700, { x: [-40, 40], y: [-0.6, 3.4], z: [-70, 8] }, 0xd8a469, 0.1, 0.13, 257);
  scene.add(drift.points);
  pack.particles.push(drift);
  const haze = makeParticles(THREE, mobile ? 60 : 160, { x: [-46, 46], y: [0.4, 9], z: [-90, -20] }, 0xf0c79a, 0.9, 0.07, 263);
  scene.add(haze.points);
  pack.particles.push(haze);

  pack.update = (time, state, motion) => {
    pack.sky.uniforms.time.value = time;
    // Du plein jour au crépuscule, puis à la nuit du désert : chaque étape change la
    // couleur, la longueur des ombres et la densité de l'air.
    const twilight = clamp(state.elapsed * 1.25);
    const night = smoothstep(0.66, 1, state.elapsed);
    const elevation = Math.max(-0.08, 0.26 - state.elapsed * 0.36);
    pack.sunDirection.set(-0.7 + state.elapsed * 0.9, elevation, -0.66).normalize();
    pack.sky.uniforms.sunDirection.value.copy(pack.sunDirection);
    pack.keyLight.position.copy(pack.sunDirection).multiplyScalar(52);
    pack.keyLight.intensity = 5.4 * (1 - twilight * 0.82);
    pack.keyLight.color.setRGB(1, 0.88 - twilight * 0.22, 0.72 - twilight * 0.42);
    pack.hemisphere.intensity = 1.5 - twilight * 0.95;

    pack.sky.uniforms.zenithColor.value.setRGB(
      0.18 - night * 0.17, 0.42 - twilight * 0.24 - night * 0.16, 0.63 - twilight * 0.28 - night * 0.3,
    );
    pack.sky.uniforms.horizonColor.value.setRGB(
      0.91 - night * 0.79, 0.7 - twilight * 0.28 - night * 0.3, 0.49 - twilight * 0.16 - night * 0.24,
    );
    pack.sky.uniforms.starStrength.value = night * 1.3;
    pack.sky.uniforms.galaxyStrength.value = night * 1.1;
    pack.sky.uniforms.sunDiscStrength.value = 1 - night;

    observatoryLight.intensity = 4 + twilight * 18;
    scene.fog.density = 0.012 + twilight * 0.008;
    pack.grade.fogDensity = 0.02 + twilight * 0.012;
    pack.grade.saturation = 1.08 + twilight * 0.1 - night * 0.16;
    pack.grade.exposure = 1.0 + night * 0.24;
    drift.points.position.x = ((time * 1.6 * motion) % 10) - 5;
    haze.points.position.x = Math.sin(time * 0.04) * 3 * motion;
  };
  return pack;
}

// Rideau d'aurore. La lumière n'est pas une nappe : elle est faite de plis verticaux
// qui montent, s'éteignent par le haut et ondulent lentement.
function makeAuroraMaterial(THREE, color, phase) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    uniforms: {
      time: { value: phase },
      strength: { value: 0.3 },
      color: { value: new THREE.Color(color) },
      secondary: { value: new THREE.Color(0xff5f9c) },
    },
    vertexShader: `
      varying vec2 vUv;
      uniform float time;
      void main(){
        vUv = uv;
        vec3 p = position;
        p.x += sin(uv.y * 5.0 + time * 0.24 + uv.x * 4.0) * 0.9;
        p.z += cos(uv.y * 3.4 - time * 0.19 + uv.x * 2.6) * 0.7;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      uniform float time, strength;
      uniform vec3 color, secondary;
      float hash11(float p){ p = fract(p * 0.1031); p *= p + 33.33; return fract(p * (p + p)); }
      float curtain(float x, float speed, float scale){
        float cell = floor(x * scale);
        float local = fract(x * scale);
        float seed = hash11(cell);
        float sway = sin(time * speed * (0.5 + seed) + seed * 30.0) * 0.3;
        return smoothstep(0.5, 0.0, abs(local - 0.5 + sway)) * (0.35 + seed * 0.65);
      }
      void main(){
        // Plis : des rideaux étroits, à des échelles différentes, qui se recouvrent.
        float folds = curtain(vUv.x, 0.5, 22.0) * 0.6
                    + curtain(vUv.x + 0.37, 0.31, 11.0) * 0.8
                    + curtain(vUv.x + 0.71, 0.19, 5.0) * 0.5;
        // La base est vive, le sommet s'évanouit : l'aurore s'éteint en altitude.
        float vertical = smoothstep(0.0, 0.22, vUv.y) * (1.0 - smoothstep(0.42, 1.0, vUv.y));
        float edge = smoothstep(0.0, 0.1, vUv.x) * (1.0 - smoothstep(0.9, 1.0, vUv.x));
        vec3 tint = mix(color, secondary, smoothstep(0.45, 0.95, vUv.y) * 0.7);
        gl_FragColor = vec4(tint, folds * vertical * edge * strength * 0.5);
      }
    `,
  });
}

function buildAurora(THREE, mobile, environmentTexture) {
  const palette = {
    fog: 0x14313d,
    fogDensity: 0.009,
    groundLight: 0x1b3b46,
    hemisphere: 0.85,
    keyIntensity: 0.5,
    rimColor: 0x9fd8ff,
    rimIntensity: 0.7,
    sun: new THREE.Vector3(-0.4, 0.1, -0.85),
    environmentIntensity: 0.85,
    fogSun: 0x9ff4dd,
    airDensity: 0.024,
    airHeight: 7,
    airFloor: -1.4,
    bloom: 0.78,
    exposure: 1.2,
    vignette: 0.54,
    grain: 0.028,
    saturation: 0.98,
    lift: 0x08131c,
    shadowExtent: 30,
    sky: {
      zenith: 0x020a14, horizon: 0x0d3243, ground: 0x061218, sun: 0xbfe8ff,
      cloudCover: 0.16, cloudSharpness: 0.9, cloudStretch: 1.6, cloudHeight: 0.2,
      cloudLight: 0x25404f, cloudDark: 0x0a141c, haze: 0.42, stars: 1.15, galaxy: 0.8, sunDisc: 0,
    },
  };
  const pack = createPack(THREE, "aurores", palette, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 3.6 : 4.0, mobile ? 15.0 : 16.6);
  pack.target.set(0, 4.2, -16);

  const snowMaterial = surfaceMaterial(THREE, {
    preset: "snow", color: 0xc6d6dc, mobile, span: [130, 150], tile: 5, normalScale: 0.9,
    physical: true, clearcoat: 0.3, clearcoatRoughness: 0.5, sheen: 0.6,
    sheenColor: new THREE.Color(0xbfe4ff),
  });
  const ground = shadowed(new THREE.Mesh(
    makeTerrain(THREE, 130, 150, mobile ? 110 : 190, mobile ? 120 : 210, (x, z) => (
      fbm(x * 0.04, z * 0.04, 5, 2) * 2.2 + ridged(x * 0.016, z * 0.016, 4, 2) * 1.1
      + fbm(x * 0.16, z * 0.16, 3, 3) * 0.28 - 1.6
    )),
    snowMaterial,
  ), false);
  ground.position.set(0, 0, -40);
  scene.add(ground);

  const lakeMaterial = makeWaterMaterial(THREE, {
    color: 0x0d2f3c, mobile, roughness: 0.07, ripple: 0.1, repeat: [10, 10],
  });
  const lake = new THREE.Mesh(new THREE.PlaneGeometry(44, 30), lakeMaterial);
  lake.rotation.x = -Math.PI / 2;
  lake.position.set(0, -1.15, -27);
  scene.add(lake);

  const slabMaterial = surfaceMaterial(THREE, {
    preset: "snow", color: 0xb8c8d0, mobile, repeat: [3, 3], normalScale: 0.6,
    physical: true, clearcoat: 0.34, clearcoatRoughness: 0.4,
  });
  addPedestal(THREE, pack, {
    position: new THREE.Vector3(0, -0.8, -3.2), radius: 4.7, height: 0.6,
    material: slabMaterial, mobile,
    fillColor: 0xdcf0ff, fillIntensity: 5, rimColor: 0x7effd8, rimIntensity: 3.0,
  });

  const rockMaterial = surfaceMaterial(THREE, {
    preset: "cliff", color: 0x2f3f49, mobile, span: [200, 60], tile: 7, normalScale: 1.4,
  });
  // Les sommets : un relief déplacé, coiffé de neige au-dessus d'une altitude.
  // Des cônes coiffés d'un cône plus petit se lisent comme un décor de crèche.
  for (let index = 0; index < 3; index += 1) {
    const geometry = makeTerrain(THREE, 200, 60, mobile ? 120 : 210, mobile ? 30 : 54, (x, z) => {
      const spine = ridged(x * 0.02 + index * 4.3, z * 0.05, 5, 3);
      const swell = fbm(x * 0.01 - index * 2.7, z * 0.02, 3, 2) * 0.5 + 0.5;
      return Math.pow(spine, 1.5) * swell * (17 + index * 7) - 6;
    });
    const peaks = new THREE.Mesh(geometry, index === 0 ? rockMaterial : new THREE.MeshStandardMaterial({
      color: new THREE.Color(0x2b3a45).lerp(new THREE.Color(0x8fa8bb), index * 0.3),
      roughness: 1,
    }));
    peaks.position.set(0, -1 - index * 0.4, -60 - index * 22);
    peaks.receiveShadow = index === 0;
    scene.add(peaks);
  }

  const auroras = [];
  for (let index = 0; index < 3; index += 1) {
    const material = makeAuroraMaterial(THREE, index === 1 ? 0x53c8ff : 0x4dffb0, index * 2.3);
    const ribbon = new THREE.Mesh(new THREE.PlaneGeometry(38, 26, 44, 24), material);
    // Décalées et inclinées, les bandes se croisent en perspective au lieu de
    // former une seule tenture plate en travers de tout le ciel.
    ribbon.position.set(-22 + index * 20, 26 + index * 3.4, -84 - index * 14);
    ribbon.rotation.z = -0.16 + index * 0.14;
    ribbon.rotation.y = (index - 1) * 0.34;
    scene.add(ribbon);
    auroras.push(ribbon);
  }
  // L'aurore éclaire la neige. Sans cette lumière verte au sol, le rideau reste une
  // image collée au fond du ciel.
  const auroraLight = new THREE.DirectionalLight(0x8fffd8, 0.3);
  auroraLight.position.set(-6, 26, -60);
  scene.add(auroraLight);

  const snow = makeParticles(THREE, mobile ? 220 : 560, { x: [-34, 34], y: [-0.4, 20], z: [-60, 8] }, 0xeafaff, 0.11, 0.42, 293);
  scene.add(snow.points);
  pack.particles.push(snow);

  pack.update = (time, state, motion) => {
    pack.sky.uniforms.time.value = time;
    const intensity = 0.26 + state.elapsed * 0.6;
    for (let index = 0; index < auroras.length; index += 1) {
      auroras[index].material.uniforms.time.value = time * motion + index * 1.7;
      auroras[index].material.uniforms.strength.value = intensity;
    }
    auroraLight.intensity = 0.2 + intensity * 0.5;
    pack.sky.uniforms.starStrength.value = 1.0 + state.elapsed * 0.4;
    pack.grade.bloomStrength = 0.7 + state.elapsed * 0.4;
    pack.grade.saturation = 0.96 + state.elapsed * 0.1;
    lakeMaterial.userData.drift(time, motion);
    snow.points.position.y = -((time * 0.34 * motion) % 4);
    snow.points.position.x = Math.sin(time * 0.13) * 1.5 * motion;
  };
  return pack;
}

// Nébuleuse : des voiles de bruit superposés. Un semis de points ne fait pas un
// nuage de gaz — il faut de la matière continue, avec des trous et des franges.
function makeNebulaTexture(THREE, colors, seed) {
  const size = 256;
  const data = new Uint8Array(size * size * 4);
  const inner = new THREE.Color(colors[0]);
  const outer = new THREE.Color(colors[1]);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const index = (y * size + x) * 4;
      const u = x / size;
      const v = y / size;
      const warpX = fbm(u * 2 + seed, v * 2, 4, 3) * 0.9;
      const warpY = fbm(u * 2 + 5.1, v * 2 + seed, 4, 3) * 0.9;
      const cloud = fbm(u + warpX, v + warpY, 5, 3) * 0.5 + 0.5;
      const radial = 1 - clamp(Math.hypot(u - 0.5, v - 0.5) * 2.1);
      const density = clamp(Math.pow(cloud, 1.8) * Math.pow(radial, 1.9) * 2.4);
      const tint = inner.clone().lerp(outer, clamp(cloud * 1.3));
      data[index] = tint.r * 255;
      data[index + 1] = tint.g * 255;
      data[index + 2] = tint.b * 255;
      data[index + 3] = density * 255;
    }
  }
  const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

function buildCosmos(THREE, mobile, environmentTexture, key = "galaxie") {
  const palette = {
    fog: 0x0a0416,
    fogDensity: 0.0022,
    groundLight: 0x02040c,
    hemisphere: 0.5,
    keyIntensity: 1.5,
    rimColor: 0xc79cff,
    rimIntensity: 1.2,
    sun: new THREE.Vector3(0.62, 0.2, -0.72),
    environmentIntensity: 0.7,
    fogSun: 0xe6c6ff,
    airDensity: 0.0015,
    airHeight: 400,
    airFloor: -120,
    bloom: 0.95,
    exposure: 1.2,
    vignette: 0.62,
    grain: 0.03,
    saturation: 1.12,
    lift: 0x0a0818,
    sky: {
      zenith: 0x040110,
      horizon: 0x160b2a,
      ground: 0x0d0722,
      sun: 0xecd0ff,
      cloudCover: 0, haze: 0.12, stars: 1.5, galaxy: 1.5, sunDisc: 0,
    },
  };
  const pack = createPack(THREE, key, palette, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 3.6 : 4.2, mobile ? 15.4 : 17.0);
  pack.target.set(0, 3.0, -18);

  const deckMaterial = surfaceMaterial(THREE, {
    preset: "metal", color: 0x232a38, mobile, repeat: [5, 5], normalScale: 0.7,
    physical: true, metalness: 0.72, roughness: 0.32, clearcoat: 0.5,
    clearcoatRoughness: 0.22, envMapIntensity: 1.1,
  });
  addPedestal(THREE, pack, {
    position: new THREE.Vector3(0, -0.7, -3.4), radius: 5.0, height: 0.66,
    material: deckMaterial, mobile, squash: 0.68,
    fillColor: 0xdce8ff, fillIntensity: 9, rimColor: 0xc79cff, rimIntensity: 5,
  });

  // Rambarde : elle donne l'échelle du pont et sépare l'intérieur du vide.
  const railMaterial = new THREE.MeshPhysicalMaterial({ color: 0x4a5266, metalness: 0.86, roughness: 0.3 });
  for (let index = 0; index < 22; index += 1) {
    const angle = Math.PI + (index / 21) * Math.PI;
    const post = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.06, 1.15, 8), railMaterial));
    post.position.set(Math.cos(angle) * 6.1, -0.05, -3.4 + Math.sin(angle) * 4.1);
    scene.add(post);
  }

  const starCount = mobile ? 1400 : 3400;
  const starPositions = new Float32Array(starCount * 3);
  const starColors = new Float32Array(starCount * 3);
  const cold = new THREE.Color(0xbfd9ff);
  const warm = new THREE.Color(0xffd2a8);
  for (let index = 0; index < starCount; index += 1) {
    starPositions[index * 3] = (seeded(index, 307) - 0.5) * 90;
    starPositions[index * 3 + 1] = 1 + seeded(index, 311) * 44;
    starPositions[index * 3 + 2] = -12 - seeded(index, 313) * 96;
    const color = cold.clone().lerp(warm, Math.pow(seeded(index, 317), 2.2));
    starColors[index * 3] = color.r;
    starColors[index * 3 + 1] = color.g;
    starColors[index * 3 + 2] = color.b;
  }
  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  starGeometry.setAttribute("color", new THREE.BufferAttribute(starColors, 3));
  const starMaterial = new THREE.PointsMaterial({
    size: mobile ? 0.14 : 0.11,
    map: getParticleTexture(THREE),
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  });
  const starField = new THREE.Points(starGeometry, starMaterial);
  starField.frustumCulled = false;
  scene.add(starField);

  // Voiles de gaz : trois calques à des profondeurs et des rotations différentes.
  const nebulaTexture = makeNebulaTexture(
    THREE,
    [0xd08cff, 0x3d1a6b],
    7.9,
  );
  pack.textures.push(nebulaTexture);
  const veils = [];
  for (let index = 0; index < 3; index += 1) {
    const veil = new THREE.Mesh(
      new THREE.PlaneGeometry(90 + index * 26, 60 + index * 18),
      new THREE.MeshBasicMaterial({
        map: nebulaTexture,
        transparent: true,
        opacity: 0.26 - index * 0.03,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    );
    veil.position.set(-14 + index * 13, 12 + index * 4, -74 - index * 16);
    veil.rotation.z = index * 1.1;
    scene.add(veil);
    veils.push(veil);
  }

  const galaxyCount = mobile ? 2400 : 6200;
  const galaxyPositions = new Float32Array(galaxyCount * 3);
  const galaxyColors = new Float32Array(galaxyCount * 3);
  const violet = new THREE.Color(0xbb8cff);
  const blue = new THREE.Color(0x82c0ff);
  const coreColor = new THREE.Color(0xfff2d8);
  for (let index = 0; index < galaxyCount; index += 1) {
    const radius = Math.pow(seeded(index, 331), 0.62) * 20;
    const arm = index % 3;
    const scatter = (seeded(index, 337) - 0.5) * (0.5 + radius * 0.14);
    const angle = arm * TAU / 3 + radius * 0.4 + scatter;
    galaxyPositions[index * 3] = Math.cos(angle) * radius;
    galaxyPositions[index * 3 + 1] = Math.sin(angle) * radius * 0.46;
    galaxyPositions[index * 3 + 2] = (seeded(index, 347) - 0.5) * (0.4 + radius * 0.05);
    const color = radius < 3.4 ? coreColor.clone() : violet.clone().lerp(blue, seeded(index, 349));
    galaxyColors[index * 3] = color.r;
    galaxyColors[index * 3 + 1] = color.g;
    galaxyColors[index * 3 + 2] = color.b;
  }
  const galaxyGeometry = new THREE.BufferGeometry();
  galaxyGeometry.setAttribute("position", new THREE.BufferAttribute(galaxyPositions, 3));
  galaxyGeometry.setAttribute("color", new THREE.BufferAttribute(galaxyColors, 3));
  const galaxyMaterial = new THREE.PointsMaterial({
    size: mobile ? 0.16 : 0.13,
    map: getParticleTexture(THREE),
    vertexColors: true,
    transparent: true,
    opacity: 0.8,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  });
  const galaxy = new THREE.Points(galaxyGeometry, galaxyMaterial);
  galaxy.position.set(-16, 20, -78);
  galaxy.rotation.set(-0.16, 0.2, -0.24);
  scene.add(galaxy);

  const planetMaterial = surfaceMaterial(THREE, {
    preset: "silt", color: 0x4a6490, mobile, repeat: [3, 2], normalScale: 1.2,
    physical: true, clearcoat: 0.12, envMapIntensity: 0.4,
  });
  const planet = new THREE.Group();
  const planetBody = new THREE.Mesh(new THREE.SphereGeometry(11, mobile ? 40 : 72, mobile ? 24 : 44), planetMaterial);
  const planetRing = new THREE.Mesh(
    new THREE.RingGeometry(13.5, 21, 128),
    new THREE.MeshPhysicalMaterial({
      color: 0xc0ac8c, transparent: true, opacity: 0.5,
      side: THREE.DoubleSide, roughness: 0.8, depthWrite: false,
    }),
  );
  planetRing.rotation.x = 1.24;
  planet.add(planetBody, planetRing);
  planet.position.set(17, 11, -52);
  planet.rotation.z = -0.22;
  // La planète est le sujet du pont : c'est elle qui donne l'échelle du vide.
  planet.visible = true;
  scene.add(planet);
  // Une lumière rasante donne à la planète son terminateur : sans elle, une sphère
  // uniformément éclairée n'est qu'un disque.
  const starLight = new THREE.DirectionalLight(0xfff0dc, 3.6);
  starLight.position.set(46, 16, -20);
  scene.add(starLight);

  const navigationLights = [];
  for (const x of [-4.7, 4.7]) {
    const light = new THREE.PointLight(x < 0 ? 0x66aaff : 0xff687d, 3, 7, 2);
    light.position.set(x, -0.15, -3.3);
    scene.add(light);
    navigationLights.push(light);
  }

  pack.update = (time, state, motion) => {
    pack.sky.uniforms.time.value = time;
    galaxy.rotation.z = -0.24 + time * 0.006 * motion;
    galaxyMaterial.opacity = 0.72 + state.elapsed * 0.2;
    for (let index = 0; index < veils.length; index += 1) {
      veils[index].material.opacity = (0.24 - index * 0.03) * (1 + state.elapsed * 0.6);
      veils[index].rotation.z += 0.00006 * motion * (index + 1);
    }
    starField.rotation.y = time * 0.0016 * motion;
    planet.rotation.y = time * 0.01 * motion;
    navigationLights.forEach((light, index) => {
      light.intensity = 2.2 + Math.sin(time * 1.3 + index * 2.1) * 0.7 * motion;
    });
    pack.sky.uniforms.starStrength.value = 1.3 + state.elapsed * 0.35;
    pack.grade.bloomStrength = 0.9 + state.elapsed * 0.35;
  };
  return pack;
}

function buildTimeRiver(THREE, mobile, environmentTexture, key = "fleuve_temps") {
  const abyss = key === "abysses";
  const palette = {
    fog: abyss ? 0x0a3a44 : 0x39456e,
    fogDensity: abyss ? 0.032 : 0.0085,
    groundLight: abyss ? 0x04181c : 0x0b0d1a,
    hemisphere: abyss ? 1.2 : 1.0,
    keyIntensity: abyss ? 2.6 : 2.4,
    rimColor: abyss ? 0x8ff0e6 : 0xb9c8ff,
    rimIntensity: abyss ? 1.0 : 0.8,
    sun: new THREE.Vector3(abyss ? -0.16 : -0.5, abyss ? 0.95 : 0.28, abyss ? -0.26 : -0.8),
    environmentIntensity: abyss ? 0.5 : 0.8,
    fogSun: abyss ? 0xa8fff0 : 0xdcc9ff,
    airDensity: abyss ? 0.045 : 0.016,
    airHeight: abyss ? 22 : 5,
    airFloor: -2,
    bloom: abyss ? 0.7 : 0.62,
    shafts: abyss ? 2.2 : 0.9,
    exposure: abyss ? 1.24 : 1.08,
    vignette: abyss ? 0.66 : 0.52,
    grain: 0.028,
    saturation: abyss ? 1.06 : 1.08,
    lift: abyss ? 0x04161a : 0x0a0d1a,
    shadowExtent: 28,
    sky: abyss ? {
      zenith: 0x0d5560, horizon: 0x083038, ground: 0x02171c, sun: 0xb4fff2,
      cloudCover: 0, haze: 1.0, stars: 0, galaxy: 0, sunDisc: 0.4,
    } : {
      zenith: 0x050a1c, horizon: 0x2e4478, ground: 0x070a16, sun: 0xf0d6ff,
      cloudCover: 0.34, cloudSharpness: 0.9, cloudStretch: 1.4, cloudHeight: 0.18,
      cloudLight: 0x3f4a76, cloudDark: 0x131728, haze: 0.5, stars: 0.9, galaxy: 0.7, sunDisc: 0.2,
    },
  };
  const pack = createPack(THREE, key, palette, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 3.8 : 4.3, mobile ? 15.2 : 16.8);
  pack.target.set(0, abyss ? 3.4 : 2.2, -16);

  const stoneMaterial = surfaceMaterial(THREE, {
    preset: "cliff", color: abyss ? 0x2c5a5c : 0x6a6f85, mobile, span: [26, 130], tile: 5, normalScale: 1.6,
  });

  if (abyss) {
    // Sous l'eau : pas de ciel, un fond de sable clair, et la lumière qui tombe de
    // très haut en colonnes. Tout ce qui s'éloigne se dissout dans le bleu-vert.
    const floorMaterial = surfaceMaterial(THREE, {
      preset: "silt", color: 0x2e6a66, mobile, span: [140, 160], tile: 5, normalScale: 1.2,
    });
    const seabed = shadowed(new THREE.Mesh(
      makeTerrain(THREE, 140, 160, mobile ? 90 : 150, mobile ? 100 : 165, (x, z) => (
        fbm(x * 0.06, z * 0.06, 4, 2) * 1.5
        + ridged(x * 0.03 + 2, z * 0.03, 3, 2) * 0.8
        + Math.sin(x * 0.34) * 0.14 - 1.5
      )),
      floorMaterial,
    ), false);
    seabed.position.set(0, 0, -46);
    scene.add(seabed);

    // Deux nappes de caustiques défilant à des vitesses opposées : leur croisement
    // évite la boucle visible qu'une seule nappe imprimerait au fond.
    const causticTexture = makeCausticTexture(THREE, mobile);
    pack.textures.push(causticTexture);
    pack.caustics = [];
    for (let layer = 0; layer < 2; layer += 1) {
      const map = causticTexture.clone();
      map.needsUpdate = true;
      map.wrapS = THREE.RepeatWrapping;
      map.wrapT = THREE.RepeatWrapping;
      map.repeat.set(7 + layer * 3, 8 + layer * 3);
      const sheet = new THREE.Mesh(
        new THREE.PlaneGeometry(140, 160),
        new THREE.MeshBasicMaterial({
          map,
          transparent: true,
          opacity: 0.3 - layer * 0.09,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
          color: 0x9ffff0,
        }),
      );
      sheet.rotation.x = -Math.PI / 2;
      sheet.position.set(0, -0.62 + layer * 0.05, -46);
      sheet.renderOrder = 1;
      scene.add(sheet);
      pack.caustics.push({ map, direction: layer ? -1 : 1 });
    }
  } else {
    const riverMaterial = makeWaterMaterial(THREE, {
      color: 0x121d3e, mobile, roughness: 0.06, ripple: 0.34, repeat: [5, 24],
    });
    riverMaterial.envMapIntensity = 1.5;
    const river = new THREE.Mesh(new THREE.PlaneGeometry(15, 130, 1, 1), riverMaterial);
    river.rotation.x = -Math.PI / 2;
    river.position.set(0, -1.3, -46);
    scene.add(river);
    pack.riverMaterial = riverMaterial;

    for (const side of [-1, 1]) {
      const bank = shadowed(new THREE.Mesh(
        makeTerrain(THREE, 26, 130, mobile ? 22 : 40, mobile ? 60 : 96, (x, z) => {
          const fromWater = side < 0 ? -x : x;
          const distance = clamp((fromWater + 13) / 26);
          const relief = fbm(x * 0.1, z * 0.07, 4, 2) * 0.7 + ridged(x * 0.06, z * 0.05, 3, 2) * 0.5;
          return Math.pow(distance, 0.8) * 2.6 + relief - 1.35;
        }),
        stoneMaterial,
      ), false);
      bank.position.set(side * 20, 0, -46);
      scene.add(bank);
    }
  }

  const bridgeMaterial = surfaceMaterial(THREE, {
    preset: "stone", color: abyss ? 0x2f5f61 : 0x555b6d, mobile, repeat: [4, 3],
    normalScale: 1.1, physical: true, clearcoat: abyss ? 0.5 : 0.14, clearcoatRoughness: 0.5,
  });
  addPedestal(THREE, pack, {
    position: new THREE.Vector3(0, -0.74, -3.2), radius: 4.7, height: 0.64,
    material: bridgeMaterial, mobile,
    fillColor: abyss ? 0xa8fff0 : 0xdcc9ff, fillIntensity: abyss ? 7 : 5,
    rimColor: abyss ? 0x65eadc : 0x8fa6ff, rimIntensity: abyss ? 4.2 : 3.2,
  });

  // Ruines : des colonnes assemblées bloc à bloc, désaxées. Un cylindre lisse n'a
  // pas d'histoire ; un empilement légèrement décalé en a une.
  const ruins = new THREE.Group();
  const columnStone = new THREE.CylinderGeometry(0.62, 0.68, 0.66, 12);
  const archStone = new THREE.BoxGeometry(0.72, 0.52, 0.9);
  for (let index = 0; index < 7; index += 1) {
    const side = index % 2 ? 1 : -1;
    const x = side * (8.4 + seeded(index, 367) * 3.4);
    const z = -10 - index * 9.2;
    const height = 3.6 + seeded(index, 373) * 3.2;
    const broken = seeded(index, 377) > 0.62;
    for (const offset of [-1.9, 1.9]) {
      const blocks = Math.max(3, Math.round(height / 0.66) - (broken && offset > 0 ? 3 : 0));
      for (let blockIndex = 0; blockIndex < blocks; blockIndex += 1) {
        const block = shadowed(new THREE.Mesh(columnStone, stoneMaterial));
        block.position.set(
          x + offset + (seeded(blockIndex + index * 13, 491) - 0.5) * 0.14,
          -0.9 + blockIndex * 0.66 + 0.35,
          z + (seeded(blockIndex + index * 11, 499) - 0.5) * 0.14,
        );
        block.rotation.y = (seeded(blockIndex + index * 17, 503) - 0.5) * 0.4;
        ruins.add(block);
      }
    }
    if (!broken) {
      for (let blockIndex = 0; blockIndex <= 12; blockIndex += 1) {
        const angle = Math.PI * blockIndex / 12;
        const block = shadowed(new THREE.Mesh(archStone, stoneMaterial));
        block.position.set(x + Math.cos(angle) * 1.9, -0.72 + height + Math.sin(angle) * 1.9, z);
        block.rotation.z = angle - Math.PI / 2;
        block.rotation.y = (seeded(blockIndex + index * 19, 509) - 0.5) * 0.12;
        ruins.add(block);
      }
    }
  }
  scene.add(ruins);

  if (abyss) {
    // Colonnes de lumière descendant de la surface. Elles donnent le haut, le poids
    // de l'eau et l'échelle du lieu — et elles éclairent réellement ce qu'elles
    // touchent, au lieu de flotter par-dessus.
    for (let index = 0; index < 4; index += 1) {
      const shaft = new THREE.Mesh(
        new THREE.CylinderGeometry(0.7 + seeded(index, 521) * 0.8, 2.4 + seeded(index, 523) * 1.6, 40, 22, 8, true),
        makeBeamMaterial(THREE, 0xbdfff2, 0.09),
      );
      shaft.position.set(-16 + index * 10.5 + seeded(index, 541) * 3, 17, -20 - index * 11);
      shaft.rotation.z = 0.08 - index * 0.02;
      shaft.renderOrder = 2;
      scene.add(shaft);
    }
    // La lumière de surface : elle tombe d'aplomb et sculpte le haut des colonnes.
    const surfaceLight = new THREE.DirectionalLight(0xcafff4, 3.4);
    surfaceLight.position.set(-4, 40, -18);
    surfaceLight.target.position.set(0, -1, -26);
    configureShadow(surfaceLight, mobile, 26);
    scene.add(surfaceLight, surfaceLight.target);
    // Rebond du fond clair vers le dessous des volumes : sous l'eau, rien n'est
    // jamais complètement noir du côté opposé à la lumière.
    const bounce = new THREE.HemisphereLight(0x7fd8cc, 0x1a4a4c, 1.5);
    scene.add(bounce);
  }

  const shardMaterial = new THREE.MeshPhysicalMaterial({
    color: abyss ? 0x7df5e5 : 0xc4d4ff,
    emissive: abyss ? 0x27bcae : 0x5a7dff,
    emissiveIntensity: 1.1,
    metalness: 0.06,
    roughness: 0.14,
    transparent: true,
    opacity: 0.66,
    transmission: 0.3,
    depthWrite: false,
  });
  const shards = new THREE.Group();
  const shardCount = mobile ? 20 : 42;
  for (let index = 0; index < shardCount; index += 1) {
    const shard = new THREE.Mesh(new THREE.OctahedronGeometry(0.15 + seeded(index, 379) * 0.28, 0), shardMaterial);
    shard.position.set((seeded(index, 383) - 0.5) * 16, 0.3 + seeded(index, 389) * 7, -6 - seeded(index, 397) * 60);
    shard.scale.y = 2 + seeded(index, 401) * 3.5;
    shard.rotation.set(seeded(index, 409) * TAU, seeded(index, 419) * TAU, seeded(index, 421) * TAU);
    shards.add(shard);
  }
  scene.add(shards);

  const motes = makeParticles(
    THREE, mobile ? 160 : 400,
    { x: [-18, 18], y: [-1, abyss ? 14 : 6], z: [-66, 4] },
    abyss ? 0xd6fff8 : 0xcdd8ff, abyss ? 0.14 : 0.08, abyss ? 0.4 : 0.24, 431,
  );
  scene.add(motes.points);
  pack.particles.push(motes);

  const riverLight = new THREE.PointLight(abyss ? 0x65eadc : 0x7f9bff, 60, 34, 2);
  riverLight.position.set(0, 1.4, -15);
  scene.add(riverLight);
  if (!abyss) {
    // La lune, posée dans l'axe du fleuve : sa trace sur l'eau donne la direction du
    // courant et sépare les deux berges.
    const moon = new THREE.Mesh(
      new THREE.SphereGeometry(2.6, 32, 20),
      new THREE.MeshBasicMaterial({ color: 0xf0e6ff }),
    );
    moon.position.set(-6, 14, -96);
    scene.add(moon);
    const moonLight = new THREE.DirectionalLight(0xc9d4ff, 2.4);
    moonLight.position.set(-6, 18, -70);
    moonLight.target.position.set(0, 0, -20);
    configureShadow(moonLight, mobile, 30);
    scene.add(moonLight, moonLight.target);
  }

  pack.update = (time, state, motion) => {
    pack.sky.uniforms.time.value = time;
    pack.riverMaterial?.userData.drift(time, motion);
    shards.children.forEach((shard, index) => {
      shard.rotation.y += 0.0016 * motion * (1 + index % 3);
      shard.position.y += Math.sin(time * 0.42 + index) * 0.0012 * motion;
    });
    shardMaterial.emissiveIntensity = 0.9 + state.elapsed * 0.8 + Math.sin(time * 0.7) * 0.1 * motion;
    riverLight.intensity = 11 + state.elapsed * 10;
    pack.grade.bloomStrength = (abyss ? 0.66 : 0.58) + state.elapsed * 0.32;
    if (abyss) {
      for (let index = 0; index < (pack.caustics?.length || 0); index += 1) {
        const layer = pack.caustics[index];
        layer.map.offset.set(
          time * 0.008 * motion * layer.direction,
          time * 0.012 * motion * layer.direction,
        );
      }
      // Le courant fait dériver la neige marine vers le haut, très lentement.
      motes.points.position.y = ((time * 0.12 * motion) % 6) - 3;
      motes.points.position.x = Math.sin(time * 0.06) * 1.4 * motion;
      pack.grade.shaftStrength = 2.0 + state.elapsed * 1.2;
    } else {
      motes.points.position.z = ((time * 0.36 * motion) % 6) - 3;
      pack.sky.uniforms.starStrength.value = 0.8 + state.elapsed * 0.5;
    }
  };
  return pack;
}

const BUILDERS = {
  arbre_etoiles: buildStarTree,
  refuge_pluie: buildRainRefuge,
  foret: buildForest,
  ocean: buildOcean,
  sahara: buildSahara,
  aurores: buildAurora,
  galaxie: (THREE, mobile, environment) => buildCosmos(THREE, mobile, environment, "galaxie"),
  fleuve_temps: (THREE, mobile, environment) => buildTimeRiver(THREE, mobile, environment, "fleuve_temps"),
  abysses: (THREE, mobile, environment) => buildTimeRiver(THREE, mobile, environment, "abysses"),
};

function disposePack(pack) {
  pack.scene.traverse((node) => {
    node.geometry?.dispose?.();
    const materials = node.material ? (Array.isArray(node.material) ? node.material : [node.material]) : [];
    for (const material of materials) material.dispose?.();
  });
  for (const texture of pack.textures) texture.dispose?.();
  pack.environmentTarget?.dispose();
}

function setParticleDensity(pack, density, reducedMotion) {
  const ratios = [0, 0.26, 0.64, 1];
  const ratio = ratios[density] ?? ratios[2];
  for (const particle of pack.particles) {
    particle.points.geometry.setDrawRange(0, Math.round(particle.count * ratio));
    particle.material.opacity = particle.baseOpacity * (reducedMotion ? 0.74 : 1);
  }
}

function createWorld(THREE, app, stage, canvas) {
  const mobile = matchMedia("(max-width: 760px)").matches;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fallbackCanvas = stage.querySelector("#decor-canvas");
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: false,
    alpha: false,
    powerPreference: "high-performance",
  });
  const pixelRatio = Math.min(devicePixelRatio || 1, mobile ? 1.15 : 1.5);
  renderer.setPixelRatio(pixelRatio);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  // Le rendu reste linéaire jusqu'au compositeur, qui applique lui-même la courbe
  // filmique : tonemapper deux fois délave l'image.
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  // Les ombres ne se recalculent pas à chaque image.
  //
  // Rien ne bouge dans ces décors : ni les arbres, ni les colonnes, ni le socle. Seuls
  // le soleil dérive avec la session et les particules flottent — et les particules ne
  // projettent rien. Redessiner la carte d'ombres soixante fois par seconde pour un
  // résultat identique coûtait près de neuf dixièmes du temps de rendu. Elle n'est donc
  // rafraîchie que lorsque la lumière a réellement tourné.
  renderer.shadowMap.autoUpdate = false;
  const composer = makeComposer(THREE, renderer, mobile);
  const environmentTexture = null;
  const packs = new Map();
  const sunScreen = new THREE.Vector3();
  let active = null;
  let width = 0;
  let height = 0;
  let frame = 0;
  let disposed = false;
  let firstFrame = false;
  let lastTime = 0;
  let pointerX = 0;
  let pointerY = 0;
  let targetPointerX = 0;
  let targetPointerY = 0;
  let lastDensity = -1;
  // Dernière position solaire pour laquelle la carte d'ombres a été calculée. La
  // valeur -1 force un premier rendu à l'activation d'un univers.
  let shadowElapsed = -1;

  function resize() {
    const rect = stage.getBoundingClientRect();
    const nextWidth = Math.max(1, Math.round(rect.width));
    const nextHeight = Math.max(1, Math.round(rect.height));
    if (width === nextWidth && height === nextHeight) return;
    width = nextWidth;
    height = nextHeight;
    renderer.setSize(width, height, false);
    composer.setSize(width, height, pixelRatio);
    renderer.shadowMap.needsUpdate = true;
    for (const pack of packs.values()) {
      pack.camera.aspect = width / height;
      pack.camera.updateProjectionMatrix();
    }
  }

  function activate() {
    const key = app.dataset.ambience;
    if (!WORLD_KEYS.has(key)) {
      active = null;
      canvas.hidden = true;
      app.dataset.world3dActive = "false";
      if (fallbackCanvas) fallbackCanvas.style.opacity = "";
      return;
    }
    if (!packs.has(key)) {
      const pack = BUILDERS[key](THREE, mobile, environmentTexture);
      captureEnvironment(THREE, renderer, pack, pack.palette);
      packs.set(key, pack);
      width = 0;
    }
    active = packs.get(key);
    active.baseCameraX ??= active.camera.position.x;
    active.baseCameraY ??= active.camera.position.y;
    canvas.hidden = false;
    app.dataset.world3dActive = "true";
    lastDensity = -1;
    shadowElapsed = -1;
    lastTime = 0;
  }

  function applyGrade(pack) {
    const uniforms = composer.uniforms;
    const grade = pack.grade;
    uniforms.fogColor.value.copy(grade.fogColor);
    uniforms.fogSunColor.value.copy(grade.fogSunColor);
    uniforms.fogDensity.value = grade.fogDensity;
    uniforms.fogHeight.value = grade.fogHeight;
    uniforms.fogFloor.value = grade.fogFloor;
    uniforms.bloomStrength.value = grade.bloomStrength;
    uniforms.shaftStrength.value = grade.shaftStrength;
    uniforms.exposure.value = grade.exposure;
    uniforms.vignette.value = grade.vignette;
    uniforms.grain.value = grade.grain;
    uniforms.chroma.value = grade.chroma;
    uniforms.saturation.value = grade.saturation;
    uniforms.lift.value.copy(grade.lift);
    uniforms.gain.value.copy(grade.gain);
    uniforms.sunColor.value.copy(pack.keyLight.color);

    // Position du soleil à l'écran : les rais de lumière ne rayonnent que depuis
    // l'astre, et seulement s'il est dans le champ.
    sunScreen.copy(pack.sunDirection).multiplyScalar(90).add(pack.camera.position);
    sunScreen.project(pack.camera);
    const visible = sunScreen.z < 1 && pack.sunDirection.y > -0.05;
    uniforms.sunScreen.value.set(sunScreen.x * 0.5 + 0.5, sunScreen.y * 0.5 + 0.5, visible ? 1 : 0);
  }

  function drawFrame(time, state, motion) {
    active.update(time, state, motion);
    // `update` vient de déplacer le soleil : on redessine les ombres seulement si sa
    // course a franchi un pas visible — soit une centaine de fois sur une session
    // entière, contre plusieurs milliers auparavant.
    if (Math.abs(state.elapsed - shadowElapsed) > 0.008) {
      renderer.shadowMap.needsUpdate = true;
      shadowElapsed = state.elapsed;
    }
    applyGrade(active);
    composer.uniforms.time.value = time;
    active.camera.lookAt(active.target);
    composer.render(active.scene, active.camera);
  }

  function render(milliseconds) {
    if (disposed) return;
    if (!active || document.hidden) {
      frame = requestAnimationFrame(render);
      return;
    }
    if (milliseconds - lastTime < (mobile ? 28 : 14)) {
      frame = requestAnimationFrame(render);
      return;
    }
    const delta = Math.min(0.04, (milliseconds - lastTime) / 1000 || 0.016);
    lastTime = milliseconds;
    const time = milliseconds / 1000;
    resize();
    const state = sessionState(app);
    const motion = reducedMotion ? 0 : [0, 0.28, 0.66, 1][state.density];
    if (state.density !== lastDensity) {
      setParticleDensity(active, state.density, reducedMotion);
      lastDensity = state.density;
    }

    pointerX += (targetPointerX - pointerX) * Math.min(1, delta * 2.1);
    pointerY += (targetPointerY - pointerY) * Math.min(1, delta * 2.1);
    active.camera.position.x = active.baseCameraX + pointerX * (reducedMotion ? 0 : 0.72);
    active.camera.position.y += (active.baseCameraY - pointerY * 0.24 - active.camera.position.y) * Math.min(1, delta * 0.5);
    drawFrame(time, state, motion);

    if (!firstFrame) {
      firstFrame = true;
      app.dataset.world3d = "ready";
    }
    if (fallbackCanvas) fallbackCanvas.style.opacity = "0";
    frame = requestAnimationFrame(render);
  }

  const mutationObserver = new MutationObserver(activate);
  mutationObserver.observe(app, { attributes: true, attributeFilter: ["data-ambience"] });
  const resizeObserver = new ResizeObserver(() => { width = 0; });
  resizeObserver.observe(stage);
  const pointerMove = (event) => {
    const rect = stage.getBoundingClientRect();
    targetPointerX = clamp((event.clientX - rect.left) / rect.width, 0, 1) * 2 - 1;
    targetPointerY = clamp((event.clientY - rect.top) / rect.height, 0, 1) * 2 - 1;
  };
  const pointerLeave = () => {
    targetPointerX = 0;
    targetPointerY = 0;
  };
  stage.addEventListener("pointermove", pointerMove, { passive: true });
  stage.addEventListener("pointerleave", pointerLeave, { passive: true });

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    active = null;
    canvas.hidden = true;
    app.dataset.world3d = "fallback";
    app.dataset.world3dActive = "false";
    app.dataset.world3dReason = "context-lost";
    if (fallbackCanvas) fallbackCanvas.style.opacity = "";
  }, { once: true });

  window.addEventListener("pagehide", () => {
    disposed = true;
    cancelAnimationFrame(frame);
    mutationObserver.disconnect();
    resizeObserver.disconnect();
    stage.removeEventListener("pointermove", pointerMove);
    stage.removeEventListener("pointerleave", pointerLeave);
    for (const pack of packs.values()) disposePack(pack);
    composer.dispose();
    renderer.dispose();
  }, { once: true });

  activate();
  frame = requestAnimationFrame(render);
}

async function boot() {
  const app = document.querySelector("#focus-app");
  const stage = document.querySelector("#focus-stage");
  const fallback = document.querySelector("#decor-canvas");
  if (!app || !stage || !fallback) return;

  let started = false;
  let observer;
  const start = async () => {
    if (started) return;
    started = true;
    observer?.disconnect();
    const canvas = document.createElement("canvas");
    canvas.className = "world-3d-canvas";
    canvas.setAttribute("aria-hidden", "true");
    canvas.hidden = true;
    stage.insertBefore(canvas, fallback);
    try {
      const THREE = await import(new URL("../vendor/three.module.js", import.meta.url).href);
      createWorld(THREE, app, stage, canvas);
    } catch (error) {
      canvas.remove();
      app.dataset.world3d = "fallback";
      app.dataset.world3dReason = "world-module-load";
      throw error;
    }
  };
  const maybeStart = () => {
    if (WORLD_KEYS.has(app.dataset.ambience)) {
      start().catch((error) => console.error("Univers 3D indisponible", error));
    }
  };

  if (WORLD_KEYS.has(app.dataset.ambience)) {
    await start();
  } else {
    observer = new MutationObserver(maybeStart);
    observer.observe(app, { attributes: true, attributeFilter: ["data-ambience"] });
    window.addEventListener("pagehide", () => observer?.disconnect(), { once: true });
  }
}

boot().catch((error) => console.error("Univers 3D indisponible", error));
