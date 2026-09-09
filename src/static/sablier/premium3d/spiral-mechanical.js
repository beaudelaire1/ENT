// Ressort d'horlogerie : ruban métallique rectangulaire, platine et pieds porteurs.
// Le ruban cuivré se retire vers l'axe ; la gorge en acier reste dans la platine.
import {makeSteel,makeChrome} from './material-kit.js';

function ribbon(T, fraction, steps=480) {
  const length=Math.max(2,Math.ceil(steps*fraction)),vertices=[],indices=[];
  for(let i=0;i<=length;i++) {
    const t=i/length*Math.max(.0001,fraction),a=t*Math.PI*8-Math.PI/2,r=.17+t*1.53;
    for(const [dr,z] of [[-.035,.10],[.035,.10],[-.035,.23],[.035,.23]])vertices.push(Math.cos(a)*(r+dr),Math.sin(a)*(r+dr),z);
    if(i<length) {
      const b=i*4,n=b+4;
      for(const [a0,a1,b0,b1] of [[b,b+1,n,n+1],[b+2,n+2,b+3,n+3],[b,n,b+2,n+2],[b+1,b+3,n+1,n+3]])
        indices.push(a0,a1,b0,a1,b1,b0);
    }
  }
  const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(vertices,3));g.setIndex(indices);g.computeVertexNormals();return g;
}

export function makeSpiralRuntime(T,{mesh,mobile}) {
  const object=new T.Group(),steel=makeSteel(T),chrome=makeChrome(T);
  steel.normalScale.set(.055,.055);chrome.normalScale.set(.035,.035);
  const brass=new T.MeshStandardMaterial({color:'#b98e57',metalness:.86,roughness:.34,normalMap:steel.normalMap,normalScale:new T.Vector2(.04,.04)});
  const dark=new T.MeshStandardMaterial({color:'#29313a',roughness:.48,metalness:.65});
  const add=(g,m,p)=>{const o=mesh(g,m);o.position.set(...p);object.add(o);return o;};
  const plate=add(new T.CylinderGeometry(1.94,1.94,.18,96),dark,[0,0,-.04]);plate.rotation.x=Math.PI/2;
  add(new T.TorusGeometry(1.88,.055,12,96),chrome,[0,0,.08]);
  add(ribbon(T,1,mobile?280:480),steel,[0,0,0]);
  const remaining=add(ribbon(T,1,mobile?280:480),brass,[0,0,.025]);
  // Pieds inclinés, posés sur une semelle ; le disque ne tient plus sur sa tranche.
  for(const side of [-1,1]) {
    const foot=add(new T.BoxGeometry(.16,.74,.32),steel,[side*.85,-1.85,-.05]);foot.rotation.z=-side*.24;
  }
  add(new T.BoxGeometry(2.45,.12,.9),dark,[0,-2.25,-.03]);
  for(let i=0;i<8;i++) {
    const a=i*Math.PI/4,x=Math.cos(a)*1.77,y=Math.sin(a)*1.77;
    const screw=add(new T.CylinderGeometry(.044,.044,.025,16),chrome,[x,y,.14]);screw.rotation.x=Math.PI/2;
    add(new T.BoxGeometry(.048,.008,.006),dark,[x,y,.157]);
  }
  const axle=add(new T.CylinderGeometry(.13,.13,.27,24),brass,[0,0,.17]);axle.rotation.x=Math.PI/2;
  add(new T.TorusGeometry(.24,.024,10,32),chrome,[0,0,.12]);
  const pointer=add(new T.SphereGeometry(.062,16,12),brass,[0,-1.7,.26]);
  // Verre mince, sans transmission volumique d'un bloc de presque un mètre.
  const cover=add(new T.CircleGeometry(1.8,80),new T.MeshPhysicalMaterial({color:'#e1edf3',metalness:0,roughness:.08,
    transparent:true,opacity:.06,depthWrite:false,clearcoat:1,side:T.FrontSide}),[0,0,.32]);
  cover.castShadow=false;
  let previous=-1;
  function update(progress) {
    const p=Math.max(0,Math.min(1,progress));
    if(Math.abs(p-previous)<.001)return;
    remaining.geometry.dispose();remaining.geometry=ribbon(T,p,mobile?280:480);remaining.visible=p>.001;
    pointer.visible=p>.001;const a=p*Math.PI*8-Math.PI/2,r=.17+p*1.53;pointer.position.set(Math.cos(a)*r,Math.sin(a)*r,.26);
    previous=p;
  }
  return {object,update};
}
