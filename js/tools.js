/*!
 * tools.js — 龙兄知识库「工具箱」纯前端引擎（主文件 / 框架）
 *
 * 设计红线（与站点安全基线一致，改动前先读）：
 *   1. 零外部依赖、零 CDN、零网络请求。所有算法（QR 编码 / PDF 合成 / ZIP 打包 /
 *      WAV 编码 / EXIF 解析 / 差异比对）都在自己的 JS 里实现，全部跑在用户设备上。
 *   2. 文件绝不离开浏览器：不使用 fetch / XMLHttpRequest / WebSocket，不往任何地方传字节。
 *   3. 不用内联事件处理器（onclick= 等），一律 addEventListener —— 页面 CSP 的
 *      script-src 只有 'self' + sha256 白名单，没有 'unsafe-inline'。
 *   4. 折叠状态挂在 <html class="tools-js"> 上：JS 没跑起来时全部面板可见，
 *      内容零丢失（与 apple-tabs.js 同一约定）。
 *
 * 文件结构：
 *   本文件 = 框架。公共底座 + 面板路由 + 按需加载器。
 *   每个工具的实现放在 static/js/tools/<id>.js，点开对应卡片时才注入执行
 *   （首屏不下载、不执行，某个子文件出错也拖不垮别的工具）。
 *   子文件通过顶部 `var x = _.x` 从 window.LXTools.api 取得公共函数，
 *   它们之间互不依赖——要加工具只需加一个子文件并在页面里加一张卡片。
 */
