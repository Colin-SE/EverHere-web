/* 合成当前时间的原生归档，只向5003独立内存验收服务写入。 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const fs=require('node:fs/promises');

function seed(){
 const today=new Date(),date=offset=>{const d=new Date(today);d.setDate(d.getDate()+offset);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
 const common=(type,id)=>({type,id,createdAt:'1',updatedAt:'1',deletedAt:null});
 const documents=[
  {...common('entity','lg-person'),kind:'person',name:'小林',meaning:'一起走过许多地方，也一起收藏寻常日子。'},
  {...common('entity','lg-pet'),kind:'pet',name:'小橘',meaning:'让每个普通的午后都有了陪伴。'},
  {...common('entity','lg-camera'),kind:'object',name:'第一台相机',meaning:'从第一次按下快门开始，练习看见生活。'},
  {...common('thread','lg-thread'),title:'慢慢学习摄影'},
  {...common('chapter','lg-chapter'),title:'初到上海的日子',eventDate:{precision:'range',start:date(-80),end:date(90)},threadIds:['lg-thread']}
 ];
 const titles=['海边，和小林等一场日落','给生活留一点光','带小橘去公园','下一次山间旅行','周末的雨和咖啡','沿着熟悉的街道走走','第一次见面的夏天','再拍一张窗边的光'];
 for(let i=0;i<8;i++)documents.push({...common('record','lg-record-'+i),title:titles[i],content:'合成验收资料：人与经历从这里相连，不代表真实用户内容。',recordState:i===1?'ongoing':i===3?'planned':'occurred',completionState:i===1?'started':i===3?'planned':'completed',eventDate:{precision:'day',start:i===6?'2018-06-15':date(i===3?7:-i),end:null},timezone:'Asia/Shanghai',placeName:i===0?'海边':'上海',coordinates:null,tags:['生活'],mood:null,showInTimeline:true,showOnGlobe:false,privacy:'standard',entityIds:i===2?['lg-pet','lg-person']:['lg-person','lg-camera'],threadIds:i===1?['lg-thread']:[],chapterIds:i<4?['lg-chapter']:[],photos:[]});
 for(const doc of documents)for(const name of ['entityIds','threadIds','chapterIds'])if(doc[name])doc[name].sort();
 const data={documents,reminders:[]},bytes=Buffer.from(JSON.stringify(data).replaceAll('/','\\/'));
 const manifest={format:'everhere-archive',archiveVersion:1,kind:'json',region:'global',createdAt:String(Date.now()),appVersion:'graph-synthetic-check',versionCode:1,databaseVersion:8,dataSha256:crypto.createHash('sha256').update(bytes).digest('hex'),dataBytes:String(bytes.length),counts:{record:8,entity:3,thread:1,chapter:1,reminder:0,photo:0},assets:[],missingOriginals:[],protectedExcluded:true,complete:false};
 return {format:'everhere-archive',archiveVersion:1,manifest,data};
}

(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'}),context=await browser.newContext({viewport:{width:1512,height:1000}}),page=await context.newPage();
 const base=process.env.TEST_BASE_URL||'http://127.0.0.1:5003';assert.match(base,/^http:\/\/(127\.0\.0\.1|localhost):5003$/);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const ready=()=>page.waitForFunction(()=>document.querySelector('#lifegraph')?.getAttribute('aria-busy')==='false');
 const inspect=selector=>page.locator('.lg-inspector '+selector);
 try{
  await page.goto(base);await page.locator('.life-hero').waitFor();
  await page.evaluate(async archive=>{const session=(await(await fetch('/api/v1/auth/session')).json()).data;const headers={'Content-Type':'application/json','X-CSRF-Token':session.csrfToken};const preview=await(await fetch('/api/v1/archive/preview',{method:'POST',headers,body:JSON.stringify({archive})})).json();if(preview.error)throw Error(preview.error.message);const value=await(await fetch('/api/v1/archive/import',{method:'POST',headers,body:JSON.stringify({archive,fingerprint:preview.data.fingerprint,targetFingerprint:preview.data.targetFingerprint})})).json();if(value.error)throw Error(value.error.message);},seed());
  await page.locator('#sidebar [data-view="lifegraph"]').click();await ready();
  assert.ok(await page.locator('.lg-node').count()<=10);await page.locator('[data-lg="fit"]').click();
  await page.evaluate(()=>{document.activeElement.blur();scrollTo(0,0);});
  await page.screenshot({path:'test-results/lifegraph-desktop.png',fullPage:true});
  await page.locator('.lg-canvas').screenshot({path:'test-results/lifegraph-preview.png'});
  await page.locator('.lg-options summary').click();await page.locator('.lg-search input').fill('小林');await page.locator('.lg-search button').click();await ready();
  await page.locator('.lg-search-results [data-lg-focus="entity:lg-person"]').click();await ready();
  assert.equal(await page.locator('.root-node').getAttribute('data-lg-node'),'entity:lg-person');
  assert.ok(await inspect('[data-lg-more]').count());await inspect('[data-lg-more]').click();await ready();
  assert.equal(await page.locator('[data-lg-node="record:lg-record-6"]').count(),1);
  await page.locator('[data-lg-node="record:lg-record-0"]').click();await inspect('[data-lg-expand]').click();await ready();
  assert.equal(await page.locator('[data-lg-node="entity:lg-camera"]').count(),1);
  const savedViewport=await page.locator('.lg-scene').getAttribute('style');
  await inspect('[data-lg-open]').click();await page.locator('#detail-dialog[open]').waitFor();
  await page.locator('[data-action="edit-record"]').click();await page.locator('#editor-dialog[open]').waitFor();
  await page.locator('#record-form [name="title"]').fill('日落之后，我们又聊了一会儿');await page.locator('#save-record').click();
  await page.locator('#editor-dialog').waitFor({state:'hidden'});await page.locator('#detail-dialog[open]').waitFor();await page.locator('[data-close="detail-dialog"]').click();await ready();
  assert.equal(await page.locator('.root-node').getAttribute('data-lg-node'),'entity:lg-person');
  assert.ok((await page.locator('[data-lg-node="record:lg-record-0"]').innerText()).includes('日落之后'));
  assert.equal(await page.locator('.lg-scene').getAttribute('style'),savedViewport);
  await page.locator('[data-lg="list"]').click();await page.locator('[data-lg-select="record:lg-record-0"]').first().click();
  await inspect('.lg-related-item').filter({hasText:'小林'}).locator('[data-lg-unlink]').click();await page.locator('#confirm-submit').click();await page.locator('#confirm-dialog').waitFor({state:'hidden'});await ready();
  const unlinked=await page.evaluate(async()=> (await(await fetch('/api/v1/records/lg-record-0')).json()).data);assert.equal(unlinked.linkedEntityIds.includes('lg-person'),false);
  await inspect('[data-lg-relate]').click();await page.locator('.lg-relation-form input').fill('日落之后');await page.locator('.lg-relation-form [type="submit"]').click();await ready();
  await page.locator('[data-lg-link="record:lg-record-0"]').click();await page.locator('#confirm-submit').click();await page.locator('#confirm-dialog').waitFor({state:'hidden'});await ready();
  const linked=await page.evaluate(async()=> (await(await fetch('/api/v1/records/lg-record-0')).json()).data);assert.ok(linked.linkedEntityIds.includes('lg-person'));assert.equal(linked.id,'lg-record-0');
  if(!(await page.locator('.lg-options').getAttribute('open')!==null))await page.locator('.lg-options summary').click();
  await page.locator('.lg-filter [name="from"]').fill('2018-01-01');await page.locator('.lg-filter [name="to"]').fill('2018-12-31');await page.locator('.lg-filter [type="submit"]').click();await ready();
  assert.equal(await page.locator('[data-lg-node="record:lg-record-6"]').count(),1);assert.equal(await page.locator('.lg-node').count(),2);
  await page.locator('[data-lg="clear-filter"]').click();await ready();
  await page.locator('[data-lg="home"]').click();await ready();await page.locator('[data-lg="canvas"]').click();if(await page.locator('.lg-options').getAttribute('open')!==null)await page.locator('.lg-options summary').click();await page.locator('[data-lg="fit"]').click();
  await page.setViewportSize({width:390,height:844});await page.locator('[data-lg="center"]').click();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.evaluate(()=>{document.activeElement.blur();scrollTo(0,0);});await page.screenshot({path:'test-results/lifegraph-mobile.png',fullPage:true});
  const canvas=page.locator('.lg-canvas'),before=await page.locator('.lg-scene').getAttribute('style');await canvas.scrollIntoViewIfNeeded();const rect=await canvas.boundingBox();await page.mouse.move(rect.x+18,rect.y+rect.height-95);await page.mouse.down();await page.mouse.move(rect.x+70,rect.y+rect.height-145,{steps:8});await page.mouse.up();assert.notEqual(await page.locator('.lg-scene').getAttribute('style'),before);
  await page.locator('[data-lg="list"]').click();await page.locator('.lg-list-title[data-lg-select="record:lg-record-0"]').click();await inspect('[data-lg-open]').click();await page.locator('#detail-dialog[open]').waitFor();
  await page.route('**/lifegraph/snapshot',route=>route.abort());await context.clearCookies();await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await ready();
  await page.locator('.lg-error').waitFor();assert.equal(await page.locator('#detail-dialog[open]').count(),0);assert.equal(await page.locator('.lg-node').count(),0);await page.unroute('**/lifegraph/snapshot');await page.locator('[data-lg="retry"]').click();await ready();
  assert.equal(await page.locator('.lg-node').count(),1);assert.equal(await page.locator('.lg-inspector').getByText('小林',{exact:true}).count(),0);
  assert.deepEqual(errors,[]);console.log('PASS: 有限现在邻域、查找聚焦、一层展开与分页、原ID编辑返回、显式关系解绑/保存、画布平移、移动布局、换空间清理');
 }catch(error){await page.screenshot({path:'test-results/lifegraph-failure.png',fullPage:true});throw error;}
 finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
