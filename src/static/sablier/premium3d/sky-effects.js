// Rideaux lumineux avec bords fondus. Le reflet de la vallée est posé sur sa glace.
export function aurora(T,{valley=false}={}) {
  const root=new T.Group(),materials=[];
  const material=()=>{
    const m=new T.ShaderMaterial({transparent:true,depthWrite:false,side:T.DoubleSide,
      blending:T.AdditiveBlending,
      uniforms:{time:{value:0},strength:{value:1}},
      vertexShader:`varying vec2 uvp; void main(){uvp=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
      fragmentShader:`varying vec2 uvp;uniform float time;uniform float strength;
        void main(){float x=uvp.x,y=uvp.y;
          float bottom=.25+sin(x*9.+time*.12)*.11+sin(x*21.-time*.08)*.04;
          float veil=exp(-max(0.,y-bottom)*5.)*smoothstep(bottom-.015,bottom+.02,y);
          float threads=.35+.65*pow(.5+.5*sin(x*220.+sin(x*28.)*2.),2.);
          float edge=smoothstep(0.,.14,x)*smoothstep(1.,.86,x)*smoothstep(1.,.75,y);
          vec3 tint=mix(vec3(.12,.8,.48),vec3(.24,.28,.68),smoothstep(.3,.85,y));
          gl_FragColor=vec4(tint,veil*threads*edge*.65*strength);
        }`});materials.push(m);return m;
  };
  const sky=new T.Mesh(new T.PlaneGeometry(450,130),material());sky.position.set(0,91,-260);root.add(sky);
  if(valley){const reflection=new T.Mesh(new T.PlaneGeometry(80,100),material());reflection.rotation.x=-Math.PI/2;reflection.position.set(0,.07,-63);reflection.material.uniforms.strength.value=.16;root.add(reflection);}
  root.userData.update=t=>{for(const m of materials)m.uniforms.time.value=t*.001;};return root;
}
