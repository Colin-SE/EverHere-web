import {api,getSession} from './api.js';
import {locale,t,h} from './i18n.js';

// 所有私人内容仅放在当前页面内存；文本一律转义，不作为 HTML 执行。
const root=document.getElementById('workspace-content'), errorBox=document.getElementById('workspace-error');
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=cents=>new Intl.NumberFormat(locale(),{style:'currency',currency:'CNY'}).format(cents/100);
const labels={draft:t('草稿'),submitted:t('待审核'),returned:t('需修改'),approved:t('待制作'),ready:t('已完成'),unpaid:t('待支付')};
let member=null,records=[],memoirs=[],products=[],current=null,edit=null,productEdit=null,dirty=false,loadId=0;
let authMode='login',orderRequest=null;
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
document.addEventListener('click',event=>{if(event.target.closest('a')&&dirty){if(!confirm(t('当前修改尚未保存，确认离开吗？')))event.preventDefault();else dirty=false;}},true);
document.querySelector('nav').addEventListener('click',event=>{const link=event.target.closest('[data-tab]');if(link&&!event.defaultPrevented&&link.hash===location.hash){event.preventDefault();route();}});

async function refreshSession(){const session=await getSession();member=session.member;document.getElementById('admin-link').hidden=member?.role!=='admin';document.getElementById('account-link').textContent=member?member.name:t('登录 / 注册');}
async function route(){
  const id=++loadId;clearError();current=null;edit=null;productEdit=null;
  document.querySelectorAll('[data-tab]').forEach(link=>link.toggleAttribute('aria-current',location.hash.slice(1)===link.dataset.tab));
  const tab=location.hash.slice(1)||'memoirs';
  root.innerHTML=h('<p class="loading">正在读取…</p>');
  try{
    if(tab==='account'){renderAccount();return;}
    if(tab!=='shop'&&!requireAccount())return;
    if(tab==='memoirs'){
      const [m,r]=await Promise.all([api('/memoirs'),api('/records?target=all')]);if(id!==loadId)return;
      memoirs=m.memoirs;records=r.records;renderMemoirs();
    }else if(tab==='shop'){
      const [p,m]=await Promise.all([api('/shop/products'),member?api('/memoirs'):Promise.resolve({memoirs:[]})]);if(id!==loadId)return;products=p.products;memoirs=m.memoirs;renderShop();
    }else if(tab==='orders'){
      const result=await api('/shop/orders');if(id!==loadId)return;renderOrders(result.orders);
    }else if(tab==='admin'){
      if(member.role!=='admin')throw new Error(t('此页面需要管理员权限。'));
      const [m,p]=await Promise.all([api('/admin/memoirs'),api('/admin/products')]);if(id!==loadId)return;memoirs=m.memoirs;products=p.products;renderAdmin();
    }else{location.hash='memoirs';}
  }catch(value){if(id!==loadId)return;root.innerHTML=h('<div class="empty">读取未完成。<p><button data-action="reload">重新读取</button></p></div>');error(value);}
}

