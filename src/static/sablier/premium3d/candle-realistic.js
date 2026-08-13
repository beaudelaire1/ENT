import { makeGlass, makeWax, makeChrome, seeded } from "./material-kit.js";
import { flameTexture } from "./flame-texture.js";

export function makeCandleRuntime(THREE, helpers, state) {
  const { reducedMotion, mesh, mobile }=helpers, group=new THREE.Group();
  const glass=makeGlass(THREE), wax=makeWax(THREE), chrome=makeChrome(THREE), seg=mobile?64:96;
  const jar=mesh(new THREE.CylinderGeometry(1.02,1.08,3.45,seg,1,true),glass,{cast:false,receive:false}); jar.position.y=-.08; jar.renderOrder=4; group.add(jar);
  const base=mesh(new THREE.CylinderGeometry(1,1.04,.16,seg),glass,{cast:false,receive:false}); base.position.y=-1.73; group.add(base);
  const rim=mesh(new THREE.TorusGeometry(1.02,.045,18,seg),glass,{cast:false,receive:false}); rim.rotation.x=Math.PI/2; rim.position.y=1.65; group.add(rim);
  const body=mesh(new THREE.CylinderGeometry(.91,.95,2.94,seg,8),wax); body.position.y=-.2; group.add(body);
  const pool=mesh(new THREE.CylinderGeometry(.87,.89,.065,seg),new THREE.MeshPhysicalMaterial({color:0xffd9aa,roughness:.18,clearcoat:.65,clearcoatRoughness:.1,transmission:.09,thickness:.18})); group.add(pool);
  const crater=mesh(new THREE.TorusGeometry(.3,.065,18,64),new THREE.MeshPhysicalMaterial({color:0xffc986,roughness:.2,clearcoat:.5})); crater.rotation.x=Math.PI/2; group.add(crater);
  const wick=mesh(new THREE.CylinderGeometry(.024,.034,.34,12),new THREE.MeshStandardMaterial({color:0x17120f,roughness:.95})); group.add(wick);
  const tip=mesh(new THREE.SphereGeometry(.045,16,10),new THREE.MeshStandardMaterial({color:0x090706,roughness:1})); group.add(tip);
  const tex=flameTexture(THREE), flame=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,color:0xffffff,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false})); flame.scale.set(.72,1.48,1); group.add(flame);
  const halo=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,color:0xff7a22,transparent:true,opacity:.26,blending:THREE.AdditiveBlending,depthWrite:false})); halo.scale.set(1.75,2.2,1); group.add(halo);
  const light=new THREE.PointLight(0xff9a46,mobile?18:28,7,2); group.add(light);
  const drips=[]; for(let i=0;i<4;i+=1){const angle=seeded(i,13)*Math.PI*2,length=.3+seeded(i,17)*.65,drip=mesh(new THREE.CapsuleGeometry(.045,length,5,12),makeWax(THREE));drip.userData={angle,length};group.add(drip);drips.push(drip);}
  const plate=mesh(new THREE.CylinderGeometry(1.18,1.24,.11,72),chrome); plate.position.y=-1.88; group.add(plate);

  function update(progress,time){
    const height=.38+2.56*progress; body.scale.y=height/2.94; body.position.y=-1.55+height/2; const topY=-1.55+height;
    pool.position.y=topY+.012; crater.position.y=topY+.055; wick.position.y=topY+.18; tip.position.y=topY+.35;
    for(const drip of drips){const visible=Math.min(drip.userData.length,Math.max(.12,height*.26));drip.scale.y=visible/drip.userData.length;drip.position.set(Math.cos(drip.userData.angle)*.89,topY-visible/2-.06,Math.sin(drip.userData.angle)*.89);drip.visible=progress>.1;}
    const y=topY+.72; flame.position.y=y; halo.position.y=y+.03; light.position.set(0,topY+.46,.08); const alive=progress>.015&&!state.finished; flame.visible=alive; halo.visible=alive; light.visible=alive;
    if(alive&&!reducedMotion){const f=1+Math.sin(time*.013)*.055+Math.sin(time*.029)*.022;flame.scale.set(.72/f,1.48*f,1);flame.position.x=Math.sin(time*.008)*.035;flame.material.rotation=Math.sin(time*.006)*.035;halo.material.opacity=.22+Math.sin(time*.011)*.05;light.intensity=(mobile?18:28)+Math.sin(time*.017)*4;}
    group.rotation.y=reducedMotion?0:Math.sin(time*.00015)*.035;
  }
  return {object:group,update};
}
