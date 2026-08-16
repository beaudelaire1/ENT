// Perles.
//
// Un mâlâ suspendu : le fil retombe sous son propre poids, les perles s'y enfilent avec
// leurs irrégularités, et la nacre renvoie le lieu. Ce qui reste à venir garde son éclat ;
// ce qui est passé s'éteint et perd sa lumière — la mesure se lit sans chiffre.
import { makePearl, makeChrome, makeSteel, seeded } from "./material-kit.js";

const COUNT_DESKTOP = 34, COUNT_MOBILE = 26;

// Courbe du collier : une chaînette légèrement ouverte, refermée par le pendentif.
function loop(THREE, count) {
  const points = [];
  for (let i = 0; i < count; i += 1) {
    const t = i / count;
    const angle = t * Math.PI * 2 - Math.PI / 2;
    // Le rayon se resserre en haut : un cercle parfait se lit comme un pictogramme.
    const radius = 1.42 + Math.sin(angle) * 0.16;
    points.push(new THREE.Vector3(
      Math.cos(angle) * radius,
      Math.sin(angle) * radius * 1.16 - 0.12,
      Math.sin(angle * 2.1) * 0.14,
    ));
  }
  return points;
}

export function makeBeadsRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const count = mobile ? COUNT_MOBILE : COUNT_DESKTOP;
  const points = loop(THREE, count);
  const curve = new THREE.CatmullRomCurve3([...points, points[0].clone()], true, "centripetal", 0.4);

  const cord = mesh(
    new THREE.TubeGeometry(curve, count * 8, 0.026, 10, true),
    new THREE.MeshPhysicalMaterial({
      color: 0x3a2b20, roughness: 0.72, metalness: 0.02, clearcoat: 0.14, sheen: 0.4,
    }),
  );
  group.add(cord);

  // Les perles sont instanciées : trente-quatre matériaux distincts coûteraient cher pour
  // une différence que seule leur couleur porte.
  // Pas de `vertexColors` : la couleur d'instance suffit, et l'activer réclamerait un
  // attribut de couleur par sommet que la géométrie n'a pas — les perles viraient au noir.
  const pearl = makePearl(THREE);
  const beads = new THREE.InstancedMesh(
    new THREE.SphereGeometry(0.2, mobile ? 28 : 44, mobile ? 20 : 30),
    pearl,
    count,
  );
  beads.castShadow = !mobile;
  beads.receiveShadow = true;
  group.add(beads);

  const chrome = makeChrome(THREE), steel = makeSteel(THREE);
  // Perles de séparation tous les quarts : les repères d'un mâlâ.
  for (let i = 0; i < count; i += Math.round(count / 4)) {
    const spacer = mesh(new THREE.TorusGeometry(0.238, 0.03, 12, 32), i % 2 === 0 ? chrome : steel);
    spacer.position.copy(points[i]);
    spacer.lookAt(points[(i + 1) % count]);
    group.add(spacer);
  }

  // Pendentif et gland, en bas, là où le fil se referme.
  const guru = mesh(new THREE.SphereGeometry(0.17, 32, 22), chrome);
  guru.scale.set(0.8, 1.2, 0.72);
  guru.position.set(0, -1.86, 0.05);
  group.add(guru);
  const cap = mesh(new THREE.ConeGeometry(0.13, 0.22, 20), steel);
  cap.position.set(0, -2.06, 0.05);
  group.add(cap);
  for (let i = 0; i < 6; i += 1) {
    const strand = mesh(
      new THREE.CylinderGeometry(0.008, 0.014, 0.62 + seeded(i, 23) * 0.22, 6),
      new THREE.MeshStandardMaterial({ color: 0x8a6f52, roughness: 0.86 }),
    );
    const angle = (i / 6) * Math.PI * 2;
    strand.position.set(Math.cos(angle) * 0.05, -2.44 - seeded(i, 29) * 0.1, 0.05 + Math.sin(angle) * 0.05);
    strand.rotation.z = Math.cos(angle) * 0.12;
    group.add(strand);
  }

  const matrix = new THREE.Matrix4();
  const quaternion = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const position = new THREE.Vector3();
  const rotations = points.map((_, i) => new THREE.Euler(
    seeded(i, 5) * Math.PI, seeded(i, 7) * Math.PI, seeded(i, 9) * Math.PI,
  ));

  const alive = new THREE.Color(0xfaf4ea);
  const warm = new THREE.Color(0xffe6bd);
  const spent = new THREE.Color(0x4a4f5a);

  function update(progress, time) {
    const remaining = progress * count;
    for (let i = 0; i < count; i += 1) {
      const fill = Math.max(0, Math.min(1, remaining - i));
      position.copy(points[i]);
      // Aucune perle n'est parfaitement ronde ni de la même taille que sa voisine.
      const size = 0.94 + seeded(i, 11) * 0.13;
      scale.set(size, size * (0.93 + seeded(i, 13) * 0.12), size * (0.95 + seeded(i, 15) * 0.09));
      quaternion.setFromEuler(rotations[i]);
      beads.setMatrixAt(i, matrix.compose(position, quaternion, scale));
      beads.setColorAt(i, fill > 0.5
        ? alive.clone().lerp(warm, 0.25)
        : spent.clone().lerp(alive, fill));
    }
    beads.instanceMatrix.needsUpdate = true;
    if (beads.instanceColor) beads.instanceColor.needsUpdate = true;

    if (!reducedMotion) {
      // Le collier oscille comme un pendule très lent, sans jamais tourner sur lui-même.
      group.rotation.z = Math.sin(time * 0.00021) * 0.03;
      group.rotation.y = Math.sin(time * 0.00013) * 0.1;
    }
  }

  update(1, 0);
  return { object: group, update };
}
