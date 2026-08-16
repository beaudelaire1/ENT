// Scène immersive du Sablier.
//
// Un seul contexte WebGL rend l'univers *et* l'objet, dans la même caméra et sous la
// même lumière. C'est la condition d'un rendu crédible : tant que le décor était peint
// en 2D derrière un objet éclairé à part, l'objet restait posé sur une image. Ici le
// ciel de l'univers est la source lumineuse de l'objet, la brume l'enveloppe et son
// ombre tombe sur le sol du lieu.
//
// L'objet est cadré exactement dans la zone `#visual-wrap` du gabarit : la mise en page
// HTML continue de commander la composition, la 3D s'y conforme.
import { makeHourglassRuntime } from "./premium3d/hourglass.js";
import { makeCandleRuntime } from "./premium3d/candle.js";
import { makeBeadsRuntime } from "./premium3d/beads.js";
import { makeCelestialRuntime } from "./premium3d/celestial.js";
import { buildWorld } from "./premium3d/worlds.js";
import { buildEnvironment } from "./premium3d/environment.js";
import { createPostFX } from "./premium3d/postfx.js";

const SUPPORTED = new Set(["hourglass", "candle", "beads", "moon", "sun"]);
const DENSITY = { 0: 0, 1: 0.4, 2: 0.72, 3: 1 };

// Hauteur de référence des objets, en unités de scène. Elle sert à convertir la taille
// en pixels de `#visual-wrap` en échelle 3D.
const OBJECT_HEIGHT = 5.2;

async function boot() {
  const app = document.querySelector("#focus-app");
  const stage = document.querySelector("#focus-stage");
  const visual = document.querySelector("#visual-wrap");
  const decorCanvas = document.querySelector("#decor-canvas");
  const fallbackCanvas = document.querySelector("#timer-canvas");
  const progressNode = document.querySelector("#digital-progress");
  const liveChip = document.querySelector("#live-chip");
  if (!app || !stage || !visual || !fallbackCanvas || !progressNode) return;

  const canvas = document.createElement("canvas");
  canvas.className = "stage-3d-canvas";
  canvas.setAttribute("aria-hidden", "true");
  stage.prepend(canvas);

  let THREE;
  try {
    THREE = await import(new URL("../vendor/three.module.js", import.meta.url).href);
  } catch (_) {
    // Repli : le dessin 2D reste en place, la page continue de fonctionner.
    app.dataset.renderer3d = "fallback";
    canvas.remove();
    return;
  }

  try {
    createRuntime(THREE, { app, stage, visual, canvas, decorCanvas, fallbackCanvas, progressNode, liveChip });
  } catch (_) {
    app.dataset.renderer3d = "fallback";
    canvas.remove();
  }
}

