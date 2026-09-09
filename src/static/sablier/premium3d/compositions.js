// Compositions à échelle métrique, matériaux procéduraux et scans locaux CC0.
// Le kit mutualise la fabrication ; chaque lieu possède ses propres plans et volumes.
import * as kit from './world-kit.js';
import {rockMaps, barkMaps, waterNormal, foliageSprite, radialSprite} from './textures.js';
import {fbm} from './noise.js';
import {materialLibrary} from './scanned-materials.js';
import {atmosphericPlanet,galacticDust} from './cosmic-surfaces.js';

function workshop(T, mobile) {
  const root = new T.Group(), updates = [], random = kit.stream(921);
  const unitBox = new T.BoxGeometry(1,1,1), unitLeaf = new T.PlaneGeometry(1,1);
  const scan=materialLibrary(T);
  const materials = new Map();
  function mat(color, type = 'stone', extra = {}) {
    const key = JSON.stringify([color,type,extra]);
    if (!materials.has(key)) {
      const maps = type === 'wood' ? barkMaps(T) : type === 'stone' ? rockMaps(T) : {};
      materials.set(key,new T.MeshStandardMaterial({color,roughness:type==='metal'?.32:type==='ice'?.17:.88,
        metalness:type==='metal'?.65:0,normalMap:maps.normalMap,normalScale:new T.Vector2(.16,.16),...extra}));
      scan(materials.get(key),type,type==='bark'?[2,7]:type==='rock'?[4,4]:[2,2]);
    }
    return materials.get(key);
  }
  function mesh(geometry, material, p, s) {
    const m = new T.Mesh(geometry,material); m.position.set(...p); if(s)m.scale.set(...s);
    m.castShadow=true; m.receiveShadow=true; root.add(m); return m;
  }
  const box=(p,s,c='#62645c',type='stone')=>mesh(unitBox,mat(c,type),p,s);
  function rock(p,s,c='#59615a') {
    const g=new T.SphereGeometry(1,24,16),pos=g.attributes.position;
    for(let i=0;i<pos.count;i++) {
      const x=pos.getX(i),y=pos.getY(i),z=pos.getZ(i),n=1+fbm(x*4+y,z*4+1,3)*.35;
      pos.setXYZ(i,x*n,y*n,z*n);
    }
    g.computeVertexNormals();return mesh(g,mat(c,'rock'),p,s);
  }
  function rod(a,b,r,c,type='wood',rTop=r) {
    const start=new T.Vector3(...a),end=new T.Vector3(...b),d=end.clone().sub(start);
    const m=mesh(new T.CylinderGeometry(rTop/r,1,1,9),mat(c,type),start.add(end).multiplyScalar(.5).toArray(),[r,d.length(),r]);
    m.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),d.normalize());return m;
  }
  function glow(p,s,c='#ffd396',intensity=1) {
    return mesh(new T.SphereGeometry(1,12,8),mat(c,'glow',{emissive:c,emissiveIntensity:intensity}),p,s);
  }
  function light(p,c,power=60,reach=25) {const l=new T.PointLight(c,power,reach,2);l.position.set(...p);root.add(l);return l;}
  function add(o) {root.add(o);if(o.userData.update)updates.push(o.userData.update);return o;}
  function floor(c='#53554c',w=100,d=100,type='stone') {
    const material=type==='soil'
      ? scan(new T.MeshStandardMaterial({color:'#b5bb98',roughness:1,normalScale:new T.Vector2(.6,.6)}),'soil',[w/5,d/5])
      : mat(c,type);
    return mesh(unitBox,material,[0,-.15,-d/2+8],[w,.3,d]);
  }
  function planks(x,y,z,w,d,color='#665044') {
    for(let i=0;i<d;i++)box([x,y,z-i],[w,.16,.94],color,'wood');
  }
  function tree(x,z,h=18,color='#446044',y=0,kind='broad') {
    const trunk='#aaa08b';rod([x,y,z],[x+.6,y+h*.85,z],h*.047,trunk,'bark',h*.017);
    for(let i=0;i<7;i++) {
      const a=i*2.4,level=y+h*(.4+i*.067),r=h*(kind==='pine'?.22:.32)*(1-i*.065);
      const end=[x+Math.cos(a)*r,level+h*.14,z+Math.sin(a)*r];
      rod([x,level,z],end,h*.013,trunk,'bark',h*.003);
      if(kind==='pine')mesh(new T.ConeGeometry(r,h*.28,10),mat(color,'leaf'),[x,level+h*.12,z]);
      else {
        const leafMat=mat(color,'leaf',{map:foliageSprite(T,color,17),alphaTest:.35,side:T.DoubleSide});
        for(let j=0;j<3;j++) {
          const leaf=mesh(unitLeaf,leafMat,[...end],[r*2.2,h*.4,1]);
          leaf.rotation.y=j*Math.PI/3;
        }
      }
    }
  }
  function arch(x,y,z,r=6,color='#8e9181',broken=false) {
    for(let i=0;i<12;i++) {
      if(broken&&i>7&&i<10)continue;
      const a=i/11*Math.PI;
      const m=box([x+Math.cos(a)*r,y+5+Math.sin(a)*r,z],[r*.3,1.15,1.8],color);m.rotation.z=a-Math.PI/2;
    }
    box([x-r,y+2.5,z],[1.2,5,1.8],color);box([x+r,y+2.5,z],[1.2,5,1.8],color);
  }
  function water({x=0,y=0,z=-30,w=60,d=80,kind='pool',color='#345d65',amplitude=.2}={}) {
    const g=new T.PlaneGeometry(w,d,64,64);g.rotateX(-Math.PI/2);
    const normal=waterNormal(T).clone();normal.userData={shared:false};normal.needsUpdate=true;normal.repeat.set(w/12,d/12);
    const m=mesh(g,new T.MeshStandardMaterial({color,roughness:kind==='ice'?.2:.19,metalness:.28,
      normalMap:normal,normalScale:new T.Vector2(.22,.22),envMapIntensity:1.2}),[x,y,z]);
    const pos=g.attributes.position,base=pos.array.slice();
    function update(t) {
      if(kind==='ice')return;
      const seconds=t*.001;
      normal.offset.set(seconds*(kind==='river'?.025:.006),seconds*.009);
      if(kind==='sea') {
        for(let i=0;i<pos.count;i++) {
          const a=base[i*3],b=base[i*3+2];
          pos.setY(i,amplitude*(Math.sin(a*.16+b*.12-seconds*.8)+.35*Math.sin(b*.34-seconds*1.2)));
        }
        pos.needsUpdate=true;g.computeVertexNormals();
      }
    }
    update(0);updates.push(update);return m;
  }
  function windows(x,z,w,h,c='#f5c184') {
    for(let y=3;y<h;y+=4)for(let dx=-w/2+1;dx<w/2;dx+=2.6)
      if(random()>.68)box([x+dx,y,z],[.75,1.25,.04],c,'glow').material=mat(c,'glow',{emissive:c,emissiveIntensity:.55});
  }
  root.userData.update=(time,motion,progress)=>{for(const update of updates)update(time,motion,progress);};
  return {T,mobile,root,updates,random,scan,mat,mesh,box,rock,rod,glow,light,add,floor,planks,tree,arch,water,windows};
}

