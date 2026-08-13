import { makePearl, makeChrome, makeSteel, seeded } from "./material-kit.js";

export function makeBeadsRuntime(THREE, helpers) {
  const { mobile, reducedMotion, mesh }=helpers, group=new THREE.Group(), count=mobile?26:32;
  const points=[]; for(let i=0;i<count;i+=1){const a=i/count*Math.PI*2,r=1.68+Math.sin(a*3)*.06;points.push(new THREE.Vector3(Math.cos(a)*r,Math.sin(a)*1.38,Math.sin(a*2.1)*.16));}
  const curve=new THREE.CatmullRomCurve3([...points,points[0].clone()],true,"centripetal",.42);
  const thread=mesh(new THREE.TubeGeometry(curve,count*7,.032,12,true),new THREE.MeshPhysicalMaterial({color:0x30231b,roughness:.62,metalness:.03,clearcoat:.12})); group.add(thread);

  const pearl=makePearl(THREE); pearl.vertexColors=true; pearl.needsUpdate=true;
  const geometry=new THREE.SphereGeometry(.235,mobile?32:48,mobile?22:32), beads=new THREE.InstancedMesh(geometry,pearl,count), matrix=new THREE.Matrix4(), quat=new THREE.Quaternion(), scale=new THREE.Vector3(), pos=new THREE.Vector3();
  beads.castShadow=true; beads.receiveShadow=true;
  for(let i=0;i<count;i+=1){pos.copy(points[i]);scale.set(.92+seeded(i,2)*.15,.9+seeded(i,3)*.18,.93+seeded(i,4)*.14);quat.setFromEuler(new THREE.Euler(seeded(i,5)*.2,seeded(i,6)*.2,seeded(i,7)*.2));matrix.compose(pos,quat,scale);beads.setMatrixAt(i,matrix);beads.setColorAt(i,new THREE.Color(0xf2eee8));} beads.instanceMatrix.needsUpdate=true; beads.instanceColor.needsUpdate=true; group.add(beads);

  const chrome=makeChrome(THREE), steel=makeSteel(THREE);
  for(const i of [0,8,16,24]){if(i>=count)continue;const p=points[i],a=i/count*Math.PI*2;const spacer=mesh(new THREE.TorusGeometry(.275,.035,14,36),i%16===0?chrome:steel);spacer.position.copy(p);spacer.rotation.set(Math.PI/2,a,0);group.add(spacer);}
  const pendant=mesh(new THREE.SphereGeometry(.18,32,22),chrome); pendant.scale.set(.78,1.18,.7); pendant.position.set(0,-1.86,.08); group.add(pendant);
  for(const x of [-.08,.08]){const tassel=mesh(new THREE.CylinderGeometry(.012,.018,.72,10),steel);tassel.position.set(x,-2.22,.08);tassel.rotation.z=x*.45;group.add(tassel);}

  const active=new THREE.Color(0xffe1ad), pearlColor=new THREE.Color(0xf2eee8), spent=new THREE.Color(0x343943);
  function update(progress,time){const alive=progress*count;for(let i=0;i<count;i+=1){const fill=Math.max(0,Math.min(1,alive-i));pos.copy(points[i]);const pulse=.94+fill*.06,imperfection=.94+seeded(i,9)*.11;scale.set(pulse*imperfection,pulse*(.95+seeded(i,10)*.1),pulse);quat.setFromEuler(new THREE.Euler(seeded(i,5)*.2,seeded(i,6)*.2,seeded(i,7)*.2));matrix.compose(pos,quat,scale);beads.setMatrixAt(i,matrix);beads.setColorAt(i,fill>.5?pearlColor.clone().lerp(active,.2):spent.clone().lerp(pearlColor,fill));}beads.instanceMatrix.needsUpdate=true;beads.instanceColor.needsUpdate=true;group.rotation.y=reducedMotion?0:Math.sin(time*.0002)*.12;group.rotation.z=reducedMotion?0:Math.sin(time*.00013)*.018;}
  return {object:group,update};
}
