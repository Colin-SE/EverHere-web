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
const paymentLabels={unpaid:'待支付',confirming:'等待支付宝确认',closing:'关单核对中',closed:'支付已关闭',
  paid:'已支付',review:'付款待人工核对',refunding:'退款确认中',refunded:'已退款'};
const fulfillmentLabels={pending:'待制作',started:'制作中',shipped:'已发货',received:'已签收',delivered:'可以下载'};
const refundLabels={requested:'退款待审核',sending:'退款提交中',uncertain:'退款结果待核对',rejected:'渠道未确认退款',refunded:'已退款'};
const tradeLabels={checkout:'已创建支付宝交易请求',paid:'支付宝确认已付款',closed:'支付已关闭',closing:'关单核对中',
  late_payment:'关单后发现付款，待核对',refund_requested:'已申请退款',refund_submitted:'已提交支付宝退款',
  refund_check_needed:'退款结果待核对',refunded:'支付宝已确认全额退款',started:'开始制作',shipped:'已发货',received:'已签收'};
const actionLabel=value=>t(actions[value]);
const stateLabel=value=>t(states[value]);
const status=order=>h`<span class="badge">${esc(stateLabel(order.processingState))}</span>
  <span class="badge">${esc(t(paymentLabels[order.state]||order.state))}</span>`;
const filters=(values,selected)=>Object.entries(values).map(([code,label])=>
  `<option value="${esc(code)}" ${code===selected?'selected':''}>${esc(t(label))}</option>`).join('');

export async function showOrders(root, route) {
  const staff=route.tab==='admin-orders', prefix=staff?'/admin/orders':'/shop/orders';
  let value=await api(prefix+(route.id?'/'+encodeURIComponent(route.id):'?'+new URLSearchParams(route.params)));
  if(!route.active())return;
  if(!staff&&route.id&&value.canCheck&&route.returnedFromAlipay){
    try{value=await api(prefix+'/'+encodeURIComponent(route.id)+'/payment-status',{method:'POST',json:{},timeout:22000});}
    catch{ /* 用户可以在订单上继续查单。 */ }
    if(!route.active())return;
    history.replaceState(history.state,'',location.pathname+location.hash);
  }
  root.innerHTML=route.id?detail(value,staff,route):listing(value,staff,route);
}

