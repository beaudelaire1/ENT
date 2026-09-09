// Les 24 compositions actives. Le catalogue conserve ses identifiants historiques.
// Les outils de fabrication vivent dans compositions.js ; aucun lieu de substitution.
import {compose} from './compositions.js';
import {aurora} from './sky-effects.js';

export const RECIPES = {
  star_tree: {
    env: {"kind": "night", "zenith": "#020d19", "horizon": "#0c3d5d", "ground": "#061017", "light": "#ffe7a0", "glow": "#7ad8ff", "elevation": 8, "azimuth": 200, "intensity": 3.4, "size": 3, "haze": 0.5, "directIntensity": 0.9, "ambient": 1.4},
    fog: ["#0a2334", 0.0042],
  },
  eternity_fountain: {
    env: {"kind": "night", "zenith": "#061724", "horizon": "#1f7180", "ground": "#07141a", "light": "#dffff7", "glow": "#57e3df", "elevation": 14, "azimuth": 150, "intensity": 4.2, "size": 2.6, "haze": 0.55, "directIntensity": 1.2},
    fog: ["#123c46", 0.0052],
  },
  eden: {
    env: {"kind": "day", "turbidity": 4.5, "rayleigh": 1.4, "mie": 0.006, "mieG": 0.82, "elevation": 26, "azimuth": 44, "light": "#fff0a6", "directIntensity": 3.1, "exposure": 0.42, "ambient": 1.9},
    fog: ["#20402f", 0.0044],
  },
  time_river: {
    env: {"kind": "night", "zenith": "#070d1d", "horizon": "#314b76", "ground": "#090d18", "light": "#f2d6a0", "glow": "#9dcaff", "elevation": 6, "azimuth": 190, "intensity": 3.8, "size": 3.2, "haze": 0.6, "directIntensity": 1},
    fog: ["#243a5c", 0.0058],
  },
  memories: {
    env: {"kind": "night", "zenith": "#15111d", "horizon": "#55445f", "ground": "#100d14", "light": "#f0cba2", "glow": "#d2b6ff", "elevation": 4, "azimuth": 170, "intensity": 2.6, "size": 4, "haze": 0.75, "directIntensity": 0.6},
    fog: ["#4a3e57", 0.0072],
  },
  interstellar: {
    env: {"kind": "night", "zenith": "#01040d", "horizon": "#111d3c", "ground": "#03050a", "light": "#c8dbff", "glow": "#8eb8ff", "elevation": 18, "azimuth": 230, "intensity": 5, "size": 1.4, "haze": 0.3, "directIntensity": 1.4, "ambient": 1.4, "exposure": 1.8},
    fog: ["#050a16", 0.0016],
  },
  galaxy: {
    env: {"kind": "night", "zenith": "#03020b", "horizon": "#25133d", "ground": "#05030b", "light": "#f2d6ff", "glow": "#d18aff", "elevation": 24, "azimuth": 210, "intensity": 4.4, "size": 2, "haze": 0.5, "directIntensity": 1.1, "backgroundColor": "#040510", "exposure": 1.4},
    fog: ["#090718", 0],
  },
  heaven: {
    env: {"kind": "day", "turbidity": 2.6, "rayleigh": 0.9, "mie": 0.004, "mieG": 0.85, "elevation": 20, "azimuth": 330, "light": "#fff8d8", "directIntensity": 3.6, "exposure": 0.34, "ambient": 1.8},
    fog: ["#c7e4f0", 0.005],
  },
  oasis: {
    env: {"kind": "day", "turbidity": 9, "rayleigh": 2.6, "mie": 0.012, "mieG": 0.78, "elevation": 5, "azimuth": 206, "light": "#ffd89b", "directIntensity": 3.2, "exposure": 0.3},
    fog: ["#8a573f", 0.0048],
  },
  abyss: {
    env: {"kind": "night", "zenith": "#021217", "horizon": "#0d4b55", "ground": "#031015", "light": "#9ff8ee", "glow": "#58d6d8", "elevation": 62, "azimuth": 180, "intensity": 3.6, "size": 6, "haze": 0.8, "directIntensity": 1.5, "backgroundColor": "#123e49", "ambient": 1.3, "exposure": 1.7},
    fog: ["#1d5660", 0.022],
  },
  rain_refuge: {
    env: {"kind": "night", "zenith": "#111820", "horizon": "#344756", "ground": "#15130f", "light": "#ffd28a", "glow": "#8ba4ba", "elevation": 5, "azimuth": 200, "intensity": 2.2, "size": 3, "haze": 0.7, "directIntensity": 0.7},
    fog: ["#35485a", 0.0038],
  },
  aurora_valley: {
    env: {"kind": "night", "zenith": "#06121e", "horizon": "#17445b", "ground": "#081018", "light": "#baffef", "glow": "#7defcf", "elevation": 10, "azimuth": 195, "intensity": 3, "size": 2.4, "haze": 0.55, "directIntensity": 0.9},
    fog: ["#12303f", 0.0055],
  },
  spring_meadow: {
    env: {"kind": "day", "turbidity": 3.4, "rayleigh": 1.6, "mie": 0.005, "mieG": 0.8, "elevation": 30, "azimuth": 46, "light": "#fff3c3", "directIntensity": 3.3, "exposure": 0.4, "ambient": 1.8},
    fog: ["#cfe3d3", 0.0034],
  },
  summer_terrace: {
    env: {"kind": "day", "turbidity": 5.2, "rayleigh": 1.9, "mie": 0.007, "mieG": 0.79, "elevation": 40, "azimuth": 324, "light": "#fff0ae", "directIntensity": 4, "exposure": 0.36, "ambient": 1.7},
    fog: ["#d8bf94", 0.0028],
  },
  autumn_lake: {
    env: {"kind": "day", "turbidity": 7, "rayleigh": 2.8, "mie": 0.009, "mieG": 0.8, "elevation": 7, "azimuth": 218, "light": "#ffd39d", "directIntensity": 3, "exposure": 0.32},
    fog: ["#9c7a5c", 0.0062],
  },
  winter_lodge: {
    env: {"kind": "day", "turbidity": 3, "rayleigh": 2.2, "mie": 0.004, "mieG": 0.82, "elevation": 14, "azimuth": 316, "light": "#eef8ff", "directIntensity": 2.6, "exposure": 0.3, "ambient": 1.7},
    fog: ["#b8ccd8", 0.0058],
  },
  rain_city: {
    env: {"kind": "night", "zenith": "#101923", "horizon": "#263748", "ground": "#10151a", "light": "#b7d5ea", "glow": "#78b8e8", "elevation": 4, "azimuth": 210, "intensity": 2, "size": 3, "haze": 0.65, "directIntensity": 0.6, "ambient": 1.6},
    fog: ["#243544", 0.0026],
  },
  ocean_cliffs: {
    env: {"kind": "day", "turbidity": 4.2, "rayleigh": 1.7, "mie": 0.006, "mieG": 0.8, "elevation": 20, "azimuth": 334, "light": "#f6e5c7", "directIntensity": 3.4, "exposure": 0.36, "ambient": 1.8},
    fog: ["#9fb9c6", 0.0042],
  },
  sahara_observatory: {
    env: {"kind": "day", "turbidity": 11, "rayleigh": 3.2, "mie": 0.014, "mieG": 0.76, "elevation": 3.4, "azimuth": 214, "light": "#ffd39b", "directIntensity": 3.6, "exposure": 0.34, "zenith": "#3f5e86", "horizon": "#e0a870", "ground": "#9a6234", "ambient": 1.5},
    fog: ["#b07747", 0.0034],
  },
  ancient_forest: {
    env: {"kind": "night", "turbidity": 6, "rayleigh": 2.4, "mie": 0.008, "mieG": 0.84, "elevation": 34, "azimuth": 42, "light": "#dff2bf", "directIntensity": 3.6, "exposure": 1.35, "ambient": 1.6, "zenith": "#152c22", "horizon": "#314c3a", "ground": "#172b1c", "glow": "#798b60", "intensity": 2, "backgroundColor": "#263e30"},
    fog: ["#283d2e", 0.014],
  },
  storm_cliffs: {
    env: {"kind": "night", "zenith": "#11131b", "horizon": "#333846", "ground": "#15191d", "light": "#dce8ff", "glow": "#a8b9db", "elevation": 7, "azimuth": 200, "intensity": 2.4, "size": 3.4, "haze": 0.7, "directIntensity": 0.8},
    fog: ["#343c50", 0.0058],
  },
  ember_hearth: {
    env: {"kind": "night", "zenith": "#120d0b", "horizon": "#271713", "ground": "#090706", "light": "#ffd083", "glow": "#ff9b4b", "elevation": -6, "azimuth": 180, "intensity": 1.2, "size": 5, "haze": 0.9, "directIntensity": 0.25, "exposure": 1.7, "ambient": 0.85},
    fog: ["#241511", 0.0125],
  },
  polar_sky: {
    env: {"kind": "night", "zenith": "#02111d", "horizon": "#0d3448", "ground": "#10222a", "light": "#d9fff0", "glow": "#77f0b0", "elevation": 8, "azimuth": 190, "intensity": 2.8, "size": 2.6, "haze": 0.5, "directIntensity": 0.8},
    fog: ["#0d2c38", 0.0044],
  },
  midnight_rooftop: {
    env: {"kind": "night", "zenith": "#030710", "horizon": "#10192a", "ground": "#080a0d", "light": "#e8edff", "glow": "#9cb9f1", "elevation": 30, "azimuth": 220, "intensity": 4, "size": 1.6, "haze": 0.4, "directIntensity": 1, "ambient": 1.3},
    fog: ["#0c1220", 0.0022],
  },
};

