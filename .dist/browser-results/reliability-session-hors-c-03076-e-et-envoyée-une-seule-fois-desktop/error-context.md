# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: reliability.spec.cjs >> session hors connexion conservée et envoyée une seule fois
- Location: tests\browser\reliability.spec.cjs:30:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.fill: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('#duration-input')
    - locator resolved to <input value="05:00" id="duration-input" inputmode="numeric"/>
    - fill("00:02")
  - attempting fill action
    - waiting for element to be visible, enabled and editable

```

# Page snapshot

```yaml
- generic [ref=f2e1]:
  - link "Aller au contenu principal" [ref=f2e2] [cursor=pointer]:
    - /url: "#main-content"
  - complementary "Volet de navigation" [ref=f2e3]:
    - link "M MyENT" [ref=f2e5] [cursor=pointer]:
      - /url: /dashboard/
      - generic [ref=f2e6]: M
      - generic [ref=f2e7]: MyENT
    - navigation "Navigation principale" [ref=f2e8]:
      - link "Tableau de bord" [ref=f2e9] [cursor=pointer]:
        - /url: /dashboard/
      - group [ref=f2e10]:
        - generic "Planning ›" [ref=f2e11] [cursor=pointer]
      - group [ref=f2e12]:
        - generic "Bibliothèque ›" [ref=f2e13] [cursor=pointer]
      - group [ref=f2e14]:
        - generic "Formations ›" [ref=f2e15] [cursor=pointer]
      - group [ref=f2e16]:
        - generic "Sablier ›" [ref=f2e17] [cursor=pointer]
        - link "Minuteur" [ref=f2e18] [cursor=pointer]:
          - /url: /sablier/
        - link "Historique" [ref=f2e19] [cursor=pointer]:
          - /url: /sablier/sessions/
        - link "Musiques" [ref=f2e20] [cursor=pointer]:
          - /url: /sablier/audio/
        - link "Playlists" [ref=f2e21] [cursor=pointer]:
          - /url: /sablier/playlists/
    - generic [ref=f2e22]:
      - link "Notifications" [ref=f2e23] [cursor=pointer]:
        - /url: /notifications/
      - link "Paramètres" [ref=f2e24] [cursor=pointer]:
        - /url: /accounts/settings/
      - button "Déconnexion" [ref=f2e26] [cursor=pointer]
  - generic [ref=f2e27]:
    - banner [ref=f2e28]:
      - searchbox "Rechercher" [ref=f2e30]
      - generic [ref=f2e31]: browser-a
    - main [ref=f2e32]:
      - generic [ref=f2e33]:
        - generic [ref=f2e34]:
          - generic [ref=f2e35]:
            - paragraph [ref=f2e36]: SABLIER / MYENT
            - paragraph [ref=f2e37]: Votre temps. Votre univers.
          - generic [ref=f2e38]:
            - link "Historique" [ref=f2e39] [cursor=pointer]:
              - /url: /sablier/sessions/
            - generic [ref=f2e40]: ● PRÊT
            - button "Immersion ⛶" [ref=f2e41] [cursor=pointer]
        - generic [ref=f2e42]:
          - complementary [ref=f2e43]:
            - paragraph [ref=f2e44]: CONFIGURATION
            - heading "Votre session" [level=1] [ref=f2e45]
            - generic [ref=f2e46]:
              - text: INTENTION
              - textbox "INTENTION" [active] [ref=f2e47]:
                - /placeholder: Réviser, créer, apprendre…
                - text: Hors connexion desktop
            - generic [ref=f2e48]: DURÉE
            - generic [ref=f2e49]:
              - textbox [ref=f2e50]: 05:00
              - button "OK" [ref=f2e51] [cursor=pointer]
            - generic [ref=f2e52]:
              - button "1m" [ref=f2e53] [cursor=pointer]
              - button "3m" [ref=f2e54] [cursor=pointer]
              - button "5m" [ref=f2e55] [cursor=pointer]
              - button "10m" [ref=f2e56] [cursor=pointer]
            - generic [ref=f2e57]: VISUALISATION
            - generic [ref=f2e58]:
              - button "◉ Anneau" [ref=f2e59] [cursor=pointer]:
                - text: ◉
                - generic [ref=f2e60]: Anneau
              - button "⌛ Sablier" [ref=f2e61] [cursor=pointer]:
                - text: ⌛
                - generic [ref=f2e62]: Sablier
              - button "≈ Marée" [ref=f2e63] [cursor=pointer]:
                - text: ≈
                - generic [ref=f2e64]: Marée
              - button "▯ Bougie" [ref=f2e65] [cursor=pointer]:
                - text: ▯
                - generic [ref=f2e66]: Bougie
              - button "⁘ Perles" [ref=f2e67] [cursor=pointer]:
                - text: ⁘
                - generic [ref=f2e68]: Perles
              - button "☾ Lune" [ref=f2e69] [cursor=pointer]:
                - text: ☾
                - generic [ref=f2e70]: Lune
              - button "▮ Colonnes" [ref=f2e71] [cursor=pointer]:
                - text: ▮
                - generic [ref=f2e72]: Colonnes
              - button "◠ Spirale" [ref=f2e73] [cursor=pointer]:
                - text: ◠
                - generic [ref=f2e74]: Spirale
              - button "☀ Soleil" [ref=f2e75] [cursor=pointer]:
                - text: ☀
                - generic [ref=f2e76]: Soleil
              - button "01 Digital" [ref=f2e77] [cursor=pointer]:
                - text: "01"
                - generic [ref=f2e78]: Digital
              - button "◎ Zen" [ref=f2e79] [cursor=pointer]:
                - text: ◎
                - generic [ref=f2e80]: Zen
            - generic [ref=f2e81]:
              - text: UNIVERS
              - combobox "UNIVERS" [ref=f2e82]:
                - option "Arbre des étoiles" [selected]
                - option "Refuge sous la pluie"
                - option "Forêt des origines"
                - option "Falaises de l'infini"
                - option "Observatoire des sables"
                - option "Vallée des aurores"
                - option "Odyssée stellaire"
                - option "Fleuve du Temps"
                - option "Sanctuaire abyssal"
            - generic [ref=f2e83]: IMMERSION
            - group "Niveau d’immersion" [ref=f2e84]:
              - button "Statique" [ref=f2e85] [cursor=pointer]
              - button "Léger" [ref=f2e86] [cursor=pointer]
              - button "Immersif" [pressed] [ref=f2e87] [cursor=pointer]
              - button "Cinématique" [ref=f2e88] [cursor=pointer]
            - generic [ref=f2e89]: DÉPOUILLEMENT
            - generic [ref=f2e90]:
              - button "1" [ref=f2e91]
              - button "2" [ref=f2e92]
              - button "3" [ref=f2e93]
            - generic [ref=f2e94]:
              - text: ALERTE FINALE
              - status "ALERTE FINALE 60" [ref=f2e95]: 60 s
              - slider [ref=f2e96]: "60"
            - generic [ref=f2e97]:
              - text: COMPÉTENCE TRAVAILLÉE
              - combobox "COMPÉTENCE TRAVAILLÉE" [ref=f2e98]:
                - option "Aucune · ne rien reporter" [selected]
                - option "Période de recette · Déjà maîtrisée"
                - option "Période de recette · À découvrir"
            - paragraph [ref=f2e99]: Le temps de la session sera ajouté au temps réel de cette compétence.
            - group [ref=f2e100]:
              - generic "Apparence et sauvegarde" [ref=f2e101] [cursor=pointer]
              - option "Anneau"
              - option "Sablier"
              - option "Marée"
              - option "Bougie"
              - option "Perles"
              - option "Lune"
              - option "Colonnes"
              - option "Spirale"
              - option "Soleil"
              - option "Digital" [selected]
              - option "Zen"
              - option "Arbre des étoiles" [selected]
              - option "Refuge sous la pluie"
              - option "Forêt des origines"
              - option "Falaises de l'infini"
              - option "Observatoire des sables"
              - option "Vallée des aurores"
              - option "Odyssée stellaire"
              - option "Fleuve du Temps"
              - option "Sanctuaire abyssal"
              - option "Statique"
              - option "Léger"
              - option "Immersif" [selected]
              - option "Cinématique"
            - paragraph [ref=f2e102]: ESPACE · lecture / pauseR · reprise à zéro F11 · plein écran
          - generic [ref=f2e103]:
            - generic [ref=f2e104]:
              - generic [ref=f2e105]: ● PRÊT
              - generic [ref=f2e106]: ARBRE DES ÉTOILES · FOCUS 2
            - paragraph [ref=f2e107]: HORS CONNEXION DESKTOP
            - generic [ref=f2e109]:
              - strong [ref=f2e110]: 05:00
              - text: COMPTE À REBOURS
            - status
        - generic [ref=f2e112]:
          - button "− 1 min" [ref=f2e113] [cursor=pointer]
          - button "▶ DÉMARRER" [ref=f2e114] [cursor=pointer]
          - button "↻ Réinitialiser" [ref=f2e115] [cursor=pointer]
          - button "+ 1 min" [ref=f2e116] [cursor=pointer]
        - generic [ref=f2e117]:
          - generic [ref=f2e118]:
            - paragraph [ref=f2e119]: PLAYLIST PERSONNELLE
            - strong [ref=f2e120]: Aucune playlist pour l’instant
          - paragraph [ref=f2e121]: Ajoutez vos musiques, puis réunissez-les en playlist pour accompagner vos sessions.
          - link "Ajouter des musiques" [ref=f2e122] [cursor=pointer]:
            - /url: /sablier/audio/
          - link "Créer une playlist" [ref=f2e123] [cursor=pointer]:
            - /url: /sablier/playlists/new/
