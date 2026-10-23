/* 只翻译开发者声明的界面文案；用户输入、协议字段和插值保持原样。 */
import english from './messages-en.js';

export const locale=()=>typeof document!=='undefined'&&document.documentElement.lang==='en'?'en':'zh-CN';
export function t(source,values={}){
  const message=locale()==='en'?(english[source]??source):source;
  return message.replace(/\{([a-zA-Z0-9_]+)\}/g,(match,key)=>Object.hasOwn(values,key)?String(values[key]):match);
}
const escape=value=>value.replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
function fragment(source,html){
  if(locale()!=='en')return source;
  // 分隔符是静态HTML语法。仅替换字典里明确列出的文本与属性片段。
  return source.split(/([<>"'\n])/).map(part=>{
    const key=part.trim();if(!Object.hasOwn(english,key))return part;
    const translated=html?escape(english[key]):english[key];
    return part.slice(0,part.length-part.trimStart().length)+translated+part.slice(part.trimEnd().length);
  }).join('');
}
export function h(strings,...values){
  if(typeof strings==='string')return fragment(strings,true);
  return strings.reduce((out,part,index)=>out+fragment(part,true)+(index<values.length?values[index]:''),'');
}
export function m(strings,...values){return strings.reduce((out,part,index)=>out+fragment(part,false)+(index<values.length?values[index]:''),'');}

/* 页面重载采用已选语言重新呈现；URL保留当前视图和筛选。编辑中的对话框先保存或关闭。 */
if(typeof document!=='undefined')document.addEventListener('change',event=>{
  const control=event.target.closest('[data-language-select]');if(!control)return;
  const next=control.value;if(!['zh-CN','en'].includes(next)||next===locale())return;
  const change=new CustomEvent('everhere:language-request',{detail:{language:next},cancelable:true});
  if(!window.dispatchEvent(change)){control.value=locale();return;}
  document.cookie=`everhere-language=${next}; Path=/; Max-Age=31536000; SameSite=Lax${location.protocol==='https:'?'; Secure':''}`;
  if(!document.cookie.split('; ').includes('everhere-language='+next)){
    control.value=locale();const node=document.getElementById('toast')||document.getElementById('auth-error');
    if(node){node.textContent=t('当前浏览器未能保存语言偏好，请允许本站 Cookie 后重试。');node.hidden=false;}return;
  }
  location.reload();
});
