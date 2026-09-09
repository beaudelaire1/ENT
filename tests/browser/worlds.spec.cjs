const {test,expect}=require('@playwright/test');
const catalog=require('../../src/sablier/scenes_catalog.json');
const fs=require('node:fs');
const path=require('node:path');
const errors=[];
test.beforeEach(async({page})=>{
  errors.length=0;page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/accounts/login/');
  await page.locator('#id_username').fill('browser-a');await page.locator('#id_password').fill('browser-test-only');
  await page.getByRole('button',{name:'Se connecter',exact:true}).click();
  await page.goto('/sablier/');
  await expect(page.locator('#focus-app')).toHaveAttribute('data-renderer3d','three');
});
test.afterEach(()=>expect(errors).toEqual([]));
async function world(page,scene){
  await page.locator('#ambience-select').selectOption(scene.key);
  await expect.poll(()=>page.evaluate(()=>window.SablierWorld.inspect().world),{timeout:20000}).toBe(scene.decor);
  await expect.poll(()=>page.evaluate(()=>window.SablierWorld.inspect().materialLoads),{timeout:30000}).toBe(0);
  await page.waitForTimeout(150);
}

test('quatre lieux : pixels immobiles, horloge active et réduction dynamique',async({page})=>{
  for(const key of ['refuge_pluie','foret','ocean','interstellaire']) {
    await world(page,catalog.find(s=>s.key===key));
    await page.locator('[data-decor="0"]').click();
    const canvas=page.locator('.stage-3d-canvas');
    const before=await canvas.screenshot();
    const first=await page.evaluate(()=>window.SablierWorld.inspect());
    await page.waitForTimeout(250);
    expect(await canvas.screenshot()).toEqual(before);
    expect((await page.evaluate(()=>window.SablierWorld.inspect())).worldTime).toBe(first.worldTime);
  }
  await page.locator('#duration-input').fill('00:15');await page.locator('#apply-duration').click();
  await page.locator('#main-control').click();
  await expect(page.locator('#digital-time')).not.toHaveText('00:15');
  await page.reload();await expect(page.locator('#main-control')).toContainText('PAUSE');
  await page.locator('#main-control').click();
  await world(page,catalog.find(s=>s.key==='refuge_pluie'));
  await page.locator('[data-decor="2"]').click();
  await expect.poll(()=>page.evaluate(()=>window.SablierWorld.inspect().worldTime)).toBeGreaterThan(0);
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect.poll(()=>page.evaluate(()=>window.SablierWorld.inspect().motion)).toBe(0);
  const frozen=await page.evaluate(()=>window.SablierWorld.inspect());
  await page.waitForTimeout(350);
  const later=await page.evaluate(()=>window.SablierWorld.inspect());
  expect(later.worldTime).toBe(frozen.worldTime);expect(later.camera).toEqual(frozen.camera);
});

test('galerie clavier, favoris et commandes pendant l’immersion',async({page})=>{
  await page.locator('.world-picker summary').click();
  await expect(page.locator('[data-world-choice]')).toHaveCount(24);
  const first=page.locator('[data-world-choice]').first();await first.focus();await page.keyboard.press('ArrowRight');
  await expect(page.locator('[data-world-choice]').nth(1)).toBeFocused();await page.keyboard.press('Enter');
  await expect(page.locator('#focus-app')).toHaveAttribute('data-ambience',catalog[1].key);
  await page.locator('[data-favorite]').nth(1).click();await page.locator('#world-filter').selectOption('favorites');
  await expect(page.locator('[data-world-card]:visible')).toHaveCount(1);
  await page.reload();await page.locator('.world-picker summary').click();await page.locator('#world-filter').selectOption('favorites');
  await expect(page.locator('[data-world-card]:visible')).toHaveCount(1);
  await page.locator('#scene-button').click();await expect(page.locator('#immersion-pause')).toBeVisible();
  await page.locator('#immersion-pause').click();await expect(page.locator('#immersion-pause')).toContainText('Pause');
  await page.locator('#scene-button').click();await expect(page.locator('#main-control')).toBeVisible();
});

test('24 univers et onze visualisations ; ressources bornées après deux parcours',async({page},testInfo)=>{
  test.setTimeout(360000);
  const samples=[];
  for(let pass=0;pass<2;pass++)for(const scene of catalog){
    await world(page,scene);
    samples.push({pass,...await page.evaluate(()=>window.SablierWorld.inspect())});
  }
  for(let i=0;i<24;i++){
    expect(samples[i+24].geometries).toBeLessThanOrEqual(samples[i].geometries+3);
    // Le cache partagé de textures est rempli au premier parcours, puis borné.
    expect(samples[i+24].textures).toBeLessThanOrEqual(Math.max(...samples.slice(0,24).map(s=>s.textures))+3);
  }
  for(const mode of ['ring','hourglass','wave','candle','beads','moon','bars','spiral','sun','digital','zen']){
    await page.locator(`.mode-grid [data-mode="${mode}"]`).click();
    await expect(page.locator('#visual-wrap')).toHaveAttribute('data-mode',mode);
    await expect(page.locator('#focus-app')).toHaveAttribute('data-renderer3d','three');
  }
  await testInfo.attach('resources.json',{body:JSON.stringify(samples,null,2),contentType:'application/json'});
});

