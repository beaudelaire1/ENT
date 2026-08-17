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
import { makeRingRuntime } from "./premium3d/ring.js";
import { makeHourglassRuntime } from "./premium3d/hourglass.js";
import { makeWaveRuntime } from "./premium3d/wave.js";
import { makeCandleRuntime } from "./premium3d/candle.js";
import { makeBeadsRuntime } from "./premium3d/beads.js";
import { makeBarsRuntime } from "./premium3d/bars.js";
import { makeSpiralRuntime } from "./premium3d/spiral.js";
import { makeCelestialRuntime } from "./premium3d/celestial.js";
import { buildWorld } from "./premium3d/worlds.js";
import { buildEnvironment } from "./premium3d/environment.js";
import { createPostFX } from "./premium3d/postfx.js";
import { disposeTextures, radialSprite } from "./premium3d/textures.js";

// Neuf des onze visualisations sont des objets en volume. Anneau, marée, colonnes et
// spirale viennent du travail mené en parallèle sur `main`, où ils étaient rendus dans un
// studio neutre : ils entrent ici dans le lieu choisi par l'utilisateur, sous sa lumière,
// comme les cinq autres. Digital et Zen restent du texte et des cercles HTML — ce sont
// des lectures de l'heure, pas des objets.
// La bougie n'est pas de la liste : la sienne est une photographie, à fond transparent,
// que l'utilisateur reconnaît et a demandé à garder. Elle se dessine sur son canvas
// au-dessus de l'univers rendu — le lieu derrière elle reste un lieu en volume, avec sa
// lumière et sa brume. Un objet photographié dans une scène rendue n'est pas une
// régression : c'est le même partage du travail que pour Digital et Zen, où la 3D tient
// le lieu et le reste tient l'objet.
const SUPPORTED = new Set([
  "ring", "hourglass", "wave", "beads", "bars", "spiral", "moon", "sun",
]);

// Les astres ne se posent pas. Un sablier, une bougie ou un mâlâ appartiennent au sol du
// lieu ; la Lune et le Soleil appartiennent à son ciel. Les traiter pareillement — même
// cadrage, même rattrapage au sol — donnait une Lune de cinq mètres posée sur le sable à
// hauteur d'œil, dans un monde qui a déjà sa lune au ciel.
const SKYBORNE = new Set(["moon", "sun"]);

