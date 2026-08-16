// Les vingt-quatre lieux du Sablier.
//
// Chaque univers du catalogue reçoit ici une recette : un ciel et son soleil, un relief,
// une brume, une végétation, un mouvement. Rien n'est un filtre de couleur posé sur un
// fond — l'été n'est pas « la forêt en jaune », c'est une autre terrasse, une autre
// heure et une autre atmosphère. Les clés reprennent exactement les noms de décor du
// catalogue serveur (`scenes_catalog.json`), afin qu'un univers ajouté là-bas signale
// franchement l'absence de sa recette ici plutôt que de retomber sur un lieu voisin.
import * as kit from "./world-kit.js";

const { PROFILES } = kit;

// `env.kind: "day"` déclenche le ciel à diffusion atmosphérique ; sinon la carte
// équirectangulaire calculée. `elevation` est la hauteur du soleil en degrés — négative
// pour un astre déjà couché.
export const RECIPES = {
  // ── Les mondes fondateurs ──────────────────────────────────────────────────────
  star_tree: {
    env: { kind: "night", zenith: "#020d19", horizon: "#0c3d5d", ground: "#061017", light: "#ffe7a0", glow: "#7ad8ff", elevation: 8, azimuth: 200, intensity: 3.4, size: 3, haze: 0.5, directIntensity: 0.9 },
    fog: ["#0a2334", 0.0042],
    ground: { profile: "plain", color: "#0a1a22", material: "rock", height: 0.6 },
    water: { level: 0.4, color: "#08202c", roughness: 0.05, size: 300, offset: 150 },
    props: [{ kind: "greatTree", trunk: "#2b2119", leaf: "#2e5f4a", height: 78, depth: -160, glow: "#ffd98a" }],
    particles: [
      { kind: "star", count: 300, color: "#cfe9ff", size: 1.2, opacity: 0.7, area: [400, 160, 300], origin: [0, 90, -220] },
      { kind: "firefly", count: 90, color: "#ffe3a0", size: 1.1, opacity: 0.6, area: [180, 40, 160], origin: [0, 14, -110] },
    ],
  },
  eternity_fountain: {
    env: { kind: "night", zenith: "#061724", horizon: "#1f7180", ground: "#07141a", light: "#dffff7", glow: "#57e3df", elevation: 14, azimuth: 150, intensity: 4.2, size: 2.6, haze: 0.55, directIntensity: 1.2 },
    fog: ["#123c46", 0.0052],
    ground: { profile: "canyon", color: "#123138", material: "rock", height: 1.1 },
    water: { level: 1.2, color: "#166b76", roughness: 0.04, size: 320, offset: 130 },
    props: [{ kind: "columns", count: 10, color: "#7d8f8c", height: 30, depth: -140 }],
    particles: [{ kind: "dust", count: 220, color: "#bdf5ee", size: 0.9, opacity: 0.45, area: [220, 70, 220], origin: [0, 18, -120] }],
    shafts: { count: 5, color: "#9ff3ea", opacity: 0.1, height: 110, width: 18 },
  },
  eden: {
    env: { kind: "day", turbidity: 4.5, rayleigh: 1.4, mie: 0.006, mieG: 0.82, elevation: 26, azimuth: 44, light: "#fff0a6", directIntensity: 3.1, exposure: 0.42, ambient: 1.9 },
    fog: ["#20402f", 0.0044],
    ground: { profile: "valley", color: "#2f5236", material: "rock", height: 0.9 },
    water: { level: 0.6, color: "#20524a", roughness: 0.06, size: 240, offset: 120 },
    grove: { kind: "redwood", count: 70, near: 50, far: 320, height: [18, 40] },
    props: [{ kind: "greatTree", trunk: "#3a2b22", leaf: "#357a4c", height: 86, depth: -180 }],
    particles: [{ kind: "firefly", count: 130, color: "#fff3b0", size: 1, opacity: 0.55, area: [200, 40, 200], origin: [0, 12, -110] }],
    shafts: { count: 7, color: "#eaffc0", opacity: 0.11 },
  },
  time_river: {
    env: { kind: "night", zenith: "#070d1d", horizon: "#314b76", ground: "#090d18", light: "#f2d6a0", glow: "#9dcaff", elevation: 6, azimuth: 190, intensity: 3.8, size: 3.2, haze: 0.6, directIntensity: 1 },
    fog: ["#243a5c", 0.0058],
    ground: { profile: "canyon", color: "#1a2233", material: "rock", height: 1 },
    water: { level: 0.8, color: "#26375c", roughness: 0.05, size: 280, offset: 130 },
    props: [{ kind: "columns", count: 12, color: "#6d7488", height: 24, depth: -120 }],
    particles: [{ kind: "dust", count: 260, color: "#cfe0ff", size: 1, opacity: 0.5, area: [240, 80, 240], origin: [0, 20, -130] }],
    shafts: { count: 6, color: "#b7d0ff", opacity: 0.09 },
  },
  memories: {
    env: { kind: "night", zenith: "#15111d", horizon: "#55445f", ground: "#100d14", light: "#f0cba2", glow: "#d2b6ff", elevation: 4, azimuth: 170, intensity: 2.6, size: 4, haze: 0.75, directIntensity: 0.6 },
    fog: ["#4a3e57", 0.0072],
    ground: { profile: "flat", color: "#191521", material: "rock", height: 0 },
    props: [{ kind: "columns", count: 8, color: "#6b5f78", height: 20, depth: -90, spacing: 22 }],
    particles: [{ kind: "dust", count: 340, color: "#e4d6ff", size: 1.1, opacity: 0.55, area: [180, 60, 200], origin: [0, 16, -90] }],
    shafts: { count: 4, color: "#e0ccff", opacity: 0.14, height: 70 },
  },
  interstellar: {
    env: { kind: "night", zenith: "#01040d", horizon: "#111d3c", ground: "#03050a", light: "#c8dbff", glow: "#8eb8ff", elevation: 18, azimuth: 230, intensity: 5, size: 1.4, haze: 0.3, directIntensity: 1.4 },
    fog: ["#050a16", 0.0016],
    ground: { profile: "flat", color: "#0a0f18", material: "rock", height: 0 },
    props: [
      { kind: "planet", radius: 240, color: "#b08a5e", position: [300, 130, -900], glow: "#ffd7a8" },
      { kind: "railing", color: "#20242c", width: 70, depth: -18 },
    ],
    particles: [{ kind: "star", count: 700, color: "#dce8ff", size: 1.3, opacity: 0.9, area: [700, 300, 500], origin: [0, 110, -300] }],
  },
  galaxy: {
    env: { kind: "night", zenith: "#03020b", horizon: "#25133d", ground: "#05030b", light: "#f2d6ff", glow: "#d18aff", elevation: 24, azimuth: 210, intensity: 4.4, size: 2, haze: 0.5, directIntensity: 1.1 },
    fog: ["#0d0718", 0.0012],
    ground: { profile: "flat", color: "#070510", material: "rock", height: 0 },
    props: [{ kind: "planet", radius: 260, color: "#8a5cae", rings: true, position: [-220, 170, -1300], glow: "#e5b6ff" }],
    particles: [
      { kind: "star", count: 900, color: "#e8d8ff", size: 1.4, opacity: 0.95, area: [800, 340, 600], origin: [0, 120, -340] },
      { kind: "dust", count: 260, color: "#c98aff", size: 3.2, opacity: 0.2, area: [500, 180, 400], origin: [0, 90, -300] },
    ],
  },
  heaven: {
    env: { kind: "day", turbidity: 2.6, rayleigh: 0.9, mie: 0.004, mieG: 0.85, elevation: 20, azimuth: 330, light: "#fff8d8", directIntensity: 3.6, exposure: 0.34, ambient: 1.8 },
    fog: ["#c7e4f0", 0.005],
    ground: { profile: "peaks", color: "#8fa9b8", material: "rock", height: 0.5, offset: 420 },
    props: [{ kind: "columns", count: 8, color: "#d8e3e8", height: 30, depth: -150 }],
    particles: [{ kind: "dust", count: 200, color: "#ffffff", size: 2.4, opacity: 0.3, area: [400, 120, 300], origin: [0, 40, -180] }],
    shafts: { count: 8, color: "#fff6d4", opacity: 0.16, height: 130, width: 22 },
  },
  oasis: {
    env: { kind: "day", turbidity: 9, rayleigh: 2.6, mie: 0.012, mieG: 0.78, elevation: 5, azimuth: 206, light: "#ffd89b", directIntensity: 3.2, exposure: 0.3 },
    fog: ["#8a573f", 0.0048],
    ground: { profile: "dunes", color: "#9a6238", material: "sand", height: 1 },
    water: { level: 0.5, color: "#2f5a52", roughness: 0.07, size: 120 },
    grove: { kind: "palm", count: 22, near: 40, far: 150, spread: 90, height: [14, 24] },
    props: [{ kind: "columns", count: 6, color: "#8d7550", height: 16, depth: -150 }],
    particles: [{ kind: "sand", count: 200, color: "#f0cf9c", size: 1.6, opacity: 0.28, area: [360, 40, 240], origin: [0, 12, -130] }],
  },
  abyss: {
    env: { kind: "night", zenith: "#021217", horizon: "#0d4b55", ground: "#031015", light: "#9ff8ee", glow: "#58d6d8", elevation: 62, azimuth: 180, intensity: 3.6, size: 6, haze: 0.8, directIntensity: 1.5 },
    fog: ["#0f4a56", 0.0062],
    ground: { profile: "plain", color: "#08202a", material: "rock", height: 0.8, grain: 90 },
    props: [{ kind: "columns", count: 12, color: "#4e7078", height: 34, depth: -110 }],
    particles: [
      { kind: "dust", count: 300, color: "#a8f4ec", size: 0.8, opacity: 0.45, area: [200, 90, 220], origin: [0, 30, -110] },
      { kind: "ember", count: 90, color: "#7ff0ff", size: 1.2, opacity: 0.5, area: [180, 80, 180], origin: [0, 4, -100] },
    ],
    shafts: { count: 9, color: "#a5f6ff", opacity: 0.15, height: 150, width: 12, tilt: 0.08 },
  },
  rain_refuge: {
    env: { kind: "night", zenith: "#111820", horizon: "#344756", ground: "#15130f", light: "#ffd28a", glow: "#8ba4ba", elevation: 5, azimuth: 200, intensity: 2.2, size: 3, haze: 0.7, directIntensity: 0.7 },
    fog: ["#35485a", 0.0078],
    ground: { profile: "flat", color: "#191c20", material: "rock", height: 0 },
    props: [
      { kind: "skyline", count: 20, color: "#141a22", windows: "#ffbe72", depth: [190, 420], spread: 340, height: [22, 70] },
      { kind: "lodge", wall: "#2e2823", roof: "#4a5058", glow: "#ffbe72", width: 16, depth: -60 },
    ],
    particles: [{ kind: "rain", count: 700, color: "#c6dced", size: 0.5, opacity: 0.4, area: [200, 90, 200], origin: [0, 10, -80] }],
  },
  aurora_valley: {
    env: { kind: "night", zenith: "#06121e", horizon: "#17445b", ground: "#081018", light: "#baffef", glow: "#7defcf", elevation: 10, azimuth: 195, intensity: 3, size: 2.4, haze: 0.55, directIntensity: 0.9 },
    fog: ["#12303f", 0.0055],
    ground: { profile: "peaks", color: "#93a8b4", material: "rock", height: 0.7, offset: 320 },
    water: { level: 0.3, color: "#123542", roughness: 0.04, size: 520, offset: 240 },
    particles: [
      { kind: "star", count: 380, color: "#dff5ff", size: 1.1, opacity: 0.8, area: [500, 180, 320], origin: [0, 110, -250] },
      { kind: "snow", count: 200, color: "#eafaff", size: 0.7, opacity: 0.35, area: [180, 60, 180], origin: [0, 20, -90] },
    ],
    aurora: { color: "#7defcf", secondary: "#79d7ff" },
  },

  // ── Les saisons ────────────────────────────────────────────────────────────────
  spring_meadow: {
    env: { kind: "day", turbidity: 3.4, rayleigh: 1.6, mie: 0.005, mieG: 0.8, elevation: 30, azimuth: 46, light: "#fff3c3", directIntensity: 3.3, exposure: 0.4, ambient: 1.8 },
    fog: ["#cfe3d3", 0.0034],
    ground: { profile: "hills", color: "#5d8a4e", material: "rock", height: 0.7 },
    water: { level: 0.2, color: "#3f7a76", roughness: 0.07, size: 140 },
    grove: { kind: "blossom", count: 46, near: 36, far: 240, height: [10, 20] },
    particles: [{ kind: "petal", count: 220, color: "#f6c9d8", size: 1, opacity: 0.7, area: [160, 50, 180], origin: [0, 16, -80] }],
    shafts: { count: 4, color: "#fff4c8", opacity: 0.08 },
  },
  summer_terrace: {
    env: { kind: "day", turbidity: 5.2, rayleigh: 1.9, mie: 0.007, mieG: 0.79, elevation: 40, azimuth: 324, light: "#fff0ae", directIntensity: 4, exposure: 0.36, ambient: 1.7 },
    fog: ["#d8bf94", 0.0028],
    ground: { profile: "hills", color: "#a98c5c", material: "sand", height: 0.85, offset: 60, grain: 80 },
    water: { level: -18, color: "#2f6f78", roughness: 0.05, size: 300, offset: 430 },
    grove: { kind: "olive", count: 40, near: 70, far: 300, height: [8, 16] },
    props: [{ kind: "pergola", color: "#8c7a5f", vine: "#43663c", width: 52, depth: -46, height: 20 }],
    particles: [{ kind: "dust", count: 170, color: "#ffeec2", size: 0.9, opacity: 0.35, area: [140, 40, 160], origin: [0, 12, -60] }],
    shafts: { count: 5, color: "#fff2c0", opacity: 0.1, height: 60, width: 10, depth: [30, 90] },
  },
  autumn_lake: {
    env: { kind: "day", turbidity: 7, rayleigh: 2.8, mie: 0.009, mieG: 0.8, elevation: 7, azimuth: 218, light: "#ffd39d", directIntensity: 3, exposure: 0.32 },
    fog: ["#9c7a5c", 0.0062],
    ground: { profile: "hills", color: "#6c4c33", material: "rock", height: 0.8 },
    water: { level: 0.2, color: "#3a3026", roughness: 0.05, size: 500, offset: 120 },
    grove: { kind: "autumn", count: 64, near: 44, far: 300, height: [12, 26] },
    particles: [{ kind: "leaf", count: 200, color: "#d98436", size: 1.2, opacity: 0.7, area: [180, 50, 200], origin: [0, 16, -90] }],
    shafts: { count: 5, color: "#ffcf92", opacity: 0.12 },
  },
  winter_lodge: {
    env: { kind: "day", turbidity: 3, rayleigh: 2.2, mie: 0.004, mieG: 0.82, elevation: 14, azimuth: 316, light: "#eef8ff", directIntensity: 2.6, exposure: 0.36, ambient: 1.9 },
    fog: ["#b8ccd8", 0.0058],
    ground: { profile: "peaks", color: "#cfdde5", material: "rock", height: 0.72, offset: 300 },
    grove: { kind: "pine", count: 70, near: 40, far: 280, height: [10, 22] },
    props: [{ kind: "lodge", wall: "#3a3128", roof: "#5c626a", glow: "#ffbe72", width: 14, depth: -110 }],
    particles: [{ kind: "snow", count: 620, color: "#f6fcff", size: 0.7, opacity: 0.6, area: [200, 90, 200], origin: [0, 12, -90] }],
  },

  // ── Les climats ────────────────────────────────────────────────────────────────
  rain_city: {
    env: { kind: "night", zenith: "#101923", horizon: "#263748", ground: "#10151a", light: "#b7d5ea", glow: "#78b8e8", elevation: 4, azimuth: 210, intensity: 2, size: 3, haze: 0.65, directIntensity: 0.6 },
    fog: ["#243544", 0.0076],
    ground: { profile: "flat", color: "#12171c", material: "rock", height: 0 },
    water: { level: 0.02, color: "#101820", roughness: 0.03, size: 400 },
    props: [{ kind: "skyline", count: 30, color: "#0e141c", windows: "#ffc87a", depth: [230, 580], spread: 400, height: [28, 100] }],
    particles: [{ kind: "rain", count: 900, color: "#bcd6ea", size: 0.45, opacity: 0.42, area: [220, 100, 220], origin: [0, 10, -90] }],
  },
  ocean_cliffs: {
    env: { kind: "day", turbidity: 4.2, rayleigh: 1.7, mie: 0.006, mieG: 0.8, elevation: 20, azimuth: 334, light: "#f6e5c7", directIntensity: 3.4, exposure: 0.36, ambient: 1.8 },
    fog: ["#9fb9c6", 0.0042],
    ground: { profile: "canyon", color: "#3c4a4c", material: "rock", height: 1.2, offset: 90 },
    water: { level: -6, color: "#2a5f72", roughness: 0.045, size: 1200, offset: 300 },
    props: [{ kind: "boulders", count: 22, near: 40, far: 220, scale: [4, 14], color: "#3a4547" }],
    particles: [{ kind: "dust", count: 160, color: "#e6f2f6", size: 1.6, opacity: 0.3, area: [300, 40, 200], origin: [0, 8, -140] }],
  },
  sahara_observatory: {
    env: { kind: "day", turbidity: 11, rayleigh: 3.2, mie: 0.014, mieG: 0.76, elevation: 3.4, azimuth: 214, light: "#ffd39b", directIntensity: 3.6, exposure: 0.34, zenith: "#3f5e86", horizon: "#e0a870", ground: "#9a6234", ambient: 1.5 },
    fog: ["#b07747", 0.0034],
    ground: { profile: "dunes", color: "#a5673a", material: "sand", height: 1.15, grain: 55 },
    props: [{ kind: "dome", color: "#4a3b2f", metal: "#2f2f36", radius: 17, depth: -170, sunk: 0.46 }],
    particles: [{ kind: "sand", count: 260, color: "#f2cf9b", size: 1.8, opacity: 0.3, area: [420, 46, 260], origin: [0, 10, -140] }],
  },
  ancient_forest: {
    env: { kind: "day", turbidity: 6, rayleigh: 2.4, mie: 0.008, mieG: 0.84, elevation: 34, azimuth: 42, light: "#dff2bf", directIntensity: 3.6, exposure: 0.4, ambient: 2.1 },
    fog: ["#2c4a3e", 0.0046],
    ground: { profile: "plain", color: "#33513a", material: "rock", height: 0.7, grain: 70 },
    grove: { kind: "redwood", count: 58, near: 52, far: 330, spread: 210, height: [34, 66], clearing: 52 },
    props: [{ kind: "boulders", count: 18, near: 30, far: 160, scale: [2, 6], color: "#33453a" }],
    particles: [{ kind: "spore", count: 280, color: "#d9f4b4", size: 0.85, opacity: 0.5, area: [160, 60, 200], origin: [0, 18, -90] }],
    shafts: { count: 9, color: "#e9ffc4", opacity: 0.15, height: 120, width: 12, tilt: 0.14, depth: [40, 200] },
  },
  storm_cliffs: {
    env: { kind: "night", zenith: "#11131b", horizon: "#333846", ground: "#15191d", light: "#dce8ff", glow: "#a8b9db", elevation: 7, azimuth: 200, intensity: 2.4, size: 3.4, haze: 0.7, directIntensity: 0.8 },
    fog: ["#343c50", 0.0058],
    ground: { profile: "canyon", color: "#2b3236", material: "rock", height: 1.3, offset: 80 },
    water: { level: -5, color: "#1d2b33", roughness: 0.06, size: 1000, offset: 300 },
    props: [{ kind: "boulders", count: 26, near: 30, far: 200, scale: [4, 16], color: "#282f33" }],
    particles: [{ kind: "rain", count: 800, color: "#b6c8da", size: 0.5, opacity: 0.35, area: [240, 110, 240], origin: [0, 14, -110] }],
    lightning: { color: "#dce8ff" },
  },
  ember_hearth: {
    env: { kind: "night", zenith: "#120d0b", horizon: "#271713", ground: "#090706", light: "#ffd083", glow: "#ff9b4b", elevation: -6, azimuth: 180, intensity: 1.2, size: 5, haze: 0.9, directIntensity: 0.25 },
    fog: ["#241511", 0.0125],
    ground: { profile: "flat", color: "#171210", material: "rock", height: 0 },
    props: [{ kind: "hearth", stone: "#2a211c", ember: "#ff7a2a", width: 22, depth: -26 }],
    particles: [{ kind: "ember", count: 200, color: "#ff9a45", size: 0.9, opacity: 0.75, area: [40, 46, 30], origin: [0, 1, -30] }],
  },
  polar_sky: {
    env: { kind: "night", zenith: "#02111d", horizon: "#0d3448", ground: "#10222a", light: "#d9fff0", glow: "#77f0b0", elevation: 8, azimuth: 190, intensity: 2.8, size: 2.6, haze: 0.5, directIntensity: 0.8 },
    fog: ["#0d2c38", 0.0044],
    ground: { profile: "plain", color: "#8fa6b2", material: "rock", height: 0.5, grain: 110 },
    particles: [
      { kind: "star", count: 520, color: "#e6f8ff", size: 1.2, opacity: 0.85, area: [600, 220, 400], origin: [0, 120, -260] },
      { kind: "snow", count: 160, color: "#ffffff", size: 0.6, opacity: 0.3, area: [180, 40, 180], origin: [0, 10, -80] },
    ],
    aurora: { color: "#77f0b0", secondary: "#8ad9ff" },
  },
  midnight_rooftop: {
    env: { kind: "night", zenith: "#030710", horizon: "#10192a", ground: "#080a0d", light: "#e8edff", glow: "#9cb9f1", elevation: 30, azimuth: 220, intensity: 4, size: 1.6, haze: 0.4, directIntensity: 1 },
    fog: ["#0c1220", 0.0058],
    ground: { profile: "flat", color: "#0b0e14", material: "rock", height: 0 },
    props: [
      { kind: "skyline", count: 34, color: "#121822", windows: "#ffd08a", depth: [240, 620], spread: 420, height: [26, 92] },
      { kind: "railing", color: "#1b1f26", width: 64, depth: -16 },
    ],
    particles: [{ kind: "star", count: 420, color: "#dce8ff", size: 1.1, opacity: 0.8, area: [600, 200, 400], origin: [0, 130, -260] }],
  },
};

