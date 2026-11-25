import {api,getSession} from './api.js';
import {locale,t,h} from './i18n.js';
import {showOrders,submitOrderAction,submitTradeAction} from './orders.js';

// 所有私人内容仅放在当前页面内存；文本一律转义，不作为 HTML 执行。
const root=document.getElementById('workspace-content'), errorBox=document.getElementById('workspace-error');
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=cents=>new Intl.NumberFormat(locale(),{style:'currency',currency:'CNY'}).format(cents/100);
const labels={draft:t('草稿'),submitted:t('待审核'),returned:t('需修改'),approved:t('待制作'),ready:t('已完成'),unpaid:t('待支付')};
let member=null,records=[],memoirs=[],products=[],current=null,edit=null,productEdit=null,dirty=false,loadId=0;
let authMode='login',orderRequest=null,coverFile=null,sharedIdentity=false,emailChallenge=null,emailVerified=false;
let generationTimer, catalogueQuery={}, purchasePhoto=null, pendingTab=null, submitting=false, renderedHash='';
const status=state=>h`<span class="badge">${esc(labels[state]||state)}</span>`;
const versionBody=item=>({version:item.version,revisionId:item.revisionId});
function error(value){errorBox.textContent=value?.message||String(value);errorBox.hidden=false;}
function clearError(){errorBox.hidden=true;errorBox.textContent='';}
function heading(kicker,title,description=''){return h`<p class="eyebrow">${kicker}</p><h1>${title}</h1><p class="intro">${description}</p>`;}
function requireAccount(){if(member)return true;root.innerHTML=heading('YOUR PRIVATE SPACE',t('登录后，继续整理属于你的回忆'),t('人生相册仍可作为访客使用。回忆录与订单通过账户区分归属。'))+h('<a class="button primary" href="#account">登录 / 注册</a>');return false;}
function markDirty(){dirty=true;}
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
window.addEventListener('everhere:language-request',event=>{if(dirty){event.preventDefault();error(new Error(t('请先保存当前内容，再切换语言。')));}});
root.addEventListener('input',event=>{if(event.target.closest('[data-dirty]')&&event.target.id!=='authorise-materials')markDirty();});
document.addEventListener('click',event=>{
  const link=event.target.closest('a');
  if(!link)return;
  if(submitting||orderRequest?.uncertain){
    event.preventDefault();error(new Error(t('请先确认当前提交的结果。')));return;
  }
  if(dirty){
    if(!confirm(t('当前修改尚未保存，确认离开吗？')))event.preventDefault();
    else dirty=false;
  }
},true);
document.querySelector('nav').addEventListener('click',event=>{const link=event.target.closest('[data-tab]');if(link&&!event.defaultPrevented&&link.hash===location.hash){event.preventDefault();route();}});

async function refreshSession(){const session=await getSession();const capabilities=await api('/accounts/capabilities');sharedIdentity=capabilities.sharedIdentity;member=session.member;emailVerified=session.emailVerified;document.getElementById('admin-link').hidden=member?.role!=='admin';document.getElementById('account-link').textContent=member?member.name:t('登录 / 注册');}
function routeLocation(){
  const [raw,search]=location.hash.slice(1).split('?');
  const [view,item]=raw.split('/');
  const tab=view||document.body.dataset.initialTab||'memoirs';
  const rawParams=new URLSearchParams(search||(!view?location.search:''));
  const filterNames=['page','q','kind','buyer','from','to','assigned','status','state','variant'];
  const params=Object.fromEntries([...rawParams].filter(([key])=>filterNames.includes(key)));
  return {tab:tab==='workspace'?'memoirs':tab,id:item||(!view?document.body.dataset.initialItem:''),params,
    returnedFromAlipay:!view&&tab==='orders'&&rawParams.has('out_trade_no'),
    link(values={},id=''){
      const query=new URLSearchParams(Object.entries(values).filter(([,value])=>value));
      return '#'+tab+(id?'/'+encodeURIComponent(id):'')+(query.size?'?'+query:'');
    }};
}
async function route(){
  const id=++loadId;clearTimeout(generationTimer);clearError();current=null;edit=null;productEdit=null;coverFile=null;purchasePhoto=null;
  const next=routeLocation(),tab=next.tab;
  renderedHash=location.hash;
  next.active=()=>id===loadId;
  document.querySelectorAll('[data-tab]').forEach(link=>link.toggleAttribute('aria-current',tab===link.dataset.tab||tab.startsWith(link.dataset.tab+'-')));
  root.replaceChildren();
  const delayed=setTimeout(()=>{if(id===loadId&&!root.hasChildNodes())root.innerHTML=h('<p class="loading" role="status">正在读取…</p>');},300);
  const longWait=setTimeout(()=>{if(id===loadId&&root.querySelector('.loading'))root.innerHTML=h('<p class="loading" role="status">加载较慢，可以重新加载。 <button data-action="reload">重新读取</button></p>');},10000);
  try{
    if(tab==='account'){renderAccount();if(member&&sharedIdentity)await showDevices(next);return;}
    if(!['shop','product'].includes(tab)&&!requireAccount()){pendingTab=next.link(next.params,next.id);return;}
    if(tab.startsWith('admin')&&member.role!=='admin')throw new Error(t('此页面需要管理员权限。'));
    if(tab==='memoirs'){
      if(next.id){
        const memoir=await api('/memoirs/'+encodeURIComponent(next.id));if(id!==loadId)return;
        showMemoir(memoir);return;
      }
      const m=await api('/memoirs');if(id!==loadId)return;
      memoirs=m.memoirs;renderMemoirs(next.params.state);
    }else if(tab==='shop'){
      catalogueQuery=next.params;
      const p=await api('/shop/products?'+new URLSearchParams(catalogueQuery));if(id!==loadId)return;
      products=p.products;renderShop();
    }else if(tab==='product'){
      const p=await api('/shop/products/'+encodeURIComponent(next.id));if(id!==loadId)return;
      renderProduct(p);
      if(next.params.variant&&member)await startPurchase(p,next.params.variant,id);
    }else if(tab==='orders'||tab==='admin-orders'){
      await showOrders(root,next);
    }else if(tab==='admin-memoirs'){
      const m=await api('/admin/memoirs');if(id!==loadId)return;
      memoirs=m.memoirs;renderAdminQueue(next.params.state);
    }else if(tab==='admin-products'){
      const p=await api('/admin/products');if(id!==loadId)return;products=p.products;renderAdminProducts();
    }else if(tab==='admin'){
      renderAdmin();
    }else{location.hash='memoirs';}
  }catch(value){if(id!==loadId)return;root.innerHTML=h('<div class="empty">读取未完成。<p><button data-action="reload">重新读取</button></p></div>');error(value);checkLogin(value);}
  finally{clearTimeout(delayed);clearTimeout(longWait);}
}

