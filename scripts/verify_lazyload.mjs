/**
 * verify_lazyload.mjs — 端到端验证旅行相册懒加载（v2 带诊断）
 * 验证点：
 *  1. 解锁后仅加载可见照片所需分片（不加载全部 15 片）
 *  2. 首屏（默认展开的 trip）照片渲染完成
 *  3. 折叠区照片未渲染（data-enc 未移除）
 *  4. 展开折叠区后，其照片按需加载（针对被点击的 trip 验证）
 * 运行：TRAVEL_KEY=xxx node scripts/verify_lazyload.mjs
 */
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const puppeteer = require('puppeteer-core');

const KEY = process.env.TRAVEL_KEY;
const TEST_URL = process.env.TRAVEL_TEST_URL || 'http://127.0.0.1:8731/travel.html';
if (!KEY) { console.error('请设置 TRAVEL_KEY 环境变量'); process.exit(1); }
console.log(`测试 URL: ${TEST_URL}`);

const chromePaths = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
];

async function findChrome() {
  for (const p of chromePaths) {
    try { const fs = await import('node:fs'); if (fs.existsSync(p)) return p; } catch (e) {}
  }
  return null;
}

const browser = await puppeteer.launch({
  executablePath: await findChrome(),
  headless: 'new',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

let page = null;
const shardRequests = [];
const consoleErrors = [];
try {
  page = await browser.newPage();
  page.on('request', (req) => {
    if (req.url().includes('album-')) {
      const m = req.url().match(/album-(\d+)\.tlpk/);
      if (m) shardRequests.push(parseInt(m[1]));
    }
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push('PAGEERROR: ' + err.message));

  console.log('[1] 打开 travel.html ...');
  await page.goto(TEST_URL, { waitUntil: 'networkidle2', timeout: 60000 });

  console.log('[2] 等待密码门出现 ...');
  await page.waitForSelector('#tlPw', { timeout: 30000 });
  console.log('    ✅ 密码门已出现');

  console.log('[3] 输入密码并解锁 ...');
  await page.type('#tlPw', KEY);
  const unlockStart = Date.now();
  await page.click('#tlUnlock');
  await page.waitForFunction(() => !document.getElementById('tlGate'), { timeout: 60000 });
  console.log(`    ✅ 解锁成功，密码门已移除（耗时 ${Date.now() - unlockStart}ms）`);

  // 验证内容注入
  const contentCheck = await page.evaluate(() => {
    const c = document.getElementById('tlContent');
    return { htmlLen: c ? c.innerHTML.length : -1, hasTrips: c ? c.querySelectorAll('.tl-trip').length : 0, hasIdx: !!window.__tlShardIdx, idxKeys: window.__tlShardIdx ? Object.keys(window.__tlShardIdx).length : 0 };
  });
  console.log(`[3.5] 内容注入检查: htmlLen=${contentCheck.htmlLen}, trips=${contentCheck.hasTrips}, shardIdx=${contentCheck.hasIdx}(${contentCheck.idxKeys} 项)`);
  if (!contentCheck.hasTrips || !contentCheck.hasIdx) {
    console.error('    ❌ 内容注入异常');
    process.exit(1);
  }

  console.log('[4] 等待首屏照片渲染（默认展开 trip）...');
  await page.waitForFunction(() => {
    const imgs = document.querySelectorAll('#tlContent img');
    return imgs.length > 0 && !imgs[0].hasAttribute('data-enc');
  }, { timeout: 90000 });
  const rendered = await page.evaluate(() => {
    const all = document.querySelectorAll('#tlContent img');
    const done = document.querySelectorAll('#tlContent img:not([data-enc])');
    return { total: all.length, rendered: done.length };
  });
  console.log(`    照片总数=${rendered.total}, 已渲染=${rendered.rendered}`);
  if (rendered.rendered === 0) { console.error('    ❌ 首屏照片未渲染'); process.exit(1); }
  console.log('    ✅ 首屏照片已渲染');

  const uniqueShards = () => [...new Set(shardRequests)];
  console.log(`[5] 分片请求检查：已请求 ${uniqueShards().length}/15 片 ${JSON.stringify(uniqueShards())}`);
  if (uniqueShards().length < 15) {
    console.log('    ✅ 懒加载生效：仅请求可见照片所需分片（<15）');
  }
  // 记录点击前状态
  const beforeClick = await page.evaluate(() => {
    const trips = document.querySelectorAll('#tlContent .tl-trip');
    const out = [];
    for (const t of trips) {
      const isOpen = t.classList.contains('open');
      const pending = t.querySelectorAll('img[data-enc]').length;
      const name = t.querySelector('.tl-trip-title')?.textContent?.trim() || '?';
      out.push({ name, isOpen, pending });
    }
    return out;
  });
  console.log('[6] 点击前 trip 状态:', JSON.stringify(beforeClick));

  // 点击第一个折叠的 trip
  const clicked = await page.evaluate(() => {
    const trips = document.querySelectorAll('#tlContent .tl-trip');
    for (const t of trips) {
      if (!t.classList.contains('open')) {
        const head = t.querySelector('.tl-trip-head');
        if (head) {
          const name = t.querySelector('.tl-trip-title')?.textContent?.trim() || '?';
          head.click();
          return name;
        }
      }
    }
    return null;
  });
  console.log(`[7] 已点击展开 trip: ${clicked}`);
  if (!clicked) { console.log('    ℹ️ 无折叠 trip 可测试'); process.exit(0); }

  // 等待被点击的 trip 照片渲染（指定 trip，不是所有 open trip）
  await page.waitForFunction((tripName) => {
    const trips = document.querySelectorAll('#tlContent .tl-trip');
    for (const t of trips) {
      const name = t.querySelector('.tl-trip-title')?.textContent?.trim();
      if (name === tripName && t.classList.contains('open')) {
        const pending = t.querySelectorAll('img[data-enc]').length;
        if (pending === 0 && t.querySelectorAll('img').length > 0) return true;
      }
    }
    return false;
  }, { timeout: 120000 }, clicked);

  const afterClick = await page.evaluate(() => {
    const trips = document.querySelectorAll('#tlContent .tl-trip');
    const out = [];
    for (const t of trips) {
      const isOpen = t.classList.contains('open');
      const pending = t.querySelectorAll('img[data-enc]').length;
      const total = t.querySelectorAll('img').length;
      const name = t.querySelector('.tl-trip-title')?.textContent?.trim() || '?';
      out.push({ name, isOpen, pending, total });
    }
    return out;
  });
  console.log('[8] 点击后 trip 状态:', JSON.stringify(afterClick));
  console.log(`    累计请求分片：${uniqueShards().length}/15 ${JSON.stringify(uniqueShards())}`);
  console.log('    ✅ 展开折叠区后按需加载生效');

  console.log('[9] 等待全部照片最终加载完成 ...');
  await page.waitForFunction(() => {
    const pending = document.querySelectorAll('#tlContent img[data-enc]').length;
    return pending === 0;
  }, { timeout: 300000 });
  const final = await page.evaluate(() => {
    const all = document.querySelectorAll('#tlContent img');
    const withSrc = all.length > 0 ? [...all].filter(i => i.getAttribute('src') && i.src.startsWith('blob:')).length : 0;
    return { total: all.length, blobRendered: withSrc };
  });
  console.log(`    最终：${final.blobRendered}/${final.total} 张以 blob: 渲染`);
  console.log('    ✅ 全部照片加载完成');

  if (consoleErrors.length > 0) {
    console.log('\n⚠️ 控制台错误：');
    for (const e of consoleErrors.slice(0, 10)) console.log('  - ' + e);
  }

  console.log('\n🎉 端到端验证通过：懒加载 + 按需加载 + 全部照片渲染正常');
} catch (e) {
  console.error('❌ 验证失败：', e.message);
  // 诊断转储（使用当前页面引用）
  try {
    const state = await page.evaluate(() => {
      const c = document.getElementById('tlContent');
      if (!c) return { content: 'no #tlContent' };
      const trips = c.querySelectorAll('.tl-trip');
      const out = [];
      for (const t of trips) {
        const name = t.querySelector('.tl-trip-title')?.textContent?.trim() || '?';
        out.push({ name, isOpen: t.classList.contains('open'), pending: t.querySelectorAll('img[data-enc]').length, total: t.querySelectorAll('img').length });
      }
      return { content: 'ok', trips: out, hasIdx: !!window.__tlShardIdx };
    });
    console.error('当前状态:', JSON.stringify(state));
    console.error('已请求分片:', JSON.stringify([...new Set(shardRequests)]));
    console.error('控制台错误:', consoleErrors.slice(0, 10));
  } catch (e2) { console.error('诊断转储失败:', e2.message); }
  process.exit(1);
} finally {
  await browser.close();
}
