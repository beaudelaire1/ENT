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
  // Bougie : la silhouette d'origine reste tracée, seule la cire se consume à
  // l'intérieur. Faire rétrécir la bougie elle-même effaçait la mesure : on ne voyait
  // plus quelle part du temps avait été brûlée, comme un sablier dont le verre
  // rapetisserait avec le sable.
  function drawCandle(progress){
    const {w,h}=resize(),{accent,border,text,surface}=palette(),cx=w/2,
      bodyW=Math.min(w,h)*.27,full=h*.6,base=h*.83,ceiling=base-full,
      top=base-full*progress,radius=bodyW*.16;
    ctx.clearRect(0,0,w,h);
    // Le halo de la flamme est peint d'abord : il baigne la scène, la cire s'y détache.
    if(progress>.004){
      glow(ctx,cx,top-bodyW*.8,bodyW*3.6,accent,.3);
      glow(ctx,cx,top-bodyW*.42,bodyW*1.4,text,.13);
    }
    // Bougeoir : assise, fût, et le reflet chaud que la flamme y dépose.
    const holder=ctx.createLinearGradient(cx-bodyW*1.6,0,cx+bodyW*1.6,0);
    holder.addColorStop(0,rgba(border,.98));holder.addColorStop(.3,rgba(text,.5));
    holder.addColorStop(.5,surface);holder.addColorStop(.72,rgba(text,.4));holder.addColorStop(1,rgba(border,.98));
    ctx.fillStyle=holder;
    ctx.beginPath();ctx.ellipse(cx,base+9,bodyW*1.58,14,0,0,Math.PI*2);ctx.fill();
    limb(text,1.2,.3);
    ctx.beginPath();ctx.roundRect(cx-bodyW*1.6,base-3,bodyW*3.2,15,8);ctx.fill();limb(text,1.2,.34);
    if(progress>.004){ctx.globalAlpha=.5;glow(ctx,cx,base,bodyW*1.7,accent,.3);ctx.globalAlpha=1;}
    // Hauteur d'origine : ce qui a déjà fondu reste mesurable, en pointillé plutôt qu'en
    // aplat fantôme — un bloc translucide se lisait comme une deuxième bougie.
    ctx.setLineDash([7,7]);ctx.globalAlpha=.55;
    ctx.beginPath();ctx.roundRect(cx-bodyW/2,ceiling,bodyW,full,radius);limb(text,1.4,.5);
    ctx.setLineDash([]);ctx.globalAlpha=1;
    if(progress>.004){
      ctx.fillStyle=litColumn(cx-bodyW/2,cx+bodyW/2,{accent,text,border});
      ctx.beginPath();ctx.roundRect(cx-bodyW/2,top,bodyW,base-top,radius);ctx.fill();
      // Liseré : c'est lui qui donne sa taille apparente à la bougie.
      limb(text,2,.62);
      // Cuvette de cire autour de la mèche, creusée par la flamme.
      ctx.fillStyle=rgba(border,.85);ctx.beginPath();ctx.ellipse(cx,top+bodyW*.06,bodyW*.5,bodyW*.14,0,0,Math.PI*2);ctx.fill();
      ctx.fillStyle=rgba(text,.9);ctx.globalAlpha=.5;ctx.beginPath();ctx.ellipse(cx,top+bodyW*.04,bodyW*.34,bodyW*.08,0,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;
      ctx.fillStyle=rgba(accent,.9);ctx.beginPath();ctx.ellipse(cx,top+bodyW*.09,bodyW*.2,bodyW*.05,0,0,Math.PI*2);ctx.fill();
      // Coulures : la cire fondue déborde à mesure qu'elle descend.
      const spill=(1-progress)*bodyW*.3;
      if(spill>1){
        ctx.beginPath();
        ctx.moveTo(cx-bodyW/2,top+bodyW*.14);
        ctx.quadraticCurveTo(cx-bodyW/2-spill,top+bodyW*.5,cx-bodyW/2,top+bodyW*.92);
        ctx.moveTo(cx+bodyW/2,top+bodyW*.22);
        ctx.quadraticCurveTo(cx+bodyW/2+spill,top+bodyW*.7,cx+bodyW/2,top+bodyW*1.15);
        ctx.lineWidth=spill;ctx.strokeStyle=rgba(accent,.92);ctx.lineCap="round";ctx.stroke();
      }
      // Mèche puis flamme : cœur blanc, manteau coloré, halo. Trois valeurs, sinon la
      // flamme n'est qu'une tache de la couleur d'ambiance.
      const flicker=state.running?Math.sin(Date.now()/90)*bodyW*.035:0,flameH=bodyW*1.15;
      ctx.strokeStyle=rgba(border,.95);ctx.lineWidth=Math.max(2,bodyW*.035);
      ctx.beginPath();ctx.moveTo(cx,top+2);ctx.quadraticCurveTo(cx+bodyW*.04,top-bodyW*.16,cx-bodyW*.03,top-bodyW*.3);ctx.stroke();
      ctx.beginPath();ctx.moveTo(cx,top-flameH-flicker);
      ctx.quadraticCurveTo(cx+bodyW*.44,top-flameH*.33,cx,top-2);
      ctx.quadraticCurveTo(cx-bodyW*.44,top-flameH*.33,cx,top-flameH-flicker);
      ctx.fillStyle=accent;ctx.shadowColor=accent;ctx.shadowBlur=bodyW*.55;ctx.fill();ctx.shadowBlur=0;
      ctx.fillStyle=rgba(text,.97);
      ctx.beginPath();ctx.moveTo(cx,top-flameH*.66-flicker*.5);
      ctx.quadraticCurveTo(cx+bodyW*.17,top-flameH*.26,cx,top-bodyW*.06);
      ctx.quadraticCurveTo(cx-bodyW*.17,top-flameH*.26,cx,top-flameH*.66-flicker*.5);ctx.fill();
      ctx.fillStyle=rgba(border,.55);
      ctx.beginPath();ctx.ellipse(cx,top-bodyW*.1,bodyW*.06,bodyW*.13,0,0,Math.PI*2);ctx.fill();
    }else{
      // Mèche éteinte : un filet de fumée plutôt qu'une bougie disparue.
      ctx.globalAlpha=.45;ctx.strokeStyle=text;ctx.lineWidth=Math.max(2,bodyW*.03);ctx.lineCap="round";
      ctx.beginPath();ctx.moveTo(cx,base-6);
      ctx.quadraticCurveTo(cx+bodyW*.28,base-bodyW*.7,cx-bodyW*.12,base-bodyW*1.3);
      ctx.stroke();ctx.globalAlpha=1;
    }
  }
  // Perles : chaque perle est une part du temps ; elles s'éteignent une à une.
  function drawBeads(progress){
    const {w,h}=resize(),{accent,border,text}=palette(),cols=6,rows=6,total=cols*rows,
      span=Math.min(w,h)*.68,step=span/(cols-1),ox=w/2-span/2,oy=h*.42-span/2,r=Math.max(5,step*.19),
      alive=progress*total;
    ctx.clearRect(0,0,w,h);glow(ctx,w/2,h*.42,span*.64,accent,.07);ctx.strokeStyle=rgba(text,.18);ctx.lineWidth=Math.max(1,r*.16);
    // Le fil suit le même trajet en serpentin que la lecture des perles.
    ctx.beginPath();for(let row=0;row<rows;row++){const y=oy+row*step;if(row===0)ctx.moveTo(ox,y);if(row%2===0){ctx.lineTo(ox+span,y);if(row<rows-1)ctx.quadraticCurveTo(ox+span+step*.25,y+step*.5,ox+span,y+step);}else{ctx.lineTo(ox,y);if(row<rows-1)ctx.quadraticCurveTo(ox-step*.25,y+step*.5,ox,y+step);}}ctx.stroke();
    for(let i=0;i<total;i++){
      const row=Math.floor(i/cols),column=row%2===0?i%cols:cols-1-i%cols,x=ox+column*step,y=oy+row*step,fill=Math.max(0,Math.min(1,alive-i));
      let bead=ctx.createRadialGradient(x-r*.35,y-r*.4,r*.08,x,y,r);bead.addColorStop(0,rgba(text,.4));bead.addColorStop(.3,rgba(border,.98));bead.addColorStop(1,rgba(border,.92));ctx.fillStyle=bead;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();limb(text,1.2,.3);
      if(fill>0){
        bead=ctx.createRadialGradient(x-r*.36,y-r*.42,r*.04,x,y,r);bead.addColorStop(0,rgba(text,.92));bead.addColorStop(.22,accent);bead.addColorStop(1,rgba(accent,.34));ctx.fillStyle=bead;ctx.globalAlpha=fill;ctx.beginPath();ctx.arc(x,y,r*(.45+.55*fill),0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;
      }
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
  // Colonnes : le temps se lit comme un niveau qui retombe, colonne après colonne.
  function drawBars(progress){
    const {w,h}=resize(),{accent,border,text}=palette(),count=14,
      span=Math.min(w,h)*.78,gap=span/count,barW=gap*.58,base=h*.72,maxH=h*.48,
      alive=progress*count,ox=w/2-span/2;
    ctx.clearRect(0,0,w,h);glow(ctx,w/2,base,span*.65,accent,.07);ctx.strokeStyle=rgba(text,.2);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(ox-gap*.2,base+1);ctx.lineTo(ox+span,base+1);ctx.stroke();
    for(let i=0;i<count;i++){
      // Une hauteur propre à chaque colonne, stable d'une image à l'autre.
      const shape=.45+.55*Math.abs(Math.sin(i*1.7)),full=maxH*shape,x=ox+i*gap+(gap-barW)/2,
        fill=Math.max(0,Math.min(1,alive-i));
      ctx.fillStyle=border;ctx.globalAlpha=.6;
      ctx.beginPath();ctx.roundRect(x,base-full,barW,full,barW*.3);ctx.fill();
      ctx.globalAlpha=1;limb(text,1.2,.26);ctx.globalAlpha=.6;
      if(fill>0){
        ctx.globalAlpha=1;ctx.fillStyle=litColumn(x,x+barW,{accent,text,border});
        const height=full*fill;
        ctx.beginPath();ctx.roundRect(x,base-height,barW,height,barW*.3);ctx.fill();limb(text,1.4,.45);
      }
    }
    ctx.globalAlpha=1;
  }
  // Spirale : le fil se déroule du centre vers l'extérieur, et se rétracte avec le temps.
  function drawSpiral(progress){
    const {w,h}=resize(),{accent,border,text}=palette(),cx=w/2,cy=h*.41,
      turns=4,maxR=Math.min(w,h)*.35,steps=460;
    ctx.clearRect(0,0,w,h);glow(ctx,cx,cy,maxR*1.1,accent,.07);
    const trace=(fraction,color,width,alpha)=>{
      if(fraction<=.0005)return;
      ctx.strokeStyle=color;ctx.lineWidth=width;ctx.globalAlpha=alpha;ctx.lineCap="round";
      ctx.beginPath();
      for(let i=0;i<=steps*fraction;i++){
        const t=i/steps,angle=t*turns*Math.PI*2-Math.PI/2,r=maxR*t;
        const x=cx+Math.cos(angle)*r,y=cy+Math.sin(angle)*r;
        i?ctx.lineTo(x,y):ctx.moveTo(x,y);
      }
      ctx.stroke();ctx.globalAlpha=1;
    };
    trace(1,border,3.4,.5);trace(progress,accent,5.4,1);
    if(progress>.001){const angle=progress*turns*Math.PI*2-Math.PI/2,r=maxR*progress,x=cx+Math.cos(angle)*r,y=cy+Math.sin(angle)*r;ctx.fillStyle=text;ctx.shadowColor=accent;ctx.shadowBlur=18;ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;}
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
    const painters={ring:drawRing,hourglass:drawHourglass,wave:drawWave,candle:drawCandle,beads:drawBeads,moon:drawMoon,bars:drawBars,spiral:drawSpiral,sun:drawSun};
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
    $("#playlist-select").addEventListener("change",e=>{currentPlaylist=playlists.find(p=>String(p.id)===e.target.value);index=0;loadTrack(false)});$("#player-toggle").addEventListener("click",()=>player.paused?player.play():player.pause());$("#player-prev").addEventListener("click",()=>move(-1));$("#player-next").addEventListener("click",()=>move(1));$("#player-shuffle").addEventListener("click",e=>{shuffle=!shuffle;e.currentTarget.classList.toggle("active",shuffle)});$("#player-repeat").addEventListener("click",e=>{repeat=!repeat;e.currentTarget.classList.toggle("active",repeat)});$("#player-volume").addEventListener("input",e=>player.volume=Number(e.target.value));player.addEventListener("play",()=>$("#player-toggle").textContent="Ⅱ");player.addEventListener("pause",()=>$("#player-toggle").textContent="▶");player.addEventListener("ended",()=>repeat?player.play():move(1));player.addEventListener("error",()=>{$("#player-artist").textContent="Lecture impossible — le fichier n'a pas pu être chargé.";});player.volume=.65;
  }
  render(true);cancelAnimationFrame(frame);loop();
});
