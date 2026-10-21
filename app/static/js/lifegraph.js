/* 人生脉络的浏览与呈现；事实只通过授权 API 读取和显式关系变更。 */
import {api} from './api.js';
import {esc,icon,dateLabel,stateLabels} from './ui.js';
import {LifeGraphState} from './lifegraph-state.js';

const labels={record:'记录',person:'人物',pet:'宠物',object:'物品',place:'地点',work:'工作',media:'影音',custom:'对象',chapter:'阶段',thread:'长期投入',now:'此刻'};
const allTypes=Object.keys(labels).filter(type=>type!=='now');
const symbols={now:'sun',record:'book',person:'people',pet:'pet',object:'archive',place:'pin',work:'book',media:'book',custom:'sprout',chapter:'calendar',thread:'thread'};
let graph=new LifeGraphState(),mounted=null;
let selected='now',filters={types:[...allTypes],from:'',to:''},viewport={x:0,y:0,scale:0.8},mode='canvas';
let results=[],relation=null,searchText='',notice='',error='',retry=null,authorized=false;

export function lifegraphShell(){return '<section id="lifegraph" aria-label="人生脉络"><p class="loading-state">正在打开与你有关的人与事…</p></section>';}

export function mountLifeGraph(root,callbacks){
  mounted?.destroy();const controller=new GraphController(root,callbacks);mounted=controller;
  controller.run(async()=>{
    authorized=false;results=[];relation=null;
    const focus=callbacks.focus||graph.root;
    if(!graph.nodes.size||focus!==graph.root)await controller.focus(focus);
    else await controller.refresh();
    authorized=true;
  });
  return ()=>{if(mounted===controller){controller.destroy();mounted=null;}};
}

