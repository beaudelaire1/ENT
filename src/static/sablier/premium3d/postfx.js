// Post-traitement de la scène immersive.
//
// Halo discret réservé aux sources lumineuses. Le flou de profondeur reste disponible
// mais désactivé par défaut : il masquait les repères qui distinguent les lieux.
import { EffectComposer } from "../../vendor/three-addons/postprocessing/EffectComposer.js";
import { RenderPass } from "../../vendor/three-addons/postprocessing/RenderPass.js";
import { ShaderPass } from "../../vendor/three-addons/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "../../vendor/three-addons/postprocessing/UnrealBloomPass.js";
import { BokehPass } from "../../vendor/three-addons/postprocessing/BokehPass.js";
import { OutputPass } from "../../vendor/three-addons/postprocessing/OutputPass.js";

// Plafond de luminance. Le ciel à diffusion atmosphérique n'est pas borné : au zénith
// d'un jour d'été, il dépasse largement ce qu'un demi-flottant sait représenter. La
// valeur devient alors infinie, le flou du halo la propage en NaN, et toute l'image
// tombe au noir — un plein soleil produisait une nuit noire. On borne donc l'image avant
// le halo. Le plafond est fixé quelques crans au-dessus du blanc : le tonemapping ACES
// écrase déjà tout ce qui le dépasse, et le halo reste borné au lieu de recouvrir la
// scène entière d'un voile blanc.
const CEILING = {
  uniforms: { tDiffuse: { value: null }, ceiling: { value: 8 } },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float ceiling;
    varying vec2 vUv;
    void main() {
      vec4 texel = texture2D(tDiffuse, vUv);
      // max puis min, et rien d'autre : toute comparaison avec NaN étant fausse, le max
      // rend 0 pour un NaN, et une valeur infinie retombe sur le plafond. Les
      // constructions plus expressives — comparaisons booléennes, très grandes
      // constantes — ne se compilent pas de la même façon partout et ramenaient ici une
      // image entièrement blanche.
      vec3 safe = min(max(texel.rgb, vec3(0.0)), vec3(ceiling));
      gl_FragColor = vec4(safe, texel.a);
    }`,
};

export function createPostFX(THREE, { renderer, scene, camera, width, height, mobile, depthOfField = false, ceiling = true }) {
  let composer;
  try {
    composer = new EffectComposer(renderer);
    composer.setSize(width, height);
    composer.addPass(new RenderPass(scene, camera));
    let ceilingPass = null;
    if (ceiling) {
      ceilingPass = new ShaderPass(CEILING);
      composer.addPass(ceilingPass);
    }

    let bokeh = null;
    if (!mobile && depthOfField) {
      // Mise au point sur l'objet, placé à neuf unités de la caméra. Le paysage part
      // dans le flou comme sur une photographie prise à grande ouverture.
      bokeh = new BokehPass(scene, camera, { focus: 9, aperture: 0.00042, maxblur: 0.012 });
      composer.addPass(bokeh);
    }

    // L'ordre compte, et il n'y en a qu'un de correct : le halo diffuse en lumière
    // linéaire, puis le tonemapping ferme la chaîne. `OutputPass` doit rester la dernière
    // passe — placée avant, elle cesse d'être la sortie, et la passe suivante réapplique
    // la courbe sRGB sur une image déjà encodée. L'image entière ressortait laiteuse,
    // sans noirs ni contraste.
    const bloom = new UnrealBloomPass(
      new THREE.Vector2(width, height),
      mobile ? 0.055 : 0.08, // Seules les sources lumineuses diffusent ; le métal reste lisible.
      0.62,                   // rayon
      1,                      // seuil, réglé ensuite selon l'exposition de l'univers
    );
    composer.addPass(bloom);
    composer.addPass(new OutputPass());

    // Le seuil du halo se lit en lumière linéaire, alors que « blanc » dépend de
    // l'exposition du lieu : à 0,3 le blanc vaut environ 3, à 0,95 environ 1. Un seuil
    // fixe ferait donc diffuser un sable de plein midi comme une flamme.
    const setExposure = (exposure) => {
      const white = 1 / Math.max(0.05, exposure);
      bloom.threshold = white * 2.5;
      if (ceilingPass) ceilingPass.uniforms.ceiling.value = white * 6;
    };
    setExposure(renderer.toneMappingExposure || 1);

    return {
      render() { composer.render(); },
      setSize(nextWidth, nextHeight) {
        composer.setSize(nextWidth, nextHeight);
        bloom.setSize(nextWidth, nextHeight);
      },
      setExposure,
      focus(distance) {
        if (bokeh) bokeh.uniforms.focus.value = distance;
      },
      dispose() {
        for (const pass of composer.passes) pass.dispose?.();
        composer.dispose();
      },
    };
  } catch (_) {
    // Le rendu direct reste parfaitement valable : on perd le halo et le flou, pas la
    // scène. Mieux vaut une image sans post-traitement qu'un écran noir.
    for (const pass of composer?.passes || []) pass.dispose?.();
    composer?.dispose?.();
    return null;
  }
}
