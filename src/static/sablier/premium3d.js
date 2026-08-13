import { makeHourglassRuntime } from "./premium3d/hourglass.js";
import { makeCandleRuntime } from "./premium3d/candle.js";
import { makeBeadsRuntime } from "./premium3d/beads.js";
import { makeCelestialRuntime } from "./premium3d/celestial.js";

const SUPPORTED = new Set(["hourglass", "candle", "beads", "moon", "sun"]);

function boot() {
  const app = document.querySelector("#focus-app");
  const canvas = document.querySelector("#premium-3d-canvas");
  const visual = document.querySelector("#visual-wrap");
  if (!app || !canvas || !visual || !app.dataset.threeUrl) return;
  import(app.dataset.threeUrl)
    .then((THREE) => createRuntime(THREE, app, canvas, visual))
    .catch(() => fallback(app, visual));
}

function fallback(app, visual) {
  app.dataset.renderer3d = "fallback";
  visual.dataset.premium3d = "false";
}

function createRuntime(THREE, app, canvas, visual) {
  const mobile = matchMedia("(max-width: 700px)").matches;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: !mobile, powerPreference: "high-performance" });
  } catch (_) {
    fallback(app, visual);
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
  const camera = new THREE.PerspectiveCamera(31, 1, 0.1, 40);
  camera.position.set(0, 0.1, 8.4);
  scene.add(camera);
  const root = new THREE.Group();
  scene.add(root);

  const hemi = new THREE.HemisphereLight(0xc9ddff, 0x120c08, 1.55);
  const key = new THREE.DirectionalLight(0xffe8cb, 4.1);
  key.position.set(-4.2, 5.5, 6.5);
  key.castShadow = !mobile;
  key.shadow.mapSize.set(mobile ? 512 : 1024, mobile ? 512 : 1024);
  Object.assign(key.shadow.camera, { near: 0.1, far: 20, left: -5, right: 5, top: 5, bottom: -5 });
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

  const state = { mode: null, progress: 1, running: false, finished: false, warning: false, ambience: app.dataset.ambience };
  let active = null;
  let lastWidth = 0;
  let lastHeight = 0;

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
      bronze: () => new THREE.MeshPhysicalMaterial({ color: 0x4a3325, metalness: 0.82, roughness: 0.19, clearcoat: 1, clearcoatRoughness: 0.12 }),
      darkMetal: () => new THREE.MeshPhysicalMaterial({ color: 0x16181b, metalness: 0.9, roughness: 0.2, clearcoat: 0.7 }),
      wax: () => new THREE.MeshPhysicalMaterial({ color: 0xfff3dd, roughness: 0.48, clearcoat: 0.22, clearcoatRoughness: 0.42, transmission: 0.035, thickness: 0.3 }),
      glass: () => new THREE.MeshPhysicalMaterial({ color: 0xeaf7ff, roughness: 0.07, transmission: 0.12, thickness: 0.36, ior: 1.46, transparent: true, opacity: 0.27, clearcoat: 1, clearcoatRoughness: 0.04, side: THREE.DoubleSide, depthWrite: false }),
      sand: () => new THREE.MeshPhysicalMaterial({ color: 0xdca75b, roughness: 0.62, metalness: 0.02, clearcoat: 0.16 }),
    },
  };

  const factories = {
    hourglass: () => makeHourglassRuntime(THREE, helpers, state),
    candle: () => makeCandleRuntime(THREE, helpers, state),
    beads: () => makeBeadsRuntime(THREE, helpers, state),
    ...makeCelestialRuntime(THREE, helpers, state),
  };

  function dispose(target) {
    if (!target) return;
    target.traverse((node) => {
      node.geometry?.dispose?.();
      const materials = node.material ? (Array.isArray(node.material) ? node.material : [node.material]) : [];
      for (const material of materials) {
        material.map?.dispose?.();
        material.dispose?.();
      }
    });
    root.remove(target);
  }

  function configureLighting(mode) {
    hemi.intensity = mode === "moon" ? 0.18 : mode === "sun" ? 0.52 : 1.55;
    key.intensity = mode === "moon" ? 0.08 : mode === "sun" ? 0.4 : 4.1;
    rim.intensity = mode === "moon" ? 0.55 : mode === "sun" ? 0.6 : 2.2;
    fill.intensity = mode === "candle" ? 5 : ["sun", "moon"].includes(mode) ? 0 : 12;
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
    if (!supported) return;
    active = factories[mode]();
    root.add(active.object);
    configureLighting(mode);
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
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
    const raw = getComputedStyle(app).getPropertyValue("--world-light").trim();
    if (/^#[0-9a-f]{6}$/i.test(raw)) rim.color.set(raw).lerp(new THREE.Color(0x7aaeff), 0.55);
  }

  function render(time) {
    if (!active) return;
    resize();
    tintWorld();
    active.update(state.progress, time);
    if (!reducedMotion) {
      camera.position.x = Math.sin(time * 0.00011) * 0.08;
      camera.position.y = 0.1 + Math.sin(time * 0.00008) * 0.045;
      camera.lookAt(0, -0.08, 0);
    }
    renderer.render(scene, camera);
  }

  app.addEventListener("sablier:frame", (event) => {
    const detail = event.detail || {};
    state.progress = Number.isFinite(detail.progress) ? detail.progress : state.progress;
    state.running = Boolean(detail.running);
    state.finished = Boolean(detail.finished);
    state.warning = Boolean(detail.warning);
    state.ambience = detail.ambience || state.ambience;
    setMode(detail.mode || visual.dataset.mode);
    render(performance.now());
  });

  const observer = new ResizeObserver(() => { lastWidth = 0; lastHeight = 0; });
  observer.observe(visual);
  window.addEventListener("pagehide", () => {
    observer.disconnect();
    renderer.dispose();
    if (active) dispose(active.object);
  }, { once: true });
  app.dataset.renderer3d = "ready";
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
else boot();