function rainRoom(k) {
  const {box,rod,mesh,mat,light,windows,updates,T,random,planks}=k;
  planks(0,-.05,6,20,25);
  box([-9,3,-3],[.4,6,22],'#413c39');box([9,3,-3],[.4,6,22],'#413c39');
  box([0,6,-3],[18,.3,22],'#343332');
  // La fenêtre proche occupe le champ, le bureau partage son appui.
  box([0,.48,-7],[18,.95,.45],'#52606a');box([0,5.8,-7],[18,.5,.6],'#343b40');
  for(const x of [-8,-3,3,8])box([x,3.2,-7],[.14,5.2,.25],'#18252d','metal');
  box([0,1.02,-6.7],[18,.14,.8],'#685347','wood');
  box([0,.78,-4.8],[9,.18,2.6],'#795b40','wood');
  for(const x of [-4,4])for(const z of [-3.9,-5.7])box([x,.35,z],[.12,.7,.12],'#282b2d','metal');
  box([1,.9,-4.8],[1.1,.05,.8],'#ded4b7');box([1.5,.99,-5.1],[.7,.15,.5],'#405061');
  rod([-2.7,.9,-5],[-2.7,1.85,-5],.035,'#ad8956','metal');
  mesh(new T.ConeGeometry(.45,.38,24,1,true),mat('#c4985b','metal'),[-2.7,1.9,-5]);
  light([-2.7,1.65,-5],'#ffc779',8,12);
  mesh(new T.CylinderGeometry(.15,.13,.27,20),mat('#a9bab4'),[2.7,1,-4.5]);
  box([0,-.35,-75],[190,.5,135],'#202d33');
  for(let i=0;i<22;i++) {
    const x=(i-10)*6,z=-32-random()*45,h=5+random()*18;
    box([x,h/2,z],[4,h,5],'#1c2d3c');windows(x,z+2.52,4,h);
  }
  // Gouttes attachées au plan de vitre, jamais dans la pièce.
  const drops=[];
  for(let i=0;i<110;i++) {
    const x=(random()-.5)*15,y=1.2+random()*4.2;
    const m=mesh(new T.SphereGeometry(1,5,4),mat('#99b7c7','ice',{transparent:true,opacity:.46}),[x,y,-6.98],[.014,.03+random()*.075,.008]);
    drops.push({m,y,speed:.08+random()*.1});
    m.userData.dynamic=true;
  }
  updates.push(t=>{for(const d of drops)d.m.position.y=1.15+(d.y-1.15+4.3-t*.001*d.speed%4.3)%4.3;});
  if(k.mobile) {
    // Le même bureau ; rapprocher la lampe du centre pour le cadre portrait.
    for(const child of k.root.children)if(Math.abs(child.position.x+2.7)<.01)child.position.x=-.9;
  }
}

