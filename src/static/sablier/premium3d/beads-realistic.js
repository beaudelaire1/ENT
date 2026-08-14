import { makeChrome, makeSteel, makePearl, seeded } from "./material-kit.js";

const TAU = Math.PI * 2;
const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
const ease = (value) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};

function makeUpperSlots(THREE, count) {
  const slots = [];
  for (let index = 0; index < count; index += 1) {
    const ratio = index / Math.max(1, count - 1);
    const angle = index * 2.24 + 0.35;
    const radius = 0.42 + ratio * 0.52 + Math.sin(index * 1.7) * 0.035;
    slots.push(new THREE.Vector3(
      Math.cos(angle) * radius,
      0.28 + ratio * 1.24,
      Math.sin(angle) * radius * 0.72,
    ));
  }
  return slots;
}

function makeLowerSlots(THREE, count) {
  const slots = [];
  for (let index = 0; index < count; index += 1) {
    const layer = Math.floor(index / 8);
    const inLayer = index - layer * 8;
    const layerCount = Math.min(8, count - layer * 8);
    const angle = inLayer / Math.max(1, layerCount) * TAU + layer * 0.58;
    const radius = layer === 0 ? 0.54 : Math.max(0.16, 0.54 - layer * 0.15);
    slots.push(new THREE.Vector3(
      Math.cos(angle) * radius,
      -1.48 + layer * 0.29,
      Math.sin(angle) * radius * 0.74,
    ));
  }
  return slots;
}

function addFrame(THREE, helpers, group, materials) {
  const { mobile, mesh } = helpers;
  const segments = mobile ? 48 : 80;

  for (const y of [-2.05, 2.05]) {
    const plate = mesh(
      new THREE.CylinderGeometry(1.58, 1.72, 0.22, segments),
      materials.chrome,
    );
    plate.position.y = y;
    group.add(plate);

    const inset = mesh(
      new THREE.CylinderGeometry(1.38, 1.45, 0.12, segments),
      materials.steel,
    );
    inset.position.y = y + (y > 0 ? -0.16 : 0.16);
    group.add(inset);

    const lip = mesh(
      new THREE.TorusGeometry(1.55, 0.055, 16, segments),
      materials.chrome,
    );
    lip.rotation.x = Math.PI / 2;
    lip.position.y = y + (y > 0 ? -0.105 : 0.105);
    group.add(lip);
  }

  for (const x of [-1.3, 1.3]) {
    for (const z of [-0.46, 0.46]) {
      const column = mesh(
        new THREE.CylinderGeometry(0.064, 0.086, 3.82, 28),
        materials.chrome,
      );
      column.position.set(x, 0, z);
      group.add(column);
      for (const y of [-1.78, 1.78]) {
        const collar = mesh(
          new THREE.CylinderGeometry(0.112, 0.112, 0.17, 28),
          materials.steel,
        );
        collar.position.set(x, y, z);
        group.add(collar);
      }
    }
  }

  const profile = [
    [0.91, 1.78], [1.04, 1.6], [1.11, 1.22], [1.08, 0.52],
    [0.72, 0.16], [0.72, -0.16], [1.08, -0.5], [1.13, -1.2],
    [1.05, -1.61], [0.91, -1.78],
  ].map(([radius, y]) => new THREE.Vector2(radius, y));
  const vessel = mesh(
    new THREE.LatheGeometry(profile, mobile ? 64 : 112),
    materials.glass,
    { cast: false, receive: false },
  );
  vessel.renderOrder = 5;
  group.add(vessel);

  for (const y of [-1.76, 1.76]) {
    const seal = mesh(
      new THREE.TorusGeometry(0.94, 0.032, 14, segments),
      materials.chrome,
    );
    seal.rotation.x = Math.PI / 2;
    seal.position.y = y;
    group.add(seal);
  }

  const throatMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd9f3f7,
    roughness: 0.035,
    transmission: 0.78,
    thickness: 0.35,
    ior: 1.46,
    transparent: true,
    opacity: 0.72,
    clearcoat: 1,
    depthWrite: false,
  });
  const throat = mesh(
    new THREE.CylinderGeometry(0.29, 0.29, 0.46, segments),
    throatMaterial,
    { cast: false, receive: false },
  );
  group.add(throat);
}

function addHelicalCradle(THREE, helpers, group, material) {
  const points = [];
  const samples = helpers.mobile ? 70 : 120;
  for (let index = 0; index <= samples; index += 1) {
    const t = index / samples;
    const angle = t * 2.8 * TAU;
    const radius = 0.46 + t * 0.42;
    points.push(new THREE.Vector3(
      Math.cos(angle) * radius,
      0.28 + t * 1.24,
      Math.sin(angle) * radius * 0.72,
    ));
  }
  const curve = new THREE.CatmullRomCurve3(points, false, "centripetal", 0.42);
  group.add(helpers.mesh(
    new THREE.TubeGeometry(curve, samples, 0.022, 10, false),
    material,
  ));
}

