const {defineConfig, devices} = require('@playwright/test');
const fs = require('node:fs');
const python = process.env.MYENT_PYTHON || (fs.existsSync('.venv/Scripts/python.exe') ? '.venv/Scripts/python.exe' : 'python');
module.exports = defineConfig({
  testDir: './tests/browser', timeout: 30000, workers: 1,
  testIgnore: 'worlds.spec.cjs',
  outputDir: '.dist/browser-results', reporter: 'list',
  use: {baseURL: 'http://127.0.0.1:8765', trace: 'retain-on-failure', screenshot: 'only-on-failure',
    launchOptions: {args: ['--disable-webgl']}},
  projects: [
    {name: 'desktop', use: {...devices['Desktop Chrome']}},
    {name: 'mobile', use: {...devices['Pixel 7']}},
  ],
  webServer: {
    command: `"${python}" tests/browser/server.py`,
    url: 'http://127.0.0.1:8765/livez/', reuseExistingServer: process.env.MYENT_REUSE_BROWSER_SERVER === '1', timeout: 120000,
  },
});
