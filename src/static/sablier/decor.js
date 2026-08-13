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
  window.SablierDecorReady = load("decor-core.js").then(() => load("seasonal-worlds.js"));
})();