function forest(k) {
  const {floor,tree,rod,rock,mesh,mat,random,T}=k;
  floor('#303d2b',180,220,'soil');
  for(let i=0;i<25;i++) {
    const z=-7-i*4,x=(i%2?-1:1)*(5+random()*32);
    tree(x,z,23+random()*18,'#314b34');
    if(i<8)for(let j=0;j<4;j++)rod([x,.25,z],[x+Math.cos(j*1.8)*4,.04,z+Math.sin(j*1.8)*4],.2,'#493c2a');
  }
  rod([-5,.7,-14],[4,.45,-20],.6,'#4c4030');
  const frond=new T.Shape();frond.moveTo(0,0);
  for(let j=0;j<10;j++){const y=j*.13,w=Math.sin(j/10*Math.PI)*.21;frond.lineTo(w,y);frond.lineTo(.02,y+.065);}
  frond.lineTo(0,1.4);
  for(let j=9;j>=0;j--){const y=j*.13,w=Math.sin(j/10*Math.PI)*.21;frond.lineTo(-w,y);frond.lineTo(-.02,y-.025);}
  const frondGeometry=new T.ShapeGeometry(frond);
  for(let i=0;i<35;i++) {
    const x=(random()-.5)*32,z=-6-random()*55;
    rock([x,.2,z],[.8,.3,.6],'#46513b');
    for(let j=0;j<6;j++) {
      const a=j*Math.PI/3;
      const leaf=mesh(frondGeometry,mat('#567447','leaf',{side:T.DoubleSide}),[x+Math.cos(a)*.25,.03,z+Math.sin(a)*.25]);
      leaf.rotation.set(-.6,a,.5);
    }
  }
}

function coast(k) {
  const {rock,water,box}=k;
  // Le promontoire s'arrête devant l'observateur ; aucun terrain ne couvre l'océan.
  rock([-7,-11,0],[18,13,19],'#6a746a');rock([0,-.7,3],[12,.7,17],'#727465');
  water({y:-17,z:-300,w:1400,d:1100,kind:'sea',color:'#316c7b',amplitude:1.1});
  for(const [x,z,h] of [[-46,-105,43],[43,-190,36],[110,-310,57]]) {
    const spire=rock([k.mobile?x*.5:x,h/2-24,z],[13,h/2+9,16],'#687777');
    spire.rotation.z=.08;
  }
  for(let i=0;i<9;i++)rock([-10+i*1.5,-.1,-5-i*.4],[1.2,.65,1],'#707262');
}

function station(k) {
  const {floor,box,rod,add,light,mat,mesh,T}=k;
  floor('#303d49',30,24);
  box([-10,4,-3],[1,9,22],'#333e4b','metal');box([10,4,-3],[1,9,22],'#333e4b','metal');
  box([0,8,-4],[21,.6,22],'#303b48','metal');
  for(const x of (k.mobile?[-9,-1.9,1.9,9]:[-9,-4,4,9]))rod([x,0,-10],[x*.85,8,-10],.12,'#aab8c1','metal');
  box([0,.5,-10],[19,1,.5],'#566371','metal');box([0,7.7,-10],[19,.5,.5],'#566371','metal');
  for(const x of [-7,7]) {
    box([x,.8,-6],[3,1.6,1.8],'#34424f','metal');
    const screen=box([x,1.64,-6],[2.7,.03,1.1],'#76c7dd');screen.material=mat('#326172','glow',{emissive:'#58b8d4',emissiveIntensity:.6});
    light([x,2,-6],'#81caff',12,8);
  }
  const planetX=k.mobile?0:45;
  add(atmosphericPlanet(T,60,[planetX,45,-330]));
  // Orbite fine : le contour de la baie reste le repère d'échelle.
  const ring=mesh(new T.TorusGeometry(83,.45,6,100),mat('#bba884','metal'),[planetX,45,-330]);ring.rotation.x=1.13;ring.rotation.z=.25;
  add(kit.particles(T,{kind:'star',count:400,area:[1100,600,180],origin:[0,50,-650],size:.8,opacity:.7}));
}

function river(k,{width=7,length=160,color='#406e78',bend=18,y=.03}={}) {
  const g=new k.T.PlaneGeometry(width,length,10,90);g.rotateX(-Math.PI/2);
  const p=g.attributes.position;
  for(let i=0;i<p.count;i++){const z=p.getZ(i)-length/2;p.setXYZ(i,p.getX(i)+Math.sin(-z/length*7)*bend,y,z);}
  g.computeVertexNormals();
  const normal=waterNormal(k.T).clone();normal.userData={shared:false};normal.needsUpdate=true;normal.repeat.set(3,30);
  const surface=k.mesh(g,new k.T.MeshStandardMaterial({color,normalMap:normal,normalScale:new k.T.Vector2(.25,.25),roughness:.18,metalness:.25}),[0,0,0]);
  k.updates.push(t=>normal.offset.y=-t*.00002);return surface;
}