function renderAccount(){
  if(member){root.innerHTML=heading('YOUR ACCOUNT',t('你好，')+esc(member.name),t('此账户统一管理人生相册、回忆录和订单。'))+h`<section class="card"><p>${esc(member.email)}</p>${status(member.role==='admin'?t('制作与商城管理员'):t('普通用户'))} ${status(emailVerified?t('邮箱已验证'):t('邮箱尚未验证'))}<div class="actions"><a class="button" href="/album">进入人生相册</a><a class="button primary" href="#memoirs">我的回忆录</a><button data-action="logout">退出账户</button></div></section>`;return;}
  const registering=authMode==='register',resetting=authMode==='reset',verifying=sharedIdentity&&(registering||resetting);
  root.innerHTML=h`<section class="auth">${heading('KEEP YOUR STORIES',resetting?t('找回密码'):registering?t('建立你的私人账户'):t('欢迎回来'),resetting?t('验证邮箱后设置新密码。原账号与资料保留，其他设备需要重新登录。'):registering?t('可选择将当前浏览器的访客档案归入新账户。资料原 ID 和照片保持不变。'):t('登录已有账户，不会自动转移当前访客档案。'))}<form id="account-form" class="card">${registering?h('<label>显示姓名<input name="name" required maxlength="80" autocomplete="name"></label>'):''}<label>邮箱<input name="email" type="email" required maxlength="254" autocomplete="username"></label>${registering&&verifying?h('<p class="muted">请使用尚未注册的邮箱。已有账户可直接登录，忘记密码可在下方找回。</p>'):''}${verifying?h('<label>邮箱验证码<input name="code" inputmode="numeric" pattern="[0-9]{8}" minlength="8" maxlength="8" autocomplete="one-time-code" required></label><button type="button" data-action="send-code">发送验证码</button><p id="code-status" role="status" class="muted"></p>'):''}<label>${verifying?t('新密码（12—128 个字符）'):t('密码（10—128 个字符）')}<input name="password" type="password" required minlength="${verifying?12:10}" maxlength="128" autocomplete="${registering||resetting?'new-password':'current-password'}"></label>${registering?h('<label class="check"><input name="claim" type="checkbox"><span>我确认将当前访客档案归入此新账户；之后须登录此账户访问。</span></label>'):''}<button class="primary" type="submit">${resetting?t('确认重置密码'):registering?t('注册并进入'):t('登录')}</button><div class="actions"><button type="button" data-action="auth-mode">${registering||resetting?t('已有账户，去登录'):t('没有账户，去注册')}</button>${sharedIdentity&&!resetting?h('<button type="button" data-action="forgot-password">忘记密码</button>'):''}<a href="/">返回访客相册</a></div><p class="muted">管理员由服务器维护者建立；公开注册仅创建普通用户。</p></form></section>`;
}
async function showDevices(route){
  let section=document.getElementById('account-devices');
  if(!section){
    root.insertAdjacentHTML('beforeend',h('<section class="card" id="account-devices"><h2>安卓设备会话</h2><div role="status"></div></section>'));
    section=document.getElementById('account-devices');
  }
  const content=section.lastElementChild;
  try{
    const result=await api('/accounts/devices');
    if(!route.active())return;
    content.innerHTML=result.devices.map(device=>h`<div class="order-item"><strong>${esc(device.name)}</strong>
      <p>${esc(t('会话到期：{date}',{date:new Date(device.expiresAt).toLocaleString(locale())}))}</p>
      <button type="button" data-revoke-device="${esc(device.id)}">退出此设备</button></div>`).join('')||h('<p>当前没有已登录的安卓设备。</p>');
  }catch(value){
    if(route.active())content.innerHTML=h`<p>${esc(value.message)}</p><button type="button" data-action="reload-devices">重新读取</button>`;
  }
}
const generationLabels={queued:'制作排队中',running:'正在生成',failed:'生成失败',succeeded:'已完成'};
function memoirStatus(m){
  return m.generation?status(t(generationLabels[m.generation.state])):status(m.state);
}
function memoirFilters(tab,selected,staff=false){
  const choices=staff?['unclaimed','mine','returned','approved','failed','ready']:['draft','submitted','returned','approved','ready'];
  return h`<nav class="actions"><a class="button" href="#${tab}" aria-current="${!selected?'page':'false'}">全部</a>
    ${choices.map(state=>h`<a class="button" href="#${tab}?state=${state}" aria-current="${selected===state?'page':'false'}">${esc(labels[state]||t({unclaimed:'待领取',mine:'只看我领取的',failed:'生成失败'}[state]))}</a>`).join('')}</nav>`;
}
function renderMemoirs(state){
  const items=memoirs.filter(m=>!state||m.state===state);
  root.innerHTML=heading('MEMOIRS',t('我的回忆录'),t('挑选自己的记录，决定章节与分享范围，再交给制作管理员审核。'))+
    h('<div class="actions"><button class="primary" data-action="new-memoir">整理新回忆录</button><a class="button" href="/album">回到人生相册</a></div>')+
    memoirFilters('memoirs',state)+h`<div class="grid">${items.map(m=>h`<article class="card">${memoirStatus(m)}
      <h2>${esc(m.title)}</h2><p>${esc(m.theme)||t('尚未填写主题')}</p>
      <p class="muted">提交版本 ${m.revisionNumber} ${m.reason?'· '+esc(m.reason):''}</p>
      <a class="button" href="#memoirs/${esc(m.id)}">${['draft','returned'].includes(m.state)?t('继续整理'):t('查看进度与成品')}</a></article>`).join('')||
      h('<div class="empty">当前分类没有回忆录。</div>')}</div>`;
}
function chapterInput(record){return {recordId:record.id,version:record.version,heading:record.title,photoUris:[]};}
function syncEditor(){if(!edit)return;const form=document.getElementById('memoir-form');if(form){edit.title=form.elements.title.value;edit.theme=form.elements.theme.value;form.querySelectorAll('[data-chapter-heading]').forEach(input=>{edit.chapters[Number(input.dataset.chapterHeading)].heading=input.value;});}}
function renderEditor(){
  const selected=new Set(edit.chapters.map(c=>c.recordId));
  root.innerHTML=heading('YOUR MANUSCRIPT',edit.id?t('继续整理回忆录'):t('整理新回忆录'),t('正文取自人生相册。编辑原记录后，请明确更新素材版本；提交时只共享你勾选的照片。'))+h`<form id="memoir-form" data-dirty><div class="split"><section><div class="card"><label>回忆录标题<input name="title" value="${esc(edit.title)}" maxlength="160" required></label><label>主题说明<textarea name="theme" maxlength="300">${esc(edit.theme)}</textarea></label><h2>章节顺序 <small class="muted">${edit.chapters.length} / 20</small></h2>${edit.chapters.map((c,i)=>{
    const r=records.find(r=>r.id===c.recordId);return h`<section class="chapter"><label>第 ${i+1} 章<input data-chapter-heading="${i}" value="${esc(c.heading)}" maxlength="200" required></label><p class="muted">${esc(r?.title||t('来源已移入回收站'))} · 选中版本 ${c.version}${r&&r.version!==c.version?t(' · 原记录已变化，提交前须更新'):''}</p><div class="actions"><button type="button" data-move="${i}" data-direction="-1" ${i===0?'disabled':''}>上移</button><button type="button" data-move="${i}" data-direction="1" ${i===edit.chapters.length-1?'disabled':''}>下移</button><button type="button" data-refresh-chapter="${i}" ${r?'':'disabled'}>更新本章素材版本</button><button type="button" data-remove-chapter="${i}">移除</button></div><div class="photos">${(r?.photoUris||[]).map(uri=>h`<label class="photo-choice"><img src="${esc(uri)}" alt="可选照片" loading="lazy"><input type="checkbox" data-chapter-photo="${i}" value="${esc(uri)}" ${c.photoUris.includes(uri)?'checked':''}>选入本章</label>`).join('')}</div><details><summary>查看来源正文</summary><p class="prose">${esc(r?.content||t('暂无正文'))}</p></details></section>`;
  }).join('')||h('<p class="muted">从右侧挑选记录加入章节。</p>')}<div class="actions"><button class="primary" type="submit">保存草稿</button><button type="button" data-action="back-memoirs">返回列表</button></div></div>${edit.id?h`<div class="card"><h2>确认分享范围并提交</h2><p>本次仅向领取任务的制作管理员提供所选章节的标题、正文、日期、状态、地点及勾选照片。提交后冻结材料；未选照片、人物关系和其他记录不提供。</p><label class="check"><input id="authorise-materials" type="checkbox"><span>我已检查章节与照片，确认授权本次制作使用这些材料。</span></label><button type="button" class="primary" data-action="submit-memoir">提交审核</button><p class="muted">如修改过内容，请先保存草稿。提交后只可在管理员退回时修改。</p></div>`:''}</section><aside><section class="card"><h2>选择自己的记录</h2><p class="muted">最多 20 条。点击加入；勾选照片后才会送审。</p><div class="record-picker">${records.map(r=>h`<label class="record-choice"><input type="checkbox" data-select-record="${esc(r.id)}" ${selected.has(r.id)?'checked':''}> ${esc(r.title)||t('未命名记录')}<small class="muted"> · ${esc(r.eventDate||t('日期待补充'))}</small></label>`).join('')||h('<p>暂无可用记录，请先到人生相册新增。</p>')}</div></section></aside></div></form>`;
}
function snapshotHTML(m){const revision=m.revision;if(!revision)return '';const s=revision.snapshot;return h`<section class="card"><h2>提交版本 ${revision.number} 的冻结材料</h2><p class="muted">相册之后的修改不会改变以下内容。</p><h3>${esc(s.title)}</h3><p>${esc(s.theme)}</p>${s.chapters.map((c,i)=>h`<section class="chapter-read"><h3>${i+1}. ${esc(c.heading)}</h3><p class="muted">${esc(c.date||t('日期待补充'))} · ${esc(c.placeName||'')} · 来源版本 ${c.sourceVersion}</p><div class="prose">${esc(c.content)}</div><div class="photos">${c.photoAssetIds.map(id=>h`<img src="/api/v1/memoirs/${esc(m.id)}/assets/${esc(id)}" alt="用户授权的章节照片" loading="lazy">`).join('')}</div></section>`).join('')}</section>`;}
function renderDetail(m,staff=false){
  current=m;edit=null;
  root.innerHTML=heading('MEMOIR STUDIO',esc(m.title),staff?t('只显示此次申请授权的材料；不会开放用户的私人相册。'):t('每次提交保留独立版本和审核结果。'))+h`<div class="actions"><button data-action="${staff?'back-admin':'back-memoirs'}">返回${staff?t('管理队列'):t('列表')}</button>${status(m.state)}<span class="muted">提交版本 ${m.revisionNumber}</span></div>${m.reason?h`<p class="notice">审核意见：${esc(m.reason)}</p>`:''}${m.renderError?h`<p class="error">${esc(m.renderError)}</p>`:''}${!staff&&['draft','returned'].includes(m.state)?h('<div class="actions"><button class="primary" data-action="edit-memoir">修改草稿 / 重新提交</button></div>'):''}${m.state==='ready'?h`<section class="card"><h2>回忆录已制作完成</h2><p>仅可查看部分样张，完整 PDF 暂不开放。购买高清电子版或纸质版时，可在商城选择此成品。</p><div class="actions"><a class="button primary" href="${esc(m.previewUrl)}" target="_blank" rel="noopener">查看 PDF 预览</a>${!staff?h('<a class="button" href="#shop">选择成品形式</a>'):''}</div><p class="muted">可在电子版订单的付款确认后下载完整 PDF。</p></section>`:''}${staff&&m.state==='submitted'?h('<form id="review-form" class="card"><h2>审核材料</h2><p>检查章节标题、正文完整性与图片可读性。不能在这里改写原文；需要改动时填写原因并退回。</p><label>审核意见（退回时必填）<textarea name="reason" maxlength="2000"></textarea></label><div class="actions"><button name="decision" value="return" type="submit">退回修改</button><button class="primary" name="decision" value="approve" type="submit">审核通过</button></div></form>'):''}${staff&&m.state==='approved'?h`<form id="generate-form" class="card"><h2>制作固定版式回忆录</h2><p>可调整排版顺序和字号，稿件文字保持用户确认的版本。</p><label>章节顺序（用逗号分隔，从 1 开始）<input name="chapterOrder" value="${esc((m.layout?.chapterOrder||m.revision.snapshot.chapters.map((_,i)=>i)).map(i=>i+1).join(','))}" required></label><label>正文字号<input name="fontSize" type="number" min="10" max="16" value="${m.layout?.fontSize||12}" required></label><button class="primary" type="submit">${m.renderError?t('重试生成'):t('生成回忆录')}</button></form>`:''}${snapshotHTML(m)}${m.history?.length?h`<details class="card"><summary>查看提交与审核历史</summary>${m.history.map(r=>h`<p>版本 ${r.number} · ${esc(labels[r.state])}${r.reason?' · '+esc(r.reason):''}</p>`).join('')}</details>`:''}`;
}
function trackGeneration(m,staff){
  clearTimeout(generationTimer);
  if(!['queued','running'].includes(m.generation?.state))return;
  const routeId=loadId;
  generationTimer=setTimeout(async()=>{
    try{
      const result=await api((staff?'/admin/memoirs/':'/memoirs/')+encodeURIComponent(m.id));
      if(routeId!==loadId||current!==m)return;
      showMemoir(result,staff);
    }catch(value){if(routeId===loadId&&current===m){error(value);trackGeneration(m,staff);}}
  },1800);
}
function showMemoir(m,staff=false){
  renderDetail(m,staff);
  const actions=root.querySelector('.actions');
  if(m.generation){
    const badge=document.createElement('span');
    badge.className='badge';badge.setAttribute('role','status');badge.textContent=t(generationLabels[m.generation.state]);
    actions.append(badge);
  }
  if(['queued','running'].includes(m.generation?.state))document.getElementById('generate-form')?.remove();
  trackGeneration(m,staff);
}
// 封面仅来自商品接口，不引用私人相册原图地址。
function productCover(product,modifier=''){
  if(!product.imageUrl)return '';
  return h`<figure class="product-cover ${modifier}"><img src="${esc(product.imageUrl)}" alt="${esc(product.name)}" loading="lazy" decoding="async">${product.name.startsWith('【测试】')?h('<figcaption>测试商品示意图</figcaption>'):''}</figure>`;
}
const kinds={gift:'文创礼品',medal:'纪念奖牌',memoir_digital:'回忆录电子版',memoir_paper:'回忆录纸质版'};
function renderShop(){
  root.innerHTML=heading('KEEPSAKES',t('文创商城'),t('纪念奖牌与礼品可独立定制，不需要先创建回忆录。回忆录成品仅对所属用户提供。'))+h`
    <form id="catalogue-filter" class="card order-filters"><label>搜索商品<input name="q" maxlength="120" value="${esc(catalogueQuery.q)}"></label>
    <label>商品类型<select name="kind"><option value="">不限</option>${Object.entries(kinds).map(([id,label])=>h`<option value="${id}" ${catalogueQuery.kind===id?'selected':''}>${esc(t(label))}</option>`).join('')}</select></label>
    <button type="submit">应用筛选</button></form><div class="grid">
    ${products.map(p=>h`<article class="card product-card">${productCover(p)}<h2>${esc(p.name)}</h2><p>${esc(p.description)}</p>
      ${p.variants.length?h`<p class="price">${esc(t('起价 {price}',{price:money(Math.min(...p.variants.map(v=>v.priceCents)))}))}</p>`:''}
      <a class="button" href="#product/${esc(p.id)}">查看商品与款式</a></article>`).join('')||
      h('<div class="empty">没有符合条件的商品。</div>')}</div>`;
}
function gallery(product){
  return h`<div class="product-gallery">${(product.gallery||[]).map(({url})=>h`<img src="${esc(url)}" alt="商品配图" loading="lazy">`).join('')}</div>`;
}
function renderProduct(product){
  current={product};
  root.innerHTML=h`<div class="actions"><a class="button" href="#shop${Object.keys(catalogueQuery).length?'?'+esc(new URLSearchParams(catalogueQuery)):''}">返回商城</a></div>
    <div class="split"><section class="card">${productCover(product,'product-cover--detail')}${gallery(product)}</section>
    <section class="card"><h1>${esc(product.name)}</h1><p class="prose">${esc(product.description)}</p><h2>商品款式</h2>
    ${product.variants.map(v=>h`<div class="order-item"><h3>${esc(v.name)}</h3><p>${esc(t(kinds[v.kind]))} · ${money(v.priceCents)}</p>
      <button data-buy="${esc(v.id)}">选择与定制</button></div>`).join('')||h('<p>暂无可用款式</p>')}</section></div>`;
}
async function startPurchase(product,variantId,routeId){
  const variant=product.variants.find(v=>v.id===variantId);
  if(!variant)throw new Error(t('商品或款式已下架，请重新选择。'));
  if(!member){
    pendingTab='#product/'+encodeURIComponent(product.id)+'?variant='+encodeURIComponent(variantId);
    location.hash='account';return;
  }
  if(variant.kind.startsWith('memoir_')){
    const list=await api('/memoirs');
    if(routeId!==loadId)return;
    memoirs=list.memoirs;
  }
  renderPurchase(product,variant);
}
function renderPurchase(product,variant){
  current={product,variant};orderRequest=null;purchasePhoto=null;
  root.innerHTML=heading('MAKE IT YOURS',esc(product.name)+' · '+esc(variant.name),t('订单按当前确认的价格、款式和定制内容保存。'))+h`<form id="purchase-form" class="card" data-dirty>${productCover(product,'product-cover--detail')}<p class="price">${money(variant.priceCents)} / 件</p>${variant.kind.startsWith('memoir_')?h`<label>选择自己的已完成回忆录<select name="revisionId" required><option value="">请选择</option>${memoirs.filter(m=>m.state==='ready').map(m=>h`<option value="${esc(m.revisionId)}">${esc(m.title)} · 版本 ${m.revisionNumber}</option>`).join('')}</select></label>`:''}<label>定制文字${variant.textRequired?t('（必填）'):t('（可选）')}<textarea name="customText" maxlength="300" ${variant.textRequired?'required':''}></textarea></label><label>定制照片${variant.photoRequired?t('（必选）'):t('（可选）')}<input name="photo" type="file" accept="image/png,image/jpeg,image/webp" ${variant.photoRequired?'required':''}></label><label class="check"><input name="authorisePhoto" type="checkbox"><span>如选择照片，我确认授权仅将该照片用于本订单。</span></label><label>数量<input type="number" name="quantity" min="1" max="10" value="1" required></label><p id="purchase-total">合计 ${money(variant.priceCents)}</p><section class="custom-preview"><h2>定制文字预览</h2><p id="purchase-preview">填写定制文字后可在此预览。</p><small>示意排版以实际制作效果为准。</small></section><button type="button" data-action="refresh-price" hidden>更新商品与价格</button><div class="actions"><button class="primary" type="submit">确认并创建待支付订单</button><button type="button" data-action="back-shop">返回商城</button></div><p class="muted">创建订单后可在订单详情付款。实体商品在付款前填写收货地址。</p></form>`;
}
function updatePurchasePreview(){
  const form=document.getElementById('purchase-form');
  if(!form||!current?.variant)return;
  const quantity=Number(form.elements.quantity.value);
  const total=document.getElementById('purchase-total');
  total.textContent=t('合计 ')+money(current.variant.priceCents*(Number.isInteger(quantity)&&quantity>=1&&quantity<=10?quantity:1));
  const preview=document.getElementById('purchase-preview');
  if(preview)preview.textContent=form.elements.customText.value||t('填写定制文字后可在此预览。');
}
function lockPurchase(form, locked){
  for(const field of form.querySelectorAll('input,textarea,select'))field.disabled=locked;
  form.querySelector('button[type="submit"]').textContent=t(locked?'查询原订单并重试':'确认并创建待支付订单');
}
async function refreshPurchasePrice(){
  const form=document.getElementById('purchase-form');
  const product=await api('/shop/products/'+encodeURIComponent(current.product.id));
  const variant=product.variants.find(item=>item.id===current.variant.id);
  if(!variant)throw new Error(t('商品或款式已下架，请重新选择。'));
  current={product,variant};
  form.elements.customText.required=variant.textRequired;
  form.elements.photo.required=variant.photoRequired;
  form.querySelector('.price').textContent=money(variant.priceCents)+' / '+t('件');
  form.querySelector('[data-action="refresh-price"]').hidden=true;
  orderRequest=null;updatePurchasePreview();
  error(new Error(t('已更新价格，请核对后再次确认订单。')));
}
function renderAdmin(){
  root.innerHTML=h`<h1>管理后台</h1><div class="grid">
    <a class="card" href="#admin-memoirs">审核与制作</a><a class="card" href="#admin-products">商品管理</a>
    <a class="card" href="#admin-orders">订单处理队列</a></div>`;
}
function renderAdminQueue(state){
  const items=memoirs.filter(m=>!state||({unclaimed:!m.reviewerId,mine:!!m.reviewerId,failed:m.generation?.state==='failed'}[state]??m.state===state));
  root.innerHTML=h`<h1>审核与制作队列</h1>`+memoirFilters('admin-memoirs',state,true)+h`<div class="grid">
    ${items.map(m=>h`<article class="card">${memoirStatus(m)}<h3>${esc(m.title||t('待领取的私人稿件'))}</h3>
     <p class="muted">提交版本 ${m.revisionNumber}</p>${m.reviewerId?h`<button data-admin-memoir="${esc(m.id)}">查看与处理</button>`:
     h`<button data-claim="${esc(m.id)}">领取审核任务</button><p class="muted">领取前不显示正文与照片。</p>`}</article>`).join('')||
     h('<p class="empty">当前没有待处理的稿件。</p>')}</div>`;
}
function renderAdminProducts(){
  root.innerHTML=h`<div class="top-row"><h1>商品管理</h1><button data-action="new-product" class="primary">添加商品</button></div>
    <div class="grid">${products.map(p=>h`<article class="card product-card">${productCover(p)}
    ${status(p.active?t('已上架'):t('未上架'))}<h3>${esc(p.name)}</h3><p>${esc(p.description)}</p>
    <button data-edit-product="${esc(p.id)}">编辑商品与款式</button></article>`).join('')}</div>`;
}
function syncProduct(){const form=document.getElementById('product-form');if(!form)return;productEdit.name=form.elements.name.value;productEdit.description=form.elements.description.value;productEdit.active=form.querySelector('input[name="active"]').checked;form.querySelectorAll('[data-variant-index]').forEach(section=>{const v=productEdit.variants[Number(section.dataset.variantIndex)];v.name=section.querySelector('[name="variantName"]').value;v.kind=section.querySelector('[name="kind"]').value;v.priceCents=Math.round(Number(section.querySelector('[name="price"]').value)*100);const stock=section.querySelector('[name=stockAvailable]').value;v.stockAvailable=stock===''?null:Number(stock);for(const field of ['active','textRequired','photoRequired'])v[field]=section.querySelector(h`[name="${field}"]`).checked;});}
function renderProductEditor(){
  root.innerHTML=heading('CATALOGUE',productEdit.id?t('编辑商品'):t('添加商品'),t('修改价格或上下架后，顾客必须刷新并重新确认；已生成订单保持原价格。'))+
    h`<form id="product-form" class="card" data-dirty>${productCover(productEdit,'product-cover--detail')}
      <label>商品配图<input name="coverImage" type="file" accept="image/jpeg,image/png,image/webp"></label>
      ${coverFile?h`<p class="muted">${esc(coverFile.name)}</p>`:''}
      <p class="muted">可选 JPEG、PNG 或 WebP，最多 5 MiB。配图会在商城公开展示，保存商品时一并上传。</p>
      ${productEdit.imageUrl?h('<button type="button" data-action="remove-cover">移除配图</button>'):''}
      <label>商品名称<input name="name" value="${esc(productEdit.name)}" required maxlength="120"></label>
      <label>说明<textarea name="description" maxlength="2000">${esc(productEdit.description)}</textarea></label>
      <label class="check"><input name="active" type="checkbox" ${productEdit.active?'checked':''}>上架此商品</label>
      <h2>商品款式</h2>${productEdit.variants.map((v,i)=>h`<section class="variant" data-variant-index="${i}">
        <div class="compact"><label>款式名称<input name="variantName" value="${esc(v.name)}" required maxlength="120"></label>
        <label>类型<select name="kind">${Object.entries(kinds).map(([key,label])=>h`<option value="${key}" ${v.kind===key?'selected':''}>${esc(t(label))}</option>`).join('')}</select></label></div>
        <label>价格（人民币元）<input name="price" type="number" min="0.01" max="100000" step="0.01" value="${(v.priceCents/100).toFixed(2)}" required></label>
        ${[['active',t('启用款式')],['textRequired',t('必须填写定制文字')],['photoRequired',t('必须选择授权照片')]].map(([name,label])=>h`<label class="check"><input name="${name}" type="checkbox" ${v[name]?'checked':''}>${label}</label>`).join('')}
        <label>可售库存<input name="stockAvailable" type="number" min="0" max="1000000" step="1" placeholder="留空为不限量" value="${v.stockAvailable??''}"></label><button type="button" data-remove-variant="${i}">移除此款式</button></section>`).join('')}
      <div class="actions"><button type="button" data-action="add-variant">增加款式</button><button class="primary" type="submit">保存商品</button><button type="button" data-action="back-products">返回管理</button></div>
    </form>`;
  if(productEdit.id)root.insertAdjacentHTML('beforeend',h`<section class="card"><h2>商品图库</h2>
    <div class="product-gallery">${(productEdit.gallery||[]).map(image=>h`<figure><img src="${esc(image.url)}" alt="商品配图">
      <button data-remove-gallery="${esc(image.id)}">移除配图</button></figure>`).join('')}</div>
    ${(productEdit.gallery||[]).length<5?h`<form id="gallery-form"><label>新增图库图片<input type="file" name="image" accept="image/jpeg,image/png,image/webp" required></label>
      <button type="submit">上传图片</button></form>`:''}</section>`);
}

