import { makeChrome, makeGlass, makeSteel, seeded } from "./material-kit.js";

export function makeBarsRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const count = mobile ? 10 : 14;
  const chrome = makeChrome(THREE);
  const steel = makeSteel(THREE);
  const glass = makeGlass(THREE);
  const activeMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xf2bc71,
    emissive: 0x4e2107,
    emissiveIntensity: 0.72,
    metalness: 0.18,
    roughness: 0.2,
    clearcoat: 0.9,
    clearcoatRoughness: 0.055,
  });
  const inactiveMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x1a2029,
    metalness: 0.72,
    roughness: 0.34,
    clearcoat: 0.42,
    clearcoatRoughness: 0.18,
  });

  const base = mesh(new THREE.BoxGeometry(4.7, 0.22, 1.45), inactiveMaterial);
  base.position.y = -1.7;
  group.add(base);

  const frontRail = mesh(new THREE.BoxGeometry(4.82, 0.065, 0.12), chrome);
  frontRail.position.set(0, -1.55, 0.76);
  group.add(frontRail);

  const fills = [];
  const caps = [];
  const heights = [];
  const span = 4.25;
  const step = span / count;
  const width = step * 0.48;
  const left = -span / 2 + step / 2;

  for (let i = 0; i < count; i += 1) {
    const fullHeight = 1.45 + seeded(i, 61) * 1.75;
    const x = left + i * step;
    heights.push(fullHeight);

    const shell = mesh(new THREE.BoxGeometry(width, fullHeight, 0.52), glass, {
      cast: false,
      receive: false,
    });
    shell.position.set(x, -1.54 + fullHeight / 2, 0);
    shell.renderOrder = 4;
    group.add(shell);

    const frame = mesh(new THREE.BoxGeometry(width + 0.06, fullHeight + 0.08, 0.12), steel);
    frame.position.set(x, -1.54 + fullHeight / 2, -0.31);
    group.add(frame);

    const fill = mesh(new THREE.BoxGeometry(width * 0.68, 1, 0.31), activeMaterial);
    fill.position.set(x, -1.54, 0.02);
    group.add(fill);
    fills.push(fill);

    const cap = mesh(new THREE.CylinderGeometry(width * 0.21, width * 0.21, 0.07, 20), chrome);
    cap.rotation.x = Math.PI / 2;
    cap.position.set(x, -1.5, 0.2);
    group.add(cap);
    caps.push(cap);
  }

  const sideLeft = mesh(new THREE.CylinderGeometry(0.07, 0.08, 3.8, 28), chrome);
  sideLeft.position.set(-2.42, 0.05, -0.2);
  group.add(sideLeft);
  const sideRight = sideLeft.clone();
  sideRight.position.x = 2.42;
  group.add(sideRight);

  const indicator = new THREE.PointLight(0xffb45f, mobile ? 5 : 8, 5.5, 2);
  indicator.position.set(-1.4, 0.8, 1.8);
  group.add(indicator);

  function update(progress, time) {
    const alive = progress * count;
    let firstPartial = -1;
    for (let i = 0; i < count; i += 1) {
      const fill = Math.max(0, Math.min(1, alive - i));
      const height = Math.max(0.002, heights[i] * fill);
      fills[i].scale.y = height;
      fills[i].position.y = -1.54 + height / 2;
      fills[i].visible = fill > 0.001;
      caps[i].position.y = -1.5 + height;
      caps[i].visible = fill > 0.001;
      if (fill > 0.001 && fill < 0.999 && firstPartial < 0) firstPartial = i;
    }

    const focusIndex = firstPartial >= 0 ? firstPartial : Math.max(0, Math.ceil(alive) - 1);
    const x = left + focusIndex * step;
    indicator.position.x = x;
    indicator.position.y = -1.1 + heights[focusIndex] * Math.max(0.15, Math.min(1, alive - focusIndex));
    indicator.intensity = (mobile ? 5 : 8) * (0.84 + (reducedMotion ? 0 : Math.sin(time * 0.0024) * 0.08));

    group.rotation.y = reducedMotion ? 0 : Math.sin(time * 0.00013) * 0.055;
    group.rotation.x = -0.04;
  }

  return { object: group, update };
}