function listing(data, staff, route) {
  const {orders,page,pageSize,total}=data, params=route.params;
  const href=(changes={})=>route.link({...params,...changes});
  return h`<h1>${staff?t('订单处理队列'):t('我的订单')}</h1>
    <p class="notice">订单会分别显示付款、处理和交付进度。</p>
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
        ${item.photoUrl?h`<a href="${esc(item.photoUrl)}" target="_blank" rel="noopener">查看订单授权照片</a>`:''}
        ${item.downloadUrl?h`<a class="button" href="${esc(item.downloadUrl)}">下载已购买的 PDF</a>`:''}</div>`).join('')}
      <p class="price">${esc(t('合计 '))}${money(order.totalCents)}</p></section>
    <section class="card"><h2>处理进度</h2><ol class="progress-list"><li><strong>已提交订单</strong> <time>${esc(date(order.createdAt))}</time></li>
      ${(order.events||[]).map(event=>h`<li><strong>${esc(actionLabel(event.action))}</strong> <time>${esc(date(event.createdAt))}</time>
        ${event.visible===false?h('<span class="badge">仅管理端可见</span>'):''}
        <p class="prose">${esc(event.message)}</p></li>`).join('')}</ol></section>
    ${tradePanel(order,staff)}
    ${next.length?h`<form data-order-action data-dirty class="card" data-version="${order.version}"><h2>处理订单</h2>
      <label>操作<select name="action">${filters(Object.fromEntries(next.map(key=>[key,actions[key]])),'')}</select></label>
      <label>说明<textarea name="message" maxlength="2000"></textarea></label>
      <p class="muted">内部备注仅在管理端显示。</p>
      <button type="submit" class="primary">确认操作</button></form>`:''}`;
}

function transactionForm(action,label,fields=''){
  return h`<form data-trade-action="${action}" class="trade-form">
    ${fields}<button type="submit">${esc(t(label))}</button></form>`;
}

function tradePanel(order,staff) {
  const trade=order.trade;
  if(staff&&!order.canHandle)return '';
  const address=trade?.address;
  const needsAddress=!address&&order.physical;
  const addressFields=needsAddress?h`<label>收件人<input name="recipient" maxlength="60" autocomplete="shipping name" required></label>
    <label>收货联系电话<input type="tel" name="phone" maxlength="30" autocomplete="shipping tel" required></label>
    <label>收货地区<input name="region" maxlength="150" autocomplete="shipping address-level1" required></label>
    <label>详细地址<textarea name="detail" maxlength="300" autocomplete="shipping street-address" required></textarea></label>`:'';
  return h`<section class="card">
    <h2>付款与交付</h2>
    ${!order.paymentAvailable&&!trade?h('<p class="muted">支付宝尚未配置。</p>'):''}
    ${trade?.environment==='sandbox'?h('<p class="notice">支付宝沙箱交易，使用测试余额。</p>'):''}
    ${address?h`<dl class="trade-address"><dt>收货地址</dt><dd>${esc(address.recipient)} · ${esc(address.phone)}</dd>
      <dd>${esc(address.region)} ${esc(address.detail)}</dd></dl>`:''}
    ${trade?.carrier?h`<p>${esc(trade.carrier)} · ${esc(trade.tracking)}</p>`:''}
    ${trade&&order.state==='paid'?h`<p>${esc(t(fulfillmentLabels[trade.fulfillment]))}</p>`:''}
    ${trade?.refundState?h`<p>${esc(t(refundLabels[trade.refundState]))}</p>`:''}
    ${(trade?.events||[]).length?h`<ol class="progress-list">${trade.events.map(event=>h`<li>${esc(t(tradeLabels[event.kind]||event.kind))}
      <time>${esc(date(event.at))}</time></li>`).join('')}</ol>`:''}
    ${order.canPay?transactionForm('alipay','用支付宝付款',addressFields):''}
    ${order.canCheck?transactionForm('payment-status','查询支付宝结果'):''}
    ${order.canCancel?transactionForm('cancel','关闭未付款订单'):''}
    ${trade?.canRequestRefund?transactionForm('refund','申请全额退款',h('<label>退款原因<textarea name="reason" required maxlength="400"></textarea></label>')):''}
    ${trade?.canApproveRefund?transactionForm('approve-refund',trade.refundState==='requested'||!trade.refundState?'提交支付宝全额退款':'核对并重试原退款'):''}
    ${staff&&order.state==='paid'&&!trade?.refundState&&address&&trade.fulfillment==='pending'?transactionForm('start','标记开始制作'):''}
    ${staff&&order.state==='paid'&&!trade?.refundState&&trade?.fulfillment==='started'?transactionForm('ship','确认发货',
      h('<label>物流公司<input name="carrier" maxlength="80" required></label><label>物流单号<input name="tracking" maxlength="100" required></label>')):''}
    ${!staff&&order.state==='paid'&&trade?.fulfillment==='shipped'?transactionForm('receive','确认收货'):''}
  </section>`;
}

export async function submitOrderAction(form, route) {
  const fields=new FormData(form), staff=route.tab==='admin-orders';
  const path=(staff?'/admin/orders/':'/shop/orders/')+encodeURIComponent(route.id)+(staff?'/process':'/reply');
  await api(path,{method:'POST',json:{action:fields.get('action'),message:fields.get('message'),version:Number(form.dataset.version)}});
}

export async function submitTradeAction(form, route){
  const action=form.dataset.tradeAction;
  const admin=route.tab==='admin-orders';
  const prefix=(admin?'/admin/orders/':'/shop/orders/')+encodeURIComponent(route.id);
  const fields=Object.fromEntries(new FormData(form));
  let method=action, json=fields;
  if(action==='alipay')json={address:Object.keys(fields).length?fields:null};
  else if(action==='approve-refund'){method='refund';json={retry:true};}
  else if(['start','ship'].includes(action)){method='fulfillment';json={...fields,action};}
  if(['cancel','approve-refund','ship','receive'].includes(action)&&!confirm(t('确认执行此订单操作？')))return false;
  const result=await api(prefix+'/'+method,{method:'POST',json,timeout:30000});
  if(action==='alipay'){
    const url=new URL(result.checkoutUrl);
    if(url.protocol!=='https:'||!['openapi.alipay.com','openapi-sandbox.dl.alipaydev.com','openapi.alipaydev.com'].includes(url.hostname))throw new Error(t('支付宝付款地址无效。'));
    location.assign(url.href);
    return false;
  }
  return true;
}
