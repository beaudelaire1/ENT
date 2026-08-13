// Moteur d'univers de Sablier.
//
// Contrat artistique : un univers est un lieu, pas un filtre de couleur. Chaque monde
// possède sa propre composition, sa source lumineuse, ses plans de profondeur et son
// vocabulaire de mouvement. Le niveau « Statique » conserve le lieu entier et arrête
// uniquement ses mouvements.
//
// Contrat audio : ce fichier ne lit, ne choisit et ne modifie aucun son. La playlist
// personnelle reste exclusivement gérée par sablier.js et par l'utilisateur.
(function (global) {
  "use strict";

  const TAU = Math.PI * 2;
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const hash = (value, salt = 0) => {
    const raw = Math.sin(value * 12.9898 + salt * 78.233) * 43758.5453;
    return raw - Math.floor(raw);
  };

  function rgb(color) {
    const match = /^#([0-9a-f]{6})$/i.exec(color || "");
    if (!match) return null;
    const value = Number.parseInt(match[1], 16);
    return [value >> 16, (value >> 8) & 255, value & 255];
  }

  function rgba(color, alpha) {
    const parts = rgb(color);
    return parts ? `rgba(${parts[0]},${parts[1]},${parts[2]},${alpha})` : color;
  }

  function mix(a, b, ratio) {
    const aa = rgb(a), bb = rgb(b);
    if (!aa || !bb) return a;
    const t = clamp(ratio, 0, 1);
    const values = aa.map((value, index) => Math.round(value + (bb[index] - value) * t));
    return `#${values.map(value => value.toString(16).padStart(2, "0")).join("")}`;
  }

  function fillSky(ctx, w, h, palette, top = palette.sky, horizon = palette.horizon, bottom = palette.ground) {
    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    gradient.addColorStop(0, top);
    gradient.addColorStop(0.58, horizon);
    gradient.addColorStop(1, bottom);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, w, h);
  }

  function glow(ctx, x, y, radius, color, alpha) {
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, rgba(color, alpha));
    gradient.addColorStop(0.38, rgba(color, alpha * 0.42));
    gradient.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, TAU);
    ctx.fill();
  }

  function stars(ctx, w, h, count, color, alpha = 0.7, salt = 0, ceiling = 0.72) {
    for (let i = 0; i < count; i++) {
      const x = hash(i, 11 + salt) * w;
      const y = hash(i, 29 + salt) * h * ceiling;
      const r = 0.45 + hash(i, 47 + salt) * 1.35;
      ctx.globalAlpha = alpha * (0.3 + hash(i, 61 + salt) * 0.7);
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, TAU);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function mountain(ctx, w, h, base, amplitude, color, alpha, salt = 0, step = 0.07) {
    ctx.globalAlpha = alpha;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(0, base);
    let index = 0;
    for (let x = 0; x <= w + w * step; x += Math.max(16, w * step)) {
      const ridge = hash(index++, 91 + salt);
      const y = base - amplitude * (0.28 + ridge * 0.72);
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function cloud(ctx, x, y, width, height, color, alpha) {
    ctx.fillStyle = rgba(color, alpha);
    for (const [dx, dy, rx, ry] of [
      [-0.28, 0.05, 0.28, 0.35], [0, -0.06, 0.34, 0.48], [0.28, 0.06, 0.3, 0.34], [0.05, 0.16, 0.52, 0.26],
    ]) {
      ctx.beginPath();
      ctx.ellipse(x + width * dx, y + height * dy, width * rx, height * ry, 0, 0, TAU);
      ctx.fill();
    }
  }

  function waterShimmer(ctx, w, h, y0, color, strength, now = 0, widthScale = 1) {
    ctx.lineCap = "round";
    for (let i = 0; i < 18; i++) {
      const y = y0 + (i / 18) * (h - y0);
      const phase = now / 1100 + i * 0.63;
      const half = w * (0.035 + i * 0.012) * widthScale;
      const x = w * 0.5 + Math.sin(phase) * w * 0.025;
      ctx.globalAlpha = strength * (0.25 + (i % 4) * 0.11);
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.8 + (i % 3) * 0.45;
      ctx.beginPath();
      ctx.moveTo(x - half, y);
      ctx.lineTo(x + half, y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  function vignette(ctx, w, h, color, alpha = 0.38) {
    const gradient = ctx.createRadialGradient(w * 0.5, h * 0.47, Math.min(w, h) * 0.18, w * 0.5, h * 0.5, Math.max(w, h) * 0.72);
    gradient.addColorStop(0, rgba(color, 0));
    gradient.addColorStop(1, rgba(color, alpha));
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, w, h);
  }

  function drawTree(ctx, x, ground, height, trunkColor, canopyColor, light, detail, salt = 0) {
    const width = height * 0.58;
    ctx.lineCap = "round";
    ctx.strokeStyle = trunkColor;
    ctx.lineWidth = Math.max(8, height * 0.085);
    ctx.beginPath();
    ctx.moveTo(x, ground);
    ctx.bezierCurveTo(x - width * 0.08, ground - height * 0.28, x + width * 0.08, ground - height * 0.48, x, ground - height * 0.7);
    ctx.stroke();
    for (let i = 0; i < 9; i++) {
      const side = i % 2 ? 1 : -1;
      const startY = ground - height * (0.4 + (i % 4) * 0.07);
      const endX = x + side * width * (0.18 + hash(i, 13 + salt) * 0.38);
      const endY = ground - height * (0.66 + hash(i, 21 + salt) * 0.22);
      ctx.lineWidth = Math.max(3, height * (0.035 - (i % 3) * 0.005));
      ctx.beginPath();
      ctx.moveTo(x + side * width * 0.04, startY);
      ctx.quadraticCurveTo(x + side * width * 0.2, startY - height * 0.08, endX, endY);
      ctx.stroke();
    }
    const clusters = Math.round(23 * detail);
    for (let i = 0; i < clusters; i++) {
      const angle = hash(i, 31 + salt) * TAU;
      const radial = Math.sqrt(hash(i, 37 + salt));
      const cx = x + Math.cos(angle) * width * 0.52 * radial;
      const cy = ground - height * 0.75 + Math.sin(angle) * height * 0.22 * radial;
      const r = height * (0.07 + hash(i, 43 + salt) * 0.08);
      ctx.fillStyle = mix(canopyColor, light, 0.05 + hash(i, 57 + salt) * 0.12);
      ctx.globalAlpha = 0.78 + hash(i, 63 + salt) * 0.2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, TAU);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function drawTower(ctx, x, base, width, height, stone, light, alpha = 1) {
    ctx.globalAlpha = alpha;
    const body = ctx.createLinearGradient(x, 0, x + width, 0);
    body.addColorStop(0, mix(stone, "#000000", 0.28));
    body.addColorStop(0.46, stone);
    body.addColorStop(1, mix(stone, light, 0.16));
    ctx.fillStyle = body;
    ctx.fillRect(x, base - height, width, height);
    ctx.fillStyle = mix(stone, "#ffffff", 0.12);
    ctx.fillRect(x - width * 0.08, base - height, width * 1.16, height * 0.08);
    const rows = Math.max(2, Math.floor(height / 62));
    for (let row = 0; row < rows; row++) {
      const y = base - height * 0.78 + row * (height * 0.58 / Math.max(1, rows - 1));
      ctx.fillStyle = rgba(light, 0.13);
      ctx.beginPath();
      ctx.roundRect(x + width * 0.28, y, width * 0.44, height * 0.08, width * 0.16);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function palm(ctx, x, ground, height, color, light, lean = 0) {
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(3, height * 0.045);
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(x, ground);
    ctx.quadraticCurveTo(x + lean * height * 0.12, ground - height * 0.5, x + lean * height * 0.18, ground - height);
    ctx.stroke();
    const crownX = x + lean * height * 0.18, crownY = ground - height;
    for (let i = 0; i < 9; i++) {
      const a = -Math.PI * 0.95 + i * Math.PI * 0.24;
      const len = height * (0.34 + (i % 3) * 0.035);
      ctx.strokeStyle = i % 2 ? color : mix(color, light, 0.18);
      ctx.lineWidth = Math.max(1.4, height * 0.018);
      ctx.beginPath();
      ctx.moveTo(crownX, crownY);
      ctx.quadraticCurveTo(crownX + Math.cos(a) * len * 0.65, crownY + Math.sin(a) * len * 0.3, crownX + Math.cos(a) * len, crownY + Math.sin(a) * len);
      ctx.stroke();
    }
  }

  function worldProgress() {
    const node = document.querySelector("#digital-progress");
    const value = Number.parseFloat(node?.style.getPropertyValue("--progress") || "");
    return Number.isFinite(value) ? clamp(value, 0, 1) : 1;
  }

  // ---------------------------------------------------------------- Arbre des étoiles
  function starTreeStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, mix(p.sky, "#00101c", 0.2), p.horizon, p.ground);
    stars(ctx, w, h, Math.round(105 * detail), "#d9f4ff", 0.78, 4, 0.72);
    glow(ctx, w * 0.5, h * 0.4, Math.min(w, h) * 0.42, p.light, 0.16);
    const waterY = h * 0.69;
    const water = ctx.createLinearGradient(0, waterY, 0, h);
    water.addColorStop(0, mix(p.horizon, "#061c26", 0.45));
    water.addColorStop(1, "#02070c");
    ctx.fillStyle = water;
    ctx.fillRect(0, waterY, w, h - waterY);
    ctx.fillStyle = "#070c0e";
    ctx.beginPath();
    ctx.ellipse(w * 0.5, h * 0.67, w * 0.22, h * 0.065, 0, 0, TAU);
    ctx.fill();
    drawTree(ctx, w * 0.5, h * 0.66, h * 0.62, "#3a261d", "#0a2927", p.light, detail, 8);
    const reflection = ctx.createLinearGradient(0, waterY, 0, h);
    reflection.addColorStop(0, rgba(p.light, 0.24));
    reflection.addColorStop(1, rgba(p.light, 0));
    ctx.fillStyle = reflection;
    ctx.beginPath();
    ctx.moveTo(w * 0.46, waterY); ctx.lineTo(w * 0.54, waterY); ctx.lineTo(w * 0.61, h); ctx.lineTo(w * 0.39, h); ctx.closePath(); ctx.fill();
    vignette(ctx, w, h, "#00060b", 0.5);
  }

  function starTreeMotion(ctx, w, h, p, amount, now, progress) {
    const waterY = h * 0.69;
    waterShimmer(ctx, w, h, waterY + 5, p.light, 0.16 * amount, now, 1.45);
    const elapsed = 1 - progress;
    for (let i = 0; i < 24; i++) {
      const angle = hash(i, 211) * TAU;
      const radial = Math.sqrt(hash(i, 217));
      const x = w * 0.5 + Math.cos(angle) * w * 0.17 * radial;
      const y = h * 0.2 + Math.sin(angle) * h * 0.17 * radial;
      const pulse = 0.5 + 0.5 * Math.sin(now / (520 + i * 17) + i);
      ctx.globalAlpha = amount * (0.05 + pulse * 0.2);
      ctx.fillStyle = p.light;
      ctx.beginPath(); ctx.arc(x, y, 0.8 + pulse * 1.6, 0, TAU); ctx.fill();
    }
    const cycle = now % 19000;
    if (cycle < 620 && amount > 0.55) {
      const t = cycle / 620;
      ctx.globalAlpha = amount * (1 - t) * 0.5;
      ctx.strokeStyle = "#e8fbff";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(w * (0.08 + t * 0.35), h * (0.13 + t * 0.08));
      ctx.lineTo(w * (0.18 + t * 0.35), h * (0.1 + t * 0.08));
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    if (elapsed > 0) {
      ctx.fillStyle = rgba("#00040a", elapsed * 0.08 * amount);
      ctx.fillRect(0, 0, w, h * 0.68);
    }
  }

  // ---------------------------------------------------------- Fontaine de l'Éternité
  function fountainStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, p.sky, mix(p.horizon, "#87ced4", 0.08), p.ground);
    cloud(ctx, w * 0.45, h * 0.16, w * 0.2, h * 0.12, "#c5e1e6", 0.08);
    mountain(ctx, w, h, h * 0.55, h * 0.35, "#102f3a", 0.7, 2, 0.11);
    const stone = "#263b3f";
    drawTower(ctx, w * 0.04, h * 0.73, w * 0.14, h * 0.48, stone, p.light, 0.95);
    drawTower(ctx, w * 0.18, h * 0.68, w * 0.1, h * 0.34, stone, p.light, 0.86);
    drawTower(ctx, w * 0.76, h * 0.71, w * 0.16, h * 0.44, stone, p.light, 0.94);
    drawTower(ctx, w * 0.64, h * 0.64, w * 0.09, h * 0.3, stone, p.light, 0.78);
    ctx.fillStyle = "#183035";
    ctx.fillRect(0, h * 0.68, w, h * 0.12);
    const canal = ctx.createLinearGradient(0, h * 0.58, 0, h);
    canal.addColorStop(0, "#2d8f98"); canal.addColorStop(0.45, "#12606d"); canal.addColorStop(1, "#06161d");
    ctx.fillStyle = canal;
    ctx.beginPath();
    ctx.moveTo(w * 0.44, h * 0.55); ctx.lineTo(w * 0.56, h * 0.55); ctx.lineTo(w * 0.82, h); ctx.lineTo(w * 0.18, h); ctx.closePath(); ctx.fill();
    const falls = [[0.16, 0.44, 0.026, 0.27], [0.31, 0.52, 0.018, 0.2], [0.72, 0.43, 0.03, 0.3], [0.86, 0.5, 0.018, 0.2]];
    for (const [x, y, width, len] of falls.slice(0, Math.max(2, Math.round(falls.length * detail)))) {
      const waterfall = ctx.createLinearGradient(w * x, h * y, w * (x + width), h * y);
      waterfall.addColorStop(0, rgba("#baf9f5", 0.12)); waterfall.addColorStop(0.5, rgba("#d9fffd", 0.7)); waterfall.addColorStop(1, rgba("#63ced2", 0.12));
      ctx.fillStyle = waterfall;
      ctx.fillRect(w * x, h * y, w * width, h * len);
    }
    glow(ctx, w * 0.5, h * 0.55, w * 0.22, p.light, 0.09);
    vignette(ctx, w, h, "#031015", 0.34);
  }

  function fountainMotion(ctx, w, h, p, amount, now) {
    waterShimmer(ctx, w, h, h * 0.58, "#b8ffff", 0.16 * amount, now, 0.85);
    const falls = [[0.17, 0.68], [0.31, 0.7], [0.73, 0.72], [0.87, 0.7]];
    for (let i = 0; i < Math.round(18 * amount); i++) {
      const [fx, fy] = falls[i % falls.length];
      const phase = (now / 2200 + hash(i, 301)) % 1;
      const x = w * fx + (hash(i, 307) - 0.5) * w * 0.07;
      const y = h * fy + phase * h * 0.1;
      ctx.globalAlpha = amount * (1 - phase) * 0.12;
      ctx.fillStyle = "#dffffc";
      ctx.beginPath(); ctx.arc(x, y, 3 + hash(i, 311) * 8, 0, TAU); ctx.fill();
    }
    if (amount > 0.6) {
      ctx.globalAlpha = 0.2 * amount;
      ctx.strokeStyle = "#d8eff1"; ctx.lineWidth = 1;
      for (let i = 0; i < 3; i++) {
        const x = w * (0.35 + ((now / 42000 + i * 0.2) % 1) * 0.3);
        const y = h * (0.18 + i * 0.025);
        ctx.beginPath(); ctx.moveTo(x - 6, y); ctx.quadraticCurveTo(x, y - 4, x + 6, y); ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  // --------------------------------------------------------------------------- Éden
  function edenStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, "#051814", p.horizon, "#07120d");
    glow(ctx, w * 0.57, h * 0.22, w * 0.32, p.light, 0.12);
    mountain(ctx, w, h, h * 0.63, h * 0.22, "#102d22", 0.72, 12, 0.08);
    // Terrasses du jardin.
    for (let i = 0; i < 4; i++) {
      ctx.fillStyle = mix("#102a1d", p.horizon, i * 0.045);
      ctx.beginPath();
      ctx.moveTo(0, h * (0.66 + i * 0.07));
      ctx.quadraticCurveTo(w * 0.42, h * (0.61 + i * 0.065), w, h * (0.68 + i * 0.06));
      ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath(); ctx.fill();
    }
    // Un arbre latéral encadre le monde au lieu d'en être le sujet central.
    drawTree(ctx, w * 0.12, h * 0.78, h * 0.82, "#34281a", "#123f28", p.light, detail * 0.9, 15);
    const stream = ctx.createLinearGradient(0, h * 0.55, 0, h);
    stream.addColorStop(0, "#5ab7a2"); stream.addColorStop(1, "#0a3b38");
    ctx.fillStyle = stream;
    ctx.beginPath();
    ctx.moveTo(w * 0.58, h * 0.55);
    ctx.bezierCurveTo(w * 0.47, h * 0.69, w * 0.72, h * 0.72, w * 0.42, h);
    ctx.lineTo(w * 0.66, h);
    ctx.bezierCurveTo(w * 0.78, h * 0.75, w * 0.58, h * 0.68, w * 0.63, h * 0.55);
    ctx.closePath(); ctx.fill();
    // Quelques fleurs ponctuelles, jamais un tapis de particules.
    for (let i = 0; i < Math.round(34 * detail); i++) {
      const x = w * (0.2 + hash(i, 401) * 0.72);
      const y = h * (0.68 + hash(i, 409) * 0.27);
      ctx.globalAlpha = 0.25 + hash(i, 419) * 0.38;
      ctx.fillStyle = i % 3 ? "#a9e8b5" : "#f2d79b";
      ctx.beginPath(); ctx.arc(x, y, 0.8 + hash(i, 421) * 1.6, 0, TAU); ctx.fill();
    }
    ctx.globalAlpha = 1;
    vignette(ctx, w, h, "#020905", 0.4);
  }

  function edenMotion(ctx, w, h, p, amount, now) {
    waterShimmer(ctx, w, h, h * 0.61, p.light, 0.07 * amount, now, 0.45);
    for (let i = 0; i < Math.round(18 * amount); i++) {
      const phase = now / (1800 + i * 55) + i * 2.1;
      const x = w * (0.22 + hash(i, 431) * 0.7) + Math.sin(phase) * 9;
      const y = h * (0.3 + hash(i, 433) * 0.5) + Math.cos(phase * 0.7) * 7;
      const pulse = 0.5 + Math.sin(phase * 1.4) * 0.5;
      ctx.globalAlpha = amount * (0.08 + pulse * 0.24);
      ctx.fillStyle = i % 4 ? "#d6ffb2" : p.light;
      ctx.beginPath(); ctx.arc(x, y, 1 + pulse * 1.8, 0, TAU); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // ---------------------------------------------------------------- Fleuve du Temps
  function timeRiverStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, p.sky, p.horizon, p.ground);
    stars(ctx, w, h, Math.round(44 * detail), "#dbe6ff", 0.36, 21, 0.56);
    mountain(ctx, w, h, h * 0.58, h * 0.18, "#18243b", 0.8, 22, 0.09);
    // Ruines appartenant à plusieurs époques, volontairement sans horloge littérale.
    const ruins = [[0.04, 0.68, 0.11, 0.36], [0.19, 0.66, 0.08, 0.25], [0.77, 0.69, 0.13, 0.4], [0.66, 0.65, 0.07, 0.28]];
    for (const [x, base, width, height] of ruins) {
      drawTower(ctx, w * x, h * base, w * width, h * height, "#25283a", p.light, 0.72);
    }
    const river = ctx.createLinearGradient(0, h * 0.52, 0, h);
    river.addColorStop(0, "#6da6d4"); river.addColorStop(0.45, "#314b76"); river.addColorStop(1, "#0b1528");
    ctx.fillStyle = river;
    ctx.beginPath();
    ctx.moveTo(w * 0.48, h * 0.51);
    ctx.bezierCurveTo(w * 0.7, h * 0.63, w * 0.31, h * 0.7, w * 0.18, h);
    ctx.lineTo(w * 0.82, h);
    ctx.bezierCurveTo(w * 0.67, h * 0.73, w * 0.38, h * 0.65, w * 0.54, h * 0.51);
    ctx.closePath(); ctx.fill();
    for (let i = 0; i < Math.round(11 * detail); i++) {
      const x = w * (0.28 + hash(i, 501) * 0.46);
      const y = h * (0.28 + hash(i, 503) * 0.5);
      const size = 5 + hash(i, 509) * 16;
      ctx.globalAlpha = 0.1 + hash(i, 521) * 0.18;
      ctx.fillStyle = p.light;
      ctx.save(); ctx.translate(x, y); ctx.rotate(hash(i, 523) * 1.2 - 0.6);
      ctx.fillRect(-size * 0.5, -size * 0.08, size, size * 0.16); ctx.restore();
    }
    ctx.globalAlpha = 1;
    vignette(ctx, w, h, "#040710", 0.42);
  }

  function timeRiverMotion(ctx, w, h, p, amount, now) {
    waterShimmer(ctx, w, h, h * 0.57, p.light, 0.1 * amount, now, 0.72);
    for (let i = 0; i < Math.round(16 * amount); i++) {
      const cycle = (now / (5200 + i * 91) + hash(i, 541)) % 1;
      const x = w * (0.25 + hash(i, 547) * 0.5) + Math.sin(cycle * TAU) * 18;
      const y = h * (0.78 - cycle * 0.5);
      ctx.globalAlpha = amount * Math.sin(Math.PI * cycle) * 0.18;
      ctx.fillStyle = i % 2 ? p.light : "#a8d7ff";
      ctx.save(); ctx.translate(x, y); ctx.rotate(now / 9000 + i);
      ctx.fillRect(-6, -1, 12, 2); ctx.restore();
    }
    ctx.globalAlpha = 1;
  }

  // ---------------------------------------------------------------------- Souvenirs
  function memoriesStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, "#17121d", p.horizon, "#0e0c11");
    glow(ctx, w * 0.69, h * 0.42, w * 0.27, p.light, 0.08);
    // Sol d'un quai / d'une pièce impossible.
    ctx.fillStyle = "#131018";
    ctx.beginPath(); ctx.moveTo(0, h * 0.62); ctx.lineTo(w, h * 0.56); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath(); ctx.fill();
    // Cadres de lieux incomplets : portes, fenêtres, souvenirs sans contenu littéral.
    const frames = [[0.08, 0.23, 0.18, 0.37], [0.36, 0.17, 0.15, 0.3], [0.7, 0.2, 0.2, 0.34]];
    for (let i = 0; i < frames.length; i++) {
      const [x, y, fw, fh] = frames[i];
      ctx.globalAlpha = 0.3 + i * 0.08;
      ctx.strokeStyle = mix("#5f5267", p.light, i * 0.08);
      ctx.lineWidth = Math.max(3, w * 0.005);
      ctx.strokeRect(w * x, h * y, w * fw, h * fh);
      const pane = ctx.createLinearGradient(0, h * y, 0, h * (y + fh));
      pane.addColorStop(0, rgba(p.light, 0.09)); pane.addColorStop(1, rgba(p.horizon, 0.01));
      ctx.fillStyle = pane; ctx.fillRect(w * x, h * y, w * fw, h * fh);
    }
    ctx.globalAlpha = 1;
    // Banc et lampadaire lointain donnent une échelle humaine sans imposer un personnage.
    ctx.fillStyle = "#09080a";
    ctx.fillRect(w * 0.18, h * 0.72, w * 0.19, h * 0.025);
    ctx.fillRect(w * 0.205, h * 0.745, w * 0.018, h * 0.08);
    ctx.fillRect(w * 0.325, h * 0.745, w * 0.018, h * 0.08);
    ctx.fillRect(w * 0.84, h * 0.43, w * 0.009, h * 0.34);
    glow(ctx, w * 0.845, h * 0.42, w * 0.08, p.light, 0.14);
    // Nappes de brume au sol.
    for (let i = 0; i < Math.round(8 * detail); i++) {
      cloud(ctx, w * hash(i, 601), h * (0.72 + hash(i, 607) * 0.2), w * 0.18, h * 0.08, "#a99eb3", 0.025);
    }
    vignette(ctx, w, h, "#050407", 0.58);
  }

  function memoriesMotion(ctx, w, h, p, amount, now) {
    for (let i = 0; i < Math.round(10 * amount); i++) {
      const phase = (now / (11000 + i * 170) + hash(i, 617)) % 1;
      const alpha = Math.sin(Math.PI * phase) * amount * 0.09;
      const x = w * (0.2 + hash(i, 619) * 0.65);
      const y = h * (0.24 + hash(i, 631) * 0.5) - phase * h * 0.04;
      const width = 20 + hash(i, 641) * 42;
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = p.light;
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, width, width * 0.62);
    }
    ctx.globalAlpha = 1;
  }

  // ----------------------------------------------------------------- Interstellaire
  function interstellarStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, "#01030a", "#07122a", "#020308");
    stars(ctx, w, h, Math.round(190 * detail), "#d9e7ff", 0.72, 31, 0.88);
    // Planète géante partiellement hors cadre.
    const px = w * 0.82, py = h * 0.28, pr = Math.min(w, h) * 0.34;
    const planet = ctx.createRadialGradient(px - pr * 0.38, py - pr * 0.42, pr * 0.05, px, py, pr);
    planet.addColorStop(0, "#d8c8b7"); planet.addColorStop(0.38, "#6579a3"); planet.addColorStop(0.72, "#263456"); planet.addColorStop(1, "#060814");
    ctx.fillStyle = planet; ctx.beginPath(); ctx.arc(px, py, pr, 0, TAU); ctx.fill();
    ctx.save(); ctx.translate(px, py); ctx.rotate(-0.22);
    ctx.strokeStyle = rgba("#ccd8ef", 0.34); ctx.lineWidth = pr * 0.075;
    ctx.beginPath(); ctx.ellipse(0, 0, pr * 1.55, pr * 0.34, 0, 0, TAU); ctx.stroke();
    ctx.strokeStyle = rgba("#8ea4ce", 0.25); ctx.lineWidth = pr * 0.025;
    ctx.beginPath(); ctx.ellipse(0, 0, pr * 1.72, pr * 0.38, 0, 0, TAU); ctx.stroke(); ctx.restore();
    // Plateforme d'observation : référence humaine nette, sans transformer l'écran en cockpit.
    ctx.fillStyle = "#06080d";
    ctx.beginPath(); ctx.moveTo(0, h * 0.86); ctx.lineTo(w * 0.17, h * 0.78); ctx.lineTo(w * 0.82, h * 0.8); ctx.lineTo(w, h * 0.87); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "#273244"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(w * 0.14, h * 0.79); ctx.lineTo(w * 0.14, h * 0.7); ctx.lineTo(w * 0.72, h * 0.72); ctx.lineTo(w * 0.72, h * 0.8); ctx.stroke();
    for (let i = 0; i < 7; i++) {
      ctx.fillStyle = i % 3 === 0 ? p.light : "#5675a4";
      ctx.globalAlpha = 0.48;
      ctx.beginPath(); ctx.arc(w * (0.22 + i * 0.07), h * 0.805, 1.6, 0, TAU); ctx.fill();
    }
    ctx.globalAlpha = 1;
    vignette(ctx, w, h, "#000106", 0.48);
  }

  function interstellarMotion(ctx, w, h, p, amount, now, progress) {
    for (let i = 0; i < Math.round(55 * amount); i++) {
      const depth = 0.2 + hash(i, 701) * 0.8;
      const speed = 0.002 + depth * 0.004;
      const x = ((hash(i, 709) + now * speed / 1000) % 1) * w;
      const y = hash(i, 719) * h * 0.73;
      ctx.globalAlpha = amount * depth * 0.16;
      ctx.fillStyle = "#e5efff";
      ctx.beginPath(); ctx.arc(x, y, 0.45 + depth, 0, TAU); ctx.fill();
    }
    const elapsed = 1 - progress;
    glow(ctx, w * (0.82 - elapsed * 0.018), h * 0.28, Math.min(w, h) * 0.37, p.light, 0.025 * amount);
    ctx.globalAlpha = 1;
  }

  // ------------------------------------------------------------------------ Galaxie
  function galaxyStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, "#010108", "#09051a", "#020108");
    stars(ctx, w, h, Math.round(170 * detail), "#e9e4ff", 0.55, 41, 1);
    const cx = w * 0.5, cy = h * 0.48, radius = Math.min(w, h) * 0.42;
    glow(ctx, cx, cy, radius * 0.75, "#9c5dca", 0.16);
    for (let i = 0; i < Math.round(900 * detail); i++) {
      const arm = i % 4;
      const t = Math.pow(hash(i, 811), 0.58);
      const angle = arm * TAU / 4 + t * TAU * 1.65 + (hash(i, 821) - 0.5) * (0.55 - t * 0.34);
      const r = radius * t;
      const x = cx + Math.cos(angle) * r * 1.25;
      const y = cy + Math.sin(angle) * r * 0.52;
      const bright = 0.18 + (1 - t) * 0.42 + hash(i, 827) * 0.18;
      ctx.globalAlpha = bright;
      ctx.fillStyle = i % 7 === 0 ? "#e8b7ff" : i % 5 === 0 ? "#a6c8ff" : "#efeaff";
      ctx.beginPath(); ctx.arc(x, y, 0.35 + hash(i, 829) * 1.15, 0, TAU); ctx.fill();
    }
    ctx.globalAlpha = 1;
    glow(ctx, cx, cy, radius * 0.22, "#fff2d6", 0.55);
    vignette(ctx, w, h, "#000006", 0.38);
  }

  function galaxyMotion(ctx, w, h, p, amount, now, progress) {
    const cx = w * 0.5, cy = h * 0.48, pulse = 0.5 + 0.5 * Math.sin(now / 2100);
    glow(ctx, cx, cy, Math.min(w, h) * (0.1 + pulse * 0.025), "#fff1cf", amount * (0.07 + (1 - progress) * 0.025));
    for (let i = 0; i < Math.round(34 * amount); i++) {
      const x = hash(i, 839) * w;
      const y = hash(i, 853) * h;
      const flicker = 0.5 + 0.5 * Math.sin(now / (700 + i * 19) + i * 0.8);
      ctx.globalAlpha = amount * flicker * 0.24;
      ctx.fillStyle = "#ffffff";
      ctx.beginPath(); ctx.arc(x, y, 0.5 + flicker * 1.3, 0, TAU); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // -------------------------------------------------------------------- Hauts Cieux
  function heavenStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, "#5d92ad", "#b8dce9", "#7ca8bd");
    glow(ctx, w * 0.58, h * 0.16, w * 0.25, "#fff9dc", 0.33);
    // Mer de nuages.
    for (let i = 0; i < Math.round(16 * detail); i++) {
      cloud(ctx, w * (-0.02 + hash(i, 901) * 1.05), h * (0.62 + hash(i, 907) * 0.28), w * (0.11 + hash(i, 911) * 0.1), h * 0.12, "#ecf8fb", 0.42);
    }
    // Îles suspendues : silhouette et roche verticale, pas des collines terrestres.
    const islands = [[0.22, 0.53, 0.17], [0.56, 0.44, 0.24], [0.83, 0.6, 0.12]];
    for (let index = 0; index < islands.length; index++) {
      const [x, y, size] = islands[index];
      ctx.fillStyle = "#354c52";
      ctx.beginPath();
      ctx.ellipse(w * x, h * y, w * size, h * size * 0.28, 0, 0, TAU); ctx.fill();
      ctx.beginPath();
      ctx.moveTo(w * (x - size * 0.82), h * y);
      ctx.lineTo(w * x, h * (y + size * 0.9));
      ctx.lineTo(w * (x + size * 0.82), h * y); ctx.closePath(); ctx.fill();
      if (index === 1) {
        // Temple central.
        ctx.fillStyle = "#d4d7c9";
        ctx.fillRect(w * (x - 0.055), h * (y - 0.16), w * 0.11, h * 0.13);
        for (let col = 0; col < 5; col++) ctx.fillRect(w * (x - 0.045 + col * 0.0225), h * (y - 0.15), w * 0.008, h * 0.12);
        ctx.fillStyle = "#b8bda9";
        ctx.beginPath(); ctx.moveTo(w * (x - 0.07), h * (y - 0.16)); ctx.lineTo(w * x, h * (y - 0.23)); ctx.lineTo(w * (x + 0.07), h * (y - 0.16)); ctx.closePath(); ctx.fill();
      }
      // Cascades qui tombent dans les nuages.
      ctx.fillStyle = rgba("#e8ffff", 0.48);
      ctx.fillRect(w * (x - size * 0.08), h * (y + size * 0.08), w * size * 0.06, h * 0.28);
    }
    vignette(ctx, w, h, "#345565", 0.18);
  }

  function heavenMotion(ctx, w, h, p, amount, now, progress) {
    const elapsed = 1 - progress;
    for (let i = 0; i < Math.round(8 * amount); i++) {
      const x = ((hash(i, 919) + now / (90000 + i * 3000)) % 1.2 - 0.1) * w;
      const y = h * (0.18 + hash(i, 929) * 0.48);
      cloud(ctx, x, y, w * 0.08, h * 0.06, "#ffffff", 0.025 * amount);
    }
    ctx.globalAlpha = amount * (0.035 + elapsed * 0.025);
    ctx.fillStyle = "#fff9d9";
    ctx.beginPath(); ctx.moveTo(w * 0.46, 0); ctx.lineTo(w * 0.58, 0); ctx.lineTo(w * 0.72, h); ctx.lineTo(w * 0.55, h); ctx.closePath(); ctx.fill();
    ctx.globalAlpha = 1;
  }

  // ------------------------------------------------------------------------- Oasis
  function oasisStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, "#171329", "#9b5f4b", "#2c160f");
    glow(ctx, w * 0.73, h * 0.23, w * 0.18, p.light, 0.2);
    // Dunes en plans distincts.
    ctx.fillStyle = "#5d3320";
    ctx.beginPath(); ctx.moveTo(0, h * 0.62); ctx.quadraticCurveTo(w * 0.26, h * 0.48, w * 0.52, h * 0.65); ctx.quadraticCurveTo(w * 0.78, h * 0.48, w, h * 0.6); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#7d4728";
    ctx.beginPath(); ctx.moveTo(0, h * 0.76); ctx.quadraticCurveTo(w * 0.34, h * 0.54, w * 0.7, h * 0.75); ctx.quadraticCurveTo(w * 0.87, h * 0.65, w, h * 0.7); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath(); ctx.fill();
    // Eau de l'oasis.
    const pool = ctx.createLinearGradient(0, h * 0.72, 0, h);
    pool.addColorStop(0, "#2d8e8f"); pool.addColorStop(1, "#0b3439");
    ctx.fillStyle = pool; ctx.beginPath(); ctx.ellipse(w * 0.52, h * 0.84, w * 0.26, h * 0.11, 0, 0, TAU); ctx.fill();
    palm(ctx, w * 0.28, h * 0.81, h * 0.34, "#1b2c20", p.light, -0.3);
    palm(ctx, w * 0.34, h * 0.79, h * 0.27, "#1a2a1d", p.light, 0.25);
    palm(ctx, w * 0.75, h * 0.82, h * 0.3, "#17261c", p.light, 0.2);
    // Une arche ruinée, repère propre à cet univers.
    ctx.strokeStyle = "#38261f"; ctx.lineWidth = Math.max(9, w * 0.014);
    ctx.beginPath(); ctx.moveTo(w * 0.61, h * 0.72); ctx.lineTo(w * 0.61, h * 0.48); ctx.arc(w * 0.68, h * 0.48, w * 0.07, Math.PI, 0); ctx.lineTo(w * 0.75, h * 0.72); ctx.stroke();
    vignette(ctx, w, h, "#100907", 0.38);
  }

  function oasisMotion(ctx, w, h, p, amount, now, progress) {
    waterShimmer(ctx, w, h, h * 0.78, p.light, 0.08 * amount, now, 0.52);
    // Voiles de sable bas, différents d'une simple pluie de particules.
    for (let i = 0; i < Math.round(12 * amount); i++) {
      const x = ((hash(i, 1001) + now / (18000 + i * 470)) % 1.2 - 0.1) * w;
      const y = h * (0.58 + hash(i, 1009) * 0.3);
      ctx.globalAlpha = 0.025 * amount;
      ctx.fillStyle = "#f1bd77";
      ctx.beginPath(); ctx.ellipse(x, y, w * 0.07, h * 0.008, -0.08, 0, TAU); ctx.fill();
    }
    // Les étoiles apparaissent à mesure que la session avance : coucher de soleil lent.
    const elapsed = 1 - progress;
    if (elapsed > 0.18) stars(ctx, w, h, Math.round(54 * amount * elapsed), "#fff4dc", elapsed * 0.48, 55, 0.48);
    ctx.globalAlpha = 1;
  }

  // --------------------------------------------------------------- Sanctuaire abyssal
  function abyssStatic(ctx, w, h, p, detail) {
    const sea = ctx.createLinearGradient(0, 0, 0, h);
    sea.addColorStop(0, "#0d5a64"); sea.addColorStop(0.35, "#073941"); sea.addColorStop(1, "#020c10");
    ctx.fillStyle = sea; ctx.fillRect(0, 0, w, h);
    // Rayons de surface très hauts, donnant immédiatement la profondeur sous-marine.
    for (let i = 0; i < 5; i++) {
      const x = w * (0.14 + i * 0.18);
      const beam = ctx.createLinearGradient(0, 0, 0, h * 0.7);
      beam.addColorStop(0, rgba(p.light, 0.13)); beam.addColorStop(1, rgba(p.light, 0));
      ctx.fillStyle = beam;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + w * 0.08, 0); ctx.lineTo(x + w * 0.22, h * 0.78); ctx.lineTo(x + w * 0.12, h * 0.78); ctx.closePath(); ctx.fill();
    }
    // Temple englouti.
    ctx.fillStyle = "#0d2427";
    ctx.fillRect(w * 0.24, h * 0.58, w * 0.52, h * 0.24);
    for (let i = 0; i < 7; i++) {
      const x = w * (0.29 + i * 0.07);
      ctx.fillStyle = i % 2 ? "#173136" : "#122a2e";
      ctx.fillRect(x, h * 0.36, w * 0.035, h * 0.39);
      ctx.fillRect(x - w * 0.008, h * 0.36, w * 0.051, h * 0.035);
    }
    ctx.fillStyle = "#0b1b1e";
    ctx.beginPath(); ctx.moveTo(w * 0.2, h * 0.58); ctx.lineTo(w * 0.5, h * 0.42); ctx.lineTo(w * 0.8, h * 0.58); ctx.closePath(); ctx.fill();
    // Sol et végétation.
    ctx.fillStyle = "#061416"; ctx.fillRect(0, h * 0.78, w, h * 0.22);
    for (let i = 0; i < Math.round(28 * detail); i++) {
      const x = hash(i, 1103) * w, height = h * (0.025 + hash(i, 1109) * 0.11);
      ctx.strokeStyle = i % 3 ? "#17483e" : "#1f5c4c"; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(x, h); ctx.quadraticCurveTo(x + 8, h - height * 0.5, x + (hash(i, 1117) - 0.5) * 14, h - height); ctx.stroke();
    }
    vignette(ctx, w, h, "#010608", 0.48);
  }

  function abyssMotion(ctx, w, h, p, amount, now) {
    // Caustiques : lignes lumineuses qui glissent sur la pierre.
    ctx.strokeStyle = rgba(p.light, 0.13 * amount); ctx.lineWidth = 1;
    for (let row = 0; row < 8; row++) {
      const y = h * (0.42 + row * 0.055);
      ctx.beginPath();
      for (let x = 0; x <= w; x += 14) {
        const wave = Math.sin(x / 55 + now / 1800 + row) * 5 + Math.sin(x / 23 - now / 2600) * 2;
        x ? ctx.lineTo(x, y + wave) : ctx.moveTo(x, y + wave);
      }
      ctx.stroke();
    }
    for (let i = 0; i < Math.round(24 * amount); i++) {
      const cycle = (hash(i, 1123) + now / (9000 + i * 170)) % 1;
      const x = w * (0.08 + hash(i, 1129) * 0.84) + Math.sin(now / 1300 + i) * 5;
      const y = h * (0.92 - cycle * 0.88);
      ctx.globalAlpha = amount * (0.06 + hash(i, 1151) * 0.12);
      ctx.strokeStyle = "#b8ffff"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(x, y, 1 + hash(i, 1153) * 2.5, 0, TAU); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  // -------------------------------------------------------------- Refuge sous la pluie
  function rainRefugeStatic(ctx, w, h, p, detail) {
    // Le monde est vu depuis l'intérieur : composition volontairement opposée aux paysages.
    fillSky(ctx, w, h, p, "#101820", "#344754", "#15130f");
    // Dehors, silhouettes et lumières floues derrière la vitre.
    ctx.fillStyle = "#15242b";
    for (let i = 0; i < 9; i++) {
      const x = w * (i / 9), height = h * (0.12 + hash(i, 1201) * 0.27);
      ctx.fillRect(x, h * 0.72 - height, w * 0.13, height);
    }
    for (let i = 0; i < Math.round(24 * detail); i++) {
      const x = hash(i, 1213) * w, y = h * (0.3 + hash(i, 1217) * 0.38), r = 3 + hash(i, 1223) * 9;
      glow(ctx, x, y, r * 3.4, i % 3 ? "#d7b36c" : "#7da5c0", 0.11);
    }
    // Cadre de la grande baie vitrée.
    ctx.strokeStyle = "#080a0c"; ctx.lineWidth = Math.max(11, w * 0.014);
    ctx.strokeRect(w * 0.08, h * 0.08, w * 0.84, h * 0.72);
    ctx.lineWidth = Math.max(7, w * 0.009);
    ctx.beginPath(); ctx.moveTo(w * 0.5, h * 0.08); ctx.lineTo(w * 0.5, h * 0.8); ctx.moveTo(w * 0.08, h * 0.5); ctx.lineTo(w * 0.92, h * 0.5); ctx.stroke();
    // Intérieur : bureau et lampe chaude.
    ctx.fillStyle = "#0a0908"; ctx.fillRect(0, h * 0.8, w, h * 0.2);
    ctx.fillStyle = "#2b2118"; ctx.fillRect(w * 0.13, h * 0.78, w * 0.31, h * 0.055);
    ctx.fillRect(w * 0.16, h * 0.83, w * 0.025, h * 0.17); ctx.fillRect(w * 0.4, h * 0.83, w * 0.025, h * 0.17);
    ctx.strokeStyle = "#342719"; ctx.lineWidth = Math.max(3, w * 0.005);
    ctx.beginPath(); ctx.moveTo(w * 0.25, h * 0.78); ctx.lineTo(w * 0.25, h * 0.58); ctx.stroke();
    ctx.fillStyle = "#594128"; ctx.beginPath(); ctx.moveTo(w * 0.19, h * 0.59); ctx.lineTo(w * 0.31, h * 0.59); ctx.lineTo(w * 0.27, h * 0.5); ctx.lineTo(w * 0.23, h * 0.5); ctx.closePath(); ctx.fill();
    glow(ctx, w * 0.25, h * 0.56, w * 0.2, p.light, 0.16);
    vignette(ctx, w, h, "#050608", 0.5);
  }

  function rainRefugeMotion(ctx, w, h, p, amount, now, progress) {
    // Pluie sur la vitre : plusieurs vitesses, aucune pluie dans la pièce.
    const count = Math.round(62 * amount);
    ctx.lineCap = "round";
    for (let i = 0; i < count; i++) {
      const speed = 0.00012 + hash(i, 1231) * 0.00018;
      const y = ((hash(i, 1237) + now * speed) % 1) * h * 0.72 + h * 0.08;
      const x = w * (0.09 + hash(i, 1249) * 0.82);
      const len = 6 + hash(i, 1259) * 24;
      ctx.globalAlpha = amount * (0.05 + hash(i, 1277) * 0.14);
      ctx.strokeStyle = "#b9d7e7"; ctx.lineWidth = 0.8 + hash(i, 1283) * 0.9;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - 1.5, y + len); ctx.stroke();
    }
    const elapsed = 1 - progress;
    glow(ctx, w * 0.25, h * 0.56, w * (0.13 + elapsed * 0.035), p.light, amount * (0.025 + elapsed * 0.025));
    ctx.globalAlpha = 1;
  }

  // --------------------------------------------------------------- Vallée des aurores
  function auroraValleyStatic(ctx, w, h, p, detail) {
    fillSky(ctx, w, h, p, "#04101c", "#12384e", "#061017");
    stars(ctx, w, h, Math.round(115 * detail), "#dff8ff", 0.66, 61, 0.62);
    mountain(ctx, w, h, h * 0.64, h * 0.3, "#102536", 0.96, 63, 0.08);
    mountain(ctx, w, h, h * 0.7, h * 0.22, "#183545", 0.82, 67, 0.07);
    // Neige sur quelques crêtes, en second trait.
    ctx.strokeStyle = rgba("#cce7ea", 0.28); ctx.lineWidth = 2;
    for (let i = 0; i < 5; i++) {
      const x = w * (0.08 + i * 0.2), y = h * (0.46 + hash(i, 1301) * 0.08);
      ctx.beginPath(); ctx.moveTo(x - w * 0.05, y + h * 0.06); ctx.lineTo(x, y); ctx.lineTo(x + w * 0.05, y + h * 0.07); ctx.stroke();
    }
    const lakeY = h * 0.7;
    const lake = ctx.createLinearGradient(0, lakeY, 0, h);
    lake.addColorStop(0, "#143746"); lake.addColorStop(1, "#05131b");
    ctx.fillStyle = lake; ctx.fillRect(0, lakeY, w, h - lakeY);
    vignette(ctx, w, h, "#02070c", 0.42);
  }

  function auroraValleyMotion(ctx, w, h, p, amount, now, progress) {
    const elapsed = 1 - progress;
    const intensity = amount * (0.18 + elapsed * 0.22);
    // Voiles d'aurore : bandes courbes translucides et non simples rectangles ondulés.
    for (let band = 0; band < 4; band++) {
      const base = h * (0.12 + band * 0.075);
      const thickness = h * (0.09 + band * 0.018);
      const gradient = ctx.createLinearGradient(0, base, 0, base + thickness);
      const color = band % 2 ? "#79d7ff" : p.light;
      gradient.addColorStop(0, rgba(color, 0)); gradient.addColorStop(0.42, rgba(color, intensity * (0.4 - band * 0.05))); gradient.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = gradient;
      ctx.beginPath();
      for (let x = 0; x <= w; x += 12) {
        const y = base + Math.sin(x / (130 + band * 35) + now / (5200 + band * 700) + band) * h * (0.025 + band * 0.007);
        x ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      for (let x = w; x >= 0; x -= 12) {
        const y = base + thickness + Math.sin(x / (115 + band * 28) + now / (5900 + band * 650) + band * 1.3) * h * 0.02;
        ctx.lineTo(x, y);
      }
      ctx.closePath(); ctx.fill();
    }
    waterShimmer(ctx, w, h, h * 0.72, p.light, 0.07 * amount, now, 1.25);
    for (let i = 0; i < Math.round(20 * amount); i++) {
      const x = hash(i, 1319) * w;
      const y = ((hash(i, 1321) + now / (19000 + i * 370)) % 1) * h;
      ctx.globalAlpha = amount * 0.12;
      ctx.fillStyle = "#e8fbff";
      ctx.beginPath(); ctx.arc(x, y, 0.6 + hash(i, 1327) * 1.4, 0, TAU); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  const WORLDS = {
    star_tree: { static: starTreeStatic, motion: starTreeMotion, motionUnits: 32 },
    eternity_fountain: { static: fountainStatic, motion: fountainMotion, motionUnits: 36 },
    eden: { static: edenStatic, motion: edenMotion, motionUnits: 28 },
    time_river: { static: timeRiverStatic, motion: timeRiverMotion, motionUnits: 28 },
    memories: { static: memoriesStatic, motion: memoriesMotion, motionUnits: 18 },
    interstellar: { static: interstellarStatic, motion: interstellarMotion, motionUnits: 58 },
    galaxy: { static: galaxyStatic, motion: galaxyMotion, motionUnits: 38 },
    heaven: { static: heavenStatic, motion: heavenMotion, motionUnits: 18 },
    oasis: { static: oasisStatic, motion: oasisMotion, motionUnits: 24 },
    abyss: { static: abyssStatic, motion: abyssMotion, motionUnits: 34 },
    rain_refuge: { static: rainRefugeStatic, motion: rainRefugeMotion, motionUnits: 64 },
    aurora_valley: { static: auroraValleyStatic, motion: auroraValleyMotion, motionUnits: 28 },
  };

  // Les anciens noms restent compris le temps que les préférences enregistrées soient
  // resauvegardées. Ce n'est pas une seconde collection artistique : chaque ancien nom
  // converge vers un univers du nouveau moteur.
  const LEGACY_AMBIENCE = {
    concentration: "star_tree",
    printemps: "eden",
    ete: "oasis",
    automne: "time_river",
    hiver: "aurora_valley",
    pluie: "rain_refuge",
    ocean: "eternity_fountain",
    sahara: "oasis",
    foret: "eden",
    orage: "interstellar",
    braises: "memories",
    aurore: "heaven",
    nuit: "galaxy",
  };

  const LEGACY_DECOR = {
    motes: "star_tree", petals: "eden", fireflies: "oasis", leaves: "time_river",
    snow: "aurora_valley", rain: "rain_refuge", waves: "eternity_fountain",
    sand: "oasis", spores: "eden", storm: "interstellar", embers: "memories",
    aurora: "heaven", stars: "galaxy",
  };

  const DENSITIES = {
    0: { detail: 0.78, motion: 0 },
    1: { detail: 0.86, motion: 0.34 },
    2: { detail: 1, motion: 0.68 },
    3: { detail: 1, motion: 1 },
  };

  function create(canvas) {
    const ctx = canvas.getContext("2d");
    const app = canvas.closest(".focus-app") || document.documentElement;
    const cache = document.createElement("canvas");
    const cacheCtx = cache.getContext("2d");
    const reducedMotion = global.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches || false;
    let name = "star_tree", density = DENSITIES[2], w = 0, h = 0, dpr = 1, dirty = true, paletteKey = "";

    // Le mode screen de l'ancien moteur faisait dépendre le paysage du thème clair/sombre
    // de MyENT. Un monde possède désormais ses propres noirs, lumières et matériaux.
    canvas.style.mixBlendMode = "normal";

    function palette(accent) {
      const style = getComputedStyle(app);
      return {
        accent: accent || style.getPropertyValue("--focus-accent").trim() || "#7ad8ff",
        sky: style.getPropertyValue("--world-sky").trim() || "#020d19",
        horizon: style.getPropertyValue("--world-horizon").trim() || "#0c3d5d",
        ground: style.getPropertyValue("--world-ground").trim() || "#061017",
        light: style.getPropertyValue("--world-light").trim() || "#ffe7a0",
      };
    }

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const nextW = Math.max(1, rect.width), nextH = Math.max(1, rect.height);
      const mobile = nextW < 760;
      const nextDpr = Math.min(global.devicePixelRatio || 1, mobile ? 1.25 : 1.65);
      if (Math.abs(nextW - w) < 1 && Math.abs(nextH - h) < 1 && nextDpr === dpr) return;
      w = nextW; h = nextH; dpr = nextDpr;
      canvas.width = Math.max(1, Math.round(w * dpr));
      canvas.height = Math.max(1, Math.round(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cache.width = Math.max(1, Math.round(w * dpr));
      cache.height = Math.max(1, Math.round(h * dpr));
      cacheCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dirty = true;
    }

    function resolve(next) {
      if (WORLDS[next]) return next;
      const stored = app.dataset?.ambience;
      if (stored && LEGACY_AMBIENCE[stored]) return LEGACY_AMBIENCE[stored];
      return LEGACY_DECOR[next] || "star_tree";
    }

    function use(next, level) {
      const resolved = resolve(next);
      const profile = DENSITIES[level] || DENSITIES[2];
      if (resolved !== name || profile !== density) {
        name = resolved;
        density = profile;
        dirty = true;
      }
    }

    function renderStatic(p) {
      cacheCtx.clearRect(0, 0, w, h);
      WORLDS[name].static(cacheCtx, w, h, p, density.detail);
      dirty = false;
    }

    function frame(now, accent) {
      resize();
      const p = palette(accent);
      const nextPaletteKey = `${p.sky}|${p.horizon}|${p.ground}|${p.light}`;
      if (nextPaletteKey !== paletteKey) {
        paletteKey = nextPaletteKey;
        dirty = true;
      }
      if (dirty) renderStatic(p);
      ctx.clearRect(0, 0, w, h);
      ctx.drawImage(cache, 0, 0, cache.width, cache.height, 0, 0, w, h);
      const motion = reducedMotion ? 0 : density.motion;
      if (motion > 0) WORLDS[name].motion(ctx, w, h, p, motion, now, worldProgress());
      ctx.globalAlpha = 1;
    }

    return {
      use,
      frame,
      inspect: () => ({
        name,
        particles: Math.round(WORLDS[name].motionUnits * (reducedMotion ? 0 : density.motion)),
        scenery: density.detail,
        motion: reducedMotion ? 0 : density.motion,
      }),
    };
  }

  global.SablierDecor = {
    create,
    names: Object.keys(WORLDS),
    backdrops: Object.keys(WORLDS),
    legacy: LEGACY_AMBIENCE,
  };
})(window);
