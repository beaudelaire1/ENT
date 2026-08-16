import { makeChrome, makeGlass, makeSteel } from "./material-kit.js";

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
  const glass = makeGlass(THREE);
  const plateMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x10151d,
    metalness: 0.86,
    roughness: 0.26,
    clearcoat: 0.84,
    clearcoatRoughness: 0.09,
  });
  const activeMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xffd99d,
    emissive: 0x6b2b00,
    emissiveIntensity: 1.18,
    metalness: 0.28,
    roughness: 0.14,
    clearcoat: 1,
    clearcoatRoughness: 0.025,
  });
  const glowMaterial = new THREE.MeshBasicMaterial({
    color: 0xffa849,
    transparent: true,
    opacity: 0.16,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  const plate = mesh(new THREE.CylinderGeometry(2.08, 2.08, 0.2, mobile ? 72 : 112), plateMaterial);
  plate.rotation.x = Math.PI / 2;
  plate.position.z = -0.16;
  group.add(plate);

  const outerRing = mesh(new THREE.TorusGeometry(1.95, 0.07, 18, mobile ? 72 : 112), chrome);
  outerRing.position.z = 0.03;
  group.add(outerRing);

  const innerRing = mesh(new THREE.TorusGeometry(0.36, 0.025, 14, 52), steel);
  innerRing.position.z = 0.11;
  group.add(innerRing);

  const crystal = mesh(new THREE.CircleGeometry(1.86, mobile ? 72 : 112), glass, { cast: false, receive: false });
  crystal.position.z = 0.255;
  crystal.renderOrder = 8;
  group.add(crystal);

  const fullPoints = spiralPoints(THREE, 1, mobile ? 240 : 360);
  const fullTube = mesh(tubeFromPoints(THREE, fullPoints, 0.043, mobile ? 240 : 360), steel);
  fullTube.position.z = 0.015;
  group.add(fullTube);

  let active = mesh(tubeFromPoints(THREE, fullPoints, 0.068, mobile ? 240 : 360), activeMaterial);
  active.position.z = 0.035;
  group.add(active);

  let glowTube = mesh(
    tubeFromPoints(THREE, fullPoints, 0.115, mobile ? 180 : 280),
    glowMaterial,
    { cast: false, receive: false },
  );
  glowTube.position.z = 0.025;
  glowTube.renderOrder = 5;
  group.add(glowTube);

  const markerMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd9e3ec,
    metalness: 0.9,
    roughness: 0.18,
    clearcoat: 0.6,
  });
  for (let i = 0; i < 16; i += 1) {
    const angle = (i / 16) * Math.PI * 2;
    const marker = mesh(
      new THREE.BoxGeometry(i % 4 === 0 ? 0.07 : 0.04, i % 4 === 0 ? 0.2 : 0.12, 0.028),
      markerMaterial,
      { cast: false, receive: false },
    );
    marker.position.set(Math.cos(angle) * 1.73, Math.sin(angle) * 1.73, 0.19);
    marker.rotation.z = angle + Math.PI / 2;
    group.add(marker);
  }

  for (const angle of [Math.PI / 4, (3 * Math.PI) / 4, (5 * Math.PI) / 4, (7 * Math.PI) / 4]) {
    const screw = mesh(new THREE.CylinderGeometry(0.055, 0.055, 0.035, 18), chrome);
    screw.rotation.x = Math.PI / 2;
    screw.position.set(Math.cos(angle) * 1.84, Math.sin(angle) * 1.84, 0.18);
    group.add(screw);
  }

  const head = mesh(new THREE.SphereGeometry(0.125, 28, 20), activeMaterial);
  head.position.z = 0.22;
  group.add(head);

  const centerPin = mesh(new THREE.CylinderGeometry(0.14, 0.17, 0.22, 30), chrome);
  centerPin.rotation.x = Math.PI / 2;
  centerPin.position.z = 0.13;
  group.add(centerPin);

  const centerJewel = mesh(
    new THREE.SphereGeometry(0.085, 24, 18),
    new THREE.MeshPhysicalMaterial({
      color: 0xffb767,
      emissive: 0x7a2e00,
      emissiveIntensity: 1.3,
      roughness: 0.08,
      transmission: 0.22,
      thickness: 0.16,
      clearcoat: 1,
    }),
    { cast: false, receive: false },
  );
  centerJewel.position.z = 0.29;
  group.add(centerJewel);

  const glow = new THREE.PointLight(0xffb65c, mobile ? 5.5 : 9, 5, 2);
  glow.position.set(0, 0, 1.38);
  group.add(glow);

  let lastGeometryProgress = 1;
  function updateGeometry(progress) {
    if (progress <= 0.002) {
      active.visible = false;
      glowTube.visible = false;
      head.visible = false;
      return;
    }
    active.visible = true;
    glowTube.visible = true;
    head.visible = true;

    if (Math.abs(progress - lastGeometryProgress) > 1 / 240) {
      const points = spiralPoints(THREE, progress, mobile ? 240 : 360);
      const oldActive = active.geometry;
      const oldGlow = glowTube.geometry;
      active.geometry = tubeFromPoints(
        THREE,
        points,
        0.068,
        Math.max(16, Math.round((mobile ? 240 : 360) * progress)),
      );
      glowTube.geometry = tubeFromPoints(
        THREE,
        points,
        0.115,
        Math.max(14, Math.round((mobile ? 180 : 280) * progress)),
      );
      oldActive.dispose();
      oldGlow.dispose();
      lastGeometryProgress = progress;
    }

    const angle = progress * Math.PI * 8 - Math.PI / 2;
    const radius = 0.13 + progress * 1.66;
    head.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius, 0.22);
    glow.position.set(Math.cos(angle) * radius * 0.68, Math.sin(angle) * radius * 0.68, 1.38);
  }

  function update(progress, time) {
    updateGeometry(progress);
    if (!reducedMotion) {
      group.rotation.y = Math.sin(time * 0.00013) * 0.052;
      group.rotation.x = -0.038 + Math.sin(time * 0.00009) * 0.014;
      activeMaterial.emissiveIntensity = 1.08 + Math.sin(time * 0.0021) * 0.11;
      glowMaterial.opacity = 0.13 + Math.sin(time * 0.0018) * 0.035;
      centerJewel.material.emissiveIntensity = 1.2 + Math.sin(time * 0.0024) * 0.15;
    }
  }

  return { object: group, update };
}
