import {t,h,m,locale} from './i18n.js';
/* 各视图只消费共享状态，不保存独立记录副本。 */
import {icon,esc,today,dateLabel,localPhoto,stateLabels,moodLabel} from './ui.js';
import {onDay,inMonth} from './record-date.js';

export const empty = (title,message,action='new',label=t('写下第一段故事'),symbol='book') => `<div class="empty-state"><i>${icon(symbol)}</i><h3>${esc(title)}</h3><p>${esc(message)}</p>${action?`<button class="button" data-action="${esc(action)}">${icon('plus')}${esc(label)}</button>`:''}</div>`;
export function card(record) {
  const photos=(record.photoUris||[]).filter(localPhoto).slice(0,3);
  return `<button class="record-card" data-record="${esc(record.id)}">
    ${photos.length?`<div class="record-photos">${photos.map(uri=>h`<img loading="lazy" src="${esc(uri)}" alt="记录中的照片">`).join('')}</div>`:''}
    <div class="record-title-row"><h3>${esc(record.title||t('一段未命名的时光'))}</h3><time>${esc(dateLabel(record.eventDate,{year:undefined}))}</time></div>
    <div class="record-top"><span class="record-state state-${esc(record.recordState)}">${stateLabels[record.recordState]}</span></div>
    <div class="record-place">${icon('pin')}${esc(record.placeName||t('地点待补充'))}</div>
    <p class="record-excerpt">${esc(record.content)}</p>
    <div class="record-meta">${(record.tags||[]).slice(0,4).map(tag=>`<span class="tag"># ${esc(tag)}</span>`).join('')}${record.mood?`<span class="mood">${icon('smile')}${esc(moodLabel(record.mood))}</span>`:''}${photos.length?h`<span class="photo-count">${record.photoUris.length} 张照片</span>`:''}</div>
  </button>`;
}

/* 首页直接参照原端 Index.ets：日落头图、时间弧线、三项概览和轻量入口。 */
export function home(records,state) {
  const ongoing=records.filter(record=>record.recordState==='ongoing');
  const plans=records.filter(record=>record.recordState==='planned'&&!['completed','cancelled'].includes(record.completionState))
    .sort((a,b)=>(a.eventDate||'9999').localeCompare(b.eventDate||'9999'));
  const recent=[...records].sort((a,b)=>{const left=BigInt(a.androidDocument?.updatedAt||String(Date.parse(a.updatedAt)||0)),right=BigInt(b.androidDocument?.updatedAt||String(Date.parse(b.updatedAt)||0));return left>right?-1:left<right?1:0;}).slice(0,3);
  const shortcuts=[['timeline',t('时间轴'),'icon_timeline_brown.svg'],['calendar',t('日历'),'icon_calendar_brown.svg'],['places',t('地点'),'icon_globe_brown.svg'],['all',t('全部记录'),'icon_threads_brown.svg'],['entities',t('人物'),'icon_person_brown.svg']];
  return h`<div class="native-home">
    <section class="life-hero" aria-label="我的人生概览">
      <div class="life-hero-top"><p>过去，现在和未来，<br class="hero-mobile-break">都是我的人生</p><button data-view="mine" class="hero-account">账户 ${icon('chevron')}</button></div>
      <div class="life-arc"><img src="/static/images/mobile/home_timeline_arc.svg" alt="连接过去、现在和未来的时间弧线"><div><button data-home-state="occurred">过去</button><button data-home-state="ongoing">现在</button><button data-home-state="planned">未来</button></div></div>
      <div class="life-overview"><button data-home-all="true"><b id="stat-total">${records.length}</b><span>人生记录</span></button><button data-home-state="ongoing"><b>${ongoing.length}</b><span>进行中</span></button><button data-home-state="planned"><b>${plans.length}</b><span>未来计划</span></button></div>
    </section>
    <div class="home-body">
      <div class="home-main-column">
        <section class="create-life-card"><div class="create-life-heading"><span class="album-letter">A</span><div><h2>记录一段人生</h2><p>重要的事情随时留下</p></div><button class="round-add" data-action="new" aria-label="新增人生记录">${icon('plus')}</button></div><button id="hero-write" class="button primary" data-action="new">新建人生记录</button></section>
        <section class="home-browse"><h2>浏览我的人生</h2><div class="home-shortcuts">${shortcuts.map(([view,label,asset])=>`<button data-view="${view}"><img src="/static/images/mobile/${asset}" alt=""><span>${label}</span></button>`).join('')}</div></section>
        <section class="home-tools"><h2>人生工具</h2><div><button data-view="upcoming">${icon('sun')}未来计划</button><button data-view="drafts">${icon('edit')}本机草稿 ${state.drafts.length}</button><button data-view="trash">${icon('trash')}回收站</button></div></section>
        <section class="home-recent"><header class="home-section-heading"><h2>最近编辑</h2><button class="text-button" data-view="all">查看全部 ${icon('chevron')}</button></header><div class="home-recent-records">${recent.length?recent.map(card).join(''):empty(t('你的人生还没有被写下来'),t('先留下第一段记忆吧。'),'new',t('记录一段人生'),'book')}</div></section>
      </div>
      <aside class="home-side-column">
        <section class="year-memory-card"><div><span>回看一段时光</span><h2>${esc(t('{year} 年的人生记忆',{year:state.homeYear}))}</h2></div><div class="year-controls"><button data-home-year="-1" aria-label="上一年">‹</button><span>${state.homeYear}</span><button data-home-year="1" aria-label="下一年">›</button></div><button class="text-button" data-action="year-places">${icon('globe')}查看这一年的地点 ${icon('chevron')}</button></section>
        <section class="home-plan-card"><header class="home-section-heading"><h2>未来计划</h2><button data-view="upcoming" class="text-button">全部 ${icon('chevron')}</button></header>${plans.length?plans.slice(0,2).map(record=>h`<button class="native-plan" data-record="${esc(record.id)}"><div><b>${esc(record.title||t('一份未来计划'))}</b><small>${esc(dateLabel(record.eventDate))}${record.placeName?` · ${esc(record.placeName)}`:''}</small></div><span class="record-state state-planned">计划中</span></button>`).join(''):h('<p class="home-empty-note">还没有未来计划，给未来留一点期待。</p><button class="text-button" data-action="new-plan">记下一份计划 +</button>')}</section>
        ${ongoing.length?h`<section class="home-ongoing-card"><header class="home-section-heading"><h2>正在经历</h2>${icon('thread')}</header>${ongoing.slice(0,2).map(record=>`<button class="native-plan" data-record="${esc(record.id)}"><div><b>${esc(record.title||t('一段正在经历的生活'))}</b><small>${esc(record.content.slice(0,55)||t('慢慢来，每一次尝试都有意义。'))}</small></div>${icon('chevron')}</button>`).join('')}</section>`:''}
        <section class="home-privacy-card">${icon('shield')}<div><h3>只属于你的生命档案</h3><p>不用每天记录，重要的事情随时留下。<br>记录仅自己可见，回忆录素材由你选择。</p></div><button data-view="mine" class="text-button">管理我的资料 ${icon('chevron')}</button></section>
      </aside>
    </div>
  </div>`;
}

/* 账户页只连接 F1—F4 的资料、稿件和订单。 */
export function mine(state) {
  const row=(view,title,description,symbol)=>`<button class="mine-row" data-view="${view}"><span class="mine-row-icon">${icon(symbol)}</span><span><b>${title}</b><small>${description}</small></span>${icon('chevron')}</button>`;
  return h`<div class="mine-page"><section class="mine-account"><span class="mine-avatar">${esc(state.user.name.slice(0,1))}</span><div><h2>${esc(state.user.name)}</h2><p>${esc(state.user.email)}</p><span class="account-connected">${icon('shield')}资料仅自己可见</span></div><a class="button account-button" href="/workspace#account">网站账户</a></section><div class="mine-groups"><section><h2>我的人生资料</h2>${row('all',t('全部记录'),t('浏览自己的文字与照片'),'list')}${row('entities',t('人物'),t('姓名、意义和一起经历的事情'),'people')}${row('drafts',t('本机草稿'),state.drafts.length+t(' 份尚未正式提交的记录 / 人物草稿'),'edit')}${row('trash',t('回收站'),t('恢复原 ID、关系和照片'),'trash')}</section><section><h2>回忆与纪念</h2><p><a class="button" href="/workspace#memoirs">我的回忆录</a></p><p><a class="button" href="/workspace#shop">文创商城</a></p><p><a class="button" href="/workspace#orders">我的订单</a></p>${row('about',t('关于与帮助'),t('资料保存和功能范围'),'shield')}</section></div></div>`;
}
export function timeline(records, state) {
  const filtered=records.filter(record=>record.showInTimeline!==false);
  const upcoming=state.allRecords.filter(record=>record.recordState==='planned'&&!['cancelled','completed'].includes(record.completionState)).sort((a,b)=>(a.eventDate||'9999').localeCompare(b.eventDate||'9999')).slice(0,2);
  const tags=[...new Set(state.allRecords.flatMap(record=>record.tags||[]))].slice(0,10);
  let lastMonth='';
  const rows=filtered.map(record=>{
    const period=/^([+-]?[0-9]{1,10})(?:-([0-9]{2}))?/.exec(record.eventDate||'');
    const month=period?(period[1]+(period[2]?'-'+period[2]:'')):t('日期未详');
    const heading=month===lastMonth?'':`<div class="timeline-month"><strong>${esc(period?dateLabel(month):t('日期未详'))}</strong></div>`;
    lastMonth=month;
    const exactDay=['day','range'].includes(record.datePrecision)&&/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(record.eventDate||'');
    const day=exactDay?record.eventDate.slice(8,10):'·';
    const weekday=exactDay?new Date(`${record.eventDate}T12:00:00`).toLocaleDateString(locale(),{weekday:'short'}):({year:t('按年记录'),month:t('按月记录'),unknown:t('日期未详')}[record.datePrecision]||t('原始日期'));
    return `${heading}<div class="timeline-entry"><div class="timeline-date"><b>${day}</b><small>${weekday}</small></div>${card(record)}</div>`;
  }).join('');
  return h`<div class="content-grid"><section class="timeline"><h2 class="section-caption"><span class="caption-dot"></span>生活的片段<small>${filtered.length} 段记忆，慢慢收藏</small></h2>${rows||empty(t('故事，从这一页开始'),t('随手记下一句话，也是一段值得珍藏的生活。'))}</section><aside class="right-rail"><section class="rail-card"><h3 class="rail-heading"><span>未来，慢慢来</span>${icon('sun')}</h3>${upcoming.length?upcoming.map(record=>`<button class="upcoming-item" data-record="${esc(record.id)}"><span class="record-state state-planned">${esc(dateLabel(record.eventDate,{year:undefined}))}</span><b>${esc(record.title||t('未来的一段时光'))}</b><small>${esc(record.placeName||t('带着期待出发'))}</small></button>`).join(''):h('<p class="empty-note">留一些空白，给还没发生的美好。</p>')}</section><section class="rail-card"><h3 class="rail-heading">生活的关键词${icon('filter')}</h3><div class="tag-cloud">${tags.length?tags.map(tag=>`<button data-tag="${esc(tag)}"># ${esc(tag)}</button>`).join(''):h('<p class="empty-note">记录时添加标签，让回忆更好找。</p>')}</div></section><section class="quote-card"><i>${icon('sprout')}</i><p>把日子过成诗，<br>把回忆酿成光。</p><small>MAKE ROOM FOR THE LITTLE THINGS</small></section></aside></div>`;
}

export function calendar(records,state) {
  const first=new Date(state.calendarYear,state.calendarMonth,1);
  const count=new Date(state.calendarYear,state.calendarMonth+1,0).getDate();
  const offset=(first.getDay()+6)%7;
  const dayKey=day=>`${state.calendarYear}-${String(state.calendarMonth+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
  const onDate=value=>records.filter(record=>onDay(record,value));
  let days='<span></span>'.repeat(offset);
  for(let day=1;day<=count;day++){
    const key=dayKey(day),items=onDate(key);
    days+=h`<button class="calendar-day ${key===today()?'today':''} ${key===state.selectedDate?'selected':''}" data-date="${key}" aria-label="${key}，${items.length} 条记录" aria-pressed="${key===state.selectedDate}"><b>${day}</b>${items.length?h`<span class="day-dots">${items.slice(0,3).map(record=>`<i class="${record.recordState==='planned'?'planned':''}"></i>`).join('')}</span><small>${items.length} 段时光</small>`:''}</button>`;
  }
  const selected=onDate(state.selectedDate);
  const coarse=records.filter(record=>['month','year','unknown'].includes(record.datePrecision)&&(record.datePrecision==='unknown'||inMonth(record,state.calendarYear,state.calendarMonth+1)));
  const monthKey=`${state.calendarYear}-${String(state.calendarMonth+1).padStart(2,'0')}`;
  return h`<div class="calendar-layout"><section class="calendar-panel"><header class="calendar-heading"><h2>${esc(dateLabel(monthKey))}</h2><label>跳至月份<input id="calendar-jump" type="month" value="${monthKey}" aria-label="选择日历月份"></label><div><button class="icon-button" data-month="-1" aria-label="上个月">←</button><button class="button small subtle" data-action="calendar-today">今天</button><button class="icon-button" data-month="1" aria-label="下个月">→</button></div></header><div class="calendar-week">${Array.from({length:7},(_,index)=>`<span>${new Intl.DateTimeFormat(locale(),{weekday:'short'}).format(new Date(2024,0,index+1))}</span>`).join('')}</div><div class="calendar-days">${days}</div></section><aside class="calendar-aside"><h3 class="section-caption">${esc(dateLabel(state.selectedDate))}<small>${selected.length} 条记录</small></h3>${selected.length?selected.map(card).join(''):empty(t('这一天，留一点空白'),t('可以补录，也可以等待下一次想写的时候。'),'new',t('记录这一天'),'calendar')}${coarse.length?h`<section class="coarse-dates"><h3>按年 / 月记录与未知日期</h3><p>保留原精度，不在某一天画标记。</p>${coarse.map(card).join('')}</section>`:''}</aside></div>`;
}

export function places(records,state) {
  const groups=new Map();
  for(const record of records){
    const key=record.placeName?.trim()||`${record.latitude}, ${record.longitude}`;
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(record);
  }
  if(!groups.size)return empty(t('还没有地点记录'),t('为记录填写地点名称，就能在这里回看。'),'new',t('记录一个地点'),'pin');
  return h`<p class="draft-notice">按地点回看同一份人生记录，无需填写坐标。</p><div class="place-list">${[...groups].map(([name,items])=>h`<section class="settings-card"><h2>${esc(name)}</h2><small>${items.length} 条记录</small>${items.map(card).join('')}</section>`).join('')}</div>`;
}

export function nodes(kind,state) {
  const items=(state.graph.entities||[]).filter(node=>node.type==='person').filter(node=>!state.personSearch||[node.name,node.summary||''].some(text=>text.toLocaleLowerCase().includes(state.personSearch.toLocaleLowerCase())));
  return h`<div class="section-toolbar"><p>保存人物名称与意义，同名人物保持独立。</p><label>搜索人物<input id="people-search" value="${esc(state.personSearch||'')}" placeholder="姓名或意义"></label><button class="button small" data-new-node="entities">${icon('plus')}新建人物</button></div>${items.length?`<div class="node-grid">${items.map(node=>h`<article class="node-card"><span class="node-symbol">${icon('people')}</span><h3><button data-focus-node="${esc(node.id)}" data-kind="entities">${esc(node.name)}</button></h3><small>${esc(node.id.slice(-8))}</small><p>${esc(node.summary||t('尚未填写意义'))}</p><footer><button class="button small" data-focus-node="${esc(node.id)}" data-kind="entities">相关经历 ${node.recordCount||0}</button><button class="button small" data-edit-node="${esc(node.id)}" data-kind="entities">编辑</button><button class="button small danger" data-delete-node="${esc(node.id)}" data-kind="entities">删除</button></footer></article>`).join('')}</div>`:empty(t('暂无匹配人物'),t('可以创建人物，或清除搜索。'),'node-entities',t('新建人物'),'people')}`;
}

export function upcoming(records){
  const future=records.filter(record=>['planned','recurring'].includes(record.recordState)&&!['completed','cancelled'].includes(record.completionState)).sort((a,b)=>(a.eventDate||'9999').localeCompare(b.eventDate||'9999'));
  if(!future.length)return empty(t('把期待，也写进生活'),t('想去的地方，想见的人，都可以从一条计划开始。'),'new-plan',t('记下一份期待'),'sun');
  return h`<h2 class="section-caption">未来可期<small>含待安排与周期性事项，不代表已发生</small></h2><div class="upcoming-grid">${future.map(record=>`<div><div class="timeline-month">${esc(dateLabel(record.eventDate))}</div>${card(record)}</div>`).join('')}</div>`;
}



export function all(records,state){return h`<p class="draft-notice">全部 ${records.length} 条匹配记录；包含关闭时间轴显示的资料，筛选与时间轴分别保留。</p><div class="upcoming-grid">${records.length?records.map(card).join(''):empty(t('没有匹配的记录'),t('可以清除筛选，或记录一段新经历。'))}</div>`;}
export function drafts(state){return h`<p class="draft-notice">记录和人物草稿独立于正式资料。只保证已经显示“已保存在本机”的内容可恢复，不会上传草稿。</p><div class="draft-list">${state.drafts.length?state.drafts.map(draft=>h`<article class="draft-item"><small>${draft.kind==='person'?t('人物草稿'):t('记录草稿')} · ${esc(draft.updatedAt)}</small><h3>${esc(draft.values.title||draft.values.name||t('未命名草稿'))}</h3><p>${esc((draft.values.content||draft.values.summary||'').slice(0,160))}</p><footer><button class="button" data-resume-draft="${esc(draft.id)}">继续编辑</button><button class="button subtle danger" data-discard-draft="${esc(draft.id)}" data-version="${draft.version}">放弃这份草稿</button></footer></article>`).join(''):empty(t('暂无本机草稿'),t('编辑时停止输入 600ms 后自动保存草稿。'),'new',t('写一段记录'))}</div>`;}
export function trash(records){return h`<p class="draft-notice">回收站不计入首页、查询和地点统计。恢复保留原 ID，不新建副本。</p><div class="trash-list">${records.length?records.map(record=>h`<article class="trash-item"><h3>${esc(record.title||t('未命名记录'))}</h3><p>${esc(record.content.slice(0,160))}</p><small>${esc(dateLabel(record.eventDate))} · ${record.photoUris?.length||0} 张照片引用</small><footer><button class="button" data-restore="${esc(record.id)}" data-version="${record.version}">恢复记录</button></footer></article>`).join(''):empty(t('回收站是空的'),t('删除的普通记录会保留在这里。'),null)}</div>`;}
export function person(records,state){const node=state.graph.entities.find(value=>value.id===state.personId);if(!node)return empty(t('人物已删除或不可读取'),t('相关人生记录仍保留在全部记录中。'),null);return h`<section class="person-focus"><small>人物 · ${esc(node.id.slice(-8))}</small><h2>${esc(node.name)}</h2><p>${esc(node.summary||t('还没有写下 TA 对你的意义。'))}</p><button class="button" data-action="person-record">记录与 TA 的经历</button><button class="button subtle" data-edit-node="${esc(node.id)}" data-kind="entities">编辑人物</button><button class="button subtle danger" data-delete-node="${esc(node.id)}" data-kind="entities">删除人物并解除关系</button></section><h3>相关经历 · ${records.length}</h3><div class="upcoming-grid">${records.map(card).join('')||empty(t('还没有关联经历'),t('可以为 TA 记录一段经历。'),'person-record',t('记录与 TA 的经历'))}</div>`;}

export function about(state){return h`<section class="settings-card"><h2>Everhere Web</h2><p>人生相册、回忆录与文创商城，使用同一网站账户。记录和照片保存在此网站的服务器数据库中。</p><p>管理员只能处理自己领取的回忆录材料，不能浏览或改写用户原始相册。</p><p>回忆录成品只开放样张预览。商城可保存待支付订单，付款、退款、印刷与物流尚未开放。</p><a class="button" href="/workspace#account">网站账户</a></section>`;}
