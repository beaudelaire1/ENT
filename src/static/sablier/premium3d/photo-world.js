// Univers photographiques du Sablier.
//
// Un lieu bâti en cylindres, en plans de feuillage peints et en rochers à facettes reste un
// dessin, quel que soit l'éclairage posé dessus. Une photographie porte d'emblée ce
// qu'aucune composition procédurale n'a atteint : le lichen sur l'écorce, la profondeur de
// la brume, une lumière réelle. Le lieu devient donc une image, et la scène ne garde que
// ce qu'une image ne sait pas faire seule : le mouvement — une lente dérive du cadre, et
// des poussières qui traversent les rayons.
//
// La photographie ne passe ni par le tonemapping ni par le halo : elle est déjà
// développée, et la courbe du rendu la délavait. Elle est tracée en espace écran, avant
// tout le reste, sans écrire la profondeur. Les fichiers sont préparés hors ligne par
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
 * La photographie plein cadre. `focus` est le point de l'image (x, y depuis le haut) gardé
 * au centre quand le cadre la rogne ; `drift` l'amplitude de la respiration du cadre.
 */
export function photoBackdrop(THREE, { src, focus = [0.5, 0.5], drift = 0.06 }) {
  const uniforms = {
    map: { value: null },
    span: { value: new THREE.Vector2(1, 1) },
    origin: { value: new THREE.Vector2(0, 0) },
    opacity: { value: 0 },
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
      varying vec2 vUv;
      void main() {
        gl_FragColor = vec4(texture2D(map, origin + vUv * span).rgb * opacity, 1.0);
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
      console.warn("Sablier : photographie du lieu indisponible", src, error);
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

/**
 * Poussières en suspension dans la lumière. Elles vivent dans une boîte de la scène, face à
 * la caméra, montent avec l'air tiède et dérivent, puis reviennent par le bord opposé.
 */
export function motes(THREE, {
  count = 160, color = "#ffe9c4", size = 40, opacity = 0.55, seed = 11,
  box = [[-5, 9], [-2, 9], [-24, -4]],
} = {}) {
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
    size: { value: size },
    opacity: { value: opacity },
    color: { value: new THREE.Color(color) },
    lower: { value: new THREE.Vector3(box[0][0], box[1][0], box[2][0]) },
    extent: { value: new THREE.Vector3(box[0][1] - box[0][0], box[1][1] - box[1][0], box[2][1] - box[2][0]) },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: `
      attribute vec3 seed;
      uniform float time;
      uniform float size;
      uniform vec3 lower;
      uniform vec3 extent;
      varying float vGlow;
      void main() {
        float t = time * 0.001;
        vec3 p = position - lower;
        p.x = mod(p.x + t * 0.05 * seed.y + sin(t * 0.3 * seed.y + seed.z * 6.2832) * 0.5, extent.x);
        p.y = mod(p.y + t * 0.035 * seed.y, extent.y);
        p.z += sin(t * 0.21 + seed.x * 6.2832) * 0.6;
        // Aucun grain ne naît ni ne disparaît d'un coup : il s'estompe aux bords de sa boîte.
        vec2 at = p.xy / extent.xy;
        float edge = smoothstep(0.0, 0.08, at.x) * (1.0 - smoothstep(0.92, 1.0, at.x))
                   * smoothstep(0.0, 0.12, at.y) * (1.0 - smoothstep(0.88, 1.0, at.y));
        // Un grain ne brille que lorsqu'il croise un rayon : la plupart du temps il est terne.
        float glint = pow(0.5 + 0.5 * sin(t * (0.6 + seed.y) + seed.z * 6.2832), 4.0);
        vGlow = edge * (0.25 + 0.75 * glint);
        vec4 view = modelViewMatrix * vec4(p + lower, 1.0);
        gl_PointSize = size * (0.4 + seed.x * 0.8) / -view.z;
        gl_Position = projectionMatrix * view;
      }`,
    fragmentShader: `
      uniform vec3 color;
      uniform float opacity;
      varying float vGlow;
      void main() {
        float alpha = (1.0 - smoothstep(0.0, 0.5, length(gl_PointCoord - 0.5))) * vGlow * opacity;
        gl_FragColor = vec4(color, alpha);
        #include <colorspace_fragment>
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
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