class GraphController {
  constructor(root,callbacks){
    this.root=root;this.callbacks=callbacks;this.busy=false;this.alive=true;this.drag=null;this.pointers=new Map();this.pinching=null;
    this.click=this.click.bind(this);this.submit=this.submit.bind(this);this.pointer=this.pointer.bind(this);this.wheel=this.wheel.bind(this);
    this.keydown=this.keydown.bind(this);this.wake=this.wake.bind(this);this.protect=this.protect.bind(this);
    root.addEventListener('click',this.click);root.addEventListener('submit',this.submit);
    for(const name of ['pointerdown','pointermove','pointerup','pointercancel'])root.addEventListener(name,this.pointer);
    root.addEventListener('wheel',this.wheel,{passive:false});root.addEventListener('keydown',this.keydown);
    window.addEventListener('focus',this.wake);document.addEventListener('visibilitychange',this.protect);
  }
  destroy(){this.alive=false;this.root.removeEventListener('click',this.click);this.root.removeEventListener('submit',this.submit);for(const name of ['pointerdown','pointermove','pointerup','pointercancel'])this.root.removeEventListener(name,this.pointer);this.root.removeEventListener('wheel',this.wheel);this.root.removeEventListener('keydown',this.keydown);window.removeEventListener('focus',this.wake);document.removeEventListener('visibilitychange',this.protect);}
  async run(action){
    if(this.busy||!this.alive)return;this.busy=true;error='';retry=action;this.render();
    try{await action();}catch(problem){if(this.alive){error=problem.message;if(problem.status===403||problem.status===401){authorized=false;graph.reset();results=[];relation=null;}}}
    finally{this.busy=false;if(this.alive){if(document.hidden)authorized=false;if(this.needsValidation&&!document.hidden){this.needsValidation=false;authorized=false;this.run(()=>this.refresh());}else this.render();}}
  }
  params(focus){const params=new URLSearchParams({focus,types:filters.types.join(',')});if(filters.from)params.set('from',filters.from);if(filters.to)params.set('to',filters.to);return params;}
  async page(focus,cursor=null){const params=this.params(focus);if(cursor)params.set('cursor',cursor);return api('/lifegraph/neighbors?'+params);}
  async focus(key='now'){
    const page=await this.page(key);if(!this.alive)return;
    graph.reset(key);graph.applyPage(page);selected=key;viewport={x:0,y:0,scale:0.8};results=[];relation=null;authorized=true;notice=page.edges.length?'':key==='now'?'这段时间还没有可展开的记录。可查找更早的人与事，或从首页开始记录。':'还没有保存关联；可以在这里明确关联已有资料。';this.callbacks.onFocus?.(key);
  }
  async expand(key,append=false){const branch=graph.branches.get(key);const page=await this.page(key,append?branch?.cursor:null);if(!this.alive)return;graph.applyPage(page,append);notice=page.edges.length?'只打开了这一层关联。':'当前筛选下没有更多关联。';}
  async refresh(){
    const keys=graph.visible().nodes.map(node=>node.key);
    if(!keys.length){await this.focus('now');return;}
    // Cookie被清理或空间切换后先更新CSRF，再授权复核，旧画面不会提前出现。
    await api('/auth/session');
    const snapshot=await api('/lifegraph/snapshot',{method:'POST',json:{keys}});if(!this.alive)return;
    if(!graph.reconcile(snapshot)){await this.focus('now');notice='原焦点已删除或不可读取，已回到现在。';}
    if(!graph.nodes.has(selected)){selected=graph.root;relation=null;}
    authorized=true;
  }
  protect(){if(document.hidden){this.callbacks.closeReadingDialogs?.();authorized=false;this.needsValidation=true;this.render();}else this.wake();}
  wake(){if(document.hidden||!this.alive)return;this.callbacks.closeReadingDialogs?.();authorized=false;results=[];relation=null;if(this.busy){this.needsValidation=true;this.render();return;}this.needsValidation=false;this.run(()=>this.refresh());}
  layout(nodes,edges){
    graph.positions.set(graph.root,{x:0,y:0});
    const depths=new Map([[graph.root,0]]),pending=[graph.root];
    while(pending.length){const source=pending.shift();for(const edge of edges){const other=edge.source===source?edge.target:edge.target===source?edge.source:null;if(other&&!depths.has(other)){depths.set(other,depths.get(source)+1);pending.push(other);}}}
    const occupied=[...graph.positions.values()];
    for(const node of nodes){if(graph.positions.has(node.key))continue;const depth=depths.get(node.key)||1;let point=null;
      for(let ring=depth;ring<25&&!point;ring++){const slots=ring*8;for(let slot=0;slot<slots;slot++){const angle=-Math.PI/2+2*Math.PI*slot/slots;const candidate={x:Math.cos(angle)*ring*320,y:Math.sin(angle)*ring*210};if(occupied.every(other=>Math.abs(candidate.x-other.x)>226||Math.abs(candidate.y-other.y)>124)){point=candidate;break;}}}
      point=point||{x:depth*330,y:occupied.length*145};graph.positions.set(node.key,point);occupied.push(point);
    }
  }
  render(){
    if(!this.alive)return;
    const visible=authorized?graph.visible():{nodes:[],edges:[]};this.layout(visible.nodes,visible.edges);
    const active=visible.nodes.find(node=>node.key===selected)||visible.nodes[0];if(active)selected=active.key;
    const focus=graph.nodes.get(graph.root);
    const optionsOpen=this.root.querySelector('.lg-options')?.open||results.length>0;
    this.root.innerHTML=`<header class="lg-heading"><div><span class="eyebrow">THE THREADS OF YOUR LIFE</span><h2>从此刻，慢慢展开一生</h2><p>循着一次经历，遇见那些与你有关的人、事与时光。</p></div><button class="button" data-lg="home">${icon('sun')}回到现在</button></header>
      <div class="lg-tools"><div class="lg-tabs" role="group" aria-label="脉络观看方式"><button data-lg="canvas" aria-pressed="${mode==='canvas'}">${icon('globe')}关系画布</button><button data-lg="list" aria-pressed="${mode==='list'}">${icon('list')}关系列表</button></div><button class="text-button" data-lg="refresh">刷新资料</button></div>
      <details class="lg-options" ${optionsOpen?'open':''}><summary>查找与筛选 <span>${filters.types.length===allTypes.length&&!filters.from&&!filters.to?'全部类型 · 时间不限':'已应用筛选'}</span></summary><div><form class="lg-search" data-lg-form="search"><label>在资料中找一个起点<input name="q" maxlength="100" value="${esc(searchText)}" placeholder="人物、阶段或一段记忆"></label><button class="button" type="submit">查找</button></form>${results.length?`<div class="lg-search-results">${results.map(node=>`<button data-lg-focus="${esc(node.key)}"><span>${esc(labels[node.type])}</span>${esc(node.label)}</button>`).join('')}</div>`:''}<form data-lg-form="filter" class="lg-filter"><fieldset><legend>显示类型</legend>${allTypes.map(type=>`<label><input type="checkbox" name="types" value="${type}" ${filters.types.includes(type)?'checked':''}>${labels[type]}</label>`).join('')}</fieldset><div><label>从<input type="date" name="from" value="${esc(filters.from)}"></label><label>至<input type="date" name="to" value="${esc(filters.to)}"></label><button class="button" type="submit">应用筛选</button><button class="text-button" type="button" data-lg="clear-filter">清除筛选</button></div></form></div></details>
      ${error?`<div class="lg-error" role="alert"><p>${esc(error)}</p><button class="button small" data-lg="retry">重试刚才操作</button></div>`:''}
      ${!authorized?`<div class="lg-checking" role="status">${this.busy?'正在核对当前空间的资料…':'资料尚未重新验证，请刷新重试。'}</div>`:`<div class="lg-workspace ${mode==='list'?'lg-list-mode':''}"><div class="lg-board"><div class="lg-canvas" tabindex="0" role="region" aria-label="人生脉络画布，方向键平移，加减键缩放"><div class="lg-canvas-hint">${icon('sprout')}每次打开一点点，生活自有连接</div><div class="lg-scene"><svg class="lg-lines" aria-hidden="true">${visible.edges.map(edge=>this.line(edge)).join('')}</svg>${visible.nodes.map(node=>this.nodeCard(node)).join('')}</div><div class="lg-canvas-controls"><button data-lg="zoom-out" aria-label="缩小">−</button><span>${Math.round(viewport.scale*100)}%</span><button data-lg="zoom-in" aria-label="放大">＋</button><button data-lg="fit" aria-label="查看当前全部节点">适合画面</button><button data-lg="center" aria-label="居中焦点">居中</button></div></div><div class="lg-list" aria-label="已展开资料与关系">${visible.nodes.map(node=>this.listItem(node,visible.edges)).join('')}</div><div class="lg-legend"><span><i></i>用户保存的正式关联</span><span><i class="temporal"></i>时间定位，不代表正式关系</span></div><p class="lg-footnote">${visible.nodes.length} 个已展开节点 · 焦点：${esc(focus?.label||'现在')}<span>拖动平移 · 滚轮或双指缩放 · 列表也可完成全部操作</span></p></div><aside class="lg-inspector" aria-label="节点摘要与关联操作">${active?this.inspector(active,visible.edges):''}</aside></div>`}
      <p class="lg-status" role="status">${this.busy?'正在读取…':esc(notice||'“现在”展示过去30天至未来14天及仍在进行中的经历，每次最多6项；修改时间不决定人生重要性。')}</p>`;
    for(const element of this.root.querySelectorAll('[data-lg-node]')){const point=graph.positions.get(element.dataset.lgNode);element.style.left=point.x+'px';element.style.top=point.y+'px';}
    this.transform();
    this.root.setAttribute('aria-busy',String(this.busy));
    this.root.querySelectorAll('button,input,select').forEach(element=>{element.disabled=this.busy;});
  }
  line(edge){const a=graph.positions.get(edge.source),b=graph.positions.get(edge.target);if(!a||!b)return '';const bend=(b.x-a.x)*0.5;return `<path class="${edge.type==='time_context'?'temporal':''}" d="M ${a.x} ${a.y} C ${a.x+bend} ${a.y}, ${b.x-bend} ${b.y}, ${b.x} ${b.y}"><title>${esc(edge.label+'：'+edge.provenance)}</title></path>`;}
  nodeCard(node){return `<button class="lg-node lg-type-${node.type} ${node.key===selected?'selected':''} ${node.key===graph.root?'root-node':''}" data-lg-node="${esc(node.key)}" aria-pressed="${node.key===selected}"><span class="lg-node-kind">${icon(symbols[node.type])}${esc(labels[node.type]||'对象')}</span><b>${esc(node.label)}</b><small>${esc(node.type==='now'?node.subtitle:node.date?.start?dateLabel(node.date.start):node.type==='record'?stateLabels[node.recordState]:'展开，看看相关经历')}</small>${graph.branches.has(node.key)?'<i class="lg-open-dot" aria-label="已展开"></i>':''}</button>`;}
  buttons(node){const branch=graph.branches.get(node.key);return `<div class="lg-node-actions"><button class="button small" data-lg-expand="${esc(node.key)}">${branch?'重新读取这一层':'展开一层关联'}</button>${branch?.cursor?`<button class="button small" data-lg-more="${esc(node.key)}">还有关联 · 继续展开</button>`:''}${branch?`<button class="text-button" data-lg-collapse="${esc(node.key)}">收起这一层</button>`:''}${node.key!==graph.root?`<button class="button small subtle" data-lg-focus="${esc(node.key)}">以此为焦点</button>`:''}</div>`;}
  listItem(node,edges){const related=edges.filter(edge=>edge.source===node.key||edge.target===node.key);return `<article class="lg-list-item"><button class="lg-list-title" data-lg-select="${esc(node.key)}">${icon(symbols[node.type])}<span><small>${esc(labels[node.type])}</small><b>${esc(node.label)}</b></span></button><ul>${related.map(edge=>{const other=graph.nodes.get(edge.source===node.key?edge.target:edge.source);return `<li>${esc(edge.label)} → <button class="text-button" data-lg-select="${esc(other?.key)}">${esc(other?.label)}</button></li>`;}).join('')||'<li>尚未打开关联</li>'}</ul>${this.buttons(node)}</article>`;}
  inspector(node,edges){const related=edges.filter(edge=>edge.source===node.key||edge.target===node.key);return `<div class="lg-inspector-kicker">${icon(symbols[node.type])}${esc(labels[node.type])} · 节点摘要</div><h3>${esc(node.label)}</h3>${node.date?.start?`<p class="lg-inspector-date">${esc(dateLabel(node.date.start))}${node.date.end?' — '+esc(dateLabel(node.date.end)):''}</p>`:''}<p class="lg-summary">${esc(node.summary||'这里还没有写下介绍。')}</p>${this.buttons(node)}<div class="lg-detail-actions">${node.type==='record'?`<button class="button primary" data-lg-open="${esc(node.key)}">查看原记录 ${icon('chevron')}</button>`:node.type==='person'?`<button class="button" data-lg-open="${esc(node.key)}">查看人物资料 ${icon('chevron')}</button>`:''}${node.key!=='now'?`<button class="text-button" data-lg-records="${esc(node.key)}">在记录中查看</button><button class="button small" data-lg-relate="${esc(node.key)}">关联${node.type==='record'?'一份资料':'一条记录'}</button>`:''}</div>${relation?this.relationForm():''}<div class="lg-related"><h4>已经看见的连接 <span>${related.length}</span></h4>${related.length?related.map(edge=>{const other=graph.nodes.get(edge.source===node.key?edge.target:edge.source);return `<div class="lg-related-item"><button data-lg-select="${esc(other?.key)}">${icon(symbols[other?.type])}<span>${esc(other?.label)}<small>${esc(edge.label)}</small></span></button><p>${esc(edge.provenance)}</p>${edge.editable?`<button class="text-button danger" data-lg-unlink="${esc(edge.id)}">解除此关联</button>`:''}</div>`;}).join(''):'<p class="lg-muted">可以展开一层，看看还有哪些关联。</p>'}<p class="lg-muted">两个人共同参与一条记录，只呈现经由记录的路径，不推断亲密、影响或因果。</p></div>`;}
  relationForm(){return `<form class="lg-relation-form" data-lg-form="relation-search"><h4>选择关联的${relation.origin.type==='record'?'资料':'记录'}</h4><label>查找已有资料<input name="q" maxlength="100" value="${esc(relation.query||'')}" placeholder="输入名称或标题"></label><button class="button small" type="submit">查找</button><button class="text-button" type="button" data-lg="cancel-relation">取消</button>${relation.matches?.length?`<div class="lg-targets">${relation.matches.map(node=>`<button type="button" data-lg-link="${esc(node.key)}"><small>${esc(labels[node.type])}</small>${esc(node.label)}</button>`).join('')}</div>`:relation.matches?'<p>没有匹配资料。可以先到人物或记录页面创建。</p>':''}</form>`;}
  transform(){const canvas=this.root.querySelector('.lg-canvas'),scene=this.root.querySelector('.lg-scene');if(!canvas||!scene)return;scene.style.transform=`translate(${canvas.clientWidth/2+viewport.x}px,${canvas.clientHeight/2+viewport.y}px) scale(${viewport.scale})`;const value=this.root.querySelector('.lg-canvas-controls span');if(value)value.textContent=Math.round(viewport.scale*100)+'%';}
  zoom(factor,x=0,y=0){const next=Math.max(0.3,Math.min(1.6,viewport.scale*factor)),ratio=next/viewport.scale;viewport.x=x-(x-viewport.x)*ratio;viewport.y=y-(y-viewport.y)*ratio;viewport.scale=next;this.transform();}
  fit(){const nodes=graph.visible().nodes,points=nodes.map(node=>graph.positions.get(node.key));const canvas=this.root.querySelector('.lg-canvas');if(!canvas||!points.length)return;const xs=points.map(p=>p.x),ys=points.map(p=>p.y),left=Math.min(...xs)-124,right=Math.max(...xs)+124,top=Math.min(...ys)-75,bottom=Math.max(...ys)+75;viewport.scale=Math.min(1,Math.max(0.3,Math.min((canvas.clientWidth-40)/(right-left),(canvas.clientHeight-90)/(bottom-top))));viewport.x=-(left+right)/2*viewport.scale;viewport.y=-(top+bottom)/2*viewport.scale;this.transform();}
  click(event){
    const target=event.target.closest('button');if(!target||!this.root.contains(target))return;event.stopPropagation();if(this.busy)return;
    if(this.suppressClick){this.suppressClick=false;return;}
    if(target.dataset.lgNode||target.dataset.lgSelect){selected=target.dataset.lgNode||target.dataset.lgSelect;relation=null;this.render();return;}
    if(target.dataset.lgFocus){this.run(()=>this.focus(target.dataset.lgFocus));return;}
    if(target.dataset.lgExpand){this.run(()=>this.expand(target.dataset.lgExpand));return;}
    if(target.dataset.lgMore){this.run(()=>this.expand(target.dataset.lgMore,true));return;}
    if(target.dataset.lgCollapse){graph.collapse(target.dataset.lgCollapse);if(!graph.nodes.has(selected))selected=graph.root;relation=null;this.render();return;}
    if(target.dataset.lgOpen){const node=graph.nodes.get(target.dataset.lgOpen);if(node.type==='record')this.callbacks.openRecord(node.id);else this.callbacks.openPerson(node.id);return;}
    if(target.dataset.lgRecords){const node=graph.nodes.get(target.dataset.lgRecords);this.callbacks.openRecords(node);return;}
    if(target.dataset.lgRelate){relation={origin:graph.nodes.get(target.dataset.lgRelate)};this.render();this.root.querySelector('.lg-relation-form input')?.focus();return;}
    if(target.dataset.lgLink){const node=relation?.matches.find(node=>node.key===target.dataset.lgLink);if(node)this.run(()=>this.changeLink(relation.origin,node,'link'));return;}
    if(target.dataset.lgUnlink){const edge=graph.visible().edges.find(edge=>edge.id===target.dataset.lgUnlink);if(edge)this.run(()=>this.changeLink(graph.nodes.get('record:'+edge.recordId),graph.nodes.get(edge.nodeKey),'unlink'));return;}
    const action=target.dataset.lg;
    if(action==='home')this.run(()=>this.focus('now'));
    else if(action==='refresh')this.run(()=>this.refresh());
    else if(action==='retry'&&retry)this.run(retry);
    else if(action==='zoom-in')this.zoom(1.2);
    else if(action==='zoom-out')this.zoom(1/1.2);
    else if(action==='fit')this.fit();
    else if(action==='center'){viewport.x=0;viewport.y=0;this.transform();}
    else if(action==='canvas'||action==='list'){mode=action;this.render();}
    else if(action==='cancel-relation'){relation=null;this.render();}
    else if(action==='clear-filter'){this.run(async()=>{const before=filters;filters={types:[...allTypes],from:'',to:''};try{await this.focus(graph.root);}catch(error){filters=before;throw error;}});}
  }
  submit(event){
    const form=event.target;if(!form.dataset.lgForm)return;event.preventDefault();event.stopPropagation();if(this.busy)return;
    const data=new FormData(form);
    if(form.dataset.lgForm==='search'){searchText=String(data.get('q')||'');this.run(async()=>{const value=await api('/lifegraph/search?'+new URLSearchParams({q:searchText}));if(!this.alive)return;results=value.nodes;notice=results.length?(value.hasMore?'找到前12项，请细化关键词。':'选择一个节点作为新的起点。'):'没有匹配资料。';});}
    else if(form.dataset.lgForm==='filter'){
      const next={types:data.getAll('types'),from:String(data.get('from')||''),to:String(data.get('to')||'')};
      if(!next.types.length){error='请至少选择一种资料类型。';this.render();return;}
      this.run(async()=>{const before=filters;filters=next;try{await this.focus(graph.root);}catch(error){filters=before;throw error;}});
    }else if(form.dataset.lgForm==='relation-search'){
      const query=String(data.get('q')||'');relation.query=query;
      this.run(async()=>{const value=await api('/lifegraph/search?'+new URLSearchParams({q:query,scope:relation.origin.type==='record'?'target':'record'}));if(!this.alive||!relation)return;relation.matches=value.nodes;notice=value.hasMore?'只展示前12项，请继续细化关键词。':'';});
    }
  }
  async changeLink(origin,target,operation){
    const record=origin.type==='record'?origin:target,node=origin.type==='record'?target:origin;
    const accepted=await this.callbacks.confirmRelation({record,node,operation});if(!accepted||!this.alive)return;
    await api('/lifegraph/relations',{method:'POST',json:{recordId:record.id,nodeKey:node.key,version:record.version,operation,confirmed:true}});
    if(!this.alive)return;relation=null;await this.refresh();
    if(graph.nodes.has(record.key))await this.expand(record.key);
    else if(graph.nodes.has(node.key))await this.expand(node.key);
    notice=operation==='link'?'关联已保存，各处读取同一份记录。':'已解除关联，原记录、人物和照片仍然保留。';
  }
  wheel(event){if(!event.target.closest('.lg-canvas')||this.busy)return;event.preventDefault();const rect=this.root.querySelector('.lg-canvas').getBoundingClientRect();this.zoom(Math.exp(-event.deltaY*0.0015),event.clientX-rect.left-rect.width/2,event.clientY-rect.top-rect.height/2);}
  keydown(event){if(!event.target.classList.contains('lg-canvas'))return;const shifts={ArrowLeft:[40,0],ArrowRight:[-40,0],ArrowUp:[0,40],ArrowDown:[0,-40]};if(shifts[event.key]){event.preventDefault();viewport.x+=shifts[event.key][0];viewport.y+=shifts[event.key][1];this.transform();}else if(['+','=','-'].includes(event.key)){event.preventDefault();this.zoom(event.key==='-'?1/1.2:1.2);}}
  pointer(event){
    const canvas=event.target.closest('.lg-canvas');if(!canvas||event.target.closest('.lg-canvas-controls')||this.busy)return;
    if(event.type==='pointerdown'){
      if(event.button!==0)return;this.pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
      (event.target.closest('[data-lg-node]')||canvas).setPointerCapture(event.pointerId);
      if(this.pointers.size===1)this.drag={id:event.pointerId,x:event.clientX,y:event.clientY,dx:viewport.x,dy:viewport.y,moved:false};
      if(this.pointers.size===2){const [a,b]=[...this.pointers.values()];this.pinching={distance:Math.hypot(a.x-b.x,a.y-b.y),scale:viewport.scale};}
    }else if(event.type==='pointermove'&&this.pointers.has(event.pointerId)){
      this.pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
      if(this.pointers.size===2&&this.pinching){const [a,b]=[...this.pointers.values()],next=this.pinching.scale*Math.hypot(a.x-b.x,a.y-b.y)/Math.max(1,this.pinching.distance);this.zoom(next/viewport.scale);this.suppressClick=true;}
      else if(this.drag?.id===event.pointerId){const dx=event.clientX-this.drag.x,dy=event.clientY-this.drag.y;if(Math.hypot(dx,dy)>6){this.drag.moved=true;viewport.x=this.drag.dx+dx;viewport.y=this.drag.dy+dy;this.transform();}}
    }else if(event.type==='pointerup'||event.type==='pointercancel'){
      if(this.drag?.moved){this.suppressClick=true;setTimeout(()=>{this.suppressClick=false;},0);}this.pointers.delete(event.pointerId);this.pinching=null;this.drag=null;
    }
  }
}
