// Pièces détachées des univers du Sablier.
//
// Un décor peint en 2D reste un décor : quelle que soit sa finesse, il n'a pas de
// profondeur, la lumière n'y circule pas et l'objet posé devant flotte au-dessus. Ces
// blocs construisent de vrais volumes — relief, eau, végétation, poussière, colonnes de
// lumière — que la brume et la perspective aérienne éloignent réellement.
import { fbm, ridged, worley } from "./noise.js";
import {
  sandMaps, rockMaps, barkMaps, waterNormal, radialSprite, foliageSprite,
} from "./textures.js";

const clamp01 = (value) => Math.max(0, Math.min(1, value));

// Générateur déterministe : deux visites du même univers doivent produire la même dune.
export function stream(seed = 1) {
  let state = (seed * 2654435761) >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

// ── Relief ───────────────────────────────────────────────────────────────────────

// Profils de terrain. Chacun rend une altitude pour un point du sol ; le facteur
// `shelter` aplatit les abords immédiats de la caméra, sinon une crête pousserait au
// milieu de la scène et masquerait l'objet.
export const PROFILES = {
  flat: () => 0,
  plain: (x, z) => fbm(x * 0.008, z * 0.008, 4) * 4,
  hills: (x, z) => fbm(x * 0.006, z * 0.006, 5) * 22 + fbm(x * 0.02, z * 0.02, 3) * 4,
  valley: (x, z) => {
    const walls = Math.pow(Math.min(1, Math.abs(x) / 90), 2) * 78;
    return walls + fbm(x * 0.01, z * 0.01, 4) * 9 - 4;
  },
  dunes: (x, z) => {
    // Crêtes longues, orientées par le vent, plus une houle lente de fond.
    const wind = ridged(x * 0.004 + z * 0.0016, z * 0.009, 4) * 34;
    const swell = fbm(x * 0.0022, z * 0.0022, 3) * 20;
    return wind + swell;
  },
  peaks: (x, z) => ridged(x * 0.0045, z * 0.0045, 6) * 120 + fbm(x * 0.02, z * 0.02, 3) * 5,
  canyon: (x, z) => {
    const strata = ridged(x * 0.005, z * 0.0035, 5) * 60;
    return strata - Math.exp(-Math.pow(x / 40, 2)) * 34;
  },
};

// Altitude du sol en un point du *monde*. Une seule fonction, utilisée par le relief
// comme par tout ce qui s'y pose.
//
// Le maillage du terrain est reculé de `offset` : un sommet écrit en coordonnées locales
// se retrouve en `z - offset`. Tant que la clairière et les arbres calculaient leur
// hauteur dans deux repères différents, la zone plate se creusait à `-2 × offset` — la
// caméra et l'objet se réveillaient à l'intérieur d'un massif — et les troncs flottaient
// à des dizaines de mètres au-dessus de leur propre sol. Tout passe désormais par ici.
export function elevation(shape, x, worldZ, { height = 1, shelter = 34, offset = 0 } = {}) {
  // Le creux d'accueil est centré sur l'observateur, pas sur le maillage : l'objet doit
  // reposer sur un sol calme, le relief commence au-delà.
  const opening = clamp01((Math.hypot(x, worldZ) - shelter) / (shelter * 2.4));
  return shape(x, worldZ + offset) * height * opening * opening;
}

export function terrain(THREE, {
  profile = "plain", size = 1700, segments = 170, color = "#8a6a45", material = "sand",
  height = 1, shelter = 34, offset = 0, grain = 150,
}) {
  const geometry = new THREE.PlaneGeometry(size, size, segments, segments);
  geometry.rotateX(-Math.PI / 2);
  const shape = PROFILES[profile] || PROFILES.plain;
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i += 1) {
    const x = position.getX(i), z = position.getZ(i);
    position.setY(i, elevation(shape, x, z - offset, { height, shelter, offset }));
  }
  geometry.computeVertexNormals();

  // Les cartes sont partagées entre tous les usages : on les clone pour leur donner une
  // répétition propre. Un sol de neuf cents mètres qui répète sa texture trois fois
  // affiche des ondulations de trois cents mètres de long — l'effet « mer de sable » qui
  // trahit immédiatement la texture plaquée.
  const shared = material === "rock" ? rockMaps(THREE) : sandMaps(THREE);
  const tile = (map) => {
    const copy = map.clone();
    copy.repeat.set(grain, grain);
    // Le clone possède son propre envoi GPU : il se libère avec l'univers, contrairement
    // à la carte d'origine que le cache garde pour les suivants.
    copy.userData = { shared: false };
    copy.needsUpdate = true;
    return copy;
  };
  const surface = new THREE.MeshStandardMaterial({
    color: new THREE.Color(color),
    roughness: 0.96,
    metalness: 0,
    normalMap: tile(shared.normalMap),
    roughnessMap: tile(shared.roughnessMap),
    normalScale: new THREE.Vector2(0.2, 0.2),
  });
  const mesh = new THREE.Mesh(geometry, surface);
  mesh.position.z = -offset;
  mesh.receiveShadow = true;
  return mesh;
}

