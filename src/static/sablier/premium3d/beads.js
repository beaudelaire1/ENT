export function makeBeadsRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const count = mobile ? 28 : 34;
  const points = [];

  for (let i = 0; i < count; i += 1) {
    const angle = (i / count) * Math.PI * 2;
    points.push(
      new THREE.Vector3(
        Math.cos(angle) * 1.72,
        Math.sin(angle) * 1.38,
        Math.sin(angle * 2.2) * 0.18,
      ),
    );
  }

  const curve = new THREE.CatmullRomCurve3([...points, points[0].clone()], true, "centripetal", 0.4);
  const thread = mesh(
    new THREE.TubeGeometry(curve, count * 6, 0.035, 10, true),
    new THREE.MeshPhysicalMaterial({ color: 0x3c3028, roughness: 0.5, metalness: 0.08 }),
  );
  group.add(thread);

  const geometry = new THREE.SphereGeometry(0.225, mobile ? 24 : 36, mobile ? 16 : 24);
  const material = new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    roughness: 0.13,
    metalness: 0.04,
    clearcoat: 1,
    clearcoatRoughness: 0.07,
    iridescence: 0.72,
    iridescenceIOR: 1.32,
    iridescenceThicknessRange: [120, 420],
    vertexColors: true,
  });
  const beads = new THREE.InstancedMesh(geometry, material, count);
  beads.castShadow = !mobile;
  beads.receiveShadow = true;

  const matrix = new THREE.Matrix4();
  const scaleMatrix = new THREE.Matrix4();
  for (let i = 0; i < count; i += 1) {
    matrix.makeTranslation(points[i].x, points[i].y, points[i].z);
    beads.setMatrixAt(i, matrix);
    beads.setColorAt(i, new THREE.Color(0xf5eee2));
  }
  beads.instanceMatrix.needsUpdate = true;
  beads.instanceColor.needsUpdate = true;
  group.add(beads);
  group.rotation.x = -0.08;

  const active = new THREE.Color(0xffe0aa);
  const pearl = new THREE.Color(0xe9e4dc);
  const spent = new THREE.Color(0x343942);

  function update(progress, time) {
    const alive = progress * count;
    for (let i = 0; i < count; i += 1) {
      const fill = Math.max(0, Math.min(1, alive - i));
      const scale = 0.83 + fill * 0.17;
      scaleMatrix.makeScale(scale, scale, scale);
      matrix.makeTranslation(points[i].x, points[i].y, points[i].z);
      matrix.multiply(scaleMatrix);
      beads.setMatrixAt(i, matrix);
      const color = fill > 0.5
        ? pearl.clone().lerp(active, 0.22)
        : spent.clone().lerp(pearl, fill);
      beads.setColorAt(i, color);
    }
    beads.instanceMatrix.needsUpdate = true;
    beads.instanceColor.needsUpdate = true;
    group.rotation.y = reducedMotion ? 0 : Math.sin(time * 0.00022) * 0.16;
    group.rotation.z = reducedMotion ? 0 : Math.sin(time * 0.00013) * 0.025;
  }

  return { object: group, update };
}
