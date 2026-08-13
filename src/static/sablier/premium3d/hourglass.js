export function makeHourglassRuntime(THREE, helpers, state) {
  const { mobile, reducedMotion, mesh, materials } = helpers;
  const group = new THREE.Group();
  const frame = materials.bronze();
  const dark = materials.darkMetal();

  for (const y of [-2.08, 2.08]) {
    const plate = mesh(new THREE.CylinderGeometry(1.55, 1.66, 0.22, 72), frame);
    plate.position.y = y;
    group.add(plate);
    const ring = mesh(new THREE.TorusGeometry(1.42, 0.055, 18, 96), dark);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = y + (y > 0 ? -0.13 : 0.13);
    group.add(ring);
  }

  for (const x of [-1.27, 1.27]) {
    for (const z of [-0.38, 0.38]) {
      const column = mesh(new THREE.CylinderGeometry(0.075, 0.095, 4.05, 28), frame);
      column.position.set(x, 0, z);
      group.add(column);
    }
  }

  const profile = [
    [0.82, 1.78], [0.96, 1.58], [0.92, 1.28], [0.74, 0.89], [0.46, 0.48], [0.18, 0.1],
    [0.18, -0.1], [0.46, -0.48], [0.74, -0.89], [0.92, -1.28], [0.96, -1.58], [0.82, -1.78],
  ].map(([radius, y]) => new THREE.Vector2(radius, y));

  const vessel = mesh(
    new THREE.LatheGeometry(profile, mobile ? 56 : 96),
    materials.glass(),
    { cast: false, receive: false },
  );
  vessel.renderOrder = 3;
  group.add(vessel);

  const top = mesh(new THREE.ConeGeometry(0.82, 1.4, mobile ? 40 : 64), materials.sand());
  top.rotation.z = Math.PI;
  group.add(top);

  const bottom = mesh(new THREE.ConeGeometry(0.92, 1.25, mobile ? 40 : 64), materials.sand());
  group.add(bottom);

  const stream = mesh(
    new THREE.CylinderGeometry(0.018, 0.026, 1.35, 12),
    new THREE.MeshStandardMaterial({ color: 0xf0c77d, roughness: 0.75 }),
    { cast: false, receive: false },
  );
  group.add(stream);

  const grainCount = mobile ? 34 : 68;
  const positions = new Float32Array(grainCount * 3);
  const seeds = new Float32Array(grainCount);
  for (let i = 0; i < grainCount; i += 1) {
    seeds[i] = Math.abs((Math.sin(i * 913.17) * 43758.5453) % 1);
    positions[i * 3] = Math.sin(i * 3.7) * 0.035;
    positions[i * 3 + 1] = -0.05 - seeds[i] * 1.35;
    positions[i * 3 + 2] = Math.cos(i * 5.1) * 0.035;
  }
  const grainGeometry = new THREE.BufferGeometry();
  grainGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const grains = new THREE.Points(
    grainGeometry,
    new THREE.PointsMaterial({
      color: 0xffd993,
      size: mobile ? 0.025 : 0.032,
      transparent: true,
      opacity: 0.86,
    }),
  );
  grains.userData.seeds = seeds;
  group.add(grains);
  group.rotation.x = -0.035;

  function update(progress, time) {
    const received = 1 - progress;
    const topScale = Math.max(0.001, Math.pow(progress, 0.58));
    top.scale.set(topScale, Math.max(0.001, progress), topScale);
    top.position.y = 0.11 + 0.7 * progress;
    top.visible = progress > 0.004;

    const bottomScale = Math.max(0.001, Math.pow(received, 0.56));
    bottom.scale.set(bottomScale, Math.max(0.001, received), bottomScale);
    bottom.position.y = -1.72 + 0.625 * received;
    bottom.visible = received > 0.004;

    const moundTop = -1.72 + 1.25 * received;
    const streamLength = Math.max(0.08, -0.12 - moundTop);
    stream.scale.y = streamLength / 1.35;
    stream.position.y = (-0.12 + moundTop) / 2;
    stream.visible = state.running && progress > 0.006 && received < 0.995;
    grains.visible = stream.visible;

    if (stream.visible && !reducedMotion) {
      const attribute = grains.geometry.getAttribute("position");
      for (let i = 0; i < seeds.length; i += 1) {
        const travel = ((time * 0.00125 + seeds[i] * 1.7) % 1) * streamLength;
        attribute.array[i * 3 + 1] = -0.12 - travel;
      }
      attribute.needsUpdate = true;
    }
    group.rotation.y = reducedMotion ? 0 : Math.sin(time * 0.00019) * 0.075;
  }

  return { object: group, update };
}
