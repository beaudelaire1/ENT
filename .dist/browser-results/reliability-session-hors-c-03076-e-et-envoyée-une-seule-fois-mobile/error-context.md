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
Error: browserContext.setOffline: Test timeout of 30000ms exceeded.
```

# Page snapshot

```yaml
- generic [ref=f2e1]:
  - link "Aller au contenu principal" [ref=f2e2] [cursor=pointer]:
    - /url: "#main-content"
  - complementary [aria-hidden] [ref=f2e3]:
    - generic [ref=f2e4]:
      - link [ref=f2e5] [cursor=pointer]:
        - /url: /dashboard/
        - generic [ref=f2e6]: M
        - generic [ref=f2e7]: MyENT
      - button [ref=f2e8]: ×
    - navigation [ref=f2e9]:
      - link [ref=f2e10] [cursor=pointer]:
        - /url: /dashboard/
        - text: Tableau de bord
      - group [ref=f2e11]:
        - generic [ref=f2e12] [cursor=pointer]: Planning ›
      - group [ref=f2e13]:
        - generic [ref=f2e14] [cursor=pointer]: Bibliothèque ›
      - group [ref=f2e15]:
        - generic [ref=f2e16] [cursor=pointer]: Formations ›
      - group [ref=f2e17]:
        - generic [ref=f2e18] [cursor=pointer]: Sablier ›
        - link [ref=f2e19] [cursor=pointer]:
          - /url: /sablier/
          - text: Minuteur
        - link [ref=f2e20] [cursor=pointer]:
          - /url: /sablier/sessions/
          - text: Historique
        - link [ref=f2e21] [cursor=pointer]:
          - /url: /sablier/audio/
          - text: Musiques
        - link [ref=f2e22] [cursor=pointer]:
          - /url: /sablier/playlists/
          - text: Playlists
    - generic [ref=f2e23]:
      - link [ref=f2e24] [cursor=pointer]:
        - /url: /notifications/
        - text: Notifications
      - link [ref=f2e25] [cursor=pointer]:
        - /url: /accounts/settings/
        - text: Paramètres
      - button [ref=f2e27] [cursor=pointer]: Déconnexion
  - button [aria-hidden]
  - generic [ref=f2e28]:
    - banner [ref=f2e29]:
      - button "Ouvrir le menu" [ref=f2e30]: ☰
      - searchbox "Rechercher" [ref=f2e32]
    - main [ref=f2e33]:
      - generic [ref=f2e34]:
        - generic [ref=f2e35]:
          - paragraph [ref=f2e37]: SABLIER / MYENT
          - generic [ref=f2e38]:
            - link "Historique" [ref=f2e39] [cursor=pointer]:
              - /url: /sablier/sessions/
            - button "Immersion ⛶" [ref=f2e40] [cursor=pointer]
        - generic [ref=f2e41]:
          - complementary [ref=f2e42]:
            - paragraph [ref=f2e43]: CONFIGURATION
            - heading "Votre session" [level=1] [ref=f2e44]
            - generic [ref=f2e45]:
              - text: INTENTION
              - textbox "INTENTION" [ref=f2e46]:
                - /placeholder: Réviser, créer, apprendre…
                - text: Hors connexion mobile
            - generic [ref=f2e47]: DURÉE
            - generic [ref=f2e48]:
              - textbox [ref=f2e49]: 00:02
              - button "OK" [ref=f2e50] [cursor=pointer]
            - generic [ref=f2e51]:
              - button "1m" [ref=f2e52] [cursor=pointer]
              - button "3m" [ref=f2e53] [cursor=pointer]
              - button "5m" [ref=f2e54] [cursor=pointer]
              - button "10m" [ref=f2e55] [cursor=pointer]
            - generic [ref=f2e56]: VISUALISATION
            - generic [ref=f2e57]:
              - button "◉ Anneau" [ref=f2e58] [cursor=pointer]:
                - text: ◉
                - generic [ref=f2e59]: Anneau
              - button "⌛ Sablier" [ref=f2e60] [cursor=pointer]:
                - text: ⌛
                - generic [ref=f2e61]: Sablier
              - button "≈ Marée" [ref=f2e62] [cursor=pointer]:
                - text: ≈
                - generic [ref=f2e63]: Marée
              - button "▯ Bougie" [ref=f2e64] [cursor=pointer]:
                - text: ▯
                - generic [ref=f2e65]: Bougie
              - button "⁘ Perles" [ref=f2e66] [cursor=pointer]:
                - text: ⁘
                - generic [ref=f2e67]: Perles
              - button "☾ Lune" [ref=f2e68] [cursor=pointer]:
                - text: ☾
                - generic [ref=f2e69]: Lune
              - button "▮ Colonnes" [ref=f2e70] [cursor=pointer]:
                - text: ▮
                - generic [ref=f2e71]: Colonnes
              - button "◠ Spirale" [ref=f2e72] [cursor=pointer]:
                - text: ◠
                - generic [ref=f2e73]: Spirale
              - button "☀ Soleil" [ref=f2e74] [cursor=pointer]:
                - text: ☀
                - generic [ref=f2e75]: Soleil
              - button "01 Digital" [ref=f2e76] [cursor=pointer]:
                - text: "01"
                - generic [ref=f2e77]: Digital
              - button "◎ Zen" [ref=f2e78] [cursor=pointer]:
                - text: ◎
                - generic [ref=f2e79]: Zen
            - generic [ref=f2e80]:
              - text: UNIVERS
              - combobox "UNIVERS" [ref=f2e81]:
                - option "Arbre des étoiles" [selected]
                - option "Refuge sous la pluie"
                - option "Forêt des origines"
                - option "Falaises de l'infini"
                - option "Observatoire des sables"
                - option "Vallée des aurores"
                - option "Odyssée stellaire"
                - option "Fleuve du Temps"
                - option "Sanctuaire abyssal"
            - generic [ref=f2e82]: IMMERSION
            - group "Niveau d’immersion" [ref=f2e83]:
              - button "Statique" [ref=f2e84] [cursor=pointer]
              - button "Léger" [ref=f2e85] [cursor=pointer]
              - button "Immersif" [pressed] [ref=f2e86] [cursor=pointer]
              - button "Cinématique" [ref=f2e87] [cursor=pointer]
            - generic [ref=f2e88]: DÉPOUILLEMENT
            - generic [ref=f2e89]:
              - button "1" [ref=f2e90]
              - button "2" [ref=f2e91]
              - button "3" [ref=f2e92]
            - generic [ref=f2e93]:
              - text: ALERTE FINALE
              - status "ALERTE FINALE 60" [ref=f2e94]: 60 s
              - slider [ref=f2e95]: "60"
            - generic [ref=f2e96]:
              - text: COMPÉTENCE TRAVAILLÉE
              - combobox "COMPÉTENCE TRAVAILLÉE" [ref=f2e97]:
                - option "Aucune · ne rien reporter" [selected]
                - option "Période de recette · Déjà maîtrisée"
                - option "Période de recette · À découvrir"
            - paragraph [ref=f2e98]: Le temps de la session sera ajouté au temps réel de cette compétence.
            - group [ref=f2e99]:
              - generic "Apparence et sauvegarde" [ref=f2e100] [cursor=pointer]
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
            - paragraph [ref=f2e101]: ESPACE · lecture / pauseR · reprise à zéro F11 · plein écran
          - generic [ref=f2e102]:
            - generic [ref=f2e103]:
              - generic [ref=f2e104]: ● SESSION TERMINÉE
              - generic [ref=f2e105]: ARBRE DES ÉTOILES · FOCUS 2
            - paragraph [ref=f2e106]: HORS CONNEXION MOBILE
            - generic [ref=f2e108]:
              - strong [ref=f2e109]: 00:00
              - text: COMPTE À REBOURS
            - status [ref=f2e111]: Session en attente de synchronisation. Nouvel essai au retour de la connexion.
            - button "Réessayer l’enregistrement" [ref=f2e112] [cursor=pointer]
        - generic [ref=f2e113]:
          - button "− 1 min" [ref=f2e114] [cursor=pointer]
          - button "↻ RECOMMENCER" [active] [ref=f2e115] [cursor=pointer]
          - button "↻ Réinitialiser" [ref=f2e116] [cursor=pointer]
          - button "+ 1 min" [ref=f2e117] [cursor=pointer]
        - generic [ref=f2e118]:
          - generic [ref=f2e119]:
            - paragraph [ref=f2e120]: PLAYLIST PERSONNELLE
            - strong [ref=f2e121]: Aucune playlist pour l’instant
          - paragraph [ref=f2e122]: Ajoutez vos musiques, puis réunissez-les en playlist pour accompagner vos sessions.
          - link "Ajouter des musiques" [ref=f2e123] [cursor=pointer]:
            - /url: /sablier/audio/
          - link "Créer une playlist" [ref=f2e124] [cursor=pointer]:
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
  32 |   const title = `Hors connexion ${testInfo.project.name}`;
  33 |   await page.locator('#session-intention').fill(title);
  34 |   await page.locator('#duration-input').fill('00:02');
  35 |   await page.locator('#apply-duration').click();
  36 |   await page.locator('#main-control').click();
  37 |   await context.setOffline(true);
  38 |   await expect(page.locator('#session-sync-status')).toContainText('attente');
  39 |   await context.setOffline(false);
  40 |   const receipt = page.waitForResponse(r => r.url().includes('/sessions/log/') && r.status() === 200);