function starTree(k) {
  k.water({y:-1,z:-160,w:600,d:550,color:'#163b49'});
  k.rock([0,-5,-35],[24,6,38],'#354037');
  k.tree(-4,-45,29,'#46634d');
  for(let i=0;i<17;i++) {
    const a=i*2.4,r=3+i%4,x=-4+Math.cos(a)*r,y=13+Math.sin(a*.5)*5,z=-45+Math.sin(a)*5;
    k.rod([x,y+1,z],[x,y,z],.018,'#766342');
    k.glow([x,y,z],[.2,.34,.2],'#ffd894',1.5);
    k.glow([x,-.94,z+8],[.18,.014,.9],'#eab77b',.6);
  }
  k.light([-4,12,-43],'#ffd393',65,30);
  k.add(kit.particles(k.T,{kind:'star',count:250,area:[500,180,200],origin:[0,90,-350],size:.65,opacity:.7}));
}

function fountain(k) {
  k.floor('#35545c');k.rock([0,22,-100],[58,60,22],'#50666b');
  for(let tier=0;tier<4;tier++) {
    const y=tier*12,z=-26-tier*17,w=42-tier*5;
    k.box([0,y-1,z],[w,2,13],'#92a9a0');
    k.water({y:y+.1,z,w:w-3,d:9,color:'#469798'});
    for(const side of [-1,1]) {
      const x=side*(w/2-3);
      k.box([x,y+4,z-3],[4,8,6],'#7f9693');
      k.arch(x,y+1,z+.1,1.1,'#c0cab2');
      k.glow([x,y+5,z+.15],[.3,.8,.05],'#a0ded5',.45);
    }
    if(tier)for(const side of [-1,1]) {
      const x=side*(8-tier*1.3),fall=k.box([x,y-6,z+6.6],[1.8,12,.1],'#70cfce');
      fall.material=k.mat('#64c7cb','water',{transparent:true,opacity:.67,emissive:'#3b7179',emissiveIntensity:.3});
      for(let j=0;j<7;j++) {
        const drop=k.box([x-.7+j*.23,y-6,z+6.72],[.05,2.8,.04],'#b9eeee');
        drop.userData.dynamic=true;
        k.updates.push(t=>drop.position.y=y-((t*.005+j*1.7)%12));
      }
    }
  }
}

function eden(k) {
  k.floor('#567246',160,240);
  for(let i=0;i<4;i++){k.box([i%2?-25:25,i*.45,-24-i*20],[24,1+i*.9,15],'#6e815c');}
  river(k,{width:5,bend:10,color:'#56978c'});k.tree(10,-56,37,'#5b9650');
  for(let i=0;i<16;i++)k.tree((i%2?-1:1)*(24+k.random()*30),-20-i*8,12+k.random()*9,'#649456');
  for(let i=0;i<25;i++)k.rock([(k.random()-.5)*40,.3,-8-k.random()*65],[1,.45,1],'#739757');
}

function timeRiver(k) {
  k.floor('#34414d',220,280);river(k,{width:18,bend:22,color:'#426580',y:.12});
  for(let i=0;i<5;i++) {
    const z=-23-i*25,x=Math.sin(-z/160*7)*22+(i%2?-17:17);
    k.arch(x,0,z,5+i*.3,'#788997',i%2===0);
    k.rock([x+6,.6,z+5],[3,1.2,2],'#697986');
  }
  for(let i=0;i<8;i++) {
    const z=-15-i*17,x=Math.sin(-z/160*7)*22;
    const fragment=k.glow([x,1,z],[.16,.08,.25],'#aacaf5',.6);
    fragment.userData.dynamic=true;
    k.updates.push(t=>fragment.position.z=z+(t*.0005)%3);
  }
}

function memories(k) {
  k.planks(0,-.05,5,24,35);
  k.box([0,4,-17],[22,8,.4],'#666071');k.box([-11,4,-8],[.3,8,18],'#514f5e');
  k.box([11,4,-8],[.3,8,18],'#514f5e');
  for(let i=0;i<7;i++) {
    const x=(i-3)*2.5,y=3.5+(i%3)*.7,w=1.1+(i%2)*.4;
    k.box([x,y,-16.7],[w+.18,1.6,.13],'#aa8a5f','wood');k.box([x,y,-16.59],[w,1.4,.03],i%2?'#696f72':'#958581');
    k.rock([x,y-.1,-16.54],[w*.32,.42,.02],i%2?'#a09b8c':'#454e57');
  }
  k.box([-3,.75,-11],[5,1.5,1.8],'#857366','wood');
  k.box([3,.8,-9],[3.2,.3,2.2],'#66504a','wood');
  for(const x of [1.7,4.3])for(const z of [-8.2,-9.8])k.box([x,.35,z],[.15,.7,.15],'#59463d','wood');
  k.box([5,1.25,-13],[2.8,1.5,.6],'#785958','wood');k.box([5,.6,-12],[2.8,.3,2],'#785958','wood');
  for(const x of [-8,8]) {
    const g=new k.T.PlaneGeometry(2.4,6.5,32,8),p=g.attributes.position;
    for(let i=0;i<p.count;i++)p.setZ(i,Math.sin(p.getX(i)*12)*.12);
    g.computeVertexNormals();const curtain=k.mesh(g,k.mat('#b7a99a','cloth',{side:k.T.DoubleSide}),[x,3.6,-15]);
    curtain.userData.dynamic=true;
    k.updates.push(t=>curtain.rotation.y=Math.sin(t*.0002)*.018);
  }
  k.light([-8,4,-11],'#edc39c',28,25);
}

