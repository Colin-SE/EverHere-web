import {api,getSession,downloadFile} from './api.js';
import {icon,hydrateIcons,esc,today,dateLabel,localPhoto,stateLabels,toast} from './ui.js';
import * as views from './views.js';
import {DraftSession} from './drafts.js';
import {openGallery} from './gallery.js';
import {lifegraphShell,mountLifeGraph} from './lifegraph.js';

/* 统一页面状态：筛选与记录在视图切换时复用，不写入浏览器持久缓存。 */
const now=new Date();
const state={view:'home',homeYear:now.getFullYear(),records:[],allRecords:[],graph:{entities:[],},filters:{},q:'',user:null,calendarYear:now.getFullYear(),calendarMonth:now.getMonth(),selectedDate:today(),place:null,drafts:[],personId:null,theme:'WARM',allQuery:{filters:{},q:''},recordQuery:{filters:{},q:''}};
const titles={lifegraph:['人生脉络','从现在出发，一点点打开人与经历的连接。'],about:['关于与帮助','本机资料、备份和当前真实能力。'],all:['全部记录','包含关闭时间轴显示的普通记录；筛选与时间轴独立。'],drafts:['本机草稿','草稿单独保存，不计正式记录，不进入云同步。'],trash:['回收站','软删除保留原 ID、关系和照片，可随时恢复。'],appearance:['外观','暖阳与林间，仅改变当前浏览器外观。'],person:['人物与经历','一份人物资料，关联同一份人生记录。'],home:['我的生活','过去，现在和未来，都是我的人生。'],timeline:['人生记录','按时间，重新遇见那些值得留下的生活。'],calendar:['日历回看','翻过日历，再次遇见那些有故事的日子。'],places:['地点','走过的地方，留下了属于你的故事。'],upcoming:['未来计划','给未来留一些期待，也给自己留一些空白。'],entities:['人物','那些人、那些地方，都在你的故事里。'],mine:['我的','保护、管理和带走自己的人生资料。'],archive:['数据管理','安心收藏，自由带走。']};
const content=document.getElementById('view-content');
const recordForm=document.getElementById('record-form');
const editor=document.getElementById('editor-dialog');
let editorRecord=null,editorPhotos=[],editorDirty=false,uploading=false,loadSequence=0;
let editorTags=[],editorOpening=false,savingRecord=false,progressTouched=false,dateInputs={},dateMode='unknown';
let disposeLifeGraph=null;
let currentDetail=null,pendingArchive=null,pendingPreview=null,pendingConfirm=null;
hydrateIcons();
document.getElementById('today-label').textContent=`${today().replaceAll('-',' . ')}  /  ${now.toLocaleDateString('zh-CN',{weekday:'long'})}`;

