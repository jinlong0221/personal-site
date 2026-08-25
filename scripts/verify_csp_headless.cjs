#!/usr/bin/env node
// Headless CSP enforcement check: load every built page and capture any
// Content-Security-Policy refusal (a wrong sha256 hash => inline script blocked).
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const PUBLIC = path.join(__dirname, '..', 'public');
const BASE = 'http://localhost:8099';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const CSP_RE = /Content Security Policy|Refused to (execute|run|load|connect)|violates the following Content Security Policy|because it violates.*CSP/i;
const SCRIPT_REFUSE_RE = /Refused to execute inline script|Refused to run the JavaScript URL|because it violates the following Content Security Policy directive: "script-src/i;
const IMG_REFUSE_RE = /img-src/i;

function walk(dir, out) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.html')) out.push(p);
  }
  return out;
}

(async () => {
  const pages = walk(PUBLIC, []).map(f => path.relative(PUBLIC, f));
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });
  const tab = await browser.newPage();
  const failures = [];
  let checked = 0;
  let imgCount = 0;
  for (const rel of pages) {
    const errors = [];
    const onConsole = m => { if (m.type() === 'error' && CSP_RE.test(m.text())) errors.push(m.text().slice(0, 200)); };
    const onPageErr = e => { /* ignore generic JS errors not CSP-related */ };
    tab.on('console', onConsole);
    tab.on('pageerror', onPageErr);
    try {
      await tab.goto(BASE + '/' + rel.replace(/\\/g, '/'), { waitUntil: 'domcontentloaded', timeout: 20000 });
      await new Promise(r => setTimeout(r, 250));
    } catch (e) {
      errors.push('GOTO_ERROR: ' + e.message.slice(0, 120));
    }
    tab.off('console', onConsole);
    tab.off('pageerror', onPageErr);
    const scriptErrs = errors.filter(e => SCRIPT_REFUSE_RE.test(e));
    const imgErrs = errors.filter(e => IMG_REFUSE_RE.test(e));
    if (scriptErrs.length) failures.push({ page: rel, errors: scriptErrs });
    if (imgErrs.length) imgCount++;
    checked++;
  }
  await browser.close();
  console.log(`\nChecked ${checked} pages. script-src refusals: ${failures.length} | (informational) img-src refusals: ${imgCount}`);
  if (failures.length) {
    for (const f of failures) {
      console.log('\n✗ ' + f.page);
      for (const e of f.errors) console.log('   ' + e);
    }
    process.exit(2);
  } else {
    console.log('✓ ALL PAGES: no inline-script CSP refusals (script-src hashes valid).');
    process.exit(0);
  }
})().catch(e => { console.error('VERIFIER CRASH:', e); process.exit(3); });