function galaxy(k) {
  k.add(galacticDust(k.T));
  const positions=[],colors=[],color=new k.T.Color();
  for(let i=0;i<6500;i++) {
    const r=Math.pow(k.random(),.58)*220,arm=i%4,a=arm*Math.PI/2+r*.031+(k.random()-.5)*.55;
    const x=Math.cos(a)*r,y=Math.sin(a)*r*.36+(k.random()-.5)*12;
    positions.push(x,y+68,-340+Math.sin(a)*r*.35);
    color.setHSL(.60+(r/220)*.18,.2+r/700,.48+k.random()*.4);colors.push(color.r,color.g,color.b);
  }
  const g=new k.T.BufferGeometry();g.setAttribute('position',new k.T.Float32BufferAttribute(positions,3));g.setAttribute('color',new k.T.Float32BufferAttribute(colors,3));
  k.root.add(new k.T.Points(g,new k.T.PointsMaterial({size:.3,vertexColors:true,transparent:true,opacity:.4,sizeAttenuation:true})));
  for(let i=0;i<7;i++) {
    const sprite=new k.T.Sprite(new k.T.SpriteMaterial({map:radialSprite(k.T,[['rgba(255,255,255,.5)',0],['rgba(255,255,255,.08)',.45],['rgba(255,255,255,0)',1]]),color:i%2?'#694a9c':'#b8819b',transparent:true,opacity:.28,depthWrite:false,blending:k.T.AdditiveBlending}));
    sprite.position.set((i-3)*48,70+Math.sin(i)*20,-400);sprite.scale.set(140,75,1);k.root.add(sprite);
  }
  k.add(kit.particles(k.T,{kind:'star',count:600,area:[1000,700,200],origin:[0,70,-700],size:.6,opacity:.6}));
}

function clouds(k,y,z,color='#d3dde0',width=350) {
  const map=radialSprite(k.T,[['rgba(255,255,255,.9)',0],['rgba(255,255,255,.5)',.5],['rgba(255,255,255,0)',1]]);
  for(let i=0;i<14;i++) {
    const s=new k.T.Sprite(new k.T.SpriteMaterial({map,color,transparent:true,opacity:.55,depthWrite:false}));
    s.position.set((i-7)*width/9,y+Math.sin(i*1.8)*width*.03,z-(i%3)*30);s.scale.set(width*.45,width*.16,1);k.root.add(s);
    const x=s.position.x;k.updates.push(t=>s.position.x=x+Math.sin(t*.00005)*3);
  }
}

function heaven(k) {
  clouds(k,0,-230,'#cddde4',450);
  for(const [x,y,z,r] of [[-28,5,-55,15],[21,23,-105,20],[0,46,-210,28]]) {
    k.rock([x,y-r*.38,z],[r,r*.5,r*.85],'#879497');
    for(let j=0;j<5;j++)k.rock([x+Math.sin(j*2.3)*r*.35,y-r*(.75+j*.12),z+Math.cos(j*2.3)*r*.3],[r*(.45-j*.065),r*.65,r*(.42-j*.055)],'#78888c');
    k.mesh(new k.T.CylinderGeometry(r,r*.94,1.3,32),k.mat('#d7d2b6'),[x,y,z]);
    for(const a of [0,Math.PI/2,Math.PI,Math.PI*1.5])k.rod([x+Math.cos(a)*r*.48,y,z+Math.sin(a)*r*.48],[x+Math.cos(a)*r*.48,y+12,z+Math.sin(a)*r*.48],.4,'#d6dbd3','stone');
    k.mesh(new k.T.ConeGeometry(r*.72,4,8),k.mat('#bbcbd0'),[x,y+14,z]);
  }
  k.box([0,-.3,1],[15,.6,18],'#c1c4bd');
}

