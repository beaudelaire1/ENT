// Univers photographiques du Sablier.
//
// Un lieu bâti en cylindres, en plans de feuillage peints et en rochers à facettes reste un
// dessin, quel que soit l'éclairage posé dessus. Une image photographique porte d'emblée ce
// qu'aucune composition procédurale n'a atteint : la matière, la profondeur de l'air, une
// lumière crédible. Le lieu devient donc une image, et la scène ne garde que ce qu'une image
// ne sait pas faire seule : le mouvement — une lente dérive du cadre, et ce qui traverse
// l'air du lieu (poussière, neige, pluie, étincelles, pétales), voire l'éclair d'un orage.
//
// L'image ne passe ni par le tonemapping ni par le halo : elle est déjà développée, et la
// courbe du rendu la délavait. Elle est tracée en espace écran, avant tout le reste, sans
// écrire la profondeur. Les fichiers sont préparés hors ligne par
// `tools/sablier-photo-worlds.py`, qui en consigne la provenance.
const BASE = new URL("../photos/", import.meta.url);
const TAU = Math.PI * 2;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function page() {
  return document.querySelector("#focus-app");
}

// Mêmes compteurs que les matières et les ciels : `materialLoads` dit aux captures de
// contrôle que le lieu n'est pas complet, `materialRevision` force une nouvelle image
// quand la photographie arrive alors que le mouvement est à l'arrêt.
function pending(delta) {
  const app = page();
  if (app) app.dataset.materialLoads = String(Math.max(0, Number(app.dataset.materialLoads || 0) + delta));
}

function revise() {
  const app = page();
  if (app) app.dataset.materialRevision = String(Number(app.dataset.materialRevision || 0) + 1);
}

/**
 * L'image plein cadre. `focus` est le point de l'image (x, y depuis le haut) gardé au centre
 * quand le cadre la rogne ; `drift` l'amplitude de la respiration du cadre.
 */