// ── Eau ──────────────────────────────────────────────────────────────────────────

export function water(THREE, { level = 0, size = 1700, color = "#20404c", roughness = 0.08, offset = 0 }) {
  const normal = waterNormal(THREE).clone();
  normal.userData = { shared: false };
  normal.needsUpdate = true;
  const geometry = new THREE.PlaneGeometry(size, size, 1, 1);
  geometry.rotateX(-Math.PI / 2);
  // Une eau qui ne réfléchit rien est une nappe de peinture. La métallicité élevée et la
  // rugosité très basse font travailler la carte d'environnement : c'est le ciel du lieu
  // qu'on voit dedans, avec sa couleur et son astre.
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(color),
    roughness,
    metalness: 0.42,
    normalMap: normal,
    normalScale: new THREE.Vector2(0.4, 0.4),
    envMapIntensity: 1.4,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(0, level, -offset);
  mesh.receiveShadow = false;
  mesh.userData.update = (time, motion) => {
    // La houle n'est pas simulée : la carte de normales dérive, ce qui suffit à donner
    // une surface vivante sans coût. À l'arrêt, l'eau reste — c'est son mouvement qui
    // cesse, pas le plan d'eau.
    if (motion <= 0) return;
    normal.offset.set((time * 0.000018 * motion) % 1, (time * 0.000011 * motion) % 1);
  };
  return mesh;
}

// ── Végétation ───────────────────────────────────────────────────────────────────

const FOLIAGE = {
  redwood: { leaf: "#2f5138", trunk: "#3b2b21", spread: 0.5, tiers: 4 },
  pine: { leaf: "#20402f", trunk: "#332721", spread: 0.42, tiers: 5 },
  blossom: { leaf: "#efc0d2", trunk: "#5a4636", spread: 0.78, tiers: 2 },
  autumn: { leaf: "#c2712c", trunk: "#3f2d24", spread: 0.82, tiers: 2 },
  palm: { leaf: "#4e6f37", trunk: "#6b5236", spread: 0.95, tiers: 1 },
  olive: { leaf: "#6c7f52", trunk: "#59503f", spread: 0.8, tiers: 2 },
};