> 41 |   await page.locator('#session-sync-retry').click();
     |                 ^ Error: browserContext.setOffline: Test timeout of 30000ms exceeded.
  42 |   const response = await receipt;
  43 |   const payload = response.request().postDataJSON();
  44 |   const token = await page.locator('#focus-app').getAttribute('data-csrf');
  45 |   await expect(page.locator('#session-sync-status')).toContainText('enregistrées');
  46 |   const duplicate = await page.request.post('/sablier/sessions/log/', {data: payload, headers: {'X-CSRFToken': token}});
  47 |   expect(duplicate.status()).toBe(200);
  48 |   await page.goto('/sablier/sessions/');
  49 |   await expect(page.locator('.list-row').filter({hasText: title})).toHaveCount(1);
  50 | });
  51 | 
  52 | test('reprise après fermeture et échéance pendant l’absence', async ({page, context}, testInfo) => {
  53 |   await page.goto('/sablier/?competency=1&duration=1');
  54 |   const title = `Reprise ${testInfo.project.name}`;
  55 |   await page.locator('#session-intention').fill(title);
  56 |   await page.locator('#duration-input').fill('00:02');
  57 |   await page.locator('#apply-duration').click();
  58 |   await page.locator('#main-control').click();
  59 |   await page.close();
  60 |   const resumed = await context.newPage();
  61 |   await resumed.goto('/sablier/');
  62 |   await expect(resumed.locator('#session-sync-status')).toContainText('enregistrées');
  63 |   await resumed.reload();
  64 |   await resumed.goto('/sablier/sessions/');
  65 |   await expect(resumed.locator('.list-row').filter({hasText: title})).toHaveCount(1);
  66 | });
  67 | 
```