function createRuntime(THREE, nodes) {
  const { app, stage, visual, canvas, decorCanvas, fallbackCanvas, progressNode, liveChip } = nodes;
  const mobile = matchMedia("(max-width: 700px)").matches;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const decorNames = JSON.parse(document.querySelector("#decor-data")?.textContent || "{}");

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: !mobile,
      powerPreference: "high-performance",
      alpha: false,
    });
  } catch (_) {
    app.dataset.renderer3d = "fallback";
    canvas.remove();
    return;
  }

  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.4 : 1.85));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.9;
  renderer.shadowMap.enabled = !mobile;
  renderer.shadowMap.type = THREE.PCFShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.35, 3000);
  camera.position.set(0, 1.72, 0);
  camera.rotation.order = "YXZ";

  // Lumière directe de l'univers. Son ombre ne couvre que les abords de l'objet : une
  // carte d'ombre étalée sur tout le paysage n'aurait plus aucune définition là où on
  // la regarde.
  const keyLight = new THREE.DirectionalLight(0xffffff, 3);
  keyLight.castShadow = !mobile;
  keyLight.shadow.mapSize.set(mobile ? 512 : 1536, mobile ? 512 : 1536);
  keyLight.shadow.camera.near = 0.5;
  keyLight.shadow.camera.far = 60;
  keyLight.shadow.camera.left = -8;
  keyLight.shadow.camera.right = 8;
  keyLight.shadow.camera.top = 8;
  keyLight.shadow.camera.bottom = -8;
  keyLight.shadow.bias = -0.0012;
  keyLight.shadow.normalBias = 0.035;
  scene.add(keyLight, keyLight.target);

  // Rebond d'appoint : sans lui, la face non éclairée de l'objet tombe au noir dans les
  // univers nocturnes, où la carte d'environnement porte peu d'énergie.
  const bounce = new THREE.PointLight(0xffffff, 6, 26, 2);
  scene.add(bounce);

  // Lumière d'ambiance du lieu : le ciel par-dessus, le sol qui renvoie par-dessous.
  // La carte d'environnement éclaire déjà les matières, mais elle est calculée depuis un
  // seul point ; sans ce complément, un sous-bois s'enfonce dans le noir absolu dès que
  // la canopée cache le soleil, et le sol devient un aplat sans matière.
  const ambient = new THREE.HemisphereLight(0xffffff, 0x404040, 1);
  scene.add(ambient);

  const objectRoot = new THREE.Group();
  scene.add(objectRoot);

  const state = { mode: null, world: null, progress: 1, running: false, finished: false, density: 1 };
  let active = null;
  let currentWorld = null;
  let environment = null;
  let post = null;
  let width = 0, height = 0;
  let frame = 0;
  let ready = false;

  const mesh = (geometry, material, { cast = true, receive = true } = {}) => {
    const item = new THREE.Mesh(geometry, material);
    item.castShadow = cast && !mobile;
    item.receiveShadow = receive;
    return item;
  };
  const helpers = { mobile, reducedMotion, mesh, THREE };

  const celestial = makeCelestialRuntime(THREE, helpers);
  const factories = {
    hourglass: () => makeHourglassRuntime(THREE, helpers, state),
    candle: () => makeCandleRuntime(THREE, helpers, state),
    beads: () => makeBeadsRuntime(THREE, helpers),
    moon: celestial.moon,
    sun: celestial.sun,
  };

  function dispose(target) {
    if (!target) return;
    const geometries = new Set(), materials = new Set(), textures = new Set();
    target.traverse((node) => {
      if (node.geometry) geometries.add(node.geometry);
      const list = node.material ? (Array.isArray(node.material) ? node.material : [node.material]) : [];
      for (const material of list) {
        materials.add(material);
        for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
      }
    });
    for (const geometry of geometries) geometry.dispose();
    for (const texture of textures) texture.dispose();
    for (const material of materials) material.dispose();
    target.removeFromParent();
  }

  // ── Univers ──────────────────────────────────────────────────────────────────
  function setWorld(key) {
    if (state.world === key) return;
    state.world = key;

    if (currentWorld) {
      dispose(currentWorld.object);
      currentWorld = null;
    }
    if (environment) {
      if (environment.background?.isObject3D) environment.background.removeFromParent();
      scene.environment = null;
      scene.background = null;
      environment.dispose();
      environment = null;
    }

    currentWorld = buildWorld(THREE, key, { mobile });
    scene.add(currentWorld.object);

    environment = buildEnvironment(THREE, renderer, currentWorld.env);
    scene.environment = environment.environment;
    if (environment.background.isObject3D) scene.add(environment.background);
    else scene.background = environment.background;

    const [fogColor, fogDensity] = currentWorld.fog || ["#0a1018", 0.006];
    scene.fog = new THREE.FogExp2(new THREE.Color(fogColor), fogDensity);

    // Le ciel à diffusion atmosphérique délivre une énergie physique : sans exposition
    // adaptée, un plein soleil sature toute l'image en blanc. Chaque univers porte donc
    // la sienne, comme on choisirait un temps de pose.
    renderer.toneMappingExposure = currentWorld.env.exposure
      ?? (currentWorld.env.kind === "day" ? 0.4 : 0.95);

    const shade = new THREE.Color(fogColor);
    ambient.color.copy(shade).lerp(new THREE.Color(0xffffff), 0.45);
    ambient.groundColor.copy(shade).multiplyScalar(0.45);
    ambient.intensity = currentWorld.env.ambient ?? (currentWorld.env.kind === "day" ? 1.6 : 0.7);

    const sun = environment.sun;
    keyLight.color.set(sun.color);
    keyLight.intensity = sun.intensity;
    keyLight.position.copy(sun.direction).multiplyScalar(40);
    bounce.color.set(sun.color);
    bounce.intensity = currentWorld.env.kind === "day" ? 3 : 8;
  }

  // ── Objet ────────────────────────────────────────────────────────────────────
  function setMode(mode) {
    if (state.mode === mode) return;
    state.mode = mode;
    const supported = SUPPORTED.has(mode);
    visual.dataset.premium3d = String(supported);

    if (active) {
      dispose(active.object);
      active = null;
    }
    // Les visualisations restées en 2D (anneau, marée, colonnes, spirale…) gardent leur
    // canvas : elles se dessinent alors par-dessus l'univers rendu, qui leur sert de lieu.
    fallbackCanvas.style.opacity = supported ? "0" : "1";
    fallbackCanvas.style.visibility = supported ? "hidden" : "visible";
    if (!supported) return;

    active = factories[mode]();
    objectRoot.add(active.object);
  }

  // Place et dimensionne l'objet pour qu'il occupe exactement la zone `#visual-wrap`.
  function frameObject() {
    const stageRect = stage.getBoundingClientRect();
    const wrapRect = visual.getBoundingClientRect();
    if (!stageRect.width || !stageRect.height) return;
    const distance = 9;
    const halfHeight = distance * Math.tan((camera.fov * Math.PI) / 360);
    const halfWidth = halfHeight * camera.aspect;
    const ndcX = ((wrapRect.left + wrapRect.width / 2 - stageRect.left) / stageRect.width) * 2 - 1;
    const ndcY = -(((wrapRect.top + wrapRect.height / 2 - stageRect.top) / stageRect.height) * 2 - 1);

    const target = Math.min(wrapRect.width, wrapRect.height) * (mobile ? 0.94 : 0.86);
    const unitsPerPixel = (halfHeight * 2) / stageRect.height;
    const scale = (target * unitsPerPixel) / OBJECT_HEIGHT;

    objectRoot.position.set(ndcX * halfWidth, camera.position.y + ndcY * halfHeight, -distance);
    objectRoot.scale.setScalar(scale);
    // Le cadrage HTML donne la hauteur idéale ; le sol du lieu a le dernier mot. Sans
    // ce rattrapage, le pied de l'objet passait sous la surface et l'objet semblait
    // enfoncé dans le sable au lieu d'y être posé.
    const base = objectRoot.position.y - (OBJECT_HEIGHT / 2) * scale;
    if (base < 0.04) objectRoot.position.y += 0.04 - base;

    // La lumière clé vise l'objet : c'est lui qui doit être défini, pas l'horizon.
    keyLight.target.position.copy(objectRoot.position);
    keyLight.target.updateMatrixWorld();
    // Un soleil rasant — un couchant du Sahara à trois degrés — projetterait une ombre
    // de soixante mètres, hors du champ de la carte d'ombre : l'objet paraîtrait flotter.
    // On garde l'azimut du soleil, qui donne la direction de la lumière, mais on relève
    // sa hauteur pour que l'ombre retombe au pied de l'objet.
    const direction = environment
      ? environment.sun.direction.clone()
      : new THREE.Vector3(0.4, 0.8, 0.45);
    if (direction.y < 0.52) {
      direction.y = 0.52;
      direction.normalize();
    }
    keyLight.position.copy(objectRoot.position).add(direction.multiplyScalar(22));
    bounce.position.set(
      objectRoot.position.x - 2.4 * scale,
      objectRoot.position.y + 0.6 * scale,
      objectRoot.position.z + 3.2 * scale,
    );
  }

  function resize() {
    const rect = stage.getBoundingClientRect();
    const nextWidth = Math.max(1, Math.round(rect.width));
    const nextHeight = Math.max(1, Math.round(rect.height));
    if (nextWidth === width && nextHeight === height) return;
    width = nextWidth;
    height = nextHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    post?.setSize(width, height);
  }

  function readState() {
    const raw = Number.parseFloat(progressNode.style.getPropertyValue("--progress"));
    state.progress = Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 1;
    state.running = Boolean(liveChip?.textContent?.includes("EN DIRECT"));
    state.finished = app.dataset.finished === "true";
    const level = Number(app.dataset.decorDensity ?? 2);
    state.density = reducedMotion ? 0 : (DENSITY[level] ?? 0.72);
    setWorld(decorNames[app.dataset.ambience] || "star_tree");
    setMode(visual.dataset.mode || app.dataset.mode);
  }

  function render(time) {
    frame = requestAnimationFrame(render);
    readState();
    resize();
    frameObject();

    currentWorld?.update(time, state.density, state.progress);
    active?.update(state.progress, time);

    if (!reducedMotion) {
      // Respiration de la caméra : quelques dixièmes de degré suffisent à sortir la
      // scène de la fixité d'une image de synthèse.
      camera.rotation.y = Math.sin(time * 0.00009) * 0.012;
      camera.rotation.x = -0.02 + Math.sin(time * 0.00007) * 0.006;
    }

    if (post) post.render();
    else renderer.render(scene, camera);

    if (!ready) {
      ready = true;
      app.dataset.renderer3d = "three";
      if (decorCanvas) decorCanvas.style.opacity = "0";
    }
  }

  resize();
  readState();
  post = createPostFX(THREE, { renderer, scene, camera, width, height, mobile });

  const observer = new ResizeObserver(() => { width = 0; height = 0; });
  observer.observe(stage);

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    cancelAnimationFrame(frame);
    app.dataset.renderer3d = "fallback";
    canvas.style.display = "none";
    fallbackCanvas.style.opacity = "1";
    fallbackCanvas.style.visibility = "visible";
    if (decorCanvas) decorCanvas.style.opacity = "";
  }, { once: true });

  window.addEventListener("pagehide", () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    post?.dispose();
    if (active) dispose(active.object);
    if (currentWorld) dispose(currentWorld.object);
    environment?.dispose();
    renderer.dispose();
  }, { once: true });

  app.dataset.renderer3d = "three-ready";
  frame = requestAnimationFrame(render);
}

boot().catch(() => {
  const app = document.querySelector("#focus-app");
  if (app) app.dataset.renderer3d = "fallback";
});
