// Textures Poly Haven CC0, servies par MyENT. Voir materials/provenance.json.
// Cache limité à la composition : aucun téléchargement externe pendant une session.
const ASSETS={wood:'wood_table_worn',bark:'bark_brown_02',rock:'rock_face_03',soil:'forest_floor'};
export function materialLibrary(T) {
  const cache=new Map(),loader=new T.TextureLoader(),app=document.querySelector('#focus-app');
  const pending=delta=>{if(app)app.dataset.materialLoads=String(Math.max(0,Number(app.dataset.materialLoads||0)+delta));};
  const changed=()=>{if(app)app.dataset.materialRevision=String(Number(app.dataset.materialRevision||0)+1);};
  return function apply(material,kind,repeat=[2,2]) {
    const asset=ASSETS[kind];if(!asset)return material;
    for(const [channel,property] of [['diff','map'],['normal','normalMap']]) {
      const key=asset+channel+repeat.join(',');
      let record=cache.get(key);
      if(!record) {
        record={consumers:new Set(),loaded:false,texture:null};cache.set(key,record);pending(1);
        loader.load(new URL(`../materials/${asset}-${channel}.webp`,import.meta.url).href,texture=>{
          texture.wrapS=texture.wrapT=T.RepeatWrapping;texture.repeat.set(...repeat);texture.anisotropy=4;
          if(channel==='diff')texture.colorSpace=T.SRGBColorSpace;
          record.texture=texture;record.loaded=true;
          for(const consumer of record.consumers){consumer[property]=texture;consumer.needsUpdate=true;}
          if(!record.consumers.size)texture.dispose();pending(-1);changed();
        },undefined,()=>{pending(-1);changed();console.warn('Sablier : matière indisponible',asset,channel);});
      }
      record.consumers.add(material);
      if(record.loaded){material[property]=record.texture;material.needsUpdate=true;}
      material.addEventListener('dispose',()=>{record.consumers.delete(material);if(!record.consumers.size)record.texture?.dispose();});
    }
    return material;
  };
}
