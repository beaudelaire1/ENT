import { makeChrome, makeSteel, makeGlass, makeSand, seeded } from "./material-kit.js";

export function makeHourglassRuntime(THREE, helpers, state) {
  const { mobile, reducedMotion, mesh } = helpers;
  const group = new THREE.Group();
  const segments = mobile ? 64 : 96;
  const chrome = makeChrome(THREE), steel = makeSteel(THREE), glass = makeGlass(THREE), sand = makeSand(THREE);
  const grainMat = new THREE.MeshStandardMaterial({color:0xf0c36c,roughness:0.84});

  for (const y of [-2.12, 2.12]) {
    const plate=mesh(new THREE.CylinderGeometry(1.62,1.72,0.24,segments),chrome); plate.position.y=y; group.add(plate);
    const inset=mesh(new THREE.CylinderGeometry(1.43,1.48,0.1,segments),steel); inset.position.y=y+(y>0?-0.16:0.16); group.add(inset);
    const ring=mesh(new THREE.TorusGeometry(1.55,0.055,18,segments),chrome); ring.rotation.x=Math.PI/2; ring.position.y=y+(y>0?-0.105:0.105); group.add(ring);
  }
  for (const x of [-1.29,1.29]) for (const z of [-0.42,0.42]) {
    const column=mesh(new THREE.CylinderGeometry(0.068,0.088,3.94,32),chrome); column.position.set(x,0,z); group.add(column);
    for (const y of [-1.84,1.84]) { const collar=mesh(new THREE.CylinderGeometry(0.115,0.115,0.16,32),steel); collar.position.set(x,y,z); group.add(collar); }
  }

  const profile=[[0.78,1.77],[0.91,1.6],[0.98,1.33],[0.92,1.08],[0.72,0.76],[0.43,0.4],[0.19,0.09],[0.19,-0.09],[0.43,-0.4],[0.72,-0.76],[0.92,-1.08],[0.98,-1.33],[0.91,-1.6],[0.78,-1.77]].map(([r,y])=>new THREE.Vector2(r,y));
  const vessel=mesh(new THREE.LatheGeometry(profile,mobile?72:128),glass,{cast:false,receive:false}); vessel.renderOrder=4; group.add(vessel);
  for(const y of [-1.75,1.75]){const seal=mesh(new THREE.TorusGeometry(0.82,0.035,16,segments),chrome);seal.rotation.x=Math.PI/2;seal.position.y=y;group.add(seal);}

  const top=mesh(new THREE.ConeGeometry(0.86,1.42,segments,16),sand); top.rotation.z=Math.PI; group.add(top);
  const bottom=mesh(new THREE.ConeGeometry(0.94,1.28,segments,16),sand); group.add(bottom);
  const stream=mesh(new THREE.CylinderGeometry(0.014,0.022,1.4,14),grainMat,{cast:false,receive:false}); group.add(stream);
  const count=mobile?90:180, geo=new THREE.IcosahedronGeometry(mobile?0.018:0.014,0), grains=new THREE.InstancedMesh(geo,grainMat,count), matrix=new THREE.Matrix4();
  const seeds=Array.from({length:count},(_,i)=>seeded(i,7)); grains.castShadow=false; grains.receiveShadow=false; group.add(grains);
  for(let i=0;i<count;i+=1){matrix.makeTranslation(0,-0.1,0);grains.setMatrixAt(i,matrix);} grains.instanceMatrix.needsUpdate=true;
  const sparkle=new THREE.PointLight(0xffdba1,mobile?2.5:4.5,4,2); sparkle.position.set(-0.9,0.75,1.5); group.add(sparkle);

  function update(progress,time){
    const received=1-progress;
    const topScale=Math.max(0.001,Math.pow(progress,0.55)); top.scale.set(topScale,Math.max(0.001,progress),topScale); top.position.y=0.12+0.71*progress; top.visible=progress>0.003;
    const bottomScale=Math.max(0.001,Math.pow(received,0.53)); bottom.scale.set(bottomScale,Math.max(0.001,received),bottomScale); bottom.position.y=-1.72+0.64*received; bottom.visible=received>0.003;
    const moundTop=-1.72+1.28*received, length=Math.max(0.08,-0.1-moundTop); stream.scale.y=length/1.4; stream.position.y=(-0.1+moundTop)/2; stream.visible=state.running&&progress>0.006&&received<0.995; grains.visible=stream.visible;
    if(stream.visible){for(let i=0;i<count;i+=1){const travel=((time*0.00145+seeds[i]*2.3)%1)*length, flutter=reducedMotion?0:Math.sin(time*0.009+i*2.1)*0.015;matrix.makeTranslation(flutter+Math.sin(i*7.3)*0.018,-0.1-travel,Math.cos(i*4.7)*0.018);grains.setMatrixAt(i,matrix);}grains.instanceMatrix.needsUpdate=true;}
    group.rotation.y=reducedMotion?0:Math.sin(time*0.0012)*0.025;
  }
  return {object:group,update};
}