// Les arbres sont des troncs instanciés surmontés de plans découpés en alpha. Une
// sphère verte pleine se lit comme une sphère verte ; une découpe irrégulière laisse
// passer le ciel et devient un feuillage.
export function grove(THREE, {
  kind = "pine", count = 60, near = 40, far = 320, spread = 220,
  height = [14, 34], seed = 7, ground = PROFILES.plain, groundHeight = 1, shelter = 34, offset = 0,
  clearing = 34,
}) {
  const preset = FOLIAGE[kind] || FOLIAGE.pine;
  const random = stream(seed);
  const group = new THREE.Group();
  const bark = barkMaps(THREE);
  const trunkMaterial = new THREE.MeshStandardMaterial({
    color: new THREE.Color(preset.trunk),
    roughness: 0.96,
    normalMap: bark.normalMap,
    roughnessMap: bark.roughnessMap,
  });
  const trunks = new THREE.InstancedMesh(
    new THREE.CylinderGeometry(0.42, 0.86, 1, 7, 1, true),
    trunkMaterial,
    count,
  );
  const leafMaterial = new THREE.MeshStandardMaterial({
    map: foliageSprite(THREE, preset.leaf, seed),
    color: new THREE.Color(preset.leaf),
    roughness: 0.88,
    transparent: true,
    alphaTest: 0.32,
    side: THREE.DoubleSide,
    depthWrite: true,
  });
  const leaves = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), leafMaterial, count * preset.tiers);
  const matrix = new THREE.Matrix4();
  const quaternion = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const position = new THREE.Vector3();
  let leaf = 0;

  for (let i = 0; i < count; i += 1) {
    const angle = random() * Math.PI * 2;
    const distance = near + Math.pow(random(), 0.62) * (far - near);
    let x = Math.cos(angle) * spread * (0.4 + random() * 0.6) * (random() > 0.5 ? 1 : -1);
    let z = -distance;
    // Clairière : aucun tronc à l'intérieur de ce rayon. Sans elle, un séquoia de
    // soixante mètres pouvait pousser à huit mètres de l'œil et masquer tout le lieu —
    // l'écran devenait une écorce.
    const reach = Math.hypot(x, z);
    if (reach < clearing) {
      const push = clearing / Math.max(1e-3, reach);
      x *= push;
      z *= push;
    }
    // Même fonction d'altitude que le relief : un arbre pousse sur son sol, pas au-dessus.
    const base = elevation(ground, x, z, { height: groundHeight, shelter, offset }) - 0.4;
    const tall = height[0] + random() * (height[1] - height[0]);
    position.set(x, base + tall / 2, z);
    scale.set(1 + random() * 0.5, tall, 1 + random() * 0.5);
    quaternion.setFromAxisAngle(new THREE.Vector3(0, 1, 0), random() * Math.PI);
    trunks.setMatrixAt(i, matrix.compose(position, quaternion, scale));

    for (let tier = 0; tier < preset.tiers; tier += 1) {
      const ratio = preset.tiers === 1 ? 1 : 0.55 + (tier / preset.tiers) * 0.5;
      const width = tall * preset.spread * (1.15 - tier * 0.16) * (0.8 + random() * 0.4);
      position.set(
        x + (random() - 0.5) * width * 0.24,
        base + tall * ratio,
        z + (random() - 0.5) * width * 0.24,
      );
      scale.set(width, width * (0.72 + random() * 0.4), 1);
      quaternion.setFromAxisAngle(new THREE.Vector3(0, 1, 0), random() * Math.PI);
      leaves.setMatrixAt(leaf, matrix.compose(position, quaternion, scale));
      leaf += 1;
    }
  }
  trunks.instanceMatrix.needsUpdate = true;
  leaves.instanceMatrix.needsUpdate = true;
  leaves.count = leaf;
  group.add(trunks, leaves);
  return group;
}

// ── Roches et blocs ──────────────────────────────────────────────────────────────

