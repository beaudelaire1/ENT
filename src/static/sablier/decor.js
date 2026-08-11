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

    function use(next) {
      if (next === name) return;
      name = next;
      decor = DECORS[next] || null;
      resize();
      particles = decor ? Array.from({ length: decor.count }, (_, i) => decor.seed(w || 1, h || 1, i)) : [];
    }

    function frame(now, color) {
      const dt = Math.min(0.05, last ? (now - last) / 1000 : 0);
      last = now;
      if (!decor) return;
      const rect = canvas.getBoundingClientRect();
      if (Math.abs(rect.width - w) > 1 || Math.abs(rect.height - h) > 1) resize();
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        if (!calm) decor.step(p, dt, w, h);   // au repos, le décor reste figé
        decor.draw(ctx, p, color, w, h);
      }
      ctx.globalAlpha = 1;
    }

    return { use, frame };
  }

  global.SablierDecor = { create, names: Object.keys(DECORS) };
})(window);