/* 确认框的异步动作出错时保持打开，不提前显示成功或丢弃输入。 */
function ask({title,message,fields='',label='确认',action}){
  const dialog=document.getElementById('confirm-dialog');
  document.getElementById('confirm-title').textContent=title;
  document.getElementById('confirm-message').textContent=message;
  document.getElementById('confirm-fields').innerHTML=fields;
  document.getElementById('confirm-error').textContent='';
  document.getElementById('confirm-submit').textContent=label;
  document.getElementById('confirm-submit').disabled=false;
  dialog.showModal();
  return new Promise(resolve=>{pendingConfirm={action,resolve};});
}
document.getElementById('confirm-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=document.getElementById('confirm-submit');button.disabled=true;
  const pending=pendingConfirm;
  try{
    await pending.action(Object.fromEntries(new FormData(event.currentTarget)));
    pendingConfirm=null;document.getElementById('confirm-dialog').close();pending.resolve(true);
  }catch(error){document.getElementById('confirm-error').textContent=error.message;}
  finally{button.disabled=false;}
});
document.getElementById('confirm-dialog').addEventListener('close',()=>{if(pendingConfirm){pendingConfirm.resolve(false);pendingConfirm=null;}document.getElementById('confirm-fields').replaceChildren();});
function updateNav(){
  document.body.dataset.currentView=state.view;
  document.querySelectorAll('.nav-item,[data-view].bottom-nav-item,.bottom-nav [data-view]').forEach(button=>{
    const mobileSection=['calendar','upcoming','all','person'].includes(state.view)?'timeline':['archive','entities','drafts','trash','appearance','about','lifegraph'].includes(state.view)?'mine':state.view;
    const active=button.dataset.view===(button.closest('.bottom-nav')?mobileSection:state.view);
    button.classList.toggle('active',active);
    if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
  });
  document.querySelectorAll('[data-switch]').forEach(button=>button.classList.toggle('active',button.dataset.switch===state.view));
  const [title,description]=titles[state.view];
  document.getElementById('page-title').textContent=title;
  document.getElementById('page-description').textContent=description;
  document.getElementById('breadcrumb').textContent=title;
  document.title=`${title} · 人生相册`;
  document.querySelector('.page-heading').hidden=['home','lifegraph'].includes(state.view);
  document.getElementById('record-tools').hidden=!['timeline','calendar','places','upcoming','all','person'].includes(state.view);
  if(document.getElementById('record-tools').hidden)document.getElementById('filters').hidden=true;
  document.getElementById('new-record').hidden=['archive','mine','trash','drafts','appearance','entities','about','lifegraph'].includes(state.view);
}
function writeRoute(replace=false){
  const params=new URLSearchParams({view:state.view});if(state.view==='lifegraph'&&state.lifegraphFocus)params.set('focus',state.lifegraphFocus);if(state.personId&&state.view==='person')params.set('id',state.personId);
  if(['timeline','calendar','all','places','person','upcoming'].includes(state.view)){for(const [key,value] of Object.entries(state.filters))if(value)params.set(key,value);if(state.q)params.set('q',state.q);}
  if(state.view==='calendar'){params.set('month',`${state.calendarYear}-${String(state.calendarMonth+1).padStart(2,'0')}`);params.set('day',state.selectedDate);}
  history[replace?'replaceState':'pushState'](null,'','#'+params.toString());
}
function restoreRoute(){
  const params=new URLSearchParams(location.hash.slice(1));const view=params.get('view');state.view=Object.hasOwn(titles,view)?view:'home';
  state.personId=params.get('id');state.lifegraphFocus=params.get('focus')||undefined;state.filters={};for(const key of ['state','progress','precision','from','to','tag','node','kind','people'])if(params.get(key))state.filters[key]=params.get(key);
  state.q=params.get('q')||'';const month=/^(\d{4})-(\d{2})$/.exec(params.get('month')||'');if(month&&Number(month[2])>=1&&Number(month[2])<=12){state.calendarYear=Number(month[1]);state.calendarMonth=Number(month[2])-1;}if(/^\d{4}-\d{2}-\d{2}$/.test(params.get('day')||''))state.selectedDate=params.get('day');
  syncFilterForm();
}
function syncFilterForm(){document.getElementById('search').value=state.q;for(const element of document.getElementById('filters').elements)if(element.name&&element.name!=='people')element.value=state.filters[element.name]||'';}
async function navigate(view){
  if(!Object.hasOwn(titles,view))return;
  if(state.view==='archive'){pendingArchive=null;pendingPreview=null;}
  if(state.view==='all'&&view!=='all'){state.allQuery={filters:{...state.filters},q:state.q};state.filters={...state.recordQuery.filters};state.q=state.recordQuery.q;}
  if(view==='all'&&state.view!=='all'){state.recordQuery={filters:{...state.filters},q:state.q};state.filters={...state.allQuery.filters};state.q=state.allQuery.q;}
  state.view=view;state.place=null;syncFilterForm();updateNav();writeRoute();closeMenu();window.scrollTo({top:0,behavior:'instant'});await load();
}
window.addEventListener('popstate',async()=>{if(editor.open){await closeEditor();if(editor.open){writeRoute(true);return;}}if(nodeDialog.open){await closeNode();if(nodeDialog.open){writeRoute(true);return;}}restoreRoute();updateNav();await load();});
async function load(){
  const sequence=++loadSequence;
  disposeLifeGraph?.();disposeLifeGraph=null;
  if(state.view==='lifegraph'){
    content.innerHTML=lifegraphShell();
    disposeLifeGraph=mountLifeGraph(document.getElementById('lifegraph'),{
      focus:state.lifegraphFocus,
      onFocus:key=>{state.lifegraphFocus=key;writeRoute(true);},
      openRecord:showDetail,
      closeReadingDialogs:()=>{for(const id of ['detail-dialog','confirm-dialog']){const dialog=document.getElementById(id);if(dialog.open)dialog.close();}},
      openPerson:id=>{state.personId=id;navigate('person');},
      openRecords:async node=>{state.allQuery={filters:node.type==='record'?{}:{node:node.id,kind:node.key.startsWith('entity:')?'entities':node.type==='chapter'?'chapters':'threads'},q:''};await navigate('all');if(node.type==='record')await showDetail(node.id);},
      confirmRelation:({record,node,operation})=>ask({title:operation==='link'?'确认保存这条关联？':'确认解除这条关联？',message:`${record.label} ↔ ${node.label}。${operation==='link'?'作为用户明确保存的正式关联，所有视图和归档将读取同一份关系。':'解除后原记录、资料和照片仍然保留。'}`,label:operation==='link'?'确认关联':'确认解除',action:async()=>{}})
    });
    return;
  }
  content.innerHTML='<div class="loading-state">正在翻开这一页生活…</div>';
  const useFilters=['timeline','calendar','places','upcoming','all','person'].includes(state.view);
  const target=['timeline','calendar'].includes(state.view)?'timeline':state.view==='places'?'spatial':'all';
  const params=new URLSearchParams({target,...(useFilters?state.filters:{}),...(useFilters&&state.q?{q:state.q}:{}),...(state.view==='trash'?{trash:'true'}:{}),...(state.view==='person'?{node:state.personId||'missing',kind:'entities'}:{})});
  try{
    const [data,graph,drafts,all]=await Promise.all([api(`/records?${params}`),api('/graph'),api('/drafts'),api('/records?target=all')]);
    if(sequence!==loadSequence)return;
    state.records=data.records;state.graph=graph;state.drafts=drafts.drafts;state.allRecords=all.records;
    render();
  }catch(error){
    if(sequence!==loadSequence)return;
    if(error.status===401){location.assign('/login');return;}
    content.innerHTML=`<div class="error-state"><p>${esc(error.message)}</p><button class="button small" data-action="retry">重新加载</button></div>`;
  }
}
function render(){
  const active=document.getElementById('active-filter');
  const node=state.filters.node?state.graph[state.filters.kind]?.find(item=>item.id===state.filters.node):null;
  active.hidden=!['timeline','calendar','places','upcoming','all'].includes(state.view)||!(node||state.place);
  if(!active.hidden)active.innerHTML=`${icon('filter')}正在查看：${esc(node?.name||state.place)}<button data-action="clear-focus">查看全部</button>`;
  const records=state.place?state.records.filter(record=>record.placeName===state.place):state.records;
  const people=document.getElementById('people-filter');if(people)people.innerHTML=state.graph.entities.filter(node=>node.type==='person').map(node=>`<option value="${esc(node.id)}" ${(state.filters.people||'').split(',').includes(node.id)?'selected':''}>${esc(node.name)}</option>`).join('');
  const renderers={all:()=>views.all(records,state),drafts:()=>views.drafts(state),trash:()=>views.trash(records),appearance:()=>views.appearance(state),person:()=>views.person(records,state),about:()=>views.about(state),home:()=>views.home(records,state),mine:()=>views.mine(state),timeline:()=>views.timeline(records,state),calendar:()=>views.calendar(records,state),places:()=>views.places(records,state),upcoming:()=>views.upcoming(records),archive:()=>views.archive(state),entities:()=>views.nodes('entities',state)};
  content.innerHTML=(renderers[state.view]||renderers.home)();
}
const recordDraft=new DraftSession('record',collectRecord,value=>{document.getElementById('draft-status').textContent=value;});
function collectRecord(){
  const fields=recordForm.elements;
  const value={};for(const key of ['title','content','recordState','completionState','datePrecision','timezone','placeName','placePrecision','mood'])value[key]=fields[key].value;
  value.tags=[...editorTags];const pending=fields.tags.value.trim();if(pending&&!value.tags.includes(pending))value.tags.push(pending);
  value.photoUris=[...editorPhotos];
  for(const key of ['linkedEntityIds','linkedThreadIds','linkedChapterIds'])value[key]=key==='linkedEntityIds'?[...recordForm.querySelectorAll(`[name="${key}"]:checked`)].map(input=>input.value):[...(recordDraft.current?.values[key]||[])];
  for(const key of ['showInTimeline','showOnGlobe'])value[key]=fields[key].checked;
  value.latitude=fields.latitude.value;value.longitude=fields.longitude.value;
  value.eventDate=fields.datePrecision.value==='unknown'?'':fields.eventDate.value;
  value.eventStartAt=value.eventDate||null;value.eventEndAt=fields.datePrecision.value==='range'?fields.eventEndAt.value||null:null;
  return value;
}
function configureDates(initial=false){
  const fields=recordForm.elements;
  if(!initial)dateInputs[dateMode]={start:fields.eventDate.value,end:fields.eventEndAt.value};
  dateMode=fields.datePrecision.value;
  const stored=dateInputs[dateMode]||{start:'',end:''};
  fields.eventDate.type=dateMode==='month'?'month':dateMode==='year'?'text':'date';
  if(stored.start&&!/^\d{4}-\d{2}(?:-\d{2})?$/.test(stored.start)&&dateMode!=='year')fields.eventDate.type='text';
  fields.eventDate.value=stored.start||'';fields.eventEndAt.value=stored.end||'';
  fields.eventDate.disabled=dateMode==='unknown';fields.eventEndAt.disabled=dateMode!=='range';
  document.getElementById('event-start-row').hidden=dateMode==='unknown';document.getElementById('event-end-row').hidden=dateMode!=='range';
  fields.eventDate.hidden=dateMode==='year';const select=document.getElementById('event-year');select.hidden=dateMode!=='year';
  const years=new Set(Array.from({length:251},(_,i)=>String(now.getFullYear()-150+i)));if(stored.start)years.add(stored.start);
  select.innerHTML='<option value="">选择年份</option>'+[...years].sort((a,b)=>Number(b)-Number(a)).map(year=>`<option value="${esc(year)}">${esc(year)} 年</option>`).join('');select.value=stored.start||'';
  document.getElementById('date-hint').textContent={month:'只保存月份，不编造某一天',year:'保留原年份与精度',range:'按实际起止日期保存',day:'选择实际事件日期',unknown:'未知日期不编造具体日期'}[dateMode];
}
document.getElementById('event-year').addEventListener('change',event=>{recordForm.elements.eventDate.value=event.target.value;recordDraft.changed();editorDirty=true;});
recordForm.elements.datePrecision.addEventListener('change',()=>{configureDates();recordDraft.changed();});
async function openEditor(record=null,planned=false,options={}){
  if(editorOpening)return;editorOpening=true;
  try{
    if(state.view==='lifegraph')state.graph=await api('/graph');
    recordForm.reset();editorRecord=record;progressTouched=false;
    const initial={recordState:planned?'planned':options.recordState||'occurred',completionState:planned?'planned':options.recordState==='ongoing'?'started':'completed',datePrecision:state.view==='calendar'?'day':'unknown',eventDate:state.view==='calendar'?state.selectedDate:'',showInTimeline:true,showOnGlobe:false,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||'Asia/Shanghai',placePrecision:'city'};
    let value=record||initial;
    {
      const draft=await recordDraft.open(options.draftId?{draftId:options.draftId}:{recordId:record?.id,personId:options.personId,values:record?{}:initial});
      value={...initial,...draft.values};
      if(draft.baseVersion&&!record){try{editorRecord=await api('/records/'+encodeURIComponent(draft.targetId));}catch{editorRecord={id:draft.targetId,version:draft.baseVersion,recordState:value.recordState};}}
    }
    editorPhotos=[...(value.photoUris||[])];editorTags=[...(value.tags||[])];
    const fields=recordForm.elements;
    for(const key of ['title','content','recordState','completionState','placeName','timezone','placePrecision'])fields[key].value=value[key]??initial[key]??'';
    fields.id.value=editorRecord?.id||'';fields.version.value=editorRecord?.version||'';
    fields.datePrecision.value=value.datePrecision||'unknown';dateInputs={[fields.datePrecision.value]:{start:value.eventStartAt??value.eventDate??'',end:value.eventEndAt||''}};configureDates(true);
    const mood=value.mood||'';if(mood&&![...fields.mood.options].some(option=>option.value===mood))fields.mood.add(new Option(mood,mood));fields.mood.value=mood;
    fields.tags.value='';fields.latitude.value=value.latitude??'';fields.longitude.value=value.longitude??'';
    fields.showInTimeline.checked=value.showInTimeline!==false;fields.showOnGlobe.checked=value.showOnGlobe===true;
    fields.recordState.querySelector('[value="recurring"]').hidden=value.recordState!=='recurring';
    const people=state.graph.entities||[];
    document.getElementById('relation-fields').innerHTML=`<fieldset><legend>关联人物</legend>${people.filter(node=>node.type==='person'||(value.linkedEntityIds||[]).includes(node.id)).map(node=>`<label class="checkbox-label"><input type="checkbox" name="linkedEntityIds" value="${esc(node.id)}" ${(value.linkedEntityIds||[]).includes(node.id)?'checked':''}>${esc(node.name)}</label>`).join('')||'<p>暂无人物，可先保存草稿，再去人物页面添加。</p>'}</fieldset>`;
    document.getElementById('editor-title').textContent=editorRecord?'编辑人生记录':'记录这一刻';document.getElementById('record-error').textContent='';
    renderPhotoPreviews();renderTags();editorDirty=false;editor.showModal();if(recordDraft.current)recordDraft.ready();
  }finally{editorOpening=false;}
}
function renderTags(){document.getElementById('editor-tags').innerHTML=editorTags.map((tag,index)=>`<button type="button" class="tag" data-remove-tag="${index}">${esc(tag)} ×</button>`).join('');}
function renderPhotoPreviews(){
  document.getElementById('photo-previews').innerHTML=editorPhotos.map((uri,index)=>`<div class="photo-preview">${localPhoto(uri)?`<img src="${esc(uri)}" alt="待保存照片" data-editor-photo="${index}">`:'<span>原图尚未恢复<br>元信息仍保留</span>'}<button type="button" data-remove-photo="${index}" aria-label="移除第 ${index+1} 张照片">×</button></div>`).join('');
}
async function saveDraftAndClose(){
  if(uploading||savingRecord)return;savingRecord=true;
  const controls=[...recordForm.querySelectorAll('input,textarea,select,button')],prior=controls.map(element=>element.disabled);controls.forEach(element=>element.disabled=true);
  try{if(recordDraft.current)await recordDraft.store();else if(editorDirty)throw new Error('请重新打开草稿后保存。');editorDirty=false;recordDraft.detach();editor.close();await load();}
  finally{savingRecord=false;controls.forEach((element,index)=>element.disabled=prior[index]);}
}
async function closeEditor(){
  if(uploading||savingRecord){toast('正在保存或导入照片，请稍候。');return;}
  if(recordDraft.current&&recordDraft.dirty){await ask({title:'保存草稿后返回？',message:'正式记录尚未改变。可以保存本机草稿稍后继续，或选择放弃本次草稿。',fields:'<button type="button" class="button danger" data-action="discard-record-draft">放弃本次草稿</button>',label:'保存草稿并返回',action:saveDraftAndClose});return;}
  if(editorDirty&&!recordDraft.current&&!globalThis.confirm('仍有未保存的编辑，确认放弃吗？'))return;
  await saveDraftAndClose();
}
recordForm.addEventListener('input',event=>{editorDirty=true;if(event.target.name==='completionState')progressTouched=true;recordDraft.changed();});
recordForm.addEventListener('change',()=>{editorDirty=true;recordDraft.changed();});
recordForm.elements.recordState.addEventListener('change',()=>{if(!editorRecord&&!progressTouched)recordForm.elements.completionState.value={occurred:'completed',ongoing:'started',planned:'planned',recurring:'started'}[recordForm.elements.recordState.value];});
recordForm.addEventListener('submit',async event=>{
  event.preventDefault();if(uploading||savingRecord)return;
  const value=collectRecord();let actualDateConfirmed=false;
  if(editorRecord?.recordState==='planned'&&value.recordState==='occurred'){
    if(value.datePrecision==='unknown'){document.getElementById('record-error').textContent='请补充实际发生日期，再把计划转为已发生。';return;}
    actualDateConfirmed=await ask({title:'确认实际发生日期',message:`这条计划将转为已发生。请确认 ${value.eventDate}${value.eventEndAt?' 至 '+value.eventEndAt:''} 是实际日期。`,label:'确认实际日期',action:async()=>{}});if(!actualDateConfirmed)return;
  }
  savingRecord=true;const controls=[...recordForm.querySelectorAll('input,textarea,select,button')];const prior=controls.map(element=>element.disabled);controls.forEach(element=>element.disabled=true);
  document.getElementById('record-error').textContent='';
  try{
    let result;
    // 收集值发生在禁用前；草稿类的 read 在这里使用固定快照。
    const originalRead=recordDraft.read;recordDraft.read=()=>value;
    try{
      if(recordDraft.current)result=await recordDraft.commit({actualDateConfirmed});
      else throw new Error('请重新打开本机草稿后保存。');
    }finally{recordDraft.read=originalRead;}
    editorDirty=false;editor.close();document.getElementById('detail-dialog').close();currentDetail=null;toast('已保存在本机。');await load();await showDetail(result.id);
  }catch(error){document.getElementById('record-error').textContent=error.message;}
  finally{savingRecord=false;controls.forEach((element,index)=>element.disabled=prior[index]);}
});
document.getElementById('photo-input').addEventListener('change',async event=>{
  const files=[...event.target.files];if(!files.length)return;
  if(editorPhotos.length+files.length>10){toast('每条记录最多 10 张照片，已有照片保持不变。');event.target.value='';return;}
  if(files.some(file=>file.size>50*1024*1024)){toast('单张照片不能超过 50 MB，已有输入保持不变。');event.target.value='';return;}
  uploading=true;const controls=[...recordForm.querySelectorAll('input,textarea,select,button')],disabled=controls.map(element=>element.disabled);controls.forEach(element=>element.disabled=true);
  document.getElementById('record-error').textContent='正在导入原图…';
  try{const form=new FormData();files.forEach(file=>form.append('photos',file));const result=await api('/photos/batch',{method:'POST',body:form});editorPhotos.push(...result.photos.map(photo=>photo.uri));editorDirty=true;renderPhotoPreviews();document.getElementById('record-error').textContent='';}
  catch(error){document.getElementById('record-error').textContent=error.message;}
  finally{uploading=false;controls.forEach((element,index)=>element.disabled=disabled[index]);event.target.value='';if(recordDraft.current)recordDraft.changed();}
});
async function showDetail(id){
  try{
    const record=await api(`/records/${encodeURIComponent(id)}`);
    if(state.view==='lifegraph')state.graph=await api('/graph');currentDetail=record;
    const links=[];
    for(const [kind,field] of Object.entries({entities:'linkedEntityIds',threads:'linkedThreadIds',chapters:'linkedChapterIds'})){
      for(const node of state.graph[kind])if(record[field]?.includes(node.id))links.push(node.name);
    }
    document.getElementById('detail-content').innerHTML=`<header class="detail-heading"><button class="icon-button close-detail" data-close="detail-dialog" aria-label="关闭详情">${icon('close')}</button><div class="record-top"><span class="record-place">${icon('pin')}${esc(record.placeName||'生活里的某个角落')}</span><span class="record-state state-${esc(record.recordState)}">${stateLabels[record.recordState]}</span></div><h2 id="detail-title">${esc(record.title||'一段未命名的时光')}</h2><div class="detail-date">${esc(dateLabel(record.eventDate))}${record.eventEndAt?` — ${esc(dateLabel(record.eventEndAt))}`:''} · ${esc(record.mood||'一段属于你的生活')}</div></header><div class="detail-body"><div class="detail-text">${esc(record.content)}</div><div class="detail-photos">${(record.photoUris||[]).map(uri=>localPhoto(uri)?`<img src="${esc(uri)}" alt="记忆中的照片" data-detail-photo="${(record.photoUris||[]).indexOf(uri)}">`:'<div class="photo-unavailable">原端照片仅保留引用，需在编辑时重新上传。</div>').join('')}</div><div class="record-meta">${(record.tags||[]).map(tag=>`<span class="tag"># ${esc(tag)}</span>`).join('')}</div><div class="detail-relations">${record.linkedEntityIds?.map(id=>{const person=state.graph.entities.find(node=>node.id===id);return person?`<button class="button small" data-person="${esc(id)}">${esc(person.name)}</button>`:'';}).join('')||''}</div></div><footer class="dialog-footer"><button class="button subtle" data-action="view-lifegraph">${icon('thread')}在脉络中查看</button>${`<button class="button subtle danger" data-action="delete-record">${icon('trash')}删除</button><button class="button primary" data-action="edit-record">${icon('edit')}编辑这段时光</button>`}</footer>`;
    document.getElementById('detail-dialog').showModal();
  }catch(error){toast(error.message);}
}
const nodeForm=document.getElementById('node-form'),nodeDialog=document.getElementById('node-dialog');
const personDraft=new DraftSession('person',()=>Object.fromEntries(new FormData(nodeForm)),value=>{document.getElementById('person-draft-status').textContent=value;});
let savingPerson=false,nodeDirty=false;
async function openNode(kind,node=null,options={}){
  nodeForm.reset();let value=node||{};personDraft.detach();
  if(kind==='entities'&&(!node||node.type==='person')){const draft=await personDraft.open(options.draftId?{draftId:options.draftId}:{personId:node?.id});value=draft.values;}
  nodeForm.elements.kind.value=kind;nodeForm.elements.id.value=node?.id||'';
  for(const key of ['name','summary','startDate','endDate'])nodeForm.elements[key].value=value[key]||'';
  nodeForm.elements.type.value=value.type||'person';nodeForm.elements.status.value=value.status||'active';

  document.getElementById('node-title').textContent='人物资料';
  document.getElementById('node-error').textContent='';nodeDirty=false;nodeDialog.showModal();if(personDraft.current)personDraft.ready();
}
async function savePersonAndClose(){
  if(savingPerson)return;const values=Object.fromEntries(new FormData(nodeForm));savingPerson=true;
  const controls=[...nodeForm.querySelectorAll('input,textarea,select,button')],prior=controls.map(element=>element.disabled),read=personDraft.read;controls.forEach(element=>element.disabled=true);personDraft.read=()=>values;
  try{if(personDraft.current)await personDraft.store();else if(nodeDirty)throw new Error('请先正式保存人物资料。');personDraft.detach();nodeDirty=false;nodeDialog.close();await load();}
  finally{personDraft.read=read;savingPerson=false;controls.forEach((element,index)=>element.disabled=prior[index]);}
}
async function closeNode(){if(savingPerson)return;if(personDraft.current&&personDraft.dirty){await ask({title:'保存人物草稿后返回？',message:'人物草稿独立保存在本机，不进入正式人物数量或云同步。',fields:'<button type="button" class="button danger" data-action="discard-person-draft">放弃人物草稿</button>',label:'保存草稿并返回',action:savePersonAndClose});return;}await savePersonAndClose();}
nodeForm.addEventListener('input',()=>{nodeDirty=true;personDraft.changed();});nodeForm.addEventListener('change',()=>{nodeDirty=true;personDraft.changed();});
nodeDialog.addEventListener('cancel',event=>{event.preventDefault();closeNode().catch(error=>toast(error.message));});
nodeForm.addEventListener('submit',async event=>{
  event.preventDefault();if(savingPerson)return;savingPerson=true;
  const values=Object.fromEntries(new FormData(nodeForm)),controls=[...nodeForm.querySelectorAll('input,textarea,select,button')],prior=controls.map(element=>element.disabled);controls.forEach(element=>element.disabled=true);
  try{
    if(personDraft.current){const read=personDraft.read;personDraft.read=()=>values;try{await personDraft.commit();}finally{personDraft.read=read;}}
    else{const {kind,id}=values,previous=state.graph[kind].find(item=>item.id===id)||{};await api(`/graph/${kind}${id?'/'+encodeURIComponent(id):''}`,{method:id?'PUT':'POST',json:{...previous,...values}});}
    nodeDialog.close();nodeDirty=false;toast('人物资料已保存在本机。');await load();
  }catch(error){document.getElementById('node-error').textContent=error.message;}
  finally{savingPerson=false;controls.forEach((element,index)=>element.disabled=prior[index]);}
});

