// Local demo server: .venv/Scripts/python.exe tests/browser/server.py
const {chromium} = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const catalog = require('../src/sablier/scenes_catalog.json');
(async () => {
  const phase = process.argv[2] || 'after';
  const all = process.argv.includes('--all');
  const objects=process.argv.includes('--objects');
  const filter=process.argv.find(arg=>arg.startsWith('--only='))?.slice(7).split(',');
  const directory = path.resolve('.dist/sablier-review', phase);
  fs.mkdirSync(directory, {recursive:true});
  const browser = await chromium.launch({args:['--enable-unsafe-swiftshader']});
  const report = [];
  for (const [device, viewport] of Object.entries({desktop:{width:1440,height:900}, mobile:{width:390,height:844}})) {
    const page = await browser.newPage({viewport, deviceScaleFactor:1});
    let selected;
    await page.route('**/sablier/',async route=>{
      const response=await route.fetch();
      let body=await response.text();
      if(selected)body=body.replace(/data-ambience="[^"]*"(?= data-warning)/,`data-ambience="${selected.key}"`).replace('class="focus-app"','class="focus-app stage-mode"');
      if(selected?.mode)body=body.replace(/data-mode="[^"]*"/,`data-mode="${selected.mode}"`);
      await route.fulfill({response,body});
    });
    if(phase==='before')await page.route(/\/static\/sablier\/.*\.(js|css)(\?|$)/,async route=>{
      const relative=decodeURIComponent(new URL(route.request().url()).pathname).replace('/static/','src/static/');
      try { const body=execFileSync('git',['show',`45437122:${relative}`],{maxBuffer:8*1024*1024});
        await route.fulfill({body,contentType:relative.endsWith('.js')?'text/javascript':'text/css'});
      } catch {await route.continue();}
    });
    await page.addInitScript(() => { const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = fn => raf(t => { if (!window.captureFrozen) fn(t); }); });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:8765/accounts/login/');
    await page.locator('#id_username').fill('browser-a');
    await page.locator('#id_password').fill('browser-test-only');
    await page.getByRole('button',{name:'Se connecter',exact:true}).click();
    const scenes = objects ? ['ring','hourglass','wave','candle','beads','moon','bars','spiral','sun','digital','zen'].map(mode=>({...catalog.find(s=>s.decor==='rain_refuge'),mode}))
      : all ? catalog : catalog.filter(s=>['rain_refuge','ancient_forest','ocean_cliffs','interstellar'].includes(s.decor));
    for (const scene of scenes) {
      if(filter&&!filter.includes(scene.mode||scene.decor))continue;
      selected=scene;
      await page.evaluate(()=>localStorage.clear());
      await page.goto('http://127.0.0.1:8765/sablier/');
      await page.waitForFunction(() => ['three','fallback'].includes(document.querySelector('#focus-app').dataset.renderer3d),null,{timeout:120000});
      await page.waitForFunction(() => !Number(document.querySelector('#focus-app').dataset.materialLoads||0),null,{timeout:120000});
      await page.waitForTimeout(800);
      const filename = `${device}-${scene.mode||scene.decor}.png`;
      await page.evaluate(() => {window.captureFrozen=true;});
      await page.screenshot({path:path.join(directory,filename),timeout:120000});
      if(all) {
        await page.addStyleTag({content:'#focus-stage>*:not(.stage-3d-canvas){visibility:hidden!important}#focus-stage::after{display:none}'});
        await page.screenshot({path:path.join(directory,`${device}-${scene.decor}-world.png`),timeout:120000});
      }
      const info = await page.evaluate(()=>({renderer:document.querySelector('#focus-app').dataset.renderer3d,reason:document.querySelector('#focus-app').dataset.renderer3dReason,stats:window.SablierWorld?.inspect()}));
      report.push({device,scene:scene.key,filename,...info,errors:[...errors]});
      if(info.renderer!=='three'||errors.length)throw new Error(`Capture invalide : ${filename} ${JSON.stringify(info)} ${errors}`);
      console.log(device,scene.decor,info.renderer);
    }
    await page.close();
  }
  fs.writeFileSync(path.join(directory,'report.json'),JSON.stringify(report,null,2));
  await browser.close();
})();

