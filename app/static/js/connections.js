import {api} from './api.js';
import {h,t} from './i18n.js';
import {esc,dateLabel} from './ui.js';

export function createConnections(container) {
  let query, history=[], request, active=false, layout='diagram';

  async function load() {
    request?.abort();
    const controller=new AbortController();
    request=controller;
    let timer=setTimeout(()=>{
      if(!controller.signal.aborted)container.querySelector('[data-connection-status]').textContent=t('正在读取关系…');
    },300);
    try{
      const result=await api('/connections?'+new URLSearchParams(query),{signal:controller.signal});
      if(!active||controller.signal.aborted)return;
      const {focus,nodes,page,hasMore}=result;
      const link=node=>h`<div class="connection-node"><button type="button" data-connection-kind="${node.kind}" data-connection-id="${esc(node.id)}">${esc(node.label||t('未命名记录'))}</button>
        ${node.kind==='record'?h`<small>${esc(dateLabel(node.date))}</small><button class="button small subtle" data-record="${esc(node.id)}">打开记录</button>`:''}</div>`;
      container.innerHTML=h`
        <section class="settings-card">
          <form class="section-toolbar" data-connection-search><label>查找人物或记录
            <input name="q" maxlength="120" value="${esc(query.q||'')}"></label>
            ${focus?'':h`<label>起点<select name="kind"><option value="person">人物</option><option value="record" ${query.kind==='record'?'selected':''}>记录</option></select></label>`}
            <button class="button small">查找</button>
          </form>
          <div class="section-toolbar">
            ${history.length?h('<button type="button" class="button small" data-connection-back>返回上一层</button>'):''}
            ${focus?h`<button class="button small" type="button" data-connection-layout>${layout==='diagram'?t('切换列表'):t('切换关系图')}</button>`:''}
          </div>
          <p data-connection-status role="status"></p>
          ${focus?h`<header class="connection-focus"><h2>${esc(focus.label||t('未命名记录'))}</h2>
            <p>来自记录中已保存的人物关联。</p>${focus.kind==='record'?h`<button class="button small" data-record="${esc(focus.id)}">打开记录</button>`:''}</header>`:''}
          <div class="connection-nodes ${focus&&layout==='diagram'?'connection-diagram':''}">${nodes.map(link).join('')||h('<p>当前没有匹配的关联。</p>')}</div>
          <div class="section-toolbar">
            ${page>1?h`<button class="button small" type="button" data-connection-page="${page-1}">上一页</button>`:''}
            ${hasMore?h`<button class="button small" type="button" data-connection-page="${page+1}">下一页</button>`:''}
          </div>
        </section>`;
    }catch(error){
      if(active&&!controller.signal.aborted)container.querySelector('[data-connection-status]').innerHTML=h`${esc(error.message)} <button type="button" class="button small" data-connection-retry>重新加载</button>`;
    }finally{clearTimeout(timer);}
  }

  container.addEventListener('submit',event=>{
    if(!event.target.matches('[data-connection-search]'))return;
    event.preventDefault();
    const form=new FormData(event.target);
    query={...query,q:form.get('q').trim(),kind:form.get('kind')||query.kind,page:'1'};
    load();
  });
  container.addEventListener('click',event=>{
    if(!active)return;
    const button=event.target.closest('button');
    if(!button)return;
    if(button.hasAttribute('data-connection-retry'))load();
    if(button.hasAttribute('data-connection-back')){query=history.pop();load();}
    if(button.hasAttribute('data-connection-layout')){layout=layout==='diagram'?'list':'diagram';load();}
    if(button.dataset.connectionPage){query={...query,page:button.dataset.connectionPage};load();}
    if(button.dataset.connectionId){
      history.push(query);query={kind:button.dataset.connectionKind,id:button.dataset.connectionId,page:'1'};load();
    }
  });
  return {
    open(focus){
      if(focus){history=[{kind:focus.kind,page:'1'}];query={...focus,page:'1'};}
      else if(!query)query={kind:'person',page:'1'};
      active=true;
      container.innerHTML=h('<p data-connection-status role="status"></p>');
      load();
    },
    close(){active=false;request?.abort();},
  };
}
