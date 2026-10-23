/* 两种语言的真实页面验收；只向独立内存验收服务写入合成资料。 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.TEST_BASE_URL||'http://127.0.0.1:5003';assert.match(base,/^http:\/\/(127\.0\.0\.1|localhost):5003$/);
 const nav=async view=>{await page.locator(`#sidebar [data-view="${view}"]`).click();await page.waitForFunction(()=>!document.querySelector('#view-content .loading-state'));};
 const language=async value=>{await page.locator('[data-language-select]').selectOption(value);await page.waitForFunction(v=>document.documentElement.lang===v,value);await page.waitForFunction(()=>!document.querySelector('#view-content .loading-state'));};
 const noChinese=async label=>{
   const text=await page.locator('body').innerText();
   const rest=text.replaceAll('简体中文','').replaceAll('人生记录','').replaceAll('人物','').replaceAll('保留中文正文与标签','').replaceAll('保留标签','');
   assert.equal(/[\u3400-\u9fff]/.test(rest),false,`${label}: ${rest.match(/.{0,35}[\u3400-\u9fff].{0,80}/g)?.join('\n')}`);
 };
 try{
  await page.goto(base);await page.locator('.life-hero').waitFor();
  assert.equal(await page.locator('html').getAttribute('lang'),'zh-CN');
  await language('en');await page.locator('.life-hero').waitFor();await noChinese('English home');
  await page.reload();await page.locator('.life-hero').waitFor();assert.equal(await page.locator('[data-language-select]').inputValue(),'en');
  const seed=await page.evaluate(async()=>{
   const session=(await(await fetch('/api/v1/auth/session')).json()).data;
   const headers={'Content-Type':'application/json','X-CSRF-Token':session.csrfToken};
   const person=(await(await fetch('/api/v1/graph/entities',{method:'POST',headers,body:JSON.stringify({name:'人物',summary:'English description'})})).json()).data;
   const record=(await(await fetch('/api/v1/records',{method:'POST',headers,body:JSON.stringify({title:'人生记录',content:'English memory',datePrecision:'year',eventDate:'2020',mood:'开心',linkedEntityIds:[person.id],latitude:0,longitude:0,showOnGlobe:true})})).json()).data;
   return {person,record,region:session.region};
  });
  for(const view of ['all','timeline','calendar','places','upcoming','entities','drafts','trash','appearance','mine','archive']){await nav(view);await noChinese(view);}
  await page.locator('[data-view="about"]').count().then(async count=>{if(!count){await nav('mine');}await page.locator('[data-view="about"]').click();});await noChinese('about');
  await nav('home');await page.locator('#hero-write').click();await page.locator('[data-create-state="occurred"]').click();await page.locator('#editor-dialog[open]').waitFor();
  await noChinese('editor');
  await page.locator('#record-form [name="title"]').fill('English saved record');
  await page.locator('#record-form [name="content"]').fill('保留中文正文与标签');
  await page.locator('#record-form [name="mood"]').selectOption({label:'Happy'});
  assert.equal(await page.locator('#record-form [name="mood"]').inputValue(),'开心');
  await page.locator('#record-form [name="datePrecision"]').selectOption('month');await page.locator('#record-form [name="eventDate"]').fill('1960-02');
  // 即便脚本触发语言更改，也不能用重载抹掉打开的编辑器。
  await page.evaluate(()=>{const select=document.querySelector('[data-language-select]');select.value='zh-CN';select.dispatchEvent(new Event('change',{bubbles:true}));});
  assert.equal(await page.locator('html').getAttribute('lang'),'en');assert.equal(await page.locator('#record-form [name="content"]').inputValue(),'保留中文正文与标签');
  await page.locator('#save-record').click();await page.locator('#detail-dialog[open]').waitFor();
  assert.match(await page.locator('.detail-date').innerText(),/February 1960/);await noChinese('record detail');
  await page.locator('[data-close="detail-dialog"]').click();
  await nav('all');const saved=await page.evaluate(async()=>{const rows=(await(await fetch('/api/v1/records?target=all')).json()).data.records;return rows.find(r=>r.title==='English saved record');});
  assert.equal(saved.mood,'开心');assert.equal(saved.content,'保留中文正文与标签');assert.equal(saved.datePrecision,'month');
  await language('zh-CN');assert.match(await page.locator('#page-title').innerText(),/全部记录/);
  await page.locator('[data-record="'+saved.id+'"]').click();await page.locator('#detail-dialog[open]').waitFor();assert.match(await page.locator('.detail-date').innerText(),/1960年2月/);
  await page.locator('[data-action="edit-record"]').click();await page.locator('#editor-dialog[open]').waitFor();assert.equal(await page.locator('[name="mood"]').inputValue(),'开心');
  await page.locator('[data-action="save-record-draft"]').click();await page.locator('#editor-dialog').waitFor({state:'hidden'});
  await page.waitForFunction(()=>!document.querySelector('#view-content .loading-state'));
  await language('en');await nav('drafts');await page.locator('[data-resume-draft]').first().click();await page.locator('#editor-dialog[open]').waitFor();
  assert.equal(await page.locator('[name="content"]').inputValue(),'保留中文正文与标签');await page.locator('#save-record').click();await page.locator('#detail-dialog[open]').waitFor();await page.locator('[data-close="detail-dialog"]').click();
  await nav('entities');await page.locator('[data-focus-node]').first().click();await page.locator('.person-focus').waitFor();await noChinese('person');
  assert.equal(await page.locator('.person-focus h2').innerText(),'人物');
  await nav('lifegraph');await page.waitForFunction(()=>document.querySelector('#lifegraph')?.getAttribute('aria-busy')==='false');await noChinese('life connections');
  await page.locator('[data-lg="filters"]').count().then(async count=>{if(count)await page.locator('[data-lg="filters"]').click();});
  await page.screenshot({path:'test-results/i18n-graph-en.png',fullPage:true});
  await nav('archive');await page.locator('[data-action="export"]').click();await noChinese('export confirmation');const wait=page.waitForEvent('download');await page.locator('#confirm-submit').click();const download=await wait;
  const archive=JSON.parse(await fs.readFile(await download.path(),'utf8'));const original=archive.data.documents.find(d=>d.id===seed.record.id);assert.equal(original.title,'人生记录');assert.equal(original.mood,'开心');
  await page.locator('#confirm-dialog').waitFor({state:'hidden'});
  await page.route('**/api/v1/records?*',route=>route.abort());await nav('all');assert.match(await page.locator('.error-state').innerText(),/Connection interrupted/);await noChinese('network error');await page.unroute('**/api/v1/records?*');await page.locator('[data-action="retry"]').click();
  await page.waitForFunction(()=>!document.querySelector('#view-content .loading-state'));
  const validation=await page.evaluate(async()=>{const session=(await(await fetch('/api/v1/auth/session')).json()).data;return (await(await fetch('/api/v1/records',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrfToken},body:JSON.stringify({title:'',content:''})})).json()).error;});assert.equal(validation.message,'Enter a title or some text.');
  await nav('home');await page.screenshot({path:'test-results/i18n-home-en.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.goto(base);await page.locator('.life-hero').waitFor();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.screenshot({path:'test-results/i18n-mobile-en.png',fullPage:true});
  assert.equal(await page.locator('[data-language-select]').isVisible(),true);
  await page.goto(base+'/login');await page.locator('#auth-error').filter({hasText:'not configured'}).waitFor();await noChinese('cloud login');
  await page.locator('[data-language-select]').selectOption('zh-CN');await page.waitForFunction(()=>document.documentElement.lang==='zh-CN');assert.match(await page.locator('h1').innerText(),/登录云账号/);
  assert.deepEqual(errors,[]);console.log('PASS: 中英文切换与持久化、全视图文案、日期格式、用户原文/心情枚举保真、编辑保护、草稿跨语言恢复、归档保真、英文错误、390px布局和登录页');
 }catch(error){await page.screenshot({path:'test-results/i18n-failure.png',fullPage:true});throw error;}
 finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
