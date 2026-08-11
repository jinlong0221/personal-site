#!/usr/bin/env node
/**
 * encrypt_travel.mjs — 旅行板块真加密（方案 B）
 *
 * 仅在 CI 设置 Secret TRAVEL_KEY 时运行；脚本内部判断，无密钥则直接跳过。
 * 跳过时不改动任何文件，因此每日自动更新流水线不会受影响。
 *
 * 流程：
 *   1. 从 public/travel.html 抽取 <div id="tlWrap" data-tl-wrap> ... </div> 内的私密内容
 *      （含 <main> 相册、页脚、JSON-LD、PAGEJS 交互逻辑）。
 *   2. 遍历 public/img/travel/** 下所有照片，用 AES-GCM 加密为 .enc，删除明文。
 *   3. 把内容里 img 的 src 改写为 data-enc="...webp.enc"。
 *   4. 内容 gzip + AES-GCM 加密，base64 内嵌进「密码门外壳页」。
 *   5. travel.html 重写为：导航正常 + 密码门 + 解密注入容器 + 解密脚本；
 *      注入 <meta name="robots" content="noindex">、<body data-pagefind-ignore>。
 *   6. 删除 public/data/travel.json（明文私有数据，运行时已烘焙进 HTML，不需要）。
 *
 * 密码学：Node WebCrypto (AES-GCM 256 + PBKDF2 SHA-256, 250k iters)，
 *         与浏览器 crypto.subtle 字节级一致，解密逻辑在浏览器端复用同一套原语。
 */
import { webcrypto as crypto } from 'node:crypto';
import { gzipSync, gunzipSync } from 'node:zlib';
import { readFileSync, writeFileSync, rmSync, existsSync, readdirSync, statSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const PUBLIC = process.env.PUBLIC ? process.env.PUBLIC : join(ROOT, 'public');
const TRAVEL_HTML = join(PUBLIC, 'travel.html');
const PASSWORD = process.env.TRAVEL_KEY;

const PBKDF2_ITERS = 250000;
const enc = new TextEncoder();

function b64(buf) { return Buffer.from(buf).toString('base64'); }
function fromB64(s) { return new Uint8Array(Buffer.from(s, 'base64')); }

async function deriveKey(password, salt) {
  const base = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITERS, hash: 'SHA-256' },
    base, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}

// 返回 iv(12) + ct 的合并字节数组
async function encryptBytes(key, data) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, data);
  const out = new Uint8Array(12 + ct.byteLength);
  out.set(iv, 0);
  out.set(new Uint8Array(ct), 12);
  return out;
}
async function decryptBytes(key, blob) {
  const iv = blob.slice(0, 12);
  const ct = blob.slice(12);
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  return new Uint8Array(pt);
}

function walk(dir, out) {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) walk(p, out);
    else out.push(p);
  }
}

const PHOTO_RE = /src=["'](img\/travel\/[^"']+\.(?:webp|jpg|jpeg|png|avif|gif))["']/gi;

