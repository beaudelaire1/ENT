(() => {
  const source = document.currentScript?.src;
  if (!source) return;
  const here = new URL(source);
  const version = here.search;
  const loadCore = () => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = new URL("sablier-core.js" + version, here).href;
    script.onload = resolve;
    script.onerror = reject;
    document.head.append(script);
  });
  Promise.resolve(window.SablierDecorReady).catch(() => null).then(loadCore);
})();