// `decorDensity` ne règle que le mouvement. Le lieu, lui, reste entier à tous les niveaux.
const MOTION = { 0: 0, 1: 0.4, 2: 0.72, 3: 1 };

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
    // Le motif est consigné dans le DOM : un repli silencieux est indiscernable d'un
    // rendu réussi, et c'est exactement ce qui avait laissé passer un moteur 3D mort.
    app.dataset.renderer3d = "fallback";
    app.dataset.renderer3dReason = "three-module-load";
    canvas.remove();
    return;
  }

  try {
    createRuntime(THREE, { app, stage, visual, canvas, decorCanvas, fallbackCanvas, progressNode, liveChip });
  } catch (_) {
    app.dataset.renderer3d = "fallback";
    app.dataset.renderer3dReason = "runtime-boot";
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
    app.dataset.renderer3dReason = "webgl-context";
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
  const camera = new THREE.PerspectiveCamera(45, 1, 0.4, 9000);
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

  // Occlusion de contact. Ce n'est pas un socle : c'est l'ombre courte que tout objet
  // creuse sous lui en interceptant la lumière du ciel. Sans elle, une bougie posée sur un
  // sol plat semble flotter, même quand son pied touche exactement le sol — l'ombre
  // portée part de côté et rien ne rattache l'objet à sa base. Un meuble ajouterait un
  // objet à la scène ; ceci n'ajoute qu'un assombrissement.
  const contact = new THREE.Mesh(
    new THREE.PlaneGeometry(1, 1),
    new THREE.MeshBasicMaterial({
      map: radialSprite(THREE, [
        ["rgba(0,0,0,.85)", 0],
        ["rgba(0,0,0,.4)", 0.34],
        ["rgba(0,0,0,0)", 1],
      ]),
      transparent: true,
      depthWrite: false,
      opacity: 0.85,
    }),
  );
  contact.rotation.x = -Math.PI / 2;
  contact.renderOrder = 1;
  scene.add(contact);

  const state = { mode: null, world: null, progress: 1, running: false, finished: false, motion: 1 };
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
    ring: () => makeRingRuntime(THREE, helpers, state),
    hourglass: () => makeHourglassRuntime(THREE, helpers, state),
    wave: () => makeWaveRuntime(THREE, helpers, state),
    // Bougie en volume : conservée et prête, mais absente de `SUPPORTED` — c'est la
    // photographie qui tient ce rôle. Rebrancher l'une ou l'autre ne tient qu'à cette liste.
    candle: () => makeCandleRuntime(THREE, helpers, state),
    beads: () => makeBeadsRuntime(THREE, helpers),
    bars: () => makeBarsRuntime(THREE, helpers, state),
    spiral: () => makeSpiralRuntime(THREE, helpers, state),
    moon: celestial.moon,
    sun: celestial.sun,
  };

  // Silhouette d'un objet dans ses propres unités : point le plus bas, hauteur, rayon.
  // Mesurée sur la géométrie plutôt que déclarée à la main — huit objets, chacun avec son
  // propre profil, et une constante oubliée suffit à faire flotter l'un d'eux au-dessus de
  // son ombre. Les sprites en sont exclus : une flamme ou un halo débordent largement du
  // corps sans jamais toucher le sol.
  //
  // La mesure se fait *avant* d'attacher l'objet au support, tant qu'il n'a pas de parent :
  // sa matrice monde est alors sa matrice locale. Mesuré une fois attaché, il rapportait un
  // encombrement déjà multiplié par l'échelle du mode précédent, et le cadrage dérivait à
  // chaque changement d'objet — un sablier finissait par sortir du cadre par le haut.
  const bounds = new THREE.Box3();
  const corner = new THREE.Vector3();
  function measure(target) {
    bounds.makeEmpty();
    target.updateMatrixWorld(true);
    target.traverse((node) => {
      if (!node.isMesh || node.isSprite) return;
      bounds.expandByObject(node);
    });
    if (bounds.isEmpty()) return { base: -OBJECT_HEIGHT / 2, height: OBJECT_HEIGHT, radius: 1.6 };
    bounds.getSize(corner);
    return {
      base: bounds.min.y,
      // Hauteur réelle de la silhouette. La supposer identique pour tous les objets —
      // une constante de référence — cadrait juste ceux qui la respectaient : un sablier
      // dont le bâti monte plus haut sortait du cadre par le haut, tandis qu'un objet
      // plus ramassé s'y perdait au milieu.
      height: Math.max(corner.y, 0.001),
      radius: Math.max(Math.abs(bounds.min.x), bounds.max.x, Math.abs(bounds.min.z), bounds.max.z),
    };
  }

  function dispose(target) {
    if (!target) return;
    const geometries = new Set(), materials = new Set(), textures = new Set();
    target.traverse((node) => {
      if (node.geometry) geometries.add(node.geometry);
      const list = node.material ? (Array.isArray(node.material) ? node.material : [node.material]) : [];
      for (const material of list) {
        materials.add(material);
        for (const value of Object.values(material)) {
          // Les cartes du cache servent à tous les univers : les libérer ici forçait un
          // réenvoi complet vers la carte graphique au changement d'ambiance, pour des
          // textures que le cache continuait pourtant de distribuer.
          if (value?.isTexture && value.userData?.shared !== true) textures.add(value);
        }
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
    // Les nuits demandent une pose plus longue que les jours — et davantage qu'avant :
    // tant que le halo réappliquait la courbe sRGB sur une image déjà encodée, les tons
    // moyens remontaient artificiellement. La chaîne corrigée rend leurs vrais noirs, il
    // faut donc ouvrir franchement.
    const exposure = currentWorld.env.exposure
      ?? (currentWorld.env.kind === "day" ? 0.4 : 2);
    renderer.toneMappingExposure = exposure;
    post?.setExposure(exposure);

    // L'appoint reste discret : trop clair, il éclaire le sol plus fort que le ciel qui
    // le surplombe et l'horizon se casse en deux bandes franches.
    const shade = new THREE.Color(fogColor);
    ambient.color.copy(shade).lerp(new THREE.Color(0xffffff), 0.22);
    ambient.groundColor.copy(shade).multiplyScalar(0.3);
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
    syncFallback();
    if (!supported) return;

    active = factories[mode]();
    active.footprint = measure(active.object);
    objectRoot.add(active.object);
  }

  // Digital et Zen n'ont pas d'objet en volume : leur lecture de l'heure reste en HTML,
  // par-dessus l'univers rendu qui leur sert de lieu.
  //
  // Les neuf autres ne prennent la place du dessin 2D qu'une fois la première image 3D
  // réellement à l'écran. Les masquer dès le choix du mode laissait un intervalle — le
  // temps de bâtir le lieu — où le dessin 2D s'affichait puis disparaissait d'un coup :
  // l'utilisateur voyait « l'ancienne vue » clignoter avant la vraie scène.
  function syncFallback() {
    const handedOver = ready && SUPPORTED.has(state.mode);
    fallbackCanvas.style.opacity = handedOver ? "0" : "1";
    fallbackCanvas.style.visibility = handedOver ? "hidden" : "visible";
  }

  // Place et dimensionne l'objet pour qu'il occupe exactement la zone `#visual-wrap`.
  function frameObject() {
    const stageRect = stage.getBoundingClientRect();
    const wrapRect = visual.getBoundingClientRect();
    if (!stageRect.width || !stageRect.height) return;
    // Un astre est loin. Le placer à neuf unités comme un objet de table le faisait passer
    // *devant* les immeubles et les arbres du lieu — une lune qui éclipse une tour. La
    // distance ne change pourtant rien à sa taille apparente : l'échelle est calculée à
    // partir d'elle, si bien qu'un même cadrage HTML donne le même disque à l'écran, mais
    // derrière le paysage.
    const skyborne = SKYBORNE.has(state.mode);
    const distance = skyborne ? 1500 : 9;
    const halfHeight = distance * Math.tan((camera.fov * Math.PI) / 360);
    const halfWidth = halfHeight * camera.aspect;
    const ndcX = ((wrapRect.left + wrapRect.width / 2 - stageRect.left) / stageRect.width) * 2 - 1;
    const ndcY = -(((wrapRect.top + wrapRect.height / 2 - stageRect.top) / stageRect.height) * 2 - 1);

    // Un astre se lit de loin : il occupe un peu moins que le cadre réservé à un objet de
    // premier plan, ce qui lui laisse la place de se détacher entier au-dessus du paysage.
    const fill = skyborne ? 0.6 : (mobile ? 0.94 : 0.86);
    const target = Math.min(wrapRect.width, wrapRect.height) * fill;
    const unitsPerPixel = (halfHeight * 2) / stageRect.height;
    // La hauteur mesurée de l'objet, et non une constante : c'est elle qui fait qu'un
    // cadrage HTML donne la même occupation à l'écran pour les neuf objets.
    const span = active?.footprint?.height || OBJECT_HEIGHT;
    let scale = (target * unitsPerPixel) / span;

    if (!skyborne) {
      // Un objet posé ne dispose pas de toute la hauteur de la zone HTML. Le sol se
      // projette aux deux tiers de l'image — l'horizon est à hauteur d'œil, et le point de
      // contact un peu en dessous —, si bien que la place réellement disponible va de ce
      // contact au haut du cadre. Cadré sur la zone entière, un sablier dépassait par le
      // haut : sa moitié supérieure était coupée net.
      const headroom = (camera.position.y + halfHeight) * 0.94;
      scale = Math.min(scale, headroom / span);
    }

    objectRoot.position.set(ndcX * halfWidth, camera.position.y + ndcY * halfHeight, -distance);
    objectRoot.scale.setScalar(scale);

    const half = (span / 2) * scale;
    // Chaque objet déclare le point le plus bas de sa silhouette. Les supposer tous
    // centrés sur une hauteur de référence laissait la bougie — dont la cire s'arrête
    // bien au-dessus de cette limite — flotter à un mètre de son ombre.
    const footing = (active?.footprint?.base ?? -OBJECT_HEIGHT / 2) * scale;
    const base = objectRoot.position.y + footing;
    if (skyborne) {
      // L'astre se détache entier au-dessus de l'horizon — qui se trouve exactement à
      // hauteur d'œil — sans jamais monter jusqu'à sortir du cadre. On contraint son
      // centre : contraindre son bord inférieur le chassait hors de l'image, sa
      // demi-hauteur croissant avec sa distance.
      const horizon = camera.position.y + half * 1.15;
      if (objectRoot.position.y < horizon) objectRoot.position.y = horizon;
    } else {
      // Un objet posé est *assis* sur le sol, pas seulement empêché d'y descendre. Le
      // rattrapage précédent ne relevait que ce qui s'enfonçait : une bougie dont la cire
      // s'arrête haut restait donc suspendue au-dessus de son ombre, sans que rien ne la
      // redescende. Le cadrage HTML garde la taille et la position latérale ; c'est le sol
      // qui fixe la hauteur.
      objectRoot.position.y += 0.02 - base;
    }

    contact.visible = !skyborne && Boolean(active);
    if (contact.visible) {
      const spread = (active?.footprint?.radius ?? 1.6) * scale * 2;
      contact.position.set(objectRoot.position.x, 0.03, objectRoot.position.z);
      contact.scale.set(spread, spread, 1);
    }

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
    keyLight.position.copy(objectRoot.position).add(direction.multiplyScalar(22 * (skyborne ? 60 : 1)));
    bounce.position.set(
      objectRoot.position.x - 2.4 * scale,
      objectRoot.position.y + 0.6 * scale,
      objectRoot.position.z + 3.2 * scale,
    );
    // La mise au point suit l'objet : le paysage se défocalise autour de lui, qu'il soit à
    // portée de main ou à l'horizon.
    post?.focus(distance);
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
    state.motion = reducedMotion ? 0 : (MOTION[level] ?? 0.72);
    setWorld(decorNames[app.dataset.ambience] || "star_tree");
    setMode(visual.dataset.mode || app.dataset.mode);
  }

  function render(time) {
    frame = requestAnimationFrame(render);
    readState();
    resize();
    frameObject();

    currentWorld?.update(time, state.motion, state.progress);
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
      // Un seul point de bascule, une fois l'image prête : la scène 3D se révèle, le décor
      // peint s'efface et le dessin 2D cède la place, tous sur la même transition.
      ready = true;
      app.dataset.renderer3d = "three";
      canvas.style.opacity = "1";
      if (decorCanvas) decorCanvas.style.opacity = "0";
      syncFallback();
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
    ready = false;
    app.dataset.renderer3d = "fallback";
    app.dataset.renderer3dReason = "context-lost";
    canvas.style.display = "none";
    syncFallback();
    if (decorCanvas) decorCanvas.style.opacity = "";
  }, { once: true });

  window.addEventListener("pagehide", () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    post?.dispose();
    if (active) dispose(active.object);
    if (currentWorld) dispose(currentWorld.object);
    environment?.dispose();
    disposeTextures();
    renderer.dispose();
  }, { once: true });

  app.dataset.renderer3d = "three-ready";
  frame = requestAnimationFrame(render);
}

boot().catch(() => {
  const app = document.querySelector("#focus-app");
  if (!app) return;
  app.dataset.renderer3d = "fallback";
  app.dataset.renderer3dReason = "boot";
});