// Rideaux d'aurore : deux nappes ondulantes, additives, dont l'amplitude suit la
// session. Elles sont dessinées ici plutôt que dans le kit car elles n'ont de sens que
// pour deux univers.
function aurora(THREE, { color, secondary }) {
  const group = new THREE.Group();
  const layers = [];
  for (let layer = 0; layer < 2; layer += 1) {
    const geometry = new THREE.PlaneGeometry(520, 150, 90, 12);
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color(layer ? secondary : color),
      transparent: true,
      opacity: 0.13,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(0, 110 + layer * 24, -300 - layer * 60);
    group.add(mesh);
    layers.push({ mesh, material, base: geometry.attributes.position.array.slice() });
  }
  group.userData.update = (time, amount, progress) => {
    for (let index = 0; index < layers.length; index += 1) {
      const { mesh, material, base } = layers[index];
      const position = mesh.geometry.attributes.position;
      for (let i = 0; i < position.count; i += 1) {
        const x = base[i * 3], y = base[i * 3 + 1];
        const wave = Math.sin(x * 0.012 + time * 0.00035 + index * 1.7) * 16
          + Math.sin(x * 0.031 - time * 0.00052) * 7;
        position.setZ(i, wave * (0.35 + (y + 75) / 150));
        position.setY(i, y + Math.sin(x * 0.02 + time * 0.0002) * 6);
      }
      position.needsUpdate = true;
      // Le rideau gagne en présence à mesure que la session avance.
      material.opacity = (0.09 + (1 - progress) * 0.12) * amount;
    }
  };
  return group;
}

