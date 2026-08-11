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
  function resize(){const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.max(1,rect.width*dpr);canvas.height=Math.max(1,rect.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);}
  function drawRing(progress){resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,cy=h/2,r=Math.min(w,h)*.42,line=Math.max(16,r*.085),accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),border=getComputedStyle(app).getPropertyValue("--focus-border").trim();ctx.clearRect(0,0,w,h);ctx.lineCap="round";ctx.lineWidth=line;ctx.strokeStyle=border;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();if(progress>.001){ctx.strokeStyle=accent;ctx.shadowColor=accent;ctx.shadowBlur=20;ctx.beginPath();ctx.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+Math.PI*2*progress);ctx.stroke();ctx.shadowBlur=0;}}
  function bottlePath(cx,cy,hw,hh){const neck=hw*.1;ctx.beginPath();ctx.moveTo(cx-hw,cy-hh);ctx.bezierCurveTo(cx-hw*.94,cy-hh*.46,cx-hw*.23,cy-hh*.19,cx-neck,cy);ctx.bezierCurveTo(cx-hw*.23,cy+hh*.19,cx-hw*.94,cy+hh*.46,cx-hw,cy+hh);ctx.lineTo(cx+hw,cy+hh);ctx.bezierCurveTo(cx+hw*.94,cy+hh*.46,cx+hw*.23,cy+hh*.19,cx+neck,cy);ctx.bezierCurveTo(cx+hw*.23,cy-hh*.19,cx+hw*.94,cy-hh*.46,cx+hw,cy-hh);ctx.closePath();}
  function drawHourglass(progress){resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,cy=h*.46,hh=h*.40,hw=w*.27,accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),border=getComputedStyle(app).getPropertyValue("--focus-border").trim();ctx.clearRect(0,0,w,h);bottlePath(cx,cy,hw,hh);ctx.fillStyle="rgba(170,180,220,.08)";ctx.fill();ctx.strokeStyle="rgba(220,230,250,.6)";ctx.lineWidth=2;ctx.stroke();ctx.save();bottlePath(cx,cy,hw-4,hh-5);ctx.clip();ctx.fillStyle=accent;
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
    if(state.running&&progress>.001){ctx.strokeStyle=accent;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx,peak);ctx.stroke();}
    ctx.restore();ctx.fillStyle=border;for(const y of [cy-hh-7,cy+hh-7]){ctx.beginPath();ctx.roundRect(cx-hw*1.2,y,hw*2.4,15,7);ctx.fill();}}
  // Marée : le niveau descend, la surface ondule. La houle n'avance que si le compte
  // à rebours tourne, sinon l'écran bougerait sans que rien ne se passe.
  function drawWave(progress){
    resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,cy=h*.48,r=Math.min(w,h)*.41,
      accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),
      border=getComputedStyle(app).getPropertyValue("--focus-border").trim();
    ctx.clearRect(0,0,w,h);
    ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.strokeStyle=border;ctx.lineWidth=2;ctx.stroke();ctx.clip();
    const level=cy+r-2*r*progress,phase=state.running?Date.now()/700:0;
    ctx.fillStyle=accent;
    for(let layer=0;layer<2;layer++){
      ctx.globalAlpha=layer?.45:1;
      ctx.beginPath();ctx.moveTo(cx-r,h);
      for(let x=cx-r;x<=cx+r;x+=6){ctx.lineTo(x,level+Math.sin((x/(38+layer*22))+phase+layer)*(7-layer*3));}
      ctx.lineTo(cx+r,h);ctx.closePath();ctx.fill();
    }
    ctx.globalAlpha=1;ctx.restore();
  }
  // Bougie : la silhouette d'origine reste tracée, seule la cire se consume à
  // l'intérieur. Faire rétrécir la bougie elle-même effaçait la mesure : on ne voyait
  // plus quelle part du temps avait été brûlée, comme un sablier dont le verre
  // rapetisserait avec le sable.
  function drawCandle(progress){
    resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,
      accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),
      border=getComputedStyle(app).getPropertyValue("--focus-border").trim(),
      bodyW=Math.min(w,h)*.21,full=h*.62,base=h*.85,ceiling=base-full,
      top=base-full*progress,radius=bodyW*.18;
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle=border;ctx.beginPath();ctx.roundRect(cx-bodyW*1.5,base,bodyW*3,14,7);ctx.fill();
    // Hauteur d'origine : ce qui a déjà fondu reste visible, en creux.
    ctx.globalAlpha=.2;ctx.fillStyle=border;
    ctx.beginPath();ctx.roundRect(cx-bodyW/2,ceiling,bodyW,full,radius);ctx.fill();
    ctx.globalAlpha=.5;ctx.strokeStyle=border;ctx.lineWidth=1.5;
    ctx.beginPath();ctx.roundRect(cx-bodyW/2,ceiling,bodyW,full,radius);ctx.stroke();
    ctx.globalAlpha=1;
    if(progress>.004){
      ctx.fillStyle=accent;ctx.globalAlpha=.9;
      ctx.beginPath();ctx.roundRect(cx-bodyW/2,top,bodyW,base-top,radius);ctx.fill();
      // Coulures : la cire fondue déborde sur les côtés à mesure qu'elle descend.
      const spill=(1-progress)*bodyW*.22;
      if(spill>1){
        ctx.beginPath();
        ctx.moveTo(cx-bodyW/2,top+6);
        ctx.quadraticCurveTo(cx-bodyW/2-spill,top+18,cx-bodyW/2,top+34);
        ctx.moveTo(cx+bodyW/2,top+10);
        ctx.quadraticCurveTo(cx+bodyW/2+spill,top+26,cx+bodyW/2,top+44);
        ctx.lineWidth=spill;ctx.strokeStyle=accent;ctx.lineCap="round";ctx.stroke();
      }
      ctx.globalAlpha=1;
      const flicker=state.running?Math.sin(Date.now()/90)*2:0,flameH=Math.min(34,bodyW*.9);
      ctx.beginPath();ctx.moveTo(cx,top-flameH-flicker);
      ctx.quadraticCurveTo(cx+bodyW*.42,top-flameH*.35,cx,top-2);
      ctx.quadraticCurveTo(cx-bodyW*.42,top-flameH*.35,cx,top-flameH-flicker);
      ctx.fillStyle=accent;ctx.shadowColor=accent;ctx.shadowBlur=26;ctx.fill();ctx.shadowBlur=0;
    }else{
      // Mèche éteinte : un filet de fumée plutôt qu'une bougie disparue.
      ctx.globalAlpha=.35;ctx.strokeStyle=border;ctx.lineWidth=2;
      ctx.beginPath();ctx.moveTo(cx,base-4);
      ctx.quadraticCurveTo(cx+10,base-26,cx-4,base-48);
      ctx.stroke();ctx.globalAlpha=1;
    }
  }
  // Perles : chaque perle est une part du temps ; elles s'éteignent une à une.
  function drawBeads(progress){
    resize();const w=canvas.clientWidth,h=canvas.clientHeight,cols=6,rows=6,total=cols*rows,
      accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),
      border=getComputedStyle(app).getPropertyValue("--focus-border").trim(),
      span=Math.min(w,h)*.80,step=span/(cols-1),ox=w/2-span/2,oy=h*.46-span/2,r=Math.max(5,step*.19),
      alive=progress*total;
    ctx.clearRect(0,0,w,h);
    for(let i=0;i<total;i++){
      const x=ox+(i%cols)*step,y=oy+Math.floor(i/cols)*step,fill=Math.max(0,Math.min(1,alive-i));
      ctx.fillStyle=border;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
      if(fill>0){
        ctx.fillStyle=accent;ctx.globalAlpha=fill;   // la perle en cours s'estompe
        ctx.beginPath();ctx.arc(x,y,r*(.35+.65*fill),0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;
      }
    }
  }
  // Lune : elle décroît comme le temps restant, de la pleine lune au croissant.
  function drawMoon(progress){
    resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,cy=h*.47,r=Math.min(w,h)*.38,
      accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),
      border=getComputedStyle(app).getPropertyValue("--focus-border").trim();
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle=border;ctx.lineWidth=2;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();
    if(progress<=.001)return;
    ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();
    ctx.fillStyle=accent;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();
    // Un disque d'ombre de même rayon glisse depuis la gauche : entièrement écarté à
    // 100 % (pleine lune), exactement superposé à 0 % (lune noire).
    ctx.globalCompositeOperation="destination-out";
    ctx.beginPath();ctx.arc(cx-2*r*progress,cy,r,0,Math.PI*2);ctx.fill();
    ctx.globalCompositeOperation="source-over";ctx.restore();
  }
  // Colonnes : le temps se lit comme un niveau qui retombe, colonne après colonne.
  function drawBars(progress){
    resize();const w=canvas.clientWidth,h=canvas.clientHeight,count=14,
      accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),
      border=getComputedStyle(app).getPropertyValue("--focus-border").trim(),
      span=Math.min(w,h)*.88,gap=span/count,barW=gap*.58,base=h*.80,maxH=h*.56,
      alive=progress*count,ox=w/2-span/2;
    ctx.clearRect(0,0,w,h);
    for(let i=0;i<count;i++){
      // Une hauteur propre à chaque colonne, stable d'une image à l'autre.
      const shape=.45+.55*Math.abs(Math.sin(i*1.7)),full=maxH*shape,x=ox+i*gap+(gap-barW)/2,
        fill=Math.max(0,Math.min(1,alive-i));
      ctx.fillStyle=border;ctx.globalAlpha=.35;
      ctx.beginPath();ctx.roundRect(x,base-full,barW,full,barW*.3);ctx.fill();
      if(fill>0){
        ctx.globalAlpha=1;ctx.fillStyle=accent;
        const height=full*fill;
        ctx.beginPath();ctx.roundRect(x,base-height,barW,height,barW*.3);ctx.fill();
      }
    }
    ctx.globalAlpha=1;
  }
  // Spirale : le fil se déroule du centre vers l'extérieur, et se rétracte avec le temps.
  function drawSpiral(progress){
    resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,cy=h*.46,
      accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),
      border=getComputedStyle(app).getPropertyValue("--focus-border").trim(),
      turns=4,maxR=Math.min(w,h)*.42,steps=460;
    ctx.clearRect(0,0,w,h);
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
    trace(1,border,3,.32);          // le chemin complet reste visible
    trace(progress,accent,5,1);     // la part qu'il reste à parcourir
  }
  // Soleil : sa course dit l'heure qui reste, du lever au coucher.
  function drawSun(progress){
    resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,horizon=h*.7,
      accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),
      border=getComputedStyle(app).getPropertyValue("--focus-border").trim(),
      arc=Math.min(w,h)*.42,r=Math.min(w,h)*.11;
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle=border;ctx.lineWidth=2;ctx.globalAlpha=.4;
    ctx.beginPath();ctx.arc(cx,horizon,arc,Math.PI,0);ctx.stroke();      // la trajectoire
    ctx.globalAlpha=.7;ctx.beginPath();ctx.moveTo(cx-arc*1.25,horizon);ctx.lineTo(cx+arc*1.25,horizon);ctx.stroke();
    ctx.globalAlpha=1;
    // Le soleil part de l'ouest à 100 % et se couche à l'est : il descend avec le temps.
    const angle=Math.PI*(1-progress),x=cx+Math.cos(angle)*arc,y=horizon-Math.sin(angle)*arc;
    if(y<=horizon+1){
      ctx.fillStyle=accent;ctx.shadowColor=accent;ctx.shadowBlur=34;
      ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
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
      if(data?.competency)$("#stage-message").textContent=`${data.hours} h REPORTÉES SUR ${data.competency.toUpperCase()}`;
    }).catch(()=>{});
  }
  function render(force=false){
    if(state.running){state.remaining=Math.max(0,(state.endsAt-Date.now())/1000);if(state.remaining<=0&&!state.finished)finish();}
    const second=Math.ceil(state.remaining),progress=clamp(state.remaining/Math.max(1,state.total),0,1),warning=!state.finished&&state.remaining<=state.warning;
    if(force||second!==lastSecond){lastSecond=second;const text=format(state.remaining);$("#canvas-time").textContent=text;$("#digital-time").textContent=text;$("#zen-time").textContent=text;$("#duration-input").value=format(state.total);$("#digital-progress").style.setProperty("--progress",progress);app.dataset.warning=String(warning);app.dataset.finished=String(state.finished);app.dataset.ambience=state.ambience;app.dataset.focusLevel=String(state.focusLevel);app.classList.toggle("hushed",state.focusLevel===2);app.classList.toggle("bare",state.focusLevel===3);$("#live-chip").textContent=state.running?"● EN DIRECT":state.finished?"● TERMINÉ":"● PRÊT";$("#session-status").textContent=state.running?"● SESSION EN COURS":state.finished?"● SESSION TERMINÉE":"● PRÊT";$("#stage-message").textContent=state.finished?"TEMPS ÉCOULÉ":state.running?"RESTEZ DANS VOTRE RYTHME":"ESPACE POUR DÉMARRER";$("#main-control").textContent=state.finished?"↻ RECOMMENCER":state.running?"Ⅱ PAUSE":"▶ DÉMARRER";$("#stage-intention").textContent=(state.intention||"SESSION DE CONCENTRATION").toUpperCase();$("#ambience-status").textContent=`${state.ambience.toUpperCase()} · FOCUS ${state.focusLevel}`;$("#zen-time").style.visibility=state.focusLevel===3&&!warning?"hidden":"visible";if(warning&&!warningCue){warningCue=true;flash();}save();}
    const mode=state.mode;$("#visual-wrap").dataset.mode=mode;
    const painters={ring:drawRing,hourglass:drawHourglass,wave:drawWave,candle:drawCandle,beads:drawBeads,moon:drawMoon,bars:drawBars,spiral:drawSpiral,sun:drawSun};
    if(painters[mode])painters[mode](progress);
    $("#canvas-label").textContent={ring:"TEMPS RESTANT",hourglass:"ÉCOULEMENT RÉEL",wave:"MARÉE DESCENDANTE",candle:"IL RESTE À BRÛLER",beads:"PERLES RESTANTES",moon:"DÉCROISSANCE",bars:"NIVEAU RESTANT",spiral:"FIL À DÉROULER",sun:"AVANT LE COUCHER"}[mode]||"TEMPS RESTANT";
    app.dataset.decorDensity=String(state.decorDensity);
    decor.use(decorNames[state.ambience]||"motes",state.decorDensity);
    app.querySelectorAll(".decor-levels [data-decor]").forEach(b=>b.classList.toggle("active",Number(b.dataset.decor)===state.decorDensity));
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
  function loadTrack(autoplay=false){const track=currentPlaylist?.tracks[index];if(!track){player.removeAttribute("src");$("#player-title").textContent="Playlist vide";$("#player-artist").textContent="";return;}player.src=track.url;$("#player-title").textContent=track.title;$("#player-artist").textContent=track.artist||"";if(autoplay)player.play().catch(()=>{});}
  function move(direction){if(!currentPlaylist?.tracks.length)return;index=shuffle?Math.floor(Math.random()*currentPlaylist.tracks.length):(index+direction+currentPlaylist.tracks.length)%currentPlaylist.tracks.length;loadTrack(true)}
  // Sans playlist, le lecteur n'est pas rendu : le minuteur doit continuer de
  // fonctionner sans lui, d'où la sortie anticipée plutôt qu'une erreur en cascade.
  if($("#playlist-select")){
    $("#playlist-select").addEventListener("change",e=>{currentPlaylist=playlists.find(p=>String(p.id)===e.target.value);index=0;loadTrack(false)});$("#player-toggle").addEventListener("click",()=>player.paused?player.play():player.pause());$("#player-prev").addEventListener("click",()=>move(-1));$("#player-next").addEventListener("click",()=>move(1));$("#player-shuffle").addEventListener("click",e=>{shuffle=!shuffle;e.currentTarget.classList.toggle("active",shuffle)});$("#player-repeat").addEventListener("click",e=>{repeat=!repeat;e.currentTarget.classList.toggle("active",repeat)});$("#player-volume").addEventListener("input",e=>player.volume=Number(e.target.value));player.addEventListener("play",()=>$("#player-toggle").textContent="Ⅱ");player.addEventListener("pause",()=>$("#player-toggle").textContent="▶");player.addEventListener("ended",()=>repeat?player.play():move(1));player.volume=.65;
  }
  render(true);cancelAnimationFrame(frame);loop();
});
