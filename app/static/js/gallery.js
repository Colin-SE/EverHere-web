import {t,h,m,locale} from './i18n.js';
/* 原图查看独立于事实编辑；切换照片不改变资源顺序或保存内容。 */
import {localPhoto} from './ui.js';
const dialog=document.getElementById('photo-dialog'),image=document.getElementById('full-photo'),stage=document.getElementById('photo-stage');
let photos=[],index=0,zoom=1,x=0,y=0,drag=null;
function transform(){image.style.transform=`translate(${x}px,${y}px) scale(${zoom})`;}
function reset(){zoom=1;x=y=0;transform();}
function render(){reset();document.getElementById('photo-position').textContent=`${index+1} / ${photos.length}`;document.getElementById('photo-error').textContent='';image.hidden=!localPhoto(photos[index]);if(image.hidden){image.removeAttribute('src');document.getElementById('photo-error').textContent=t('这张原图尚未在本机恢复，照片元信息仍保留。');}else image.src=photos[index];}
export function openGallery(uris,selected=0){photos=[...uris];if(!photos.length)return;index=Math.max(0,Math.min(photos.length-1,selected));render();if(!dialog.open)dialog.showModal();}
image.addEventListener('error',()=>{document.getElementById('photo-error').textContent=t('原图暂时不可读取，请重试；记录和照片引用保持不变。');});
image.addEventListener('load',()=>{document.getElementById('photo-error').textContent='';});
stage.addEventListener('wheel',event=>{event.preventDefault();zoom=Math.min(8,Math.max(1,zoom*(event.deltaY<0?1.15:1/1.15)));if(zoom===1)x=y=0;transform();},{passive:false});
image.addEventListener('dblclick',()=>{zoom=zoom===1?2:1;x=y=0;transform();});
stage.addEventListener('pointerdown',event=>{drag={id:event.pointerId,x:event.clientX,y:event.clientY,startX:x,startY:y};stage.setPointerCapture(event.pointerId);});
stage.addEventListener('pointermove',event=>{if(!drag||drag.id!==event.pointerId||zoom===1)return;x=drag.startX+event.clientX-drag.x;y=drag.startY+event.clientY-drag.y;transform();});
stage.addEventListener('pointerup',()=>{drag=null;});stage.addEventListener('pointercancel',()=>{drag=null;});
document.addEventListener('click',event=>{if(!dialog.open)return;const button=event.target.closest('button');if(!button)return;if(button.dataset.photoStep){index=(index+Number(button.dataset.photoStep)+photos.length)%photos.length;render();}if(button.dataset.action==='photo-reset')reset();if(button.dataset.action==='photo-retry')render();});
dialog.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();index=(index+(event.key==='ArrowLeft'?-1:1)+photos.length)%photos.length;render();}});
dialog.addEventListener('close',()=>{image.removeAttribute('src');photos=[];reset();});
