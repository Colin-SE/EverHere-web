/* 只连接专用合成服务，验证码与凭证不输出到日志。 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {randomUUID}=require('node:crypto');
const fs=require('node:fs/promises');
const base='http://127.0.0.1:5017';
const headers={'X-Everhere-Region':'cn'};
const nonce=Date.now(),webEmail=`web-${nonce}@example.test`,mobileEmail=`mobile-${nonce}@example.test`;
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const context=await browser.newContext({viewport:{width:1280,height:900}}),page=await context.newPage();
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const button=name=>page.getByRole('button',{name,exact:true});
 const mail=async(email,purpose)=>(await(await context.request.get(`${base}/__test/code?email=${encodeURIComponent(email)}&purpose=${purpose}`)).json()).code;
 const post=async(path,data,token)=>context.request.post(base+'/v1/auth/'+path,{headers:{...headers,...(token?{Authorization:'Bearer '+token}:{})},data});
 await fs.mkdir('test-results/shared-identity',{recursive:true});
 try{
  await page.goto(base+'/workspace#account');await button('没有账户，去注册').click();
  await page.getByLabel('显示姓名').fill('合成用户');await page.getByLabel('邮箱',{exact:true}).fill(webEmail);
  await page.getByLabel('新密码（12—128 个字符）').fill('synthetic-password-123');
  await button('发送验证码').click();await page.waitForFunction(()=>document.getElementById('code-status')?.textContent.includes('验证码'));
  const code=await mail(webEmail,'register');
  await page.getByLabel('邮箱验证码').fill(code==='00000000'?'11111111':'00000000');await button('注册并进入').click();
  await page.waitForFunction(()=>document.getElementById('workspace-error')?.textContent.includes('验证码不正确'));
  assert.equal(await page.getByLabel('显示姓名').inputValue(),'合成用户');
  assert.equal(await page.getByLabel('新密码（12—128 个字符）').inputValue(),'synthetic-password-123');
  await page.getByLabel('邮箱验证码').fill(code);await button('注册并进入').click();await button('整理新回忆录').waitFor();
  const login=await post('login',{email:webEmail,password:'synthetic-password-123',installationId:randomUUID(),deviceName:'合成 API 手机'});
  assert.equal(login.status(),200);const tokens=await login.json();
  await page.goto(base+'/workspace#account');await page.getByText(webEmail,{exact:true}).waitFor();await page.reload();await button('退出账户').waitFor();
  await button('退出账户').click();await button('忘记密码').click();
  await page.getByLabel('邮箱',{exact:true}).fill(webEmail);await page.getByLabel('新密码（12—128 个字符）').fill('new-synthetic-password');
  await button('发送验证码').click();await page.waitForFunction(()=>document.getElementById('code-status')?.textContent.includes('验证码'));
  await page.getByLabel('邮箱验证码').fill(await mail(webEmail,'reset'));await button('确认重置密码').click();
  await page.waitForFunction(()=>document.getElementById('workspace-error')?.textContent==='密码已重置，请使用新密码登录。');
  assert.equal((await context.request.get(base+'/v1/auth/me',{headers:{...headers,Authorization:'Bearer '+tokens.accessToken}})).status(),401);
  // 手机注册后，网页使用同一账号登录。
  const cid=await(await post('code',{email:mobileEmail,purpose:'register'})).json();
  assert.equal((await post('register',{challengeId:cid.challengeId,code:await mail(mobileEmail,'register'),password:'mobile-synthetic-password'})).status(),201);
  await page.getByLabel('邮箱',{exact:true}).fill(mobileEmail);await page.getByLabel('密码（10—128 个字符）').fill('mobile-synthetic-password');await button('登录').click();await button('整理新回忆录').waitFor();
  await page.goto(base+'/workspace#account');await page.getByText(mobileEmail,{exact:true}).waitFor();await button('退出账户').click();
  await page.setViewportSize({width:390,height:844});await button('没有账户，去注册').click();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:'test-results/shared-identity/register-cn-390.png',fullPage:true});
  await page.locator('[data-language-select]').selectOption('en');
  await page.locator('[data-action="auth-mode"]').click();await page.getByRole('button',{name:'Send code',exact:true}).waitFor();
  await page.screenshot({path:'test-results/shared-identity/register-en-390.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('Shared account browser checks passed: both registration directions, retained input, reset revocation, reload, CN/EN narrow layouts.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