export function boulders(THREE, {
  count = 24, near = 20, far = 200, spread = 160, scale: sizeRange = [2, 9],
  color = "#5b5147", seed = 11, ground = PROFILES.plain, groundHeight = 1, shelter = 34, offset = 0,
}) {
  const random = stream(seed);
  const maps = rockMaps(THREE);
  const geometry = new THREE.IcosahedronGeometry(1, 1);
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i += 1) {
    // Une icosphère régulière se reconnaît du premier coup d'œil : on tord ses sommets.
    const x = position.getX(i), y = position.getY(i), z = position.getZ(i);
    const push = 0.72 + worley(x * 2 + 5, z * 2, 1) * 0.5 + fbm(x * 3, y * 3, 3) * 0.2;
    position.setXYZ(i, x * push, y * push * 0.78, z * push);
  }
  geometry.computeVertexNormals();
  const mesh = new THREE.InstancedMesh(
    geometry,
    new THREE.MeshStandardMaterial({
      color: new THREE.Color(color),
      roughness: 0.98,
      normalMap: maps.normalMap,
      roughnessMap: maps.roughnessMap,
    }),
    count,
  );
  const matrix = new THREE.Matrix4(), quaternion = new THREE.Quaternion();
  const vector = new THREE.Vector3(), size = new THREE.Vector3();
  for (let i = 0; i < count; i += 1) {
    const x = (random() - 0.5) * spread * 2;
    const z = -(near + random() * (far - near));
    const base = elevation(ground, x, z, { height: groundHeight, shelter, offset });
    const radius = sizeRange[0] + random() * (sizeRange[1] - sizeRange[0]);
    vector.set(x, base + radius * 0.42, z);
    size.set(radius, radius * (0.6 + random() * 0.5), radius);
    quaternion.setFromEuler(new THREE.Euler(random() * 0.4, random() * Math.PI * 2, random() * 0.4));
    mesh.setMatrixAt(i, matrix.compose(vector, quaternion, size));
  }
  mesh.instanceMatrix.needsUpdate = true;
  mesh.castShadow = false;
  mesh.receiveShadow = true;
  return mesh;
}

// ── Particules ───────────────────────────────────────────────────────────────────
// Neige, pluie, braises, spores, voiles de sable, lucioles, poussière. Chaque famille a
// sa dérive propre : c'est le mouvement, plus que la forme, qui la rend lisible.

const PARTICLE_SPRITES = {
  soft: [["rgba(255,255,255,1)", 0], ["rgba(255,255,255,.45)", 0.45], ["rgba(255,255,255,0)", 1]],
  spark: [["rgba(255,244,214,1)", 0], ["rgba(255,168,64,.6)", 0.4], ["rgba(255,90,0,0)", 1]],
  streak: [["rgba(210,232,255,.9)", 0], ["rgba(190,220,255,.25)", 0.6], ["rgba(190,220,255,0)", 1]],
};

export function particles(THREE, {
  kind = "dust", count = 240, color = "#ffffff", size = 0.6, opacity = 0.6,
  area = [220, 90, 240], speed = 1, seed = 23, origin = [0, 12, -90],
}) {
  const random = stream(seed);
  const positions = new Float32Array(count * 3);
  const seeds = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    positions[i * 3] = (random() - 0.5) * area[0];
    positions[i * 3 + 1] = random() * area[1];
    positions[i * 3 + 2] = (random() - 0.5) * area[2];
    seeds[i * 3] = random();
    seeds[i * 3 + 1] = 0.55 + random() * 0.9;
    seeds[i * 3 + 2] = random() * Math.PI * 2;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const sprite = kind === "ember" ? "spark" : kind === "rain" ? "streak" : "soft";
  const material = new THREE.PointsMaterial({
    color: new THREE.Color(color),
    map: radialSprite(THREE, PARTICLE_SPRITES[sprite]),
    size,
    sizeAttenuation: true,
    transparent: true,
    opacity,
    depthWrite: false,
    blending: kind === "ember" || kind === "firefly" || kind === "star"
      ? THREE.AdditiveBlending
      : THREE.NormalBlending,
  });
  const points = new THREE.Points(geometry, material);
  points.position.set(origin[0], origin[1], origin[2]);
  points.frustumCulled = false;

  // `motion` ne règle que le mouvement, jamais la présence. Une pluie à l'arrêt reste une
  // pluie suspendue ; en faisant disparaître les gouttes, le niveau « Statique » retirait
  // au monde ce qui le définissait — la ville sous la pluie n'avait plus de pluie.
  points.userData.update = (time, motion) => {
    material.opacity = opacity;
    if (motion <= 0) return;
    const t = time * 0.001 * speed;
    for (let i = 0; i < count; i += 1) {
      const drift = seeds[i * 3 + 1], phase = seeds[i * 3 + 2];
      const index = i * 3;
      if (kind === "snow") {
        positions[index + 1] = area[1] - ((t * 3 * drift + seeds[index] * area[1]) % area[1]);
        positions[index] += Math.sin(t * 0.6 + phase) * 0.02;
      } else if (kind === "rain") {
        positions[index + 1] = area[1] - ((t * 46 * drift + seeds[index] * area[1]) % area[1]);
      } else if (kind === "ember") {
        positions[index + 1] = (t * 5 * drift + seeds[index] * area[1]) % area[1];
        positions[index] += Math.sin(t * 1.6 + phase) * 0.05;
      } else if (kind === "petal" || kind === "leaf") {
        positions[index + 1] = area[1] - ((t * 4 * drift + seeds[index] * area[1]) % area[1]);
        positions[index] += Math.sin(t * 0.9 + phase) * 0.08;
        positions[index + 2] += Math.cos(t * 0.7 + phase) * 0.05;
      } else if (kind === "sand") {
        positions[index] = ((t * 14 * drift + seeds[index] * area[0]) % area[0]) - area[0] / 2;
      } else {
        // Poussière, spores, lucioles : une dérive lente, sans direction dominante.
        positions[index] += Math.sin(t * 0.5 * drift + phase) * 0.02;
        positions[index + 1] += Math.cos(t * 0.4 * drift + phase) * 0.015;
        material.opacity = opacity * (0.55 + 0.45 * Math.sin(t * drift + phase));
      }
    }
    geometry.attributes.position.needsUpdate = true;
  };
  return points;
}

