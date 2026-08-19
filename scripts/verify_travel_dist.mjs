// 验证 travel-dist 密文产物（单包架构，2026-08-19 起）：
//   1. 解密外壳 BLOB（内容 HTML）→ 检查板块结构与 data-enc/data-enc-href 引用清单
//   2. 解密 album.tlpk.enc 相册包 → 解析 manifest → 与引用清单比对自洽性
//   3. 校验包内照片字节可还原、magic 正确、数据区长度闭合
// 用法：node scripts/verify_travel_dist.mjs [travel-dist/travel.html] [TRAVEL_KEY]
//       默认读取 ~/.config/longxiong/travel_key（权限 600，与 ima 凭证同模式）
import { readFileSync, existsSync, statSync, readdirSync } from 'node:fs';
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

async function decryptAlbum(key) {
  const albumPath = join(dirname(SHELL), 'img/travel/album.tlpk.enc');
  if (!existsSync(albumPath)) throw new Error(`相册包不存在: ${albumPath}`);
  const raw = new Uint8Array(readFileSync(albumPath));
  const iv = raw.slice(0, 12), ct = raw.slice(12);
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  const u8 = new Uint8Array(pt);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  if (dv.getUint32(0, false) !== 0x544C504B) throw new Error('相册包 magic 校验失败（非 TLPK）');
  const mlen = dv.getUint32(4, false);
  const manifest = JSON.parse(new TextDecoder().decode(u8.subarray(8, 8 + mlen)));
  // 校验数据区闭合：最后一字节偏移应等于总长
  let off = 8 + mlen;
  for (const it of manifest) {
    if (off + it.size > u8.byteLength) throw new Error(`相册包数据区越界: ${it.rel}`);
    off += it.size;
  }
  if (off !== u8.byteLength) throw new Error(`相册包数据区长度不闭合（${off} != ${u8.byteLength}）`);
  // 抽查字节可还原：校验每个条目首个 16 字节非空（防全零数据）
  let nonEmpty = 0;
  off = 8 + mlen;
  for (const it of manifest) {
    const slice = u8.subarray(off, off + Math.min(16, it.size));
    if (slice.some(b => b !== 0)) nonEmpty++;
    off += it.size;
  }
  return { manifest, totalBytes: u8.byteLength - (8 + mlen), nonEmpty };
}

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
  console.log(`✓ 外壳 BLOB 解密成功，明文 ${text.length} 字符`);

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

  // 3. 引用清单（data-enc + data-enc-href）
  console.log('\n=== 相册引用清单 ===');
  const refs = [...new Set([
    ...[...text.matchAll(/data-enc="([^"]+)"/g)].map(m => m[1]),
    ...[...text.matchAll(/data-enc-href="([^"]+)"/g)].map(m => m[1]),
  ])];
  refs.sort();
  console.log(`  引用总数: ${refs.length}`);

  // 4. 解密相册包，比对自洽性
  console.log('\n=== 相册包 album.tlpk.enc 校验 ===');
  const album = await decryptAlbum(key);
  const manifestRels = album.manifest.map(m => m.rel).sort();
  console.log(`  包内照片数: ${manifestRels.length}，数据区 ${(album.totalBytes / 1024).toFixed(0)}KB，非空条目 ${album.nonEmpty}/${manifestRels.length}`);
  const missingInAlbum = refs.filter(r => !manifestRels.includes(r));
  const extraInAlbum = manifestRels.filter(r => !refs.includes(r));
  if (missingInAlbum.length) { console.log(`  ❌ 引用但包内缺失: ${missingInAlbum.join(', ')}`); }
  if (extraInAlbum.length) { console.log(`  ⚠️ 包内多出未引用: ${extraInAlbum.join(', ')}`); }
  console.log(`  引用↔包内比对: 缺失 ${missingInAlbum.length}，多余 ${extraInAlbum.length}`);

  // 5. 校验产物目录无残留旧 .enc 逐张文件（单包架构应只保留 album.tlpk.enc）
  const imgBase = join(dirname(SHELL), 'img/travel');
  const walk = (d, acc = []) => { for (const e of readdirSync(d, { withFileTypes: true })) { const p = join(d, e.name); e.isDirectory() ? walk(p, acc) : acc.push(p); } return acc; };
  const leftover = walk(imgBase).filter(p => p.endsWith('.enc') && !p.endsWith('album.tlpk.enc'));
  if (leftover.length) { console.log(`  ⚠️ 残留旧逐张 .enc（应清理）: ${leftover.map(p => p.split('/img/travel/')[1]).join(', ')}`); }

  const allOk = missingInAlbum.length === 0 && extraInAlbum.length === 0 && album.nonEmpty === manifestRels.length && album.totalBytes > 0;
  console.log(allOk ? '\n✅ 产物完全自洽：外壳 BLOB ↔ 相册包 manifest 零缺失零多余，照片字节可还原' : '\n⚠️ 存在不一致，需排查');
  if (!allOk) process.exit(1);
}
main().catch(e => { console.error('❌ 失败:', e.message); process.exit(1); });
