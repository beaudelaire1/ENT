document.addEventListener("DOMContentLoaded", () => {
  const app = document.querySelector("#focus-app");
  if (!app) return;
  const $ = (selector) => app.querySelector(selector);
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const storageKey = `myent:sablier:${app.dataset.user}`;
  const defaultTotal = Number(app.dataset.total) || 300;
  let state = {total:defaultTotal,remaining:defaultTotal,running:false,finished:false,endsAt:0,mode:app.dataset.mode,intention:$("#session-intention").value,warning:Number(app.dataset.warning)||60,focusLevel:Number(app.dataset.focusLevel)||2,ambience:app.dataset.ambience};
  try { state = {...state,...JSON.parse(localStorage.getItem(storageKey)||"{}")}; } catch (_) {}
  if (state.running) state.remaining = Math.max(0,(state.endsAt-Date.now())/1000);
  if (state.running && state.remaining <= 0) { state.running=false; state.finished=true; }
  let lastSecond = -1, warningCue=false, frame=0;
  const canvas=$("#timer-canvas"),ctx=canvas.getContext("2d"),finishAudio=$("#finish-audio"),soundscape=$("#soundscape-audio");

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
  function drawRing(progress){resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,cy=h/2,r=Math.min(w,h)*.34,line=Math.max(14,r*.075),accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),border=getComputedStyle(app).getPropertyValue("--focus-border").trim();ctx.clearRect(0,0,w,h);ctx.lineCap="round";ctx.lineWidth=line;ctx.strokeStyle=border;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();if(progress>.001){ctx.strokeStyle=accent;ctx.shadowColor=accent;ctx.shadowBlur=20;ctx.beginPath();ctx.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+Math.PI*2*progress);ctx.stroke();ctx.shadowBlur=0;}}
  function bottlePath(cx,cy,hw,hh){const neck=hw*.1;ctx.beginPath();ctx.moveTo(cx-hw,cy-hh);ctx.bezierCurveTo(cx-hw*.94,cy-hh*.46,cx-hw*.23,cy-hh*.19,cx-neck,cy);ctx.bezierCurveTo(cx-hw*.23,cy+hh*.19,cx-hw*.94,cy+hh*.46,cx-hw,cy+hh);ctx.lineTo(cx+hw,cy+hh);ctx.bezierCurveTo(cx+hw*.94,cy+hh*.46,cx+hw*.23,cy+hh*.19,cx+neck,cy);ctx.bezierCurveTo(cx+hw*.23,cy-hh*.19,cx+hw*.94,cy-hh*.46,cx+hw,cy-hh);ctx.closePath();}
  function drawHourglass(progress){resize();const w=canvas.clientWidth,h=canvas.clientHeight,cx=w/2,cy=h*.44,hh=h*.32,hw=w*.22,accent=getComputedStyle(app).getPropertyValue("--focus-accent").trim(),border=getComputedStyle(app).getPropertyValue("--focus-border").trim();ctx.clearRect(0,0,w,h);bottlePath(cx,cy,hw,hh);ctx.fillStyle="rgba(170,180,220,.08)";ctx.fill();ctx.strokeStyle="rgba(220,230,250,.6)";ctx.lineWidth=2;ctx.stroke();ctx.save();bottlePath(cx,cy,hw-4,hh-5);ctx.clip();ctx.fillStyle=accent;
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
    if(force||second!==lastSecond){lastSecond=second;const text=format(state.remaining);$("#canvas-time").textContent=text;$("#digital-time").textContent=text;$("#zen-time").textContent=text;$("#duration-input").value=format(state.total);$("#digital-progress").style.setProperty("--progress",progress);app.dataset.warning=String(warning);app.dataset.finished=String(state.finished);$("#live-chip").textContent=state.running?"● EN DIRECT":state.finished?"● TERMINÉ":"● PRÊT";$("#session-status").textContent=state.running?"● SESSION EN COURS":state.finished?"● SESSION TERMINÉE":"● PRÊT";$("#stage-message").textContent=state.finished?"TEMPS ÉCOULÉ":state.running?"RESTEZ DANS VOTRE RYTHME":"ESPACE POUR DÉMARRER";$("#main-control").textContent=state.finished?"↻ RECOMMENCER":state.running?"Ⅱ PAUSE":"▶ DÉMARRER";$("#stage-intention").textContent=(state.intention||"SESSION DE CONCENTRATION").toUpperCase();$("#ambience-status").textContent=`${state.ambience.toUpperCase()} · FOCUS ${state.focusLevel}`;$("#zen-time").style.visibility=state.focusLevel===3&&!warning?"hidden":"visible";if(warning&&!warningCue){warningCue=true;flash();}save();}
    const mode=state.mode;$("#visual-wrap").dataset.mode=mode;if(mode==="ring")drawRing(progress);else if(mode==="hourglass")drawHourglass(progress);$("#canvas-label").textContent=mode==="ring"?"TEMPS RESTANT":"ÉCOULEMENT RÉEL";app.querySelectorAll(".mode-grid [data-mode]").forEach(button=>button.classList.toggle("active",button.dataset.mode===mode));app.querySelectorAll(".focus-levels [data-level]").forEach(button=>button.classList.toggle("active",Number(button.dataset.level)===state.focusLevel));
  }
  function loop(){render();frame=requestAnimationFrame(loop)}
  $("#apply-duration").addEventListener("click",()=>{const input=$("#duration-input"),seconds=parseDuration(input.value);input.setCustomValidity("");if(seconds)setDuration(seconds);else {input.setCustomValidity("Durée invalide (maximum 24 h).");input.reportValidity();}});
  app.querySelectorAll("[data-preset]").forEach(b=>b.addEventListener("click",()=>setDuration(Number(b.dataset.preset)*60)));
  app.querySelectorAll(".mode-grid [data-mode]").forEach(b=>b.addEventListener("click",()=>{state.mode=b.dataset.mode;save();render(true)}));
  app.querySelectorAll(".focus-levels [data-level]").forEach(b=>b.addEventListener("click",()=>{state.focusLevel=Number(b.dataset.level);save();render(true)}));
  $("#session-intention").addEventListener("input",e=>{state.intention=e.target.value;save();render(true)});
  $("#ambience-select").addEventListener("change",e=>{state.ambience=e.target.value;save();setSoundscape();render(true)});
  $("#warning-slider").addEventListener("input",e=>{state.warning=Number(e.target.value);$("#warning-output").textContent=`${state.warning} s`;warningCue=false;save()});
  $("#main-control").addEventListener("click",startPause);$("#reset-control").addEventListener("click",reset);$("#minus-minute").addEventListener("click",()=>adjust(-60));$("#plus-minute").addEventListener("click",()=>adjust(60));
  function setSoundscape(){if(app.dataset.soundscape!=="true"){soundscape.pause();return;}soundscape.src=`/static/sablier/audio/${state.ambience}.wav`;soundscape.volume={1:.03,2:.055,3:.09}[state.focusLevel];soundscape.play().catch(()=>{});}
  $("#soundscape-toggle").addEventListener("click",()=>{app.dataset.soundscape=app.dataset.soundscape==="true"?"false":"true";$("#soundscape-toggle").classList.toggle("active",app.dataset.soundscape==="true");setSoundscape();});
  $("#scene-button").addEventListener("click",async()=>{app.classList.add("stage-mode");try{await app.requestFullscreen()}catch(_){}});document.addEventListener("fullscreenchange",()=>{if(!document.fullscreenElement)app.classList.remove("stage-mode")});
  document.addEventListener("keydown",e=>{if(["INPUT","TEXTAREA","SELECT"].includes(document.activeElement?.tagName))return;if(e.code==="Space"){e.preventDefault();startPause()}else if(e.key.toLowerCase()==="r")reset();else if(e.key==="F11"){e.preventDefault();$("#scene-button").click()}else if(e.key==="Escape"&&app.classList.contains("stage-mode")){document.exitFullscreen?.();app.classList.remove("stage-mode")}});
  const prefForm=$("#focus-preferences"),durationHidden=prefForm.querySelector("#id_default_duration_seconds");prefForm.addEventListener("submit",()=>{durationHidden.value=Math.round(state.total);prefForm.querySelector("#id_session_intention").value=state.intention;prefForm.querySelector("#id_mode").value=state.mode;prefForm.querySelector("#id_ambience").value=state.ambience;prefForm.querySelector("#id_focus_level").value=state.focusLevel;prefForm.querySelector("#id_warning_seconds").value=state.warning;prefForm.querySelector("#id_soundscape_enabled").checked=app.dataset.soundscape==="true";});

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