// ── Colonnes de lumière ──────────────────────────────────────────────────────────
// Des plans additifs orientés vers la caméra. Le volume lumineux est le signe le plus
// économique d'une atmosphère chargée : poussière en forêt, brume au sanctuaire.

export function lightShafts(THREE, {
  count = 6, color = "#e8f6c8", opacity = 0.12, height = 90, width = 14,
  spread = 120, depth = [60, 220], tilt = 0.24, seed = 41,
}) {
  const random = stream(seed);
  const group = new THREE.Group();
  const texture = radialSprite(THREE, [
    [`rgba(255,255,255,.85)`, 0],
    [`rgba(255,255,255,.16)`, 0.5],
    [`rgba(255,255,255,0)`, 1],
  ], 64);
  const material = new THREE.MeshBasicMaterial({
    color: new THREE.Color(color),
    map: texture,
    transparent: true,
    opacity,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  for (let i = 0; i < count; i += 1) {
    const shaft = new THREE.Mesh(new THREE.PlaneGeometry(width * (0.5 + random()), height), material);
    shaft.position.set(
      (random() - 0.5) * spread * 2,
      height * 0.42,
      -(depth[0] + random() * (depth[1] - depth[0])),
    );
    shaft.rotation.z = (random() - 0.5) * tilt;
    group.add(shaft);
  }
  group.userData.update = (time, motion) => {
    // Le rai de lumière existe même immobile : seule sa respiration s'arrête.
    material.opacity = opacity * (motion > 0 ? 0.72 + 0.28 * Math.sin(time * 0.0002) : 1);
  };
  return group;
}

// ── Constructions ────────────────────────────────────────────────────────────────
// Quelques bâtis identifiables. Ils tiennent l'échelle du paysage : sans repère
// construit, une dune de trente mètres et une dune de trois cents se ressemblent.

export function columns(THREE, { count = 8, color = "#8d8477", height = 26, radius = 1.8, spacing = 16, depth = -120 }) {
  const group = new THREE.Group();
  const maps = rockMaps(THREE);
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(color),
    roughness: 0.92,
    normalMap: maps.normalMap,
    roughnessMap: maps.roughnessMap,
  });
  const random = stream(53);
  for (let i = 0; i < count; i += 1) {
    const side = i % 2 === 0 ? -1 : 1;
    const rank = Math.floor(i / 2);
    const broken = 0.45 + random() * 0.55;             // toutes les colonnes sont ruinées
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(radius * 0.86, radius, height * broken, 16, 1), material);
    shaft.position.set(side * spacing, height * broken / 2, depth - rank * spacing * 1.6);
    group.add(shaft);
    const capital = new THREE.Mesh(new THREE.BoxGeometry(radius * 2.6, radius * 0.7, radius * 2.6), material);
    capital.position.set(side * spacing, height * broken, depth - rank * spacing * 1.6);
    if (broken > 0.8) group.add(capital);
  }
  return group;
}