function renderAccount(){
  if(member){root.innerHTML=heading('YOUR ACCOUNT',t('你好，')+esc(member.name),t('此账户用于本网站的回忆录和订单，云账户仍独立管理。'))+h`<section class="card"><p>${esc(member.email)}</p>${status(member.role==='admin'?t('制作与商城管理员'):t('普通用户'))}<div class="actions"><a class="button" href="/">进入人生相册</a><a class="button primary" href="#memoirs">我的回忆录</a><button data-action="logout">退出账户</button></div></section>`;return;}
  const registering=authMode==='register';
  root.innerHTML=h`<section class="auth">${heading('KEEP YOUR STORIES',registering?t('建立你的私人账户'):t('欢迎回来'),registering?t('可选择将当前浏览器的访客档案归入新账户。资料原 ID 和照片保持不变。'):t('登录已有账户，不会自动转移当前访客档案。'))}<form id="account-form" class="card">${registering?h('<label>显示姓名<input name="name" required maxlength="80" autocomplete="name"></label>'):''}<label>邮箱<input name="email" type="email" required maxlength="254" autocomplete="username"></label><label>密码（10—128 个字符）<input name="password" type="password" required minlength="10" maxlength="128" autocomplete="${registering?'new-password':'current-password'}"></label>${registering?h('<label class="check"><input name="claim" type="checkbox"><span>我确认将当前访客档案归入此新账户；之后须登录此账户访问。</span></label>'):''}<button class="primary" type="submit">${registering?t('注册并进入'):t('登录')}</button><div class="actions"><button type="button" data-action="auth-mode">${registering?t('已有账户，去登录'):t('没有账户，去注册')}</button><a href="/">返回访客相册</a></div><p class="muted">管理员由服务器维护者建立；公开注册仅创建普通用户。</p></form></section>`;
}
function renderMemoirs(){root.innerHTML=heading('MEMOIRS',t('把零散的片段，整理成一个故事'),t('挑选自己的记录，决定章节与分享范围，再交给制作管理员审核。'))+h('<div class="actions"><button class="primary" data-action="new-memoir">整理新回忆录</button><a class="button" href="/">回到人生相册</a></div>')+ (memoirs.length?h`<div class="grid">${memoirs.map(m=>h`<article class="card">${status(m.state)}<h2>${esc(m.title)}</h2><p>${esc(m.theme)||t('尚未填写主题')}</p><p class="muted">提交版本 ${m.revisionNumber} ${m.reason?'· '+esc(m.reason):''}</p><button data-memoir="${esc(m.id)}">${['draft','returned'].includes(m.state)?t('继续整理'):t('查看进度与成品')}</button></article>`).join('')}</div>`:h('<div class="empty">第一本回忆录，从一段想留下的经历开始。</div>'));}
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
  const back=staff?'admin':'memoirs';
  root.innerHTML=heading('MEMOIR STUDIO',esc(m.title),staff?t('只显示此次申请授权的材料；不会开放用户的私人相册。'):t('每次提交保留独立版本和审核结果。'))+h`<div class="actions"><button data-action="${staff?'back-admin':'back-memoirs'}">返回${staff?t('管理队列'):t('列表')}</button>${status(m.state)}<span class="muted">提交版本 ${m.revisionNumber}</span></div>${m.reason?h`<p class="notice">审核意见：${esc(m.reason)}</p>`:''}${m.renderError?h`<p class="error">${esc(m.renderError)}</p>`:''}${!staff&&['draft','returned'].includes(m.state)?h('<div class="actions"><button class="primary" data-action="edit-memoir">修改草稿 / 重新提交</button></div>'):''}${m.state==='ready'?h`<section class="card"><h2>回忆录已制作完成</h2><p>可查看带标记的预览版。购买高清电子版或纸质版时，可在商城选择此成品。</p><div class="actions"><a class="button primary" href="${esc(m.previewUrl)}" target="_blank" rel="noopener">查看 PDF 预览</a>${!staff?h('<a class="button" href="#shop">选择成品形式</a>'):''}</div><p class="muted">本阶段开放预览与待支付订单；高清交付和支付将在后续阶段提供。</p></section>`:''}${staff&&m.state==='submitted'?h('<form id="review-form" class="card"><h2>审核材料</h2><p>检查章节标题、正文完整性与图片可读性。不能在这里改写原文；需要改动时填写原因并退回。</p><label>审核意见（退回时必填）<textarea name="reason" maxlength="2000"></textarea></label><div class="actions"><button name="decision" value="return" type="submit">退回修改</button><button class="primary" name="decision" value="approve" type="submit">审核通过</button></div></form>'):''}${staff&&m.state==='approved'?h`<form id="generate-form" class="card"><h2>制作固定版式回忆录</h2><p>可调整排版顺序和字号，稿件文字保持用户确认的版本。</p><label>章节顺序（用逗号分隔，从 1 开始）<input name="chapterOrder" value="${esc((m.layout?.chapterOrder||m.revision.snapshot.chapters.map((_,i)=>i)).map(i=>i+1).join(','))}" required></label><label>正文字号<input name="fontSize" type="number" min="10" max="16" value="${m.layout?.fontSize||12}" required></label><button class="primary" type="submit">${m.renderError?t('重试生成'):t('生成回忆录')}</button></form>`:''}${snapshotHTML(m)}${m.history?.length?h`<details class="card"><summary>查看提交与审核历史</summary>${m.history.map(r=>h`<p>版本 ${r.number} · ${esc(labels[r.state])}${r.reason?' · '+esc(r.reason):''}</p>`).join('')}</details>`:''}`;
}
function renderShop(){root.innerHTML=heading('KEEPSAKES',t('留住一段经历，也纪念一个此刻'),t('纪念奖牌与礼品可独立定制，不需要先创建回忆录。回忆录成品仅对所属用户提供。'))+h('<p class="notice">当前可确认待支付订单。支付、收货信息和交付将在下一阶段开放。</p>')+ (products.length?h`<div class="grid">${products.map(p=>h`<article class="card"><span class="badge">私人定制</span><h2>${esc(p.name)}</h2><p>${esc(p.description)}</p>${p.variants.map(v=>h`<div class="order-item"><h3>${esc(v.name)}</h3><p class="price">${money(v.priceCents)}</p><button data-buy="${esc(v.id)}">选择与定制</button></div>`).join('')||h('<p class="muted">暂无可用款式</p>')}</article>`).join('')}</div>`:h('<div class="empty">商品正在准备中，管理员上架后会在这里显示。</div>'));}
function renderPurchase(variantId){
  if(!requireAccount())return;
  const product=products.find(p=>p.variants.some(v=>v.id===variantId)),variant=product.variants.find(v=>v.id===variantId);
  current={product,variant};orderRequest=null;
  root.innerHTML=heading('MAKE IT YOURS',esc(product.name)+' · '+esc(variant.name),t('订单按当前确认的价格、款式和定制内容保存。'))+h`<form id="purchase-form" class="card" data-dirty><p class="price">${money(variant.priceCents)} / 件</p>${variant.kind.startsWith('memoir_')?h`<label>选择自己的已完成回忆录<select name="revisionId" required><option value="">请选择</option>${memoirs.filter(m=>m.state==='ready').map(m=>h`<option value="${esc(m.revisionId)}">${esc(m.title)} · 版本 ${m.revisionNumber}</option>`).join('')}</select></label>`:''}<label>定制文字${variant.textRequired?t('（必填）'):t('（可选）')}<textarea name="customText" maxlength="300" ${variant.textRequired?'required':''}></textarea></label><label>定制照片${variant.photoRequired?t('（必选）'):t('（可选）')}<input name="photo" type="file" accept="image/png,image/jpeg,image/webp" ${variant.photoRequired?'required':''}></label><label class="check"><input name="authorisePhoto" type="checkbox"><span>如选择照片，我确认授权仅将该照片用于本订单。</span></label><label>数量<input type="number" name="quantity" min="1" max="10" value="1" required></label><p id="purchase-total">合计 ${money(variant.priceCents)}</p><div class="actions"><button class="primary" type="submit">确认并创建待支付订单</button><button type="button" data-action="back-shop">返回商城</button></div><p class="muted">此操作不会扣款、印刷或发货。收货地址在后续结算时填写。</p></form>`;
}
function renderOrders(orders){root.innerHTML=heading('YOUR ORDERS',t('你的定制清单'),t('价格、款式和定制文字已保存为订单快照，之后调整商品不会改动此处。'))+h('<p class="notice">当前阶段仅保存待支付订单，尚未开放付款、取消及交付。</p>')+ (orders.length?orders.map(o=>h`<article class="card">${status(o.state)}<p class="muted">订单 ${esc(o.id)}</p>${o.items.map(i=>h`<div class="order-item"><h3>${esc(i.snapshot.productName)} · ${esc(i.snapshot.variantName)}</h3><p>${esc(i.snapshot.customText)}</p><p>${money(i.unitPriceCents)} × ${i.quantity}${i.snapshot.photoAuthorised?t(' · 已保存授权照片'):''}</p>${i.snapshot.revisionId?h('<p class="muted">绑定已完成的私人回忆录版本</p>'):''}</div>`).join('')}<p class="price">合计 ${money(o.totalCents)}</p></article>`).join(''):h('<div class="empty">还没有订单。<p><a href="#shop">去看看纪念品</a></p></div>'));}
function renderAdmin(){root.innerHTML=heading('PRODUCTION & SHOP',t('把用户交来的回忆，认真完成'),t('先领取审核任务，再读取用户授权的材料。商品管理与回忆录制作并行。'))+h('<div class="section-links"><a class="button" href="#admin-queue">审核与制作</a><a class="button" href="#admin-catalogue">商品管理</a></div>')+h`<section id="admin-queue"><h2>审核与制作队列</h2>${memoirs.length?h`<div class="grid">${memoirs.map(m=>h`<article class="card">${status(m.state)}<h3>${esc(m.title||t('待领取的私人稿件'))}</h3><p class="muted">提交版本 ${m.revisionNumber}</p>${m.reviewerId?h`<button data-admin-memoir="${esc(m.id)}">查看与处理</button>`:h`<button data-claim="${esc(m.id)}">领取审核任务</button><p class="muted">领取前不显示正文与照片。</p>`}</article>`).join('')}</div>`:h('<p class="empty">当前没有待处理的稿件。</p>')}</section><section id="admin-catalogue"><div class="top-row"><h2>商品管理</h2><button data-action="new-product" class="primary">添加商品</button></div><p class="muted">支持独立奖牌、礼品及电子 / 纸质回忆录款式。金额以人民币分保存。</p><div class="grid">${products.map(p=>h`<article class="card">${status(p.active?t('已上架'):t('未上架'))}<h3>${esc(p.name)}</h3><p>${esc(p.description)}</p><button data-edit-product="${esc(p.id)}">编辑商品与款式</button></article>`).join('')}</div></section>`;}
function syncProduct(){const form=document.getElementById('product-form');if(!form)return;productEdit.name=form.elements.name.value;productEdit.description=form.elements.description.value;productEdit.active=form.querySelector('input[name="active"]').checked;form.querySelectorAll('[data-variant-index]').forEach(section=>{const v=productEdit.variants[Number(section.dataset.variantIndex)];v.name=section.querySelector('[name="variantName"]').value;v.kind=section.querySelector('[name="kind"]').value;v.priceCents=Math.round(Number(section.querySelector('[name="price"]').value)*100);for(const field of ['active','textRequired','photoRequired'])v[field]=section.querySelector(h`[name="${field}"]`).checked;});}
function renderProductEditor(){root.innerHTML=heading('CATALOGUE',productEdit.id?t('编辑商品'):t('添加商品'),t('修改价格或上下架后，顾客必须刷新并重新确认；已生成订单保持原价格。'))+h`<form id="product-form" class="card" data-dirty><label>商品名称<input name="name" value="${esc(productEdit.name)}" required maxlength="120"></label><label>说明<textarea name="description" maxlength="2000">${esc(productEdit.description)}</textarea></label><label class="check"><input name="active" type="checkbox" ${productEdit.active?'checked':''}>上架此商品</label><h2>商品款式</h2>${productEdit.variants.map((v,i)=>h`<section class="variant" data-variant-index="${i}"><div class="compact"><label>款式名称<input name="variantName" value="${esc(v.name)}" required maxlength="120"></label><label>类型<select name="kind">${[['medal',t('纪念奖牌')],['gift',t('文创礼品')],['memoir_digital',t('回忆录电子版')],['memoir_paper',t('回忆录纸质版')]].map(([key,label])=>h`<option value="${key}" ${v.kind===key?'selected':''}>${label}</option>`).join('')}</select></label></div><label>价格（人民币元）<input name="price" type="number" min="0.01" max="100000" step="0.01" value="${(v.priceCents/100).toFixed(2)}" required></label>${[['active',t('启用款式')],['textRequired',t('必须填写定制文字')],['photoRequired',t('必须选择授权照片')]].map(([name,label])=>h`<label class="check"><input name="${name}" type="checkbox" ${v[name]?'checked':''}>${label}</label>`).join('')}<button type="button" data-remove-variant="${i}">移除此款式</button></section>`).join('')}<div class="actions"><button type="button" data-action="add-variant">增加款式</button><button class="primary" type="submit">保存商品</button><button type="button" data-action="back-admin">返回管理</button></div></form>`;}

