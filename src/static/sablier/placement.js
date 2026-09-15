/* Où poser l'objet dans le lieu.
 *
 * Chaque univers décrit son image — ses supports, son ciel, sa fenêtre — dans le catalogue
 * (`place`). Ce fichier ne contient que des règles appliquées à cette description : aucun
 * univers n'y est nommé. Un objet posé va sur le meilleur support visible, à une taille qui
 * suit la profondeur dans des bornes lisibles ; un astre va dans le ciel, sinon dans la
 * fenêtre ; sans surface, l'objet flotte.
 *
 * Toutes les coordonnées d'image sont normalisées de 0 à 1, y compté depuis le haut. Les
 * coordonnées d'écran sont des pixels de la scène.
 */
(() => {
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const lerp = (a, b, t) => a + (b - a) * t;

  // Géométrie des objets dans leur canvas carré, en fractions de son côté : `foot` est la
  // ligne où l'objet touche son support (le centre pour un astre), `height` et `width` son
  // encombrement visible. `size` module la taille commune : des colonnes larges et basses ne
  // doivent pas occuper la hauteur d'un sablier.
  const OBJECTS = {
    hourglass: { role: "pose", foot: 0.895, height: 0.855, width: 0.57, size: 1 },
    candle: { role: "pose", foot: 0.87, height: 0.78, width: 0.59, size: 0.95 },
    wave: { role: "pose", foot: 0.796, height: 0.711, width: 1.12, size: 0.9 },
    ring: { role: "pose", foot: 0.78, height: 0.72, width: 1, size: 0.9 },
    beads: { role: "pose", foot: 0.9, height: 0.75, width: 0.9, size: 0.85 },
    bars: { role: "pose", foot: 0.755, height: 0.5, width: 1.5, size: 0.7 },
    spiral: { role: "pose", foot: 0.73, height: 0.68, width: 1, size: 0.85 },
    moon: { role: "astre", center: 0.44, height: 0.74, width: 1, size: 0.55 },
    sun: { role: "astre", center: 0.5, height: 0.8, width: 1.6, size: 0.8 },
  };

  // Taille d'un objet posé, en part de la hauteur de scène : au premier plan, puis au plus
  // loin. Bornée en pixels pour rester lisible, et en largeur pour tenir sur un téléphone.
  const SIZE = { near: 0.44, far: 0.17, min: 110, maxShare: 0.5, maxWidthShare: 0.8 };

  // Un support crédible l'emporte sur un support plus visible : on pose un sablier sur une
  // table avant de le poser par terre.
  const KIND = { table: 3, rebord: 2, sol: 1 };

  // Une zone d'interface qui commence dans ce haut de scène (statut, intention) est un
  // plafond : l'objet se raccourcit sous elle au lieu de l'éviter par le côté.
  const CEILING = 0.15;

  // L'ombre dit sur quoi l'objet repose : nette sur le bois, large et douce sur la neige.
  const SHADOW = {
    bois: { opacity: 0.5, spread: 1, softness: 0.35 },
    pierre: { opacity: 0.48, spread: 1, softness: 0.35 },
    "métal": { opacity: 0.45, spread: 1, softness: 0.3 },
    herbe: { opacity: 0.4, spread: 1.1, softness: 0.55 },
    sable: { opacity: 0.36, spread: 1.3, softness: 0.7 },
    neige: { opacity: 0.32, spread: 1.4, softness: 0.8 },
    "mouillé": { opacity: 0.3, spread: 1.2, softness: 0.5 },
  };

  /**
   * La part de l'image visible quand elle couvre une vue sans déformation, rognée autour du
   * point focal. `zoom` et `pan` portent la respiration du cadre ; `pan[1]` monte l'image.
   */
  function frame({ imageAspect, view, focus = [0.5, 0.5], zoom = 1, pan = [0, 0] }) {
    const viewAspect = view.w / Math.max(1, view.h);
    const cover = viewAspect > imageAspect ? [1, imageAspect / viewAspect] : [viewAspect / imageAspect, 1];
    const sx = cover[0] / zoom;
    const sy = cover[1] / zoom;
    return {
      ox: clamp(focus[0] + pan[0] - sx / 2, 0, 1 - sx),
      oy: clamp(focus[1] - pan[1] - sy / 2, 0, 1 - sy),
      sx,
      sy,
    };
  }

  const toScreen = ([u, v], fr, view) => ({ x: ((u - fr.ox) / fr.sx) * view.w, y: ((v - fr.oy) / fr.sy) * view.h });
  const toImage = ({ x, y }, fr, view) => [fr.ox + (x / view.w) * fr.sx, fr.oy + (y / view.h) * fr.sy];

  const overlaps = (a, b) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;

  // La partie d'un segment d'image qui tombe dans la fenêtre visible, en paramètres 0..1.
  function clipSegment([[u0, v0], [u1, v1]], fr) {
    let t0 = 0;
    let t1 = 1;
    const limits = [
      [u0, u1 - u0, fr.ox, fr.ox + fr.sx],
      [v0, v1 - v0, fr.oy, fr.oy + fr.sy],
    ];
    for (const [start, delta, low, high] of limits) {
      if (Math.abs(delta) < 1e-9) {
        if (start < low || start > high) return null;
        continue;
      }
      let a = (low - start) / delta;
      let b = (high - start) / delta;
      if (a > b) [a, b] = [b, a];
      t0 = Math.max(t0, a);
      t1 = Math.min(t1, b);
      if (t0 >= t1) return null;
    }
    return [t0, t1];
  }

  // Une zone d'image rectangulaire, réduite à ce qui est visible, en pixels ; nulle si trop
  // peu en reste pour y loger un astre.
  function visibleArea([x0, y0, x1, y1], fr, view) {
    const top = toScreen([Math.max(x0, fr.ox), Math.max(y0, fr.oy)], fr, view);
    const bottom = toScreen([Math.min(x1, fr.ox + fr.sx), Math.min(y1, fr.oy + fr.sy)], fr, view);
    const area = { l: top.x, t: top.y, r: bottom.x, b: bottom.y };
    if (area.r - area.l < view.w * 0.12 || area.b - area.t < view.h * 0.1) return null;
    return area;
  }

  function sizeFor(object, depth, view) {
    const share = lerp(SIZE.near, SIZE.far, clamp(depth, 0, 1)) * object.size;
    const byWidth = (view.w * SIZE.maxWidthShare) / object.width;
    return clamp(Math.min(share * view.h, byWidth), Math.min(SIZE.min, byWidth), SIZE.maxShare * view.h);
  }

  function box(object, anchor, objectHeight) {
    const side = objectHeight / object.height;
    const along = object.role === "astre" ? object.center : object.foot;
    return { left: anchor.x - side / 2, top: anchor.y - along * side, size: side };
  }

  function bounds(object, anchor, objectHeight) {
    const width = objectHeight * object.width;
    const top = object.role === "astre" ? anchor.y - objectHeight / 2 : anchor.y - objectHeight;
    return { l: anchor.x - width / 2, r: anchor.x + width / 2, t: top, b: top + objectHeight };
  }

  // La plus grande hauteur, au plus `height`, à laquelle l'objet posé en `point` tient dans
  // la vue et laisse l'interface libre — nulle s'il n'y parvient même au minimum lisible.
  // L'objet cède en taille avant de renoncer au support : sur un téléphone, les sols passent
  // sous le temps et le bouton de pause, et seuls leurs bords restent libres ; un objet plus
  // petit y tient debout, là où un objet entier ne pouvait que flotter.
  function fittingHeight(object, point, height, view, ui) {
    const margin = 8;
    const floor = Math.min(SIZE.min, height);
    const ceiling = Math.max(0, ...ui.filter((zone) => zone.t <= view.h * CEILING).map((zone) => zone.b));
    let fit = Math.min(height, point.y - ceiling);
    // Assez de place de part et d'autre du pied pour la largeur de l'objet.
    const room = Math.min(point.x - margin, view.w - margin - point.x);
    fit = Math.min(fit, (room * 2) / object.width);
    for (const zone of ui) {
      if (zone.t <= view.h * CEILING) continue;
      const area = bounds(object, point, fit);
      if (!overlaps(area, zone)) continue;
      // À côté de la zone, l'objet s'amincit jusqu'à la frôler ; au-dessus ou dessous, il se
      // raccourcit ; en plein dedans, aucune taille ne le sauve.
      let side = 0;
      if (point.x <= zone.l) side = ((zone.l - point.x) * 2) / object.width;
      else if (point.x >= zone.r) side = ((point.x - zone.r) * 2) / object.width;
      const above = point.y <= zone.t ? fit : 0;
      fit = Math.max(side, above);
    }
    if (fit < floor || point.y > view.h) return 0;
    const area = bounds(object, point, fit);
    if (ui.some((zone) => overlaps(area, zone))) return 0;
    return fit;
  }

  // Où poser l'objet sur un segment d'écran. D'abord à sa taille entière, au point le plus
  // central qui l'accueille ; seulement si aucun point n'y parvient, au point qui le laisse
  // le plus grand. Rétrécir près du centre alors qu'il tenait entier un peu plus loin sur le
  // même support donnait des objets minuscules sans raison.
  // `at(t)` donne le point d'écran du segment, `heightAt(t)` la taille qu'y prend l'objet :
  // un support qui s'enfonce dans l'image rapetisse l'objet à mesure qu'il s'éloigne.
  function standingPoint(object, at, [t0, t1], heightAt, view, ui) {
    const samples = [];
    for (let i = 0; i <= 24; i += 1) {
      const t = lerp(t0, t1, i / 24);
      samples.push({ t, point: at(t) });
    }
    samples.sort((p, q) => Math.abs(p.point.x - view.w / 2) - Math.abs(q.point.x - view.w / 2));
    let largest = null;
    for (const { t, point } of samples) {
      const wanted = heightAt(t);
      const height = fittingHeight(object, point, wanted, view, ui);
      if (!height) continue;
      if (height >= wanted - 0.5) return { point, height, t };
      if (!largest || height > largest.height + 0.5) largest = { point, height, t };
    }
    return largest;
  }

  function floating(object, place, fr, view, reason) {
    const anchor = place?.float ? toScreen(place.float, fr, view) : { x: view.w / 2, y: view.h * 0.46 };
    const height = sizeFor(object, 0.35, view);
    const center = { x: clamp(anchor.x, view.w * 0.2, view.w * 0.8), y: clamp(anchor.y, view.h * 0.25, view.h * 0.7) };
    if (object.role === "astre") {
      return { role: "astre", anchor: center, objectHeight: height * 0.6, box: box(object, center, height * 0.6), shadow: null, bob: false, horizon: null, support: null, reason };
    }
    const foot = { x: center.x, y: center.y + height / 2 };
    return { role: "flotte", anchor: foot, objectHeight: height, box: box(object, foot, height), shadow: null, bob: true, horizon: null, support: null, reason };
  }

  function resolveAstre(object, place, fr, view, ui) {
    const sky = place.sky ? visibleArea(place.sky.area, fr, view) : null;
    const pane = !sky && place.window ? visibleArea(place.window, fr, view) : null;
    const zone = sky || pane;
    if (!zone) return floating(object, place, fr, view, "sans ciel ni fenêtre");
    const height = Math.min((zone.b - zone.t) * 0.7, view.h * 0.24 * object.size * 1.8, (zone.r - zone.l) * 0.7 / object.width);
    let center = { x: (zone.l + zone.r) / 2, y: (zone.t + zone.b) / 2 };
    // Un astre ne passe pas sous l'interface : on le déplace dans sa zone plutôt que de le couvrir.
    for (const zoneUi of ui) {
      const area = bounds(object, center, height);
      if (overlaps(area, zoneUi)) center = { x: center.x, y: clamp(zoneUi.b + height / 2 + 4, zone.t + height / 2, zone.b - height / 2) };
    }
    const horizon = sky && place.sky.horizon != null ? toScreen([0.5, place.sky.horizon], fr, view).y : zone.b;
    return { role: "astre", anchor: center, objectHeight: height, box: box(object, center, height), shadow: null, bob: false, horizon, support: null, reason: sky ? "ciel" : "fenêtre" };
  }

  /**
   * Le placement d'un mode dans un lieu, pour une vue et sa fenêtre d'image visible.
   * `ui` : rectangles d'écran ({l, t, r, b}) que l'objet ne doit pas couvrir.
   */
  function resolve({ place, mode, frame: fr, view, ui = [] }) {
    const object = OBJECTS[mode] || OBJECTS.hourglass;
    if (!place) return floating(object, null, fr, view, "lieu non décrit");
    if (object.role === "astre") return resolveAstre(object, place, fr, view, ui);
    if (place.type === "espace") return floating(object, place, fr, view, "espace");

    let best = null;
    for (const support of place.supports || []) {
      const clipped = clipSegment(support.line, fr);
      if (!clipped) continue;
      const [[u0, v0], [u1, v1]] = support.line;
      const at = (t) => toScreen([lerp(u0, u1, t), lerp(v0, v1, t)], fr, view);
      // Une profondeur, ou une par extrémité quand le support part du premier plan vers le fond.
      const depthAt = (t) => (Array.isArray(support.depth) ? lerp(support.depth[0], support.depth[1], t) : support.depth);
      const found = standingPoint(object, at, clipped, (t) => sizeFor(object, depthAt(t), view), view, ui);
      if (!found) continue;
      const score = (KIND[support.kind] || 0) * 10
        + (clipped[1] - clipped[0]) * 2
        + (1 - depthAt(found.t)) * 1.5
        - (Math.abs(found.point.x - view.w / 2) / view.w) * 2;
      if (!best || score > best.score) best = { support, found, score };
    }
    if (!best) return floating(object, place, fr, view, "aucun support visible");

    const { support, found } = best;
    const base = SHADOW[support.surface] || SHADOW.pierre;
    const shadow = place.type === "sous-marin" ? { ...base, opacity: base.opacity * 0.7 } : base;
    return {
      role: "pose",
      anchor: found.point,
      objectHeight: found.height,
      box: box(object, found.point, found.height),
      shadow,
      bob: false,
      horizon: null,
      support: { kind: support.kind, surface: support.surface },
      reason: support.kind,
    };
  }

  globalThis.SablierPlacement = { OBJECTS, SIZE, frame, toScreen, toImage, resolve };
  if (typeof module !== "undefined") module.exports = globalThis.SablierPlacement;
})();
