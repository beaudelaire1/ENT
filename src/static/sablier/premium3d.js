import { makeHourglassRuntime } from "./premium3d/hourglass.js";
import { makeCandleRuntime } from "./premium3d/candle.js";
import { makeBeadsRuntime } from "./premium3d/beads.js";
import { makeCelestialRuntime } from "./premium3d/celestial.js";

const SUPPORTED = new Set(["hourglass", "candle", "beads", "moon", "sun"]);

async function boot() {
  const app = document.querySelector("#focus-app");
  const visual = document.querySelector("#visual-wrap");
  const fallbackCanvas = document.querySelector("#timer-canvas");
  const progressNode = document.querySelector("#digital-progress");
  const liveChip = document.querySelector("#live-chip");
  if (!app || !visual || !fallbackCanvas || !progressNode) return;

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
    canvas.remove();
    return;
  }

  createRuntime(THREE, app, visual, canvas, fallbackCanvas, progressNode, liveChip);
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
    canvas.remove();
    return;
  }

  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.2 : 1.65));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  renderer.shadowMap.enabled = !mobile;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
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
  let raf = 0;
  let firstThreeFrame = false;

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
    hourglass: () => makeHourglassRuntime(THREE, helpers, state),
    candle: () => makeCandleRuntime(THREE, helpers, state),
    beads: () => makeBeadsRuntime(THREE, helpers),
    moon: celestial.moon,
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
    hemi.intensity = mode === "moon" ? 0.14 : mode === "sun" ? 0.5 : 1.55;
    key.intensity = mode === "moon" ? 0.04 : mode === "sun" ? 0.3 : 4.1;
    rim.intensity = mode === "moon" ? 0.42 : mode === "sun" ? 0.55 : 2.2;
    fill.intensity = mode === "candle" ? 4 : ["sun", "moon"].includes(mode) ? 0 : 12;
    floor.visible = !["sun", "moon"].includes(mode);
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
    if (/^#[0-9a-f]{6}$/i.test(raw)) {
      rim.color.set(raw).lerp(new THREE.Color(0x7aaeff), 0.55);
    }
  }

  function render(time) {
    readState();
    if (active) {
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
  };
  canvas.addEventListener("webglcontextlost", contextLost, { once: true });

  window.addEventListener("pagehide", () => {
    cancelAnimationFrame(raf);
    observer.disconnect();
    if (active) dispose(active.object);
    renderer.dispose();
  }, { once: true });

  app.dataset.renderer3d = "three-ready";
  raf = requestAnimationFrame(render);
}

boot().catch(() => {
  const app = document.querySelector("#focus-app");
  if (app) app.dataset.renderer3d = "fallback";
});
