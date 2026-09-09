// Rend les 24 univers hors ligne et enregistre la vue de chacun.
//
// Ces vues sont ce que voit un poste sans WebGL : elles doivent donc sortir du moteur
// qu'elles remplacent, et non d'une illustration dessinée à côté. Le rendu est figé
// avant la capture — sinon deux exécutions du même univers donneraient deux images.
//
//   .venv/Scripts/python.exe tests/browser/server.py
//   node tools/sablier-plates.cjs && python tools/sablier-plates.py
const {chromium} = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const catalog = require('../src/sablier/scenes_catalog.json');
const DEVICES = {desktop: {viewport: {width: 1440, height: 900}, deviceScaleFactor: 1},
                 mobile: {viewport: {width: 390, height: 844}, deviceScaleFactor: 2}};
(async () => {
  const only = process.argv.find(arg => arg.startsWith('--only='))?.slice(7).split(',');
  const directory = path.resolve('.dist/sablier-plates');
  fs.mkdirSync(directory, {recursive: true});
  const browser = await chromium.launch({args: ['--enable-unsafe-swiftshader']});
  const report = [];
  for (const [device, options] of Object.entries(DEVICES)) {
    const page = await browser.newPage(options);
    const errors = [];
    page.on('pageerror', event => errors.push(event.message));
    // Le décompte n'apparaît pas sur la vue fixe, mais son horloge ferait avancer
    // l'univers entre deux images : on gèle l'animation avant le premier rendu.
    // Le gel suspend la boucle, il ne la coupe pas : le moteur rappelle `render` depuis
    // `render` lui-même, si bien qu'un appel simplement ignoré arrêterait le rendu pour
    // de bon — et l'univers suivant ne serait jamais construit.
    await page.addInitScript(() => {
      const raf = window.requestAnimationFrame.bind(window);
      window.requestAnimationFrame = fn => {
        const tick = time => (window.captureFrozen ? raf(tick) : fn(time));
        return raf(tick);
      };
    });
    await page.goto('http://127.0.0.1:8765/accounts/login/');
    await page.locator('#id_username').fill('browser-a');
    await page.locator('#id_password').fill('browser-test-only');
    await page.getByRole('button', {name: 'Se connecter', exact: true}).click();
    await page.goto('http://127.0.0.1:8765/sablier/');
    await page.evaluate(() => document.querySelector('#focus-app').classList.add('stage-mode'));
    // Seul l'univers est conservé : la vue fixe se pose sous l'interface vivante.
    await page.addStyleTag({content: '#focus-stage>*:not(.stage-3d-canvas){visibility:hidden!important}#focus-stage::after{display:none}'});
    for (const scene of catalog) {
      if (only && !only.includes(scene.decor)) continue;
      // Le sélecteur est dans la colonne masquée par l'immersion : on le pilote par
      // l'événement qu'il émettrait, plutôt que de rouvrir l'interface entre deux vues.
      await page.evaluate(key => {
        const select = document.querySelector('#ambience-select');
        select.value = key;
        select.dispatchEvent(new Event('change', {bubbles: true}));
      }, scene.key);
      await page.waitForFunction(decor => window.SablierWorld?.inspect().world === decor, scene.decor, {timeout: 120000});
      await page.waitForFunction(() => !window.SablierWorld.inspect().materialLoads, null, {timeout: 120000});
      await page.waitForTimeout(600);
      await page.evaluate(() => {window.captureFrozen = true;});
      const filename = `${device}-${scene.decor}.png`;
      await page.locator('.stage-3d-canvas').screenshot({path: path.join(directory, filename), timeout: 120000});
      const info = await page.evaluate(() => ({renderer: document.querySelector('#focus-app').dataset.renderer3d, stats: window.SablierWorld.inspect()}));
      if (info.renderer !== 'three' || errors.length) throw new Error(`Vue invalide : ${filename} ${info.renderer} ${errors}`);
      await page.evaluate(() => {window.captureFrozen = false;});
      report.push({device, world: scene.decor, filename, ...info});
      console.log(device, scene.decor, info.stats.triangles);
    }
    await page.close();
  }
  fs.writeFileSync(path.join(directory, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
})();