export function dome(THREE, { color = "#463a30", metal = "#2b2b31", radius = 16, depth = -160, sunk = 0.42 }) {
  // Un observatoire à demi enseveli : la coupole émerge, le tambour est enfoncé.
  const group = new THREE.Group();
  const maps = rockMaps(THREE);
  const stone = new THREE.MeshStandardMaterial({
    color: new THREE.Color(color), roughness: 0.95, normalMap: maps.normalMap, roughnessMap: maps.roughnessMap,
  });
  const shell = new THREE.MeshStandardMaterial({ color: new THREE.Color(metal), roughness: 0.44, metalness: 0.78 });
  const drum = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius * 1.08, radius * 1.1, 36), stone);
  drum.position.set(0, radius * 0.55 - radius * sunk * 1.1, depth);
  group.add(drum);
  const cap = new THREE.Mesh(new THREE.SphereGeometry(radius, 36, 18, 0, Math.PI * 2, 0, Math.PI / 2), shell);
  cap.position.set(0, radius * 1.1 - radius * sunk * 1.1, depth);
  group.add(cap);
  const slit = new THREE.Mesh(new THREE.BoxGeometry(radius * 0.24, radius * 1.02, radius * 2.04), new THREE.MeshStandardMaterial({ color: 0x0a0a0c, roughness: 1 }));
  slit.position.set(0, radius * 1.32 - radius * sunk * 1.1, depth);
  group.add(slit);
  return group;
}

export function pergola(THREE, { color = "#8c7a5f", vine = "#41603a", width = 46, depth = -34, height = 15 }) {
  // La terrasse d'été : une trame de poutres qui découpe le soleil en lamelles.
  const group = new THREE.Group();
  const wood = new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.82 });
  const post = new THREE.BoxGeometry(1.5, height, 1.5);
  for (const x of [-width / 2, width / 2]) {
    for (const z of [depth + 16, depth - 16]) {
      const pillar = new THREE.Mesh(post, wood);
      pillar.position.set(x, height / 2, z);
      group.add(pillar);
    }
  }
  const beam = new THREE.BoxGeometry(width + 4, 1.1, 1.4);
  for (let i = 0; i < 9; i += 1) {
    const rafter = new THREE.Mesh(beam, wood);
    rafter.position.set(0, height, depth + 16 - i * 4);
    group.add(rafter);
  }
  const leafMaterial = new THREE.MeshStandardMaterial({
    map: foliageSprite(THREE, vine, 12), color: new THREE.Color(vine),
    transparent: true, alphaTest: 0.34, side: THREE.DoubleSide, roughness: 0.9,
  });
  const random = stream(19);
  for (let i = 0; i < 22; i += 1) {
    const clump = new THREE.Mesh(new THREE.PlaneGeometry(7 + random() * 6, 5 + random() * 5), leafMaterial);
    clump.position.set((random() - 0.5) * width, height + 1.4 - random() * 2.4, depth + 16 - random() * 32);
    clump.rotation.set(-Math.PI / 2 + (random() - 0.5) * 0.5, random() * Math.PI, 0);
    group.add(clump);
  }
  return group;
}

