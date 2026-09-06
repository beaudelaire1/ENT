// Matières du Sablier.
//
// Chaque matière associe ses constantes physiques (indice de réfraction, métallicité,
// transmission) aux cartes de relief calculées dans `textures.js`. Une matière sans
// carte reste une couleur : c'est exactement ce qui donne aux objets 3D un air de
// pictogramme gonflé. L'environnement de l'univers fait le reste — ces matières sont
// écrites pour être éclairées par une carte d'environnement, pas par deux lampes.
import { sandMaps, glassMaps, metalMaps, waxMaps, pearlMaps, lunarMaps } from "./textures.js";

export function makeChrome(THREE) {
  const maps = metalMaps(THREE);
  return new THREE.MeshPhysicalMaterial({
    color: 0xe4e9ee,
    metalness: 1,
    roughness: 0.13,
    clearcoat: 0.85,
    clearcoatRoughness: 0.06,
    normalMap: maps.normalMap,
    roughnessMap: maps.roughnessMap,
    normalScale: new THREE.Vector2(0.35, 0.35),
    envMapIntensity: 1.6,
  });
}

export function makeSteel(THREE) {
  const maps = metalMaps(THREE);
  return new THREE.MeshPhysicalMaterial({
    color: 0x6f7783,
    metalness: 0.95,
    roughness: 0.29,
    clearcoat: 0.35,
    normalMap: maps.normalMap,
    roughnessMap: maps.roughnessMap,
    normalScale: new THREE.Vector2(0.5, 0.5),
    envMapIntensity: 1.1,
  });
}

// Verre soufflé. `transmission` transporte la lumière à travers l'épaisseur, `ior` et
// `dispersion` séparent légèrement les couleurs sur les arêtes — le détail qui distingue
// un vrai verre d'une coque translucide.
export function makeGlass(THREE) {
  const maps = glassMaps(THREE);
  const material = new THREE.MeshPhysicalMaterial({
    color: 0xf7fdff,
    roughness: 0.02,
    metalness: 0,
    transmission: 1,
    thickness: 0.85,
    ior: 1.52,
    transparent: true,
    opacity: 1,
    clearcoat: 1,
    clearcoatRoughness: 0.02,
    normalMap: maps.normalMap,
    roughnessMap: maps.roughnessMap,
    normalScale: new THREE.Vector2(0.16, 0.16),
    side: THREE.DoubleSide,
    depthWrite: false,
    envMapIntensity: 1.35,
    attenuationColor: new THREE.Color(0xdff2ff),
    attenuationDistance: 6,
  });
  if ("dispersion" in material) material.dispersion = 0.28;
  return material;
}

export function makeSand(THREE) {
  const maps = sandMaps(THREE);
  return new THREE.MeshPhysicalMaterial({
    color: 0xd8a758,
    roughness: 0.92,
    metalness: 0,
    map: maps.map,
    normalMap: maps.normalMap,
    roughnessMap: maps.roughnessMap,
    normalScale: new THREE.Vector2(1.15, 1.15),
    sheen: 0.35,
    sheenRoughness: 0.72,
    sheenColor: new THREE.Color(0xffe2b0),
    envMapIntensity: 1,
  });
}

export function makePearl(THREE) {
  const maps = pearlMaps(THREE);
  return new THREE.MeshPhysicalMaterial({
    color: 0xf6f1ea,
    roughness: 0.11,
    metalness: 0.02,
    clearcoat: 1,
    clearcoatRoughness: 0.03,
    iridescence: 1,
    iridescenceIOR: 1.34,
    iridescenceThicknessRange: [120, 420],
    sheen: 0.4,
    sheenRoughness: 0.18,
    sheenColor: new THREE.Color(0xfff0e2),
    normalMap: maps.normalMap,
    roughnessMap: maps.roughnessMap,
    normalScale: new THREE.Vector2(0.22, 0.22),
    envMapIntensity: 1.3,
  });
}

// Cire : diffusion sous la surface. `transmission` faible et `attenuationDistance`
// courte donnent cette chaleur laiteuse qu'on voit sur une bougie éclairée par sa
// propre flamme.
export function makeWax(THREE) {
  const maps = waxMaps(THREE);
  return new THREE.MeshPhysicalMaterial({
    color: 0xffeeda,
    roughness: 0.38,
    metalness: 0,
    clearcoat: 0.28,
    clearcoatRoughness: 0.38,
    transmission: 0.42,
    thickness: 1.6,
    ior: 1.44,
    transparent: true,
    attenuationColor: new THREE.Color(0xffc98f),
    attenuationDistance: 1.1,
    normalMap: maps.normalMap,
    roughnessMap: maps.roughnessMap,
    normalScale: new THREE.Vector2(0.42, 0.42),
    sheen: 0.5,
    sheenRoughness: 0.42,
    sheenColor: new THREE.Color(0xffd9b0),
    envMapIntensity: 0.9,
  });
}

export function makeRegolith(THREE) {
  const maps = lunarMaps(THREE);
  return new THREE.MeshStandardMaterial({
    color: 0xc9c6c0,
    roughness: 1,
    metalness: 0,
    map: maps.map,
    normalMap: maps.normalMap,
    normalScale: new THREE.Vector2(1.4, 1.4),
    envMapIntensity: 0.35,
  });
}

export function seeded(index, salt = 1) {
  const value = Math.sin(index * 91.733 + salt * 37.719) * 43758.5453;
  return Math.abs(value - Math.floor(value));
}