async function back(tab){if(dirty&&!confirm(t('尚有未保存的修改，确认离开吗？')))return;dirty=false;if(location.hash==='#'+tab)await route();else location.hash=tab;}
async function openMemoirEditor(value){
  const id=loadId;
  const result=await api('/records?target=all');
  if(id!==loadId)return;
  records=result.records;edit=value;renderEditor();
}
function checkLogin(value){
  if(value.status!==401||value.code!=='login_required')return;
  const next=routeLocation();
  pendingTab=next.link(next.params,next.id);
  root.querySelectorAll('input[type="password"]').forEach(input=>{input.value='';});
  error(new Error(t('请重新登录后继续。当前编辑仍在这个页面。')));
}
root.addEventListener('change',event=>{
  const target=event.target;
  if(target.name==='coverImage')coverFile=target.files[0]||null;
  if(target.matches('[data-select-record]')){syncEditor();const r=records.find(r=>r.id===target.dataset.selectRecord);if(target.checked&&edit.chapters.length>=20){target.checked=false;error(new Error(t('最多选择 20 条记录。')));return;}edit.chapters=target.checked?[...edit.chapters,chapterInput(r)]:edit.chapters.filter(c=>c.recordId!==r.id);dirty=true;renderEditor();}
  if(target.matches('[data-chapter-photo]')){const chapter=edit.chapters[Number(target.dataset.chapterPhoto)];chapter.photoUris=target.checked?[...chapter.photoUris,target.value]:chapter.photoUris.filter(uri=>uri!==target.value);dirty=true;}
  if(target.name==='quantity'&&current?.variant)document.getElementById('purchase-total').textContent=t('合计 ')+money(current.variant.priceCents*Number(target.value));
});
root.addEventListener('click',async event=>{
  const button=event.target.closest('button');if(!button)return;clearError();button.disabled=true;
  if(button.type==='submit'&&button.form){button.disabled=false;return;}
  try{
    const action=button.dataset.action;
    if(action==='reload')await route();
    if(action==='auth-mode'){authMode=authMode==='login'?'register':'login';emailChallenge=null;renderAccount();}
    if(action==='forgot-password'){authMode='reset';emailChallenge=null;renderAccount();}
    if(action==='send-code'){
      const form=document.getElementById('account-form'),input=form.elements.email;
      if(!input.reportValidity())return;
      const address=input.value.trim().toLowerCase(),purpose=authMode==='reset'?'reset':'register';
      const result=await api('/accounts/code',{method:'POST',json:{email:address,purpose}});
      emailChallenge={id:result.challengeId,email:address,purpose};
      document.getElementById('code-status').textContent=t('若此邮箱可用于本次操作，验证码将发送至邮箱，10 分钟内有效。请检查收件箱和垃圾邮件。');
    }
    if(action==='logout'){await api('/accounts/logout',{method:'POST',json:{}});dirty=false;await refreshSession();if(routeLocation().tab==='account')await route();else location.hash='account';}
    if(button.dataset.revokeDevice){
      await api('/accounts/devices/'+button.dataset.revokeDevice,{method:'DELETE',json:{}});
      const id=loadId;await showDevices({active:()=>id===loadId});
    }
    if(action==='reload-devices'){
      const id=loadId;await showDevices({active:()=>id===loadId});
    }
    if(action==='new-memoir')await openMemoirEditor({title:'',theme:'',chapters:[]});
    if(action==='back-memoirs')await back('memoirs');
    if(action==='back-admin')await back('admin-memoirs');
    if(action==='back-products')await back('admin-products');
    if(action==='back-shop')await back('shop');
    if(action==='edit-memoir')await openMemoirEditor(structuredClone(current));
    if(button.dataset.move!==undefined){syncEditor();const from=Number(button.dataset.move),to=from+Number(button.dataset.direction);[edit.chapters[from],edit.chapters[to]]=[edit.chapters[to],edit.chapters[from]];dirty=true;renderEditor();}
    if(button.dataset.removeChapter!==undefined){syncEditor();edit.chapters.splice(Number(button.dataset.removeChapter),1);dirty=true;renderEditor();}
    if(button.dataset.refreshChapter!==undefined){syncEditor();const c=edit.chapters[Number(button.dataset.refreshChapter)],r=await api('/records/'+encodeURIComponent(c.recordId));records=records.map(item=>item.id===r.id?r:item);c.version=r.version;c.photoUris=c.photoUris.filter(uri=>r.photoUris.includes(uri));dirty=true;renderEditor();}
    if(action==='submit-memoir'){if(dirty)throw new Error(t('请先保存草稿，再确认分享范围。'));if(!document.getElementById('authorise-materials').checked)throw new Error(t('请先确认本次分享材料的范围。'));showMemoir(await api(h`/memoirs/${edit.id}/submit`,{method:'POST',json:{version:edit.version,authoriseMaterials:true}}));}
    if(button.dataset.buy)await startPurchase(current.product,button.dataset.buy,loadId);
    if(button.dataset.claim){const m=memoirs.find(m=>m.id===button.dataset.claim);showMemoir(await api(h`/admin/memoirs/${m.id}/claim`,{method:'POST',json:versionBody(m)}),true);}
    if(button.dataset.adminMemoir)showMemoir(await api('/admin/memoirs/'+button.dataset.adminMemoir),true);
    if(action==='remove-cover'){if(dirty)throw new Error(t('请先保存当前商品修改，再移除配图。'));productEdit=await api('/admin/products/'+productEdit.id+'/image',{method:'DELETE',json:{version:productEdit.version}});renderProductEditor();}
    if(action==='new-product'){coverFile=null;productEdit={name:'',description:'',active:false,variants:[{name:t('标准款'),kind:'medal',priceCents:3900,active:true,textRequired:true,photoRequired:false}]};renderProductEditor();}
    if(button.dataset.editProduct){coverFile=null;productEdit=structuredClone(products.find(p=>p.id===button.dataset.editProduct));renderProductEditor();}
    if(action==='add-variant'){syncProduct();productEdit.variants.push({name:'',kind:'gift',priceCents:3900,active:true,textRequired:true,photoRequired:false});dirty=true;renderProductEditor();}
    if(button.dataset.removeVariant!==undefined){syncProduct();productEdit.variants.splice(Number(button.dataset.removeVariant),1);dirty=true;renderProductEditor();}
    if(button.dataset.removeGallery){
      if(dirty)throw new Error(t('请先保存当前商品修改。'));
      productEdit=await api('/admin/products/'+productEdit.id+'/gallery/'+button.dataset.removeGallery,{method:'DELETE',json:{version:productEdit.version}});
      renderProductEditor();
    }
    if(action==='refresh-price')await refreshPurchasePrice();
  }catch(value){error(value);checkLogin(value);}finally{button.disabled=false;}
});
root.addEventListener('submit',async event=>{
  event.preventDefault();if(submitting)return;
  submitting=true;clearError();const form=event.target,buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
  try{
    if(form.id==='account-form'){
      const fields=new FormData(form),email=fields.get('email').trim().toLowerCase(),verifying=sharedIdentity&&authMode!=='login';
      if(verifying&&(!emailChallenge||emailChallenge.email!==email||emailChallenge.purpose!==(authMode==='reset'?'reset':'register')))throw new Error(t('请先为当前邮箱获取验证码。'));
      await api('/accounts/'+(authMode==='reset'?'reset-password':authMode),{method:'POST',json:{email,password:fields.get('password'),name:fields.get('name'),claimCurrentSpace:fields.get('claim')==='on',challengeId:verifying?emailChallenge.id:undefined,code:verifying?fields.get('code'):undefined}});
      dirty=false;emailChallenge=null;
      if(authMode==='reset'){authMode='login';await refreshSession();renderAccount();errorBox.textContent=t('密码已重置，请使用新密码登录。');errorBox.hidden=false;}
      else{await refreshSession();location.hash=pendingTab||'memoirs';pendingTab=null;}
    }else if(form.id==='memoir-form'){
      syncEditor();const saved=await api('/memoirs'+(edit.id?'/'+edit.id:''),{method:edit.id?'PUT':'POST',json:edit});dirty=false;edit=saved;renderEditor();
    }else if(form.id==='review-form'){
      showMemoir(await api(h`/admin/memoirs/${current.id}/review`,{method:'POST',json:{...versionBody(current),reason:form.elements.reason.value,decision:event.submitter.value}}),true);
    }else if(form.id==='generate-form'){
      const id=current.id;showMemoir(await api(h`/admin/memoirs/${id}/generate`,{method:'POST',json:{...versionBody(current),background:true,chapterOrder:form.elements.chapterOrder.value.split(',').map(s=>Number(s.trim())-1),fontSize:Number(form.elements.fontSize.value)}}),true);
    }else if(form.id==='product-form'){
      const file=coverFile||form.elements.coverImage.files[0];
      if(file&&file.size>5*1024*1024)throw new Error(t('商品图片不能超过 5 MiB。'));
      syncProduct();productEdit=await api('/admin/products'+(productEdit.id?'/'+productEdit.id:''),{method:productEdit.id?'PUT':'POST',json:productEdit});
      dirty=false;
      if(file){
        const upload=new FormData();upload.set('version',String(productEdit.version));upload.set('image',file);
        try{productEdit=await api('/admin/products/'+productEdit.id+'/image',{method:'POST',body:upload,timeout:60000});}
        catch(value){renderProductEditor();throw new Error(t('商品已保存，封面上传未完成。')+' '+value.message);}
      }
      coverFile=null;await route();
    }else if(form.id==='gallery-form'){
      if(dirty)throw new Error(t('请先保存当前商品修改。'));
      const data=new FormData(form);data.set('version',String(productEdit.version));
      productEdit=await api('/admin/products/'+productEdit.id+'/gallery',{method:'POST',body:data,timeout:60000});
      renderProductEditor();
    }else if(form.id==='catalogue-filter'||form.matches('[data-order-filters]')){
      const query=new URLSearchParams([...new FormData(form)].filter(([,value])=>value));
      const hash='#'+routeLocation().tab+(query.size?'?'+query:'');
      if(hash===location.hash)await route();else location.hash=hash;
    }else if(form.matches('[data-order-action]')){
      await submitOrderAction(form,routeLocation());dirty=false;await route();
    }else if(form.matches('[data-trade-action]')){
      if(await submitTradeAction(form,routeLocation())){dirty=false;await route();}
    }else if(form.id==='purchase-form'){
      const fields=new FormData(form),file=fields.get('photo');
      if(!orderRequest){
        let photoUri=null;
        if(file?.size){
          if(file.size>10*1024*1024)throw new Error(t('定制照片最多 10 MiB。'));
          if(fields.get('authorisePhoto')!=='on')throw new Error(t('请选择照片授权确认。'));
          if(!purchasePhoto)purchasePhoto={file,key:crypto.randomUUID(),uri:null};
          if(!purchasePhoto.uri){
            const upload=new FormData();upload.set('requestKey',purchasePhoto.key);upload.append('photos',purchasePhoto.file);
            purchasePhoto.uri=(await api('/photos/batch',{method:'POST',body:upload,timeout:60000})).photos[0].uri;
          }
          photoUri=purchasePhoto.uri;
        }
        orderRequest={requestKey:crypto.randomUUID(),items:[{variantId:current.variant.id,variantVersion:current.variant.version,productVersion:current.product.version,quantity:Number(fields.get('quantity')),customText:fields.get('customText'),photoUri,authorisePhoto:fields.get('authorisePhoto')==='on',revisionId:fields.get('revisionId')||null}]};
      }
      let order;
      try{
        if(orderRequest.uncertain){
          try{order=await api('/shop/orders/by-request/'+encodeURIComponent(orderRequest.requestKey));}
          catch(value){if(value.status!==404)throw value;}
        }
        if(!order)order=await api('/shop/orders',{method:'POST',json:{requestKey:orderRequest.requestKey,items:orderRequest.items}});
      }catch(value){
        if(!value.status||value.status>=500)orderRequest.uncertain=true;
        else orderRequest.uncertain=false;
        lockPurchase(form,Boolean(orderRequest.uncertain));
        if(value.code==='price_changed'||value.code==='variantId')form.querySelector('[data-action="refresh-price"]').hidden=false;
        if(orderRequest.uncertain)throw new Error(t('订单结果待确认。请先查询原订单。')+' '+value.message);
        throw value;
      }
      dirty=false;orderRequest=null;location.hash='orders/'+encodeURIComponent(order.id);
    }
  }catch(value){error(value);checkLogin(value);}finally{submitting=false;buttons.forEach(b=>b.disabled=false);}
});
// 网络失败后保留同一请求编号重试；用户修改订单内容时重新确认。
root.addEventListener('input',event=>{
  if(!event.target.closest('#purchase-form'))return;
  if(event.target.name==='photo')purchasePhoto=null;
  if(!orderRequest?.uncertain)orderRequest=null;
  updatePurchasePreview();
});
root.addEventListener('error',event=>{
  if(!(event.target instanceof HTMLImageElement))return;
  if(!event.target.closest('.product-cover,.product-gallery'))return;
  const placeholder=document.createElement('span');placeholder.className='product-cover--empty';
  placeholder.textContent=t('商品图片暂不可用');event.target.replaceWith(placeholder);
},true);
window.addEventListener('hashchange',()=>{
  if((submitting||orderRequest?.uncertain||dirty)&&location.hash!==renderedHash){
    history.replaceState(null,'',renderedHash||location.pathname+location.search);
    return;
  }
  dirty=false;route();
});
try{await refreshSession();await route();}catch(value){error(value);root.innerHTML=h('<p class="empty">暂时无法读取账户，请刷新后重试。</p>');}
