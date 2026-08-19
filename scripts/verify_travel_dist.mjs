// 验证 travel-dist/travel.html 外壳 BLOB：解密后检查内容结构与图片引用清单
// 用法：node scripts/verify_travel_dist.mjs [travel-dist/travel.html] [TRAVEL_KEY]
//       默认读取 ~/.config/longxiong/travel_key（权限 600，与 ima 凭证同模式）
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { homedir } from 'node:os';

const SHELL = process.argv[2] || '/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site/travel-dist/travel.html';
const KEY_FILE = join(homedir(), '.config/longxiong/travel_key');
let PASSWORD = process.argv[3];
if (!PASSWORD) {
  try { PASSWORD = readFileSync(KEY_FILE, 'utf8').trim(); }
  catch { throw new Error('需要 TRAVEL_KEY（或先写入 ~/.config/longxiong/travel_key）'); }
}
const html = readFileSync(SHELL, 'utf8');

// 提取 BLOB / SALT
const blobM = html.match(/var BLOB="([^"]+)"/);
const saltM = html.match(/var SALT="([^"]+)"/);
if (!blobM || !saltM) { console.error('❌ 未找到 BLOB/SALT'); process.exit(1); }
const blobB64 = blobM[1], saltB64 = saltM[1];
console.log(`✓ 提取 BLOB(${blobB64.length} chars) + SALT(${saltB64.length} chars)`);

const b64ToU8 = (s) => { const b = Buffer.from(s, 'base64'); return new Uint8Array(b); };
const enc = new TextEncoder();

async function main() {
  const key = await crypto.subtle.importKey('raw', enc.encode(PASSWORD), 'PBKDF2', false, ['deriveKey'])
    .then(k => crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: b64ToU8(saltB64), iterations: 1000000, hash: 'SHA-256' },
      k, { name: 'AES-GCM', length: 256 }, false, ['decrypt']));

  const blob = b64ToU8(blobB64);
  const iv = blob.slice(0, 12), ct = blob.slice(12);
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  // gunzip（Node 22 支持 DecompressionStream）
  const ds = new DecompressionStream('gzip');
  const stream = new Blob([pt]).stream().pipeThrough(ds);
  const text = await new Response(stream).text();
  console.log(`✓ 解密成功，明文 ${text.length} 字符`);

  // 1. 板块标题
  console.log('\n=== trip 板块标题 ===');
  const titles = [...text.matchAll(/class="[^"]*tl-trip-title[^"]*"[^>]*>([^<]+)</g)].map(m => m[1].trim());
  titles.forEach(t => console.log(`  - ${t}`));

  // 2. 个人合影检查
  console.log('\n=== 个人合影合并检查 ===');
  console.log(`  「个人合影」出现: ${text.includes('个人合影') ? '✓' : '✗'}`);
  console.log(`  「宜兴」出现: ${text.includes('宜兴') ? '✓' : '✗'}`);
  console.log(`  「葛军」出现: ${text.includes('葛军') ? '✓' : '✗'}`);
  console.log(`  「宋晓峰」出现: ${text.includes('宋晓峰') ? '✓' : '✗'}`);

  // 3. data-enc 引用清单
  console.log('\n=== data-enc 引用清单 ===');
  const refs = [...new Set([...text.matchAll(/data-enc="([^"]+)"/g)].map(m => m[1]))];
  refs.sort();
  console.log(`  引用总数: ${refs.length}`);

  // 4. 与本地 enc 文件比对
  const encBase = join(dirname(SHELL), 'img/travel');
  let missing = 0, extra = 0;
  for (const r of refs) {
    const p = join(encBase, r.replace('img/travel/', ''));
    if (!existsSync(p)) { console.log(`  ❌ 缺少文件: ${r}`); missing++; }
  }
  // 收集实际 enc 文件
  const walk = (d, acc = []) => { for (const e of readdirSync(d, { withFileTypes: true })) { const p = join(d, e.name); e.isDirectory() ? walk(p, acc) : acc.push(p); } return acc; };
  const actual = walk(encBase).filter(p => p.endsWith('.enc')).map(p => 'img/travel/' + p.replace(encBase + '/', ''));
  for (const a of actual) { if (!refs.includes(a)) { console.log(`  ⚠️ 多出未引用文件: ${a}`); extra++; } }
  console.log(`  引用缺失: ${missing}，多余文件: ${extra}，本地 enc 总数: ${actual.length}`);

  console.log(missing === 0 && extra === 0 ? '\n✅ BLOB 内容与 enc 文件完全自洽' : '\n⚠️ 存在不一致，需排查');
}
main().catch(e => { console.error('❌ 失败:', e.message); process.exit(1); });
