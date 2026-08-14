import { makeChrome, makeGlass } from "./material-kit.js";

export function makeWaveRuntime(THREE, helpers, state) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const segments = mobile ? 64 : 96;
  const glass = makeGlass(THREE);
  const chrome = makeChrome(THREE);
  const water = new THREE.MeshPhysicalMaterial({
    color: 0x4aa7c4,
    roughness: 0.12,
    metalness: 0,
    transmission: 0.24,
    thickness: 0.78,
    ior: 1.333,
    transparent: true,
    opacity: 0.9,
    clearcoat: 0.75,
    clearcoatRoughness: 0.08,
    attenuationColor: new THREE.Color(0x0c607b),
    attenuationDistance: 2.8,
  });
  const surfaceMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x86d9ea,
    emissive: 0x063342,
    emissiveIntensity: 0.3,
    roughness: 0.08,
    metalness: 0,
    transmission: 0.18,
    transparent: true,
    opacity: 0.94,
    clearcoat: 1,
    clearcoatRoughness: 0.035,
    side: THREE.DoubleSide,
  });

  const vessel = mesh(
    new THREE.CylinderGeometry(1.58, 1.58, 3.05, segments, 1, true),
    glass,
    { cast: false, receive: false },
  );
  vessel.renderOrder = 4;
  group.add(vessel);

  const glassBottom = mesh(new THREE.CylinderGeometry(1.58, 1.58, 0.13, segments), glass, {
    cast: false,
    receive: false,
  });
  glassBottom.position.y = -1.52;
  glassBottom.renderOrder = 4;
  group.add(glassBottom);

  const rim = mesh(new THREE.TorusGeometry(1.58, 0.055, 18, segments), chrome);
  rim.rotation.x = Math.PI / 2;
  rim.position.y = 1.52;
  group.add(rim);

  const foot = mesh(new THREE.CylinderGeometry(1.82, 1.9, 0.16, segments), chrome);
  foot.position.y = -1.68;
  group.add(foot);

  const waterVolume = mesh(new THREE.CylinderGeometry(1.43, 1.43, 2.72, segments), water, {
    cast: false,
    receive: false,
  });
  group.add(waterVolume);

  const surface = mesh(new THREE.CircleGeometry(1.43, segments), surfaceMaterial, {
    cast: false,
    receive: false,
  });
  surface.rotation.x = -Math.PI / 2;
  surface.renderOrder = 3;
  group.add(surface);

  const rippleMaterial = new THREE.MeshBasicMaterial({
    color: 0xc9f7ff,
    transparent: true,
    opacity: 0.18,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const ripples = [];
  for (let i = 0; i < 4; i += 1) {
    const ripple = mesh(new THREE.TorusGeometry(0.34, 0.012, 10, 64), rippleMaterial.clone(), {
      cast: false,
      receive: false,
    });
    ripple.rotation.x = Math.PI / 2;
    ripple.userData.phase = i / 4;
    ripple.renderOrder = 6;
    group.add(ripple);
    ripples.push(ripple);
  }

  const caustic = new THREE.PointLight(0x78d9ef, mobile ? 7 : 11, 7, 2);
  caustic.position.set(-1.2, 0.9, 2.2);
  group.add(caustic);

  function update(progress, time) {
    const safe = Math.max(0.002, progress);
    const height = 2.72 * safe;
    const surfaceY = -1.36 + height;
    waterVolume.scale.y = safe;
    waterVolume.position.y = -1.36 + height / 2;
    waterVolume.visible = progress > 0.001;
    surface.position.y = surfaceY;
    surface.visible = progress > 0.001;

    const moving = state.running && !reducedMotion;
    const phase = moving ? time * 0.00042 : 0;
    surface.rotation.z = moving ? Math.sin(time * 0.0011) * 0.025 : 0;
    surface.scale.set(
      1 + (moving ? Math.sin(time * 0.0018) * 0.008 : 0),
      1 + (moving ? Math.cos(time * 0.0014) * 0.006 : 0),
      1,
    );

    for (const ripple of ripples) {
      const cycle = (phase + ripple.userData.phase) % 1;
      const scale = 0.55 + cycle * 2.2;
      ripple.position.y = surfaceY + 0.018;
      ripple.scale.set(scale, scale, scale);
      ripple.material.opacity = moving ? (1 - cycle) * 0.16 : 0.035;
      ripple.visible = progress > 0.015;
    }

    caustic.position.y = Math.max(-0.8, surfaceY + 0.35);
    caustic.intensity = (mobile ? 7 : 11) * (0.65 + progress * 0.35);
    group.rotation.y = reducedMotion ? 0 : Math.sin(time * 0.00012) * 0.04;
  }

  return { object: group, update };
}
