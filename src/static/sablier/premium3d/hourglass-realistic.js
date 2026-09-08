// Sablier.
//
// Le sable n'est pas un cône qui grandit : il occupe le volume que le verre lui laisse.
// En haut il se creuse d'un entonnoir qui s'ouvre au-dessus du col ; en bas il forme un
// tas dont la pente est celle du talus naturel, sommet sous le filet. Les deux masses
// sont donc reconstruites à partir du profil intérieur du verre plutôt que posées
// devant lui — c'est ce qui les fait épouser la paroi au lieu de flotter dedans.
import { makeChrome, makeSteel, makeGlass, makeSand, seeded } from "./material-kit.js";
import { fbm } from "./noise.js";

// Demi-profil du verre : rayon extérieur en fonction de la hauteur. Le col est étroit,
// les bulbes s'évasent, les ouvertures se resserrent contre les plateaux.
const PROFILE = [
  [0.80, 1.78], [0.92, 1.62], [0.99, 1.34], [0.93, 1.08], [0.73, 0.76],
  [0.44, 0.40], [0.20, 0.10], [0.17, 0.00],
];

// Rayon intérieur à une hauteur donnée, par interpolation du profil (symétrique).
function innerRadius(y) {
  const height = Math.abs(y);
  const table = PROFILE;
  if (height >= table[0][1]) return table[0][0] * 0.94;
  for (let i = table.length - 1; i > 0; i -= 1) {
    const [r0, y0] = table[i], [r1, y1] = table[i - 1];
    if (height >= y0 && height <= y1) {
      const t = (height - y0) / Math.max(1e-6, y1 - y0);
      return (r0 + (r1 - r0) * t) * 0.94;
    }
  }
  return table[table.length - 1][0] * 0.94;
}

const TOP = 1.78, NECK = 0.055, SPAN = TOP - NECK;

// Le sable est une matière, pas une hauteur. Placer sa surface à la fraction de temps
// restante ne dit juste que dans un tube droit : une ampoule s'évase, et sa moitié basse
// tient bien moins de sable que sa moitié haute. Le haut se vidait donc très en avance
// sur le chronomètre. On cumule plutôt ∫r²dy — le volume intérieur, à π près qui se
// simplifie dans le rapport — et on inverse cette table : `height(fraction)` rend la
// hauteur à laquelle le sable occupe exactement cette part du volume de l'ampoule.
const FILL = (() => {
  const steps = 200, cumulative = [0];
  for (let i = 1; i <= steps; i += 1) {
    const a = innerRadius(NECK + SPAN * (i - 1) / steps);
    const b = innerRadius(NECK + SPAN * i / steps);
    cumulative.push(cumulative[i - 1] + (a * a + a * b + b * b) / 3 * SPAN / steps);
  }
  const total = cumulative[steps];
  return {
    total,
    height(fraction) {
      const target = Math.max(0, Math.min(1, fraction)) * total;
      for (let i = 1; i <= steps; i += 1) {
        if (cumulative[i] < target) continue;
        const span = cumulative[i] - cumulative[i - 1];
        return NECK + SPAN * (i - 1 + (span > 1e-9 ? (target - cumulative[i - 1]) / span : 0)) / steps;
      }
      return TOP;
    },
  };
})();

// Contour de la masse supérieure : paroi jusqu'au niveau, puis entonnoir vers le col.
function upperOutline(THREE, fill, running) {
  const points = [];
  if (fill <= 0.002) return points;
  // L'entonnoir reprend du volume au sable, et sa profondeur dépend du niveau, qui dépend
  // d'elle : trois passes suffisent à faire converger les deux. Son creux n'est pas un
  // cône — il tombe en t^1,7 — et il emporte 0,2·r²·h, non le tiers d'un cône droit.
  let level = FILL.height(fill);
  let mouth = innerRadius(level);
  // L'entonnoir se creuse d'autant plus que le sable est haut et que l'écoulement dure.
  let depth = Math.min((level - NECK) * 0.55, mouth * (running ? 0.46 : 0.22));
  for (let pass = 0; pass < 3; pass += 1) {
    level = FILL.height(fill + mouth * mouth * depth * 0.2 / FILL.total);
    mouth = innerRadius(level);
    depth = Math.min((level - NECK) * 0.55, mouth * (running ? 0.46 : 0.22));
  }
  points.push(new THREE.Vector2(0.0008, NECK * 0.4));
  points.push(new THREE.Vector2(innerRadius(NECK), NECK));
  for (let i = 1; i <= 14; i += 1) {
    const y = NECK + (level - NECK) * (i / 14);
    points.push(new THREE.Vector2(innerRadius(y), y));
  }
  for (let i = 1; i <= 10; i += 1) {
    const t = i / 10;
    const radius = mouth * (1 - t);
    const drop = depth * Math.pow(t, 1.7);
    points.push(new THREE.Vector2(Math.max(0.0008, radius), level - drop));
  }
  return points;
}

