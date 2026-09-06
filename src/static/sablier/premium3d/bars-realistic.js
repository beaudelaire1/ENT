import { makeChrome, makeGlass, makeSteel, seeded } from "./material-kit.js";

export function makeBarsRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const count = mobile ? 10 : 14;
  const chrome = makeChrome(THREE);
  const steel = makeSteel(THREE);
  const glass = makeGlass(THREE);
  const amber = new THREE.MeshPhysicalMaterial({
    color: 0xe9a957,
    emissive: 0x5c2606,
    emissiveIntensity: 0.82,
    metalness: 0.03,
    roughness: 0.12,
    transmission: 0.18,
    thickness: 0.42,
    clearcoat: 1,
    clearcoatRoughness: 0.035,
    attenuationColor: new THREE.Color(0xb45d18),
    attenuationDistance: 2.4,
  });
  const graphite = new THREE.MeshPhysicalMaterial({
    color: 0x111720,
    metalness: 0.78,
    roughness: 0.28,
    clearcoat: 0.72,
    clearcoatRoughness: 0.12,
  });
  const tickMaterial = new THREE.MeshStandardMaterial({
    color: 0xd9e4ef,
    metalness: 0.75,
    roughness: 0.3,
  });
  // Le bâti est structurel, pas décoratif : il tient les montants et les quatorze
  // tubes de verre, qui sans lui tomberaient. C'est ce qui le distingue d'un socle —
  // le placage d'acier et la rampe lumineuse qui le doublaient, eux, ne servaient
  // qu'à faire joli sur fond neutre et ont été retirés.
  const base = mesh(new THREE.BoxGeometry(4.9, 0.24, 1.5), graphite);
  base.position.y = -1.75;
  group.add(base);

  const frontRail = mesh(new THREE.BoxGeometry(5.02, 0.065, 0.11), chrome);
  frontRail.position.set(0, -1.55, 0.81);
  group.add(frontRail);
  const backRail = frontRail.clone();
  backRail.position.z = -0.81;
  group.add(backRail);

  const fills = [];
  const menisci = [];
  const heights = [];
  const barLights = [];
  const span = 4.25;
  const step = span / count;
  const width = step * 0.48;
  const left = -span / 2 + step / 2;

  for (let i = 0; i < count; i += 1) {
    const fullHeight = 1.5 + seeded(i, 61) * 1.68;
    const x = left + i * step;
    heights.push(fullHeight);

    const shell = mesh(new THREE.BoxGeometry(width, fullHeight, 0.5), glass, {
      cast: false,
      receive: false,
    });
    shell.position.set(x, -1.53 + fullHeight / 2, 0);
    shell.renderOrder = 5;
    group.add(shell);

    const backFrame = mesh(new THREE.BoxGeometry(width + 0.06, fullHeight + 0.08, 0.1), steel);
    backFrame.position.set(x, -1.53 + fullHeight / 2, -0.31);
    group.add(backFrame);

    const topClamp = mesh(new THREE.BoxGeometry(width + 0.08, 0.07, 0.62), chrome);
    topClamp.position.set(x, -1.49 + fullHeight, 0);
    group.add(topClamp);

    const bottomClamp = mesh(new THREE.BoxGeometry(width + 0.08, 0.07, 0.62), chrome);
    bottomClamp.position.set(x, -1.5, 0);
    group.add(bottomClamp);

    const fill = mesh(new THREE.BoxGeometry(width * 0.66, 1, 0.31), amber, { cast: false, receive: false });
    fill.position.set(x, -1.5, 0.02);
    group.add(fill);
    fills.push(fill);

    const meniscus = mesh(
      new THREE.SphereGeometry(width * 0.38, 20, 12),
      amber,
      { cast: false, receive: false },
    );
    meniscus.scale.set(1, 0.22, 0.72);
    meniscus.position.set(x, -1.48, 0.02);
    meniscus.renderOrder = 4;
    group.add(meniscus);
    menisci.push(meniscus);

    for (let tick = 1; tick <= 3; tick += 1) {
      const mark = mesh(
        new THREE.BoxGeometry(width * (tick === 2 ? 0.42 : 0.28), 0.018, 0.024),
        tickMaterial,
        { cast: false, receive: false },
      );
      mark.position.set(x + width * 0.3, -1.53 + (fullHeight * tick) / 4, 0.285);
      group.add(mark);
    }

    const barLight = new THREE.PointLight(0xffb35a, mobile ? 0.7 : 1.05, 1.25, 2);
    barLight.position.set(x, -1.15, 0.62);
    group.add(barLight);
    barLights.push(barLight);
  }

  const sideLeft = mesh(new THREE.CylinderGeometry(0.075, 0.09, 3.92, 28), chrome);
  sideLeft.position.set(-2.48, 0.06, -0.18);
  group.add(sideLeft);
  const sideRight = sideLeft.clone();
  sideRight.position.x = 2.48;
  group.add(sideRight);

  for (const x of [-2.48, 2.48]) {
    for (const y of [-1.71, 1.92]) {
      const collar = mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.15, 24), steel);
      collar.position.set(x, y, -0.18);
      group.add(collar);
    }
  }

  const indicator = new THREE.PointLight(0xffb45f, mobile ? 5.5 : 9, 5.8, 2);
  indicator.position.set(-1.4, 0.8, 1.75);
  group.add(indicator);

  const indicatorLens = mesh(
    new THREE.SphereGeometry(0.105, 24, 18),
    new THREE.MeshPhysicalMaterial({
      color: 0xffd28a,
      emissive: 0x8e3c08,
      emissiveIntensity: 1.45,
      roughness: 0.12,
      clearcoat: 1,
    }),
    { cast: false, receive: false },
  );
  indicatorLens.position.z = 0.52;
  group.add(indicatorLens);

  function update(progress, time) {
    const alive = progress * count;
    let firstPartial = -1;
    for (let i = 0; i < count; i += 1) {
      const amount = Math.max(0, Math.min(1, alive - i));
      const height = Math.max(0.002, heights[i] * amount);
      fills[i].scale.y = height;
      fills[i].position.y = -1.5 + height / 2;
      fills[i].visible = amount > 0.001;
      menisci[i].position.y = -1.48 + height;
      menisci[i].visible = amount > 0.001;
      barLights[i].position.y = Math.min(-1.08 + height, 1.45);
      barLights[i].intensity = amount > 0.001 ? (mobile ? 0.7 : 1.05) * (0.45 + amount * 0.55) : 0;
      if (amount > 0.001 && amount < 0.999 && firstPartial < 0) firstPartial = i;
    }

    const focusIndex = firstPartial >= 0 ? firstPartial : Math.max(0, Math.min(count - 1, Math.ceil(alive) - 1));
    const amount = Math.max(0.04, Math.min(1, alive - focusIndex));
    const x = left + focusIndex * step;
    const y = -1.05 + heights[focusIndex] * amount;
    indicator.position.set(x, y, 1.7);
    indicatorLens.position.set(x, y, 0.52);
    indicator.intensity = (mobile ? 5.5 : 9) * (0.86 + (reducedMotion ? 0 : Math.sin(time * 0.0024) * 0.08));

    if (!reducedMotion) {
      const pulse = 0.78 + Math.sin(time * 0.0018) * 0.08;
      amber.emissiveIntensity = pulse;
      group.rotation.y = Math.sin(time * 0.00013) * 0.052;
    } else {
      group.rotation.y = 0;
    }
    group.rotation.x = -0.045;
  }

  return { object: group, update };
}
