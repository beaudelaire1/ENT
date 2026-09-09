// Matières imaginaires calculées : bandes atmosphériques et poussière galactique.
// Aucun défilement ni rotation imposés ; ces détails ne dépendent pas du minuteur.
const noise=`
float hash(vec3 p){p=fract(p*.3183099+vec3(.1,.2,.3));p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
float fbm(vec3 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=noise(p)*a;p=p*2.03+vec3(5.2,1.7,7.3);a*=.5;}return v;}
`;

export function atmosphericPlanet(T,radius,position){
  const material=new T.ShaderMaterial({vertexShader:`varying vec3 vPoint;void main(){vPoint=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`varying vec3 vPoint;${noise}
void main(){
  vec3 p=normalize(vPoint);float n=fbm(p*vec3(5.,15.,5.));
  float bands=sin(p.y*24.+n*5.)*.5+.5;
  vec3 c=mix(vec3(.15,.24,.30),vec3(.28,.36,.40),smoothstep(.15,.9,bands));
  c=mix(c,vec3(.50,.52,.50),smoothstep(.58,.82,n)*.7);
  c*=.75+fbm(p*80.)*.5;
  float sunlight=max(0.,dot(p,normalize(vec3(-.65,.8,.65))));
  c*=.045+pow(sunlight,.65)*.85;
  float rim=pow(1.-max(0.,p.z),4.);
  c+=vec3(.13,.3,.42)*rim*sunlight*.7;
  gl_FragColor=vec4(c,1.);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`});
  const body=new T.Mesh(new T.SphereGeometry(radius,80,48),material);body.position.set(...position);
  return body;
}

export function galacticDust(T){
  const material=new T.ShaderMaterial({transparent:true,depthWrite:false,blending:T.AdditiveBlending,
    vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`varying vec2 vUv;${noise}
void main(){
  vec2 p=(vUv-.5)*2.;p.y*=1.65;float r=length(p),a=atan(p.y,p.x);
  float cloud=fbm(vec3(p*8.,2.)),detail=fbm(vec3(p*48.,8.));
  float spiral=pow(.5+.5*sin(a*2.+log(r+.08)*7.+cloud*3.),3.);
  float disk=exp(-r*3.6)*(1.-smoothstep(.7,1.15,r));
  float dust=smoothstep(.32,.75,detail+cloud*.25);
  float arms=disk*(.18+spiral*.9)*(.2+dust);
  float core=exp(-r*24.)*.8;
  vec3 c=mix(vec3(.22,.31,.48),vec3(.62,.38,.44),cloud)*arms*1.8+vec3(.92,.78,.58)*core;
  gl_FragColor=vec4(c,1.);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`});
  const plane=new T.Mesh(new T.PlaneGeometry(650,400),material);plane.position.set(0,70,-350);plane.rotation.z=-.16;
  return plane;
}
