import {t,h,m,locale} from './i18n.js';
/* 本地图标与转义工具，不依赖 CDN，不把用户正文当 HTML 执行。 */
const paths = {
  home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18m-13 5h2m4 0h2"/>',
  globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6.5h14M5 17.5h14"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  people:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-17a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 4v3"/>',
  thread:'<path d="M6 3v10a5 5 0 0 0 10 0V8m-4 0 4-4 4 4"/><circle cx="6" cy="3" r="1.5"/>',
  book:'<path d="M12 5v16M3 3h4a5 5 0 0 1 5 2 5 5 0 0 1 5-2h4v16h-4a5 5 0 0 0-5 2 5 5 0 0 0-5-2H3z"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 5v2"/>',
  archive:'<path d="M4 7h16v14H4zM3 3h18v4H3zm6 9h6"/>',
  sprout:'<path d="M12 22v-9M12 13C4 14 2 10 3 4c6 0 10 2 9 9Zm0 4c8 1 10-3 9-9-6 0-9 3-9 9Z"/>',
  chevron:'<path d="m9 6 6 6-6 6"/>',
  shield:'<path d="m12 2 8 3v6c0 6-8 11-8 11S4 17 4 11V5z"/><path d="m8 11 3 3 5-6"/>',
  settings:'<path d="m10 3-.7 3-2 .9L4.5 6 2.7 9l2.1 2v2l-2.1 2 1.8 3 2.8-.9 2 .9.7 3h4l.7-3 2-.9 2.8.9 1.8-3-2.1-2v-2l2.1-2L19.5 6l-2.8.9-2-.9L14 3z"/><circle cx="12" cy="12" r="3"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  sparkles:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5zM20 2v4m-2-2h4"/>',
  heart:'<path d="M20.5 4.5a5 5 0 0 0-7 0L12 6l-1.5-1.5a5 5 0 0 0-7 7L12 20l8.5-8.5a5 5 0 0 0 0-7Z"/>',
  list:'<path d="M8 5h13M8 12h13M8 19h13M3 5h.01M3 12h.01M3 19h.01"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  filter:'<path d="M4 6h16M7 12h10M10 18h4"/>',
  image:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  pin:'<path d="M19 10c0 5-7 12-7 12S5 15 5 10a7 7 0 0 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
  smile:'<circle cx="12" cy="12" r="9"/><path d="M8 14a4 4 0 0 0 8 0M8 9h.01M16 9h.01"/>',
  edit:'<path d="m15 5 4 4M4 20l1-5L17 3a2.8 2.8 0 0 1 4 4L9 19z"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  logout:'<path d="M10 4H4v16h6m-1-8h12m-5-5 5 5-5 5"/>',
  pet:'<ellipse cx="12" cy="16" rx="5" ry="4"/><circle cx="5" cy="9" r="2"/><circle cx="10" cy="5" r="2"/><circle cx="16" cy="5" r="2"/><circle cx="20" cy="10" r="2"/>'
};
export const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.book}</svg>`;
export function hydrateIcons(root = document) { root.querySelectorAll('[data-icon]').forEach(node => { node.innerHTML = icon(node.dataset.icon); }); }
export const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export function today() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
export function dateLabel(value, options = {}) {
  if(!value)return t('日期未详');
  const year=/^([+-]?[0-9]{1,10})$/.exec(value);
  if(year)return locale()==='en'?year[1]:year[1]+'年';
  const month=/^([+-]?[0-9]{4,10})-([0-9]{2})$/.exec(value);
  if(month){
    if(locale()==='en')return new Intl.DateTimeFormat('en',{month:'long'}).format(new Date(2000,Number(month[2])-1,1))+' '+month[1];
    return month[1]+'年'+Number(month[2])+'月';
  }
  // 扩展年份保留原文，不交给 Date 改写为公元日期。
  if(!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)||value.startsWith('0000'))return value;
  const date=new Date(value+'T12:00:00');
  return Number.isNaN(date.getTime())?value:date.toLocaleDateString(locale(),{year:'numeric',month:'long',day:'numeric',...options});
}
export function localPhoto(uri) { return typeof uri === 'string' && /^\/api\/v1\/photos\/[a-f0-9-]{36}$/.test(uri); }
export function moodLabel(value){
  // 已有八个心情值属于稳定存储值；自定义/导入文字不作翻译。
  return ['开心','平静','温暖','期待','自由','难过','疲惫','复杂'].includes(value)?t(value):value;
}
export const stateLabels = {occurred:t('已发生'), ongoing:t('进行中'), planned:t('计划中'), recurring:t('周期性')};
export const typeLabels = {person:t('人物'),pet:t('宠物'),place:t('地点'),work:t('工作'),media:t('影音作品'),custom:t('自定义')};
export const threadLabels = {active:t('进行中'),planned:t('准备开始'),paused:t('暂时搁置'),completed:t('已完成'),redirected:t('转向了'),ended:t('已结束')};
let toastTimer;
export function toast(message) { const node = document.getElementById('toast'); if (!node) return; node.textContent=message; node.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>{node.hidden=true;},3800); }
