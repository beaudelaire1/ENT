export function makeChrome(THREE){return new THREE.MeshPhysicalMaterial({color:0xd9e0e7,metalness:1,roughness:0.12,clearcoat:0.9,clearcoatRoughness:0.05});}
export function makeSteel(THREE){return new THREE.MeshPhysicalMaterial({color:0x747c87,metalness:0.96,roughness:0.24,clearcoat:0.45});}
export function makeGlass(THREE){return new THREE.MeshPhysicalMaterial({color:0xf4fbff,roughness:0.025,metalness:0,transmission:0.96,thickness:0.72,ior:1.46,transparent:true,opacity:0.94,clearcoat:1,clearcoatRoughness:0.015,side:THREE.DoubleSide,depthWrite:false});}
export function makeSand(THREE){return new THREE.MeshPhysicalMaterial({color:0xd4a04f,roughness:0.76,metalness:0.01,clearcoat:0.08});}
export function makePearl(THREE){return new THREE.MeshPhysicalMaterial({color:0xf4efe7,roughness:0.14,metalness:0.02,clearcoat:1,clearcoatRoughness:0.04,iridescence:0.9,iridescenceIOR:1.31,iridescenceThicknessRange:[110,390],sheen:0.3,sheenRoughness:0.2,sheenColor:new THREE.Color(0xffeee0)});}
export function makeWax(THREE){return new THREE.MeshPhysicalMaterial({color:0xffead0,roughness:0.42,metalness:0,clearcoat:0.3,clearcoatRoughness:0.3,transmission:0.07,thickness:0.5,attenuationColor:new THREE.Color(0xffd2a0),attenuationDistance:1.8});}
export function seeded(index,salt=1){const value=Math.sin(index*91.733+salt*37.719)*43758.5453;return Math.abs(value-Math.floor(value));}
