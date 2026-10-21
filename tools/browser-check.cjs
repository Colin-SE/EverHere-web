/* 使用一次性合成库验收当前 Android 对齐功能，不创建账户或历史格式备份。 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.TEST_BASE_URL||'http://127.0.0.1:5003';
 const nav=async view=>{await page.locator(`#sidebar [data-view="${view}"]`).click();await page.waitForFunction(()=>!document.querySelector('#view-content .loading-state'));};
 try{
  await page.goto(base);await page.locator('.life-hero').waitFor();
  await page.locator('#hero-write').click();await page.locator('[data-create-state="occurred"]').click();
  await page.locator('#editor-dialog[open]').waitFor();
  assert.equal(await page.locator('[name="datePrecision"]').inputValue(),'unknown');
  await page.locator('#record-form [name="title"]').fill('浏览器合成记录');
  await page.locator('#record-form [name="content"]').fill('草稿需要刷新后恢复 <script>window.bad=true</script>');
  await page.getByRole('button',{name:'保存草稿并返回',exact:true}).first().click();
  await page.reload();await page.locator('.life-hero').waitFor();await nav('drafts');
  await page.locator('[data-resume-draft]').first().click();await page.locator('#editor-dialog[open]').waitFor();
  assert.equal(await page.locator('#record-form [name="title"]').inputValue(),'浏览器合成记录');
  await page.locator('[name="datePrecision"]').selectOption('month');await page.locator('[name="eventDate"]').fill('1960-02');
  await page.locator('#photo-input').setInputFiles({name:'memory.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAwAAAAICAIAAABChommAAAAFUlEQVR4nGNsml7OQAgwEVQx7BUBANXiAaD6UKd3AAAAAElFTkSuQmCC','base64')});
  await page.locator('#photo-previews img').waitFor();await page.locator('#save-record').click();
  await page.locator('#detail-dialog[open]').waitFor();assert.equal(await page.locator('#detail-title').textContent(),'浏览器合成记录');
  assert.equal(await page.evaluate(()=>window.bad),undefined);
  await page.locator('.detail-photos img').click();await page.locator('#photo-dialog[open]').waitFor();
  await page.locator('[data-close="photo-dialog"]').click();await page.locator('[data-action="edit-record"]').click();await page.locator('#editor-dialog[open]').waitFor();
  assert.equal(await page.locator('[name="eventDate"]').inputValue(),'1960-02');
  await page.locator('#record-form summary').click();await page.locator('[name="showInTimeline"]').uncheck();
  await page.locator('#save-record').click();await page.locator('#detail-dialog[open]').waitFor();
  await page.locator('[data-close="detail-dialog"]').click();await nav('timeline');assert.equal(await page.locator('.record-card').count(),0);
  await nav('all');await page.locator('.record-card').filter({hasText:'浏览器合成记录'}).click();
  await page.locator('[data-action="delete-record"]').click();await page.locator('#confirm-submit').click();
  await page.locator('#confirm-dialog').waitFor({state:'hidden'});await nav('trash');
  await page.locator('[data-restore]').click();await page.waitForFunction(()=>!document.querySelector('[data-restore]'));
  await nav('entities');await page.locator('[data-new-node="entities"]').click();
  await page.locator('#node-form [name="name"]').fill('阿遥');await page.locator('#node-form [name="summary"]').fill('合成人物资料');
  await page.locator('#node-form [type="submit"]').click();await page.locator('#node-dialog').waitFor({state:'hidden'});
  await page.locator('[data-focus-node]').first().click();await page.locator('[data-action="person-record"]').first().click();
  await page.locator('#editor-dialog[open]').waitFor();assert.equal(await page.locator('#relation-fields input:checked').count(),1);
  await page.locator('[data-action="discard-record-draft"]').click();
  await nav('archive');await page.locator('#import-file').setInputFiles('tests/fixtures/android-native-v1.zip');
  await page.locator('#restore-confirmed').check();await page.locator('[data-action="confirm-import"]').click();
  await page.waitForFunction(()=>!document.querySelector('#restore-confirmed'));
  await page.locator('[data-action="export"]').click();const downloadWait=page.waitForEvent('download');await page.locator('#confirm-submit').click();
  const download=await downloadWait;const exported=JSON.parse(await fs.readFile(await download.path(),'utf8'));assert.equal(exported.format,'everhere-archive');
  await page.locator('#confirm-dialog').waitFor({state:'hidden'});
  await page.locator('[data-action="zip-export"]').click();const zipWait=page.waitForEvent('download');await page.locator('#confirm-submit').click();
  const zip=await zipWait;const bytes=await fs.readFile(await zip.path());assert.equal(bytes.readUInt16LE(0),0x4b50);
  await page.locator('#confirm-dialog').waitFor({state:'hidden'});await nav('calendar');
  await page.locator('#calendar-jump').fill('1960-02');await page.locator('#calendar-jump').dispatchEvent('change');
  await page.locator('.coarse-dates .record-card').first().waitFor();assert.equal(await page.locator('.day-dots').count(),0);

  await nav('appearance');await page.locator('[data-theme="FOREST"]').click();await page.reload();
  assert.equal(await page.locator('html').getAttribute('data-theme'),'FOREST');
  await page.screenshot({path:'test-results/current-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.goto(base);await page.locator('.life-hero').waitFor();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:'test-results/current-mobile.png',fullPage:true});
  assert.equal(await page.locator('[data-view="vault"]').count(),0);assert.deepEqual(errors,[]);
  console.log('PASS: 草稿恢复、月精度、原图浏览、全部/时间轴隔离、回收站、人物草稿与预填、Android ZIP 恢复与导出、主题与移动布局');
 }catch(error){await page.screenshot({path:'test-results/current-failure.png',fullPage:true});throw error;}
 finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