export function lodge(THREE, { wall = "#3a3128", roof = "#5c626a", glow = "#ffbe72", width = 14, depth = -110 }) {
  const group = new THREE.Group();
  const body = new THREE.Mesh(
    new THREE.BoxGeometry(width, width * 0.62, width * 0.8),
    new THREE.MeshStandardMaterial({ color: new THREE.Color(wall), roughness: 0.93 }),
  );
  body.position.set(-width * 0.6, width * 0.31, depth);
  group.add(body);
  const cover = new THREE.Mesh(
    new THREE.ConeGeometry(width * 0.86, width * 0.5, 4),
    new THREE.MeshStandardMaterial({ color: new THREE.Color(roof), roughness: 0.86 }),
  );
  cover.position.set(-width * 0.6, width * 0.86, depth);
  cover.rotation.y = Math.PI / 4;
  group.add(cover);
  const window_ = new THREE.Mesh(
    new THREE.PlaneGeometry(width * 0.26, width * 0.2),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(glow) }),
  );
  window_.position.set(-width * 0.6 + width * 0.02, width * 0.34, depth + width * 0.401);
  group.add(window_);
  const lamp = new THREE.PointLight(new THREE.Color(glow), 340, width * 9, 2);
  lamp.position.set(-width * 0.6, width * 0.36, depth + width * 0.6);
  group.add(lamp);
  return group;
}

export function skyline(THREE, {
  count = 26, color = "#0e141c", windows = "#ffc87a", depth = [90, 320], spread = 260, height = [30, 120], seed = 61,
}) {
  const random = stream(seed);
  const group = new THREE.Group();
  const material = new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.88 });
  const geometry = new THREE.BoxGeometry(1, 1, 1);
  const blocks = new THREE.InstancedMesh(geometry, material, count);
  const matrix = new THREE.Matrix4(), quaternion = new THREE.Quaternion();
  const position = new THREE.Vector3(), scale = new THREE.Vector3();
  for (let i = 0; i < count; i += 1) {
    const tall = height[0] + random() * (height[1] - height[0]);
    const width = 14 + random() * 26;
    position.set((random() - 0.5) * spread * 2, tall / 2, -(depth[0] + random() * (depth[1] - depth[0])));
    scale.set(width, tall, width * (0.7 + random() * 0.6));
    quaternion.setFromAxisAngle(new THREE.Vector3(0, 1, 0), random() * 0.3);
    blocks.setMatrixAt(i, matrix.compose(position, quaternion, scale));
  }
  blocks.instanceMatrix.needsUpdate = true;
  group.add(blocks);
  // Fenêtres allumées : de simples points additifs, mais ce sont eux qui donnent
  // l'échelle humaine de la ville.
  group.add(particles(THREE, {
    kind: "star", count: 320, color: windows,
    size: 1.1, opacity: 0.85, area: [spread * 2, height[1], depth[1] - depth[0]],
    origin: [0, height[1] * 0.45, -(depth[0] + depth[1]) / 2], seed: seed + 3,
  }));
  return group;
}

export function greatTree(THREE, { trunk = "#3a2b22", leaf = "#2f6b45", height = 74, depth = -150, glow = null }) {
  const group = new THREE.Group();
  const bark = barkMaps(THREE);
  const wood = new THREE.MeshStandardMaterial({
    color: new THREE.Color(trunk), roughness: 0.96, normalMap: bark.normalMap, roughnessMap: bark.roughnessMap,
  });
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(height * 0.045, height * 0.14, height, 18, 4, true), wood);
  stem.position.set(0, height / 2, depth);
  group.add(stem);
  const random = stream(29);
  for (let i = 0; i < 9; i += 1) {
    const branch = new THREE.Mesh(new THREE.CylinderGeometry(height * 0.012, height * 0.03, height * 0.4, 8), wood);
    const angle = (i / 9) * Math.PI * 2;
    branch.position.set(Math.cos(angle) * height * 0.13, height * (0.6 + random() * 0.2), depth + Math.sin(angle) * height * 0.13);
    branch.rotation.set(Math.sin(angle) * 0.6, 0, -Math.cos(angle) * 0.6);
    group.add(branch);
  }
  const canopy = new THREE.MeshStandardMaterial({
    map: foliageSprite(THREE, leaf, 5), color: new THREE.Color(leaf),
    transparent: true, alphaTest: 0.3, side: THREE.DoubleSide, roughness: 0.9,
  });
  for (let i = 0; i < 26; i += 1) {
    const size = height * (0.22 + random() * 0.3);
    const clump = new THREE.Mesh(new THREE.PlaneGeometry(size, size * 0.8), canopy);
    const angle = random() * Math.PI * 2, radius = Math.pow(random(), 0.6) * height * 0.42;
    clump.position.set(Math.cos(angle) * radius, height * (0.66 + random() * 0.34), depth + Math.sin(angle) * radius);
    clump.rotation.y = random() * Math.PI;
    group.add(clump);
  }
  if (glow) {
    const lamp = new THREE.PointLight(new THREE.Color(glow), 900, height * 4, 2);
    lamp.position.set(0, height * 0.8, depth);
    group.add(lamp);
  }
  return group;
}