async function main() {
  if (!PASSWORD) { console.log('[encrypt_travel] TRAVEL_KEY 未设置，跳过加密（旅行页保持公开）。'); return; }
  if (!existsSync(TRAVEL_HTML)) { console.log('[encrypt_travel] public/travel.html 不存在，跳过。'); return; }

  let html = readFileSync(TRAVEL_HTML, 'utf8');
  const openTag = '<div id="tlWrap" data-tl-wrap>';
  const oi = html.indexOf(openTag);
  if (oi < 0) { console.error('[encrypt_travel] 未找到 tlWrap 标记，终止（避免部署未加密页面）。'); process.exit(1); }

  const bodyIdx = html.lastIndexOf('</body>');
  if (bodyIdx < 0) { console.error('[encrypt_travel] 未找到 </body>，终止。'); process.exit(1); }
  const cdi = html.lastIndexOf('</div>', bodyIdx); // tlWrap 的闭合 </div>（紧邻 </body>）
  if (cdi < 0) { console.error('[encrypt_travel] 未找到 tlWrap 闭合标记，终止。'); process.exit(1); }

  const content = html.slice(oi + openTag.length, cdi);

  // —— 1. 加密所有旅行照片 ——
  const imgDir = join(PUBLIC, 'img', 'travel');
  let nPhotos = 0;
  if (existsSync(imgDir)) {
    const files = [];
    walk(imgDir, files);
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const key = await deriveKey(PASSWORD, salt);
    for (const f of files) {
      const data = new Uint8Array(readFileSync(f));
      const blob = await encryptBytes(key, data);
      const encFile = f + '.enc';
      mkdirSync(dirname(encFile), { recursive: true });
      writeFileSync(encFile, blob);
      rmSync(f);
      nPhotos++;
    }
    globalThis.__salt = salt; // 给内容加密复用同一 salt/key
    globalThis.__key = key;
  } else {
    console.log('[encrypt_travel] public/img/travel 不存在，跳过照片加密。');
  }

  const salt = globalThis.__salt || crypto.getRandomValues(new Uint8Array(16));
  const key = globalThis.__key || await deriveKey(PASSWORD, salt);

  // —— 2. 改写内容里的 img src -> data-enc ——
  const contentRewritten = content.replace(PHOTO_RE, (_m, p1) => `data-enc="${p1}.enc"`);

  // —— 3. 内容 gzip + AES-GCM 加密 ——
  const gz = gzipSync(Buffer.from(contentRewritten, 'utf8'));
  const blob = await encryptBytes(key, new Uint8Array(gz));
  const blobB64 = b64(blob);
  const saltB64 = b64(salt);

  // —— 4. 组装外壳页（导航/页脚保留，正文区替换为密码门 + 解密容器）——
  let head = html.slice(0, oi);              // 含 <head> + 导航（已渲染）
  const tail = html.slice(cdi + '</div>'.length); // 含全局脚本 + </body></html>

  if (!/name=["']robots["']/.test(head)) {
    head = head.replace('</head>', '<meta name="robots" content="noindex">\n</head>');
  }
  head = head.replace('<body>', '<body data-pagefind-ignore>');

  const shell = head + buildGate(blobB64, saltB64) + tail;
  writeFileSync(TRAVEL_HTML, shell);

  // —— 5. 删除明文私有数据文件 ——
  const dj = join(PUBLIC, 'data', 'travel.json');
  if (existsSync(dj)) rmSync(dj);

  console.log(`[encrypt_travel] 完成：外壳页已写入，照片加密 ${nPhotos} 张，已注入 noindex + data-pagefind-ignore。`);
}

function buildGate(blobB64, saltB64) {
  return `
<div id="tlContent" data-pagefind-ignore></div>
<div id="tlGate" class="tl-gate">
  <div class="tl-gate-card">
    <div class="tl-gate-lock" aria-hidden="true">🔒</div>
    <h2>家庭旅行 · 私密相册</h2>
    <p class="tl-gate-sub">本页仅限家人查看，请输入访问密码。</p>
    <input type="password" id="tlPw" class="tl-gate-input" placeholder="请输入密码" autocomplete="off" aria-label="访问密码" inputmode="text">
    <button id="tlUnlock" class="tl-gate-btn" type="button">解锁查看</button>
    <p id="tlErr" class="tl-gate-err" hidden>密码错误，请重试。</p>
  </div>
</div>
<style>
.tl-gate{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:var(--bg,#0e0e10);z-index:9999;padding:24px}
.tl-gate-card{background:var(--surface,#16161a);border:1px solid var(--border,#2a2a30);border-radius:18px;padding:34px 30px;max-width:360px;width:100%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.45)}
.tl-gate-lock{font-size:38px;margin-bottom:6px}
.tl-gate-card h2{margin:.2em 0;font-size:1.3rem;color:var(--text,#eee)}
.tl-gate-sub{color:var(--text-muted,#9aa);font-size:.9rem;margin:.4em 0 1.1em}
.tl-gate-input{width:100%;padding:11px 14px;border-radius:10px;border:1px solid var(--border,#2a2a30);background:var(--bg,#0e0e10);color:var(--text,#eee);font-size:1rem;box-sizing:border-box}
.tl-gate-input:focus{outline:none;border-color:var(--gold,#c9a14a)}
.tl-gate-btn{margin-top:12px;width:100%;padding:11px;border:none;border-radius:10px;background:var(--gold,#c9a14a);color:#1a1408;font-size:1rem;font-weight:600;cursor:pointer;font-family:inherit}
.tl-gate-btn:hover{filter:brightness(1.06)}
.tl-gate-err{color:#e0777a;font-size:.85rem;margin:.7em 0 0}
</style>
<script>
(function(){
  var BLOB="${blobB64}";
  var SALT="${saltB64}";
  var enc=new TextEncoder();
  function b64ToU8(s){var b=atob(s),u=new Uint8Array(b.length);for(var i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u;}
  function derive(pw,salt){return crypto.subtle.importKey("raw",enc.encode(pw),"PBKDF2",false,["deriveKey"]).then(function(k){return crypto.subtle.deriveKey({name:"PBKDF2",salt:salt,iterations:250000,hash:"SHA-256"},k,{name:"AES-GCM",length:256},false,["encrypt","decrypt"]);});}
  function decBytes(key,blob){var iv=blob.slice(0,12),ct=blob.slice(12);return crypto.subtle.decrypt({name:"AES-GCM",iv:iv},key,ct).then(function(pt){return new Uint8Array(pt);});}
  function gunzip(u){return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text();}
  function reRun(root){var s=root.querySelectorAll("script");for(var i=0;i<s.length;i++){var n=document.createElement("script");n.textContent=s[i].textContent;s[i].replaceWith(n);}}
  function decryptPhoto(img,key){
    var rel=img.getAttribute("data-enc");
    fetch(rel).then(function(r){return r.arrayBuffer();}).then(function(buf){return decBytes(key,new Uint8Array(buf));})
      .then(function(u){return URL.createObjectURL(new Blob([u]));})
      .then(function(url){img.src=url;img.removeAttribute("data-enc");})
      .catch(function(e){console.error("照片解密失败",rel,e);});
  }
  function loadPhotos(key){
    var root=document.getElementById("tlContent");
    var hero=root.querySelector(".tl-hero-img");
    var imgs=root.querySelectorAll("img[data-enc]");
    for(var i=0;i<imgs.length;i++){
      var img=imgs[i];
      if(img===hero){ decryptPhoto(img,key); }
      else if("IntersectionObserver" in window){
        (function(im){var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){decryptPhoto(im,key);io.unobserve(im);}});});io.observe(im);})(img);
      } else { decryptPhoto(img,key); }
    }
  }
  function unlock(){
    var err=document.getElementById("tlErr"); err.hidden=true;
    var pw=document.getElementById("tlPw").value;
    derive(pw,b64ToU8(SALT)).then(function(key){
      return decBytes(key,b64ToU8(BLOB)).then(function(u){return gunzip(u);}).then(function(html){
        var c=document.getElementById("tlContent");
        c.innerHTML=html; reRun(c);
        loadPhotos(key);
        var g=document.getElementById("tlGate"); if(g) g.remove();
      });
    }).catch(function(e){ err.hidden=false; });
  }
  document.getElementById("tlUnlock").addEventListener("click",unlock);
  document.getElementById("tlPw").addEventListener("keydown",function(e){if(e.key==="Enter")unlock();});
})();
</script>
`;
}

// —— 自检：验证 Node 端加解密与 gzip 往返（与浏览器 crypto.subtle 同原语）——
if (process.argv.includes('--selftest')) {
  (async () => {
    const pw = '测试密码-Abc123-🔑';
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const key = await deriveKey(pw, salt);
    const orig = enc.encode('<main>家庭旅行 <img src="img/travel/a.webp"> 测试内容 123</main>');
    const blob = await encryptBytes(key, orig);
    const back = await decryptBytes(key, blob);
    if (Buffer.compare(Buffer.from(back), Buffer.from(orig)) !== 0) { console.error('SELFTEST FAIL: 内容不一致'); process.exit(1); }
    const gz = gzipSync(Buffer.from('内容测试'.repeat(80)));
    if (gunzipSync(gz).toString('utf8') !== '内容测试'.repeat(80)) { console.error('SELFTEST FAIL: gzip'); process.exit(1); }
    // 错误密码必须解密失败
    const badKey = await deriveKey('wrong', salt);
    let failed = false;
    try { await decryptBytes(badKey, blob); } catch (e) { failed = true; }
    if (!failed) { console.error('SELFTEST FAIL: 错误密码竟能解密'); process.exit(1); }
    console.log('SELFTEST OK ✅ (加解密往返一致 / gzip 一致 / 错误密码被拒)');
  })();
}

main().catch((e) => { console.error(e); process.exit(1); });