export function photoBackdrop(THREE, { src, focus = [0.5, 0.5], drift = 0.06 }) {
  const uniforms = {
    map: { value: null },
    span: { value: new THREE.Vector2(1, 1) },
    origin: { value: new THREE.Vector2(0, 0) },
    opacity: { value: 0 },
    flash: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position.xy, 0.999, 1.0);
      }`,
    fragmentShader: `
      uniform sampler2D map;
      uniform vec2 span;
      uniform vec2 origin;
      uniform float opacity;
      uniform float flash;
      varying vec2 vUv;
      void main() {
        vec3 colour = texture2D(map, origin + vUv * span).rgb * opacity;
        // L'éclair vient du ciel : il blanchit le haut de l'image plus que le premier plan.
        colour += flash * vec3(0.42, 0.47, 0.58) * (0.45 + 0.55 * vUv.y);
        gl_FragColor = vec4(colour, 1.0);
        #include <colorspace_fragment>
      }`,
    depthTest: false,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -100;

  let imageAspect = 16 / 9;
  let viewAspect = 16 / 9;
  let zoom = 1;
  let pan = [0, 0];
  let loaded = false;

  // Couvre l'écran sans déformer : l'axe le plus serré montre toute l'image, l'autre la
  // rogne autour du point focal, sans jamais sortir de ses bords.
  function frame() {
    const cover = viewAspect > imageAspect ? [1, imageAspect / viewAspect] : [viewAspect / imageAspect, 1];
    const sx = cover[0] / zoom;
    const sy = cover[1] / zoom;
    // L'image est retournée au chargement : le haut de la photo est en v = 1.
    uniforms.span.value.set(sx, sy);
    uniforms.origin.value.set(
      clamp(focus[0] + pan[0] - sx / 2, 0, 1 - sx),
      clamp(1 - focus[1] + pan[1] - sy / 2, 0, 1 - sy),
    );
  }

  pending(1);
  const texture = new THREE.TextureLoader().load(
    new URL(src, BASE).href,
    (image) => {
      imageAspect = image.image.width / image.image.height;
      uniforms.map.value = image;
      uniforms.opacity.value = 1;
      loaded = true;
      frame();
      revise();
      pending(-1);
    },
    undefined,
    (error) => {
      // Un lieu noir vaut mieux qu'une scène qui n'apparaît jamais : la scène prend la main,
      // et l'échec reste lisible dans la console.
      console.warn("Sablier : image du lieu indisponible", src, error);
      loaded = true;
      pending(-1);
    },
  );
  texture.colorSpace = THREE.SRGBColorSpace;
  mesh.userData.dispose = () => texture.dispose();

  return {
    mesh,
    get ready() { return loaded; },
    resize(width, height) {
      viewAspect = width / Math.max(1, height);
      frame();
    },
    setFlash(value) {
      uniforms.flash.value = value;
    },
    update(time) {
      // Une respiration de cent secondes : trop lente pour qu'on la voie bouger, assez
      // ample pour que l'image ne soit jamais une affiche figée.
      const phase = (time * 0.001 * TAU) / 100;
      zoom = 1 + drift * (0.5 - 0.5 * Math.cos(phase));
      pan = [Math.sin(phase * 0.7) * 0.012, Math.sin(phase * 0.43) * 0.008];
      frame();
    },
  };
}

// Ce qui traverse l'air d'un lieu. Chaque famille vit dans une boîte de la scène, face à la
// caméra (qui regarde vers -z depuis 1,7 m), avance à sa vitesse et revient par le bord
// opposé. `velocity` est en unités par seconde ; `glint` fait scintiller, `glow` additionne
// la lumière au lieu de la recouvrir, `shape` 1 trace un trait de pluie au lieu d'un point.
const PARTICLES = {
  // Poussière dans une lumière rasante : monte avec l'air tiède, ne brille qu'en croisant un rayon.
  dust: { count: 160, color: "#ffe9c4", size: 40, opacity: 0.55, velocity: [0.05, 0.035, 0], sway: 0.5, glint: 1, glow: true, box: [[-5, 9], [-2, 9], [-24, -4]] },
  // Lucioles, reflets de lanternes : rares, lents, qui s'allument et s'éteignent.
  fireflies: { count: 50, color: "#ffd48a", size: 70, opacity: 0.8, velocity: [0.08, 0.05, 0], sway: 1.2, glint: 1, glow: true, box: [[-10, 6], [-2, 6], [-20, -5]] },
  snow: { count: 900, color: "#ffffff", size: 75, opacity: 0.85, velocity: [0.18, -1.1, 0], sway: 0.8, glint: 0, glow: false, box: [[-16, 16], [-6, 12], [-22, -3]] },
  // Une goutte ne se voit que filée : le trait doit couvrir plusieurs pixels de haut et au
  // moins un de large, sans quoi la pluie existe dans la scène sans jamais apparaître.
  rain: { count: 1400, color: "#d6e6ff", size: 260, opacity: 0.3, velocity: [0.4, -9, 0], sway: 0, glint: 0, glow: false, shape: 1, box: [[-16, 16], [-6, 12], [-22, -3]] },
  // Étincelles d'un foyer : naissent bas, montent vite, vacillent et s'éteignent en chemin.
  sparks: { count: 90, color: "#ffab4a", size: 48, opacity: 0.95, velocity: [0.04, 0.9, 0], sway: 0.35, glint: 1, glow: true, box: [[-5, 2], [-2.5, 4], [-12, -7]] },
  petals: { count: 60, color: "#fff1f5", size: 60, opacity: 0.75, velocity: [0.3, -0.35, 0], sway: 1, glint: 0, glow: false, box: [[-14, 14], [-4, 10], [-18, -4]] },
  leaves: { count: 28, color: "#d8662c", size: 70, opacity: 0.85, velocity: [0.35, -0.5, 0], sway: 1.2, glint: 0, glow: false, box: [[-14, 14], [-4, 10], [-18, -4]] },
  // Sable soulevé au ras des dunes : un voile rapide et bas, jamais une tempête.
  sand: { count: 160, color: "#e9b979", size: 22, opacity: 0.35, velocity: [1.4, 0.04, 0], sway: 0.2, glint: 0, glow: false, box: [[-16, 16], [-5, 2], [-16, -4]] },
  // Neige marine : particules en suspension qui descendent à peine dans la lumière d'en haut.
  marine: { count: 140, color: "#c6f4f2", size: 34, opacity: 0.4, velocity: [0.03, -0.08, 0], sway: 0.5, glint: 0.5, glow: true, box: [[-12, 12], [-5, 10], [-22, -4]] },
};

/** Une famille de particules, d'après un préréglage de `PARTICLES` et ses retouches. */
export function particles(THREE, { kind = "dust", seed = 11, ...overrides } = {}) {
  const preset = { ...(PARTICLES[kind] || PARTICLES.dust), ...overrides };
  const { count, box } = preset;
  let state = seed * 9301 + 49297;
  const random = () => (state = (state * 9301 + 49297) % 233280) / 233280;
  const positions = new Float32Array(count * 3);
  const seeds = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    for (let axis = 0; axis < 3; axis += 1) {
      positions[i * 3 + axis] = box[axis][0] + random() * (box[axis][1] - box[axis][0]);
    }
    seeds[i * 3] = random();
    seeds[i * 3 + 1] = 0.5 + random();
    seeds[i * 3 + 2] = random();
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("seed", new THREE.BufferAttribute(seeds, 3));

  const uniforms = {
    time: { value: 0 },
    size: { value: preset.size },
    opacity: { value: preset.opacity },
    color: { value: new THREE.Color(preset.color) },
    velocity: { value: new THREE.Vector3(...preset.velocity) },
    sway: { value: preset.sway },
    glint: { value: preset.glint },
    shape: { value: preset.shape || 0 },
    lower: { value: new THREE.Vector3(box[0][0], box[1][0], box[2][0]) },
    extent: { value: new THREE.Vector3(box[0][1] - box[0][0], box[1][1] - box[1][0], box[2][1] - box[2][0]) },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: `
      attribute vec3 seed;
      uniform float time;
      uniform float size;
      uniform vec3 velocity;
      uniform float sway;
      uniform float glint;
      uniform vec3 lower;
      uniform vec3 extent;
      varying float vGlow;
      void main() {
        float t = time * 0.001;
        vec3 p = position - lower;
        p.x = mod(p.x + t * velocity.x * seed.y + sin(t * 0.3 * seed.y + seed.z * 6.2832) * sway, extent.x);
        p.y = mod(p.y + t * velocity.y * seed.y, extent.y);
        p.z += sin(t * 0.21 + seed.x * 6.2832) * 0.6;
        // Aucun grain ne naît ni ne disparaît d'un coup : il s'estompe aux bords de sa boîte.
        vec2 at = p.xy / extent.xy;
        float edge = smoothstep(0.0, 0.08, at.x) * (1.0 - smoothstep(0.92, 1.0, at.x))
                   * smoothstep(0.0, 0.12, at.y) * (1.0 - smoothstep(0.88, 1.0, at.y));
        float twinkle = pow(0.5 + 0.5 * sin(t * (0.6 + seed.y) + seed.z * 6.2832), 4.0);
        vGlow = edge * mix(1.0, 0.25 + 0.75 * twinkle, glint);
        vec4 view = modelViewMatrix * vec4(p + lower, 1.0);
        gl_PointSize = size * (0.4 + seed.x * 0.8) / -view.z;
        gl_Position = projectionMatrix * view;
      }`,
    fragmentShader: `
      uniform vec3 color;
      uniform float opacity;
      uniform float shape;
      varying float vGlow;
      void main() {
        vec2 c = gl_PointCoord - 0.5;
        // « round » et non « dot » : ce nom masquerait la fonction GLSL du même nom.
        float round = 1.0 - smoothstep(0.0, 0.5, length(c));
        float streak = (1.0 - smoothstep(0.0, 0.08, abs(c.x))) * (1.0 - smoothstep(0.3, 0.5, abs(c.y)));
        float alpha = mix(round, streak, shape) * vGlow * opacity;
        gl_FragColor = vec4(color, alpha);
        #include <colorspace_fragment>
      }`,
    transparent: true,
    depthWrite: false,
    blending: preset.glow ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  points.renderOrder = 5;

  return {
    points,
    update(time) {
      uniforms.time.value = time;
    },
  };
}
