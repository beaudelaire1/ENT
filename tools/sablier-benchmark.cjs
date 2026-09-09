const {chromium}=require('@playwright/test');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({args:['--enable-unsafe-swiftshader']});
  const results=[];
  for(const viewport of [{width:1440,height:900},{width:390,height:844}]) {
    const page=await browser.newPage({viewport,deviceScaleFactor:1});
    await page.goto('http://127.0.0.1:8765/accounts/login/');await page.locator('#id_username').fill('browser-a');await page.locator('#id_password').fill('browser-test-only');await page.getByRole('button',{name:'Se connecter',exact:true}).click();
    await page.goto('http://127.0.0.1:8765/sablier/');await page.waitForFunction(()=>window.SablierWorld);
    for(const key of ['refuge_pluie','foret','ocean','interstellaire']) {
      const start=Date.now();await page.locator('#ambience-select').selectOption(key);
      await page.waitForFunction(key=>document.querySelector('#focus-app').dataset.ambience===key&&window.SablierWorld.inspect().world===JSON.parse(document.querySelector('#decor-data').textContent)[key],key);
      await page.waitForFunction(()=>window.SablierWorld.inspect().materialLoads===0);
      const switchMs=Date.now()-start;
      await page.locator('[data-decor="2"]').click();await page.waitForTimeout(1500);
      const first=await page.evaluate(()=>({at:performance.now(),...window.SablierWorld.inspect()}));
      await page.waitForTimeout(4000);
      const last=await page.evaluate(()=>({at:performance.now(),...window.SablierWorld.inspect()}));
      results.push({viewport,key,switchMs,measuredSeconds:(last.at-first.at)/1000,frames:last.renders-first.renders,
        renderedFps:Math.round((last.renders-first.renders)*10000/(last.at-first.at))/10,...last});
      console.log(viewport.width,key,results.at(-1).renderedFps);
    }
    await page.close();
  }
  fs.mkdirSync('.dist/sablier-review',{recursive:true});fs.writeFileSync('.dist/sablier-review/performance.json',JSON.stringify({browser:browser.version(),results},null,2));
  await browser.close();
})();