/* 归档下载之前展示范围；导入预览保留在内存，确认后才提交。 */
async function exportArchive(){await ask({title:'导出普通 JSON',message:'普通 JSON 包含记录、人物与关系、删除标记和照片元信息，不包含原图文件。导出只在本机执行。',label:'下载 JSON',action:async()=>{const data=await api('/archive/export');const url=URL.createObjectURL(new Blob([JSON.stringify(data)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=`everhere-${today()}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}});}
function showImportPreview(data){
  pendingPreview=data;const preview=document.getElementById('import-preview');preview.hidden=false;
  preview.innerHTML=`<h3>恢复预览 · 尚未写入</h3><dl><dt>新增记录</dt><dd>${data.newRecords}</dd><dt>重复记录</dt><dd>${data.skippedRecords}</dd><dt>同 ID / 草稿冲突</dt><dd>${data.conflicts?.length||0}</dd><dt>人物 / 线索 / 阶段</dt><dd>${data.entities} / ${data.threads} / ${data.chapters}</dd><dt>提醒元信息（不启动通知）</dt><dd>${data.reminders||0}</dd><dt>照片元信息</dt><dd>${data.photoCount||0}</dd></dl>${data.missingOriginals?.length?`<p class="warning">这份 JSON 不包含 ${data.missingOriginals.length} 张原图，恢复后保留元信息和缺图提示。</p><label class="checkbox-label"><input id="accept-missing" type="checkbox">我明确接受本次缺图恢复</label>`:''}${data.conflicts?.length?'<label class="checkbox-label"><input id="copy-conflicts" type="checkbox">对冲突保留两份，原记录、草稿和墓碑不覆盖</label>':''}<label class="checkbox-label"><input id="restore-confirmed" type="checkbox">确认只将以上范围恢复到当前本机空间，不上传云端</label><p id="restore-error" class="form-error" role="alert"></p><button class="button primary" data-action="confirm-import">确认恢复到本机</button><button class="button subtle" data-action="refresh-import">重新预览</button><button class="button subtle danger" data-action="discard-import">放弃本次暂存</button>`;
}
async function previewImport(file){
  const preview=document.getElementById('import-preview');preview.hidden=false;preview.textContent='正在检查归档条目和原图…';pendingPreview=null;
  try{if(file.size>128*1024*1024)throw new Error('Web 单次归档上限为 128 MB。');const form=new FormData();form.append('archive',file);showImportPreview(await api('/archive/files/preview',{method:'POST',body:form}));}
  catch(error){preview.textContent=error.message;}
}

function replaceRecordFilters(values){
  // 首页统计和年份入口发起新的筛选；普通视图切换保留原条件。
  state.filters={...values};state.q='';document.getElementById('search').value='';
  for(const element of document.getElementById('filters').elements){
    if(element.name)element.value=state.filters[element.name]||'';
  }
}

const actions={
  'view-lifegraph':async()=>{if(!currentDetail)return;state.lifegraphFocus='record:'+currentDetail.id;document.getElementById('detail-dialog').close();await navigate('lifegraph');},
  'save-record-draft':saveDraftAndClose,'save-person-draft':savePersonAndClose,
  'discard-record-draft':async()=>{if(uploading||savingRecord)return;if(recordDraft.current)await recordDraft.discard();editorDirty=false;editor.close();document.getElementById('confirm-dialog').close();await load();},
  'discard-person-draft':async()=>{if(savingPerson)return;if(personDraft.current)await personDraft.discard();nodeDirty=false;nodeDialog.close();document.getElementById('confirm-dialog').close();await load();},
  'add-tag':()=>{const field=recordForm.elements.tags,tag=field.value.trim();if(tag&&!editorTags.includes(tag))editorTags.push(tag);field.value='';renderTags();editorDirty=true;recordDraft.changed();},
  'person-record':()=>openEditor(null,false,{personId:state.personId}),
  new:()=>document.getElementById('creation-dialog').showModal(), 'new-plan':()=>openEditor(null,true), retry:load,
  'year-places':async()=>{replaceRecordFilters({from:`${state.homeYear}-01-01`,to:`${state.homeYear}-12-31`});await navigate('places');},
  'calendar-today':()=>{const day=new Date();state.calendarYear=day.getFullYear();state.calendarMonth=day.getMonth();state.selectedDate=today();render();},
  'clear-focus':async()=>{delete state.filters.node;delete state.filters.kind;state.place=null;await load();},
  'edit-record':()=>{document.getElementById('detail-dialog').close();openEditor(currentDetail);},
  'delete-record':async()=>{
    const record=currentDetail;if(!record)return;
    await ask({title:'删除这段记忆？',message:'记录将移入本机回收站，原图和关联保留，可按原 ID 恢复。',label:'确认删除',action:async()=>{await api(`/records/${encodeURIComponent(record.id)}`,{method:'DELETE',json:{version:record.version}});document.getElementById('detail-dialog').close();currentDetail=null;toast('记录已删除。');await load();}});
  },
  export:exportArchive,
  'cloud-status':async()=>{const value=await api('/cloud/status');
    if(value.configured&&!value.loggedIn){await ask({title:'登录共同云账号',message:'使用与安卓版相同区域的账号。登录只验证身份，不上传或下载人生资料。',fields:'<label>云账号邮箱<input name="email" type="email" required autocomplete="username"></label><label>云账号密码<input name="password" type="password" required maxlength="128" autocomplete="current-password"></label>',label:'只登录账号',action:async fields=>{await api('/cloud/login',{method:'POST',json:fields});toast('云账号已登录，资料仍仅保存在本机。');}});return;}
    await ask({title:'本机资料与云账号',message:value.reason||(value.loggedIn?'云账号已登录，资料仍只保存在本机；范围许可未接通，尚不能执行云同步。':'共同云服务尚未配置。默认只保存本机资料，登录不会上传记录。'),label:'知道了',action:async()=>{}});},
  'confirm-import':async()=>{
    if(!pendingPreview)return;const button=content.querySelector('[data-action="confirm-import"]');button.disabled=true;
    const values={confirmed:!!document.getElementById('restore-confirmed')?.checked,acceptMissingPhotos:!!document.getElementById('accept-missing')?.checked,copyConflicts:!!document.getElementById('copy-conflicts')?.checked};
    try{const result=await api('/archive/jobs/'+encodeURIComponent(pendingPreview.id)+'/confirm',{method:'POST',json:values});pendingPreview=null;toast(`已恢复 ${result.newRecords} 条记录，保留 ${result.skippedRecords} 条重复记录。`);await load();}
    catch(error){document.getElementById('restore-error').textContent=error.message;}
    finally{if(button.isConnected)button.disabled=false;}
  },
  'zip-export':async()=>{await ask({title:'导出含原图 ZIP',message:'将导出当前空间的普通记录、关系、删除标记和原图。原图未恢复或校验不符时停止，不生成不完整 ZIP。本机导出不连接云端。',label:'检查并下载 ZIP',action:async()=>{await downloadFile('/archive/export.zip',`everhere-${today()}.zip`);}});},
  'archive-jobs':async()=>{const data=await api('/archive/jobs');document.getElementById('archive-jobs').innerHTML=data.jobs.length?data.jobs.map(job=>`<p>${job.kind.toUpperCase()} · ${job.total} 条记录 · ${esc(job.createdAt)} <button class="text-button" data-archive-job="${esc(job.id)}">继续预览</button></p>`).join(''):'<p>暂无未完成的本机恢复。</p>';},
  'refresh-import':async()=>{if(pendingPreview)showImportPreview(await api('/archive/jobs/'+encodeURIComponent(pendingPreview.id)+'/refresh',{method:'POST',json:{}}));},
  'discard-import':async()=>{if(!pendingPreview)return;await api('/archive/jobs/'+encodeURIComponent(pendingPreview.id),{method:'DELETE',json:{}});pendingPreview=null;document.getElementById('import-preview').hidden=true;toast('本次加密暂存已删除，原始文件和正式资料不变。');},
  logout:async()=>{await api('/cloud/logout',{method:'POST',json:{}});location.assign('/');},

};
document.addEventListener('click',async event=>{
  const target=event.target.closest('button,[data-record][role="button"]');if(!target)return;
  try{
    if(target.dataset.close){if(target.dataset.close==='editor-dialog')await closeEditor();else if(target.dataset.close==='node-dialog')await closeNode();else document.getElementById(target.dataset.close).close();}
    else if(target.dataset.view)await navigate(target.dataset.view);
    else if(target.dataset.graphFocus){state.lifegraphFocus=target.dataset.graphFocus;await navigate('lifegraph');}
    else if(target.dataset.switch)await navigate(target.dataset.switch);
    else if(target.dataset.homeAll){state.allQuery={filters:{},q:''};await navigate('all');}
    else if(target.dataset.homeState){state.allQuery={filters:{state:target.dataset.homeState},q:''};await navigate('all');}
    else if(target.dataset.homeYear){state.homeYear=Math.min(9998,Math.max(1000,state.homeYear+Number(target.dataset.homeYear)));render();}
    else if(target.dataset.record)await showDetail(target.dataset.record);
    else if(target.dataset.action){if(target.dataset.action.startsWith('node-'))openNode(target.dataset.action.slice(5));else await actions[target.dataset.action]?.();}
    else if(target.dataset.newNode)await openNode(target.dataset.newNode);
    else if(target.dataset.editNode)await openNode(target.dataset.kind,state.graph[target.dataset.kind].find(node=>node.id===target.dataset.editNode));
    else if(target.dataset.deleteNode){const {kind,deleteNode:id}=target.dataset;await ask({title:'删除这份关联资料？',message:'只移除对象及其关联，人生记录会完整保留。',label:'确认删除',action:async()=>{await api(`/graph/${kind}/${encodeURIComponent(id)}`,{method:'DELETE',json:{version:state.graph[kind].find(node=>node.id===id)?.version}});toast('已删除人物，相关记录和原图仍然保留。');await load();}});}
    else if(target.dataset.focusNode){if(target.dataset.kind==='entities'&&state.graph.entities.find(node=>node.id===target.dataset.focusNode)?.type==='person'){state.personId=target.dataset.focusNode;await navigate('person');}else{state.filters.node=target.dataset.focusNode;state.filters.kind=target.dataset.kind;await navigate('all');}}
    else if(target.dataset.date){state.selectedDate=target.dataset.date;writeRoute();render();}
    else if(target.dataset.month){const date=new Date(state.calendarYear,state.calendarMonth+Number(target.dataset.month),1);state.calendarYear=date.getFullYear();state.calendarMonth=date.getMonth();writeRoute();render();}
    else if(target.dataset.tag){state.filters.tag=target.dataset.tag;document.getElementById('filters').elements.tag.value=target.dataset.tag;await load();}
    else if(target.dataset.place){state.place=target.dataset.place;state.view='timeline';updateNav();render();}
    else if(target.dataset.removePhoto!==undefined){editorPhotos.splice(Number(target.dataset.removePhoto),1);editorDirty=true;renderPhotoPreviews();recordDraft.changed();}
    else if(target.dataset.removeTag!==undefined){editorTags.splice(Number(target.dataset.removeTag),1);editorDirty=true;renderTags();recordDraft.changed();}
    else if(target.dataset.archiveJob){showImportPreview(await api('/archive/jobs/'+encodeURIComponent(target.dataset.archiveJob)));}
    else if(target.dataset.createState){document.getElementById('creation-dialog').close();await openEditor(null,target.dataset.createState==='planned',{recordState:target.dataset.createState,personId:state.view==='person'?state.personId:undefined});}
    else if(target.dataset.person){state.personId=target.dataset.person;await navigate('person');}
    else if(target.dataset.resumeDraft){const draft=state.drafts.find(item=>item.id===target.dataset.resumeDraft);if(draft?.kind==='person')await openNode('entities',null,{draftId:draft.id});else await openEditor(null,false,{draftId:target.dataset.resumeDraft});}
    else if(target.dataset.discardDraft){await ask({title:'放弃这份本机草稿？',message:'只删除这份未提交的草稿，正式记录和原始备份文件保留。',label:'放弃草稿',action:async()=>{await api('/drafts/'+encodeURIComponent(target.dataset.discardDraft),{method:'DELETE',json:{version:Number(target.dataset.version)}});await load();}});}
    else if(target.dataset.restore){await api('/records/'+encodeURIComponent(target.dataset.restore)+'/restore',{method:'POST',json:{version:Number(target.dataset.version)}});toast('已按原 ID 恢复记录、关系与照片。');await load();}
    else if(target.dataset.theme){state.theme=target.dataset.theme;document.documentElement.dataset.theme=state.theme;try{localStorage.setItem('everhere-theme',state.theme);}catch{toast('主题已应用，当前浏览器无法保存外观偏好。');}render();}
  }catch(error){toast(error.message);}
});
document.addEventListener('keydown',event=>{if(event.target.matches('[data-record][role="button"]')&&['Enter',' '].includes(event.key)){event.preventDefault();event.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
document.addEventListener('change',event=>{if(event.target.id==='calendar-jump'&&event.target.value){const [year,month]=event.target.value.split('-').map(Number);state.calendarYear=year;state.calendarMonth=month-1;writeRoute();render();}if(event.target.id==='import-file'&&event.target.files[0])previewImport(event.target.files[0]);});
document.addEventListener('error',event=>{if(event.target instanceof HTMLImageElement&&event.target.id!=='full-photo'&&localPhoto(event.target.getAttribute('src'))){const replacement=document.createElement('span');replacement.className='photo-unavailable';replacement.textContent='照片引用不可用，请重新上传。';event.target.replaceWith(replacement);}},true);
document.getElementById('new-record').addEventListener('click',()=>actions.new());
document.getElementById('profile-button').addEventListener('click',()=>navigate('mine'));
document.getElementById('settings-button').addEventListener('click',()=>navigate('mine'));
document.getElementById('filter-toggle').addEventListener('click',()=>{const form=document.getElementById('filters');form.hidden=!form.hidden;document.getElementById('filter-toggle').setAttribute('aria-expanded',String(!form.hidden));});
document.getElementById('filters').addEventListener('submit',async event=>{event.preventDefault();const form=new FormData(event.currentTarget),values=Object.fromEntries(form);values.people=form.getAll('people').join(',');state.filters={...(state.filters.node?{node:state.filters.node,kind:state.filters.kind}:{}),...Object.fromEntries(Object.entries(values).filter(([,value])=>value))};writeRoute();await load();});
document.getElementById('filters').addEventListener('reset',()=>{state.filters={};state.place=null;setTimeout(()=>{writeRoute();load();},0);});
let searchTimer,peopleTimer;
document.addEventListener('input',event=>{if(event.target.id!=='people-search')return;state.personSearch=event.target.value;clearTimeout(peopleTimer);peopleTimer=setTimeout(()=>{const value=state.personSearch;render();const input=document.getElementById('people-search');input?.focus();input?.setSelectionRange(value.length,value.length);},250);});
document.getElementById('search').addEventListener('input',event=>{clearTimeout(searchTimer);const value=event.target.value;searchTimer=setTimeout(()=>{state.q=value.trim();writeRoute(true);load();},300);});
function closeMenu(){document.getElementById('sidebar').classList.remove('is-open');document.getElementById('sidebar-shade').hidden=true;document.getElementById('menu-button').setAttribute('aria-expanded','false');}
document.getElementById('menu-button').addEventListener('click',()=>{document.getElementById('sidebar').classList.add('is-open');document.getElementById('sidebar-shade').hidden=false;document.getElementById('menu-button').setAttribute('aria-expanded','true');});
document.getElementById('sidebar-shade').addEventListener('click',closeMenu);
editor.addEventListener('cancel',event=>{event.preventDefault();closeEditor().catch(error=>toast(error.message));});
document.addEventListener('visibilitychange',()=>{if(document.hidden){if(editor.open&&recordDraft.current)recordDraft.store().catch(()=>{});if(nodeDialog.open&&personDraft.current)personDraft.store().catch(()=>{});}});
document.addEventListener('click',event=>{const image=event.target.closest('[data-detail-photo],[data-editor-photo]');if(!image)return;openGallery(image.dataset.detailPhoto!==undefined?currentDetail?.photoUris||[]:editorPhotos,Number(image.dataset.detailPhoto??image.dataset.editorPhoto));});
window.addEventListener('beforeunload',event=>{if((editor.open&&(recordDraft.current?recordDraft.dirty:editorDirty))||(nodeDialog.open&&(personDraft.current?personDraft.dirty:nodeDirty))||uploading||savingRecord||savingPerson){event.preventDefault();event.returnValue='';}});
try{
  try{const theme=localStorage.getItem('everhere-theme');state.theme=theme==='FOREST'?'FOREST':'WARM';}catch{}document.documentElement.dataset.theme=state.theme;restoreRoute();
  const session=await getSession();state.cloudAccount=!!session.user;state.user=session.user||{name:'本机档案',email:'本机资料空间 · 云同步默认关闭'};state.region=session.region||'cn';updateNav();await load();
}catch(error){content.innerHTML=`<div class="error-state">${esc(error.message)}<br><button class="button small" data-action="retry">重新加载</button></div>`;}