function palm(k,x,z,h) {
  k.rod([x,0,z],[x+1,h,z],.3,'#786345','wood',.16);
  for(let i=0;i<9;i++) {
    const a=i*Math.PI*2/9,end=[x+1+Math.cos(a)*4,h-1,z+Math.sin(a)*4];
    k.rod([x+1,h,z],end,.06,'#536e3a','wood',.01);
    for(let j=1;j<6;j++) {
      const t=j/6,l=k.mesh(new k.T.PlaneGeometry(1.4,.28),k.mat('#648341','leaf',{side:k.T.DoubleSide}),[x+1+Math.cos(a)*4*t,h-.9*t,z+Math.sin(a)*4*t]);l.rotation.set(-.6,-a,.3);
    }
  }
}
function oasis(k) {
  k.add(kit.terrain(k.T,{profile:'dunes',size:600,segments:85,color:'#ad8250',material:'sand',height:.65,shelter:40}));
  const pool=k.water({z:-23,w:28,d:22,color:'#43796e'});pool.geometry.dispose();pool.geometry=new k.T.CircleGeometry(1,64);pool.geometry.rotateX(-Math.PI/2);pool.scale.set(14,1,11);
  for(let i=0;i<10;i++){const a=i/10*Math.PI*2;palm(k,Math.cos(a)*17,-23+Math.sin(a)*14,8+i%4);}
  for(let i=0;i<20;i++){const a=i*.8;k.rock([Math.cos(a)*16,.2,-23+Math.sin(a)*13],[1.6,.6,1.2],'#748149');}
}

function abyss(k) {
  k.floor('#3e6264',180,200);
  k.arch(0,0,-36,9,'#527b7b',true);k.arch(-22,0,-65,6,'#55716e',true);
  k.rock([12,1,-30],[7,3,5],'#436b65');k.box([0,-.2,-36],[22,1,18],'#5e7773');
  for(let i=0;i<24;i++) {
    const x=(k.random()-.5)*65,z=-12-k.random()*65;
    k.rod([x,0,z],[x+.3,2+k.random()*2,z],.1,i%2?'#68888a':'#817891','wood',.03);
    k.rod([x,1,z],[x-1.1,2.5,z],.06,'#68888a','wood',.01);
  }
  for(let i=0;i<14;i++) {
    const fish=k.rock([-8+i*.7,4+Math.sin(i)*.5,-23-i%3],[.28,.1,.08],'#87b6bc'),x=fish.position.x;
    fish.userData.dynamic=true;
    k.updates.push(t=>fish.position.x=x+Math.sin(t*.00012)*5);
  }
  k.add(kit.particles(k.T,{kind:'dust',count:55,size:.13,area:[65,20,65],origin:[0,0,-35],opacity:.3,color:'#91c6c8'}));
  k.add(kit.lightShafts(k.T,{count:3,height:65,width:5,depth:[32,65],spread:22,opacity:.06,color:'#75adb2'}));
}