// Le tas du bas : hauteur de sa surface sous le col, et hauteur de son talus. Le talus
// n'est pas un chapeau posé sur le niveau — il porte du sable lui aussi, et c'est ce
// sable-là qui manquait au compte quand le niveau ignorait son existence.
function lowerShape(fill) {
  let level = FILL.height(1 - fill), mound = 0;
  for (let pass = 0; pass < 3; pass += 1) {
    const edge = innerRadius(level);
    // Angle de talus d'un sable sec : autour de trente-quatre degrés.
    const shape = Math.min(edge * 0.68, SPAN * (1 - fill) * 0.9 + edge * 0.18);
    // Un tas ne peut pas contenir plus de sable qu'il n'en est tombé.
    mound = Math.min(shape, fill * FILL.total * 3 / Math.max(1e-6, edge * edge));
    level = FILL.height(1 - fill + edge * edge * mound / 3 / FILL.total);
  }
  return { level, mound };
}

// Contour du tas inférieur : fond plat, paroi jusqu'au niveau, puis talus jusqu'au
// sommet. Le sommet reste sous le filet, là où les grains retombent.
function lowerOutline(THREE, fill) {
  const points = [];
  if (fill <= 0.002) return points;
  const floor = -TOP;
  const shape = lowerShape(fill);
  const level = -shape.level;
  points.push(new THREE.Vector2(0.0008, floor));
  points.push(new THREE.Vector2(innerRadius(floor), floor + 0.01));
  for (let i = 1; i <= 12; i += 1) {
    const y = floor + (level - floor) * (i / 12);
    points.push(new THREE.Vector2(innerRadius(y), y));
  }
  const edge = innerRadius(level);
  for (let i = 1; i <= 10; i += 1) {
    const t = i / 10;
    points.push(new THREE.Vector2(Math.max(0.0008, edge * (1 - t)), level + shape.mound * t));
  }
  return points;
}

// Le tas parfait n'existe pas : on froisse légèrement la surface révolue.
function roughen(geometry, amount) {
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i += 1) {
    const x = position.getX(i), y = position.getY(i), z = position.getZ(i);
    const radius = Math.hypot(x, z);
    if (radius < 0.02) continue;
    const noise = fbm(x * 4.5, z * 4.5, 3) * amount;
    position.setXYZ(i, x * (1 + noise), y + noise * 0.35, z * (1 + noise));
  }
  position.needsUpdate = true;
  geometry.computeVertexNormals();
}

