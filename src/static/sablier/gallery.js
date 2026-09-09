(() => {
  const app=document.querySelector('#focus-app'),select=document.querySelector('#ambience-select');
  const gallery=document.querySelector('#world-gallery');if(!gallery)return;
  const key=`myent-world-favorites:${app.dataset.user}`;
  let favorites;
  try {const saved=JSON.parse(localStorage.getItem(key)||'[]');favorites=new Set(Array.isArray(saved)?saved:[]);}catch{favorites=new Set();}
  const cards=[...gallery.querySelectorAll('[data-world-card]')];
  const filter=document.querySelector('#world-filter');
  function sync() {
    for(const card of cards) {
      const world=card.dataset.worldCard,favorite=favorites.has(world),choice=card.querySelector('[data-world-choice]');
      choice.setAttribute('aria-pressed',String(world===app.dataset.ambience));
      card.querySelector('[data-favorite]').setAttribute('aria-pressed',String(favorite));
      card.querySelector('[data-favorite]').textContent=favorite?'★':'☆';
      card.hidden=filter.value==='favorites'?!favorite:filter.value!=='all'&&filter.value!==card.dataset.group;
    }
    document.querySelector('#world-empty').hidden=cards.some(card=>!card.hidden);
    select.value=app.dataset.ambience;
  }
  gallery.addEventListener('click',event=>{
    const choice=event.target.closest('[data-world-choice]'),star=event.target.closest('[data-favorite]');
    if(choice){select.value=choice.dataset.worldChoice;select.dispatchEvent(new Event('change',{bubbles:true}));}
    if(star){const world=star.dataset.favorite;if(favorites.has(world))favorites.delete(world);else favorites.add(world);
      try{localStorage.setItem(key,JSON.stringify([...favorites]));}catch{document.querySelector('#world-empty').textContent='Les favoris restent disponibles jusqu’à la fermeture de cette page.';}}
    sync();
  });
  gallery.addEventListener('keydown',event=>{
    if(!['ArrowRight','ArrowLeft','ArrowDown','ArrowUp','Home','End'].includes(event.key))return;
    if(!event.target.matches('[data-world-choice]'))return;
    const choices=cards.filter(c=>!c.hidden).map(c=>c.querySelector('[data-world-choice]'));
    const i=choices.indexOf(event.target),step=['ArrowRight','ArrowDown'].includes(event.key)?1:-1;
    const next=event.key==='Home'?0:event.key==='End'?choices.length-1:(i+step+choices.length)%choices.length;
    event.preventDefault();choices[next]?.focus();
  });
  filter.addEventListener('change',sync);
  new MutationObserver(sync).observe(app,{attributes:true,attributeFilter:['data-ambience']});
  sync();
  const fallback=document.querySelector('#world-fallback'),status=document.querySelector('#renderer-status');
  const portrait=matchMedia('(max-width: 700px)');
  fallback.addEventListener('error',()=>{fallback.dataset.unavailable='true';});
  fallback.addEventListener('load',()=>{delete fallback.dataset.unavailable;});
  function rendererState(){
    const decor=JSON.parse(document.querySelector('#decor-data').textContent)[app.dataset.ambience];
    status.hidden=app.dataset.renderer3d!=='fallback';
    if(!status.hidden){
      // La vignette de la galerie ne ferait pas une vue plein cadre : le repli tire sur
      // la version large, l'orientation décidant seule laquelle des deux est chargée.
      const url=`${gallery.dataset.thumbnailBase}${decor}${portrait.matches?'-mobile':'-wide'}.webp?v=${gallery.dataset.thumbnailVersion}`;
      if(fallback.getAttribute('src')!==url)fallback.src=url;
    }
    status.textContent=status.hidden?'':'Vue fixe · rendu 3D indisponible';
    status.title=app.dataset.renderer3dReason||'';
  }
  new MutationObserver(rendererState).observe(app,{attributes:true,attributeFilter:['data-ambience','data-renderer3d','data-renderer3d-reason']});
  portrait.addEventListener('change',rendererState);
  rendererState();
})();
