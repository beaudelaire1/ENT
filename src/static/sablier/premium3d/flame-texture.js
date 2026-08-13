export function flameTexture(THREE) {
  const canvas=document.createElement("canvas"); canvas.width=128; canvas.height=256;
  const ctx=canvas.getContext("2d"); ctx.clearRect(0,0,128,256);
  const glow=ctx.createRadialGradient(64,150,4,64,150,72); glow.addColorStop(0,"rgba(255,245,190,1)"); glow.addColorStop(.24,"rgba(255,180,55,.92)"); glow.addColorStop(.62,"rgba(255,88,12,.34)"); glow.addColorStop(1,"rgba(255,60,0,0)"); ctx.fillStyle=glow; ctx.beginPath(); ctx.ellipse(64,150,48,96,0,0,Math.PI*2); ctx.fill();
  const core=ctx.createLinearGradient(0,72,0,210); core.addColorStop(0,"rgba(255,255,235,0)"); core.addColorStop(.35,"rgba(255,250,205,.92)"); core.addColorStop(.72,"rgba(255,170,55,.92)"); core.addColorStop(1,"rgba(60,105,255,.22)"); ctx.fillStyle=core; ctx.beginPath(); ctx.moveTo(64,54); ctx.bezierCurveTo(98,105,88,178,64,215); ctx.bezierCurveTo(40,178,30,105,64,54); ctx.fill();
  const texture=new THREE.CanvasTexture(canvas); texture.colorSpace=THREE.SRGBColorSpace; return texture;
}