function mountain(k,x,z,h,snow=true) {
  const g=new k.T.PlaneGeometry(h*2.5,h*2.4,55,55);g.rotateX(-Math.PI/2);
  const p=g.attributes.position,colors=[];
  const base=new k.T.Color('#526572'),cap=new k.T.Color('#dce3e4');
  for(let i=0;i<p.count;i++) {
    const px=p.getX(i),pz=p.getZ(i),r=Math.hypot(px/h,pz/h);
    const n=fbm(px*.065+x,pz*.065+z,4),ridge=Math.abs(Math.sin(px*.024+pz*.035));
    const y=Math.pow(Math.max(0,1-r/1.25),1.6)*h*(.72+ridge*.38+n*.22);
    p.setY(i,y);const c=snow&&y>h*.47+n*h*.05?cap:base;colors.push(c.r,c.g,c.b);
  }
  g.setAttribute('color',new k.T.Float32BufferAttribute(colors,3));g.computeVertexNormals();
  return k.mesh(g,k.scan(new k.T.MeshStandardMaterial({vertexColors:true,roughness:.95,normalScale:new k.T.Vector2(.35,.35)}),'rock',[7,7]),[x,-1,z]);
}
function valley(k) {
  k.floor('#758c99',240,300);k.water({z:-75,w:90,d:140,kind:'ice',color:'#618f9a'});
  for(let i=0;i<4;i++)for(const side of [-1,1])mountain(k,side*(105+i*45),-140-i*65,75+i*22);
  for(let i=0;i<14;i++)k.rod([(i-7)*5,.05,-15-i*7],[(i-7)*5+10,.05,-25-i*7],.025,'#b9d6da','ice');
}
function spring(k) {
  k.floor('#6d884d',150,200);river(k,{width:3,bend:5,color:'#608f91'});
  for(let i=0;i<14;i++)k.tree((i%2?-1:1)*(7+i*.7),-12-i*6,10+i%4,'#dcaabd');
  k.rod([-4,3,-4],[-1,4.5,-7],.14,'#654d43');
  k.add(kit.particles(k.T,{kind:'petal',count:25,size:.15,area:[25,8,45],origin:[0,0,-22],opacity:.55,color:'#f7cbda'}));
}
function summer(k) {
  k.floor('#a29c85',80,70);
  for(let i=0;i<6;i++)for(let j=0;j<5;j++)k.box([(i-2.5)*3,-.02,-j*3],[2.95,.1,2.95],(i+j)%2?'#b8af96':'#aaa18a');
  for(const x of [-5,5])for(const z of [-5,-18])k.box([x,2.3,z],[.3,4.6,.3],'#796449','wood');
  for(let i=0;i<12;i++)k.box([0,4.7,-4-i*1.4],[11,.22,.18],'#6d593e','wood');
  k.box([0,4.4,-11],[.22,.4,16],'#796449','wood');
  k.box([-3,.8,-10],[2.4,.18,2],'#a29072');
  for(let i=0;i<4;i++)mountain(k,(i-1.5)*100,-270,60+i*9,false);
  k.tree(16,-38,17,'#6b804d');
}
function autumn(k) {
  k.floor('#585c3e',200,220);k.water({x:20,z:-70,w:42,d:150,color:'#516d73'});
  k.planks(-6,.2,2,5,65,'#776044');
  for(let i=0;i<14;i++)k.tree(-13-i%3*5,-8-i*9,13+i%5,['#a77035','#bd883c','#865638'][i%3]);
  for(let i=0;i<140;i++) {
    const leaf=k.mesh(new k.T.CircleGeometry(.16,5),k.mat(i%2?'#a56a2f':'#c38a46','leaf'),[-9+k.random()*6,.31,-k.random()*65]);leaf.rotation.x=-Math.PI/2;
  }
  k.add(kit.particles(k.T,{kind:'leaf',count:18,size:.18,area:[18,10,60],origin:[-7,0,-30],color:'#c68a45'}));
}
function winter(k) {
  k.floor('#c5d2d7',220,260);for(let i=0;i<5;i++)mountain(k,(i-2)*65,-150-i%2*50,75+i*8);
  k.box([3,3,-35],[12,6,9],'#625449','wood');
  for(const side of [-1,1]) {
    const roof=k.box([3+side*3.3,7,-35],[7.5,.4,11],'#7d837e');roof.rotation.z=-side*.42;
    const snow=k.box([3+side*3.3,7.3,-35],[7.6,.45,11.2],'#dde5e8');snow.rotation.z=-side*.42;
    k.box([3+side*3,3.4,-30.45],[1.8,2,.09],'#e2b86e','glow').material=k.mat('#e6c08d','glow',{emissive:'#efac62',emissiveIntensity:.8});
  }
  k.box([3,1.7,-30.4],[1.6,3.4,.2],'#443c34','wood');k.box([6,8,-37],[1.1,3,1.1],'#817f76');
  k.light([3,2,-28],'#ffd59c',65,24);
  for(let i=0;i<10;i++)k.tree((i%2?-1:1)*(19+i),-22-i*10,13+i%4,'#aebfbd',0,'pine');
  k.add(kit.particles(k.T,{kind:'snow',count:100,size:.1,area:[70,25,80],origin:[0,0,-35],opacity:.65}));
}
function street(k) {
  k.floor('#303a43',100,180);
  for(const side of [-1,1]) {
    k.box([side*7,.12,-60],[3,.24,140],'#61676b');
    for(let i=0;i<8;i++) {
      const z=-12-i*15,h=14+i%3*4,x=side*12;
      k.box([x,h/2,z],[7,h,13],i%2?'#4d5761':'#596069');
      for(let y=3;y<h;y+=3)for(let j=0;j<3;j++) {
        const win=k.box([side*8.45,y,z-4+j*3],[.04,1.3,1],'#dfbb8a');
        win.material=k.mat('#ad997c','glow',{emissive:'#c39c69',emissiveIntensity:(i+j)%3===0?.7:.02});
      }
    }
  }
  for(let i=0;i<18;i++) {
    const puddle=k.water({x:(k.random()-.5)*9,z:-6-i*6,w:2,d:4,color:'#596b78'});
    const outline=new k.T.Shape();
    for(let j=0;j<=48;j++){
      const a=j/48*Math.PI*2,r=1+Math.sin(a*3+i)*.18+Math.sin(a*7)*.09;
      const x=Math.cos(a)*r,z=Math.sin(a)*r*1.9;
      if(j===0)outline.moveTo(x,z);else outline.lineTo(x,z);
    }
    puddle.geometry.dispose();puddle.geometry=new k.T.ShapeGeometry(outline);puddle.geometry.rotateX(-Math.PI/2);
    puddle.position.y=.015;
    const reflection=k.box([puddle.position.x,.022,puddle.position.z],[.2,.005,1.5],'#bc9c73');reflection.material=k.mat('#bb9b78','glow',{emissive:'#ac794b',emissiveIntensity:.25});
  }
  k.add(kit.particles(k.T,{kind:'rain',count:160,size:.08,area:[15,20,100],origin:[0,0,-48],opacity:.4}));
}
function observatory(k) {
  k.add(kit.terrain(k.T,{profile:'dunes',size:950,segments:110,color:'#b78b53',height:1.25,shelter:18,grain:80}));
  k.add(kit.dome(k.T,{color:'#8b7052',metal:'#666a6d',radius:12,depth:-90,sunk:.55}));
  k.rod([-2,11,-87],[5,17,-84],1,'#343e49','metal');
  for(let i=0;i<6;i++)k.box([-18+i*6,-.3,-60],[4,.3,2],'#a98961');
  k.add(kit.particles(k.T,{kind:'sand',count:45,size:.13,area:[90,6,100],origin:[0,0,-60],opacity:.25,color:'#e1c397'}));
}
function storm(k) {
  k.water({y:-2,z:-300,w:1500,d:1300,kind:'sea',amplitude:2.4,color:'#344854'});
  clouds(k,58,-240,'#56606e',470);clouds(k,90,-390,'#414b59',700);
  k.rock([-7,-4,0],[14,4,12],'#434d50');
  k.add(kit.particles(k.T,{kind:'rain',count:110,size:.1,area:[100,35,130],origin:[0,0,-50],opacity:.35,color:'#9cb3c0'}));
}
function hearth(k) {
  k.floor('#3e3934',35,40);k.box([0,2.2,-12],[12,4.4,1],'#686056');
  for(const x of [-5.5,5.5])k.box([x,1.6,-8],[1,3.2,9],'#70675e');
  k.box([0,.1,-8],[11,.2,9],'#8a8071');
  const coals=[];
  for(let i=0;i<45;i++) {
    const x=(k.random()-.5)*7,z=-6-k.random()*5;
    const coal=k.rock([x,.35+k.random()*.35,z],[.3+k.random()*.4,.3,.35],'#302c29');
    if(i%3===0){coal.material=k.mat('#372321','coal',{emissive:'#c44413',emissiveIntensity:.32});coals.push(coal);}
    k.rod([x,.17,z],[x+.2,.17,z+.4],.02,'#dc6a2f','glow').material=k.mat('#c64717','glow',{emissive:'#ed6b2d',emissiveIntensity:.8});
  }
  const light=k.light([0,1,-8],'#fda666',26,20);
  k.updates.push(t=>{light.intensity=24+Math.sin(t*.0008)*2;});
}
function polar(k) {k.floor('#9eafb9',1800,1800);}
function rooftop(k) {
  k.floor('#59616b',32,32);k.box([0,.65,-14],[32,1.3,.35],'#6c7078');
  for(const x of [-15,15])k.box([x,.65,-4],[.35,1.3,21],'#6c7078');
  for(let i=0;i<32;i++) {
    const x=(i%11-5)*14,z=-70-Math.floor(i/11)*55,h=10+k.random()*37;
    k.box([x,h/2-9,z],[10,h,12],i%2?'#303f50':'#243344');k.windows(x,z+6.02,10,h-9,'#d0af83');
  }
  k.box([-6,.7,-8],[4,.15,1.5],'#7b6b5d','wood');for(const x of [-7.5,-4.5])k.box([x,.35,-8],[.12,.7,1.2],'#3b4148','metal');
  k.mesh(new k.T.CylinderGeometry(.8,.6,1.1,24),k.mat('#806b5b'),[6,.55,-9]);k.tree(6,-9,4,'#475d46');
}