const PROP_BUILDERS = {
  columns: kit.columns,
  dome: kit.dome,
  pergola: kit.pergola,
  lodge: kit.lodge,
  skyline: kit.skyline,
  greatTree: kit.greatTree,
  hearth: kit.hearth,
  railing: kit.railing,
  planet: kit.planet,
  boulders: kit.boulders,
};

// Assemble un univers. `density` (0 à 1) suit le niveau d'immersion choisi par
// l'utilisateur : à 0 le lieu reste entier, seuls ses mouvements s'arrêtent.
export function buildWorld(THREE, key, { density = 1, mobile = false } = {}) {
  const recipe = RECIPES[key] || RECIPES.star_tree;
  const group = new THREE.Group();
  const updates = [];
  const detail = mobile ? 0.55 : 1;

  const profile = PROFILES[recipe.ground?.profile] || PROFILES.plain;
  const groundHeight = recipe.ground?.height ?? 1;
  const shelter = recipe.ground?.shelter ?? 34;
  const offset = recipe.ground?.offset ?? 0;

  if (recipe.ground) {
    group.add(kit.terrain(THREE, {
      ...recipe.ground,
      segments: Math.round((mobile ? 90 : 150) * 1),
      shelter,
      offset,
    }));
  }
  if (recipe.water) {
    const surface = kit.water(THREE, recipe.water);
    group.add(surface);
    updates.push(surface.userData.update);
  }
  if (recipe.grove) {
    group.add(kit.grove(THREE, {
      ...recipe.grove,
      count: Math.max(8, Math.round(recipe.grove.count * detail)),
      ground: profile,
      groundHeight,
      shelter,
      offset,
    }));
  }
  for (const prop of recipe.props || []) {
    const build = PROP_BUILDERS[prop.kind];
    if (!build) continue;
    const object = build(THREE, prop.kind === "boulders"
      ? { ...prop, ground: profile, groundHeight, shelter, offset }
      : prop);
    group.add(object);
    if (object.userData.update) updates.push(object.userData.update);
  }
  for (const spec of recipe.particles || []) {
    const cloud = kit.particles(THREE, {
      ...spec,
      count: Math.max(24, Math.round(spec.count * detail)),
    });
    group.add(cloud);
    updates.push(cloud.userData.update);
  }
  if (recipe.shafts) {
    const shafts = kit.lightShafts(THREE, {
      ...recipe.shafts,
      count: Math.max(3, Math.round((recipe.shafts.count ?? 6) * detail)),
    });
    group.add(shafts);
    updates.push(shafts.userData.update);
  }
  if (recipe.aurora) {
    const curtains = aurora(THREE, recipe.aurora);
    group.add(curtains);
    updates.push(curtains.userData.update);
  }

  let flash = null;
  if (recipe.lightning) {
    flash = new THREE.DirectionalLight(new THREE.Color(recipe.lightning.color), 0);
    flash.position.set(-40, 90, -220);
    group.add(flash);
  }

  return {
    object: group,
    env: recipe.env,
    fog: recipe.fog,
    update(time, amount, progress) {
      for (const update of updates) update(time, amount, progress);
      if (flash) {
        // Un éclair rare : neuf secondes de calme, puis deux décharges rapprochées.
        const cycle = time % 9000;
        flash.intensity = cycle < 90 ? 6 * amount : cycle > 220 && cycle < 280 ? 3.4 * amount : 0;
      }
    },
  };
}

export const WORLD_KEYS = Object.keys(RECIPES);
