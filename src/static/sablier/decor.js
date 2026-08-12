// Décors animés de Sablier : pétales, feuilles, neige, pluie, vagues, sable, lucioles,
// étoiles. Écrits à la main sur canvas, comme le minuteur : une bibliothèque de
// particules pèserait des centaines de kilo-octets pour ces quelques trajectoires, et
// ne saurait de toute façon pas dessiner le sablier lui-même.
//
// Le décor est purement décoratif : il ne porte aucune information et s'efface
// entièrement si le système demande à réduire les animations.
(function (global) {
  "use strict";

  const TAU = Math.PI * 2;
  const rand = (min, max) => min + Math.random() * (max - min);

  const rgba = (color, alpha) => {
    const match = /^#([0-9a-f]{6})$/i.exec(color || "");
    if (!match) return color;
    const value = Number.parseInt(match[1], 16);
    return `rgba(${value >> 16},${(value >> 8) & 255},${value & 255},${alpha})`;
  };

  function ellipseGlow(ctx, x, y, rx, ry, color, alpha) {
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, Math.max(rx, ry));
    gradient.addColorStop(0, rgba(color, alpha));
    gradient.addColorStop(0.5, rgba(color, alpha * 0.35));
    gradient.addColorStop(1, rgba(color, 0));
    ctx.save();
    ctx.scale(1, ry / rx);
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y * rx / ry, rx, 0, TAU);
    ctx.fill();
    ctx.restore();
  }

  function hill(ctx, w, h, base, height, color, alpha, phase = 0) {
    ctx.globalAlpha = alpha;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(0, base);
    for (let x = 0; x <= w; x += Math.max(8, w / 70)) {
      const y = base - Math.sin((x / w) * Math.PI + phase) * height - Math.sin((x / w) * TAU * 1.7) * height * 0.15;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function pine(ctx, x, ground, size, color, alpha) {
    ctx.globalAlpha = alpha;
    ctx.fillStyle = color;
    ctx.fillRect(x - size * 0.035, ground - size * 0.22, size * 0.07, size * 0.22);
    for (let layer = 0; layer < 3; layer++) {
      const y = ground - size * (0.28 + layer * 0.21);
      const width = size * (0.34 - layer * 0.065);
      ctx.beginPath();
      ctx.moveTo(x, y - size * 0.34);
      ctx.lineTo(x - width, y + size * 0.2);
      ctx.lineTo(x + width, y + size * 0.2);
      ctx.closePath();
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function skyWash(ctx, w, h, color, intensity, horizon = 0.68) {
    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    gradient.addColorStop(0, rgba(color, 0));
    gradient.addColorStop(horizon, rgba(color, 0.08 * intensity));
    gradient.addColorStop(1, rgba(color, 0.24 * intensity));
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, w, h);
  }

  // Une ambiance n'est plus seulement une couleur et quelques particules : ce premier
  // plan dessine un lieu reconnaissable. Les formes restent volontairement douces pour
  // que le minuteur demeure le sujet de l'écran.
  const BACKDROPS = {
    motes(ctx, w, h, color, intensity) {
      ellipseGlow(ctx, w * 0.5, h * 0.42, w * 0.48, h * 0.34, color, 0.12 * intensity);
      const beam = ctx.createLinearGradient(w * 0.28, 0, w * 0.66, h);
      beam.addColorStop(0, rgba(color, 0.08 * intensity));
      beam.addColorStop(0.45, rgba(color, 0.018 * intensity));
      beam.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = beam;
      ctx.beginPath();
      ctx.moveTo(w * 0.22, 0); ctx.lineTo(w * 0.48, 0); ctx.lineTo(w * 0.78, h); ctx.lineTo(w * 0.47, h); ctx.closePath(); ctx.fill();
    },
    petals(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity);
      ellipseGlow(ctx, w * 0.78, h * 0.26, w * 0.18, h * 0.18, color, 0.18 * intensity);
      hill(ctx, w, h, h * 0.86, h * 0.11, color, 0.09 * intensity, 0.2);
      ctx.strokeStyle = rgba(color, 0.22 * intensity); ctx.lineCap = "round";
      ctx.lineWidth = Math.max(5, w * 0.008); ctx.beginPath(); ctx.moveTo(w, h * 0.12); ctx.bezierCurveTo(w * 0.84, h * 0.16, w * 0.82, h * 0.32, w * 0.65, h * 0.37); ctx.stroke();
      ctx.lineWidth *= 0.38;
      for (let i = 0; i < 7; i++) { const x = w * (0.68 + i * 0.045), y = h * (0.35 - Math.sin(i) * 0.08); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - w * 0.055, y - h * 0.08); ctx.stroke(); }
    },
    fireflies(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity, 0.48);
      ellipseGlow(ctx, w * 0.72, h * 0.65, w * 0.25, h * 0.18, color, 0.22 * intensity);
      hill(ctx, w, h, h * 0.84, h * 0.15, color, 0.12 * intensity, 0.8);
      ctx.strokeStyle = rgba(color, 0.18 * intensity); ctx.lineWidth = 1;
      for (let x = 0; x < w; x += Math.max(9, w / 65)) { const blade = h * (0.025 + ((x * 17) % 31) / 520); ctx.beginPath(); ctx.moveTo(x, h); ctx.quadraticCurveTo(x + 4, h - blade * 0.65, x - 2, h - blade); ctx.stroke(); }
    },
    leaves(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity);
      ellipseGlow(ctx, w * 0.2, h * 0.3, w * 0.22, h * 0.22, color, 0.17 * intensity);
      hill(ctx, w, h, h * 0.9, h * 0.18, color, 0.08 * intensity, 1.2);
      ctx.strokeStyle = rgba(color, 0.22 * intensity); ctx.lineCap = "round"; ctx.lineWidth = Math.max(7, w * 0.012);
      for (const x of [0.08, 0.88]) { ctx.beginPath(); ctx.moveTo(w * x, h); ctx.bezierCurveTo(w * (x - 0.02), h * 0.72, w * (x + 0.04), h * 0.5, w * (x + (x < 0.5 ? 0.12 : -0.12)), h * 0.35); ctx.stroke(); }
    },
    snow(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity, 0.42);
      ellipseGlow(ctx, w * 0.77, h * 0.22, w * 0.13, h * 0.13, color, 0.16 * intensity);
      hill(ctx, w, h, h * 0.82, h * 0.2, color, 0.09 * intensity, 0.1);
      hill(ctx, w, h, h * 0.94, h * 0.13, color, 0.15 * intensity, 1.1);
      for (const [x, size] of [[0.08, 0.16], [0.18, 0.11], [0.82, 0.18], [0.92, 0.12]]) pine(ctx, w * x, h * 0.92, h * size, color, 0.18 * intensity);
    },
    rain(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity, 0.35);
      const reflection = ctx.createLinearGradient(0, h * 0.68, 0, h);
      reflection.addColorStop(0, rgba(color, 0)); reflection.addColorStop(1, rgba(color, 0.17 * intensity));
      ctx.fillStyle = reflection; ctx.fillRect(0, h * 0.6, w, h * 0.4);
      ctx.fillStyle = rgba(color, 0.055 * intensity);
      for (let i = 0; i < 6; i++) { const x = w * (0.08 + i * 0.17), width = w * (0.035 + (i % 3) * 0.018); ctx.beginPath(); ctx.ellipse(x, h * 0.88, width, h * 0.17, 0, 0, TAU); ctx.fill(); }
    },
    waves(ctx, w, h, color, intensity, now) {
      skyWash(ctx, w, h, color, intensity, 0.4);
      const sunY = h * 0.28; ellipseGlow(ctx, w * 0.72, sunY, w * 0.14, h * 0.14, color, 0.18 * intensity);
      ctx.strokeStyle = rgba(color, 0.22 * intensity); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(0, h * 0.68); ctx.lineTo(w, h * 0.68); ctx.stroke();
      const shimmer = (Math.sin(now / 1300) + 1) * 0.5;
      ctx.fillStyle = rgba(color, (0.045 + shimmer * 0.025) * intensity);
      ctx.beginPath(); ctx.moveTo(w * 0.66, sunY + h * 0.08); ctx.lineTo(w * 0.78, sunY + h * 0.08); ctx.lineTo(w * 0.9, h); ctx.lineTo(w * 0.52, h); ctx.closePath(); ctx.fill();
    },
    sand(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity, 0.3);
      ellipseGlow(ctx, w * 0.76, h * 0.23, w * 0.19, h * 0.19, color, 0.24 * intensity);
      hill(ctx, w, h, h * 0.76, h * 0.12, color, 0.11 * intensity, 0.35);
      hill(ctx, w, h, h * 0.93, h * 0.24, color, 0.2 * intensity, 1.4);
      ctx.strokeStyle = rgba(color, 0.13 * intensity); ctx.lineWidth = 1.2;
      for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.moveTo(w * 0.08, h * (0.78 + i * 0.035)); ctx.bezierCurveTo(w * 0.35, h * (0.69 + i * 0.04), w * 0.66, h * (0.88 + i * 0.02), w * 0.96, h * (0.8 + i * 0.04)); ctx.stroke(); }
    },
    spores(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity, 0.35);
      ellipseGlow(ctx, w * 0.5, h * 0.35, w * 0.42, h * 0.3, color, 0.15 * intensity);
      ctx.fillStyle = rgba(color, 0.11 * intensity);
      for (const [x, width] of [[0.05, 0.06], [0.17, 0.045], [0.8, 0.055], [0.93, 0.075]]) { ctx.fillRect(w * x, 0, w * width, h); }
      const ray = ctx.createLinearGradient(0, 0, 0, h);
      ray.addColorStop(0, rgba(color, 0.11 * intensity)); ray.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = ray; ctx.beginPath(); ctx.moveTo(w * 0.34, 0); ctx.lineTo(w * 0.5, 0); ctx.lineTo(w * 0.71, h); ctx.lineTo(w * 0.55, h); ctx.closePath(); ctx.fill();
    },
    storm(ctx, w, h, color, intensity, now) {
      skyWash(ctx, w, h, color, intensity, 0.25);
      const drift = Math.sin(now / 1900) * w * 0.018;
      ctx.fillStyle = rgba(color, 0.1 * intensity);
      for (let row = 0; row < 3; row++) for (let i = -1; i < 6; i++) { ctx.beginPath(); ctx.ellipse(i * w * 0.22 + drift + row * 25, h * (0.08 + row * 0.08), w * 0.17, h * 0.09, 0, 0, TAU); ctx.fill(); }
      hill(ctx, w, h, h * 0.95, h * 0.1, color, 0.08 * intensity, 0.9);
    },
    embers(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity, 0.55);
      ellipseGlow(ctx, w * 0.5, h * 0.88, w * 0.38, h * 0.25, color, 0.28 * intensity);
      ctx.fillStyle = rgba(color, 0.24 * intensity);
      for (let i = 0; i < 13; i++) { const x = w * (0.24 + i * 0.043), y = h * (0.88 + (i % 3) * 0.018); ctx.save(); ctx.translate(x, y); ctx.rotate((i % 5 - 2) * 0.12); ctx.beginPath(); ctx.roundRect(-w * 0.045, -h * 0.012, w * 0.09, h * 0.024, h * 0.012); ctx.fill(); ctx.restore(); }
    },
    aurora(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity, 0.28);
      ellipseGlow(ctx, w * 0.16, h * 0.18, w * 0.09, h * 0.09, color, 0.13 * intensity);
      hill(ctx, w, h, h * 0.86, h * 0.26, color, 0.12 * intensity, 0.15);
      hill(ctx, w, h, h * 0.98, h * 0.18, color, 0.2 * intensity, 1.05);
    },
    stars(ctx, w, h, color, intensity) {
      skyWash(ctx, w, h, color, intensity, 0.3);
      ellipseGlow(ctx, w * 0.78, h * 0.22, w * 0.11, h * 0.11, color, 0.18 * intensity);
      ctx.strokeStyle = rgba(color, 0.33 * intensity); ctx.lineWidth = Math.max(2, w * 0.004); ctx.beginPath(); ctx.arc(w * 0.78, h * 0.22, Math.min(w, h) * 0.045, Math.PI * 0.2, Math.PI * 1.8); ctx.stroke();
      hill(ctx, w, h, h * 0.9, h * 0.2, color, 0.12 * intensity, 0.35);
      hill(ctx, w, h, h, h * 0.13, color, 0.19 * intensity, 1.2);
    },
  };

  // Chaque décor sait semer ses particules et les faire vivre. `p` est une particule,
  // `w`/`h` la taille de la scène, `dt` le temps écoulé en secondes.
  const DECORS = {
    motes: {
      count: 26,
      seed: (w, h) => ({ x: rand(0, w), y: rand(0, h), r: rand(1, 2.4), vy: rand(-6, -2), vx: rand(-4, 4), a: rand(0.05, 0.18) }),
      step: (p, dt, w, h) => {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        if (p.y < -10) { p.y = h + 10; p.x = rand(0, w); }
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, TAU); ctx.fill();
      },
    },

    petals: {
      count: 22,
      seed: (w, h) => ({ x: rand(0, w), y: rand(-h, h), r: rand(4, 8), vy: rand(18, 34), sway: rand(14, 30), phase: rand(0, TAU), spin: rand(-1.4, 1.4), angle: rand(0, TAU), a: rand(0.3, 0.6) }),
      step: (p, dt, w, h) => {
        p.y += p.vy * dt;
        p.phase += dt * 1.1;
        p.x += Math.sin(p.phase) * p.sway * dt;
        p.angle += p.spin * dt;
        if (p.y > h + 12) { p.y = -12; p.x = rand(0, w); }
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.angle);
        ctx.beginPath(); ctx.ellipse(0, 0, p.r, p.r * 0.55, 0, 0, TAU); ctx.fill();
        ctx.restore();
      },
    },

    leaves: {
      count: 18,
      seed: (w, h) => ({ x: rand(0, w), y: rand(-h, h), r: rand(5, 10), vy: rand(24, 46), sway: rand(24, 52), phase: rand(0, TAU), spin: rand(-2, 2), angle: rand(0, TAU), a: rand(0.32, 0.62) }),
      step: (p, dt, w, h) => {
        p.y += p.vy * dt;
        p.phase += dt * 1.6;
        p.x += Math.sin(p.phase) * p.sway * dt;
        p.angle += p.spin * dt;
        if (p.y > h + 14) { p.y = -14; p.x = rand(0, w); }
      },
      draw: (ctx, p, color) => {
        // Deux arcs opposés : une feuille, pas un disque.
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.angle);
        ctx.beginPath();
        ctx.moveTo(-p.r, 0);
        ctx.quadraticCurveTo(0, -p.r * 0.85, p.r, 0);
        ctx.quadraticCurveTo(0, p.r * 0.85, -p.r, 0);
        ctx.fill();
        ctx.restore();
      },
    },

    snow: {
      count: 46,
      seed: (w, h) => ({ x: rand(0, w), y: rand(-h, h), r: rand(1.2, 3.4), vy: rand(14, 32), sway: rand(8, 22), phase: rand(0, TAU), a: rand(0.25, 0.7) }),
      step: (p, dt, w, h) => {
        p.y += p.vy * dt;
        p.phase += dt * 0.9;
        p.x += Math.sin(p.phase) * p.sway * dt;
        if (p.y > h + 6) { p.y = -6; p.x = rand(0, w); }
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, TAU); ctx.fill();
      },
    },

    rain: {
      count: 60,
      seed: (w, h) => ({ x: rand(0, w), y: rand(-h, h), len: rand(10, 26), vy: rand(420, 700), vx: rand(-40, -14), a: rand(0.12, 0.32) }),
      step: (p, dt, w, h) => {
        p.y += p.vy * dt;
        p.x += p.vx * dt;
        if (p.y > h + 20) { p.y = -20; p.x = rand(0, w + 60); }
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.3;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + p.vx * 0.03, p.y + p.len); ctx.stroke();
      },
    },

    fireflies: {
      count: 20,
      seed: (w, h) => ({ x: rand(0, w), y: rand(0, h), r: rand(1.6, 3.2), vx: rand(-16, 16), vy: rand(-12, 12), phase: rand(0, TAU), a: 0 }),
      step: (p, dt, w, h) => {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.phase += dt * 2.2;
        p.a = 0.12 + 0.34 * (0.5 + 0.5 * Math.sin(p.phase));   // clignotement
        if (p.x < -8) p.x = w + 8; else if (p.x > w + 8) p.x = -8;
        if (p.y < -8) p.y = h + 8; else if (p.y > h + 8) p.y = -8;
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, TAU); ctx.fill();
        ctx.globalAlpha = p.a * 0.25;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 3.4, 0, TAU); ctx.fill();
      },
    },

    stars: {
      count: 70,
      seed: (w, h) => ({ x: rand(0, w), y: rand(0, h * 0.85), r: rand(0.6, 1.8), phase: rand(0, TAU), speed: rand(0.4, 1.6), a: 0 }),
      step: (p, dt) => {
        p.phase += dt * p.speed;
        p.a = 0.15 + 0.45 * (0.5 + 0.5 * Math.sin(p.phase));   // scintillement
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, TAU); ctx.fill();
      },
    },

    sand: {
      count: 90,
      seed: (w, h) => ({ x: rand(0, w), y: h * rand(0.45, 1.0), r: rand(0.7, 2.0), vx: rand(70, 190), phase: rand(0, TAU), a: rand(0.08, 0.28) }),
      step: (p, dt, w, h) => {
        p.x += p.vx * dt;
        p.phase += dt * 3;
        p.y += Math.sin(p.phase) * 8 * dt;
        if (p.x > w + 8) { p.x = -8; p.y = h * rand(0.45, 1.0); }
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.fillRect(p.x, p.y, p.r * 2.2, p.r);   // grains étirés par le vent
      },
    },

    spores: {
      count: 30,
      seed: (w, h) => ({ x: rand(0, w), y: rand(0, h), r: rand(1.4, 3.6), vy: rand(-9, -3), phase: rand(0, TAU), sway: rand(6, 18), a: rand(0.1, 0.35) }),
      step: (p, dt, w, h) => {
        p.y += p.vy * dt;
        p.phase += dt * 0.7;
        p.x += Math.sin(p.phase) * p.sway * dt;
        if (p.y < -8) { p.y = h + 8; p.x = rand(0, w); }
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, TAU); ctx.fill();
        ctx.globalAlpha = p.a * 0.3;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 2.6, 0, TAU); ctx.fill();
      },
    },

    embers: {
      count: 40,
      seed: (w, h) => ({ x: rand(w * 0.3, w * 0.7), y: rand(h * 0.6, h + 40), r: rand(1, 2.6), vy: rand(-70, -28), phase: rand(0, TAU), sway: rand(10, 30), life: rand(0.3, 1), a: 0 }),
      step: (p, dt, w, h) => {
        p.y += p.vy * dt;
        p.phase += dt * 3;
        p.x += Math.sin(p.phase) * p.sway * dt;
        p.life -= dt * 0.22;
        p.a = Math.max(0, p.life) * 0.55;   // l'étincelle pâlit en montant
        if (p.life <= 0 || p.y < -10) { p.y = h + rand(0, 30); p.x = rand(w * 0.3, w * 0.7); p.life = rand(0.6, 1); }
      },
      draw: (ctx, p, color) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, TAU); ctx.fill();
      },
    },

    // L'orage : une pluie battante, et de loin en loin un éclair qui blanchit la scène.
    storm: {
      count: 70,
      seed: (w, h, index) => (index === 0
        ? { lightning: true, timer: rand(2, 6), flash: 0 }
        : { x: rand(0, w), y: rand(-h, h), len: rand(16, 40), vy: rand(620, 980), vx: rand(-90, -50), a: rand(0.14, 0.36) }),
      step: (p, dt, w, h) => {
        if (p.lightning) {
          p.timer -= dt;
          p.flash = Math.max(0, p.flash - dt * 3.2);
          if (p.timer <= 0) { p.flash = 1; p.timer = rand(3, 9); }
          return;
        }
        p.y += p.vy * dt;
        p.x += p.vx * dt;
        if (p.y > h + 24) { p.y = -24; p.x = rand(0, w + 120); }
      },
      draw: (ctx, p, color, w, h) => {
        if (p.lightning) {
          if (p.flash <= 0) return;
          ctx.globalAlpha = p.flash * 0.16;
          ctx.fillStyle = color;
          ctx.fillRect(0, 0, w, h);
          return;
        }
        ctx.globalAlpha = p.a;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + p.vx * 0.03, p.y + p.len); ctx.stroke();
      },
    },

    // Aurore : des voiles qui ondulent lentement en haut de la scène.
    aurora: {
      count: 4,
      seed: (w, h, index) => ({ index, amp: 16 + index * 9, len: 300 + index * 90, speed: 9 + index * 4, offset: rand(0, 500), base: h * (0.18 + index * 0.1), thickness: 34 + index * 12, a: 0.14 - index * 0.025 }),
      step: (p, dt) => { p.offset += p.speed * dt; },
      draw: (ctx, p, color, w) => {
        ctx.globalAlpha = Math.max(0.03, p.a);
        ctx.fillStyle = color;
        ctx.beginPath();
        for (let x = 0; x <= w; x += 10) ctx.lineTo(x, p.base + Math.sin((x + p.offset) / p.len * TAU) * p.amp);
        for (let x = w; x >= 0; x -= 10) ctx.lineTo(x, p.base + p.thickness + Math.sin((x + p.offset * 1.3) / p.len * TAU) * p.amp);
        ctx.closePath();
        ctx.fill();
      },
    },

    // Les vagues ne sont pas des particules : chaque « p » est une houle entière.
    waves: {
      count: 3,
      seed: (w, h, index) => ({ index, amp: 10 + index * 7, len: 260 + index * 130, speed: 22 + index * 12, offset: rand(0, 400), base: h * (0.72 + index * 0.09), a: 0.16 - index * 0.04 }),
      step: (p, dt) => { p.offset += p.speed * dt; },
      draw: (ctx, p, color, w, h) => {
        ctx.globalAlpha = p.a;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(0, h);
        for (let x = 0; x <= w; x += 8) {
          ctx.lineTo(x, p.base + Math.sin((x + p.offset) / p.len * TAU) * p.amp);
        }
        ctx.lineTo(w, h);
        ctx.closePath();
        ctx.fill();
      },
    },
  };

  function create(canvas) {
    const ctx = canvas.getContext("2d");
    const calm = global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let particles = [], decor = null, name = "", last = 0, w = 0, h = 0;

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(devicePixelRatio || 1, 2);
      w = rect.width; h = rect.height;
      canvas.width = Math.max(1, w * dpr);
      canvas.height = Math.max(1, h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // Chaque cran module à la fois la profondeur du paysage et la quantité de matière
    // animée. « Aucun » efface réellement la scène ; les vagues et aurores changent elles
    // aussi de présence, alors qu'elles gardaient auparavant le même nombre de bandes.
    const DENSITIES = {
      0: { particles: 0, scenery: 0 },
      1: { particles: 0.38, scenery: 0.42 },
      2: { particles: 1, scenery: 0.72 },
      3: { particles: 1.75, scenery: 1 },
    };
    let density = DENSITIES[2];

    function use(next, level) {
      const profile = DENSITIES[level] ?? DENSITIES[2];
      if (next === name && profile === density) return;
      name = next;
      density = profile;
      decor = profile.particles > 0 ? DECORS[next] || null : null;
      resize();
      ctx.clearRect(0, 0, w, h);
      const continuous = next === "waves" || next === "aurora";
      const factor = continuous ? 0.55 + profile.particles * 0.45 : profile.particles;
      const count = Math.max(1, Math.round((decor?.count || 0) * Math.min(1.6, factor)));
      particles = decor ? Array.from({ length: count }, (_, i) => decor.seed(w || 1, h || 1, i)) : [];
    }

    function frame(now, color) {
      const dt = Math.min(0.05, last ? (now - last) / 1000 : 0);
      last = now;
      const rect = canvas.getBoundingClientRect();
      if (Math.abs(rect.width - w) > 1 || Math.abs(rect.height - h) > 1) resize();
      ctx.clearRect(0, 0, w, h);
      if (!decor) return;
      BACKDROPS[name]?.(ctx, w, h, color, density.scenery, now);
      for (const p of particles) {
        if (!calm) decor.step(p, dt, w, h);   // au repos, le décor reste figé
        decor.draw(ctx, p, color, w, h);
      }
      ctx.globalAlpha = 1;
    }

    return { use, frame, inspect: () => ({ name, particles: particles.length, scenery: density.scenery }) };
  }

  global.SablierDecor = { create, names: Object.keys(DECORS), backdrops: Object.keys(BACKDROPS) };
})(window);
