// Lune et Soleil.
//
// Les deux astres se lisent par leur lumière : la Lune ne décroît pas, c'est le
// terminateur qui traverse son disque ; le Soleil ne rétrécit pas, il descend. Le relief
// vient d'une carte de régolithe calculée plutôt que de tores collés en surface — des
// cratères posés par-dessus une sphère lisse restent des anneaux vus de face dès qu'on
// s'écarte du centre.
import { makeRegolith, seeded } from "./material-kit.js";
import { radialSprite } from "./textures.js";

function makeMoon(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();

  const regolith = makeRegolith(THREE);
  const sphere = mesh(
    new THREE.SphereGeometry(1.55, mobile ? 72 : 128, mobile ? 48 : 84),
    regolith,
    { cast: false, receive: false },
  );
  group.add(sphere);

  // La lumière de phase appartient à l'objet : elle tourne autour de lui pendant que la
  // session s'écoule, et c'est elle seule qui dessine le croissant.
  const target = new THREE.Object3D();
  group.add(target);
  const phase = new THREE.DirectionalLight(0xfff6e4, 9.5);
  phase.target = target;
  group.add(phase);

  // Halo cendré : la part non éclairée reste faiblement visible, comme la lumière
  // cendrée d'un croissant réel.
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({
    map: radialSprite(THREE, [
      ["rgba(214,226,255,.5)", 0],
      ["rgba(180,200,255,.12)", 0.42],
      ["rgba(150,180,255,0)", 1],
    ]),
    transparent: true,
    opacity: 0.5,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }));
  halo.scale.set(6.4, 6.4, 1);
  group.add(halo);

  function update(progress, time) {
    const angle = (1 - progress) * Math.PI;
    phase.position.set(Math.sin(angle) * 6, 1.3, Math.cos(angle) * 6);
    halo.material.opacity = 0.24 + progress * 0.3;
    group.rotation.y = reducedMotion ? -0.18 : -0.18 + Math.sin(time * 0.00008) * 0.045;
    group.rotation.x = reducedMotion ? 0.03 : 0.03 + Math.sin(time * 0.00005) * 0.015;
  }

  return { object: group, update };
}

function makeSun(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();

  // Photosphère : la granulation est portée par une carte d'émission bruitée, sinon la
  // sphère est un disque orange uniforme qu'aucun éclat ne trahit.
  const surface = new THREE.MeshStandardMaterial({
    color: 0xff9422,
    emissive: 0xff5510,
    emissiveIntensity: 5.4,
    roughness: 0.7,
    metalness: 0,
  });
  const sphere = mesh(
    new THREE.SphereGeometry(1.26, mobile ? 72 : 112, mobile ? 48 : 72),
    surface,
    { cast: false, receive: false },
  );
  group.add(sphere);

  const corona = new THREE.Sprite(new THREE.SpriteMaterial({
    map: radialSprite(THREE, [
      ["rgba(255,250,220,1)", 0],
      ["rgba(255,186,66,.94)", 0.18],
      ["rgba(255,96,18,.4)", 0.5],
      ["rgba(255,60,0,0)", 1],
    ], 192),
    color: 0xffa844,
    transparent: true,
    opacity: 0.9,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }));
  corona.scale.set(6.4, 6.4, 1);
  group.add(corona);

  // Protubérances : quelques arcs fins au limbe, qui respirent lentement.
  const arcs = [];
  const arcMaterial = new THREE.MeshBasicMaterial({
    color: 0xff7a26, transparent: true, opacity: 0.3,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
  for (let i = 0; i < 5; i += 1) {
    const arc = mesh(
      new THREE.TorusGeometry(1.36 + seeded(i, 31) * 0.12, 0.035, 8, 48, 1.1 + seeded(i, 33)),
      arcMaterial,
      { cast: false, receive: false },
    );
    arc.rotation.set(seeded(i, 35) * 0.6, seeded(i, 37) * Math.PI, seeded(i, 39) * Math.PI * 2);
    group.add(arc);
    arcs.push(arc);
  }

  const light = new THREE.PointLight(0xff9b43, 42, 22, 1.35);
  group.add(light);

  function update(progress, time) {
    // La course dit l'heure : au zénith en début de session, couché à la fin.
    const angle = progress * Math.PI;
    group.position.x = Math.cos(angle) * 1.4;
    group.position.y = -0.72 + Math.sin(angle) * 1.2;
    const pulse = reducedMotion ? 1 : 1 + Math.sin(time * 0.0022) * 0.016;
    sphere.scale.setScalar(pulse);
    corona.material.opacity = reducedMotion ? 0.86 : 0.82 + Math.sin(time * 0.0017) * 0.06;
    surface.emissiveIntensity = reducedMotion ? 5.4 : 5.4 + Math.sin(time * 0.0009) * 0.5;
    for (let i = 0; i < arcs.length; i += 1) {
      arcs[i].scale.setScalar(reducedMotion ? 1 : 1 + Math.sin(time * 0.0011 + i) * 0.035);
    }
    sphere.rotation.y = reducedMotion ? 0 : time * 0.00005;
  }

  return { object: group, update };
}

export function makeCelestialRuntime(THREE, helpers) {
  return { moon: () => makeMoon(THREE, helpers), sun: () => makeSun(THREE, helpers) };
}
