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
  window.SablierPremium3DReady = import(new URL("premium3d.js" + version, here).href)
    .catch((error) => {
      const app = document.querySelector("#focus-app");
      if (app) {
        app.dataset.renderer3d = "fallback";
        app.dataset.renderer3dReason = "premium-module-load";
      }
      console.error("Sablier premium 3D indisponible", error);
      return null;
    });
  window.SablierDecorReady = load("decor-core.js").then(() => load("seasonal-worlds.js"));
  window.SablierDecorReady.catch((error) => console.error("Décor Sablier indisponible", error));
})();
