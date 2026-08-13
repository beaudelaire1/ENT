function makeMoon(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();

  const lunarMaterial = new THREE.MeshStandardMaterial({
    color: 0xc9c6bd,
    roughness: 0.96,
    metalness: 0,
  });
  const sphere = mesh(
    new THREE.SphereGeometry(1.48, mobile ? 64 : 96, mobile ? 40 : 64),
    lunarMaterial,
  );
  group.add(sphere);

  const craterMaterial = new THREE.MeshStandardMaterial({
    color: 0x77756f,
    roughness: 1,
    transparent: true,
    opacity: 0.48,
    polygonOffset: true,
    polygonOffsetFactor: -1,
  });
  const craterData = [
    [-0.34, 0.36, 0.87, 0.22],
    [0.28, 0.42, 0.86, 0.16],
    [0.45, 0.04, 0.89, 0.12],
    [-0.08, -0.12, 0.99, 0.18],
    [-0.42, -0.28, 0.86, 0.14],
    [0.22, -0.42, 0.88, 0.2],
    [0.03, 0.6, 0.8, 0.1],
    [0.53, -0.2, 0.82, 0.09],
  ];
  const forward = new THREE.Vector3(0, 0, 1);
  for (const [x, y, z, size] of craterData) {
    const direction = new THREE.Vector3(x, y, z).normalize();
    const crater = mesh(
      new THREE.CircleGeometry(size, 32),
      craterMaterial.clone(),
      { cast: false, receive: false },
     );
    crater.position.copy(direction).multiplyScalar(1.486);
    crater.quaternion.setFromUnitVectors(forward, direction);
    crater.scale.y = 0.72;
    group.add(crater);
  }

  const target = new THREE.Object3D();
  group.add(target);
  const phaseLight = new THREE.DirectionalLight(0xfff4dc, 7.6);
  phaseLight.target = target;
  group.add(phaseLight);

  function update(progress, time) {
    const angle = (1 - progress) * Math.PI;
    phaseLight.position.set(Math.sin(angle) * 5.5, 1.25, Math.cos(angle) * 5.5);
    group.rotation.y = reducedMotion ? -0.16 : -0.16 + Math.sin(time * 0.00008) * 0.06;
    group.rotation.x = reducedMotion ? 0.03 : 0.03 + Math.sin(time * 0.00005) * 0.018;
  }

  return { object: group, update };
}

function makeGlowTexture(THREE) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 256;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createRadialGradient(128, 128, 8, 128, 128, 128);
  gradient.addColorStop(0, "rgba(255,249,214,1)");
  gradient.addColorStop(0.16, "rgba(255,184,74,.94)");
  gradient.addColorStop(0.42, "rgba(255,106,24,.42)");
  gradient.addColorStop(1, "rgba(255,72,0,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 256, 256);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function makeSun(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();

  const sphere = mesh(
    new THREE.SphereGeometry(1.22, mobile ? 64 : 96, mobile ? 40 : 64),
    new THREE.MeshStandardMaterial({
      color: 0xffa126,
      emissive: 0xff5b12,
      emissiveIntensity: 3.8,
      roughness: 0.72,
      metalness: 0,
    }),
    { cast: false, receive: false },
  );
  group.add(sphere);

  const glow = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: makeGlowTexture(THREE),
      color: 0xffa13d,
      transparent: true,
      opacity: 0.88,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
  );
  glow.scale.set(5.9, 5.9, 1);
  group.add(glow);

  const light = new THREE.PointLight(0xff9c43, 34, 18, 1.4);
  group.add(light);

  const coronaGeometry = new THREE.RingGeometry(1.35, 1.67, mobile ? 64 : 128);
  const corona = mesh(
    coronaGeometry,
    new THREE.MeshBasicMaterial({
      color: 0xffa453,
      transparent: true,
      opacity: 0.16,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
    { cast: false, receive: false },
  );
  group.add(corona);

  function update(progress, time) {
    const angle = progress * Math.PI;
    group.position.x = Math.cos(angle) * 1.45;
    group.position.y = -0.72 + Math.sin(angle) * 1.25;
    const pulse = reducedMotion ? 1 : 1 + Math.sin(time * 0.0022) * 0.018;
    sphere.scale.setScalar(pulse);
    glow.material.opacity = reducedMotion ? 0.84 : 0.8 + Math.sin(time * 0.0017) * 0.07;
    corona.rotation.z = reducedMotion ? 0 : time * 0.000025;
    corona.material.opacity = reducedMotion ? 0.14 : 0.14 + Math.sin(time * 0.0013) * 0.035;
    sphere.rotation.y = reducedMotion ? 0 : time * 0.000035;
  }

  return { object: group, update };
}

export function makeCelestialRuntime(THREE, helpers) {
  return {
    moon: () => makeMoon(THREE, helpers),
    sun: () => makeSun(THREE, helpers),
  };
}
