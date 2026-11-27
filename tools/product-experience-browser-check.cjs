/* 隔离浏览器回归：商品下单到处理完成、同源人物关系与 3D 降级。 */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const base = 'http://127.0.0.1:5004';
const password = 'browser-test-only-password';
const fixture = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAwAAAAICAIAAABChommAAAAFUlEQVR4nGNsml7OQAgwEVQx7BUBANXiAaD6UKd3AAAAAElFTkSuQmCC', 'base64');

async function request(context, path, json, method = 'POST') {
  const session = await context.request.get(base + '/api/v1/auth/session');
  const { csrfToken } = (await session.json()).data;
  const response = await context.request.fetch(base + '/api/v1' + path, {
    method, data: json, headers: { 'X-CSRF-Token': csrfToken },
  });
  const result = await response.json();
  assert.ok(response.ok(), JSON.stringify(result));
  return result.data;
}

async function run() {
  const browser = await chromium.launch({ headless: true, channel: 'msedge', args: ['--enable-unsafe-swiftshader'] });
  const errors = [];
  const owner = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  const staff = await browser.newContext();
  const account = 'browser-p123-' + Date.now() + '@example.test';
  try {
    assert.equal((await (await owner.request.get(base + '/health')).json()).database, 'mysql');
    await request(owner, '/accounts/register', { email: account, name: 'Browser buyer', password });
    await request(staff, '/accounts/login', { email: 'reviewer@example.test', password });
    const product = await request(staff, '/admin/products', {
      name: 'Browser keepsake', description: 'Custom souvenir', active: true,
      variants: [{ name: 'Standard', kind: 'gift', priceCents: 3990, textRequired: true }],
    });
    const person = await request(owner, '/graph/entities', { name: 'Browser friend' });
    await request(owner, '/records', { title: 'Browser memory', content: 'Linked content', placeName: 'Public library', linkedEntityIds: [person.id] });

    const page = await owner.newPage();
    const admin = await staff.newPage();
    for (const p of [page, admin]) p.on('pageerror', error => errors.push(error.message));
    await owner.addCookies([{name:'everhere-language',value:'en',url:base}]);
    await page.goto(base + '/connections');
    await page.getByRole('button', { name: person.name, exact: true }).click();
    await page.getByRole('button', { name: 'List view' }).click();
    await page.getByRole('button', { name: 'Open entry' }).click();
    await page.getByRole('heading', { name: 'Browser memory' }).waitFor();
    await page.goto(base + '/places');
    await page.getByRole('button', { name: 'Open 3D globe' }).click();
    await page.locator('canvas').waitFor({ state: 'visible' });
    await page.getByRole('button', { name: 'Start rotation' }).waitFor();
    await page.locator('canvas').press('ArrowLeft');
    await page.route('**/earth-land-110m.png', route => route.abort());
    await page.reload();
    await page.getByRole('button', { name: 'Open 3D globe' }).click();
    await page.getByText('The 3D globe is unavailable. You can still use the places list.').waitFor();
    await page.getByRole('heading', { name: 'Public library' }).waitFor();

    await page.goto(base + '/album');
    await page.locator('#new-record').click();
    await page.locator('[data-create-state="occurred"]').click();
    await page.locator('#record-form [name="title"]').fill('Offline text stays here');
    await owner.setOffline(true);
    await page.locator('[data-network-status]').waitFor();
    await page.locator('#save-record').click();
    await page.locator('#record-error').filter({ hasText: /network|connection/i }).waitFor();
    assert.equal(await page.locator('#record-form [name="title"]').inputValue(), 'Offline text stays here');
    await owner.setOffline(false);
    await page.locator('#photo-input').setInputFiles({ name: 'entry.png', mimeType: 'image/png', buffer: fixture });
    await page.getByText('Photos uploaded. Save this entry to finish.').waitFor();
    await page.locator('#save-record').click();
    await page.locator('#detail-title').filter({ hasText: 'Offline text stays here' }).waitFor();

    await page.goto(base + '/shop/products/' + product.id);
    await page.locator('[data-buy]').click();
    await page.locator('[name="customText"]').fill('Remember this');
    assert.equal(await page.locator('#purchase-preview').textContent(), 'Remember this');
    let orderAttempt = 0;
    await page.route('**/api/v1/shop/orders', async route => {
      if (route.request().method() !== 'POST' || orderAttempt++) return route.continue();
      await route.fetch();
      await route.abort();
    });
    await page.locator('#purchase-form button[type="submit"]').click();
    await page.locator('#workspace-error').waitFor({ state: 'visible' });
    await page.locator('#purchase-form button[type="submit"]').click();
    await page.getByRole('heading', { name: 'Order details' }).waitFor();
    assert.equal(orderAttempt, 1);
    const orderId = new URL(page.url()).hash.split('/').at(-1);
    await admin.goto(base + '/admin/orders/' + orderId);
    await admin.locator('[data-order-action] button[type="submit"]').click();
    await admin.locator('[data-order-action] [name="action"]').selectOption('request_info');
    await admin.locator('[data-order-action] textarea').fill('Please confirm the text');
    await admin.locator('[data-order-action] button[type="submit"]').click();
    await admin.getByText('Please confirm the text', { exact: true }).waitFor();
    await page.reload();
    await page.locator('[data-order-action] textarea').fill('Confirmed by buyer');
    await page.locator('[data-order-action] button[type="submit"]').click();
    await page.getByText('Confirmed by buyer', { exact: true }).waitFor();

    await admin.reload();
    await admin.locator('[data-order-action] [name="action"]').selectOption('complete');
    await admin.locator('[data-order-action] button[type="submit"]').click();
    await admin.getByText('处理完成', { exact: true }).waitFor();
    await page.reload();
    await page.getByText('Processing complete', { exact: true }).waitFor();
    await page.getByText('Unpaid', { exact: true }).waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    console.log('P1–P3 browser checks passed: offline edit, upload, connection source, globe fallback, order replay and handling.');
  } finally {
    await browser.close();
  }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
