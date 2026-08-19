// 验证 travel-dist 密文产物（分片架构，2026-08-19 起）：
//   1. 解密外壳 BLOB（内容 HTML）→ 检查板块结构与 data-enc/data-enc-href 引用清单
//   2. 逐个解密 album-*.tlpk 相册分片 → 合并 manifest → 与引用清单比对自洽性
//   3. 校验每片 magic、gzip 可解压、数据区长度闭合、每片大小 ≤300KB（CDN 稳定传输阈值）
// 用法：node scripts/verify_travel_dist.mjs [travel-dist/travel.html] [TRAVEL_KEY]
//       默认读取 ~/.config/longxiong/travel_key（权限 600，与 ima 凭证同模式）
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { homedir } from 'node:os';
import { gunzipSync } from 'node:zlib';

const SHELL = process.argv[2] || '/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site/travel-dist/travel.html';
const KEY_FILE = join(homedir(), '.config/longxiong/travel_key');
let PASSWORD = process.argv[3];
if (!PASSWORD) {
  try { PASSWORD = readFileSync(KEY_FILE, 'utf8').trim(); }
  catch { throw new Error('需要 TRAVEL_KEY（或先写入 ~/.config/longxiong/travel_key）'); }
}
const html = readFileSync(SHELL, 'utf8');
const MAX_SHARD_BYTES = 300 * 1024; // 与 encrypt_travel.mjs 中保持一致

// 提取 BLOB / SALT / ALBUM_COUNT
const blobM = html.match(/var BLOB="([^"]+)"/);
const saltM = html.match(/var SALT="([^"]+)"/);
const countM = html.match(/var ALBUM_COUNT=(\d+)/);
if (!blobM || !saltM) { console.error('❌ 未找到 BLOB/SALT'); process.exit(1); }
const blobB64 = blobM[1], saltB64 = saltM[1];
const albumCount = countM ? parseInt(countM[1], 10) : 0;
console.log(`✓ 提取 BLOB(${blobB64.length} chars) + SALT(${saltB64.length} chars) + ALBUM_COUNT=${albumCount}`);

const b64ToU8 = (s) => { const b = Buffer.from(s, 'base64'); return new Uint8Array(b); };
const enc = new TextEncoder();

// 解密 + gunzip 一个分片 → 返回 { manifest, totalBytes, nonEmpty, cipherBytes }
async function decryptShard(key, path) {
  const raw = new Uint8Array(readFileSync(path));
  const iv = raw.slice(0, 12), ct = raw.slice(12);
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  const plain = gunzipSync(Buffer.from(pt));
  const u8 = new Uint8Array(plain);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  if (dv.getUint32(0, false) !== 0x544C504B) throw new Error(`分片 magic 校验失败: ${path}`);
  const mlen = dv.getUint32(4, false);
  const manifest = JSON.parse(new TextDecoder().decode(u8.subarray(8, 8 + mlen)));
  let off = 8 + mlen;
  for (const it of manifest) {
    if (off + it.size > u8.byteLength) throw new Error(`分片数据区越界: ${it.rel}`);
    off += it.size;
  }
  if (off !== u8.byteLength) throw new Error(`分片数据区长度不闭合（${off} != ${u8.byteLength}）: ${path}`);
  let nonEmpty = 0;
  off = 8 + mlen;
  for (const it of manifest) {
    const slice = u8.subarray(off, off + Math.min(16, it.size));
    if (slice.some(b => b !== 0)) nonEmpty++;
    off += it.size;
  }
  return { manifest, totalBytes: u8.byteLength - (8 + mlen), nonEmpty, cipherBytes: raw.byteLength };
}

async function main() {
  const key = await crypto.subtle.importKey('raw', enc.encode(PASSWORD), 'PBKDF2', false, ['deriveKey'])
    .then(k => crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: b64ToU8(saltB64), iterations: 1000000, hash: 'SHA-256' },
      k, { name: 'AES-GCM', length: 256 }, false, ['decrypt']));

  const blob = b64ToU8(blobB64);
  const iv = blob.slice(0, 12), ct = blob.slice(12);
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
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

  // 4. 逐个解密分片，合并 manifest
  console.log('\n=== 相册分片 album-*.tlpk 校验 ===');
  const imgBase = join(dirname(SHELL), 'img/travel');
  const allManifest = [];
  let maxCipher = 0;
  let totalPlain = 0;
  let totalNonEmpty = 0;
  let shardFiles = [];
  const walk = (d, acc = []) => { for (const e of readdirSync(d, { withFileTypes: true })) { const p = join(d, e.name); e.isDirectory() ? walk(p, acc) : acc.push(p); } return acc; };
  shardFiles = walk(imgBase).filter(p => /album-\d+\.tlpk$/.test(p)).sort((a, b) => {
    const na = parseInt(a.match(/album-(\d+)\.tlpk/)[1], 10), nb = parseInt(b.match(/album-(\d+)\.tlpk/)[1], 10);
    return na - nb;
  });
  if (shardFiles.length !== albumCount) { console.error(`❌ 分片数不匹配：ALBUM_COUNT=${albumCount}，实际文件 ${shardFiles.length}`); process.exit(1); }
  for (const sf of shardFiles) {
    const { manifest, totalBytes, nonEmpty, cipherBytes } = await decryptShard(key, sf);
    const num = sf.match(/album-(\d+)\.tlpk/)[1];
    if (cipherBytes > MAX_SHARD_BYTES) { console.log(`  ⚠️ 片 ${num} 密文 ${(cipherBytes / 1024).toFixed(0)}KB 超过 300KB 阈值`); }
    console.log(`  ✓ 片 ${num}: ${manifest.length} 张，密文 ${(cipherBytes / 1024).toFixed(0)}KB，明文 ${(totalBytes / 1024).toFixed(0)}KB，非空 ${nonEmpty}/${manifest.length}`);
    maxCipher = Math.max(maxCipher, cipherBytes);
    totalPlain += totalBytes;
    totalNonEmpty += nonEmpty;
    allManifest.push(...manifest);
  }
  const manifestRels = allManifest.map(m => m.rel).sort();
  const missingInShards = refs.filter(r => !manifestRels.includes(r));
  const extraInShards = manifestRels.filter(r => !refs.includes(r));
  if (missingInShards.length) { console.log(`  ❌ 引用但分片内缺失: ${missingInShards.join(', ')}`); }
  if (extraInShards.length) { console.log(`  ⚠️ 分片内多出未引用: ${extraInShards.join(', ')}`); }
  console.log(`  引用↔分片比对: 缺失 ${missingInShards.length}，多余 ${extraInShards.length}，照片明文合计 ${(totalPlain / 1024).toFixed(0)}KB`);

  // 5. 校验产物目录无残留旧格式文件（.enc 逐张 / album.tlpk.enc 单包）
  const leftover = walk(imgBase).filter(p => /\.enc$/.test(p) || /album\.tlpk\.enc$/.test(p));
  if (leftover.length) { console.log(`  ⚠️ 残留旧格式文件（应清理）: ${leftover.map(p => p.split('/img/travel/')[1]).join(', ')}`); }

  const allOk = missingInShards.length === 0 && extraInShards.length === 0 && totalNonEmpty === allManifest.length && shardFiles.length === albumCount;
  console.log(allOk ? '\n✅ 产物完全自洽：外壳 BLOB ↔ 分片 manifest 零缺失零多余，照片字节可还原，分片数与外壳声明一致' : '\n⚠️ 存在不一致，需排查');
  if (!allOk) process.exit(1);
}
main().catch(e => { console.error('❌ 失败:', e.message); process.exit(1); });