const CAMERAS = {
  star_tree: {height:1.72,pitch:.12,fov:58},
  rain_refuge: {height:1.6,pitch:0,fov:58},
  ancient_forest: {height:1.72,pitch:0,fov:60},
  ocean_cliffs: {height:2.8,pitch:-.12,fov:52},
  interstellar: {height:1.72,pitch:.03,fov:52},
  eternity_fountain: {height:2,pitch:.13,fov:58},
  eden: {height:2,pitch:.05,fov:58},
  memories: {height:1.65,pitch:.04,fov:54},
  galaxy: {height:0,pitch:.1,fov:62},
  heaven: {height:2,pitch:.12,fov:58},
  abyss: {height:2,pitch:.05,fov:56},
  aurora_valley: {height:1.8,pitch:.09,fov:62},
  summer_terrace: {height:1.65,pitch:.06,fov:64},
  winter_lodge: {height:1.75,pitch:.08,fov:58},
  storm_cliffs: {height:2,pitch:.08,fov:64},
  ember_hearth: {height:1.4,pitch:-.04,fov:52},
  polar_sky: {height:1.7,pitch:.22,fov:64},
  midnight_rooftop: {height:1.7,pitch:.07,fov:58},
};

export function buildWorld(THREE,key,{mobile=false}={}) {
  const recipe=RECIPES[key];
  if(!recipe)throw new Error(`Univers inconnu : ${key}`);
  const object=compose(THREE,key,mobile);
  if(!object)throw new Error(`Composition absente : ${key}`);
  const updates=[object.userData.update];
  if(key==='aurora_valley'||key==='polar_sky') {
    const curtain=aurora(THREE,{valley:key==='aurora_valley'});object.add(curtain);updates.push(curtain.userData.update);
  }
  let flash;
  if(key==='storm_cliffs') {
    flash=new THREE.DirectionalLight('#bbcde4',0);flash.position.set(-20,80,-180);object.add(flash);
  }
  const camera={height:1.72,pitch:0,fov:56,...CAMERAS[key]};
  if(mobile)camera.fov=Math.max(65,camera.fov);
  return {object,env:recipe.env,fog:recipe.fog,camera,
    update(time,motion,progress,lightningEnabled=false){
      if(flash&&(!lightningEnabled||motion<=0))flash.intensity=0;
      if(motion<=0)return;
      // time est déjà l'horloge d'animation ralentie : ne pas multiplier deux fois.
      for(const update of updates)update(time,1,progress);
      if(flash){const cycle=time%57000;flash.intensity=lightningEnabled&&cycle>55000?Math.sin((cycle-55000)/2000*Math.PI)*.65:0;}
    },
  };
}
export const WORLD_KEYS=Object.keys(RECIPES);
