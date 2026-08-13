import { makeSteel, seeded } from "./material-kit.js";

function makeMoon(THREE, helpers){
  const {mobile,reducedMotion,mesh}=helpers,group=new THREE.Group();
  const lunar=new THREE.MeshPhysicalMaterial({color:0xbdbab2,roughness:.92,metalness:0,clearcoat:.03});
  const sphere=mesh(new THREE.SphereGeometry(1.5,mobile?72:112,mobile?48:72),lunar);group.add(sphere);
  const craterMat=new THREE.MeshStandardMaterial({color:0x6f6d68,roughness:1});
  const forward=new THREE.Vector3(0,0,1);
  for(let i=0;i<24;i+=1){const theta=seeded(i,21)*Math.PI*2,phi=.28+seeded(i,22)*1.05,size=.045+seeded(i,23)*.14,dir=new THREE.Vector3(Math.cos(theta)*Math.sin(phi),Math.cos(phi)*.72,Math.sin(theta)*Math.sin(phi)).normalize();if(dir.z<.05)dir.z=Math.abs(dir.z)+.08;dir.normalize();const crater=mesh(new THREE.TorusGeometry(size,size*.3,10,24),craterMat,{cast:false,receive:false});crater.position.copy(dir).multiplyScalar(1.485);crater.quaternion.setFromUnitVectors(forward,dir);crater.scale.y=.72;group.add(crater);}
  const target=new THREE.Object3D();group.add(target);const phase=new THREE.DirectionalLight(0xfff3dc,8.4);phase.target=target;group.add(phase);
  function update(progress,time){const angle=(1-progress)*Math.PI;phase.position.set(Math.sin(angle)*5.6,1.4,Math.cos(angle)*5.6);group.rotation.y=reducedMotion?-.18:-.18+Math.sin(time*.00008)*.045;group.rotation.x=reducedMotion?.03:.03+Math.sin(time*.00005)*.015;}
  return {object:group,update};
}

function glowTexture(THREE){const c=document.createElement("canvas");c.width=c.height=192;const x=c.getContext("2d"),g=x.createRadialGradient(96,96,4,96,96,96);g.addColorStop(0,"rgba(255,250,220,1)");g.addColorStop(.18,"rgba(255,185,64,.96)");g.addColorStop(.5,"rgba(255,95,18,.42)");g.addColorStop(1,"rgba(255,60,0,0)");x.fillStyle=g;x.fillRect(0,0,192,192);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;}

function makeSun(THREE,helpers){
  const {mobile,reducedMotion,mesh}=helpers,group=new THREE.Group();
  const surface=new THREE.MeshStandardMaterial({color:0xff9c24,emissive:0xff4d09,emissiveIntensity:4.8,roughness:.68,metalness:0});
  const sphere=mesh(new THREE.SphereGeometry(1.24,mobile?72:112,mobile?48:72),surface,{cast:false,receive:false});group.add(sphere);
  const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTexture(THREE),color:0xffa13d,transparent:true,opacity:.9,blending:THREE.AdditiveBlending,depthWrite:false}));glow.scale.set(6.2,6.2,1);group.add(glow);
  const corona=mesh(new THREE.TorusGeometry(1.43,.19,24,mobile?80:128),new THREE.MeshBasicMaterial({color:0xff8a32,transparent:true,opacity:.22,blending:THREE.AdditiveBlending,depthWrite:false}),{cast:false,receive:false});group.add(corona);
  const light=new THREE.PointLight(0xff9b43,38,20,1.35);group.add(light);
  function update(progress,time){const angle=progress*Math.PI;group.position.x=Math.cos(angle)*1.4;group.position.y=-.72+Math.sin(angle)*1.2;const pulse=reducedMotion?1:1+Math.sin(time*.0022)*.016;sphere.scale.setScalar(pulse);glow.material.opacity=reducedMotion?.86:.82+Math.sin(time*.0017)*.06;corona.rotation.z=reducedMotion?0:time*.00004;corona.scale.setScalar(reducedMotion?1:1+Math.sin(time*.0013)*.03);sphere.rotation.y=reducedMotion?0:time*.00005;}
  return {object:group,update};
}

export function makeCelestialRuntime(THREE,helpers){return {moon:()=>makeMoon(THREE,helpers),sun:()=>makeSun(THREE,helpers)};}
