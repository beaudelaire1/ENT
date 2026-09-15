const {test} = require('node:test');
const assert = require('node:assert/strict');
const placement = require('../src/static/sablier/placement.js');

const desktop = {w: 1280, h: 800};
const phone = {w: 375, h: 812};
const overlaps = (a, b) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
const objectBounds = (result, mode) => {
  const object = placement.OBJECTS[mode];
  const width = result.objectHeight * object.width;
  return {l: result.anchor.x - width / 2, r: result.anchor.x + width / 2, t: result.anchor.y - result.objectHeight, b: result.anchor.y};
};

// La formule d'origine de `photoBackdrop` (premium3d/photo-world.js), en coordonnées de texture.
function legacyOrigin({imageAspect, view, focus, zoom, pan}) {
  const viewAspect = view.w / view.h;
  const cover = viewAspect > imageAspect ? [1, imageAspect / viewAspect] : [viewAspect / imageAspect, 1];
  const sx = cover[0] / zoom, sy = cover[1] / zoom;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  return {x: clamp(focus[0] + pan[0] - sx / 2, 0, 1 - sx), y: clamp(1 - focus[1] + pan[1] - sy / 2, 0, 1 - sy), sx, sy};
}

test('la fenêtre visible est celle que la scène affiche', () => {
  for (const view of [desktop, phone, {w: 1920, h: 700}]) {
    for (const focus of [[0.5, 0.5], [0.2, 0.8], [0.9, 0.1]]) {
      for (const [zoom, pan] of [[1, [0, 0]], [1.05, [0.01, -0.006]]]) {
        const input = {imageAspect: 16 / 9, view, focus, zoom, pan};
        const fr = placement.frame(input);
        const old = legacyOrigin(input);
        assert.ok(Math.abs(fr.ox - old.x) < 1e-9);
        // Haut de la fenêtre en image = 1 − origine en texture − hauteur.
        assert.ok(Math.abs(fr.oy - (1 - old.y - old.sy)) < 1e-9);
      }
    }
  }
});

const terrace = {
  type: 'exterieur',
  supports: [
    {kind: 'sol', surface: 'pierre', line: [[0.1, 0.92], [0.9, 0.92]], depth: 0.1},
    {kind: 'table', surface: 'bois', line: [[0.3, 0.7], [0.6, 0.7]], depth: 0.3},
  ],
  sky: {horizon: 0.45, area: [0, 0, 1, 0.4]},
};

test('un objet posé choisit la table plutôt que le sol', () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: desktop, focus: [0.5, 0.5]});
  const result = placement.resolve({place: terrace, mode: 'hourglass', frame: fr, view: desktop});
  assert.equal(result.role, 'pose');
  assert.equal(result.support.kind, 'table');
  // Le pied est sur la ligne du plateau.
  assert.ok(Math.abs(result.anchor.y - placement.toScreen([0.5, 0.7], fr, desktop).y) < 1);
  assert.equal(result.shadow.opacity, 0.5);
});

test('sur téléphone, un support hors du cadre est écarté', () => {
  const place = {type: 'exterieur', supports: [
    {kind: 'table', surface: 'bois', line: [[0.05, 0.75], [0.15, 0.75]], depth: 0.2},
    {kind: 'sol', surface: 'herbe', line: [[0.3, 0.9], [0.7, 0.9]], depth: 0.2},
  ]};
  const fr = placement.frame({imageAspect: 16 / 9, view: phone, focus: [0.5, 0.5]});
  const result = placement.resolve({place, mode: 'candle', frame: fr, view: phone});
  assert.equal(result.support.kind, 'sol');
  assert.ok(result.anchor.x > 0 && result.anchor.x < phone.w);
});

test("l'objet ne couvre ni le temps ni le bouton de pause", () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: desktop, focus: [0.5, 0.5]});
  const ui = [{l: 540, t: 640, r: 740, b: 800}];
  const place = {type: 'exterieur', supports: [{kind: 'sol', surface: 'sable', line: [[0.2, 0.9], [0.8, 0.9]], depth: 0.2}]};
  const result = placement.resolve({place, mode: 'hourglass', frame: fr, view: desktop, ui});
  assert.equal(result.role, 'pose');
  assert.ok(!overlaps(objectBounds(result, 'hourglass'), ui[0]));
});

test("sur un téléphone, l'objet rétrécit pour tenir à côté du temps plutôt que de flotter", () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: phone, focus: [0.5, 0.5]});
  // Un sol bas qui traverse toute la bande visible, donc sous le bloc du temps et de la pause.
  const ui = [{l: 111, t: 686, r: 280, b: 834}];
  const place = {type: 'exterieur', supports: [{kind: 'sol', surface: 'neige', line: [[0.1, 0.9], [0.9, 0.9]], depth: 0.3}]};
  const result = placement.resolve({place, mode: 'hourglass', frame: fr, view: phone, ui});
  assert.equal(result.role, 'pose');
  const area = objectBounds(result, 'hourglass');
  assert.ok(!overlaps(area, ui[0]));
  assert.ok(area.l >= 8 && area.r <= phone.w - 8);
  assert.ok(result.objectHeight >= placement.SIZE.min);
});

