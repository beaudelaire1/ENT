import { makeChrome, makeSteel } from "./material-kit.js";

function arcCurve(THREE, radius, fraction) {
  class RingArc extends THREE.Curve {
    constructor() {
      super();
      this.radius = radius;
      this.fraction = fraction;
    }

    getPoint(t, target = new THREE.Vector3()) {
      const angle = -Math.PI / 2 + Math.PI * 2 * this.fraction * t;
      return target.set(Math.cos(angle) * this.radius, Math.sin(angle) * this.radius, 0.16);
    }
  }
  return new RingArc();
}

export function makeRingRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const segments = mobile ? 64 : 96;
  const chrome = makeChrome(THREE);
  const steel = makeSteel(THREE);
  const graphite = new THREE.MeshPhysicalMaterial({
    color: 0x11151b,
    metalness: 0.78,
    roughness: 0.28,
    clearcoat: 0.72,
    clearcoatRoughness: 0.12,
  });
  const glass = new THREE.MeshPhysicalMaterial({
    color: 0xeaf4ff,
    roughness: 0.055,
    transmission: 0.82,
    thickness: 0.32,
    ior: 1.46,
    transparent: true,
    opacity: 0.42,
    clearcoat: 1,
    clearcoatRoughness: 0.03,
    depthWrite: false,
  });
  const luminous = new THREE.MeshPhysicalMaterial({
    color: 0xffd89a,
    emissive: 0x6f2c06,
    emissiveIntensity: 1.2,
    metalness: 0.42,
    roughness: 0.18,
    clearcoat: 1,
    clearcoatRoughness: 0.04,
  });

  const backplate = mesh(new THREE.CylinderGeometry(1.93, 1.93, 0.16, segments), graphite);
  backplate.rotation.x = Math.PI / 2;
  backplate.position.z = -0.16;
  group.add(backplate);

  const outerBezel = mesh(new THREE.TorusGeometry(1.83, 0.12, 20, segments), chrome);
  outerBezel.position.z = 0.01;
  group.add(outerBezel);

  const track = mesh(new THREE.TorusGeometry(1.49, 0.115, 18, segments), steel);
  track.position.z = 0.07;
  group.add(track);

  const innerBezel = mesh(new THREE.TorusGeometry(1.18, 0.035, 14, segments), chrome);
  innerBezel.position.z = 0.1;
  group.add(innerBezel);

  const crystal = mesh(new THREE.CircleGeometry(1.16, segments), glass, { cast: false, receive: false });
  crystal.position.z = 0.13;
  crystal.renderOrder = 5;
  group.add(crystal);

  const tickMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xdfe5ec,
    metalness: 0.88,
    roughness: 0.2,
    clearcoat: 0.65,
  });
  const tickCount = mobile ? 30 : 60;
  for (let i = 0; i < tickCount; i += 1) {
    const angle = -Math.PI / 2 + (i / tickCount) * Math.PI * 2;
    const major = i % 5 === 0;
    const tick = mesh(
      new THREE.BoxGeometry(major ? 0.045 : 0.025, major ? 0.18 : 0.1, 0.035),
      tickMaterial,
      { cast: false, receive: false },
    );
    const radius = major ? 1.18 : 1.21;
    tick.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius, 0.19);
    tick.rotation.z = angle + Math.PI / 2;
    group.add(tick);
  }

  const active = mesh(new THREE.TubeGeometry(arcCurve(THREE, 1.49, 1), segments, 0.07, 12, false), luminous);
  active.position.z = 0.08;
  group.add(active);

  const head = mesh(new THREE.SphereGeometry(0.115, 24, 18), luminous);
  head.position.z = 0.24;
  group.add(head);

  const glow = new THREE.PointLight(0xffb65d, mobile ? 5 : 8, 4.5, 2);
  glow.position.set(0, 1.3, 1.5);
  group.add(glow);

  let lastGeometryProgress = 1;
  function updateArc(progress) {
    if (progress <= 0.002) {
      active.visible = false;
      head.visible = false;
      return;
    }
    active.visible = true;
    head.visible = true;
    if (Math.abs(progress - lastGeometryProgress) > 1 / 240) {
      const old = active.geometry;
      active.geometry = new THREE.TubeGeometry(
        arcCurve(THREE, 1.49, Math.max(0.002, progress)),
        Math.max(8, Math.round(segments * progress)),
        0.07,
        12,
        false,
      );
      old.dispose();
      lastGeometryProgress = progress;
    }
    const angle = -Math.PI / 2 + Math.PI * 2 * progress;
    head.position.set(Math.cos(angle) * 1.49, Math.sin(angle) * 1.49, 0.24);
    glow.position.set(Math.cos(angle) * 1.25, Math.sin(angle) * 1.25, 1.35);
  }

  function update(progress, time) {
    updateArc(progress);
    if (!reducedMotion) {
      group.rotation.y = Math.sin(time * 0.00016) * 0.055;
      group.rotation.x = -0.035 + Math.sin(time * 0.0001) * 0.018;
      luminous.emissiveIntensity = 1.08 + Math.sin(time * 0.0022) * 0.08;
    }
  }

  return { object: group, update };
}
