const base=require('./playwright.config.cjs');
module.exports={...base,testMatch:'worlds.spec.cjs',testIgnore:[],timeout:90000,
  reporter:[['list'],['json',{outputFile:'.dist/sablier-review/browser-worlds.json'}]],
  expect:{timeout:20000},
  use:{...base.use,launchOptions:{args:['--enable-unsafe-swiftshader']}},
  webServer:{...base.webServer,reuseExistingServer:process.env.MYENT_REUSE_BROWSER_SERVER==='1'},
};