test("l'objet se déplace sur son support pour garder sa taille avant de rétrécir", () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: desktop, focus: [0.5, 0.5]});
  // Le temps occupe le bas du centre ; le sol s'étend assez loin pour poser l'objet entier à côté.
  const ui = [{l: 520, t: 620, r: 760, b: 790}];
  const support = {kind: 'sol', surface: 'herbe', line: [[0.1, 0.94], [0.9, 0.94]], depth: 0.15};
  const free = placement.resolve({place: {type: 'exterieur', supports: [support]}, mode: 'hourglass', frame: fr, view: desktop});
  const beside = placement.resolve({place: {type: 'exterieur', supports: [support]}, mode: 'hourglass', frame: fr, view: desktop, ui});
  assert.ok(Math.abs(beside.objectHeight - free.objectHeight) < 1);
  assert.ok(!overlaps(objectBounds(beside, 'hourglass'), ui[0]));
});

test("sur un support qui s'enfonce dans l'image, l'objet rapetisse avec la distance", () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: desktop, focus: [0.5, 0.5]});
  const resolveAt = (depth) => placement.resolve({
    place: {type: 'exterieur', supports: [{kind: 'sol', surface: 'pierre', line: [[0.1, 0.9], [0.9, 0.9]], depth}]},
    mode: 'hourglass', frame: fr, view: desktop,
  });
  // Au centre du segment, une profondeur de 0,9 à 0 vaut une profondeur uniforme de 0,45.
  const sloped = resolveAt([0.9, 0]);
  const even = resolveAt(0.45);
  assert.ok(Math.abs(sloped.anchor.x - even.anchor.x) < 40);
  const expected = placement.resolve({
    place: {type: 'exterieur', supports: [{kind: 'sol', surface: 'pierre', line: [[0.1, 0.9], [0.9, 0.9]], depth: [0.9, 0].reduce((a, b) => a + (b - a) * ((placement.toImage(sloped.anchor, fr, desktop)[0] - 0.1) / 0.8))}]},
    mode: 'hourglass', frame: fr, view: desktop,
  });
  assert.ok(Math.abs(sloped.objectHeight - expected.objectHeight) < 2);
});

test('la taille suit la profondeur, dans ses bornes', () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: desktop, focus: [0.5, 0.5]});
  const at = (depth) => placement.resolve({
    place: {type: 'exterieur', supports: [{kind: 'sol', surface: 'herbe', line: [[0.2, 0.95], [0.8, 0.95]], depth}]},
    mode: 'hourglass', frame: fr, view: desktop,
  }).objectHeight;
  assert.ok(at(0) > at(1));
  for (const depth of [0, 0.5, 1]) {
    assert.ok(at(depth) >= placement.SIZE.min);
    assert.ok(at(depth) <= placement.SIZE.maxShare * desktop.h);
  }
});

test('un astre va au ciel, sinon à la fenêtre, sinon il flotte', () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: desktop, focus: [0.5, 0.5]});
  assert.equal(placement.resolve({place: terrace, mode: 'moon', frame: fr, view: desktop}).reason, 'ciel');
  const room = {type: 'interieur', supports: [], window: [0.5, 0.1, 0.9, 0.6]};
  assert.equal(placement.resolve({place: room, mode: 'sun', frame: fr, view: desktop}).reason, 'fenêtre');
  const closed = {type: 'interieur', supports: []};
  const lost = placement.resolve({place: closed, mode: 'moon', frame: fr, view: desktop});
  assert.equal(lost.reason, 'sans ciel ni fenêtre');
  // Le soleil se couche sur l'horizon de l'image, pas sur un horizon inventé.
  const sun = placement.resolve({place: terrace, mode: 'sun', frame: fr, view: desktop});
  assert.ok(Math.abs(sun.horizon - placement.toScreen([0.5, 0.45], fr, desktop).y) < 1);
});

test("dans l'espace, ou sans support visible, l'objet flotte sans ombre", () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: desktop, focus: [0.5, 0.5]});
  const space = placement.resolve({place: {type: 'espace', supports: terrace.supports}, mode: 'beads', frame: fr, view: desktop});
  assert.equal(space.role, 'flotte');
  assert.equal(space.shadow, null);
  assert.equal(space.bob, true);
  const bare = placement.resolve({place: {type: 'exterieur', supports: []}, mode: 'hourglass', frame: fr, view: desktop});
  assert.equal(bare.role, 'flotte');
});

test('le cadre de dessin met le pied de l’objet sur son point d’appui', () => {
  const fr = placement.frame({imageAspect: 16 / 9, view: desktop, focus: [0.5, 0.5]});
  for (const mode of ['hourglass', 'candle', 'wave', 'ring', 'beads', 'bars', 'spiral']) {
    const result = placement.resolve({place: terrace, mode, frame: fr, view: desktop});
    const object = placement.OBJECTS[mode];
    assert.ok(Math.abs(result.box.top + object.foot * result.box.size - result.anchor.y) < 1e-6, mode);
    assert.ok(Math.abs(result.box.left + result.box.size / 2 - result.anchor.x) < 1e-6, mode);
  }
});
