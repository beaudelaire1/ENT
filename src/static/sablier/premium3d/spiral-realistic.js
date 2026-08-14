import { makeChrome, makeSteel } from "./material-kit.js";

function spiralPoints(THREE, fraction, steps = 360) {
  const points = [];
  const safe = Math.max(0.004, fraction);
  const count = Math.max(3, Math.round(steps * safe));
  for (let i = 0; i <= count; i += 1) {
    const t = (i / count) * safe;
    const angle = t * Math.PI * 8 - Math.PI / 2;
    const radius = 0.13 + t * 1.66;
    points.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0.14));
  }
  return points;
}

function tubeFromPoints(THREE, points, radius, tubularSegments) {
  const curve = new THREE.CatmullRomCurve3(points, false, "centripetal", 0.35);
  return new THREE.TubeGeometry(curve, tubularSegments, radius, 10, false);
}

export function makeSpiralRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const chrome = makeChrome(THREE);
  const steel = makeSteel(THREE);
  const plateMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x11151c,
    metalness: 0.84,
    roughness: 0.3,
    clearcoat: 0.7,
    clearcoatRoughness: 0.14,
  });
  const activeMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xffd393,
    emissive: 0x612700,
    emissiveIntensity: 1.05,
    metalness: 0.38,
    roughness: 0.19,
    clearcoat: 1,
    clearcoatRoughness: 0.04,
  });

  const plate = mesh(new THREE.CylinderGeometry(2.05, 2.05, 0.18, mobile ? 72 : 112), plateMaterial);
  plate.rotation.x = Math.PI / 2;
  plate.position.z = -0.14;
  group.add(plate);

  const outerRing = mesh(new THREE.TorusGeometry(1.92, 0.055, 16, mobile ? 72 : 112), chrome);
  outerRing.position.z = 0.03;
  group.add(outerRing);

  const fullPoints = spiralPoints(THREE, 1, mobile ? 240 : 360);
  const fullTube = mesh(
    tubeFromPoints(THREE, fullPoints, 0.045, mobile ? 240 : 360),
    steel,
  );
  group.add(fullTube);

  let active = mesh(
    tubeFromPoints(THREE, fullPoints, 0.072, mobile ? 240 : 360),
    activeMaterial,
  );
  group.add(active);

  const head = mesh(new THREE.SphereGeometry(0.12, 24, 18), activeMaterial);
  head.position.z = 0.18;
  group.add(head);

  const centerPin = mesh(new THREE.CylinderGeometry(0.13, 0.16, 0.2, 28), chrome);
  centerPin.rotation.x = Math.PI / 2;
  centerPin.position.z = 0.12;
  group.add(centerPin);

  const glow = new THREE.PointLight(0xffb65c, mobile ? 5 : 8, 4.8, 2);
  glow.position.set(0, 0, 1.35);
  group.add(glow);

  let lastGeometryProgress = 1;
  function updateGeometry(progress) {
    if (progress <= 0.002) {
      active.visible = false;
      head.visible = false;
      return;
    }
    active.visible = true;
    head.visible = true;

    if (Math.abs(progress - lastGeometryProgress) > 1 / 240) {
      const points = spiralPoints(THREE, progress, mobile ? 240 : 360);
      const old = active.geometry;
      active.geometry = tubeFromPoints(
        THREE,
        points,
        0.072,
        Math.max(16, Math.round((mobile ? 240 : 360) * progress)),
      );
      old.dispose();
      lastGeometryProgress = progress;
    }

    const angle = progress * Math.PI * 8 - Math.PI / 2;
    const radius = 0.13 + progress * 1.66;
    head.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius, 0.18);
    glow.position.set(Math.cos(angle) * radius * 0.65, Math.sin(angle) * radius * 0.65, 1.35);
  }

  function update(progress, time) {
    updateGeometry(progress);
    if (!reducedMotion) {
      group.rotation.y = Math.sin(time * 0.00013) * 0.05;
      group.rotation.x = -0.035 + Math.sin(time * 0.00009) * 0.014;
      activeMaterial.emissiveIntensity = 0.98 + Math.sin(time * 0.0021) * 0.09;
    }
  }

  return { object: group, update };
}
