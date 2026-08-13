export function makeCandleRuntime(THREE, helpers, state) {
  const { reducedMotion, mesh, materials } = helpers;
  const group = new THREE.Group();
  const wax = materials.wax();

  const body = mesh(new THREE.CylinderGeometry(0.78, 0.86, 3.4, 72, 10), wax);
  group.add(body);

  const rim = mesh(new THREE.TorusGeometry(0.73, 0.055, 18, 72), wax);
  rim.rotation.x = Math.PI / 2;
  group.add(rim);

  const pool = mesh(
    new THREE.CylinderGeometry(0.66, 0.68, 0.055, 64),
    new THREE.MeshPhysicalMaterial({ color: 0xffe8c9, roughness: 0.28, clearcoat: 0.55 }),
  );
  group.add(pool);

  const wick = mesh(
    new THREE.CylinderGeometry(0.025, 0.035, 0.26, 12),
    new THREE.MeshStandardMaterial({ color: 0x1b1715, roughness: 0.9 }),
  );
  group.add(wick);

  const outer = mesh(
    new THREE.SphereGeometry(0.25, 28, 20),
    new THREE.MeshBasicMaterial({
      color: 0xff8b25,
      transparent: true,
      opacity: 0.78,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
    { cast: false, receive: false },
  );
  outer.scale.set(0.75, 1.8, 0.75);
  group.add(outer);

  const inner = mesh(
    new THREE.SphereGeometry(0.15, 24, 18),
    new THREE.MeshBasicMaterial({
      color: 0xfff6c9,
      transparent: true,
      opacity: 0.92,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
    { cast: false, receive: false },
  );
  inner.scale.set(0.66, 1.55, 0.66);
  group.add(inner);

  const flameLight = new THREE.PointLight(0xff9c48, 24, 7, 2);
  group.add(flameLight);

  const drips = [];
  for (const [angle, length, radius] of [
    [0.35, 0.74, 0.065],
    [2.1, 0.48, 0.055],
    [4.65, 0.62, 0.06],
  ]) {
    const drip = mesh(new THREE.CylinderGeometry(radius * 0.72, radius, length, 18), materials.wax());
    drip.userData = { angle, length };
    drips.push(drip);
    group.add(drip);
  }

  function update(progress, time) {
    const height = 0.34 + 3.06 * progress;
    body.scale.y = height / 3.4;
    body.position.y = -1.7 + height / 2;
    const topY = -1.7 + height;
    rim.position.y = topY;
    pool.position.y = topY;
    wick.position.y = topY + 0.12;

    for (const drip of drips) {
      const { angle, length } = drip.userData;
      const visibleLength = Math.min(length, Math.max(0.08, height * 0.34));
      drip.scale.y = visibleLength / length;
      drip.position.set(
        Math.cos(angle) * 0.72,
        topY - visibleLength / 2 - 0.05,
        Math.sin(angle) * 0.72,
      );
      drip.visible = progress > 0.12;
    }

    const flameY = topY + 0.54;
    outer.position.y = flameY;
    inner.position.y = flameY - 0.04;
    flameLight.position.y = topY + 0.35;

    const alive = progress > 0.015 && !state.finished;
    outer.visible = alive;
    inner.visible = alive;
    flameLight.visible = alive;

    if (alive && !reducedMotion) {
      const flicker = 1 + Math.sin(time * 0.012) * 0.065 + Math.sin(time * 0.027) * 0.025;
      outer.scale.set(0.75 / flicker, 1.8 * flicker, 0.75 / flicker);
      inner.scale.set(0.66, 1.55 * (2 - flicker), 0.66);
      outer.position.x = Math.sin(time * 0.008) * 0.035;
      inner.position.x = outer.position.x * 0.5;
      flameLight.intensity = 22 + Math.sin(time * 0.017) * 4;
    }

    group.rotation.y = reducedMotion ? 0 : Math.sin(time * 0.00016) * 0.055;
  }

  return { object: group, update };
}
