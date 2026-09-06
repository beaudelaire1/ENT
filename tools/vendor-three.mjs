// Copie locale de Three.js pour les visualisations du Sablier.
//
// Rien n'est chargé depuis un CDN : le moteur 3D doit donc être copié *en entier*
// dans `src/static/vendor`. Depuis la version 0.16x, `three.module.js` n'est plus
// autonome — il réexporte `three.core.js`. Ne copier que le premier fichier laissait
// donc un import mort : le navigateur échouait silencieusement sur `three.core.js`,
// `premium3d.js` basculait en repli et le Sablier n'affichait plus que le dessin 2D.
// Ce script copie l'arbre complet, dépendances comprises, et vérifie qu'aucun import
// ne pointe en dehors du dossier vendu.
import { mkdirSync, copyFileSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const SOURCE = join(ROOT, "node_modules", "three");
const TARGET = join(ROOT, "src", "static", "vendor");
const ADDONS = join(TARGET, "three-addons");

// Le moteur lui-même. `three.core.js` porte la quasi-totalité du code depuis 0.16x.
const BUILD = ["three.module.js", "three.core.js"];

// Modules d'exemple réellement utilisés par la scène immersive. Sky rend un ciel à
// diffusion atmosphérique ; les passes de post-traitement donnent le halo lumineux
// des flammes, du soleil et du sable.
const ADDON_FILES = [
  "objects/Sky.js",
  "postprocessing/EffectComposer.js",
  "postprocessing/Pass.js",
  "postprocessing/RenderPass.js",
  "postprocessing/ShaderPass.js",
  "postprocessing/MaskPass.js",
  "postprocessing/OutputPass.js",
  "postprocessing/UnrealBloomPass.js",
  "postprocessing/BokehPass.js",
  "shaders/BokehShader.js",
  "shaders/CopyShader.js",
  "shaders/LuminosityHighPassShader.js",
  "shaders/OutputShader.js",
];

function fail(message) {
  console.error(`vendor-three: ${message}`);
  process.exit(1);
}

if (!existsSync(SOURCE)) fail("`node_modules/three` est absent — lancez `npm install` d'abord.");

mkdirSync(TARGET, { recursive: true });
for (const name of BUILD) {
  const from = join(SOURCE, "build", name);
  if (!existsSync(from)) fail(`fichier attendu introuvable : build/${name}`);
  copyFileSync(from, join(TARGET, name));
}

// Les modules d'exemple importent le spécificateur nu `three`, que le navigateur ne
// sait pas résoudre sans import map. On le réécrit vers le chemin relatif du moteur
// vendu : la page reste un simple ensemble de modules statiques.
for (const file of ADDON_FILES) {
  const from = join(SOURCE, "examples", "jsm", file);
  if (!existsSync(from)) fail(`module d'exemple introuvable : examples/jsm/${file}`);
  const to = join(ADDONS, file);
  mkdirSync(dirname(to), { recursive: true });
  const engine = relative(dirname(to), join(TARGET, "three.module.js")).split("\\").join("/");
  const source = readFileSync(from, "utf8").replace(
    /from\s+["']three["']/g,
    `from "${engine.startsWith(".") ? engine : `./${engine}`}"`,
  );
  writeFileSync(to, source);
}

// Garde-fou : plus aucun import ne doit sortir du dossier vendu, sans quoi le moteur
// se casserait à nouveau en production sans que rien ne le signale.
const copied = [
  ...BUILD.map(name => join(TARGET, name)),
  ...ADDON_FILES.map(file => join(ADDONS, file)),
];
for (const path of copied) {
  const source = readFileSync(path, "utf8");
  for (const [, specifier] of source.matchAll(/(?:^|\n)\s*(?:import|export)[^;]*?from\s+["']([^"']+)["']/g)) {
    if (!specifier.startsWith(".")) fail(`${relative(ROOT, path)} importe encore « ${specifier} »`);
    const resolved = resolve(dirname(path), specifier);
    if (!existsSync(resolved)) fail(`${relative(ROOT, path)} importe « ${specifier} », absent du dossier vendu`);
  }
}

console.log(`vendor-three: ${copied.length} fichiers copiés dans src/static/vendor.`);
