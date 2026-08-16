// Post-traitement de la scène immersive.
//
// Deux effets seulement, mais ce sont ceux qu'un œil attend d'une image prise plutôt que
// calculée : la diffusion des hautes lumières autour d'une flamme ou d'un soleil, et une
// profondeur de champ qui détache l'objet de son paysage. Sans eux, tout le champ est
// net partout et la scène retrouve l'aspect « rendu de synthèse » qu'on cherche à fuir.
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

export function createPostFX(THREE, { renderer, scene, camera, width, height, mobile, depthOfField = true, ceiling = true }) {
  let composer;
  try {
    composer = new EffectComposer(renderer);
    composer.setSize(width, height);
    composer.addPass(new RenderPass(scene, camera));
    if (ceiling) composer.addPass(new ShaderPass(CEILING));

    let bokeh = null;
    if (!mobile && depthOfField) {
      // Mise au point sur l'objet, placé à neuf unités de la caméra. Le paysage part
      // dans le flou comme sur une photographie prise à grande ouverture.
      bokeh = new BokehPass(scene, camera, { focus: 9, aperture: 0.00042, maxblur: 0.012 });
      composer.addPass(bokeh);
    }

    // L'ordre compte. Le tonemapping vient *avant* le halo : appliqué après, le halo
    // travaillerait sur les valeurs brutes du ciel, où un après-midi d'été vaut plusieurs
    // milliers. Le flou étalait alors cette énergie sur toute l'image et la scène entière
    // virait au blanc. Tonemappée d'abord, l'image tient dans [0,1] et le halo ne déborde
    // plus que des sources réellement lumineuses : flamme, soleil, éclat du sable.
    composer.addPass(new OutputPass());
    const bloom = new UnrealBloomPass(
      new THREE.Vector2(width, height),
      mobile ? 0.22 : 0.3,    // intensité
      0.62,                   // rayon
      mobile ? 0.86 : 0.8,    // seuil : seules les vraies hautes lumières diffusent
    );
    composer.addPass(bloom);

    return {
      render() { composer.render(); },
      setSize(nextWidth, nextHeight) {
        composer.setSize(nextWidth, nextHeight);
        bloom.setSize(nextWidth, nextHeight);
      },
      focus(distance) {
        if (bokeh) bokeh.uniforms.focus.value = distance;
      },
      dispose() {
        composer.dispose();
      },
    };
  } catch (_) {
    // Le rendu direct reste parfaitement valable : on perd le halo et le flou, pas la
    // scène. Mieux vaut une image sans post-traitement qu'un écran noir.
    composer?.dispose?.();
    return null;
  }
}