test('bougeoir conservé et sable transféré lors des reprises aux différents niveaux',async({page},testInfo)=>{
  test.setTimeout(180000);
  await world(page,catalog.find(s=>s.key==='refuge_pluie'));
  const measures=[];
  for(const mode of ['candle','hourglass'])for(const progress of [1,.5,0]) {
    await page.evaluate(({mode,progress})=>{
      const app=document.querySelector('#focus-app'),key=`myent:sablier:${app.dataset.user}`;
      const state=JSON.parse(localStorage.getItem(key));
      Object.assign(state,{mode,total:300,remaining:300*progress,running:false,finished:progress===0});
      localStorage.setItem(key,JSON.stringify(state));
    },{mode,progress});
    await page.reload();await expect(page.locator('#focus-app')).toHaveAttribute('data-renderer3d','three');
    await expect(page.locator('#visual-wrap')).toHaveAttribute('data-mode',mode);
    await page.waitForFunction(mode=>performance.getEntriesByName(new URL(JSON.parse(document.querySelector('#asset-data').textContent)[mode],location.href).href).length,mode);
    await page.waitForTimeout(200);
    const pixels=await page.evaluate(()=>{
      const c=document.querySelector('#timer-canvas'),ctx=c.getContext('2d'),w=c.width,h=c.height;
      const strip=ctx.getImageData(0,Math.floor(h*.8),w,Math.max(1,Math.floor(h*.07))).data;
      let hash=0;for(const value of strip)hash=(Math.imul(hash,31)+value)|0;
      const data=ctx.getImageData(0,Math.floor(h*.5),w,Math.floor(h*.34)).data;
      let gold=0;for(let i=0;i<data.length;i+=4)if(data[i]>100&&data[i]>data[i+1]*1.05&&data[i+1]>data[i+2]*1.25&&data[i+3]>100)gold++;
      return {hash,gold};
    });
    measures.push({mode,progress,...pixels});
    const body=await page.locator('#focus-stage').screenshot();
    const directory=path.resolve('.dist/sablier-review/progress');fs.mkdirSync(directory,{recursive:true});
    fs.writeFileSync(path.join(directory,`${testInfo.project.name}-${mode}-${progress}.png`),body);
    await testInfo.attach(`${mode}-${progress}.png`,{body,contentType:'image/png'});
  }
  expect(measures[1].hash).toBe(measures[0].hash);expect(measures[2].hash).toBe(measures[0].hash);
  expect(measures[5].gold).toBeGreaterThan(measures[3].gold);
});

test('veille du rendu et reprise de l’échéance (événement de visibilité simulé)',async({page})=>{
  await page.locator('#duration-input').fill('00:20');await page.locator('#apply-duration').click();await page.locator('#main-control').click();
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'));});
  const before=await page.evaluate(()=>window.SablierWorld.inspect());await page.waitForTimeout(1300);
  expect((await page.evaluate(()=>window.SablierWorld.inspect())).renders).toBe(before.renders);
  await page.evaluate(()=>{delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));});
  await expect(page.locator('#digital-time')).not.toHaveText('00:20');
});

test('perte du contexte : vue locale identifiable et minuteur utilisable',async({page})=>{
  await world(page,catalog.find(s=>s.key==='refuge_pluie'));
  await page.evaluate(()=>document.querySelector('.stage-3d-canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
  await expect(page.locator('#focus-app')).toHaveAttribute('data-renderer3d','fallback');
  await expect(page.locator('#focus-app')).toHaveAttribute('data-renderer3d-reason','context-lost');
  await expect(page.locator('#world-fallback')).toBeVisible();
  await page.waitForFunction(()=>document.querySelector('#world-fallback').naturalWidth>0);
  await page.locator('#ambience-select').selectOption('ocean');
  await expect(page.locator('#world-fallback')).toHaveAttribute('src',/ocean_cliffs(-wide|-mobile)\.webp\?v=/);
  await page.locator('#duration-input').fill('00:05');await page.locator('#apply-duration').click();await page.locator('#main-control').click();
  await expect(page.locator('#digital-time')).not.toHaveText('00:05');
});
