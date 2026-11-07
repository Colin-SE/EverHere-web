/* 合成用户和管理员分开浏览器会话，覆盖真实页面上的提交、退回、制作与下单。 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const base=process.env.TEST_BASE_URL||'http://127.0.0.1:5004';
(async()=>{
 assert.match(base,/^http:\/\/(127\.0\.0\.1|localhost):5004$/);
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const userContext=await browser.newContext({viewport:{width:1440,height:1000}}),adminContext=await browser.newContext({viewport:{width:1440,height:1000}});
 const user=await userContext.newPage(),admin=await adminContext.newPage(),errors=[];
 const productName=`旅行纪念奖牌 ${Date.now()}`;
 for(const p of [user,admin])p.on('pageerror',e=>errors.push(e.message));
 await fs.mkdir('test-results/workflows',{recursive:true});
 const action=(page,name)=>page.getByRole('button',{name,exact:true});
 const saveDraft=async page=>{await action(page,'保存草稿').click();await page.waitForFunction(()=>{const button=document.querySelector('#memoir-form button[type=submit]');return button&&!button.disabled;});};
 try{
  assert.equal((await (await user.request.get(base+'/health')).json()).database,'sqlite');
  await user.goto(base+'/workspace#account');await action(user,'没有账户，去注册').click();
  await user.getByLabel('显示姓名').fill('旅行记录者');await user.getByLabel('邮箱',{exact:true}).fill(`traveller${Date.now()}@example.test`);await user.getByLabel('密码（10—128 个字符）').fill('browser-user-password');
  await action(user,'注册并进入').click();await action(user,'整理新回忆录').waitFor({timeout:8000}).catch(async e=>{console.error('Account UI:',user.url(),await user.locator('body').innerText(),errors);throw e;});
  // 原相册入口实际新增、保存；新模块复用其稳定记录，而非另建源数据。
  await user.goto(base+'/');await user.locator('#hero-write').click();await user.locator('[data-create-state="occurred"]').click();
  await user.locator('#record-form [name="title"]').fill('七天旅行的第一天');await user.locator('#record-form [name="content"]').fill('抵达海边，在这里留下了第一段回忆。');
  await user.locator('#photo-input').setInputFiles({name:'memory.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAwAAAAICAIAAABChommAAAAFUlEQVR4nGNsml7OQAgwEVQx7BUBANXiAaD6UKd3AAAAAElFTkSuQmCC','base64')});await user.locator('#photo-previews img').waitFor();
  await user.locator('#save-record').click();await user.locator('#detail-dialog[open]').waitFor();
  await user.goto(base+'/workspace#memoirs');await action(user,'整理新回忆录').click();
  await user.getByLabel('回忆录标题',{exact:true}).fill('我们的七天旅行');await user.getByLabel('主题说明').fill('第一次完整整理旅行经历');
  await user.locator('[data-select-record]').first().check();await user.locator('[data-chapter-photo]').first().check();await saveDraft(user);await user.locator('#authorise-materials').waitFor();
  await user.locator('#authorise-materials').check();await action(user,'提交审核').click();await user.getByText('待审核',{exact:true}).waitFor();
  await admin.goto(base+'/workspace#account');await admin.getByLabel('邮箱',{exact:true}).fill('reviewer@example.test');await admin.getByLabel('密码（10—128 个字符）').fill('browser-test-only-password');await action(admin,'登录').click();
  await admin.locator('#admin-link').click();await action(admin,'领取审核任务').click();await admin.getByLabel('审核意见（退回时必填）').fill('请将章节标题补充为完整的第一天。');await action(admin,'退回修改').click();await admin.getByText('需修改',{exact:true}).waitFor();
  await user.reload();await user.getByRole('button',{name:'继续整理',exact:true}).click();await action(user,'修改草稿 / 重新提交').click();await user.locator('[data-chapter-heading]').first().fill('第一天：海边的开始');await saveDraft(user);await user.locator('#authorise-materials').check();await action(user,'提交审核').click();await user.getByText('待审核',{exact:true}).waitFor();
  await admin.reload();await action(admin,'领取审核任务').click();await action(admin,'审核通过').click();await action(admin,'生成回忆录').click();await admin.getByRole('heading',{name:'回忆录已制作完成'}).waitFor();
  await admin.screenshot({path:'test-results/workflows/admin-ready.png',fullPage:true});
  await user.reload();await action(user,'查看进度与成品').click();const previewUrl=await user.getByRole('link',{name:'查看 PDF 预览'}).getAttribute('href');
  const preview=await user.request.get(base+previewUrl);assert.equal(preview.status(),200);assert((await preview.body()).subarray(0,4).equals(Buffer.from('%PDF')));await fs.writeFile('test-results/workflows/memoir-preview.pdf',await preview.body());
  await user.screenshot({path:'test-results/workflows/user-ready.png',fullPage:true});
  await admin.locator('#admin-link').click();await action(admin,'添加商品').click();await admin.getByLabel('商品名称',{exact:true}).fill(productName);await admin.getByLabel('说明',{exact:true}).fill('将一个重要时刻，留作自己的纪念。');await admin.getByLabel('上架此商品',{exact:true}).check();await admin.getByLabel('商品配图',{exact:true}).setInputFiles({name:'product.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAwAAAAICAIAAABChommAAAAFUlEQVR4nGNsml7OQAgwEVQx7BUBANXiAaD6UKd3AAAAAElFTkSuQmCC','base64')});await action(admin,'保存商品').click();await admin.getByRole('heading',{name:'商品管理',exact:true}).waitFor();
  await user.locator('[data-tab="shop"]').click();await user.locator('article.card').filter({has:user.getByRole('heading',{name:productName,exact:true})}).getByRole('button',{name:'选择与定制',exact:true}).click();await user.getByLabel('定制文字（必填）').fill('2026 · 勇敢出发');await action(user,'确认并创建待支付订单').click();await user.getByText('待支付',{exact:true}).waitFor();
  assert.equal(await user.locator('.order-item').count(),1);assert(await user.getByText('2026 · 勇敢出发',{exact:true}).isVisible());
  await user.locator('[data-tab="orders"]').click();await user.getByText('2026 · 勇敢出发',{exact:true}).waitFor();
  await user.setViewportSize({width:390,height:844});await user.screenshot({path:'test-results/workflows/mobile-order.png',fullPage:true});
  assert(await user.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await user.locator('[data-tab="shop"]').click();await user.getByRole('heading',{name:productName,exact:true}).waitFor();await user.screenshot({path:'test-results/workflows/mobile-shop.png',fullPage:true});
  await user.locator('[data-language-select]').selectOption('en');await user.getByRole('heading',{name:'A keepsake for a moment that matters'}).waitFor();assert(await user.getByRole('heading',{name:productName,exact:true}).isVisible());
  await user.screenshot({path:'test-results/workflows/mobile-shop-en.png',fullPage:true});
  await user.locator('[data-tab="orders"]').click();await user.getByText('2026 · 勇敢出发',{exact:true}).waitFor();
  assert.deepEqual(errors,[]);console.log('F1–F4 browser flow passed; desktop and 390px screenshots saved.');
 }catch(error){await user.screenshot({path:'test-results/workflows/failure-user.png',fullPage:true});console.error('User page notice:',await user.locator('#workspace-error').textContent());throw error;}finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
