import { makeRingRuntime } from "./premium3d/ring.js";
import { makeHourglassRuntime } from "./premium3d/hourglass.js";
import { makeWaveRuntime } from "./premium3d/wave.js";
import { makeBeadsRuntime } from "./premium3d/beads.js";
import { makeBarsRuntime } from "./premium3d/bars.js";
import { makeSpiralRuntime } from "./premium3d/spiral.js";
import { makeCelestialRuntime } from "./premium3d/celestial.js";

// Bougie reste volontairement un rendu Canvas procédural : c'est la silhouette
// mince validée par l'utilisateur. L'ajouter ici réintroduirait un remplacement
// asynchrone par un second objet, donc une rupture visuelle et un coût GPU inutile.
const SUPPORTED = new Set(["ring", "hourglass", "wave", "beads", "moon", "bars", "spiral", "sun"]);

function createStudioEnvironment(THREE, renderer, mobile) {
  const environmentScene = new THREE.Scene();
  environmentScene.background = new THREE.Color(0x0b0f16);

  const room = new THREE.Mesh(
    new THREE.BoxGeometry(16, 10, 16),
    new THREE.MeshBasicMaterial({ color: 0x151b24, side: THREE.BackSide }),
  );
  environmentScene.add(room);

  const panels = [
    { position: [-4.6, 2.7, 3.2], size: [4.8, 2.8], color: 0xffefd6 },
    { position: [4.2, 1.5, 1.8], size: [3.2, 5.4], color: 0x99c7ff },
    { position: [0, -3.4, 1.7], size: [6.4, 2.1], color: 0xffb66c },
    { position: [0, 3.5, -3.8], size: [5.6, 2.0], color: 0xdce8ff },
  ];
  for (const spec of panels) {
    const panel = new THREE.Mesh(
      new THREE.PlaneGeometry(spec.size[0], spec.size[1]),
      new THREE.MeshBasicMaterial({ color: spec.color, side: THREE.DoubleSide }),
    );
    panel.position.set(...spec.position);
    panel.lookAt(0, 0, 0);
    environmentScene.add(panel);
  }

  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileCubemapShader();
  const target = pmrem.fromScene(environmentScene, mobile ? 0.08 : 0.04, 0.1, 30);
  pmrem.dispose();
  environmentScene.traverse((node) => {
    node.geometry?.dispose?.();
    if (Array.isArray(node.material)) {
      for (const material of node.material) material.dispose();
    } else {
      node.material?.dispose?.();
    }
  });
  return target;
}

function createStudioBackdrop(THREE) {
  const source = document.createElement("canvas");
  source.width = 512;
  source.height = 512;
  const context = source.getContext("2d");
  if (!context) return null;

  const gradient = context.createRadialGradient(256, 205, 18, 256, 255, 360);
  gradient.addColorStop(0, "rgba(105, 137, 190, 0.27)");
  gradient.addColorStop(0.4, "rgba(30, 40, 58, 0.19)");
  gradient.addColorStop(0.72, "rgba(10, 14, 22, 0.11)");
  gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, source.width, source.height);

  const texture = new THREE.CanvasTexture(source);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    opacity: 0.9,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(8.8, 6.6), material);
  plane.position.z = -3.25;
  plane.renderOrder = -10;
  return { plane, texture, material };
}

async function boot() {
  const app = document.querySelector("#focus-app");
  const visual = document.querySelector("#visual-wrap");
  const fallbackCanvas = document.querySelector("#timer-canvas");
  const progressNode = document.querySelector("#digital-progress");
  const liveChip = document.querySelector("#live-chip");
  if (!app || !visual || !fallbackCanvas || !progressNode) return;

  let started = false;
  let observer;
  const start = async () => {
    if (started) return;
    started = true;
    observer?.disconnect();
    const canvas = document.createElement("canvas");
    canvas.className = "premium-3d-canvas";
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.cssText = [
      "position:absolute",
      "inset:0",
      "width:100%",
      "height:100%",
      "max-width:none",
      "max-height:none",
      "pointer-events:none",
      "display:none",
      "z-index:1",
    ].join(";");
    visual.prepend(canvas);

    let THREE;
    try {
      THREE = await import(new URL("../vendor/three.module.js", import.meta.url).href);
    } catch (_) {
      app.dataset.renderer3d = "fallback";
      app.dataset.renderer3dReason = "three-module-load";
      canvas.remove();
      return;
    }

    createRuntime(THREE, app, visual, canvas, fallbackCanvas, progressNode, liveChip);
  };
  const maybeStart = () => {
    const mode = visual.dataset.mode || app.dataset.mode;
    if (SUPPORTED.has(mode)) start();
  };

  if (SUPPORTED.has(visual.dataset.mode || app.dataset.mode)) {
    await start();
  } else {
    observer = new MutationObserver(maybeStart);
    observer.observe(visual, { attributes: true, attributeFilter: ["data-mode"] });
    observer.observe(app, { attributes: true, attributeFilter: ["data-mode"] });
    window.addEventListener("pagehide", () => observer?.disconnect(), { once: true });
  }
}

