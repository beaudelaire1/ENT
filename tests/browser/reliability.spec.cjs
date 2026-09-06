const {test, expect} = require('@playwright/test');

test.beforeEach(async ({page}) => {
  await page.goto('/accounts/login/');
  await page.locator('#id_username').fill('browser-a');
  await page.locator('#id_password').fill('browser-test-only');
  await page.getByRole('button', {name: 'Se connecter', exact: true}).click();
  await expect(page).toHaveURL(/dashboard/);
});

test('progression et jour local sont cohérents', async ({page}) => {
  await expect(page.locator('#academic-progress')).toHaveAttribute('value', '50');
  await page.goto('/agenda/?view=week&date=2026-09-07');
  await expect(page.locator('.week-day').first()).toContainText('Lundi soir');
  await expect(page.locator('.week-day').nth(1)).not.toContainText('Lundi soir');
});

test('un échec de disposition reste visible puis peut être réessayé', async ({page}) => {
  await page.route('**/dashboard/layout/', route => route.fulfill({status: 500}));
  const move = page.locator('[data-move-widget="down"]').first();
  await move.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#layout-status')).toContainText('non enregistrée');
  await page.unroute('**/dashboard/layout/');
  await page.getByText('Personnaliser', {exact: true}).click();
  await page.getByRole('button', {name: 'Appliquer', exact: true}).click();
  await expect(page.locator('#layout-status')).toBeEmpty();
});

test('session hors connexion conservée et envoyée une seule fois', async ({page, context}, testInfo) => {
  await page.goto('/sablier/');
  const title = `Hors connexion ${testInfo.project.name}`;
  await page.locator('#session-intention').fill(title);
  await page.locator('#duration-input').fill('00:02');
  await page.locator('#apply-duration').click();
  await page.locator('#main-control').click();
  await context.setOffline(true);
  await expect(page.locator('#session-sync-status')).toContainText('attente');
  await context.setOffline(false);
  const receipt = page.waitForResponse(r => r.url().includes('/sessions/log/') && r.status() === 200);
  await page.locator('#session-sync-retry').click();
  const response = await receipt;
  const payload = response.request().postDataJSON();
  const token = await page.locator('#focus-app').getAttribute('data-csrf');
  await expect(page.locator('#session-sync-status')).toContainText('enregistrées');
  const duplicate = await page.request.post('/sablier/sessions/log/', {data: payload, headers: {'X-CSRFToken': token}});
  expect(duplicate.status()).toBe(200);
  await page.goto('/sablier/sessions/');
  await expect(page.locator('.list-row').filter({hasText: title})).toHaveCount(1);
});

test('reprise après fermeture et échéance pendant l’absence', async ({page, context}, testInfo) => {
  await page.goto('/sablier/?competency=1&duration=1');
  const title = `Reprise ${testInfo.project.name}`;
  await page.locator('#session-intention').fill(title);
  await page.locator('#duration-input').fill('00:02');
  await page.locator('#apply-duration').click();
  await page.locator('#main-control').click();
  await page.close();
  const resumed = await context.newPage();
  await resumed.goto('/sablier/');
  await expect(resumed.locator('#session-sync-status')).toContainText('enregistrées');
  await resumed.reload();
  await resumed.goto('/sablier/sessions/');
  await expect(resumed.locator('.list-row').filter({hasText: title})).toHaveCount(1);
});
