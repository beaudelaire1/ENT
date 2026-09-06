(() => {
  const source = document.currentScript?.src;
  if (!source) return;
  const here = new URL(source);
  const version = here.search;
  const load = (name) => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = new URL(name + version, here).href;
    script.onload = resolve;
    script.onerror = reject;
    document.head.append(script);
  });

  const nativeStyles = document.createElement("link");
  nativeStyles.rel = "stylesheet";
  nativeStyles.href = new URL("premium3d/native-modes.css" + version, here).href;
  document.head.append(nativeStyles);

  const stub = {
    names: [],
    backdrops: [],
    create(canvas) {
      let implementation = null;
      let queuedUse = null;
      const proxy = {
        use(...args) {
          if (implementation) implementation.use(...args);
          else queuedUse = args;
        },
        frame(...args) {
          implementation?.frame(...args);
        },
        inspect() {
          return implementation?.inspect?.() || { name: null, particles: 0, scenery: 0, motion: 0 };
        },
      };
      window.SablierDecorReady.then(() => {
        const engine = window.SablierDecor;
        if (!engine || engine === stub) return;
        implementation = engine.create(canvas);
        if (queuedUse) implementation.use(...queuedUse);
      });
      return proxy;
    },
  };

  window.SablierDecor = stub;

  // Le lieu est rendu en volume par `premium3d.js`, dans un seul contexte WebGL ; le décor
  // peint n'est que son repli. Trois états, et un seul basculement visible :
  //
  //   booting  — personne n'est encore en charge. Rien du lieu ne s'affiche.
  //   three    — la scène a sa première image et prend le lieu.
  //   fallback — la 3D est hors jeu ; le décor peint apparaît, avec le motif de l'échec.
  //
  // Poser `booting` ici, avant tout rendu, est ce qui empêche le décor peint de s'afficher
  // pendant la construction du lieu — c'est cet affichage-là qui donnait l'impression que
  // « les anciennes vues reviennent » à chaque ouverture de page.
  const app = document.querySelector("#focus-app");
  if (app) app.dataset.renderer3d = "booting";
  // Ne renonce que si personne n'a encore tranché : un échec tardif ne doit pas effacer
  // une scène qui rend déjà.
  const giveUp = (reason) => {
    if (app?.dataset.renderer3d !== "booting") return;
    app.dataset.renderer3d = "fallback";
    app.dataset.renderer3dReason = reason;
  };

  // Un démarrage muet ne doit jamais devenir un écran vide définitif : si aucune image
  // n'est venue au bout de ce délai, le repli prend la main de lui-même.
  setTimeout(() => giveUp("slow-start"), 8000);

  window.SablierPremium3DReady = import(new URL("premium3d.js" + version, here).href)
    .catch((error) => {
      giveUp("premium-module-load");
      console.error("Sablier premium 3D indisponible", error);
      return null;
    });
  window.SablierDecorReady = load("decor-core.js").then(() => load("seasonal-worlds.js"));
  window.SablierDecorReady.catch((error) => console.error("Décor Sablier indisponible", error));
})();
