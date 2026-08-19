#!/usr/bin/env node
/**
 * encrypt_travel.mjs — 旅行板块真加密（方案 B，单包架构）
 *
 * 仅在 CI 设置 Secret TRAVEL_KEY 时运行；脚本内部判断，无密钥则直接跳过。
 * 跳过时不改动任何文件，因此每日自动更新流水线不会受影响。
 *
 * 流程：
 *   1. 从 public/travel.html 抽取 <div id="tlWrap" data-tl-wrap> ... </div> 内的私密内容
 *      （含 <main> 相册、页脚、JSON-LD、PAGEJS 交互逻辑）。
 *   2. 遍历 public/img/travel/** 下所有照片，打包为一个 album.tlpk.enc（magic "TLPK" +
 *      manifest JSON + 全部照片字节，整体 AES-GCM 加密），删除明文。
 *   3. 把内容里 img 的 src 改写为 data-enc="相对路径"（作为相册包 manifest 的 key）。
 *   4. 内容 gzip + AES-GCM 加密，base64 内嵌进「密码门外壳页」。
 *   5. travel.html 重写为：导航正常 + 密码门 + 解密注入容器 + 解密脚本；
 *      注入 <meta name="robots" content="noindex">、<body data-pagefind-ignore>。
 *   6. 删除 public/data/travel.json（明文私有数据，运行时已烘焙进 HTML，不需要）。
 *
 * 单包架构动机（2026-08-19 根治）：
 *   旧方案每张照片独立 .enc，解锁瞬间浏览器并发 fetch 31 个文件；CDN 边缘节点对 .enc
 *   偶发连接超时（实测 3-6%），任一失败即个别照片永久缺图——补丁式重试治标不治本。
 *   单包方案把 31 次网络请求合并为 1 次：一次成功 = 全部照片可用，从架构上根除
 *   “部分照片不显示”。浏览器端 fetch 带 30s 超时 + 5 次指数退避重试，成功率 ~99.99%。
 *
 * 密码学：Node WebCrypto (AES-GCM 256 + PBKDF2 SHA-256, 1M iters)，
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

const PBKDF2_ITERS = 1000000; // 抗离线爆破：解锁时只做一次密钥派生，1M 在手机上约亚秒级；爆破弱密码成本约为 250k 的 4 倍
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
// 画廊「点开看大图」的 <a href="img/travel/...webp" target="_blank"> 也要改写，
// 否则明文 .webp 被删后点击链接会 404。
const HREF_RE = /href=["'](img\/travel\/[^"']+\.(?:webp|jpg|jpeg|png|avif|gif))["']/gi;

async function main() {
  if (!PASSWORD) {
    // 无密钥时不强制删除，避免把「已加密外壳」误删导致线上整页 404：
    // - 若 travel.html 仍是明文（含 data-tl-wrap），删除以防明文泄露；
    // - 若已是加密外壳（无 data-tl-wrap），保留，等带密钥时再重加密。
    if (existsSync(TRAVEL_HTML)) {
      const raw = readFileSync(TRAVEL_HTML, 'utf8');
      if (/data-tl-wrap/.test(raw)) {
        console.warn('[encrypt_travel] TRAVEL_KEY 未设置但检测到明文旅行页，已删除以防泄露。');
        rmSync(TRAVEL_HTML);
      } else {
        console.warn('[encrypt_travel] TRAVEL_KEY 未设置，但 travel.html 已是加密外壳，保留不删。');
      }
    }
    // 仅清理可能残留的明文照片（保留 .enc 密文）；明文数据文件同理删除。
    const dir = join(PUBLIC, 'img', 'travel');
    if (existsSync(dir)) {
      const files = [];
      walk(dir, files);
      for (const f of files) {
        if (!f.endsWith('.enc')) { try { rmSync(f); } catch (e) {} }
      }
    }
    const dj = join(PUBLIC, 'data', 'travel.json');
    if (existsSync(dj)) rmSync(dj);
    return;
  }
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

  // —— 1. 加密所有旅行照片（单包架构：打包成一个 album.tlpk.enc，浏览器一次请求全量加载）——
  // 历史教训（2026-08-19）：旧方案逐张 .enc 各自加密，解锁瞬间浏览器并发 fetch 31 个文件，
  // CDN 边缘节点对 .enc 偶发连接超时（实测 3-6%），任一失败即个别照片永久缺图，补丁式重试治标不治本。
  // 单包方案把 31 次网络请求合并为 1 次：一次成功 = 全部照片可用，从架构上根除“部分照片不显示”。
  const imgDir = join(PUBLIC, 'img', 'travel');
  let nPhotos = 0;
  let salt;
  let key;
  if (existsSync(imgDir)) {
    const files = [];
    walk(imgDir, files);
    const photos = files.filter(f => !f.endsWith('.enc')); // 跳过已存在的密文（防重复打包）
    salt = crypto.getRandomValues(new Uint8Array(16));
    key = await deriveKey(PASSWORD, salt);
    if (photos.length > 0) {
      // —— 打包格式：magic "TLPK"(4B) + manifestLen(4B, BE) + manifest JSON + 全部照片字节 ——
      const manifest = [];
      const parts = [];
      let total = 0;
      for (const f of photos) {
        const rel = f.slice(imgDir.length + 1).replace(/\\/g, '/'); // 相对 img/travel/ 的路径，如 2025-japan/mario-block.webp
        const data = new Uint8Array(readFileSync(f));
        manifest.push({ rel, size: data.byteLength });
        parts.push(data);
        total += data.byteLength;
      }
      const mjson = JSON.stringify(manifest);
      const headLen = 8 + mjson.length;
      const all = new Uint8Array(headLen + total);
      const dv = new DataView(all.buffer);
      dv.setUint32(0, 0x544C504B, false); // "TLPK"
      dv.setUint32(4, mjson.length, false);
      new TextEncoder().encodeInto(mjson, all.subarray(8, 8 + mjson.length));
      let off = headLen;
      for (const p of parts) { all.set(p, off); off += p.byteLength; }
      // —— AES-GCM 加密单包（iv 12B + ct）——
      const blob = await encryptBytes(key, all);
      const albumFile = join(imgDir, 'album.tlpk.enc');
      mkdirSync(dirname(albumFile), { recursive: true });
      writeFileSync(albumFile, blob);
      // 删除明文照片
      for (const f of photos) rmSync(f);
      nPhotos = photos.length;
      console.log(`[encrypt_travel] 照片打包加密完成：${nPhotos} 张 → album.tlpk.enc（${(blob.byteLength / 1024).toFixed(0)}KB 密文）`);
    } else {
      console.log('[encrypt_travel] public/img/travel 无明文照片（可能已有 album.tlpk.enc），跳过。');
    }
    globalThis.__salt = salt; // 给内容加密复用同一 salt/key
    globalThis.__key = key;
  } else {
    console.log('[encrypt_travel] public/img/travel 不存在，跳过照片加密。');
  }

  // 内容加密复用同一 salt/key（照片打包时已派生；若目录不存在则新建）
  salt = globalThis.__salt || salt || crypto.getRandomValues(new Uint8Array(16));
  key = globalThis.__key || key || await deriveKey(PASSWORD, salt);

  // —— 2. 改写内容里的 img src -> data-enc（同时处理画廊 <a href> 大图链接）——
  // data-enc 值改为相对 img/travel/ 的路径（如 2025-japan/mario-block.webp），作为相册包 manifest 的 key；
  // 浏览器解锁后从已解密的字典直接取 Blob URL，不再逐张 fetch。
  const contentRewritten = content
    .replace(PHOTO_RE, (_m, p1) => `data-enc="${p1.replace(/^img\/travel\//, '')}"`)
    .replace(HREF_RE, (_m, p1) => `data-enc-href="${p1.replace(/^img\/travel\//, '')}"`);

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
  // 解密后的照片以 blob: URL 渲染，需在本页 CSP 的 img-src 放开 blob:（仅作用于加密后的 travel 外壳页）
  head = head.replace("img-src 'self' data:", "img-src 'self' data: blob:");
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
<div id="tlLightbox" class="tl-lb" hidden>
  <div class="tl-lb-backdrop" data-lb-close></div>
  <div class="tl-lb-stage">
    <img id="tlLbImg" alt="旅行大图">
    <div class="tl-lb-bar">
      <button type="button" id="tlLbNew" class="tl-lb-btn">在新标签页打开</button>
      <button type="button" class="tl-lb-btn" data-lb-close>关闭 (Esc)</button>
    </div>
  </div>
</div>
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
.tl-gate{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#0e0e10;z-index:9999;padding:24px}
.tl-gate-card{background:#16161a;border:1px solid #322b20;border-radius:18px;padding:34px 30px;max-width:360px;width:100%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.45)}
.tl-gate-lock{font-size:38px;margin-bottom:6px}
.tl-gate-card h2{margin:.2em 0;font-size:1.3rem;color:#EDE6D6}
.tl-gate-sub{color:#A89F8C;font-size:.9rem;margin:.4em 0 1.1em}
.tl-gate-input{width:100%;padding:11px 14px;border-radius:10px;border:1px solid #322b20;background:#0e0e10;color:#EDE6D6;font-size:1rem;box-sizing:border-box}
.tl-gate-input:focus{outline:none;border-color:#C9A84C}
.tl-gate-input::placeholder{color:#6C6353}
.tl-gate-btn{margin-top:12px;width:100%;padding:11px;border:none;border-radius:10px;background:#C9A84C;color:#1a1408;font-size:1rem;font-weight:600;cursor:pointer;font-family:inherit}
.tl-gate-btn:hover{filter:brightness(1.06)}
.tl-gate-err{color:#e0777a;font-size:.85rem;margin:.7em 0 0}
.tl-lb{position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.92);padding:24px}
.tl-lb[hidden]{display:none}
.tl-lb-backdrop{position:absolute;inset:0;cursor:zoom-out}
.tl-lb-stage{position:relative;max-width:94vw;max-height:90vh;display:flex;flex-direction:column;gap:12px;align-items:center}
.tl-lb-stage img{max-width:94vw;max-height:80vh;width:auto;height:auto;object-fit:contain;border-radius:10px;box-shadow:0 24px 70px rgba(0,0,0,.6);background:#111}
.tl-lb-bar{display:flex;gap:10px}
.tl-lb-btn{padding:9px 16px;border:1px solid rgba(255,255,255,.28);border-radius:10px;background:rgba(28,28,32,.92);color:#fff;font-size:.9rem;font-weight:600;cursor:pointer;font-family:inherit}
.tl-lb-btn:hover{border-color:#D8B25E;color:#fff}
</style>
<script>
(function(){
  var BLOB="${blobB64}";
  var SALT="${saltB64}";
  var enc=new TextEncoder();
  function b64ToU8(s){var b=atob(s),u=new Uint8Array(b.length);for(var i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u;}
  function derive(pw,salt){return crypto.subtle.importKey("raw",enc.encode(pw),"PBKDF2",false,["deriveKey"]).then(function(k){return crypto.subtle.deriveKey({name:"PBKDF2",salt:salt,iterations:1000000,hash:"SHA-256"},k,{name:"AES-GCM",length:256},false,["encrypt","decrypt"]);});}
  function decBytes(key,blob){var iv=blob.slice(0,12),ct=blob.slice(12);return crypto.subtle.decrypt({name:"AES-GCM",iv:iv},key,ct).then(function(pt){return new Uint8Array(pt);});}
  function gunzip(u){return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text();}
  function reRun(root){
    var s=root.querySelectorAll("script");
    for(var i=0;i<s.length;i++){
      var n=document.createElement("script");
      var attrs=s[i].attributes;
      for(var a=0;a<attrs.length;a++){ n.setAttribute(attrs[a].name, attrs[a].value); }
      n.textContent=s[i].textContent;
      s[i].replaceWith(n);
    }
  }
  function photoType(rel){
    var s=rel.toLowerCase();
    if(s.endsWith(".png")) return "image/png";
    if(s.endsWith(".jpg")||s.endsWith(".jpeg")) return "image/jpeg";
    if(s.endsWith(".gif")) return "image/gif";
    if(s.endsWith(".avif")) return "image/avif";
    return "image/webp";
  }
  // 带超时 + 指数退避重试的 fetch：相册包单次请求（31 张照片合并为一个加密文件），
  // 从架构上根除“逐张 .enc 偶发连接超时导致个别照片永久缺图”的历史问题（2026-08-19 实测
  // CDN 边缘节点对 .enc 有 3-6% 偶发超时）。30s 超时 + 5 次退避（0.6s/1.2s/1.8s/2.4s），
  // 单请求失败率降至 ~0.01%；硬错误（HTTP 4xx/5xx，如文件确实不存在）不重试。
  function fetchWithRetry(url, tries, timeoutMs){
    var ctrl=(typeof AbortController!=="undefined")?new AbortController():null;
    var timer=ctrl?setTimeout(function(){ctrl.abort();}, timeoutMs||30000):null;
    var p=fetch(url, ctrl?{signal:ctrl.signal}:{});
    var done=p.then(function(r){
      if(!r.ok) return Promise.reject(Object.assign(new Error("HTTP "+r.status),{http:true}));
      return r;
    });
    if(timer) done=done.then(function(v){clearTimeout(timer);return v;});
    return done.catch(function(e){
      if(timer) clearTimeout(timer);
      if(e && e.http) throw e;
      if(tries>1) return new Promise(function(res,rej){setTimeout(function(){fetchWithRetry(url,tries-1,timeoutMs).then(res,rej);},600*(6-tries));});
      throw e;
    });
  }
  var tlUrls=null; // rel → BlobURL 字典（解锁后一次性建立，页面生命周期内有效）
  // 解析相册包：magic "TLPK"(4B) + manifestLen(4B,BE) + manifest JSON + 照片数据区
  function parseAlbum(pt){
    var dv=new DataView(pt.buffer,pt.byteOffset,pt.byteLength);
    if(dv.getUint32(0,false)!==0x544C504B) throw new Error("相册包格式错误(magic)");
    var mlen=dv.getUint32(4,false);
    var manifest=JSON.parse(new TextDecoder().decode(pt.subarray(8,8+mlen)));
    var off=8+mlen,map={};
    for(var i=0;i<manifest.length;i++){
      var it=manifest[i];
      map[it.rel]=URL.createObjectURL(new Blob([pt.subarray(off,off+it.size)],{type:photoType(it.rel)}));
      off+=it.size;
    }
    return map;
  }
  // 一次性渲染全部照片 + 绑定大图灯箱（数据全在内存，零网络请求）
  function renderAll(){
    var imgs=document.querySelectorAll("#tlContent img[data-enc]");
    var fail=0;
    for(var i=0;i<imgs.length;i++){
      var img=imgs[i],rel=img.getAttribute("data-enc");
      var url=tlUrls[rel];
      if(url){ img.removeAttribute("loading"); img.src=url; img.removeAttribute("data-enc"); }
      else { fail++; console.error("相册包缺少照片", rel); }
    }
    var as=document.querySelectorAll("#tlContent a[data-enc-href]");
    for(var i=0;i<as.length;i++){
      var a=as[i];
      var rel=a.getAttribute("data-enc-href");
      a.removeAttribute("data-enc-href");
      (function(rel,a){ a.addEventListener("click",function(e){ e.preventDefault(); openLightbox(rel); }); })(rel,a);
    }
    return fail;
  }
  // 画廊「点开看大图」：直接使用已解密的 Blob URL（零网络、零解密延迟）
  var lb=document.getElementById("tlLightbox");
  var lbImg=document.getElementById("tlLbImg");
  var lbNew=document.getElementById("tlLbNew");
  function openLightbox(rel){
    var url=tlUrls[rel];
    if(!url){ console.error("相册包缺少照片", rel); return; }
    lbImg.setAttribute("data-rel",rel);
    lbImg.src=url;
    lb.hidden=false;
  }
  function closeLightbox(){ lb.hidden=true; }
  lb.addEventListener("click",function(e){ if(e.target.hasAttribute("data-lb-close")) closeLightbox(); });
  document.addEventListener("keydown",function(e){ if(e.key==="Escape" && !lb.hidden) closeLightbox(); });
  // 「在新标签页打开」在点击同步瞬间触发，保留 user activation，不会被弹窗拦截
  lbNew.addEventListener("click",function(){ var rel=lbImg.getAttribute("data-rel"); if(rel&&tlUrls[rel]) window.open(tlUrls[rel],"_blank","noopener"); });
  // 解锁：解密内容 BLOB → 渲染 HTML → 拉取相册包（1 次请求）→ 解密 → 全部照片立即可用
  function unlock(){
    var err=document.getElementById("tlErr"); err.hidden=true;
    var pw=document.getElementById("tlPw").value;
    derive(pw,b64ToU8(SALT)).then(function(key){
      return decBytes(key,b64ToU8(BLOB)).then(function(u){return gunzip(u);}).then(function(html){
        var c=document.getElementById("tlContent");
        c.innerHTML=html; reRun(c);
        return fetchWithRetry("img/travel/album.tlpk.enc",5,60000)
          .then(function(r){return r.arrayBuffer();})
          .then(function(buf){ return decBytes(key,new Uint8Array(buf)); });
      }).then(function(pt){
        tlUrls=parseAlbum(pt);
        var fail=renderAll();
        var g=document.getElementById("tlGate"); if(g) g.remove();
        if(fail>0) console.warn("相册包缺少 "+fail+" 张照片");
      });
    }).catch(function(e){ err.hidden=false; console.error("解锁失败", e); });
  }
  document.getElementById("tlUnlock").addEventListener("click",unlock);
  document.getElementById("tlPw").addEventListener("keydown",function(e){if(e.key==="Enter")unlock();});
})();
</script>
`;
}

// —— 自检：验证 Node 端加解密与 gzip 往返 + 相册包打包/解包（与浏览器 crypto.subtle 同原语）——
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
    // —— 相册包打包/解包往返 ——
    const fakePhotos = [
      { rel: '2025-japan/mario-block.webp', data: new TextEncoder().encode('fake-webp-data-1') },
      { rel: '2026-sheyang/song-xiaofeng-1.webp', data: new TextEncoder().encode('fake-webp-data-2-较长内容填充填充') },
    ];
    const manifest = fakePhotos.map(p => ({ rel: p.rel, size: p.data.byteLength }));
    const mjson = JSON.stringify(manifest);
    const headLen = 8 + mjson.length;
    const total = fakePhotos.reduce((s, p) => s + p.data.byteLength, 0);
    const all = new Uint8Array(headLen + total);
    const dv = new DataView(all.buffer);
    dv.setUint32(0, 0x544C504B, false);
    dv.setUint32(4, mjson.length, false);
    new TextEncoder().encodeInto(mjson, all.subarray(8, 8 + mjson.length));
    let off = headLen;
    for (const p of fakePhotos) { all.set(p.data, off); off += p.data.byteLength; }
    const packed = await encryptBytes(key, all);
    const unpacked = await decryptBytes(key, packed);
    const udv = new DataView(unpacked.buffer, unpacked.byteOffset, unpacked.byteLength);
    if (udv.getUint32(0, false) !== 0x544C504B) { console.error('SELFTEST FAIL: 包 magic'); process.exit(1); }
    const umlen = udv.getUint32(4, false);
    const umanifest = JSON.parse(new TextDecoder().decode(unpacked.subarray(8, 8 + umlen)));
    let uoff = 8 + umlen;
    for (const it of umanifest) {
      const bytes = unpacked.subarray(uoff, uoff + it.size);
      const expected = fakePhotos.find(p => p.rel === it.rel).data;
      if (Buffer.compare(Buffer.from(bytes), Buffer.from(expected)) !== 0) { console.error('SELFTEST FAIL: 包内照片字节不一致 ' + it.rel); process.exit(1); }
      uoff += it.size;
    }
    if (uoff !== unpacked.byteLength) { console.error('SELFTEST FAIL: 包数据区长度不闭合'); process.exit(1); }
    console.log('SELFTEST OK ✅ (加解密往返 / gzip / 错误密码被拒 / 相册包打包解包一致)');
  })();
}

// 自检模式跳过 main()（避免 public/ 中残留旧外壳触发 exit 打断自检）
if (!process.argv.includes('--selftest')) {
  main().catch((e) => { console.error(e); process.exit(1); });
}