export function makeHourglassRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const segments = mobile ? 48 : 84;
  const chrome = makeChrome(THREE), steel = makeSteel(THREE);
  const glass = makeGlass(THREE), sand = makeSand(THREE);

  // ── Monture ──────────────────────────────────────────────────────────────────
  // Deux plateaux tournés plutôt que deux cylindres : le congé sur l'arête accroche la
  // lumière et c'est ce liseré qui donne au métal son épaisseur.
  const plateProfile = [
    [0, 0], [1.52, 0], [1.62, 0.05], [1.64, 0.13], [1.6, 0.2],
    [1.3, 0.22], [1.24, 0.3], [0.9, 0.32], [0, 0.33],
  ].map(([r, y]) => new THREE.Vector2(r, y));
  for (const side of [-1, 1]) {
    const plate = mesh(new THREE.LatheGeometry(plateProfile, segments), chrome);
    plate.scale.y = side;
    plate.position.y = side * 2.1;
    group.add(plate);
    const collar = mesh(new THREE.TorusGeometry(0.86, 0.05, 14, segments), steel);
    collar.rotation.x = Math.PI / 2;
    collar.position.y = side * 1.86;
    group.add(collar);
  }

  // Trois montants : la vue de face en montre deux, le troisième ferme la cage et
  // apparaît en réfraction à travers les bulbes.
  for (let i = 0; i < 3; i += 1) {
    const angle = (i / 3) * Math.PI * 2 - Math.PI / 2;
    const x = Math.cos(angle) * 1.34, z = Math.sin(angle) * 1.34;
    const column = mesh(new THREE.CylinderGeometry(0.062, 0.062, 4.02, 20), chrome);
    column.position.set(x, 0, z);
    group.add(column);
    for (const y of [-1.94, 1.94]) {
      const ferrule = mesh(new THREE.CylinderGeometry(0.098, 0.11, 0.2, 20), steel);
      ferrule.position.set(x, y, z);
      group.add(ferrule);
    }
  }

  // ── Verre ────────────────────────────────────────────────────────────────────
  const outline = [];
  for (const [r, y] of PROFILE) outline.push(new THREE.Vector2(r, y));
  for (let i = PROFILE.length - 2; i >= 0; i -= 1) {
    outline.push(new THREE.Vector2(PROFILE[i][0], -PROFILE[i][1]));
  }
  const vessel = mesh(new THREE.LatheGeometry(outline, mobile ? 64 : 128), glass, { cast: false, receive: false });
  vessel.renderOrder = 6;
  group.add(vessel);
  for (const y of [-TOP, TOP]) {
    const seal = mesh(new THREE.TorusGeometry(0.8, 0.04, 12, segments), chrome);
    seal.rotation.x = Math.PI / 2;
    seal.position.y = y;
    group.add(seal);
  }

  // ── Sable ────────────────────────────────────────────────────────────────────
  const upper = mesh(new THREE.BufferGeometry(), sand, { receive: false });
  const lower = mesh(new THREE.BufferGeometry(), sand, { receive: false });
  upper.renderOrder = 2;
  lower.renderOrder = 2;
  group.add(upper, lower);

  // Filet : un cylindre très fin porte la continuité, les grains instanciés portent le
  // détail. L'un sans l'autre donne soit un trait de crayon, soit une pluie sans corps.
  const streamMaterial = new THREE.MeshStandardMaterial({
    color: 0xe7c184, roughness: 0.78, metalness: 0,
    transparent: true, opacity: 0.92,
  });
  const stream = mesh(new THREE.CylinderGeometry(0.011, 0.026, 1, 10), streamMaterial, { cast: false, receive: false });
  group.add(stream);

  const grainCount = mobile ? 120 : 260;
  const grains = new THREE.InstancedMesh(
    new THREE.IcosahedronGeometry(mobile ? 0.019 : 0.015, 0),
    new THREE.MeshStandardMaterial({ color: 0xf0c882, roughness: 0.85 }),
    grainCount,
  );
  grains.frustumCulled = false;
  group.add(grains);
  const grainSeeds = Array.from({ length: grainCount }, (_, i) => ({
    phase: seeded(i, 3),
    swing: (seeded(i, 5) - 0.5) * 0.05,
    spin: seeded(i, 7) * Math.PI,
    speed: 0.85 + seeded(i, 11) * 0.4,
  }));

  // Éclat rasant : le sable en écoulement scintille, un objet mat le fait paraître mort.
  const sparkle = new THREE.PointLight(0xffd9a0, 0, 3.4, 2);
  sparkle.position.set(0.15, -0.5, 0.9);
  group.add(sparkle);

  const matrix = new THREE.Matrix4();
  const quaternion = new THREE.Quaternion();
  const scale = new THREE.Vector3(1, 1, 1);
  const position = new THREE.Vector3();
  let builtAt = -1;
  let builtRunning = null;

  function rebuild(progress, running) {
    const lathe = mobile ? 40 : 72;
    const upperPoints = upperOutline(THREE, progress, running);
    upper.visible = upperPoints.length > 2;
    if (upper.visible) {
      upper.geometry.dispose();
      upper.geometry = new THREE.LatheGeometry(upperPoints, lathe);
      roughen(upper.geometry, 0.012);
    }
    const lowerPoints = lowerOutline(THREE, 1 - progress);
    lower.visible = lowerPoints.length > 2;
    if (lower.visible) {
      lower.geometry.dispose();
      lower.geometry = new THREE.LatheGeometry(lowerPoints, lathe);
      roughen(lower.geometry, 0.014);
    }
    builtAt = progress;
    builtRunning = running;
  }

  function update(progress, time) {
    const running = progress > 0.001 && progress < 0.999;
    // Reconstruire à chaque image serait inutile : l'œil ne distingue pas un quart de
    // pour cent de sable. On regénère par paliers, ce qui garde le rendu fluide.
    if (Math.abs(progress - builtAt) > 0.004 || running !== builtRunning) rebuild(progress, running);

    const flowing = progress > 0.004 && progress < 0.999;
    const heap = lowerShape(1 - progress);
    const heapTop = -heap.level + heap.mound;
    const streamTop = NECK * 0.6;
    const streamBottom = Math.min(streamTop - 0.05, heapTop + 0.08);
    const length = Math.max(0.05, streamTop - streamBottom);
    stream.visible = flowing;
    stream.scale.y = length;
    stream.position.y = streamBottom + length / 2;
    streamMaterial.opacity = flowing ? 0.85 : 0;

    grains.visible = flowing;
    if (flowing) {
      for (let i = 0; i < grainCount; i += 1) {
        const seed = grainSeeds[i];
        // Chaque grain retombe en boucle entre le col et le sommet du tas.
        const t = ((time * 0.0009 * seed.speed) + seed.phase) % 1;
        const y = streamTop - t * length;
        const spread = 0.014 + t * 0.05;
        position.set(
          Math.sin(seed.spin + t * 7) * spread + seed.swing * t,
          y,
          Math.cos(seed.spin + t * 7) * spread,
        );
        quaternion.setFromEuler(new THREE.Euler(t * 9 + seed.phase, t * 7, t * 5));
        grains.setMatrixAt(i, matrix.compose(position, quaternion, scale));
      }
      grains.instanceMatrix.needsUpdate = true;
    }
    sparkle.intensity = flowing ? 2.4 + Math.sin(time * 0.004) * 0.5 : 0;

    if (!reducedMotion) {
      group.rotation.y = Math.sin(time * 0.00007) * 0.06;
    }
  }

  rebuild(1, false);
  return { object: group, update };
}