function createRuntime(THREE, app, visual, canvas, fallbackCanvas, progressNode, liveChip) {
  const mobile = matchMedia("(max-width: 700px)").matches;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let renderer;

  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: !mobile,
      powerPreference: "high-performance",
      premultipliedAlpha: true,
    });
  } catch (_) {
    app.dataset.renderer3d = "fallback";
    app.dataset.renderer3dReason = "webgl-init";
    canvas.remove();
    return;
  }

  renderer.setClearColor(0x000000, 0);
  // Un DPR élevé doublait presque le coût GPU sans différence perceptible dans la
  // scène du minuteur. La définition reste nette, y compris sur écran Retina.
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.1 : 1.35));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  renderer.shadowMap.enabled = !mobile;
  renderer.shadowMap.type = THREE.PCFShadowMap;

  const scene = new THREE.Scene();
  let studioEnvironment = null;
  try {
    studioEnvironment = createStudioEnvironment(THREE, renderer, mobile);
    scene.environment = studioEnvironment.texture;
    scene.environmentIntensity = mobile ? 0.95 : 1.18;
    app.dataset.renderer3dEnvironment = "studio";
  } catch (_) {
    app.dataset.renderer3dEnvironment = "direct-lights";
  }

  const backdrop = createStudioBackdrop(THREE);
  if (backdrop) scene.add(backdrop.plane);

  const camera = new THREE.PerspectiveCamera(mobile ? 34 : 31, 1, 0.1, 40);
  camera.position.set(0, 0.08, mobile ? 8.85 : 8.4);
  scene.add(camera);

  const root = new THREE.Group();
  scene.add(root);

  const hemi = new THREE.HemisphereLight(0xc9ddff, 0x120c08, 1.55);
  const key = new THREE.DirectionalLight(0xffe8cb, 4.1);
  key.position.set(-4.2, 5.5, 6.5);
  key.castShadow = !mobile;
  key.shadow.mapSize.set(mobile ? 512 : 1024, mobile ? 512 : 1024);
  key.shadow.camera.near = 0.1;
  key.shadow.camera.far = 20;
  key.shadow.camera.left = -5;
  key.shadow.camera.right = 5;
  key.shadow.camera.top = 5;
  key.shadow.camera.bottom = -5;

  const rim = new THREE.DirectionalLight(0x84bfff, 2.2);
  rim.position.set(4.5, 2.8, -4.2);

  const fill = new THREE.PointLight(0xffaa63, 12, 14, 2);
  fill.position.set(-2.6, 0.5, 3.5);
  scene.add(hemi, key, rim, fill);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(7, 7),
    new THREE.ShadowMaterial({ color: 0x000000, opacity: 0.24 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -2.42;
  floor.receiveShadow = true;
  scene.add(floor);

  const state = {
    mode: null,
    progress: 1,
    running: false,
    finished: false,
    ambience: app.dataset.ambience,
  };

  let active = null;
  let lastWidth = 0;
  let lastHeight = 0;
  let lastRenderTime = 0;
  let raf = 0;
  let firstThreeFrame = false;
  let rimBaseHex = 0x84bfff;
  const rimBase = new THREE.Color(rimBaseHex);
  const worldTint = new THREE.Color();

  const mesh = (geometry, material, { cast = true, receive = true } = {}) => {
    const item = new THREE.Mesh(geometry, material);
    item.castShadow = cast && !mobile;
    item.receiveShadow = receive;
    return item;
  };

  const helpers = {
    mobile,
    reducedMotion,
    mesh,
    materials: {
      bronze: () => new THREE.MeshPhysicalMaterial({
        color: 0x4a3325,
        metalness: 0.82,
        roughness: 0.19,
        clearcoat: 1,
        clearcoatRoughness: 0.12,
      }),
      darkMetal: () => new THREE.MeshPhysicalMaterial({
        color: 0x16181b,
        metalness: 0.9,
        roughness: 0.2,
        clearcoat: 0.7,
      }),
      wax: () => new THREE.MeshPhysicalMaterial({
        color: 0xfff3dd,
        roughness: 0.48,
        metalness: 0,
        clearcoat: 0.22,
        clearcoatRoughness: 0.42,
        transmission: 0.035,
        thickness: 0.3,
      }),
      glass: () => new THREE.MeshPhysicalMaterial({
        color: 0xeaf7ff,
        roughness: 0.07,
        metalness: 0,
        transmission: 0.12,
        thickness: 0.36,
        ior: 1.46,
        transparent: true,
        opacity: 0.27,
        clearcoat: 1,
        clearcoatRoughness: 0.04,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
      sand: () => new THREE.MeshPhysicalMaterial({
        color: 0xdca75b,
        roughness: 0.62,
        metalness: 0.02,
        clearcoat: 0.16,
      }),
    },
  };

  const celestial = makeCelestialRuntime(THREE, helpers);
  const factories = {
    ring: () => makeRingRuntime(THREE, helpers),
    hourglass: () => makeHourglassRuntime(THREE, helpers, state),
    wave: () => makeWaveRuntime(THREE, helpers, state),
    beads: () => makeBeadsRuntime(THREE, helpers),
    moon: celestial.moon,
    bars: () => makeBarsRuntime(THREE, helpers),
    spiral: () => makeSpiralRuntime(THREE, helpers),
    sun: celestial.sun,
  };

  function dispose(target) {
    if (!target) return;
    const geometries = new Set();
    const materials = new Set();
    const textures = new Set();
    target.traverse((node) => {
      if (node.geometry) geometries.add(node.geometry);
      const nodeMaterials = node.material
        ? (Array.isArray(node.material) ? node.material : [node.material])
        : [];
      for (const material of nodeMaterials) {
        materials.add(material);
        if (material.map) textures.add(material.map);
      }
    });
    for (const geometry of geometries) geometry.dispose();
    for (const texture of textures) texture.dispose();
    for (const material of materials) material.dispose();
    root.remove(target);
  }

  function configureLighting(mode) {
    key.color.set(0xffe8cb);
    rimBaseHex = 0x84bfff;
    rim.color.set(rimBaseHex);
    fill.color.set(0xffaa63);

    hemi.intensity = mode === "moon" ? 0.14 : mode === "sun" ? 0.5 : 1.55;
    key.intensity = mode === "moon" ? 0.04 : mode === "sun" ? 0.3 : 4.1;
    rim.intensity = mode === "moon" ? 0.42 : mode === "sun" ? 0.55 : 2.2;
    fill.intensity = mode === "candle" ? 4 : ["sun", "moon"].includes(mode) ? 0 : 12;
    floor.visible = !["candle", "sun", "moon"].includes(mode);
    // La bougie possède déjà sa lumière et son assise sombre : une shadow-map de
    // 1024 px sur chaque image n'ajoutait rien, mais coûtait beaucoup.
    key.castShadow = !mobile && !["candle", "moon", "sun"].includes(mode);
    floor.receiveShadow = key.castShadow;

    if (mode === "wave") {
      key.color.set(0xdff8ff);
      rimBaseHex = 0x62d8ff;
      rim.color.set(rimBaseHex);
      fill.color.set(0x3da8c9);
      key.intensity = 3.2;
      rim.intensity = 2.8;
      fill.intensity = 7;
    } else if (["ring", "bars", "spiral"].includes(mode)) {
      key.color.set(0xf7f3e9);
      rimBaseHex = 0x8fb8ff;
      rim.color.set(rimBaseHex);
      fill.color.set(0xe2a55b);
      key.intensity = 4.5;
      rim.intensity = 2.5;
      fill.intensity = 7.5;
    }
  }

  function setMode(mode) {
    if (state.mode === mode) return;
    state.mode = mode;
    const supported = SUPPORTED.has(mode);
    visual.dataset.premium3d = String(supported);
    app.dataset.renderer3d = supported ? "three" : "canvas";

    if (active) {
      dispose(active.object);
      active = null;
    }

    firstThreeFrame = false;
    lastRenderTime = 0;
    fallbackCanvas.style.opacity = "1";
    fallbackCanvas.style.visibility = "visible";
    canvas.style.display = supported ? "block" : "none";

    if (!supported) return;

    active = factories[mode]();
    root.add(active.object);
    configureLighting(mode);
  }

  function readState() {
    const mode = visual.dataset.mode || app.dataset.mode;
    const rawProgress = Number.parseFloat(progressNode.style.getPropertyValue("--progress"));
    state.progress = Number.isFinite(rawProgress) ? Math.max(0, Math.min(1, rawProgress)) : 1;
    state.running = Boolean(liveChip?.textContent?.includes("EN DIRECT"));
    state.finished = app.dataset.finished === "true";
    state.ambience = app.dataset.ambience || state.ambience;
    setMode(mode);
  }

  function resize() {
    const rect = visual.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    if (width === lastWidth && height === lastHeight) return;
    lastWidth = width;
    lastHeight = height;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function tintWorld() {
    const style = getComputedStyle(app);
    const raw = style.getPropertyValue("--world-light").trim();
    rimBase.setHex(rimBaseHex);
    if (/^#[0-9a-f]{6}$/i.test(raw)) {
      worldTint.set(raw);
      rim.color.copy(rimBase).lerp(worldTint, 0.28);
    } else {
      rim.color.copy(rimBase);
    }
  }

  function render(time) {
    if (document.hidden) {
      raf = requestAnimationFrame(render);
      return;
    }
    readState();
    if (active) {
      // Le temps change une fois par seconde. 40 i/s en marche et 20 i/s au repos
      // suffisent largement aux flammes et évitent une boucle GPU à 60/120 i/s.
      const minimumFrameTime = state.running ? (mobile ? 34 : 24) : (mobile ? 82 : 48);
      if (firstThreeFrame && time - lastRenderTime < minimumFrameTime) {
        raf = requestAnimationFrame(render);
        return;
      }
      lastRenderTime = time;
      resize();
      tintWorld();
      active.update(state.progress, time);

      if (!reducedMotion) {
        camera.position.x = Math.sin(time * 0.00011) * 0.08;
        camera.position.y = 0.08 + Math.sin(time * 0.00008) * 0.045;
        camera.lookAt(0, -0.08, 0);
      }

      renderer.render(scene, camera);

      if (!firstThreeFrame) {
        firstThreeFrame = true;
        fallbackCanvas.style.opacity = "0";
        fallbackCanvas.style.visibility = "hidden";
      }
    }

    raf = requestAnimationFrame(render);
  }

  const observer = new ResizeObserver(() => {
    lastWidth = 0;
    lastHeight = 0;
  });
  observer.observe(visual);

  const contextLost = () => {
    cancelAnimationFrame(raf);
    fallbackCanvas.style.opacity = "1";
    fallbackCanvas.style.visibility = "visible";
    canvas.style.display = "none";
    app.dataset.renderer3d = "fallback";
    app.dataset.renderer3dReason = "context-lost";
  };
  canvas.addEventListener("webglcontextlost", contextLost, { once: true });

  window.addEventListener("pagehide", () => {
    cancelAnimationFrame(raf);
    observer.disconnect();
    if (active) dispose(active.object);
    if (backdrop) {
      backdrop.plane.geometry.dispose();
      backdrop.material.dispose();
      backdrop.texture.dispose();
      scene.remove(backdrop.plane);
    }
    studioEnvironment?.dispose();
    renderer.dispose();
  }, { once: true });

  app.dataset.renderer3d = "three-ready";
  delete app.dataset.renderer3dReason;
  raf = requestAnimationFrame(render);
}

boot().catch(() => {
  const app = document.querySelector("#focus-app");
  if (app) {
    app.dataset.renderer3d = "fallback";
    app.dataset.renderer3dReason = "premium-boot";
  }
});
