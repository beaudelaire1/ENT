document.addEventListener("DOMContentLoaded", () => {
  const app = document.querySelector("#focus-app");
  if (!app) return;
  const $ = (selector) => app.querySelector(selector);
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const storageKey = `myent:sablier:${app.dataset.user}`;
  const defaultTotal = Number(app.dataset.total) || 300;
  let state = {total:defaultTotal,remaining:defaultTotal,running:false,finished:false,endsAt:0,mode:app.dataset.mode,intention:$("#session-intention").value,warning:Number(app.dataset.warning)||60,focusLevel:Number(app.dataset.focusLevel)||2,ambience:app.dataset.ambience,decorDensity:Number(app.dataset.decorDensity??2)};
  // Le navigateur garde l'état de la session en cours — c'est lui qui permet de
  // retrouver un décompte exact après une actualisation. Mais les réglages enregistrés
  // sur le serveur font foi dès qu'ils sont plus récents que cette copie locale : sans
  // cet arbitrage, enregistrer ses préférences n'avait aucun effet visible, l'ancienne
  // copie locale les réécrasant à chaque chargement.
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || "{}");
    const settings = ["mode", "ambience", "focusLevel", "decorDensity"];
    const serverIsNewer = String(stored.savedAt || "") !== String(app.dataset.savedAt || "");
    for (const [key, value] of Object.entries(stored)) {
      if (serverIsNewer && settings.includes(key)) continue;
      state[key] = value;
    }
  } catch (_) {}
  // Un lancement depuis une compétence est une intention explicite : il prime sur une
  // ancienne session conservée dans ce navigateur.
  if (app.dataset.contextual === "true") {
    state = {...state,total:defaultTotal,remaining:defaultTotal,running:false,finished:false,endsAt:0,intention:$("#session-intention").value};
  }
  state.savedAt = app.dataset.savedAt || "";
  if (state.running) state.remaining = Math.max(0,(state.endsAt-Date.now())/1000);
  if (state.running && state.remaining <= 0) { state.running=false; state.finished=true; }
  let lastSecond = -1, warningCue=false, frame=0;
  const canvas=$("#timer-canvas"),ctx=canvas.getContext("2d"),finishAudio=$("#finish-audio");
  const decorNames=JSON.parse(document.querySelector("#decor-data").textContent);
  const decor=window.SablierDecor.create($("#decor-canvas"));
  // Les rendus historiques sont les références canoniques. Les images locales
  // apportent leur matière, tandis que Canvas conserve les animations temporelles.
  // Aucun second moteur ne peut ensuite les remplacer par une réinterprétation.
  const assets={};
  try{
    const manifest=window.SABLIER_ASSETS||JSON.parse(document.querySelector("#asset-data")?.textContent||"{}");
    for(const [name,url] of Object.entries(manifest)){
      const img=new Image();img.decoding="async";img.src=url;assets[name]=img;
    }
  }catch(_){}
  const ready=(name)=>Boolean(assets[name]?.complete&&assets[name].naturalWidth>0);

  function parseDuration(value){
    value=value.trim().replace(",","."); let seconds;
    if(!value.includes(":")) seconds=Math.round(Number(value)*60);
    else { const parts=value.split(":").map(Number); if(parts.some(Number.isNaN)||parts.length<2||parts.length>3)return null; seconds=parts.length===2?parts[0]*60+parts[1]:parts[0]*3600+parts[1]*60+parts[2]; }
    return seconds>=1&&seconds<=86400?seconds:null;
  }
  function format(seconds){ const total=Math.max(0,Math.ceil(seconds)),h=Math.floor(total/3600),m=Math.floor((total%3600)/60),s=total%60; return h?`${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`:`${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`; }
  function save(){ localStorage.setItem(storageKey,JSON.stringify(state)); }
  function setDuration(seconds){ state={...state,total:seconds,remaining:seconds,running:false,finished:false,endsAt:0};warningCue=false;save();render(true); }
  function startPause(){
    if(state.finished){reset();}
    if(state.running){state.remaining=Math.max(0,(state.endsAt-Date.now())/1000);state.running=false;}
    else{state.endsAt=Date.now()+state.remaining*1000;state.running=true;}
    save();render(true);
  }
  function reset(){state.running=false;state.finished=false;state.remaining=state.total;state.endsAt=0;warningCue=false;save();render(true);}
  function adjust(seconds){state.remaining=clamp(state.remaining+seconds,0,86400);state.total=Math.max(1,state.total,state.remaining);state.finished=false;if(state.running)state.endsAt=Date.now()+state.remaining*1000;warningCue=false;save();render(true);}
  function resize(){
    const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2),pixelW=Math.max(1,Math.round(rect.width*dpr)),pixelH=Math.max(1,Math.round(rect.height*dpr));
    if(canvas.width!==pixelW||canvas.height!==pixelH){canvas.width=pixelW;canvas.height=pixelH;ctx.setTransform(dpr,0,0,dpr,0,0);}
    return {w:rect.width,h:rect.height};
  }
  function palette(){const css=getComputedStyle(app);return {accent:css.getPropertyValue("--focus-accent").trim(),border:css.getPropertyValue("--focus-border").trim(),text:css.getPropertyValue("--focus-text").trim(),surface:css.getPropertyValue("--focus-surface").trim()};}
  function rgba(color,alpha){const match=/^#([0-9a-f]{6})$/i.exec(color||"");if(!match)return color;const value=Number.parseInt(match[1],16);return `rgba(${value>>16},${(value>>8)&255},${value&255},${alpha})`;}
  function glow(ctx,x,y,r,color,alpha=.22){const gradient=ctx.createRadialGradient(x,y,0,x,y,r);gradient.addColorStop(0,rgba(color,alpha));gradient.addColorStop(.45,rgba(color,alpha*.35));gradient.addColorStop(1,rgba(color,0));ctx.fillStyle=gradient;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();}
  // Contraste des volumes. Chaque visuel réglait ses dégradés au cas par cas et finissait
  // par s'éteindre sur les bords : une forme dont les flancs se fondent dans le fond
  // paraît plus petite qu'elle n'est. Ces deux fonctions donnent un langage commun —
  // flanc éclairé franc, ombre tenue, liseré qui referme la silhouette.
  function litColumn(x0,x1,{accent,text,border}){
    const g=ctx.createLinearGradient(x0,0,x1,0);
    g.addColorStop(0,rgba(border,.98));      // arête d'ombre, opaque : elle tient le bord
    g.addColorStop(.12,rgba(accent,.86));
    g.addColorStop(.34,rgba(text,.97));      // reflet, la zone la plus claire
    g.addColorStop(.55,accent);
    g.addColorStop(.84,rgba(accent,.66));
    g.addColorStop(1,rgba(border,.98));
    return g;
  }
  function limb(color,width,alpha){ctx.strokeStyle=rgba(color,alpha);ctx.lineWidth=width;ctx.stroke();}
  function drawRing(progress){
    const {w,h}=resize(),{accent,border,text}=palette(),cx=w/2,cy=h*.42,r=Math.min(w,h)*.34,line=Math.max(12,r*.072);
    ctx.clearRect(0,0,w,h);glow(ctx,cx,cy,r*1.22,accent,.11);ctx.lineCap="round";
    for(let i=0;i<60;i++){const angle=-Math.PI/2+i*Math.PI*2/60,major=i%5===0,inside=r+line*.9,outside=inside+(major?line*.34:line*.18);ctx.strokeStyle=major?rgba(text,.34):rgba(border,.7);ctx.lineWidth=major?1.5:1;ctx.beginPath();ctx.moveTo(cx+Math.cos(angle)*inside,cy+Math.sin(angle)*inside);ctx.lineTo(cx+Math.cos(angle)*outside,cy+Math.sin(angle)*outside);ctx.stroke();}
    const track=ctx.createLinearGradient(cx-r,cy-r,cx+r,cy+r);track.addColorStop(0,rgba(border,.85));track.addColorStop(.5,rgba(text,.22));track.addColorStop(1,rgba(border,.85));ctx.lineWidth=line;ctx.strokeStyle=track;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();
    if(progress>.001){const end=-Math.PI/2+Math.PI*2*progress,active=ctx.createLinearGradient(cx-r,cy-r,cx+r,cy+r);active.addColorStop(0,rgba(accent,.7));active.addColorStop(.55,accent);active.addColorStop(1,rgba(text,.98));ctx.strokeStyle=active;ctx.shadowColor=accent;ctx.shadowBlur=18;ctx.beginPath();ctx.arc(cx,cy,r,-Math.PI/2,end);ctx.stroke();ctx.shadowBlur=0;ctx.fillStyle=text;ctx.beginPath();ctx.arc(cx+Math.cos(end)*r,cy+Math.sin(end)*r,line*.14,0,Math.PI*2);ctx.fill();}
    ctx.lineWidth=1;ctx.strokeStyle=rgba(text,.13);ctx.beginPath();ctx.arc(cx,cy,r-line*.7,0,Math.PI*2);ctx.stroke();
  }
  function bottlePath(cx,cy,hw,hh){const neck=hw*.1;ctx.beginPath();ctx.moveTo(cx-hw,cy-hh);ctx.bezierCurveTo(cx-hw*.94,cy-hh*.46,cx-hw*.23,cy-hh*.19,cx-neck,cy);ctx.bezierCurveTo(cx-hw*.23,cy+hh*.19,cx-hw*.94,cy+hh*.46,cx-hw,cy+hh);ctx.lineTo(cx+hw,cy+hh);ctx.bezierCurveTo(cx+hw*.94,cy+hh*.46,cx+hw*.23,cy+hh*.19,cx+neck,cy);ctx.bezierCurveTo(cx+hw*.23,cy-hh*.19,cx+hw*.94,cy-hh*.46,cx+hw,cy-hh);ctx.closePath();}
  function drawHourglass(progress){const {w,h}=resize(),{accent,border,text,surface}=palette(),cx=w/2,cy=h*.41,hh=h*.31,hw=Math.min(w*.22,h*.23);ctx.clearRect(0,0,w,h);glow(ctx,cx,cy,Math.max(hw,hh)*1.18,accent,.09);
    // Montants en bois/métal : trois valeurs plutôt qu'un aplat donnent du volume.
    const frame=ctx.createLinearGradient(cx-hw*1.3,0,cx+hw*1.3,0);frame.addColorStop(0,border);frame.addColorStop(.28,rgba(text,.52));frame.addColorStop(.52,surface);frame.addColorStop(.76,rgba(text,.42));frame.addColorStop(1,border);
    ctx.fillStyle=frame;for(const y of [cy-hh-13,cy+hh-1]){ctx.beginPath();ctx.roundRect(cx-hw*1.25,y,hw*2.5,16,7);ctx.fill();ctx.strokeStyle=rgba(text,.22);ctx.lineWidth=1;ctx.stroke();}
    for(const x of [cx-hw*1.08,cx+hw*1.08]){ctx.fillStyle=frame;ctx.beginPath();ctx.roundRect(x-5,cy-hh,10,hh*2,5);ctx.fill();}
    bottlePath(cx,cy,hw,hh);const glass=ctx.createLinearGradient(cx-hw,0,cx+hw,0);glass.addColorStop(0,rgba(text,.2));glass.addColorStop(.18,rgba(text,.045));glass.addColorStop(.5,rgba(accent,.025));glass.addColorStop(.82,rgba(text,.045));glass.addColorStop(1,rgba(text,.2));ctx.fillStyle=glass;ctx.fill();ctx.strokeStyle=rgba(text,.58);ctx.lineWidth=1.6;ctx.stroke();
    // Le sable est éclairé de la gauche comme les autres volumes : un dégradé vertical le
    // faisait s'éteindre vers le bas, où la masse est justement la plus épaisse.
    ctx.save();bottlePath(cx,cy,hw-4,hh-5);ctx.clip();ctx.fillStyle=litColumn(cx-hw,cx+hw,{accent,text,border});
    // Le sable est peint sur toute la largeur et c'est le découpage qui lui donne sa
    // forme : il épouse ainsi exactement la paroi, y compris là où elle s'évase.
    // Le dessiner comme un trapèze à bords droits laissait des vides contre la courbe.
    const topY=cy-hh,floorY=cy+hh,received=1-progress;
    if(progress>.001){
      const surface=cy-(cy-topY)*progress;               // la surface descend vers le col
      ctx.fillRect(cx-hw,surface,hw*2,cy-surface+1);
    }
    let peak=floorY;
    if(received>.001){
      const level=floorY-(floorY-cy)*received;           // le niveau monte du fond vers le col
      const mound=(floorY-cy)*.16*(1-received)*Math.min(1,received*6);
      peak=level-mound;
      ctx.fillRect(cx-hw,level,hw*2,floorY-level+1);
      ctx.beginPath();ctx.moveTo(cx-hw,level+1);ctx.lineTo(cx,peak);ctx.lineTo(cx+hw,level+1);ctx.closePath();ctx.fill();
    }
    if(state.running&&progress>.001){ctx.strokeStyle=rgba(text,.82);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(cx,cy-1);ctx.lineTo(cx,peak);ctx.stroke();ctx.strokeStyle=accent;ctx.lineWidth=2.2;ctx.beginPath();ctx.moveTo(cx+1.5,cy);ctx.lineTo(cx+1.5,peak);ctx.stroke();}
    // Quelques grains rendent les deux masses moins parfaitement numériques.
    ctx.fillStyle=rgba(text,.65);for(let i=0;i<18;i++){const seed=(i*47)%101/101,x=cx-hw*.72+seed*hw*1.44,y=received>.001?floorY-4-((i*29)%70)/70*Math.max(3,(floorY-peak)*.72):cy;ctx.globalAlpha=.18+(i%4)*.08;ctx.beginPath();ctx.arc(x,y,Math.max(.6,hw*.006),0,Math.PI*2);ctx.fill();}ctx.globalAlpha=1;
    ctx.restore();
    // Reflets verticaux sur le verre, interrompus au col.
    ctx.strokeStyle=rgba(text,.28);ctx.lineWidth=Math.max(1,hw*.018);ctx.lineCap="round";for(const side of [-1,1]){ctx.beginPath();ctx.moveTo(cx+side*hw*.68,cy-hh*.72);ctx.quadraticCurveTo(cx+side*hw*.48,cy-hh*.3,cx+side*hw*.14,cy-hh*.08);ctx.stroke();ctx.beginPath();ctx.moveTo(cx+side*hw*.14,cy+hh*.08);ctx.quadraticCurveTo(cx+side*hw*.48,cy+hh*.3,cx+side*hw*.68,cy+hh*.72);ctx.stroke();}
  }
  // Marée : le niveau descend, la surface ondule. La houle n'avance que si le compte
  // à rebours tourne, sinon l'écran bougerait sans que rien ne se passe.
  function drawWave(progress){
    const {w,h}=resize(),{accent,border,text}=palette(),cx=w/2,cy=h*.42,r=Math.min(w,h)*.34;
    ctx.clearRect(0,0,w,h);glow(ctx,cx,cy,r*1.18,accent,.08);
    ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();
    const level=cy+r-2*r*progress,phase=state.running?Date.now()/850:0,water=ctx.createLinearGradient(0,level,0,cy+r);water.addColorStop(0,rgba(text,.76));water.addColorStop(.08,accent);water.addColorStop(.65,rgba(accent,.72));water.addColorStop(1,rgba(border,.9));
    for(let layer=2;layer>=0;layer--){const offset=layer*6,amp=7+layer*3;ctx.globalAlpha=1-layer*.2;ctx.fillStyle=layer===0?water:rgba(accent,.54-layer*.08);ctx.beginPath();ctx.moveTo(cx-r,cy+r);for(let x=cx-r;x<=cx+r;x+=4){const wave=Math.sin(x/(34+layer*19)+phase*(1-layer*.12)+layer*1.7)*amp+Math.sin(x/17-phase*.55)*2;ctx.lineTo(x,level+offset+wave);}ctx.lineTo(cx+r,cy+r);ctx.closePath();ctx.fill();}
    // Écume et reflet : deux traits fins suffisent à donner une surface d'eau.
    ctx.globalAlpha=.72;ctx.strokeStyle=rgba(text,.72);ctx.lineWidth=1.4;ctx.beginPath();for(let x=cx-r;x<=cx+r;x+=4){const y=level+Math.sin(x/34+phase)*7+Math.sin(x/17-phase*.55)*2;x===cx-r?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();
    ctx.globalAlpha=.2;ctx.strokeStyle=text;for(let i=0;i<7;i++){const y=level+18+i*18,width=r*(.12+i*.035);ctx.beginPath();ctx.moveTo(cx-width,y);ctx.lineTo(cx+width,y);ctx.stroke();}
    ctx.restore();ctx.globalAlpha=1;ctx.strokeStyle=rgba(text,.55);ctx.lineWidth=2.4;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();ctx.strokeStyle=rgba(text,.1);ctx.lineWidth=1;ctx.beginPath();ctx.arc(cx,cy,r-5,0,Math.PI*2);ctx.stroke();
  }
  // Bougie mince canonique : sa matière et sa largeur ne dépendent jamais de
  // l'univers. Seule sa hauteur traduit le temps restant.
  function drawCandle(progress){
    const {w,h}=resize(),cx=w/2,
      bodyW=Math.min(w,h)*.235,full=h*.6,base=h*.83,
      top=base-full*progress,radius=bodyW*.16;
    ctx.clearRect(0,0,w,h);
    // Le halo de la flamme est peint d'abord : il baigne la scène, la cire s'y détache.
    if(progress>.004){
      glow(ctx,cx,top-bodyW*.48,bodyW*2.45,"#ff9d32",.24);
      glow(ctx,cx,top-bodyW*.25,bodyW*1.05,"#fff1c2",.12);
    }
    // Bougeoir : assise, fût, et le reflet chaud que la flamme y dépose.
    const holder=ctx.createLinearGradient(cx-bodyW*1.15,0,cx+bodyW*1.15,0);
    holder.addColorStop(0,"#4a2608");holder.addColorStop(.2,"#a96512");
    holder.addColorStop(.46,"#f5d477");holder.addColorStop(.62,"#a66110");holder.addColorStop(1,"#3a1d07");
    ctx.fillStyle=holder;
    ctx.beginPath();ctx.ellipse(cx,base+9,bodyW*1.08,12,0,0,Math.PI*2);ctx.fill();
    limb("#f8d980",1.2,.5);
    ctx.beginPath();ctx.roundRect(cx-bodyW*1.1,base-3,bodyW*2.2,14,7);ctx.fill();limb("#f8d980",1.2,.56);
    ctx.strokeStyle="#d79b32";ctx.lineWidth=Math.max(2,bodyW*.025);
    for(const side of [-1,1]){ctx.beginPath();ctx.ellipse(cx+side*bodyW*1.08,base+4,bodyW*.26,8,0,0,Math.PI*2);ctx.stroke();}
    if(progress>.004){ctx.globalAlpha=.45;glow(ctx,cx,base,bodyW*1.28,"#ffae42",.24);ctx.globalAlpha=1;}
    if(progress>.004){
      const wax=ctx.createLinearGradient(cx-bodyW/2,0,cx+bodyW/2,0);
      wax.addColorStop(0,"#d7c38b");wax.addColorStop(.2,"#f2e3b5");wax.addColorStop(.48,"#fff8dc");wax.addColorStop(.72,"#f2dfac");wax.addColorStop(1,"#c9b476");
      ctx.fillStyle=wax;
      ctx.beginPath();ctx.roundRect(cx-bodyW/2,top,bodyW,base-top,radius);ctx.fill();
      // Liseré : c'est lui qui donne sa taille apparente à la bougie.
      limb("#fff5d2",2,.72);
      // Cuvette de cire autour de la mèche, creusée par la flamme.
      ctx.fillStyle="#f5e5b7";ctx.beginPath();ctx.ellipse(cx,top+bodyW*.06,bodyW*.49,bodyW*.12,0,0,Math.PI*2);ctx.fill();
      ctx.fillStyle="#d6a85c";ctx.beginPath();ctx.ellipse(cx,top+bodyW*.065,bodyW*.22,bodyW*.055,0,0,Math.PI*2);ctx.fill();
      ctx.fillStyle="#f2c46d";ctx.beginPath();ctx.ellipse(cx,top+bodyW*.062,bodyW*.12,bodyW*.028,0,0,Math.PI*2);ctx.fill();
      // Mèche puis flamme : cœur blanc, manteau coloré, halo. Trois valeurs, sinon la
      // flamme n'est qu'une tache de la couleur d'ambiance.
      const flicker=state.running?Math.sin(Date.now()/90)*bodyW*.02:0,flameH=bodyW*.62;
      ctx.strokeStyle="#24170c";ctx.lineWidth=Math.max(2,bodyW*.035);
      ctx.beginPath();ctx.moveTo(cx,top+2);ctx.quadraticCurveTo(cx+bodyW*.03,top-bodyW*.08,cx-bodyW*.02,top-bodyW*.17);ctx.stroke();
      ctx.beginPath();ctx.moveTo(cx,top-flameH-flicker);
      ctx.quadraticCurveTo(cx+bodyW*.22,top-flameH*.33,cx,top-2);
      ctx.quadraticCurveTo(cx-bodyW*.22,top-flameH*.33,cx,top-flameH-flicker);
      ctx.fillStyle="#ff9d32";ctx.shadowColor="#ff8b25";ctx.shadowBlur=bodyW*.55;ctx.fill();ctx.shadowBlur=0;
      ctx.fillStyle="#fff0b8";
      ctx.beginPath();ctx.moveTo(cx,top-flameH*.66-flicker*.5);
      ctx.quadraticCurveTo(cx+bodyW*.09,top-flameH*.26,cx,top-bodyW*.035);
      ctx.quadraticCurveTo(cx-bodyW*.09,top-flameH*.26,cx,top-flameH*.66-flicker*.5);ctx.fill();
      ctx.fillStyle="rgba(255,255,255,.82)";
      ctx.beginPath();ctx.ellipse(cx,top-bodyW*.1,bodyW*.06,bodyW*.13,0,0,Math.PI*2);ctx.fill();
    }else{
      // Mèche éteinte : un filet de fumée plutôt qu'une bougie disparue.
      ctx.globalAlpha=.45;ctx.strokeStyle="#d9dee2";ctx.lineWidth=Math.max(2,bodyW*.03);ctx.lineCap="round";
      ctx.beginPath();ctx.moveTo(cx,base-6);
      ctx.quadraticCurveTo(cx+bodyW*.28,base-bodyW*.7,cx-bodyW*.12,base-bodyW*1.3);
      ctx.stroke();ctx.globalAlpha=1;
    }
  }
  // Perles : un collier vivant se défait au fil du temps. Les perles écoulées
  // quittent le fil et se déposent sur le plateau, au lieu de rester une grille fixe.
  function drawBeads(progress){
    const {w,h}=resize(),{accent,border,text,surface}=palette(),unit=Math.min(w,h),total=24,
      remaining=Math.ceil(progress*total),cx=w/2,cy=h*.38,rx=unit*.29,ry=unit*.205,r=unit*.031,
      shimmer=state.running?Date.now()/720:0;
    ctx.clearRect(0,0,w,h);glow(ctx,cx,cy,unit*.48,accent,.1);
    // Fil satiné et fermoir : l'ellipse reste entière, les vides rendent les perles
    // déjà écoulées immédiatement lisibles.
    const cord=ctx.createLinearGradient(cx-rx,0,cx+rx,0);cord.addColorStop(0,rgba(border,.65));cord.addColorStop(.5,rgba(text,.62));cord.addColorStop(1,rgba(border,.65));
    ctx.strokeStyle=cord;ctx.lineWidth=Math.max(1.2,unit*.004);ctx.beginPath();ctx.ellipse(cx,cy,rx,ry,0,0,Math.PI*2);ctx.stroke();
    ctx.fillStyle=rgba(text,.7);ctx.beginPath();ctx.roundRect(cx-unit*.045,cy-ry-r*1.15,unit*.09,unit*.035,unit*.012);ctx.fill();limb(text,1,.45);
    // Plateau de réception, volontairement bas et discret.
    const trayY=h*.69,tray=ctx.createLinearGradient(cx-unit*.3,0,cx+unit*.3,0);tray.addColorStop(0,rgba(border,.72));tray.addColorStop(.45,rgba(text,.78));tray.addColorStop(.62,rgba(surface,.9));tray.addColorStop(1,rgba(border,.72));
    ctx.fillStyle=tray;ctx.beginPath();ctx.ellipse(cx,trayY,unit*.3,unit*.045,0,0,Math.PI*2);ctx.fill();limb(text,1.2,.3);
    const pearl=(x,y,active,index,scale=1)=>{
      const pr=r*scale,pulse=active&&state.running?1+Math.sin(shimmer*4+index*1.73)*.035:1,
        nacre=ctx.createRadialGradient(x-pr*.38,y-pr*.42,pr*.04,x,y,pr);
      if(active){nacre.addColorStop(0,"rgba(255,255,255,.98)");nacre.addColorStop(.16,"rgba(225,249,255,.96)");nacre.addColorStop(.48,rgba(accent,.78));nacre.addColorStop(.78,rgba(text,.58));nacre.addColorStop(1,rgba(border,.94));}
      else{nacre.addColorStop(0,rgba(text,.52));nacre.addColorStop(.28,rgba(surface,.9));nacre.addColorStop(.72,rgba(border,.94));nacre.addColorStop(1,rgba(border,.99));}
      ctx.save();ctx.fillStyle=nacre;ctx.shadowColor=active?accent:"rgba(0,0,0,.65)";ctx.shadowBlur=active?pr*.85:pr*.42;ctx.beginPath();ctx.arc(x,y,pr*pulse,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
      ctx.strokeStyle=rgba(text,active ? .58 : .2);ctx.lineWidth=Math.max(.7,pr*.055);ctx.stroke();ctx.fillStyle="rgba(255,255,255,.78)";ctx.beginPath();ctx.ellipse(x-pr*.34,y-pr*.38,pr*.16,pr*.1,-.55,0,Math.PI*2);ctx.fill();ctx.restore();
    };
    for(let i=0;i<total;i++){
      if(i<remaining){const a=-Math.PI/2+(i/total)*Math.PI*2,x=cx+Math.cos(a)*rx,y=cy+Math.sin(a)*ry;pearl(x,y,true,i);}
      else{const fallen=i-remaining,row=Math.floor(fallen/8),col=fallen%8,x=cx+(col-3.5)*r*1.72+(row%2?r*.75:0),y=trayY-r*.65-row*r*1.45;pearl(x,y,false,i,.92);}
    }
  }
  // Lune : elle décroît comme le temps restant, de la pleine lune au croissant.
  function drawMoon(progress){
    const {w,h}=resize(),{accent,border,text,surface}=palette(),cx=w/2,cy=h*.44,r=Math.min(w,h)*.37;
    ctx.clearRect(0,0,w,h);
    glow(ctx,cx,cy,r*1.6,accent,.2);
    // Le disque sombre : c'est la lumière qui recule, pas la lune. Sans lui, un croissant
    // flottait seul et l'astre paraissait rétrécir au fil du décompte.
    const shadowed=ctx.createRadialGradient(cx-r*.3,cy-r*.35,r*.1,cx,cy,r);
    shadowed.addColorStop(0,rgba(border,.5));shadowed.addColorStop(.7,rgba(border,.34));shadowed.addColorStop(1,rgba(border,.2));
    if(progress<=.001){
      ctx.fillStyle=shadowed;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();
      ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);limb(text,2,.5);
      ctx.setLineDash([4,9]);ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);limb(text,1.2,.3);ctx.setLineDash([]);
      return;
    }
    ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();
    // Face éclairée : le bord reste lumineux au lieu de s'éteindre, pour que le disque
    // se referme franchement sur le fond.
    const lunar=ctx.createRadialGradient(cx-r*.34,cy-r*.4,r*.06,cx,cy,r*1.06);
    lunar.addColorStop(0,rgba(text,.99));lunar.addColorStop(.28,rgba(text,.9));
    lunar.addColorStop(.62,accent);lunar.addColorStop(1,rgba(accent,.82));
    ctx.fillStyle=lunar;ctx.fillRect(cx-r,cy-r,r*2,r*2);
    // Mers et cratères : intérieur creusé, bord éclairé du côté du soleil.
    for(const [dx,dy,size,a] of [[-.3,-.24,.15,.3],[.26,-.33,.1,.34],[.33,.2,.18,.26],[-.2,.32,.11,.32],[.04,.03,.08,.24],[-.06,-.52,.07,.22],[.5,-.06,.09,.2]]){
      ctx.fillStyle=rgba(surface,a);
      ctx.beginPath();ctx.ellipse(cx+dx*r,cy+dy*r,size*r,size*r*.74,-.3,0,Math.PI*2);ctx.fill();
      limb(border,1.6,a*1.3);
      ctx.beginPath();ctx.ellipse(cx+dx*r-size*r*.1,cy+dy*r-size*r*.12,size*r*.86,size*r*.6,-.3,Math.PI*.9,Math.PI*1.9);limb(text,1.4,a*.9);
    }
    // Un disque d'ombre de même rayon glisse depuis la gauche : entièrement écarté à
    // 100 % (pleine lune), exactement superposé à 0 % (lune noire).
    //
    // La couleur doit être opaque. `destination-out` retire de l'alpha en proportion de
    // celle de la source : le dernier `fillStyle` posé était un cratère à 20 %, si bien
    // que l'ombre n'enlevait qu'un cinquième de la lumière. La lune restait un disque
    // uniformément clair, sans phase lisible — et donc sans forme à percevoir.
    ctx.globalCompositeOperation="destination-out";
    ctx.fillStyle="#000";
    ctx.beginPath();ctx.arc(cx-2*r*progress,cy,r,0,Math.PI*2);ctx.fill();
    // La face nuit est repeinte *derrière* ce qui subsiste. L'effacement emporte tout ce
    // qui se trouve sous lui, disque sombre compris : peint avant, il disparaissait avec
    // la lumière et l'on retombait sur un croissant flottant.
    ctx.globalCompositeOperation="destination-over";
    ctx.fillStyle=shadowed;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();
    ctx.globalCompositeOperation="source-over";
    // Terminateur : la frontière jour/nuit se dessine, sinon la coupure paraît plate.
    ctx.beginPath();ctx.arc(cx-2*r*progress,cy,r,0,Math.PI*2);limb(text,1.6,.3);
    ctx.restore();
    ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);limb(text,2,.55);
  }
  // Colonnes : une banque de tubes de verre gradués, remplis d'ambre liquide.
  // La matière descend colonne après colonne ; le châssis reste toujours visible.
  function drawBars(progress){
    const {w,h}=resize(),{border,text,surface}=palette(),count=9,unit=Math.min(w,h),
      span=unit*.74,gap=span/count,barW=gap*.58,base=h*.68,maxH=h*.45,
      alive=progress*count,ox=w/2-span/2,heights=[.54,.76,.64,.88,1,.82,.93,.7,.58];
    ctx.clearRect(0,0,w,h);glow(ctx,w/2,base,span*.62,"#ffad52",.12);
    const plinth=ctx.createLinearGradient(ox,0,ox+span,0);plinth.addColorStop(0,rgba(border,.98));plinth.addColorStop(.24,rgba(text,.7));plinth.addColorStop(.5,rgba(surface,.96));plinth.addColorStop(.76,rgba(text,.65));plinth.addColorStop(1,rgba(border,.98));
    ctx.fillStyle=plinth;ctx.beginPath();ctx.roundRect(ox-gap*.18,base,span+gap*.36,unit*.075,unit*.02);ctx.fill();limb(text,1.2,.36);
    ctx.fillStyle="rgba(255,169,73,.12)";ctx.beginPath();ctx.roundRect(ox,base+unit*.012,span,unit*.034,unit*.012);ctx.fill();
    for(let i=0;i<count;i++){
      const full=maxH*heights[i],x=ox+i*gap+(gap-barW)/2,fill=Math.max(0,Math.min(1,alive-i)),inner=barW*.62;
      const shell=ctx.createLinearGradient(x,0,x+barW,0);shell.addColorStop(0,"rgba(205,231,240,.13)");shell.addColorStop(.18,"rgba(255,255,255,.62)");shell.addColorStop(.42,"rgba(179,213,226,.12)");shell.addColorStop(.78,"rgba(255,255,255,.36)");shell.addColorStop(1,"rgba(117,151,166,.28)");
      ctx.fillStyle=shell;ctx.beginPath();ctx.roundRect(x,base-full,barW,full,barW*.42);ctx.fill();ctx.strokeStyle=rgba(text,.5);ctx.lineWidth=Math.max(1,unit*.002);ctx.stroke();
      if(fill>0){
        const height=Math.max(inner*.3,(full-inner*.16)*fill),ix=x+(barW-inner)/2,top=base-height-inner*.08,
          amber=ctx.createLinearGradient(ix,0,ix+inner,0);amber.addColorStop(0,"#7a3508");amber.addColorStop(.2,"#dc761b");amber.addColorStop(.48,"#ffd07a");amber.addColorStop(.72,"#e58b2e");amber.addColorStop(1,"#6b2b07");
        ctx.fillStyle=amber;ctx.shadowColor="rgba(255,143,43,.65)";ctx.shadowBlur=unit*.018;ctx.beginPath();ctx.roundRect(ix,top,inner,height,inner*.42);ctx.fill();ctx.shadowBlur=0;
        ctx.fillStyle="rgba(255,228,166,.82)";ctx.beginPath();ctx.ellipse(ix+inner/2,top+inner*.12,inner*.48,inner*.15,0,0,Math.PI*2);ctx.fill();
      }
      // Colliers métalliques et graduations donnent une échelle réelle aux niveaux.
      ctx.fillStyle=plinth;ctx.beginPath();ctx.roundRect(x-barW*.08,base-full-barW*.04,barW*1.16,barW*.14,barW*.05);ctx.fill();ctx.beginPath();ctx.roundRect(x-barW*.08,base-barW*.1,barW*1.16,barW*.14,barW*.05);ctx.fill();
      ctx.strokeStyle=rgba(text,.32);ctx.lineWidth=1;for(let tick=1;tick<4;tick++){const y=base-full*tick/4;ctx.beginPath();ctx.moveTo(x+barW*.72,y);ctx.lineTo(x+barW*.96,y);ctx.stroke();}
    }
  }
  // Spirale : un ressort d'horlogerie sous verre, enchâssé dans une platine métallique.
  function drawSpiral(progress){
    const {w,h}=resize(),{border,text,surface}=palette(),cx=w/2,cy=h*.39,
      turns=4.35,maxR=Math.min(w,h)*.31,steps=520;
    ctx.clearRect(0,0,w,h);glow(ctx,cx,cy,maxR*1.45,"#ffad52",.14);
    const plate=ctx.createRadialGradient(cx-maxR*.32,cy-maxR*.38,maxR*.06,cx,cy,maxR*1.08);plate.addColorStop(0,rgba(text,.22));plate.addColorStop(.42,rgba(surface,.94));plate.addColorStop(.78,rgba(border,.98));plate.addColorStop(1,"rgba(3,6,10,.98)");
    ctx.fillStyle=plate;ctx.beginPath();ctx.arc(cx,cy,maxR*1.08,0,Math.PI*2);ctx.fill();ctx.strokeStyle=rgba(text,.7);ctx.lineWidth=Math.max(2,maxR*.025);ctx.stroke();
    ctx.strokeStyle="rgba(255,255,255,.13)";ctx.lineWidth=1;ctx.beginPath();ctx.arc(cx,cy,maxR*.98,0,Math.PI*2);ctx.stroke();
    for(let i=0;i<24;i++){const a=i*Math.PI/12,inner=maxR*.92,outer=maxR*(i%6===0 ? 1.02 : .975);ctx.strokeStyle=rgba(text,i%6===0 ? .5 : .22);ctx.lineWidth=i%6===0 ? 2 : 1;ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*inner,cy+Math.sin(a)*inner);ctx.lineTo(cx+Math.cos(a)*outer,cy+Math.sin(a)*outer);ctx.stroke();}
    const trace=(fraction,color,width,alpha)=>{
      if(fraction<=.0005)return;
      ctx.strokeStyle=color;ctx.lineWidth=width;ctx.globalAlpha=alpha;ctx.lineCap="round";
      ctx.beginPath();
      for(let i=0;i<=steps*fraction;i++){
        const t=i/steps,angle=t*turns*Math.PI*2-Math.PI/2,r=maxR*(.06+.94*t);
        const x=cx+Math.cos(angle)*r,y=cy+Math.sin(angle)*r;
        i?ctx.lineTo(x,y):ctx.moveTo(x,y);
      }
      ctx.stroke();ctx.globalAlpha=1;
    };
    trace(1,"rgba(6,9,13,.96)",maxR*.095,1);trace(1,rgba(text,.35),maxR*.048,1);
    const active=ctx.createLinearGradient(cx-maxR,cy-maxR,cx+maxR,cy+maxR);active.addColorStop(0,"#8d3d08");active.addColorStop(.48,"#ffab42");active.addColorStop(.78,"#ffe0a1");active.addColorStop(1,"#c96814");
    ctx.shadowColor="rgba(255,142,43,.72)";ctx.shadowBlur=maxR*.08;trace(progress,active,maxR*.057,1);ctx.shadowBlur=0;trace(progress,"rgba(255,245,214,.64)",maxR*.012,1);
    const hub=ctx.createRadialGradient(cx-maxR*.04,cy-maxR*.05,1,cx,cy,maxR*.12);hub.addColorStop(0,"#fff1c7");hub.addColorStop(.3,"#ffb14d");hub.addColorStop(.7,"#6f2d08");hub.addColorStop(1,"#19100a");ctx.fillStyle=hub;ctx.beginPath();ctx.arc(cx,cy,maxR*.115,0,Math.PI*2);ctx.fill();limb(text,1.2,.5);
    for(const a of [Math.PI/4,Math.PI*.75,Math.PI*1.25,Math.PI*1.75]){const x=cx+Math.cos(a)*maxR*.9,y=cy+Math.sin(a)*maxR*.9;ctx.fillStyle=rgba(text,.65);ctx.beginPath();ctx.arc(x,y,maxR*.035,0,Math.PI*2);ctx.fill();ctx.strokeStyle=rgba(border,.8);ctx.beginPath();ctx.moveTo(x-maxR*.02,y);ctx.lineTo(x+maxR*.02,y);ctx.stroke();}
    if(progress>.001){const angle=progress*turns*Math.PI*2-Math.PI/2,r=maxR*(.06+.94*progress),x=cx+Math.cos(angle)*r,y=cy+Math.sin(angle)*r;ctx.fillStyle="#fff1c8";ctx.shadowColor="#ff9d32";ctx.shadowBlur=maxR*.14;ctx.beginPath();ctx.arc(x,y,maxR*.04,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;}
  }
  // Soleil : sa course dit l'heure qui reste, du lever au coucher.
  function drawSun(progress){
    const {w,h}=resize(),{accent,border,text}=palette(),cx=w/2,horizon=h*.64,
      arc=Math.min(w,h)*.35,r=Math.min(w,h)*.09;
    ctx.clearRect(0,0,w,h);const dusk=ctx.createLinearGradient(0,h*.12,0,horizon);dusk.addColorStop(0,rgba(accent,0));dusk.addColorStop(1,rgba(accent,.1));ctx.fillStyle=dusk;ctx.fillRect(cx-arc*1.3,h*.1,arc*2.6,horizon-h*.1);
    ctx.strokeStyle=border;ctx.lineWidth=1.5;ctx.globalAlpha=.4;
    ctx.beginPath();ctx.arc(cx,horizon,arc,Math.PI,0);ctx.stroke();      // la trajectoire
    ctx.globalAlpha=.7;ctx.beginPath();ctx.moveTo(cx-arc*1.25,horizon);ctx.lineTo(cx+arc*1.25,horizon);ctx.stroke();
    ctx.globalAlpha=1;
    // Le soleil part de l'ouest à 100 % et se couche à l'est : il descend avec le temps.
    const angle=Math.PI*(1-progress),x=cx+Math.cos(angle)*arc,y=horizon-Math.sin(angle)*arc;
    if(y<=horizon+1){
      glow(ctx,x,y,r*2.6,accent,.24);const disc=ctx.createRadialGradient(x-r*.3,y-r*.35,r*.08,x,y,r);disc.addColorStop(0,rgba(text,.99));disc.addColorStop(.35,accent);disc.addColorStop(1,rgba(accent,.95));ctx.fillStyle=disc;ctx.shadowColor=accent;ctx.shadowBlur=20;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;limb(text,1.6,.45);
      ctx.strokeStyle=rgba(text,.3);ctx.lineWidth=1;for(let i=0;i<12;i++){const a=i*Math.PI/6,inner=r*1.25,outer=r*(1.42+(i%2)*.1);ctx.beginPath();ctx.moveTo(x+Math.cos(a)*inner,y+Math.sin(a)*inner);ctx.lineTo(x+Math.cos(a)*outer,y+Math.sin(a)*outer);ctx.stroke();}
    }
  }
  // ------------------------------------------------------------------
  // Rendus photoréalistes : la photo fournit la matière (verre, chrome, cire,
  // nacre…), le canvas n'anime que ce qui vit — sable, eau, flamme, ombre.
  // Chaque renderer retombe sur le tracé vectoriel tant que sa photo n'est
  // pas chargée : jamais d'écran vide, même hors-ligne.
  // ------------------------------------------------------------------
  // Sablier : le sable est peint DERRIÈRE la photo, dans l'empreinte des
  // ampoules ; la vitre lui garde ainsi ses reflets et ses épaisseurs.
  let hourglassGrainPattern=null;
  function getHourglassGrainPattern(){
    if(hourglassGrainPattern)return hourglassGrainPattern;
    const tile=document.createElement("canvas"),grain=tile.getContext("2d");
    tile.width=128;tile.height=128;
    let seed=0x51ab1e;
    const random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
    for(let i=0;i<1650;i++){
      const x=random()*tile.width,y=random()*tile.height,r=.22+random()*.88,tone=random();
      grain.fillStyle=tone>.78?`rgba(255,239,179,${.28+random()*.5})`:tone>.34?`rgba(210,151,61,${.25+random()*.5})`:`rgba(112,70,22,${.18+random()*.38})`;
      grain.beginPath();grain.arc(x,y,r,0,Math.PI*2);grain.fill();
    }
    hourglassGrainPattern=ctx.createPattern(tile,"repeat");
    return hourglassGrainPattern;
  }
  function drawHourglassPhoto(progress){
    if(!ready("hourglass")){drawHourglass(progress);return;}
    const img=assets.hourglass,{w,h}=resize(),{accent}=palette();
    ctx.clearRect(0,0,w,h);
    // Le fichier source est cadré très verticalement. Une correction horizontale
    // restitue les épaules du verre et l'assise métallique sans rogner l'objet.
    const shapeWidth=1.34,ih=h*.86,iw=ih*img.naturalWidth/img.naturalHeight*shapeWidth,ix=w/2-iw/2,iy=h*.04;
    const cx=w/2,neckY=iy+ih*.479,topY=iy+ih*.108,floorY=iy+ih*.821,hw=iw*.208;
    glow(ctx,cx,neckY,Math.max(iw,ih)*.5,accent,.07);
    // Profil réel des ampoules, mesuré sur la photo : t=0 au col, t=1 à
    // l'extrémité. Le tracé épouse le verre au lieu de le dépasser.
    const profile=[[0,.07],[.08,.22],[.18,.45],[.3,.68],[.42,.86],[.55,.97],[.68,1],[.8,.99],[.9,.94],[1,.86]];
    const bulbPath=(yNeck,yEnd)=>{
      const H=yEnd-yNeck;
      ctx.beginPath();
      profile.forEach(([t,f],i)=>{const y=yNeck+H*t,x=cx-hw*f;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});
      for(let i=profile.length-1;i>=0;i--){const [t,f]=profile[i];ctx.lineTo(cx+hw*f,yNeck+H*t);}
      ctx.closePath();
    };
    // Sable doré : dégradé horizontal, éclairé au centre comme la photo.
    const sand=ctx.createLinearGradient(cx-hw,0,cx+hw,0);
    sand.addColorStop(0,"#9a6826");sand.addColorStop(.28,"#dfae55");sand.addColorStop(.5,"#f6d891");sand.addColorStop(.74,"#d9a04a");sand.addColorStop(1,"#8d5f22");
    const grain=getHourglassGrainPattern();
    const fillSand=(path)=>{
      ctx.fillStyle=sand;path();ctx.fill();
      if(grain){ctx.save();ctx.globalAlpha=.82;ctx.fillStyle=grain;path();ctx.fill();ctx.restore();}
    };
    const received=1-progress;
    if(progress>.001){
      ctx.save();bulbPath(neckY,topY);ctx.clip();
      const surface=neckY-(neckY-topY)*progress;
      fillSand(()=>{ctx.beginPath();ctx.rect(cx-hw,surface,hw*2,neckY-surface+1);});
      // Surface irrégulière et petit creux que le filet creuse dans les grains.
      ctx.strokeStyle="rgba(255,231,165,.72)";ctx.lineWidth=Math.max(.8,iw*.0024);ctx.beginPath();
      for(let x=cx-hw*.9;x<=cx+hw*.9;x+=3){const y=surface+Math.sin(x*.19)*1.15+Math.sin(x*.047)*.75;x===cx-hw*.9?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();
      ctx.fillStyle="rgba(92,53,17,.32)";ctx.beginPath();ctx.ellipse(cx,surface+1,hw*.14,Math.max(1.5,hw*.025),0,0,Math.PI*2);ctx.fill();
      ctx.restore();
    }
    let peak=floorY;
    if(received>.001){
      ctx.save();bulbPath(neckY,floorY);ctx.clip();
      const level=floorY-(floorY-neckY)*received;
      const mound=Math.min(hw*.5,(floorY-neckY)*.32*Math.min(1,received*3.5));
      peak=level-mound;
      fillSand(()=>{ctx.beginPath();ctx.rect(cx-hw,level,hw*2,floorY-level+1);ctx.moveTo(cx-hw*.84,level+2);ctx.bezierCurveTo(cx-hw*.48,level-mound*.12,cx-hw*.2,peak+mound*.16,cx,peak);ctx.bezierCurveTo(cx+hw*.22,peak+mound*.14,cx+hw*.52,level-mound*.1,cx+hw*.84,level+2);ctx.closePath();});
      ctx.strokeStyle="rgba(255,229,160,.52)";ctx.lineWidth=Math.max(.8,iw*.002);ctx.beginPath();ctx.moveTo(cx-hw*.78,level);ctx.quadraticCurveTo(cx-hw*.18,peak+mound*.08,cx,peak);ctx.quadraticCurveTo(cx+hw*.2,peak+mound*.08,cx+hw*.78,level);ctx.stroke();
      ctx.restore();
    }
    if(state.running&&progress>.001){
      const stream=ctx.createLinearGradient(0,neckY,0,peak);
      stream.addColorStop(0,"#f8e0a2");stream.addColorStop(1,"#d99f49");
      ctx.strokeStyle=stream;ctx.lineCap="round";
      ctx.lineWidth=Math.max(1.2,iw*.005);ctx.beginPath();ctx.moveTo(cx,neckY+1);ctx.lineTo(cx,peak);ctx.stroke();
      ctx.lineWidth=Math.max(.6,iw*.002);ctx.strokeStyle="rgba(255,240,200,.9)";ctx.beginPath();ctx.moveTo(cx-iw*.002,neckY+1);ctx.lineTo(cx-iw*.002,peak);ctx.stroke();
      const phase=Date.now()/46;
      for(let i=0;i<18;i++){
        const travel=((phase+i*7.17)%18)/18,y=neckY+(peak-neckY)*travel,x=cx+Math.sin(i*12.7+phase*.15)*iw*.0045;
        ctx.fillStyle=i%3===0?"rgba(255,239,188,.95)":"rgba(205,143,54,.92)";ctx.beginPath();ctx.arc(x,y,Math.max(.55,iw*(.0014+(i%4)*.00028)),0,Math.PI*2);ctx.fill();
      }
    }
    ctx.drawImage(img,ix,iy,iw,ih);
  }
  // Bougie de référence : la cire photographique reste mince et le bougeoir reste
  // fixe. Seuls la hauteur, la flamme et la fumée évoluent avec le temps.
  function drawCandlePhoto(progress){
    if(!ready("candle")){const {w,h}=resize();ctx.clearRect(0,0,w,h);return;}
    const img=assets.candle,{w,h}=resize(),{accent,text}=palette();
    ctx.clearRect(0,0,w,h);
    const baseY=h*.87,fullH=h*.7,iw=Math.min(w*.46,fullH*img.naturalWidth/img.naturalHeight),scale=iw/img.naturalWidth;
    const waxTop=img.naturalHeight*.058,base=img.naturalHeight*.975;
    const topSrc=waxTop+(1-progress)*(base-waxTop),srcH=base-topSrc,dh=srcH*scale,dx=w/2-iw/2,dy=baseY-dh,fx=w/2;
    if(progress>.004){glow(ctx,fx,dy-iw*.12,iw*1.1,accent,.28);glow(ctx,fx,dy-iw*.05,iw*.45,"#ffd98a",.2);}
    ctx.drawImage(img,0,topSrc,img.naturalWidth,srcH,dx,dy,iw,dh);
    if(progress>.004){
      ctx.strokeStyle="#241a10";ctx.lineWidth=Math.max(1.5,iw*.012);ctx.lineCap="round";
      ctx.beginPath();ctx.moveTo(fx,dy+1);ctx.lineTo(fx+iw*.006,dy-iw*.028);ctx.stroke();
      const fh=iw*.3,flick=state.running?Math.sin(Date.now()/90)*iw*.012+Math.sin(Date.now()/47)*iw*.006:0;
      ctx.save();ctx.translate(fx,dy-iw*.03);
      ctx.fillStyle="rgba(255,150,40,.9)";ctx.shadowColor="#ff9b30";ctx.shadowBlur=iw*.22;
      ctx.beginPath();ctx.moveTo(0,-fh-flick);
      ctx.quadraticCurveTo(iw*.075,-fh*.38,0,0);ctx.quadraticCurveTo(-iw*.075,-fh*.38,0,-fh-flick);ctx.fill();
      ctx.shadowBlur=0;ctx.fillStyle="#ffe9b0";
      ctx.beginPath();ctx.moveTo(0,-fh*.62-flick*.5);
      ctx.quadraticCurveTo(iw*.038,-fh*.24,0,-iw*.004);ctx.quadraticCurveTo(-iw*.038,-fh*.24,0,-fh*.62-flick*.5);ctx.fill();
      ctx.fillStyle="rgba(255,255,255,.95)";
      ctx.beginPath();ctx.ellipse(0,-fh*.16,iw*.014,fh*.1,0,0,Math.PI*2);ctx.fill();
      ctx.restore();
    }else{
      ctx.globalAlpha=.4;ctx.strokeStyle=text;ctx.lineWidth=Math.max(1.2,iw*.008);ctx.lineCap="round";
      ctx.beginPath();ctx.moveTo(fx,dy-2);
      ctx.quadraticCurveTo(fx+iw*.09,dy-iw*.2,fx-iw*.04,dy-iw*.38);ctx.stroke();ctx.globalAlpha=1;
    }
  }
  // Marée : une véritable étendue d'eau recule vers l'horizon. Aucun récipient :
  // le niveau, l'écume et l'estran portent directement l'écoulement du temps.
  function drawTide(progress){
    const {w,h}=resize(),{accent,text}=palette(),unit=Math.min(w,h),cx=w/2,horizon=h*.27,
      shoreline=h*(.43+.24*progress),bottom=h*.78,phase=state.running?Date.now()/760:0,
      shoreY=(x)=>shoreline+Math.sin(x/(unit*.075)+phase)*unit*.007+Math.sin(x/(unit*.031)-phase*.58)*unit*.0025;
    ctx.clearRect(0,0,w,h);glow(ctx,cx,horizon,unit*.72,accent,.12);
    const haze=ctx.createLinearGradient(0,horizon-unit*.1,0,horizon+unit*.16);haze.addColorStop(0,"rgba(189,235,244,0)");haze.addColorStop(.45,"rgba(177,228,239,.16)");haze.addColorStop(1,"rgba(31,81,91,0)");ctx.fillStyle=haze;ctx.fillRect(0,horizon-unit*.1,w,unit*.27);
    // L'estran apparaît sous le front de mer lorsque l'eau recule.
    const wetSand=ctx.createLinearGradient(0,shoreline,0,bottom);wetSand.addColorStop(0,"rgba(54,91,92,.5)");wetSand.addColorStop(.32,"rgba(89,77,61,.38)");wetSand.addColorStop(1,"rgba(23,26,28,.05)");ctx.fillStyle=wetSand;ctx.beginPath();ctx.moveTo(0,shoreY(0));for(let x=0;x<=w;x+=4)ctx.lineTo(x,shoreY(x));ctx.lineTo(w,bottom);ctx.lineTo(0,bottom);ctx.closePath();ctx.fill();
    // La mer est une nappe en perspective : étroite à l'horizon, large au rivage.
    const sea=ctx.createLinearGradient(0,horizon,0,shoreline);sea.addColorStop(0,"rgba(177,231,240,.72)");sea.addColorStop(.12,rgba(accent,.82));sea.addColorStop(.58,"rgba(17,105,126,.9)");sea.addColorStop(1,"rgba(8,61,78,.94)");ctx.fillStyle=sea;ctx.beginPath();ctx.moveTo(0,horizon);ctx.lineTo(w,horizon);ctx.lineTo(w,shoreY(w));for(let x=w;x>=0;x-=4)ctx.lineTo(x,shoreY(x));ctx.closePath();ctx.fill();
    // Rides de perspective : leur largeur et leur amplitude augmentent vers l'avant.
    for(let layer=1;layer<=8;layer++){
      const t=layer/9,yBase=horizon+(shoreline-horizon)*t,span=Math.min(w*.49,unit*(.25+t*.3)),amp=unit*(.0015+t*.0045),alpha=.16+t*.15;
      ctx.strokeStyle=layer%2?`rgba(207,245,248,${alpha})`:rgba(text,alpha*.58);ctx.lineWidth=Math.max(.8,unit*(.0015+t*.003));ctx.beginPath();
      for(let x=cx-span;x<=cx+span;x+=4){const y=yBase+Math.sin(x/(unit*(.035+t*.04))+phase*(.42+t*.35)+layer)*amp;x===cx-span?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();
    }
    // Front d'écume : c'est lui qui avance vers l'utilisateur à marée haute.
    ctx.strokeStyle="rgba(238,253,252,.94)";ctx.lineWidth=Math.max(2,unit*.007);ctx.shadowColor=rgba(accent,.65);ctx.shadowBlur=unit*.03;ctx.beginPath();for(let x=0;x<=w;x+=3){const y=shoreY(x);x===0?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();ctx.shadowBlur=0;
    ctx.strokeStyle="rgba(255,255,255,.55)";ctx.lineWidth=1;for(let i=0;i<22;i++){const x=w*(i/21),y=shoreY(x)+unit*(.011+.005*Math.sin(i*2.2));ctx.beginPath();ctx.arc(x,y,unit*(.005+(i%4)*.0014),Math.PI*.08,Math.PI*.92);ctx.stroke();}
    for(let i=0;i<32;i++){const t=.12+(i%7)/8,x=cx+Math.sin(i*15.73)*unit*(.22+t*.25),y=horizon+(shoreline-horizon)*t+Math.cos(i*8.4)*unit*.006;ctx.strokeStyle=i%4===0?"rgba(230,250,251,.5)":"rgba(118,207,220,.28)";ctx.lineWidth=i%5===0?2:1;ctx.beginPath();ctx.moveTo(x-unit*.016,y);ctx.lineTo(x+unit*(.018+(i%3)*.008),y);ctx.stroke();}
    ctx.strokeStyle=rgba(text,.16);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(cx-unit*.28,horizon);ctx.lineTo(cx+unit*.28,horizon);ctx.stroke();
    ctx.globalCompositeOperation="destination-in";const edgeFade=ctx.createLinearGradient(0,0,w,0);edgeFade.addColorStop(0,"rgba(0,0,0,0)");edgeFade.addColorStop(.055,"#000");edgeFade.addColorStop(.945,"#000");edgeFade.addColorStop(1,"rgba(0,0,0,0)");ctx.fillStyle=edgeFade;ctx.fillRect(0,0,w,h);ctx.globalCompositeOperation="source-over";
  }
  // Lune : la photo fournit les mers et cratères ; l'ombre qui la mange est un
  // disque sombre à bord doux qui glisse depuis la gauche, comme la nuit.
  function drawMoonPhoto(progress){
    if(!ready("moon")){drawMoon(progress);return;}
    const img=assets.moon,{w,h}=resize(),{accent}=palette();
    ctx.clearRect(0,0,w,h);
    const d=Math.min(w,h)*.74,cx=w/2,cy=h*.44,r=d/2;
    glow(ctx,cx,cy,r*1.8,accent,.2);
    ctx.drawImage(img,cx-r,cy-r,d,d);
    ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();
    ctx.fillStyle="rgba(3,6,12,.97)";ctx.shadowColor="rgba(3,6,12,1)";ctx.shadowBlur=r*.14;
    ctx.beginPath();ctx.arc(cx-2.2*r*progress,cy,r,0,Math.PI*2);ctx.fill();
    ctx.restore();
  }
  // Soleil : le disque photographique traverse une atmosphère et éclaire un horizon,
  // au lieu de flotter comme une petite icône isolée.
  function drawSunPhoto(progress){
    if(!ready("sun")){drawSun(progress);return;}
    const img=assets.sun,{w,h}=resize(),{accent,border,text}=palette(),unit=Math.min(w,h);
    ctx.clearRect(0,0,w,h);
    const cx=w/2,horizon=h*.62,arc=unit*.34,d=unit*.31,r=d/2,
      angle=Math.PI*(.08+.64*progress),x=cx+Math.cos(angle)*arc,y=horizon-Math.sin(angle)*arc;
    const sky=ctx.createRadialGradient(x,y,r*.18,x,y,unit*.72);sky.addColorStop(0,"rgba(255,218,125,.38)");sky.addColorStop(.28,"rgba(255,143,57,.16)");sky.addColorStop(1,"rgba(255,104,32,0)");ctx.fillStyle=sky;ctx.beginPath();ctx.ellipse(cx,h*.38,unit*.54,unit*.39,0,0,Math.PI*2);ctx.fill();
    const horizonGlow=ctx.createRadialGradient(cx,horizon,unit*.02,cx,horizon,unit*.5);horizonGlow.addColorStop(0,"rgba(255,190,96,.22)");horizonGlow.addColorStop(.56,"rgba(255,153,63,.09)");horizonGlow.addColorStop(1,"rgba(91,46,25,0)");ctx.fillStyle=horizonGlow;ctx.beginPath();ctx.ellipse(cx,horizon,unit*.5,unit*.16,0,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle=rgba(text,.1);ctx.lineWidth=1.2;ctx.setLineDash([5,9]);ctx.beginPath();ctx.arc(cx,horizon,arc,Math.PI*.08,Math.PI*.72,true);ctx.stroke();ctx.setLineDash([]);
    ctx.strokeStyle=rgba(border,.55);ctx.lineWidth=1.4;ctx.beginPath();ctx.moveTo(cx-unit*.46,horizon);ctx.quadraticCurveTo(cx,horizon-unit*.018,cx+unit*.46,horizon);ctx.stroke();
    // Reflet solaire sur l'horizon, resserré à mesure que le soleil descend.
    const reflection=ctx.createLinearGradient(0,horizon,0,h*.77);reflection.addColorStop(0,"rgba(255,226,155,.48)");reflection.addColorStop(1,"rgba(255,139,48,0)");ctx.fillStyle=reflection;ctx.beginPath();ctx.moveTo(x-r*.2,horizon);ctx.lineTo(x+r*.2,horizon);ctx.lineTo(x+r*.62,h*.77);ctx.lineTo(x-r*.62,h*.77);ctx.closePath();ctx.fill();
    glow(ctx,x,y,d*1.45,"#ff9d32",.34);ctx.shadowColor="#ff9d32";ctx.shadowBlur=d*.55;ctx.drawImage(img,x-r,y-r,d,d);ctx.shadowBlur=0;
    ctx.strokeStyle="rgba(255,234,183,.3)";ctx.lineWidth=1;for(let i=0;i<18;i++){const a=i*Math.PI/9,inner=r*1.03,outer=r*(1.2+(i%3)*.05);ctx.beginPath();ctx.moveTo(x+Math.cos(a)*inner,y+Math.sin(a)*inner);ctx.lineTo(x+Math.cos(a)*outer,y+Math.sin(a)*outer);ctx.stroke();}
    // L'atmosphère se dissout dans le décor au lieu de révéler le rectangle du canvas.
    ctx.globalCompositeOperation="destination-in";const atmosphereMask=ctx.createRadialGradient(cx,h*.39,unit*.2,cx,h*.39,unit*.63);atmosphereMask.addColorStop(0,"#000");atmosphereMask.addColorStop(.68,"#000");atmosphereMask.addColorStop(1,"rgba(0,0,0,0)");ctx.fillStyle=atmosphereMask;ctx.fillRect(0,0,w,h);
    const horizontalFade=ctx.createLinearGradient(0,0,w,0);horizontalFade.addColorStop(0,"rgba(0,0,0,0)");horizontalFade.addColorStop(.07,"#000");horizontalFade.addColorStop(.93,"#000");horizontalFade.addColorStop(1,"rgba(0,0,0,0)");ctx.fillStyle=horizontalFade;ctx.fillRect(0,0,w,h);
    const verticalFade=ctx.createLinearGradient(0,0,0,h);verticalFade.addColorStop(0,"rgba(0,0,0,0)");verticalFade.addColorStop(.08,"#000");verticalFade.addColorStop(.84,"#000");verticalFade.addColorStop(1,"rgba(0,0,0,0)");ctx.fillStyle=verticalFade;ctx.fillRect(0,0,w,h);ctx.globalCompositeOperation="source-over";
  }
  // Anneau : une vraie jauge d'horlogerie porte les graduations ; le temps
  // restant est un arc lumineux posé dans sa gorge.
  function drawRingPhoto(progress){
    if(!ready("ring")){drawRing(progress);return;}
    const img=assets.ring,{w,h}=resize(),{accent,text}=palette();
    ctx.clearRect(0,0,w,h);
    const d=Math.min(w,h)*.72,cx=w/2,cy=h*.42,r=d*.395;
    glow(ctx,cx,cy,d*.62,accent,.09);
    ctx.drawImage(img,cx-d/2,cy-d/2,d,d);
    if(progress>.001){
      const end=-Math.PI/2+Math.PI*2*progress;
      const active=ctx.createLinearGradient(cx-r,cy-r,cx+r,cy+r);
      active.addColorStop(0,rgba(accent,.75));active.addColorStop(.55,accent);active.addColorStop(1,rgba(text,.98));
      ctx.strokeStyle=active;ctx.lineWidth=d*.035;ctx.lineCap="round";
      ctx.shadowColor=accent;ctx.shadowBlur=d*.06;
      ctx.beginPath();ctx.arc(cx,cy,r,-Math.PI/2,end);ctx.stroke();
      ctx.shadowBlur=0;
      ctx.fillStyle=text;ctx.beginPath();ctx.arc(cx+Math.cos(end)*r,cy+Math.sin(end)*r,d*.012,0,Math.PI*2);ctx.fill();
    }
  }
  function flash(){const layer=$("#flash-layer");layer.classList.remove("flash");void layer.offsetWidth;layer.classList.add("flash");}
  function finish(){state.running=false;state.finished=true;state.remaining=0;save();flash();if(app.dataset.endSound==="true")finishAudio.play().catch(()=>{});logSession();}
  // Une session achevée est envoyée au serveur : c'est ce qui alimente le temps réel de
  // la grille de suivi. Un échec réseau ne doit rien casser — la session est perdue,
  // le minuteur continue de fonctionner.
  function logSession(){
    const seconds=Math.round(state.total);
    if(!(seconds>=1&&seconds<=86400))return;
    const select=$("#session-competency");
    fetch(app.dataset.logUrl,{
      method:"POST",
      headers:{"Content-Type":"application/json","X-CSRFToken":app.dataset.csrf},
      body:JSON.stringify({seconds,intention:state.intention||"",competency:select?.value||null}),
    }).then(response=>response.ok?response.json():null).then(data=>{
      if(data?.competency){$("#stage-message").textContent=`${data.hours} h REPORTÉES SUR ${data.competency.toUpperCase()}`;const back=$("#return-after-session");if(back&&app.dataset.returnUrl)back.hidden=false;}
    }).catch(()=>{});
  }
  function ambienceLabel(){const select=$("#ambience-select"),option=[...select.options].find(item=>item.value===state.ambience);return option?.textContent||state.ambience;}
  function render(force=false){
    if(state.running){state.remaining=Math.max(0,(state.endsAt-Date.now())/1000);if(state.remaining<=0&&!state.finished)finish();}
    const second=Math.ceil(state.remaining),progress=clamp(state.remaining/Math.max(1,state.total),0,1),warning=!state.finished&&state.remaining<=state.warning;
    if(force||second!==lastSecond){lastSecond=second;const text=format(state.remaining);$("#canvas-time").textContent=text;$("#digital-time").textContent=text;$("#zen-time").textContent=text;$("#duration-input").value=format(state.total);$("#digital-progress").style.setProperty("--progress",progress);$("#zen-progress").style.setProperty("--progress",progress);app.dataset.warning=String(warning);app.dataset.finished=String(state.finished);app.dataset.ambience=state.ambience;app.dataset.focusLevel=String(state.focusLevel);app.classList.toggle("hushed",state.focusLevel===2);app.classList.toggle("bare",state.focusLevel===3);$("#live-chip").textContent=state.running?"● EN DIRECT":state.finished?"● TERMINÉ":"● PRÊT";$("#session-status").textContent=state.running?"● SESSION EN COURS":state.finished?"● SESSION TERMINÉE":"● PRÊT";$("#stage-message").textContent=state.finished?"TEMPS ÉCOULÉ":state.running?"RESTEZ DANS VOTRE RYTHME":"ESPACE POUR DÉMARRER";$("#main-control").textContent=state.finished?"↻ RECOMMENCER":state.running?"Ⅱ PAUSE":"▶ DÉMARRER";$("#stage-intention").textContent=(state.intention||"SESSION DE CONCENTRATION").toUpperCase();$("#ambience-status").textContent=`${ambienceLabel().toUpperCase()} · FOCUS ${state.focusLevel}`;if(warning&&!warningCue){warningCue=true;flash();}save();}
    const mode=state.mode;$("#visual-wrap").dataset.mode=mode;
    const painters={ring:drawRingPhoto,hourglass:drawHourglassPhoto,wave:drawTide,candle:drawCandlePhoto,beads:drawBeads,moon:drawMoonPhoto,bars:drawBars,spiral:drawSpiral,sun:drawSunPhoto};
    if(painters[mode])painters[mode](progress);
    $("#canvas-label").textContent={ring:"TEMPS RESTANT",hourglass:"ÉCOULEMENT RÉEL",wave:"MARÉE DESCENDANTE",candle:"IL RESTE À BRÛLER",beads:"PERLES RESTANTES",moon:"DÉCROISSANCE",bars:"NIVEAU RESTANT",spiral:"FIL À DÉROULER",sun:"AVANT LE COUCHER"}[mode]||"TEMPS RESTANT";
    app.dataset.decorDensity=String(state.decorDensity);
    decor.use(decorNames[state.ambience]||"motes",state.decorDensity);
    app.querySelectorAll(".decor-levels [data-decor]").forEach(button=>{
      const active=Number(button.dataset.decor)===state.decorDensity;
      button.classList.toggle("active",active);
      button.setAttribute("aria-pressed",String(active));
    });
    decor.frame(performance.now(),getComputedStyle(app).getPropertyValue("--focus-accent").trim());app.querySelectorAll(".mode-grid [data-mode]").forEach(button=>button.classList.toggle("active",button.dataset.mode===mode));app.querySelectorAll(".focus-levels [data-level]").forEach(button=>button.classList.toggle("active",Number(button.dataset.level)===state.focusLevel));
  }
  function loop(){render();frame=requestAnimationFrame(loop)}
  $("#apply-duration").addEventListener("click",()=>{const input=$("#duration-input"),seconds=parseDuration(input.value);input.setCustomValidity("");if(seconds)setDuration(seconds);else {input.setCustomValidity("Durée invalide (maximum 24 h).");input.reportValidity();}});
  app.querySelectorAll("[data-preset]").forEach(b=>b.addEventListener("click",()=>setDuration(Number(b.dataset.preset)*60)));
  app.querySelectorAll(".mode-grid [data-mode]").forEach(b=>b.addEventListener("click",()=>{state.mode=b.dataset.mode;save();render(true)}));
  app.querySelectorAll(".focus-levels [data-level]").forEach(b=>b.addEventListener("click",()=>{state.focusLevel=Number(b.dataset.level);save();render(true)}));
  app.querySelectorAll(".decor-levels [data-decor]").forEach(b=>b.addEventListener("click",()=>{state.decorDensity=Number(b.dataset.decor);save();render(true)}));
  $("#session-intention").addEventListener("input",e=>{state.intention=e.target.value;save();render(true)});
  $("#ambience-select").addEventListener("change",e=>{state.ambience=e.target.value;save();render(true)});
  $("#warning-slider").addEventListener("input",e=>{state.warning=Number(e.target.value);$("#warning-output").textContent=`${state.warning} s`;warningCue=false;save()});
  $("#main-control").addEventListener("click",startPause);$("#reset-control").addEventListener("click",reset);$("#minus-minute").addEventListener("click",()=>adjust(-60));$("#plus-minute").addEventListener("click",()=>adjust(60));
  $("#scene-button").addEventListener("click",async()=>{app.classList.add("stage-mode");try{await app.requestFullscreen()}catch(_){}});document.addEventListener("fullscreenchange",()=>{if(!document.fullscreenElement)app.classList.remove("stage-mode")});
  document.addEventListener("keydown",e=>{if(["INPUT","TEXTAREA","SELECT"].includes(document.activeElement?.tagName))return;if(e.code==="Space"){e.preventDefault();startPause()}else if(e.key.toLowerCase()==="r")reset();else if(e.key==="F11"){e.preventDefault();$("#scene-button").click()}else if(e.key==="Escape"&&app.classList.contains("stage-mode")){document.exitFullscreen?.();app.classList.remove("stage-mode")}});
  const prefForm=$("#focus-preferences"),durationHidden=prefForm.querySelector("#id_default_duration_seconds");prefForm.addEventListener("submit",()=>{durationHidden.value=Math.round(state.total);prefForm.querySelector("#id_session_intention").value=state.intention;prefForm.querySelector("#id_mode").value=state.mode;prefForm.querySelector("#id_ambience").value=state.ambience;prefForm.querySelector("#id_focus_level").value=state.focusLevel;prefForm.querySelector("#id_warning_seconds").value=state.warning;prefForm.querySelector("#id_decor_density").value=state.decorDensity;});

  const playlists=JSON.parse(document.querySelector("#playlist-data").textContent),player=$("#playlist-audio");let currentPlaylist=null,index=0,shuffle=false,repeat=false;
  function loadTrack(autoplay=false){const track=currentPlaylist?.tracks[index];if(!track){player.removeAttribute("src");$("#player-title").textContent="Playlist vide";$("#player-artist").textContent="";return;}player.src=track.url;$("#player-title").textContent=track.title;$("#player-artist").textContent=track.artist||"";if(autoplay)player.play().catch(error=>{if(error?.name!=="NotAllowedError")$("#player-artist").textContent="Lecture impossible — fichier introuvable ou illisible.";});}
  function move(direction){if(!currentPlaylist?.tracks.length)return;index=shuffle?Math.floor(Math.random()*currentPlaylist.tracks.length):(index+direction+currentPlaylist.tracks.length)%currentPlaylist.tracks.length;loadTrack(true)}
  // Sans playlist, le lecteur n'est pas rendu : le minuteur doit continuer de
  // fonctionner sans lui, d'où la sortie anticipée plutôt qu'une erreur en cascade.
  if($("#playlist-select")){
    $("#playlist-select").addEventListener("change",e=>{currentPlaylist=playlists.find(p=>String(p.id)===e.target.value);index=0;loadTrack(false)});$("#player-toggle").addEventListener("click",()=>player.paused?player.play():player.pause());$("#player-prev").addEventListener("click",()=>move(-1));$("#player-next").addEventListener("click",()=>move(1));$("#player-shuffle").addEventListener("click",e=>{shuffle=!shuffle;e.currentTarget.classList.toggle("active",shuffle)});$("#player-repeat").addEventListener("click",e=>{repeat=!repeat;e.currentTarget.classList.toggle("active",repeat)});$("#player-volume").addEventListener("input",e=>player.volume=Number(e.target.value));player.addEventListener("play",()=>$("#player-toggle").textContent="Ⅱ");player.addEventListener("pause",()=>$("#player-toggle").textContent="▶");player.addEventListener("ended",()=>repeat?player.play():move(1));player.addEventListener("error",()=>{const causes={1:"lecture interrompue",2:"erreur réseau",3:"décodage impossible — fichier corrompu ou format non pris en charge",4:"source refusée — bloquée par la politique de sécurité, ou introuvable"};const code=player.error?.code;$("#player-artist").textContent=`Lecture impossible — ${causes[code]||"cause inconnue"} (code ${code??"?"}).`;});player.volume=.65;
  }
  render(true);cancelAnimationFrame(frame);loop();
});