export function hearth(THREE, { stone = "#2a211c", ember = "#ff7a2a", width = 26, depth = -30 }) {
  const group = new THREE.Group();
  const maps = rockMaps(THREE);
  const rock = new THREE.MeshStandardMaterial({
    color: new THREE.Color(stone), roughness: 0.98, normalMap: maps.normalMap, roughnessMap: maps.roughnessMap,
  });
  const back = new THREE.Mesh(new THREE.BoxGeometry(width, width * 0.9, 3), rock);
  back.position.set(0, width * 0.45, depth - 8);
  group.add(back);
  for (const x of [-width / 2, width / 2]) {
    const jamb = new THREE.Mesh(new THREE.BoxGeometry(4, width * 0.9, 16), rock);
    jamb.position.set(x, width * 0.45, depth);
    group.add(jamb);
  }
  const lintel = new THREE.Mesh(new THREE.BoxGeometry(width + 8, 4, 18), rock);
  lintel.position.set(0, width * 0.9, depth);
  group.add(lintel);
  const bed = new THREE.Mesh(
    new THREE.CylinderGeometry(width * 0.34, width * 0.38, 1.6, 24),
    new THREE.MeshStandardMaterial({
      color: new THREE.Color(ember), emissive: new THREE.Color(ember),
      emissiveIntensity: 2.4, roughness: 0.9,
    }),
  );
  bed.position.set(0, 0.8, depth);
  group.add(bed);
  const fire = new THREE.PointLight(new THREE.Color(ember), 1800, 140, 2);
  fire.position.set(0, 4, depth + 2);
  group.add(fire);
  group.userData.update = (time, motion) => {
    // Les braises éclairent toujours ; c'est leur battement qui s'apaise.
    const breath = motion > 0 ? Math.sin(time * 0.003) * 260 + Math.sin(time * 0.011) * 140 : 0;
    fire.intensity = 1500 + breath * motion;
  };
  return group;
}

export function railing(THREE, { color = "#1b1f26", width = 60, height = 3.4, depth = -14 }) {
  const group = new THREE.Group();
  const metal = new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.5, metalness: 0.72 });
  const rail = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, width, 10), metal);
  rail.rotation.z = Math.PI / 2;
  rail.position.set(0, height, depth);
  group.add(rail);
  for (let i = 0; i <= 14; i += 1) {
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, height, 8), metal);
    post.position.set(-width / 2 + (i / 14) * width, height / 2, depth);
    group.add(post);
  }
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(width * 1.6, 40),
    new THREE.MeshStandardMaterial({ color: 0x14161a, roughness: 0.95 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, 0, depth + 20);
  floor.receiveShadow = true;
  group.add(floor);
  return group;
}

// Anneaux planétaires et corps célestes lointains, pour les univers sans sol.
export function planet(THREE, { radius = 90, color = "#c08c5a", rings = true, position = [120, 40, -420], glow = "#ffd7a8" }) {
  const group = new THREE.Group();
  const body = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 64, 40),
    new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.92 }),
  );
  group.add(body);
  if (rings) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(radius * 1.35, radius * 2.1, 128),
      new THREE.MeshBasicMaterial({
        color: new THREE.Color(glow), transparent: true, opacity: 0.34,
        side: THREE.DoubleSide, depthWrite: false,
      }),
    );
    ring.rotation.set(-Math.PI / 2.3, 0, 0.4);
    group.add(ring);
  }
  group.position.set(position[0], position[1], position[2]);
  return group;
}

export { clamp01 };
