// Bougie.
//
// Une bougie n'est pas un cylindre qui rétrécit : elle se creuse. Le bord reste haut,
// la cire fond en cuvette autour de la mèche, déborde en coulures et se fige. La
// silhouette est donc tournée à partir d'un profil recalculé à chaque palier de fonte,
// comme le sable du sablier — et la flamme éclaire réellement la cire, ce qui lui donne
// sa transparence chaude.
import { makeWax, makeChrome, makeSteel, seeded } from "./material-kit.js";
import { flameSprite, radialSprite } from "./textures.js";

const BASE = -1.62;          // assise de la bougie
const FULL = 3.1;            // hauteur d'origine
const RADIUS = 0.92;

// Contour de la bougie : paroi extérieure, bord arrondi, cuvette de fonte vers la mèche.
function outline(THREE, height, melt) {
  const points = [new THREE.Vector2(0.001, BASE)];
  points.push(new THREE.Vector2(RADIUS, BASE + 0.02));
  points.push(new THREE.Vector2(RADIUS * 1.005, BASE + height * 0.5));
  const top = BASE + height;
  points.push(new THREE.Vector2(RADIUS, top - RADIUS * 0.18));
  // Le bord : une lèvre mince, plus haute que la cire fondue qu'elle retient.
  points.push(new THREE.Vector2(RADIUS * 0.97, top));
  points.push(new THREE.Vector2(RADIUS * 0.88, top - RADIUS * 0.04));
  // La cuvette, d'autant plus creusée que la flamme a brûlé longtemps.
  const bowl = RADIUS * (0.2 + melt * 0.34);
  for (let i = 1; i <= 8; i += 1) {
    const t = i / 8;
    points.push(new THREE.Vector2(
      Math.max(0.001, RADIUS * 0.88 * (1 - t)),
      top - RADIUS * 0.04 - bowl * Math.sin(t * Math.PI * 0.5),
    ));
  }
  return points;
}

export function makeCandleRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const segments = mobile ? 48 : 84;
  const wax = makeWax(THREE);

  const body = mesh(new THREE.BufferGeometry(), wax);
  group.add(body);

  // Bougeoir tourné : assiette, tige, coupelle. Le métal capte la flamme par-dessous et
  // c'est ce reflet chaud qui pose la bougie sur quelque chose.
  const chrome = makeChrome(THREE), steel = makeSteel(THREE);
  const dish = mesh(new THREE.LatheGeometry([
    [0, 0], [1.32, 0], [1.42, 0.06], [1.44, 0.14], [1.3, 0.17],
    [1.06, 0.19], [1.02, 0.3], [0.98, 0.34], [0, 0.35],
  ].map(([r, y]) => new THREE.Vector2(r, y)), segments), chrome);
  dish.position.y = BASE - 0.34;
  group.add(dish);
  const collar = mesh(new THREE.TorusGeometry(RADIUS + 0.06, 0.05, 14, segments), steel);
  collar.rotation.x = Math.PI / 2;
  collar.position.y = BASE + 0.03;
  group.add(collar);

  // Coulures : figées le long de la paroi, elles descendent avec le niveau de la cire.
  const drips = [];
  for (let i = 0; i < 5; i += 1) {
    const angle = seeded(i, 13) * Math.PI * 2;
    const drip = mesh(new THREE.CapsuleGeometry(0.05 + seeded(i, 15) * 0.03, 1, 5, 12), wax);
    drip.userData = { angle, length: 0.35 + seeded(i, 17) * 0.8, offset: seeded(i, 19) };
    group.add(drip);
    drips.push(drip);
  }

  // Mèche : le brin carbonisé, puis la braise à sa base.
  const wick = mesh(
    new THREE.CylinderGeometry(0.022, 0.032, 0.3, 10),
    new THREE.MeshStandardMaterial({ color: 0x171310, roughness: 0.96 }),
    { receive: false },
  );
  group.add(wick);
  const ember = mesh(
    new THREE.SphereGeometry(0.05, 14, 10),
    new THREE.MeshStandardMaterial({ color: 0x2a1109, emissive: 0xff5a12, emissiveIntensity: 3, roughness: 1 }),
    { cast: false, receive: false },
  );
  group.add(ember);

  // Flamme : un sprite pour le corps, un halo plus large pour la diffusion, et une
  // lumière qui vacille. Les trois ensemble ; un seul des trois se voit tout de suite.
  const flameTexture = flameSprite(THREE);
  const flame = new THREE.Sprite(new THREE.SpriteMaterial({
    map: flameTexture, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  flame.scale.set(0.62, 1.32, 1);
  group.add(flame);
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({
    map: radialSprite(THREE, [
      ["rgba(255,214,150,.55)", 0],
      ["rgba(255,150,60,.1)", 0.34],
      ["rgba(255,110,20,0)", 1],
    ]),
    transparent: true, opacity: 0.26, blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  halo.scale.set(4.6, 5, 1);
  group.add(halo);
  const light = new THREE.PointLight(0xff9c46, mobile ? 26 : 40, 9, 2);
  group.add(light);

  let builtAt = -1;
  function rebuild(height, melt) {
    body.geometry.dispose();
    body.geometry = new THREE.LatheGeometry(outline(THREE, height, melt), mobile ? 44 : 76);
    builtAt = height;
  }

  function update(progress, time) {
    const height = Math.max(0.2, FULL * progress);
    // La cuvette se creuse au début puis se stabilise : c'est le régime d'une flamme.
    const melt = Math.min(1, (1 - progress) * 2.4);
    if (Math.abs(height - builtAt) > 0.012) rebuild(height, melt);

    const top = BASE + height;
    const pool = top - RADIUS * (0.04 + (0.2 + melt * 0.34) * 0.4);
    wick.position.y = pool + 0.14;
    ember.position.y = pool + 0.27;

    for (const drip of drips) {
      const { angle, length, offset } = drip.userData;
      // Une coulure ne peut pas dépasser la cire qui l'a produite.
      const visible = Math.min(length, Math.max(0.14, (FULL - height) * 0.5 + 0.2));
      drip.scale.y = visible;
      drip.position.set(
        Math.cos(angle) * RADIUS * 0.99,
        top - RADIUS * 0.1 - visible * 0.5 - offset * 0.2,
        Math.sin(angle) * RADIUS * 0.99,
      );
      drip.visible = progress > 0.06;
    }

    const alive = progress > 0.004;
    flame.visible = halo.visible = ember.visible = alive;
    light.intensity = alive ? (mobile ? 24 : 38) : 0;
    if (alive && !reducedMotion) {
      // Vacillement : deux fréquences, sinon la flamme pulse comme un métronome.
      const flicker = Math.sin(time * 0.009) * 0.5 + Math.sin(time * 0.023) * 0.5;
      flame.position.set(
        Math.sin(time * 0.0031) * 0.022,
        pool + 0.62 + flicker * 0.03,
        Math.cos(time * 0.0027) * 0.018,
      );
      flame.scale.set(0.6 + flicker * 0.03, 1.3 + flicker * 0.1, 1);
      halo.position.copy(flame.position);
      light.position.set(flame.position.x, pool + 0.5, flame.position.z);
      light.intensity = (mobile ? 24 : 38) * (0.88 + flicker * 0.12);
      halo.material.opacity = 0.2 + flicker * 0.06;
      ember.material.emissiveIntensity = 2.6 + flicker * 0.9;
    } else if (alive) {
      flame.position.set(0, pool + 0.62, 0);
      halo.position.copy(flame.position);
      light.position.set(0, pool + 0.5, 0);
    }
  }

  rebuild(FULL, 0);
  return { object: group, update };
}
