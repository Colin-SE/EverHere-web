import {api} from './api.js';
import {h,t,locale} from './i18n.js';
import {esc} from './ui.js';

const money=value=>new Intl.NumberFormat(locale(),{style:'currency',currency:'CNY'}).format(value/100);
const date=value=>new Date(value).toLocaleString(locale(),{dateStyle:'medium',timeStyle:'short'});
const states={pending:'待处理',processing:'处理中',needs_info:'待补充信息',completed:'处理完成',cancelled:'处理已终止',
              unresolved:'未解决',resolved:'已解决'};
const actions={claim:'领取订单',request_info:'请买家补充',reply:'提交补充信息',complete:'标记处理完成',
               cancel:'终止处理',reopen:'重新开启',note:'添加内部备注',message:'发送买家可见消息'};
const kinds={gift:'文创礼品',medal:'纪念奖牌',memoir_digital:'回忆录电子版',memoir_paper:'回忆录纸质版'};
const actionLabel=value=>t(actions[value]);
const stateLabel=value=>t(states[value]);
const status=order=>h`<span class="badge">${esc(stateLabel(order.processingState))}</span>
  <span class="badge">${esc(t('待支付'))}</span>`;
const filters=(values,selected)=>Object.entries(values).map(([code,label])=>
  `<option value="${esc(code)}" ${code===selected?'selected':''}>${esc(t(label))}</option>`).join('');

export async function showOrders(root, route) {
  const staff=route.tab==='admin-orders', prefix=staff?'/admin/orders':'/shop/orders';
  const value=await api(prefix+(route.id?'/'+encodeURIComponent(route.id):'?'+new URLSearchParams(route.params)));
  if(!route.active())return;
  root.innerHTML=route.id?detail(value,staff,route):listing(value,staff,route);
}

function listing(data, staff, route) {
  const {orders,page,pageSize,total}=data, params=route.params;
  const href=(changes={})=>route.link({...params,...changes});
  return h`<h1>${staff?t('订单处理队列'):t('我的订单')}</h1>
    <p class="notice">支付尚未开放。处理进度仅记录订单沟通和资料确认。</p>
    <form data-order-filters class="card order-filters">
      ${staff?h`<label>订单号、姓名或邮箱<input name="q" maxlength="120" value="${esc(params.q)}"></label>
        <label>商品类型<select name="kind"><option value="">不限</option>${filters(kinds,params.kind)}</select></label>
        <label>起始日期<input type="date" name="from" value="${esc(params.from)}"></label>
        <label>截止日期<input type="date" name="to" value="${esc(params.to)}"></label>
        <label class="check"><input type="checkbox" name="assigned" value="me" ${params.assigned==='me'?'checked':''}>只看我领取的</label>
        ${params.buyer?h`<input type="hidden" name="buyer" value="${esc(params.buyer)}"><a href="${esc(href({buyer:'',page:1}))}">清除买家筛选</a>`:''}`:''}
      <label>处理状态<select name="status"><option value="">不限</option>${filters(states,params.status)}</select></label>
      <button type="submit">应用筛选</button>
    </form>
    <div class="order-list">${orders.map(order=>h`<article class="card order-row">
      <div><h2><a href="${esc(route.link(params,order.id))}">${esc(order.items.map(item=>item.snapshot.productName).join(' · '))}</a></h2>
        <p class="muted">${esc(order.id)} · ${esc(date(order.createdAt))}</p>
        ${staff?h`<p><a href="${esc(href({buyer:order.buyer.id,page:1}))}">${esc(order.buyer.name)} · ${esc(order.buyer.email)}</a> · ${esc(order.assignee||t('待领取'))}</p>`:''}</div>
      <div>${status(order)}<strong>${money(order.totalCents)}</strong></div>
    </article>`).join('')||h('<p class="empty">没有符合条件的订单。</p>')}</div>
    <nav class="actions" aria-label="分页">
      ${page>1?h`<a class="button" href="${esc(href({page:page-1}))}">上一页</a>`:''}
      <span>${esc(t('第 {page} 页 · 共 {total} 条',{page,total}))}</span>
      ${page*pageSize<total?h`<a class="button" href="${esc(href({page:page+1}))}">下一页</a>`:''}
    </nav>`;
}

function detail(order, staff, route) {
  const next=[];
  if(staff&&order.canClaim)next.push('claim');
  if(staff&&order.canHandle){
    if(order.processingState==='processing')next.push('request_info','complete','cancel');
    if(order.processingState==='needs_info')next.push('cancel');
    if(['completed','cancelled'].includes(order.processingState))next.push('reopen');
    next.push('note','message');
  }
  if(!staff&&order.processingState==='needs_info')next.push('reply');
  return h`<div class="actions"><a class="button" href="${esc(route.link(route.params))}">返回订单列表</a>${status(order)}</div>
    <h1>订单详情</h1><p class="muted">${esc(order.id)} · ${esc(date(order.createdAt))}</p>
    ${staff?h`<section class="card"><h2>下单用户</h2><p>${esc(order.buyer.name)} · ${esc(order.buyer.email)}</p>
      <a href="${esc(route.link({buyer:order.buyer.id}))}">查看该用户的订单</a>
      <p>${esc(t('负责人：{name}',{name:order.assignee||t('待领取')}))}</p></section>`:''}
    <section class="card"><h2>购买内容</h2>
      ${order.items.map(item=>h`<div class="order-item"><h3>${esc(item.snapshot.productName)} · ${esc(item.snapshot.variantName)}</h3>
        <p>${esc(item.snapshot.customText||'')}</p><p>${money(item.unitPriceCents)} × ${item.quantity}</p>
        ${item.snapshot.photoAuthorised?h('<p>已保存授权照片</p>'):''}
        ${item.photoUrl?h`<a href="${esc(item.photoUrl)}" target="_blank" rel="noopener">查看订单授权照片</a>`:''}</div>`).join('')}
      <p class="price">${esc(t('合计 '))}${money(order.totalCents)}</p></section>
    <section class="card"><h2>处理进度</h2><ol class="progress-list"><li><strong>已提交订单</strong> <time>${esc(date(order.createdAt))}</time></li>
      ${(order.events||[]).map(event=>h`<li><strong>${esc(actionLabel(event.action))}</strong> <time>${esc(date(event.createdAt))}</time>
        ${event.visible===false?h('<span class="badge">仅管理端可见</span>'):''}
        <p class="prose">${esc(event.message)}</p></li>`).join('')}</ol></section>
    ${next.length?h`<form data-order-action data-dirty class="card" data-version="${order.version}"><h2>处理订单</h2>
      <label>操作<select name="action">${filters(Object.fromEntries(next.map(key=>[key,actions[key]])),'')}</select></label>
      <label>说明<textarea name="message" maxlength="2000"></textarea></label>
      <p class="muted">内部备注仅在管理端显示。</p>
      <button type="submit" class="primary">确认操作</button></form>`:''}`;
}

export async function submitOrderAction(form, route) {
  const fields=new FormData(form), staff=route.tab==='admin-orders';
  const path=(staff?'/admin/orders/':'/shop/orders/')+encodeURIComponent(route.id)+(staff?'/process':'/reply');
  await api(path,{method:'POST',json:{action:fields.get('action'),message:fields.get('message'),version:Number(form.dataset.version)}});
}