export function makeBeadsRuntime(THREE, helpers) {
  const { mobile, reducedMotion } = helpers;
  const group = new THREE.Group();
  const count = mobile ? 18 : 24;
  const materials = {
    chrome: makeChrome(THREE),
    steel: makeSteel(THREE),
    glass: new THREE.MeshPhysicalMaterial({
      color: 0xe9f6f7,
      roughness: 0.035,
      metalness: 0,
      transmission: 0.34,
      thickness: 0.28,
      ior: 1.46,
      transparent: true,
      opacity: 0.3,
      clearcoat: 1,
      clearcoatRoughness: 0.02,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
    pearl: makePearl(THREE),
    rail: new THREE.MeshPhysicalMaterial({
      color: 0x8a5d34,
      metalness: 0.88,
      roughness: 0.22,
      clearcoat: 0.72,
      clearcoatRoughness: 0.12,
    }),
  };
  materials.pearl.vertexColors = true;
  materials.pearl.envMapIntensity = 1.45;
  materials.pearl.roughness = 0.24;
  materials.pearl.clearcoat = 0.86;
  materials.pearl.iridescence = 0.72;
  materials.pearl.emissive = new THREE.Color(0x2d241f);
  materials.pearl.emissiveIntensity = 0.13;
  materials.pearl.needsUpdate = true;

  addFrame(THREE, helpers, group, materials);
  addHelicalCradle(THREE, helpers, group, materials.rail);

  const upperSlots = makeUpperSlots(THREE, count);
  const lowerSlots = makeLowerSlots(THREE, count);
  const pearlGeometry = new THREE.SphereGeometry(0.175, mobile ? 32 : 52, mobile ? 22 : 36);
  const pearls = new THREE.InstancedMesh(pearlGeometry, materials.pearl, count);
  pearls.castShadow = !mobile;
  pearls.receiveShadow = true;
  pearls.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  group.add(pearls);

  const glow = new THREE.PointLight(0xffe6bd, mobile ? 3.5 : 6, 5, 2);
  glow.position.set(-0.72, 0.72, 1.35);
  group.add(glow);

  const matrix = new THREE.Matrix4();
  const quaternion = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const position = new THREE.Vector3();
  const throatTop = new THREE.Vector3(0, 0.18, 0.03);
  const throatBottom = new THREE.Vector3(0, -0.5, 0.04);
  const pearlColor = new THREE.Color();
  const warmPearl = new THREE.Color(0xfff0da);
  const coolPearl = new THREE.Color(0xdde8ee);
  const movingPearl = new THREE.Color(0xffd89b);

  function update(progress, time) {
    const transferred = (1 - progress) * count;
    for (let index = 0; index < count; index += 1) {
      const transfer = clamp(transferred - index, 0, 1);
      const upper = upperSlots[index];
      const lower = lowerSlots[index];

      if (transfer <= 0) {
        position.copy(upper);
      } else if (transfer >= 1) {
        position.copy(lower);
      } else {
        const t = ease(transfer);
        if (t < 0.34) {
          const local = ease(t / 0.34);
          position.copy(upper).lerp(throatTop, local);
          position.x += Math.sin(local * Math.PI) * (index % 2 ? 0.09 : -0.09);
        } else if (t < 0.68) {
          const local = ease((t - 0.34) / 0.34);
          position.set(Math.sin(local * TAU + index) * 0.025, 0.18 - local * 0.68, 0.04);
        } else {
          position.copy(throatBottom).lerp(lower, ease((t - 0.68) / 0.32));
        }
      }

      const imperfection = 0.94 + seeded(index, 9) * 0.1;
      const travelling = transfer > 0 && transfer < 1;
      const pulse = travelling && !reducedMotion ? 1 + Math.sin(time * 0.008) * 0.025 : 1;
      scale.set(
        imperfection * pulse,
        (0.95 + seeded(index, 10) * 0.08) * pulse,
        (0.93 + seeded(index, 11) * 0.1) * pulse,
      );
      quaternion.setFromEuler(new THREE.Euler(
        seeded(index, 5) * 0.16,
        seeded(index, 6) * 0.18 + time * (travelling && !reducedMotion ? 0.0014 : 0),
        seeded(index, 7) * 0.14,
      ));
      matrix.compose(position, quaternion, scale);
      pearls.setMatrixAt(index, matrix);

      pearlColor.copy(coolPearl).lerp(warmPearl, 0.5 + seeded(index, 13) * 0.14);
      if (travelling) pearlColor.lerp(movingPearl, 0.3);
      pearls.setColorAt(index, pearlColor);
    }
    pearls.instanceMatrix.needsUpdate = true;
    pearls.instanceColor.needsUpdate = true;
    group.rotation.y = reducedMotion ? 0 : Math.sin(time * 0.00016) * 0.055;
    group.rotation.z = reducedMotion ? 0 : Math.sin(time * 0.00009) * 0.006;
  }

  update(1, 0);
  return { object: group, update };
}