export const COMPOSITIONS = {
  rain_refuge: rainRoom,
  ancient_forest: forest,
  ocean_cliffs: coast,
  interstellar: station,
  star_tree: starTree,
  eternity_fountain: fountain,
  eden,
  time_river: timeRiver,
  memories,
  galaxy,
  heaven,
  oasis,
  abyss,
  aurora_valley: valley,
  spring_meadow: spring,
  summer_terrace: summer,
  autumn_lake: autumn,
  winter_lodge: winter,
  rain_city: street,
  sahara_observatory: observatory,
  storm_cliffs: storm,
  ember_hearth: hearth,
  polar_sky: polar,
  midnight_rooftop: rooftop,
};

export function compose(T,key, mobile=false) {
  const build=COMPOSITIONS[key];if(!build)return null;
  const k=workshop(T,mobile);k.root.name=key;build(k);
  // Les objets proches gardent leurs formes ; les exemplaires statiques partagent un
  // seul appel de dessin. Les pièces animées conservent leur identité et leur géométrie.
  const batches=new Map();
  for(const node of k.root.children) {
    if(!node.isMesh||node.isInstancedMesh||node.userData.dynamic||!node.geometry.parameters)continue;
    const id=node.geometry.type+JSON.stringify(node.geometry.parameters)+node.material.uuid;
    if(!batches.has(id))batches.set(id,[]);batches.get(id).push(node);
  }
  const discarded=new Set();
  for(const nodes of batches.values()) {
    if(nodes.length<3)continue;
    const first=nodes[0],instances=new T.InstancedMesh(first.geometry,first.material,nodes.length);
    instances.castShadow=true;instances.receiveShadow=true;
    nodes.forEach((node,i)=>{node.updateMatrix();instances.setMatrixAt(i,node.matrix);node.removeFromParent();if(node.geometry!==first.geometry)discarded.add(node.geometry);});
    instances.instanceMatrix.needsUpdate=true;k.root.add(instances);
  }
  for(const geometry of discarded)geometry.dispose();
  return k.root;
}