async function back(tab){if(dirty&&!confirm(t('尚有未保存的修改，确认离开吗？')))return;dirty=false;if(location.hash==='#'+tab)await route();else location.hash=tab;}
root.addEventListener('change',event=>{
  const target=event.target;
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
    if(action==='auth-mode'){authMode=authMode==='login'?'register':'login';renderAccount();}
    if(action==='logout'){await api('/accounts/logout',{method:'POST',json:{}});dirty=false;await refreshSession();if(location.hash==='#account')await route();else location.hash='account';}
    if(action==='new-memoir'){edit={title:'',theme:'',chapters:[]};renderEditor();}
    if(action==='back-memoirs')await back('memoirs');
    if(action==='back-admin')await back('admin');
    if(action==='back-shop')await back('shop');
    if(button.dataset.memoir)renderDetail(await api('/memoirs/'+button.dataset.memoir));
    if(action==='edit-memoir'){edit=structuredClone(current);renderEditor();}
    if(button.dataset.move!==undefined){syncEditor();const from=Number(button.dataset.move),to=from+Number(button.dataset.direction);[edit.chapters[from],edit.chapters[to]]=[edit.chapters[to],edit.chapters[from]];dirty=true;renderEditor();}
    if(button.dataset.removeChapter!==undefined){syncEditor();edit.chapters.splice(Number(button.dataset.removeChapter),1);dirty=true;renderEditor();}
    if(button.dataset.refreshChapter!==undefined){syncEditor();const c=edit.chapters[Number(button.dataset.refreshChapter)],r=await api('/records/'+encodeURIComponent(c.recordId));records=records.map(item=>item.id===r.id?r:item);c.version=r.version;c.photoUris=c.photoUris.filter(uri=>r.photoUris.includes(uri));dirty=true;renderEditor();}
    if(action==='submit-memoir'){if(dirty)throw new Error(t('请先保存草稿，再确认分享范围。'));if(!document.getElementById('authorise-materials').checked)throw new Error(t('请先确认本次分享材料的范围。'));renderDetail(await api(h`/memoirs/${edit.id}/submit`,{method:'POST',json:{version:edit.version,authoriseMaterials:true}}));}
    if(button.dataset.buy)renderPurchase(button.dataset.buy);
    if(button.dataset.claim){const m=memoirs.find(m=>m.id===button.dataset.claim);renderDetail(await api(h`/admin/memoirs/${m.id}/claim`,{method:'POST',json:versionBody(m)}),true);}
    if(button.dataset.adminMemoir)renderDetail(await api('/admin/memoirs/'+button.dataset.adminMemoir),true);
    if(action==='new-product'){productEdit={name:'',description:'',active:false,variants:[{name:t('标准款'),kind:'medal',priceCents:3900,active:true,textRequired:true,photoRequired:false}]};renderProductEditor();}
    if(button.dataset.editProduct){productEdit=structuredClone(products.find(p=>p.id===button.dataset.editProduct));renderProductEditor();}
    if(action==='add-variant'){syncProduct();productEdit.variants.push({name:'',kind:'gift',priceCents:3900,active:true,textRequired:true,photoRequired:false});dirty=true;renderProductEditor();}
    if(button.dataset.removeVariant!==undefined){syncProduct();productEdit.variants.splice(Number(button.dataset.removeVariant),1);dirty=true;renderProductEditor();}
  }catch(value){error(value);}finally{button.disabled=false;}
});
root.addEventListener('submit',async event=>{
  event.preventDefault();clearError();const form=event.target,buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
  try{
    if(form.id==='account-form'){
      const fields=new FormData(form);await api('/accounts/'+authMode,{method:'POST',json:{email:fields.get('email'),password:fields.get('password'),name:fields.get('name'),claimCurrentSpace:fields.get('claim')==='on'}});dirty=false;await refreshSession();location.hash='memoirs';
    }else if(form.id==='memoir-form'){
      syncEditor();const saved=await api('/memoirs'+(edit.id?'/'+edit.id:''),{method:edit.id?'PUT':'POST',json:edit});dirty=false;edit=saved;renderEditor();
    }else if(form.id==='review-form'){
      renderDetail(await api(h`/admin/memoirs/${current.id}/review`,{method:'POST',json:{...versionBody(current),reason:form.elements.reason.value,decision:event.submitter.value}}),true);
    }else if(form.id==='generate-form'){
      const id=current.id;try{renderDetail(await api(h`/admin/memoirs/${id}/generate`,{method:'POST',json:{...versionBody(current),chapterOrder:form.elements.chapterOrder.value.split(',').map(s=>Number(s.trim())-1),fontSize:Number(form.elements.fontSize.value)}}),true);}catch(value){if(value.code==='render_failed')renderDetail(await api('/admin/memoirs/'+id),true);throw value;}
    }else if(form.id==='product-form'){
      syncProduct();await api('/admin/products'+(productEdit.id?'/'+productEdit.id:''),{method:productEdit.id?'PUT':'POST',json:productEdit});dirty=false;await route();
    }else if(form.id==='purchase-form'){
      const fields=new FormData(form),file=fields.get('photo');
      if(!orderRequest){
        let photoUri=null;if(file?.size){if(file.size>10*1024*1024)throw new Error(t('定制照片最多 10 MiB。'));if(fields.get('authorisePhoto')!=='on')throw new Error(t('请选择照片授权确认。'));const upload=new FormData();upload.set('photo',file);photoUri=(await api('/photos',{method:'POST',body:upload})).uri;}
        orderRequest={requestKey:crypto.randomUUID(),items:[{variantId:current.variant.id,variantVersion:current.variant.version,productVersion:current.product.version,quantity:Number(fields.get('quantity')),customText:fields.get('customText'),photoUri,authorisePhoto:fields.get('authorisePhoto')==='on',revisionId:fields.get('revisionId')||null}]};
      }
      const order=await api('/shop/orders',{method:'POST',json:orderRequest});dirty=false;orderRequest=null;renderOrders([order]);
    }
  }catch(value){error(value);}finally{buttons.forEach(b=>b.disabled=false);}
});
// 网络失败后保留同一请求编号重试；用户修改订单内容时重新确认。
root.addEventListener('input',event=>{if(event.target.closest('#purchase-form'))orderRequest=null;});
window.addEventListener('hashchange',()=>{if(['#admin-queue','#admin-catalogue'].includes(location.hash))return;dirty=false;route();});
try{await refreshSession();await route();}catch(value){error(value);root.innerHTML=h('<p class="empty">暂时无法读取账户，请刷新后重试。</p>');}
