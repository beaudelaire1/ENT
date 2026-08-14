import { makeChrome, makeGlass, seeded } from "./material-kit.js";

export function makeWaveRuntime(THREE, helpers, state) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const segments = mobile ? 56 : 88;
  const glass = makeGlass(THREE);
  const chrome = makeChrome(THREE);
  const water = new THREE.MeshPhysicalMaterial({
    color: 0x3296b8,
    roughness: 0.065,
    metalness: 0,
    transmission: 0.58,
    thickness: 1.1,
    ior: 1.333,
    transparent: true,
    opacity: 0.94,
    clearcoat: 0.92,
    clearcoatRoughness: 0.025,
    attenuationColor: new THREE.Color(0x075d79),
    attenuationDistance: 2.35,
  });
  const surfaceMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x91e6f4,
    emissive: 0x063b4a,
    emissiveIntensity: 0.38,
    roughness: 0.045,
    metalness: 0,
    transmission: 0.38,
    transparent: true,
    opacity: 0.95,
    clearcoat: 1,
    clearcoatRoughness: 0.018,
    side: THREE.DoubleSide,
  });
  const bubbleMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xeafcff,
    roughness: 0.02,
    transmission: 0.9,
    thickness: 0.18,
    ior: 1.2,
    transparent: true,
    opacity: 0.5,
    clearcoat: 1,
    depthWrite: false,
  });

  const vessel = mesh(
    new THREE.CylinderGeometry(1.58, 1.58, 3.08, segments, 1, true),
    glass,
    { cast: false, receive: false },
  );
  vessel.renderOrder = 6;
  group.add(vessel);

  const glassBottom = mesh(new THREE.CylinderGeometry(1.58, 1.58, 0.15, segments), glass, {
    cast: false,
    receive: false,
  });
  glassBottom.position.y = -1.54;
  glassBottom.renderOrder = 6;
  group.add(glassBottom);

  const rim = mesh(new THREE.TorusGeometry(1.585, 0.065, 18, segments), chrome);
  rim.rotation.x = Math.PI / 2;
  rim.position.y = 1.54;
  group.add(rim);

  const foot = mesh(new THREE.CylinderGeometry(1.82, 1.92, 0.18, segments), chrome);
  foot.position.y = -1.7;
  group.add(foot);

  const footInset = mesh(
    new THREE.CylinderGeometry(1.55, 1.66, 0.07, segments),
    new THREE.MeshPhysicalMaterial({ color: 0x161b22, metalness: 0.82, roughness: 0.22, clearcoat: 0.65 }),
  );
  footInset.position.y = -1.59;
  group.add(footInset);

  const waterVolume = mesh(new THREE.CylinderGeometry(1.42, 1.42, 2.72, segments), water, {
    cast: false,
    receive: false,
  });
  group.add(waterVolume);

  const surfaceGeometry = new THREE.CircleGeometry(1.42, segments);
  const surfaceBase = [];
  const surfacePosition = surfaceGeometry.attributes.position;
  for (let i = 0; i < surfacePosition.count; i += 1) {
    surfaceBase.push([surfacePosition.getX(i), surfacePosition.getY(i)]);
  }
  const surface = mesh(surfaceGeometry, surfaceMaterial, { cast: false, receive: false });
  surface.rotation.x = -Math.PI / 2;
  surface.renderOrder = 5;
  group.add(surface);

  const meniscus = mesh(
    new THREE.TorusGeometry(1.405, 0.025, 12, segments),
    new THREE.MeshPhysicalMaterial({
      color: 0xb8f6ff,
      emissive: 0x0a5268,
      emissiveIntensity: 0.5,
      roughness: 0.03,
      transmission: 0.55,
      transparent: true,
      opacity: 0.78,
      clearcoat: 1,
      depthWrite: false,
    }),
    { cast: false, receive: false },
  );
  meniscus.rotation.x = Math.PI / 2;
  meniscus.renderOrder = 7;
  group.add(meniscus);

  const rippleMaterial = new THREE.MeshBasicMaterial({
    color: 0xc9f7ff,
    transparent: true,
    opacity: 0.16,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const ripples = [];
  for (let i = 0; i < 4; i += 1) {
    const ripple = mesh(new THREE.TorusGeometry(0.32, 0.012, 10, 64), rippleMaterial.clone(), {
      cast: false,
      receive: false,
    });
    ripple.rotation.x = Math.PI / 2;
    ripple.userData.phase = i / 4;
    ripple.renderOrder = 8;
    group.add(ripple);
    ripples.push(ripple);
  }

  const bubbleCount = mobile ? 28 : 64;
  const bubbleGeometry = new THREE.SphereGeometry(0.035, mobile ? 10 : 14, mobile ? 7 : 10);
  const bubbles = new THREE.InstancedMesh(bubbleGeometry, bubbleMaterial, bubbleCount);
  bubbles.frustumCulled = false;
  bubbles.renderOrder = 4;
  group.add(bubbles);
  const bubbleMatrix = new THREE.Matrix4();
  const bubbleScale = new THREE.Vector3();
  const bubbleQuaternion = new THREE.Quaternion();
  const bubbleSeeds = Array.from({ length: bubbleCount }, (_, index) => ({
    angle: seeded(index, 101) * Math.PI * 2,
    radius: Math.sqrt(seeded(index, 103)) * 1.22,
    height: seeded(index, 107),
    speed: 0.025 + seeded(index, 109) * 0.045,
    size: 0.42 + seeded(index, 113) * 0.95,
    drift: seeded(index, 127) * Math.PI * 2,
  }));

  const causticMaterial = new THREE.MeshBasicMaterial({
    color: 0x62d8ff,
    transparent: true,
    opacity: 0.11,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const caustics = [];
  for (let i = 0; i < 3; i += 1) {
    const caustic = mesh(new THREE.RingGeometry(0.32 + i * 0.21, 0.39 + i * 0.23, 64), causticMaterial.clone(), {
      cast: false,
      receive: false,
    });
    caustic.rotation.x = -Math.PI / 2;
    caustic.position.y = -1.42 + i * 0.006;
    caustic.userData.phase = i * 1.8;
    group.add(caustic);
    caustics.push(caustic);
  }

  const keyCaustic = new THREE.PointLight(0x7de8ff, mobile ? 7 : 12, 7, 2);
  keyCaustic.position.set(-1.15, 0.85, 2.15);
  group.add(keyCaustic);
  const underLight = new THREE.PointLight(0x1c8cae, mobile ? 3 : 5, 4.5, 2);
  underLight.position.set(0, -1.35, 0.45);
  group.add(underLight);

  function updateSurface(time, moving) {
    const position = surface.geometry.attributes.position;
    for (let i = 0; i < position.count; i += 1) {
      const [x, y] = surfaceBase[i];
      const radius = Math.hypot(x, y) / 1.42;
      const edgeFade = Math.max(0, 1 - radius * radius);
      const wave = moving
        ? Math.sin(x * 3.1 + time * 0.0021) * 0.035 + Math.cos(y * 4.0 - time * 0.00165) * 0.022
        : 0;
      position.setZ(i, wave * edgeFade);
    }
    position.needsUpdate = true;
    surface.geometry.computeVertexNormals();
  }

  function updateBubbles(progress, time, surfaceY) {
    const waterHeight = 2.72 * Math.max(0.002, progress);
    bubbles.visible = progress > 0.035;
    if (!bubbles.visible) return;

    for (let i = 0; i < bubbleCount; i += 1) {
      const seed = bubbleSeeds[i];
      const cycle = (seed.height + time * 0.0001 * seed.speed * 60) % 1;
      const y = -1.34 + cycle * Math.max(0.08, waterHeight - 0.08);
      const safeY = Math.min(surfaceY - 0.055, y);
      const drift = reducedMotion ? 0 : Math.sin(time * 0.00085 + seed.drift) * 0.055;
      bubbleScale.setScalar(seed.size);
      bubbleMatrix.compose(
        new THREE.Vector3(
          Math.cos(seed.angle) * seed.radius + drift,
          safeY,
          Math.sin(seed.angle) * seed.radius + drift * 0.35,
        ),
        bubbleQuaternion,
        bubbleScale,
      );
      bubbles.setMatrixAt(i, bubbleMatrix);
    }
    bubbles.instanceMatrix.needsUpdate = true;
  }

  function update(progress, time) {
    const safe = Math.max(0.002, progress);
    const height = 2.72 * safe;
    const surfaceY = -1.36 + height;
    waterVolume.scale.y = safe;
    waterVolume.position.y = -1.36 + height / 2;
    waterVolume.visible = progress > 0.001;
    surface.position.y = surfaceY;
    surface.visible = progress > 0.001;
    meniscus.position.y = surfaceY + 0.012;
    meniscus.visible = progress > 0.001;

    const moving = state.running && !reducedMotion;
    updateSurface(time, moving);
    updateBubbles(progress, time, surfaceY);

    const phase = moving ? time * 0.00042 : 0;
    for (const ripple of ripples) {
      const cycle = (phase + ripple.userData.phase) % 1;
      const scale = 0.52 + cycle * 2.35;
      ripple.position.y = surfaceY + 0.03;
      ripple.scale.set(scale, scale, scale);
      ripple.material.opacity = moving ? (1 - cycle) * 0.18 : 0.025;
      ripple.visible = progress > 0.015;
    }

    for (const caustic of caustics) {
      const pulse = reducedMotion ? 0 : Math.sin(time * 0.0015 + caustic.userData.phase);
      const scale = 0.96 + pulse * 0.055;
      caustic.scale.set(scale, scale, scale);
      caustic.material.opacity = 0.07 + progress * 0.06 + pulse * 0.012;
    }

    keyCaustic.position.y = Math.max(-0.7, surfaceY + 0.38);
    keyCaustic.intensity = (mobile ? 7 : 12) * (0.62 + progress * 0.38);
    underLight.intensity = (mobile ? 3 : 5) * (0.55 + progress * 0.45);
    group.rotation.y = reducedMotion ? 0 : Math.sin(time * 0.00012) * 0.045;
  }

  return { object: group, update };
}