```

# Test source

```ts
  1  | const {test, expect} = require('@playwright/test');
  2  | 
  3  | test.beforeEach(async ({page}) => {
  4  |   await page.goto('/accounts/login/');
  5  |   await page.locator('#id_username').fill('browser-a');
  6  |   await page.locator('#id_password').fill('browser-test-only');
  7  |   await page.getByRole('button', {name: 'Se connecter', exact: true}).click();
  8  |   await expect(page).toHaveURL(/dashboard/);
  9  | });
  10 | 
  11 | test('progression et jour local sont cohérents', async ({page}) => {
  12 |   await expect(page.locator('#academic-progress')).toHaveAttribute('value', '50');
  13 |   await page.goto('/agenda/?view=week&date=2026-09-07');
  14 |   await expect(page.locator('.week-day').first()).toContainText('Lundi soir');
  15 |   await expect(page.locator('.week-day').nth(1)).not.toContainText('Lundi soir');
  16 | });
  17 | 
  18 | test('un échec de disposition reste visible puis peut être réessayé', async ({page}) => {
  19 |   await page.route('**/dashboard/layout/', route => route.fulfill({status: 500}));
  20 |   const move = page.locator('[data-move-widget="down"]').first();
  21 |   await move.focus();
  22 |   await page.keyboard.press('Enter');
  23 |   await expect(page.locator('#layout-status')).toContainText('non enregistrée');
  24 |   await page.unroute('**/dashboard/layout/');
  25 |   await page.getByText('Personnaliser', {exact: true}).click();
  26 |   await page.getByRole('button', {name: 'Appliquer', exact: true}).click();
  27 |   await expect(page.locator('#layout-status')).toBeEmpty();
  28 | });
  29 | 
  30 | test('session hors connexion conservée et envoyée une seule fois', async ({page, context}, testInfo) => {
  31 |   await page.goto('/sablier/');
  32 |   await page.clock.install();
  33 |   const title = `Hors connexion ${testInfo.project.name}`;
  34 |   await page.locator('#session-intention').fill(title);
> 35 |   await page.locator('#duration-input').fill('00:02');
     |                                         ^ Error: locator.fill: Test timeout of 30000ms exceeded.
  36 |   await page.locator('#apply-duration').click();
  37 |   await page.locator('#main-control').click();
  38 |   await context.setOffline(true);
  39 |   await page.clock.fastForward(3000);
  40 |   await expect(page.locator('#session-sync-status')).toContainText('attente');
  41 |   await context.setOffline(false);
  42 |   const receipt = page.waitForResponse(r => r.url().includes('/sessions/log/') && r.status() === 200);
  43 |   await page.locator('#session-sync-retry').click();
  44 |   const response = await receipt;
  45 |   const payload = response.request().postDataJSON();
  46 |   const token = await page.locator('#focus-app').getAttribute('data-csrf');
  47 |   await expect(page.locator('#session-sync-status')).toContainText('enregistrées');
  48 |   const duplicate = await page.request.post('/sablier/sessions/log/', {data: payload, headers: {'X-CSRFToken': token}});
  49 |   expect(duplicate.status()).toBe(200);
  50 |   await page.goto('/sablier/sessions/');
  51 |   await expect(page.locator('.list-row').filter({hasText: title})).toHaveCount(1);
  52 | });
  53 | 
  54 | test('reprise après fermeture et échéance pendant l’absence', async ({page, context}, testInfo) => {
  55 |   await page.goto('/sablier/?competency=1&duration=1');
  56 |   const title = `Reprise ${testInfo.project.name}`;
  57 |   await page.locator('#session-intention').fill(title);
  58 |   await page.locator('#duration-input').fill('00:02');
  59 |   await page.locator('#apply-duration').click();
  60 |   await page.locator('#main-control').click();
  61 |   await page.close();
  62 |   const resumed = await context.newPage();
  63 |   await resumed.clock.install({time: new Date(Date.now() + 4000)});
  64 |   await resumed.goto('/sablier/');
  65 |   await expect(resumed.locator('#session-sync-status')).toContainText('enregistrées');
  66 |   await resumed.reload();
  67 |   await resumed.goto('/sablier/sessions/');
  68 |   await expect(resumed.locator('.list-row').filter({hasText: title})).toHaveCount(1);
  69 | });
  70 | 
```