(function () {
  'use strict';

  /* ======================================================================
     1. 通用底座
     ====================================================================== */
  var doc = document;

  function $(sel, root) { return (root || doc).querySelector(sel); }
  function $$(sel, root) {
    return Array.prototype.slice.call((root || doc).querySelectorAll(sel));
  }

  function fmtBytes(n) {
    if (!isFinite(n) || n < 0) return '—';
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1024 / 1024).toFixed(2) + ' MB';
  }

  function fmtNum(n, d) { return Number(n).toFixed(d === undefined ? 0 : d); }

  function hex2(n) { return (n < 16 ? '0' : '') + n.toString(16); }

  function rgbToHex(r, g, b) {
    return '#' + hex2(r) + hex2(g) + hex2(b);
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function baseName(name) {
    return String(name).replace(/\.[^.]+$/, '');
  }

  function extOf(name) {
    var m = /\.([^.]+)$/.exec(String(name));
    return m ? m[1].toLowerCase() : '';
  }

  /** 触发浏览器下载（纯本地 Blob，不产生任何网络请求） */
  function download(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = doc.createElement('a');
    a.href = url;
    a.download = filename;
    a.rel = 'noopener';
    doc.body.appendChild(a);
    a.click();
    doc.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }

  function toast(panel, text, kind) {
    var msg = $('[data-msg]', panel);
    if (!msg) return;
    msg.textContent = text;
    msg.className = 'tl-msg on ' + (kind || 'ok');
    if (kind !== 'err') {
      clearTimeout(msg._t);
      msg._t = setTimeout(function () { msg.className = 'tl-msg'; }, 5200);
    }
  }

  function setStat(panel, cells, note) {
    var box = $('[data-stat]', panel);
    if (!box) return;
    if (!cells || !cells.length) { box.className = 'tl-stat'; box.innerHTML = ''; return; }
    var html = '<div class="tl-stat-grid">';
    for (var i = 0; i < cells.length; i++) {
      html += '<div class="tl-stat-cell"><div class="tl-stat-k">' + esc(cells[i][0]) +
        '</div><div class="tl-stat-v">' + esc(cells[i][1]) + '</div></div>';
    }
    html += '</div>';
    if (note) html += '<div class="tl-stat-note">' + note + '</div>';
    box.innerHTML = html;
    box.className = 'tl-stat on';
  }

  /* ---- 位图读取：优先 createImageBitmap，退化到 Image ---- */
  function loadBitmap(file) {
    if (typeof createImageBitmap === 'function') {
      return createImageBitmap(file).catch(function () { return loadViaImg(file); });
    }
    return loadViaImg(file);
  }

  function loadViaImg(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        // 用 canvas 转成"可随时 drawImage 而不依赖 url 存活"的对象
        var c = doc.createElement('canvas');
        c.width = img.naturalWidth; c.height = img.naturalHeight;
        c.getContext('2d').drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        resolve(c);
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error('无法解码这张图片')); };
      img.src = url;
    });
  }

  function bitmapSize(bmp) {
    return { w: bmp.width || bmp.naturalWidth, h: bmp.height || bmp.naturalHeight };
  }

  function newCanvas(w, h) {
    var c = doc.createElement('canvas');
    c.width = Math.max(1, Math.round(w));
    c.height = Math.max(1, Math.round(h));
    return c;
  }

  function canvasToBlob(canvas, type, quality) {
    return new Promise(function (resolve, reject) {
      canvas.toBlob(function (b) {
        if (b) resolve(b); else reject(new Error('当前浏览器不支持导出 ' + type));
      }, type, quality);
    });
  }

  function blobToBytes(blob) {
    return blob.arrayBuffer().then(function (ab) { return new Uint8Array(ab); });
  }

  /* ---- CRC32 + 最小 ZIP（store 模式，不压缩）---- */
  var CRC_TABLE = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) {
      var c = n;
      for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      t[n] = c >>> 0;
    }
    return t;
  })();

  function crc32(bytes) {
    var c = 0xFFFFFFFF;
    for (var i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  /**
   * 打包成 ZIP（store 方式，仅做归档不做压缩——图片/音频本身已是压缩格式）。
   * @param {Array<{name:string,bytes:Uint8Array}>} entries
   */
  function zipStore(entries) {
    var chunks = [], central = [], offset = 0;
    var enc = new TextEncoder();

    function u16(v) { return new Uint8Array([v & 0xFF, (v >>> 8) & 0xFF]); }
    function u32(v) { return new Uint8Array([v & 0xFF, (v >>> 8) & 0xFF, (v >>> 16) & 0xFF, (v >>> 24) & 0xFF]); }
    function cat(arrs) {
      var len = 0, i;
      for (i = 0; i < arrs.length; i++) len += arrs[i].length;
      var out = new Uint8Array(len), p = 0;
      for (i = 0; i < arrs.length; i++) { out.set(arrs[i], p); p += arrs[i].length; }
      return out;
    }

    entries.forEach(function (e) {
      var nameBytes = enc.encode(e.name);
      var crc = crc32(e.bytes);
      // ZIP 规范要求 DOS 时间；这里固定一个值，避免同一批文件因为秒数不同而校验和不同
      var dosTime = 0x6000, dosDate = 0x5A21; // 2025-01-01 12:00
      var local = cat([
        u32(0x04034b50), u16(20), u16(0x0800), u16(0), u16(dosTime), u16(dosDate),
        u32(crc), u32(e.bytes.length), u32(e.bytes.length), u16(nameBytes.length), u16(0),
        nameBytes, e.bytes
      ]);
      chunks.push(local);
      central.push(cat([
        u32(0x02014b50), u16(20), u16(20), u16(0x0800), u16(0), u16(dosTime), u16(dosDate),
        u32(crc), u32(e.bytes.length), u32(e.bytes.length),
        u16(nameBytes.length), u16(0), u16(0), u16(0), u16(0), u32(0),
        u32(offset), nameBytes
      ]));
      offset += local.length;
    });

    var cd = cat(central);
    var end = cat([
      u32(0x06054b50), u16(0), u16(0), u16(entries.length), u16(entries.length),
      u32(cd.length), u32(offset), u16(0)
    ]);
    return cat([cat(chunks), cd, end]);
  }

  /* ---- 文件投放区 ---- */
  /**
   * @param {HTMLElement} panel
   * @param {{items?:Array, multiple?:boolean, onAdd:Function}} cfg items 传调用方的列表，双方共用同一个数组
   */
  function bindDrop(panel, cfg) {
    var drop = $('[data-drop]', panel);
    if (!drop) return null;
    var input = $('input[type=file]', drop);
    // 直接写进调用方传进来的数组：两边共用同一份，避免各存一份而列表读不到文件
    var store = cfg.items || [];
    var box = {
      items: store,
      pick: function () { input.click(); },
      add: function (fileList) {
        var arr = Array.prototype.slice.call(fileList || []);
        if (!cfg.multiple) {
          arr = arr.slice(0, 1);
          store.forEach(function (it) { if (it.thumb) URL.revokeObjectURL(it.thumb); });
          store.length = 0;
        }
        arr.forEach(function (f) { store.push({ file: f, out: null, outName: '', meta: '' }); });
        if (cfg.onAdd) cfg.onAdd(store, arr);
      },
      clear: function () {
        store.forEach(function (it) { if (it.thumb) URL.revokeObjectURL(it.thumb); });
        store.length = 0;
      }
    };
    drop.addEventListener('click', function (e) {
      if (e.target !== input) input.click();
    });
    input.addEventListener('change', function () {
      box.add(input.files);
      input.value = '';
    });
    ['dragenter', 'dragover'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) {
        e.preventDefault(); e.stopPropagation();
        drop.classList.add('is-over');
      });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) {
        e.preventDefault(); e.stopPropagation();
        if (ev === 'dragleave' && drop.contains(e.relatedTarget)) return;
        drop.classList.remove('is-over');
      });
    });
    drop.addEventListener('drop', function (e) {
      var dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length) box.add(dt.files);
    });
    return box;
  }

  /** 渲染文件列表（含结果体积、缩略图、上移下移、单张下载） */
  function renderList(panel, items, opts) {
    opts = opts || {};
    var list = $('[data-list]', panel);
    if (!list) return;
    if (!items.length) { list.innerHTML = ''; return; }
    var html = '';
    items.forEach(function (it, i) {
      var thumb = it.thumb ? '<img class="tl-item-th" src="' + it.thumb + '" alt="">' :
        '<span class="tl-item-th"></span>';
      var meta = opts.meta ? opts.meta(it, i) : '';
      var acts = '';
      if (opts.reorder) {
        acts += '<button class="tl-mini" type="button" data-mv="up" data-i="' + i + '"' +
          (i === 0 ? ' disabled' : '') + ' aria-label="上移">↑</button>' +
          '<button class="tl-mini" type="button" data-mv="down" data-i="' + i + '"' +
          (i === items.length - 1 ? ' disabled' : '') + ' aria-label="下移">↓</button>';
      }
      if (it.out) {
        acts += '<button class="tl-mini" type="button" data-save="' + i + '">下载</button>';
      }
      acts += '<button class="tl-mini" type="button" data-del="' + i + '" aria-label="移除">×</button>';
      html += '<div class="tl-item">' + thumb +
        '<div class="tl-item-main"><div class="tl-item-nm" title="' + esc(it.file.name) + '">' +
        esc(it.file.name) + '</div><div class="tl-item-mt">' + meta + '</div></div>' +
        (acts ? '<div class="tl-item-act">' + acts + '</div>' : '') + '</div>';
    });
    list.innerHTML = html;

    $$('[data-del]', list).forEach(function (b) {
      b.addEventListener('click', function () {
        var i = +b.getAttribute('data-del');
        if (items[i] && items[i].thumb) URL.revokeObjectURL(items[i].thumb);
        items.splice(i, 1);
        if (opts.onChange) opts.onChange();
      });
    });
    $$('[data-mv]', list).forEach(function (b) {
      b.addEventListener('click', function () {
        var i = +b.getAttribute('data-i');
        var d = b.getAttribute('data-mv') === 'up' ? -1 : 1;
        var j = i + d;
        if (j < 0 || j >= items.length) return;
        var t = items[i]; items[i] = items[j]; items[j] = t;
        if (opts.onChange) opts.onChange();
      });
    });
    $$('[data-save]', list).forEach(function (b) {
      b.addEventListener('click', function () {
        var it = items[+b.getAttribute('data-save')];
        if (it && it.out) download(it.out, it.outName || outNameOf(it));
      });
    });
  }

  function outNameOf(it) {
    return baseName(it.file.name) + (it.outExt || '-out');
  }

  /** 批量打包下载 */
  function zipItems(items, zipName) {
    var ready = items.filter(function (it) { return it.out; });
    if (!ready.length) return Promise.reject(new Error('还没有可下载的结果'));
    var used = {};
    return Promise.all(ready.map(function (it) {
      return blobToBytes(it.out).then(function (b) {
        var nm = it.outName || outNameOf(it);
        if (used[nm]) nm = baseName(nm) + '-' + (++used[nm]) + '.' + extOf(nm);
        else used[nm] = 1;
        return { name: nm, bytes: b };
      });
    })).then(function (entries) {
      download(new Blob([zipStore(entries)], { type: 'application/zip' }), zipName);
      return entries.length;
    });
  }

  /** 生成缩略图 dataURL（列表里显示用；尺寸很小，不占内存） */
  function thumbOf(bmp) {
    var s = bitmapSize(bmp);
    var sc = Math.min(1, 76 / Math.max(1, Math.max(s.w, s.h)));
    var c = newCanvas(s.w * sc, s.h * sc);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    try { return c.toDataURL('image/jpeg', 0.7); } catch (e) { return ''; }
  }

  /* ======================================================================
     2. 面板辅助与公共工具
     ====================================================================== */
  function panelOf(id) { return doc.getElementById('tp-' + id); }
  function field(P, name) { return P.querySelector('[data-in="' + name + '"]'); }
  function outEl(P, name) { return P.querySelector('[data-out="' + name + '"]'); }
  function btnOf(P, act) { return P.querySelector('[data-act="' + act + '"]'); }

  function valOf(P, name) {
    var el = field(P, name);
    if (!el) return undefined;
    return el.type === 'checkbox' ? el.checked : el.value;
  }
  function numOf(P, name, dflt) {
    var v = parseFloat(valOf(P, name));
    return isFinite(v) ? v : dflt;
  }

  /** 把 range / number 的当前值实时写进对应的 <output> */
  function bindOutputs(P) {
    $$('[data-in]', P).forEach(function (el) {
      var o = outEl(P, el.getAttribute('data-in'));
      if (!o || el.type === 'checkbox' || el.tagName === 'SELECT') return;
      var sync = function () { o.textContent = el.value; };
      el.addEventListener('input', sync);
      sync();
    });
  }

  /**
   * 面板内的分段切换：把 [data-seg-tab="x"] 和 [data-sub="x"] 对起来。
   *
   * 默认（脚本没跑起来）时：分段条本身是 display:none（见页面 CSS 的 .tl-seg），
   * 各子块的标题文字可见、内容全部平铺——所以子块的隐藏只能靠这里的 is-off，
   * 绝不能在 HTML 里写死 tl-hidden，否则脚本一失效就丢内容。
   */
  function bindSeg(P) {
    var seg = $('[data-seg]', P);
    if (!seg) return;
    var tabs = $$('[data-seg-tab]', seg);
    var subs = $$('[data-sub]', P);
    if (!tabs.length || !subs.length) return;

    function pick(name) {
      tabs.forEach(function (t) {
        var on = t.getAttribute('data-seg-tab') === name;
        t.classList.toggle('on', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      subs.forEach(function (s) {
        s.classList.toggle('is-off', s.getAttribute('data-sub') !== name);
      });
    }

    tabs.forEach(function (t) {
      t.addEventListener('click', function () { pick(t.getAttribute('data-seg-tab')); });
    });
    var cur = tabs.filter(function (t) { return t.classList.contains('on'); })[0] || tabs[0];
    pick(cur.getAttribute('data-seg-tab'));
  }

  /** 顺序处理，不并行：一次解码几十张图容易把内存打满 */
  function runSeq(items, worker) {
    var i = 0;
    return new Promise(function (resolve, reject) {
      (function step() {
        if (i >= items.length) return resolve();
        var it = items[i], n = i++;
        Promise.resolve().then(function () { return worker(it, n); }).then(step, reject);
      })();
    });
  }

  function sizeCell(before, after) {
    if (!after) return [['原始体积', fmtBytes(before)]];
    var pct = before ? Math.round((1 - after / before) * 100) : 0;
    return [
      ['原始体积', fmtBytes(before)],
      ['处理后', fmtBytes(after)],
      [pct >= 0 ? '减小' : '增大', (pct >= 0 ? '' : '+') + (pct >= 0 ? pct : -pct) + '%']
    ];
  }

  /** 比例缩放，且保证长边不超过 limit（limit=0 表示不限制） */
  function fitSize(w, h, limit) {
    if (!limit || Math.max(w, h) <= limit) return { w: w, h: h };
    var sc = limit / Math.max(w, h);
    return { w: Math.max(1, Math.round(w * sc)), h: Math.max(1, Math.round(h * sc)) };
  }

  /** 浏览器抛的错是英文原文（"Unable to decode audio data"、"The source image could not
       be decoded." 之类），直接摆到界面上读者看不懂。这里把常见几种翻成大白话；翻不到的
      用调用方给的兜底说法——宁可说得笼统，也不把英文糊给读者。自己代码里抛的中文提示
      （那是写给人看的）原样透出。 */
  var PLAIN_ERR = [
    [/decode audio|unable to decode/i,
      '这个文件浏览器解不开。mp3、m4a、wav 一般都能读，读不了多半是格式特殊，或者文件已损坏'],
    [/could not be decoded|image.*decod|invalidstateerror/i,
      '这张图浏览器读不出来，可能不是常见的图片格式，或者文件已损坏'],
    [/quotaexceeded|out of memory|buffer allocation|allocation size/i,
      '文件太大，浏览器内存装不下，换成小一点的再试'],
    [/securityerror|tainted|not allowed|permission/i,
      '出于安全限制读不了这个文件的内容，换成本地文件再试'],
    [/encodingerror|not supported|unsupported/i,
      '浏览器不支持这个格式']
  ];

  function plainErr(e, fallback) {
    var raw = (e && e.message) || '';
    for (var i = 0; i < PLAIN_ERR.length; i++) {
      if (PLAIN_ERR[i][0].test(raw)) return PLAIN_ERR[i][1];
    }
    if (/[\u4e00-\u9fa5]/.test(raw)) return raw;   // 我们自己写的中文提示，原样用
    return fallback || '这一步没做成，换个文件再试一次';
  }

  function drawToCanvas(bmp, w, h, bg) {
    var c = newCanvas(w, h);
    var ctx = c.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    if (bg) { ctx.fillStyle = bg; ctx.fillRect(0, 0, c.width, c.height); }
    ctx.drawImage(bmp, 0, 0, c.width, c.height);
    return c;
  }

  function concatBytes(arrs) {
    var len = 0, i;
    for (i = 0; i < arrs.length; i++) len += arrs[i].length;
    var out = new Uint8Array(len), p = 0;
    for (i = 0; i < arrs.length; i++) { out.set(arrs[i], p); p += arrs[i].length; }
    return out;
  }

  /** 清掉面板上的提示条 */
  function clearToast(P) {
    var msg = $('[data-msg]', P);
    if (!msg) return;
    clearTimeout(msg._t);
    msg.className = 'tl-msg';
    msg.textContent = '';
  }

  /** 复制文字：优先用剪贴板 API，老浏览器退回 execCommand */
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (res, rej) {
      var ta = doc.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-1000px';
      doc.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = doc.execCommand('copy'); } catch (e) { ok = false; }
      doc.body.removeChild(ta);
      ok ? res() : rej(new Error('这个浏览器不允许自动复制，请手动选中'));
    });
  }

  /** 把 canvas 当图片塞进剪贴板（Safari / Chrome 支持，其余给出提示） */
  function copyCanvas(cv) {
    if (!navigator.clipboard || !window.ClipboardItem) {
      return Promise.reject(new Error('这个浏览器不支持把图片放进剪贴板，请改用「下载 PNG」'));
    }
    return new Promise(function (res, rej) {
      cv.toBlob(function (b) {
        if (!b) return rej(new Error('图片生成失败'));
        navigator.clipboard.write([new window.ClipboardItem({ 'image/png': b })]).then(function () {
          res();
        }, function () {
          rej(new Error('复制失败，请改用「下载 PNG」'));
        });
      }, 'image/png');
    });
  }

  /* ======================================================================
     3. 按需加载 —— 工具代码只在用户点开对应卡片时才注入执行

     好处：二十个工具的首屏体积与十个时相同；某个子文件的语法错误也拖不垮整页；
     没被打开过的工具一行代码都不会下载和执行。

     子文件 static/js/tools/<id>.js 加载完成后会自己调用 window.LXTools.define()
     注册 setup 函数，这里的 onload 再把它跑起来。版本串沿用主文件 script 标签上
     的 ?v=（CI 会把它换成内容哈希），所以主文件一更新，全部子文件的缓存一起失效。
     ====================================================================== */
  var SETUP = {};      // id -> setup 函数
  var LOADED = {};     // id -> 'loading' | 'done' | 'fail'

  // 子模块自身的版本号：改动某个子文件之后，把这里对应的数字加一。
  // 子文件的 URL 是运行时拼的，光靠主文件的哈希变化盖不住「只改了某个子文件」的情况，
  // 少改这一处，老访客会一直拿着缓存里的旧子文件。新增工具记得在这里加一行。
  var SUB_VER = {
    compress: 1, convert: 1, resize: 1, pdf: 1, watermark: 1,
    stitch: 1, exif: 1, color: 1, qr: 1, audio: 1,
    dates: 1, diff: 1, grid: 1, longcut: 1, mask: 1
  };

  window.LXTools = {
    api: {
      doc: doc, $: $, $$: $$,
      fmtBytes: fmtBytes, fmtNum: fmtNum, hex2: hex2, rgbToHex: rgbToHex, esc: esc,
      baseName: baseName, extOf: extOf, download: download, toast: toast, setStat: setStat,
      loadBitmap: loadBitmap, loadViaImg: loadViaImg, bitmapSize: bitmapSize,
      newCanvas: newCanvas, canvasToBlob: canvasToBlob, blobToBytes: blobToBytes,
      crc32: crc32, zipStore: zipStore, bindDrop: bindDrop, renderList: renderList,
      outNameOf: outNameOf, zipItems: zipItems, thumbOf: thumbOf,
      panelOf: panelOf, field: field, outEl: outEl, btnOf: btnOf, valOf: valOf,
      numOf: numOf, bindOutputs: bindOutputs, runSeq: runSeq, sizeCell: sizeCell,
      fitSize: fitSize, plainErr: plainErr, drawToCanvas: drawToCanvas, bindSeg: bindSeg,
      concatBytes: concatBytes, clearToast: clearToast, copyText: copyText, copyCanvas: copyCanvas,
      scrollPanel: scrollPanel,
      CRC_TABLE: CRC_TABLE, PLAIN_ERR: PLAIN_ERR
    },
    define: function (id, fn) { SETUP[id] = fn; },
    state: LOADED
  };

  var currentTool = '';

  function verQuery() {
    var tag = $('script[src*="tools.js"]');
    var src = tag ? (tag.getAttribute('src') || '') : '';
    var i = src.indexOf('?');
    return i < 0 ? '' : src.slice(i);
  }

  // 子文件地址：自带版本号 + 主文件版本串（主文件一更新，全部子文件缓存一起失效）
  function subUrl(id) {
    var main = verQuery().replace(/^\?v=/, '');
    return 'js/tools/' + id + '.js?v=' + (SUB_VER[id] || 1) + (main ? '.' + main : '');
  }

  function ensureTool(id, after) {
    after = after || function () {};
    if (LOADED[id] === 'done') { after(); return; }
    if (LOADED[id] === 'loading') return;      // 已经在路上，onload 会收尾
    var P = panelOf(id);
    if (!P) return;
    LOADED[id] = 'loading';

    var tag = doc.createElement('script');
    tag.src = subUrl(id);
    tag.async = true;

    tag.onload = function () {
      var fn = SETUP[id];
      if (typeof fn !== 'function') {
        LOADED[id] = 'fail';
        if (window.console && console.error) console.error('[tools] ' + id + ' 加载完成却没有注册工具');
        toast(P, '这个工具没能启动。刷新一下页面再试。', 'err');
        return;
      }
      try {
        fn();
      } catch (e) {
        LOADED[id] = 'fail';
        if (window.console && console.error) console.error('[tools] ' + id + ' 初始化失败：', e);
        toast(P, plainErr(e, '这个工具没能启动。刷新一下页面再试。'), 'err');
        return;
      }
      LOADED[id] = 'done';
      after();
    };

    tag.onerror = function () {
      LOADED[id] = 'fail';
      if (window.console && console.error) console.error('[tools] ' + id + ' 加载失败：js/tools/' + id + '.js');
      toast(P, '这个工具没能加载。检查一下网络，或者刷新页面再试。', 'err');
    };

    (doc.head || doc.documentElement).appendChild(tag);
  }

  function scrollPanel(P) {
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    try { P.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' }); }
    catch (e) { P.scrollIntoView(); }
  }

  function fromHash() {
    var m = /^#tool-([a-z]+)$/.exec(String(location.hash || ''));
    return m && panelOf(m[1]) ? m[1] : '';
  }

  function openPanel(id, doScroll) {
    if (id && !panelOf(id)) id = '';
    currentTool = id || '';

    $$('.tl-panel').forEach(function (p) {
      p.classList.toggle('is-open', !!id && p.id === 'tp-' + id);
      if (!id || p.id !== 'tp-' + id) p.classList.remove('tl-hl');
    });
    $$('[data-tool]').forEach(function (t) {
      var on = t.getAttribute('data-tool') === currentTool;
      t.classList.toggle('is-active', on && !!currentTool);
      t.setAttribute('aria-expanded', on && !!currentTool ? 'true' : 'false');
    });

    var base = location.pathname + location.search;
    try { history.replaceState(null, '', id ? base + '#tool-' + id : base); } catch (e) { /* 无关紧要 */ }

    if (!id) return;
    var P = panelOf(id);
    if (!P) return;
    // 面板本身是 HTML，立刻就能看见：先滚动定位，再等工具脚本到位补一个高亮。
    if (doScroll) scrollPanel(P);
    ensureTool(id, function () {
      var Q = panelOf(id);
      if (!Q) return;
      Q.classList.add('tl-hl');
      setTimeout(function () { Q.classList.remove('tl-hl'); }, 1800);
    });
  }

  function closePanel(P) {
    var id = P && P.id && P.id.indexOf('tp-') === 0 ? P.id.slice(3) : '';
    if (id && id !== currentTool) {
      P.classList.remove('is-open', 'tl-hl');
      return;
    }
    openPanel('');
  }

  function wireTiles() {
    $$('[data-tool]').forEach(function (t) {
      t.setAttribute('aria-expanded', 'false');
      t.addEventListener('click', function () {
        var id = t.getAttribute('data-tool');
        if (!panelOf(id)) return;
        if (currentTool === id) openPanel('');
        else openPanel(id, true);
      });
    });
    // 「收起」按钮统一在文档上代理，面板重绘也不会失效
    doc.addEventListener('click', function (e) {
      var el = e.target;
      var b = el && el.closest ? el.closest('[data-close]') : null;
      if (!b) return;
      closePanel(b.closest ? b.closest('.tl-panel') : null);
    });
  }

  function boot() {
    try {
      wireTiles();
    } catch (e) {
      // 折叠开关没装上就绝不加 tools-js：宁可十个面板全部平铺，也不让内容被藏起来
      if (window.console && console.error) console.error('[tools] 折叠开关绑定失败，已保持全部展开：', e);
      return;
    }
    doc.documentElement.classList.add('tools-js');

    // 这里不再预跑全部工具：点开哪张卡片才加载哪个。
    window.addEventListener('hashchange', function () { openPanel(fromHash(), true); });
    var init = fromHash();
    if (init) openPanel(init, true);
  }

  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
