(function (global) {
  "use strict";

  const base = global.SablierDecor;
  if (!base?.create) return;
  const TAU = Math.PI * 2;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const hash = (i, s = 0) => { const n = Math.sin(i * 12.9898 + s * 78.233) * 43758.5453; return n - Math.floor(n); };
  const rgba = (hex, a) => {
    const m = /^#([0-9a-f]{6})$/i.exec(hex || "");
    if (!m) return hex;
    const n = Number.parseInt(m[1], 16);
    return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
  };
  const mix = (a, b, t) => {
    const parse = (c) => /^#([0-9a-f]{6})$/i.exec(c || "");
    const aa = parse(a), bb = parse(b); if (!aa || !bb) return a;
    const A = Number.parseInt(aa[1], 16), B = Number.parseInt(bb[1], 16), q = clamp(t, 0, 1);
    const c = [16, 8, 0].map(shift => Math.round(((A >> shift) & 255) * (1 - q) + ((B >> shift) & 255) * q));
    return `#${c.map(v => v.toString(16).padStart(2, "0")).join("")}`;
  };
  function sky(ctx, w, h, top, mid, ground) {
    const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, top); g.addColorStop(.6, mid); g.addColorStop(1, ground);
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  }
  function glow(ctx, x, y, r, color, alpha) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, rgba(color, alpha)); g.addColorStop(.4, rgba(color, alpha * .35)); g.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
  }
  function ridge(ctx, w, h, baseY, amp, color, salt, alpha = 1) {
    ctx.globalAlpha = alpha; ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(0, h); ctx.lineTo(0, baseY);
    for (let i = 0, x = 0; x <= w + 40; i++, x += Math.max(24, w * .065)) ctx.lineTo(x, baseY - amp * (.22 + hash(i, salt) * .78));
    ctx.lineTo(w, h); ctx.closePath(); ctx.fill(); ctx.globalAlpha = 1;
  }
  function tree(ctx, x, ground, height, trunk, leaves, salt, bare = false) {
    ctx.strokeStyle = trunk; ctx.lineCap = "round"; ctx.lineWidth = Math.max(4, height * .055); ctx.beginPath(); ctx.moveTo(x, ground); ctx.quadraticCurveTo(x - height * .04, ground - height * .48, x + height * .025, ground - height * .82); ctx.stroke();
    for (let i = 0; i < 8; i++) { const side = i % 2 ? 1 : -1, y = ground - height * (.35 + i * .055), dx = side * height * (.12 + hash(i, salt) * .2); ctx.lineWidth = Math.max(1.5, height * .018); ctx.beginPath(); ctx.moveTo(x, y); ctx.quadraticCurveTo(x + dx * .45, y - height * .07, x + dx, y - height * (.07 + hash(i, salt + 3) * .09)); ctx.stroke(); }
    if (bare) return;
    for (let i = 0; i < 24; i++) { const a = hash(i, salt + 11) * TAU, r = Math.sqrt(hash(i, salt + 17)), cx = x + Math.cos(a) * height * .25 * r, cy = ground - height * .78 + Math.sin(a) * height * .16 * r; ctx.globalAlpha = .72 + hash(i, salt + 19) * .24; ctx.fillStyle = mix(leaves, "#ffffff", hash(i, salt + 23) * .12); ctx.beginPath(); ctx.arc(cx, cy, height * (.035 + hash(i, salt + 29) * .055), 0, TAU); ctx.fill(); }
    ctx.globalAlpha = 1;
  }
  function water(ctx, w, h, y, top, bottom) { const g = ctx.createLinearGradient(0, y, 0, h); g.addColorStop(0, top); g.addColorStop(1, bottom); ctx.fillStyle = g; ctx.fillRect(0, y, w, h - y); }
  function shimmer(ctx, w, h, y0, color, amount, now) { for (let i = 0; i < 18; i++) { const y = y0 + (h - y0) * i / 18, x = w * .5 + Math.sin(now / 1700 + i) * w * .035, half = w * (.025 + i * .01); ctx.globalAlpha = amount * (.08 + (i % 4) * .035); ctx.strokeStyle = color; ctx.beginPath(); ctx.moveTo(x - half, y); ctx.lineTo(x + half, y); ctx.stroke(); } ctx.globalAlpha = 1; }
  function vignette(ctx, w, h, color = "#000000", alpha = .4) { const g = ctx.createRadialGradient(w * .5, h * .46, Math.min(w, h) * .16, w * .5, h * .5, Math.max(w, h) * .76); g.addColorStop(0, rgba(color, 0)); g.addColorStop(1, rgba(color, alpha)); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); }

  function springStatic(ctx, w, h, p) {
    sky(ctx, w, h, "#8dc9d8", "#d5e6cd", "#39533a"); glow(ctx, w * .72, h * .2, w * .2, "#fff3c3", .28); ridge(ctx, w, h, h * .63, h * .16, "#52735a", 10, .72);
    ctx.fillStyle = "#527b47"; ctx.beginPath(); ctx.moveTo(0, h * .72); ctx.quadraticCurveTo(w * .4, h * .58, w, h * .73); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.fill();
    tree(ctx, w * .18, h * .78, h * .48, "#5a4636", "#dba8bc", 21); tree(ctx, w * .82, h * .8, h * .41, "#594636", "#f1c5ce", 31);
    const stream = ctx.createLinearGradient(0, h * .6, 0, h); stream.addColorStop(0, "#9dc9c7"); stream.addColorStop(1, "#315a61"); ctx.fillStyle = stream; ctx.beginPath(); ctx.moveTo(w * .51, h * .58); ctx.bezierCurveTo(w * .38, h * .74, w * .66, h * .72, w * .38, h); ctx.lineTo(w * .65, h); ctx.bezierCurveTo(w * .75, h * .75, w * .53, h * .69, w * .57, h * .58); ctx.fill();
    for (let i = 0; i < 54; i++) { ctx.globalAlpha = .28 + hash(i, 44) * .45; ctx.fillStyle = i % 3 ? "#f3d4dd" : "#fff0aa"; ctx.beginPath(); ctx.arc(hash(i, 47) * w, h * (.72 + hash(i, 53) * .23), .7 + hash(i, 59) * 1.8, 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; vignette(ctx, w, h, "#18311f", .22);
  }
  function springMotion(ctx, w, h, p, amount, now) { shimmer(ctx, w, h, h * .64, "#eaffff", amount, now); for (let i = 0; i < Math.round(22 * amount); i++) { const t = (hash(i, 67) + now / (12000 + i * 220)) % 1; ctx.save(); ctx.translate(((hash(i, 71) + t * .16) % 1) * w, h * (.18 + t * .68)); ctx.rotate(t * 5 + i); ctx.globalAlpha = .16 * amount; ctx.fillStyle = i % 2 ? "#f0bdcb" : "#f6dfb4"; ctx.ellipse(0, 0, 3, 1.5, 0, 0, TAU); ctx.fill(); ctx.restore(); } ctx.globalAlpha = 1; }

  function summerStatic(ctx, w, h) {
    sky(ctx, w, h, "#4e94c0", "#f3c982", "#72523a"); glow(ctx, w * .78, h * .17, w * .23, "#fff0ae", .42); ridge(ctx, w, h, h * .62, h * .22, "#786f58", 80, .6);
    ctx.fillStyle = "#a78c68"; ctx.fillRect(0, h * .72, w, h * .28); ctx.strokeStyle = rgba("#ead7b7", .22); ctx.lineWidth = 1; for (let x = -w; x < w * 2; x += w * .09) { ctx.beginPath(); ctx.moveTo(x, h); ctx.lineTo(w * .5 + (x - w * .5) * .35, h * .72); ctx.stroke(); }
    ctx.fillStyle = "#5c4937"; ctx.fillRect(w * .08, h * .2, w * .035, h * .56); ctx.fillRect(w * .88, h * .18, w * .035, h * .58); ctx.fillRect(w * .08, h * .2, w * .835, h * .035);
    for (let i = 0; i < 8; i++) { const x = w * (.14 + i * .1); ctx.strokeStyle = "#405b37"; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(x, h * .2); ctx.quadraticCurveTo(x + 20, h * .28, x - 12, h * .37); ctx.stroke(); }
    ctx.fillStyle = "#22342a"; ctx.beginPath(); ctx.ellipse(w * .26, h * .67, w * .14, h * .05, 0, 0, TAU); ctx.fill(); water(ctx, w, h, h * .79, "#4f9ba0", "#17484d"); vignette(ctx, w, h, "#3b2515", .2);
  }
  function summerMotion(ctx, w, h, p, amount, now, progress) { shimmer(ctx, w, h, h * .8, "#fff4c4", amount * .8, now); const heat = amount * .055; for (let i = 0; i < 5; i++) { const y = h * (.46 + i * .045) + Math.sin(now / 1600 + i) * 3; ctx.globalAlpha = heat; ctx.strokeStyle = "#fff1c2"; ctx.beginPath(); for (let x = 0; x <= w; x += 16) { const yy = y + Math.sin(x / 48 + now / 900 + i) * 2; x ? ctx.lineTo(x, yy) : ctx.moveTo(x, yy); } ctx.stroke(); } ctx.globalAlpha = 1; if (1 - progress > .55) glow(ctx, w * .78, h * .17, w * .2, "#ffb96a", .06 * amount); }

  function autumnStatic(ctx, w, h) {
    sky(ctx, w, h, "#6b7280", "#d49963", "#3b2b25"); glow(ctx, w * .23, h * .24, w * .19, "#ffd39d", .24); ridge(ctx, w, h, h * .58, h * .22, "#503d35", 101, .7); water(ctx, w, h, h * .68, "#75574d", "#221b1b");
    for (let i = 0; i < 9; i++) tree(ctx, w * (.03 + i * .12), h * .72, h * (.28 + hash(i, 109) * .2), "#3b2a24", i % 3 === 0 ? "#a54026" : i % 3 === 1 ? "#d17934" : "#85542a", 120 + i);
    ctx.fillStyle = "#4a3529"; ctx.beginPath(); ctx.moveTo(0, h * .85); ctx.lineTo(w * .36, h * .74); ctx.lineTo(w * .52, h); ctx.lineTo(0, h); ctx.fill(); vignette(ctx, w, h, "#1c1210", .34);
  }
  function autumnMotion(ctx, w, h, p, amount, now) { shimmer(ctx, w, h, h * .7, "#e7b77f", amount * .6, now); for (let i = 0; i < Math.round(28 * amount); i++) { const t = (hash(i, 137) + now / (9000 + i * 110)) % 1, x = ((hash(i, 139) + t * .22) % 1) * w, y = h * (.1 + t * .8); ctx.save(); ctx.translate(x, y); ctx.rotate(t * 10 + i); ctx.globalAlpha = .16 + hash(i, 149) * .17; ctx.fillStyle = i % 3 === 0 ? "#c04b2f" : i % 3 === 1 ? "#dc8a39" : "#9a652e"; ctx.fillRect(-3, -1.5, 6, 3); ctx.restore(); } ctx.globalAlpha = 1; }

  function winterStatic(ctx, w, h) {
    sky(ctx, w, h, "#4c627a", "#b4cad8", "#60747d"); glow(ctx, w * .7, h * .18, w * .18, "#eef8ff", .2); ridge(ctx, w, h, h * .7, h * .42, "#aabcc5", 170, .98); ridge(ctx, w, h, h * .76, h * .28, "#728793", 177, .9);
    ctx.fillStyle = "#d5e2e5"; ctx.fillRect(0, h * .75, w, h * .25); ctx.fillStyle = "#2f3940"; ctx.fillRect(w * .15, h * .62, w * .2, h * .15); ctx.fillStyle = "#53616a"; ctx.beginPath(); ctx.moveTo(w * .12, h * .63); ctx.lineTo(w * .25, h * .52); ctx.lineTo(w * .39, h * .63); ctx.fill(); glow(ctx, w * .24, h * .69, w * .06, "#ffc37d", .18);
    for (let i = 0; i < 8; i++) { const x = w * (.48 + i * .07), gh = h * (.13 + hash(i, 181) * .1); ctx.fillStyle = "#213d3c"; ctx.beginPath(); ctx.moveTo(x, h * .78); ctx.lineTo(x - gh * .16, h * .78); ctx.lineTo(x, h * .78 - gh); ctx.lineTo(x + gh * .16, h * .78); ctx.fill(); } vignette(ctx, w, h, "#24313b", .24);
  }
  function winterMotion(ctx, w, h, p, amount, now) { for (let i = 0; i < Math.round(48 * amount); i++) { const speed = .000045 + hash(i, 191) * .00009, y = ((hash(i, 193) + now * speed) % 1) * h, x = ((hash(i, 197) + Math.sin(now / 4000 + i) * .03) % 1) * w; ctx.globalAlpha = .18 + hash(i, 199) * .28; ctx.fillStyle = "#f4fbff"; ctx.beginPath(); ctx.arc(x, y, .7 + hash(i, 211) * 2.2, 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; }

  function rainCityStatic(ctx, w, h) {
    sky(ctx, w, h, "#101923", "#263748", "#10151a"); ctx.fillStyle = "#111920"; for (let i = 0; i < 11; i++) { const x = w * i / 11, bh = h * (.16 + hash(i, 230) * .35); ctx.fillRect(x, h * .68 - bh, w * .11, bh); for (let r = 0; r < 4; r++) { ctx.fillStyle = rgba(i % 3 ? "#ffc46b" : "#68bfff", .18); ctx.fillRect(x + w * .025, h * .4 + r * 18, w * .012, 4); } ctx.fillStyle = "#111920"; }
    ctx.fillStyle = "#090d11"; ctx.beginPath(); ctx.moveTo(0, h * .7); ctx.lineTo(w, h * .66); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.fill(); for (let i = 0; i < 12; i++) glow(ctx, hash(i, 247) * w, h * (.64 + hash(i, 251) * .25), w * .035, i % 2 ? "#ffb75d" : "#5ab9ff", .08); vignette(ctx, w, h, "#020405", .48);
  }
  function rainCityMotion(ctx, w, h, p, amount, now) { for (let i = 0; i < Math.round(82 * amount); i++) { const y = ((hash(i, 257) + now * (.00015 + hash(i, 263) * .00017)) % 1) * h, x = hash(i, 269) * w, len = 9 + hash(i, 271) * 26; ctx.globalAlpha = .06 + hash(i, 277) * .16; ctx.strokeStyle = "#b7d5ea"; ctx.lineWidth = .7 + hash(i, 281); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - 4, y + len); ctx.stroke(); } ctx.globalAlpha = 1; }

  function oceanStatic(ctx, w, h) {
    sky(ctx, w, h, "#5f8ba7", "#b2c8d0", "#31596a"); glow(ctx, w * .68, h * .17, w * .2, "#f6e5c7", .2); ridge(ctx, w, h, h * .7, h * .32, "#374e50", 302, .7); water(ctx, w, h, h * .53, "#477f91", "#0d3442");
    ctx.fillStyle = "#1d2d2e"; ctx.beginPath(); ctx.moveTo(0, h * .58); ctx.lineTo(w * .17, h * .42); ctx.lineTo(w * .26, h * .67); ctx.lineTo(w * .21, h); ctx.lineTo(0, h); ctx.fill(); ctx.beginPath(); ctx.moveTo(w, h * .62); ctx.lineTo(w * .86, h * .49); ctx.lineTo(w * .79, h); ctx.lineTo(w, h); ctx.fill(); vignette(ctx, w, h, "#102833", .27);
  }
  function oceanMotion(ctx, w, h, p, amount, now) { for (let row = 0; row < 10; row++) { const y = h * (.57 + row * .043); ctx.globalAlpha = .08 + row * .008; ctx.strokeStyle = row % 2 ? "#d5eef0" : "#8fc2c9"; ctx.beginPath(); for (let x = 0; x <= w; x += 10) { const yy = y + Math.sin(x / (36 + row * 5) + now / 1200 + row) * (2 + row * .25); x ? ctx.lineTo(x, yy) : ctx.moveTo(x, yy); } ctx.stroke(); } ctx.globalAlpha = 1; if (amount > .65) { ctx.strokeStyle = rgba("#e9f5f3", .28); for (let i = 0; i < 3; i++) { const x = w * (.35 + ((now / 60000 + i * .21) % .38)), y = h * (.25 + i * .025); ctx.beginPath(); ctx.arc(x, y, 6, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke(); } } }

  function saharaStatic(ctx, w, h) {
    sky(ctx, w, h, "#3c3951", "#d6935c", "#7f4727"); glow(ctx, w * .25, h * .23, w * .2, "#ffd39b", .28); ctx.fillStyle = "#8b512d"; ctx.beginPath(); ctx.moveTo(0, h * .61); ctx.quadraticCurveTo(w * .25, h * .43, w * .52, h * .62); ctx.quadraticCurveTo(w * .78, h * .47, w, h * .59); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.fill(); ctx.fillStyle = "#b26b37"; ctx.beginPath(); ctx.moveTo(0, h * .78); ctx.quadraticCurveTo(w * .38, h * .51, w * .7, h * .75); ctx.quadraticCurveTo(w * .88, h * .65, w, h * .7); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.fill();
    ctx.fillStyle = "#362820"; ctx.fillRect(w * .64, h * .49, w * .11, h * .22); ctx.beginPath(); ctx.arc(w * .695, h * .49, w * .055, Math.PI, 0); ctx.fill(); ctx.fillStyle = "#17161a"; ctx.beginPath(); ctx.arc(w * .695, h * .52, w * .029, Math.PI, 0); ctx.fill(); ctx.fillRect(w * .666, h * .52, w * .058, h * .12); ctx.strokeStyle = "#3d3127"; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(w * .69, h * .47); ctx.lineTo(w * .69, h * .34); ctx.stroke(); ctx.fillStyle = "#19191c"; ctx.beginPath(); ctx.arc(w * .69, h * .33, 7, 0, TAU); ctx.fill(); vignette(ctx, w, h, "#2a1409", .32);
  }
  function saharaMotion(ctx, w, h, p, amount, now, progress) { for (let i = 0; i < Math.round(16 * amount); i++) { const x = ((hash(i, 331) + now / (15000 + i * 300)) % 1.3 - .15) * w, y = h * (.55 + hash(i, 337) * .34); ctx.globalAlpha = .018 + hash(i, 347) * .025; ctx.fillStyle = "#f5c181"; ctx.beginPath(); ctx.ellipse(x, y, w * (.04 + hash(i, 349) * .05), 2 + hash(i, 353) * 4, -.08, 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; if (1 - progress > .35) { const starsN = Math.round((1 - progress) * 46 * amount); for (let i = 0; i < starsN; i++) { ctx.globalAlpha = .25; ctx.fillStyle = "#fff0d5"; ctx.beginPath(); ctx.arc(hash(i, 359) * w, hash(i, 367) * h * .42, .5 + hash(i, 373), 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; } }

  function forestStatic(ctx, w, h) {
    sky(ctx, w, h, "#0b1c17", "#224136", "#101c17"); glow(ctx, w * .48, 0, w * .3, "#dff2bf", .13); for (let i = 0; i < 14; i++) { const x = w * (-.05 + i * .082), depth = .55 + (i % 4) * .11, width = w * (.025 + depth * .015); ctx.fillStyle = i % 3 ? "#172a22" : "#22382b"; ctx.fillRect(x, 0, width, h * (.82 + hash(i, 389) * .2)); }
    ctx.fillStyle = "#0d1713"; ctx.fillRect(0, h * .76, w, h * .24); ctx.strokeStyle = rgba("#ddf3c4", .11); ctx.lineWidth = w * .025; for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.moveTo(w * (.33 + i * .08), 0); ctx.lineTo(w * (.18 + i * .11), h * .8); ctx.stroke(); } vignette(ctx, w, h, "#020806", .52);
  }
  function forestMotion(ctx, w, h, p, amount, now) { for (let i = 0; i < Math.round(26 * amount); i++) { const phase = now / (4000 + i * 90) + i, x = w * (.08 + hash(i, 397) * .84) + Math.sin(phase) * 5, y = h * (.18 + hash(i, 401) * .65) + Math.cos(phase * .7) * 4; ctx.globalAlpha = .06 + hash(i, 409) * .12; ctx.fillStyle = i % 5 === 0 ? "#d8f4a4" : "#a8cdb1"; ctx.beginPath(); ctx.arc(x, y, .6 + hash(i, 419) * 1.7, 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; }

  function stormStatic(ctx, w, h) {
    sky(ctx, w, h, "#11131b", "#333846", "#15191d"); for (let i = 0; i < 9; i++) { ctx.globalAlpha = .18 + hash(i, 431) * .18; ctx.fillStyle = "#666b77"; ctx.beginPath(); ctx.ellipse(hash(i, 433) * w, h * (.11 + hash(i, 439) * .2), w * (.12 + hash(i, 443) * .13), h * .07, 0, 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; water(ctx, w, h, h * .56, "#263945", "#09151b"); ctx.fillStyle = "#111718"; ctx.beginPath(); ctx.moveTo(0, h * .58); ctx.lineTo(w * .22, h * .38); ctx.lineTo(w * .3, h); ctx.lineTo(0, h); ctx.fill(); ctx.beginPath(); ctx.moveTo(w, h * .62); ctx.lineTo(w * .81, h * .46); ctx.lineTo(w * .73, h); ctx.lineTo(w, h); ctx.fill(); vignette(ctx, w, h, "#010203", .55);
  }
  function stormMotion(ctx, w, h, p, amount, now) { for (let row = 0; row < 8; row++) { const y = h * (.6 + row * .05); ctx.strokeStyle = rgba("#9db4c0", .1); ctx.beginPath(); for (let x = 0; x <= w; x += 12) { const yy = y + Math.sin(x / 31 + now / 700 + row) * 4; x ? ctx.lineTo(x, yy) : ctx.moveTo(x, yy); } ctx.stroke(); } const cycle = now % 9000; if (cycle < 230 * amount) { ctx.globalAlpha = .45 * (1 - cycle / (230 * amount)); ctx.fillStyle = "#dce8ff"; ctx.fillRect(0, 0, w, h * .72); ctx.globalAlpha = 1; ctx.strokeStyle = "#f3f6ff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * .64, h * .08); ctx.lineTo(w * .58, h * .25); ctx.lineTo(w * .63, h * .24); ctx.lineTo(w * .54, h * .44); ctx.stroke(); } }

  function embersStatic(ctx, w, h) {
    sky(ctx, w, h, "#120d0b", "#271713", "#090706"); ctx.fillStyle = "#1b1511"; ctx.fillRect(0, h * .66, w, h * .34); ctx.fillStyle = "#342319"; ctx.fillRect(w * .25, h * .3, w * .5, h * .48); ctx.fillStyle = "#090807"; ctx.fillRect(w * .3, h * .37, w * .4, h * .33); const g = ctx.createRadialGradient(w * .5, h * .65, 0, w * .5, h * .65, w * .22); g.addColorStop(0, "#f29842"); g.addColorStop(.28, "#8d3b20"); g.addColorStop(1, "#160d0a"); ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(w * .5, h * .68, w * .18, h * .06, 0, 0, TAU); ctx.fill(); glow(ctx, w * .5, h * .58, w * .32, "#ff9b4b", .17); vignette(ctx, w, h, "#050302", .45);
  }
  function embersMotion(ctx, w, h, p, amount, now) { for (let i = 0; i < Math.round(30 * amount); i++) { const t = (hash(i, 461) + now / (3500 + i * 80)) % 1, x = w * .5 + (hash(i, 463) - .5) * w * .24 + Math.sin(t * 7 + i) * 10, y = h * .68 - t * h * .35; ctx.globalAlpha = (1 - t) * (.16 + hash(i, 467) * .35); ctx.fillStyle = i % 3 ? "#ff873a" : "#ffd083"; ctx.beginPath(); ctx.arc(x, y, .7 + hash(i, 479) * 1.8, 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; }

  function auroraStatic(ctx, w, h) { sky(ctx, w, h, "#02111d", "#0d3448", "#10222a"); for (let i = 0; i < 70; i++) { ctx.globalAlpha = .25 + hash(i, 487) * .45; ctx.fillStyle = "#dff5ff"; ctx.beginPath(); ctx.arc(hash(i, 491) * w, hash(i, 499) * h * .55, .4 + hash(i, 503), 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; ridge(ctx, w, h, h * .79, h * .12, "#152c33", 509, .9); ctx.fillStyle = "#d8e3e0"; ctx.fillRect(0, h * .79, w, h * .21); vignette(ctx, w, h, "#031018", .35); }
  function auroraMotion(ctx, w, h, p, amount, now) { for (let band = 0; band < 5; band++) { const baseY = h * (.08 + band * .075), thick = h * (.1 + band * .01), g = ctx.createLinearGradient(0, baseY, 0, baseY + thick), color = band % 2 ? "#79d7ff" : "#77f0b0"; g.addColorStop(0, rgba(color, 0)); g.addColorStop(.45, rgba(color, .16 * amount)); g.addColorStop(1, rgba(color, 0)); ctx.fillStyle = g; ctx.beginPath(); for (let x = 0; x <= w; x += 10) { const y = baseY + Math.sin(x / (95 + band * 24) + now / (3700 + band * 400)) * h * .035; x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } for (let x = w; x >= 0; x -= 10) { const y = baseY + thick + Math.sin(x / (110 + band * 20) + now / (4300 + band * 500) + 1) * h * .025; ctx.lineTo(x, y); } ctx.closePath(); ctx.fill(); } }

  function nightStatic(ctx, w, h) { sky(ctx, w, h, "#030710", "#10192a", "#080a0d"); for (let i = 0; i < 95; i++) { ctx.globalAlpha = .25 + hash(i, 521) * .55; ctx.fillStyle = "#dce8ff"; ctx.beginPath(); ctx.arc(hash(i, 523) * w, hash(i, 541) * h * .6, .35 + hash(i, 547) * 1.2, 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; glow(ctx, w * .74, h * .18, w * .11, "#e8edff", .18); ctx.fillStyle = "#dbe2ef"; ctx.beginPath(); ctx.arc(w * .74, h * .18, Math.min(w, h) * .045, 0, TAU); ctx.fill(); ctx.fillStyle = "#090d15"; for (let i = 0; i < 13; i++) { const x = w * i / 13, bh = h * (.1 + hash(i, 557) * .28); ctx.fillRect(x, h * .73 - bh, w * .09, bh); } ctx.fillStyle = "#050607"; ctx.fillRect(0, h * .73, w, h * .27); ctx.strokeStyle = "#2d3035"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, h * .79); ctx.lineTo(w, h * .79); ctx.stroke(); vignette(ctx, w, h, "#000000", .46); }
  function nightMotion(ctx, w, h, p, amount, now) { for (let i = 0; i < Math.round(18 * amount); i++) { const pulse = .5 + .5 * Math.sin(now / (800 + i * 43) + i); ctx.globalAlpha = .08 + pulse * .16; ctx.fillStyle = i % 4 ? "#ffd58a" : "#7fb8ff"; ctx.beginPath(); ctx.arc(w * (.08 + hash(i, 563) * .84), h * (.46 + hash(i, 569) * .22), 1 + pulse, 0, TAU); ctx.fill(); } ctx.globalAlpha = 1; }

  const WORLDS = {
    spring_meadow: { static: springStatic, motion: springMotion, motionUnits: 22 },
    summer_terrace: { static: summerStatic, motion: summerMotion, motionUnits: 18 },
    autumn_lake: { static: autumnStatic, motion: autumnMotion, motionUnits: 28 },
    winter_lodge: { static: winterStatic, motion: winterMotion, motionUnits: 48 },
    rain_city: { static: rainCityStatic, motion: rainCityMotion, motionUnits: 82 },
    ocean_cliffs: { static: oceanStatic, motion: oceanMotion, motionUnits: 16 },
    sahara_observatory: { static: saharaStatic, motion: saharaMotion, motionUnits: 22 },
    ancient_forest: { static: forestStatic, motion: forestMotion, motionUnits: 26 },
    storm_cliffs: { static: stormStatic, motion: stormMotion, motionUnits: 14 },
    ember_hearth: { static: embersStatic, motion: embersMotion, motionUnits: 30 },
    polar_sky: { static: auroraStatic, motion: auroraMotion, motionUnits: 24 },
    midnight_rooftop: { static: nightStatic, motion: nightMotion, motionUnits: 18 },
  };
  const DENSITY = { 0: { detail: .78, motion: 0 }, 1: { detail: .86, motion: .34 }, 2: { detail: 1, motion: .68 }, 3: { detail: 1, motion: 1 } };
  const originalCreate = base.create.bind(base);

  base.create = function createComposite(canvas) {
    const original = originalCreate(canvas), ctx = canvas.getContext("2d"), app = canvas.closest(".focus-app") || document.documentElement;
    const cache = document.createElement("canvas"), cacheCtx = cache.getContext("2d");
    const reduced = global.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches || false;
    let world = null, density = DENSITY[2], w = 0, h = 0, dpr = 1, dirty = true, paletteKey = "";
    function palette() { const s = getComputedStyle(app); return { sky: s.getPropertyValue("--world-sky").trim() || "#081018", horizon: s.getPropertyValue("--world-horizon").trim() || "#29485a", ground: s.getPropertyValue("--world-ground").trim() || "#10151a", light: s.getPropertyValue("--world-light").trim() || "#ffe5b4" }; }
    function resize() { const r = canvas.getBoundingClientRect(), nw = Math.max(1, r.width), nh = Math.max(1, r.height), nd = Math.min(global.devicePixelRatio || 1, nw < 760 ? 1.25 : 1.65); if (Math.abs(nw - w) < 1 && Math.abs(nh - h) < 1 && nd === dpr) return; w = nw; h = nh; dpr = nd; canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); cache.width = Math.round(w * dpr); cache.height = Math.round(h * dpr); cacheCtx.setTransform(dpr, 0, 0, dpr, 0, 0); dirty = true; }
    return {
      use(next, level) { if (WORLDS[next]) { if (world !== next || density !== (DENSITY[level] || DENSITY[2])) dirty = true; world = next; density = DENSITY[level] || DENSITY[2]; } else { world = null; original.use(next, level); } },
      frame(now, accent) { if (!world) return original.frame(now, accent); resize(); const p = palette(), key = `${p.sky}|${p.horizon}|${p.ground}|${p.light}`; if (key !== paletteKey) { paletteKey = key; dirty = true; } if (dirty) { cacheCtx.clearRect(0, 0, w, h); WORLDS[world].static(cacheCtx, w, h, p, density.detail); dirty = false; } ctx.clearRect(0, 0, w, h); ctx.drawImage(cache, 0, 0, cache.width, cache.height, 0, 0, w, h); const motion = reduced ? 0 : density.motion; if (motion > 0) { const node = document.querySelector("#digital-progress"), progress = Number.parseFloat(node?.style.getPropertyValue("--progress") || "1"); WORLDS[world].motion(ctx, w, h, p, motion, now, Number.isFinite(progress) ? clamp(progress, 0, 1) : 1); } ctx.globalAlpha = 1; },
      inspect() { return world ? { name: world, particles: Math.round(WORLDS[world].motionUnits * (reduced ? 0 : density.motion)), scenery: density.detail, motion: reduced ? 0 : density.motion } : original.inspect(); },
    };
  };
  base.names = [...base.names, ...Object.keys(WORLDS)];
  base.backdrops = [...base.backdrops, ...Object.keys(WORLDS)];
  base.seasonal = Object.keys(WORLDS);
})(window);
