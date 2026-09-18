/*!
 * tools.js — 龙兄知识库「工具箱」纯前端引擎
 *
 * 设计红线（与站点安全基线一致，改动前先读）：
 *   1. 零外部依赖、零 CDN、零网络请求。所有算法（QR 编码 / PDF 合成 / ZIP 打包 /
 *      WAV 编码 / EXIF 解析）都在本文件里自己实现，全部跑在用户自己的设备上。
 *   2. 文件绝不离开浏览器：不使用 fetch / XMLHttpRequest / WebSocket，不往任何地方传字节。
 *   3. 不用内联事件处理器（onclick= 等），一律 addEventListener —— 页面 CSP 的
 *      script-src 只有 'self' + sha256 白名单，没有 'unsafe-inline'。
 *   4. 折叠状态挂在 <html class="tools-js"> 上：JS 没跑起来时十个面板全部可见，
 *      内容零丢失（与 apple-tabs.js 同一约定）。
 *
 * 文件结构：
 *   0) 二维码编码器（无 DOM 依赖；Node 里 require 本文件可直接单测）
 *   1) 通用底座：字节格式化 / 下载 / ZIP / CRC32 / 图片解码 / 文件投放区
 *   2) 十个工具
 *   3) 启动与面板路由
 */
(function () {
  'use strict';

  /* ======================================================================
     0. 二维码编码器  —— QR Code Model 2，字节模式（byte），纠错 L/M/Q/H
     参照 ISO/IEC 18004。只实现字节模式（UTF-8），足够网址/文本/WiFi 场景。
     ====================================================================== */

  // 每块纠错码字数 [ECL][版本]，下标 0 为占位（非法值）
  var ECC_CODEWORDS_PER_BLOCK = [
    [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
    [-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    [-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30]
  ];
  // 纠错块数 [ECL][版本]
  var NUM_EC_BLOCKS = [
    [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
    [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49],
    [-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68],
    [-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81]
  ];
  var ECC_ORDER = ['L', 'M', 'Q', 'H'];
  // 格式信息里的纠错等级编码：L=01, M=00, Q=11, H=10
  var ECL_FORMAT_BITS = [1, 0, 3, 2];

  function qrUtf8Bytes(str) {
    // 与 TextEncoder 等价的最小实现（老浏览器兜底用）
    if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(str);
    var out = [];
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i);
      if (c < 0x80) out.push(c);
      else if (c < 0x800) out.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F));
      else if (c >= 0xD800 && c <= 0xDBFF && i + 1 < str.length) {
        var c2 = str.charCodeAt(++i);
        var cp = 0x10000 + ((c - 0xD800) << 10) + (c2 - 0xDC00);
        out.push(0xF0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3F), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F));
      } else out.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F));
    }
    return new Uint8Array(out);
  }

  /** 版本 ver 的原始数据模块数（不含功能图形） */
  function qrRawDataModules(ver) {
    var result = (16 * ver + 128) * ver + 64;
    if (ver >= 2) {
      var na = Math.floor(ver / 7) + 2;
      result -= (25 * na - 10) * na - 55;
      if (ver >= 7) result -= 36;
    }
    return result;
  }

  function qrNumDataCodewords(ver, ecl) {
    return Math.floor(qrRawDataModules(ver) / 8)
      - ECC_CODEWORDS_PER_BLOCK[ecl][ver] * NUM_EC_BLOCKS[ecl][ver];
  }

  /** 对齐图形中心坐标表 */
  function qrAlignPositions(ver) {
    if (ver === 1) return [];
    var num = Math.floor(ver / 7) + 2;
    var size = ver * 4 + 17;
    // 注意：这里必须用整除（不是向上取整）。用 Math.ceil 会让 v7 得到 20 而不是标准的 22。
    var step = (ver === 32) ? 26
      : Math.floor((ver * 4 + num * 2 + 1) / (num * 2 - 2)) * 2;
    var result = [];
    for (var i = 0; i < num - 1; i++) result.push(size - 7 - i * step);
    result.push(6);
    return result.reverse();
  }

  // ---- GF(256) 运算（模 0x11D）----
  function gfMul(x, y) {
    var z = 0;
    for (var i = 7; i >= 0; i--) {
      z = (z << 1) ^ ((z >>> 7) * 0x11D);
      z ^= ((y >>> i) & 1) * x;
    }
    return z & 0xFF;
  }

  function rsDivisor(degree) {
    var result = new Array(degree);
    for (var i = 0; i < degree; i++) result[i] = 0;
    result[degree - 1] = 1;
    var root = 1;
    for (var i2 = 0; i2 < degree; i2++) {
      for (var j = 0; j < result.length; j++) {
        result[j] = gfMul(result[j], root);
        if (j + 1 < result.length) result[j] ^= result[j + 1];
      }
      root = gfMul(root, 0x02);
    }
    return result;
  }

  function rsRemainder(data, divisor) {
    var result = new Array(divisor.length);
    for (var i = 0; i < result.length; i++) result[i] = 0;
    for (var k = 0; k < data.length; k++) {
      var factor = data[k] ^ result.shift();
      result.push(0);
      for (var j = 0; j < result.length; j++) result[j] ^= gfMul(divisor[j], factor);
    }
    return result;
  }

  function bitAt(x, i) { return ((x >>> i) & 1) !== 0; }

  /**
   * 生成二维码模块矩阵。
   * @param {string} text  UTF-8 内容
   * @param {string} eclName 'L' | 'M' | 'Q' | 'H'
   * @returns {{size:number, version:number, modules:boolean[][], mask:number}}
   */
  function qrEncode(text, eclName) {
    var ecl = ECC_ORDER.indexOf(eclName || 'M');
    if (ecl < 0) ecl = 1;

    var bytes = qrUtf8Bytes(text);
    var version = 0;
    for (var v = 1; v <= 40; v++) {
      var ccBits = v <= 9 ? 8 : 16;
      if (4 + ccBits + bytes.length * 8 <= qrNumDataCodewords(v, ecl) * 8) { version = v; break; }
    }
    if (!version) throw new Error('内容太长（超过 QR 版本 40 的容量），请缩短后重试');

    var capBits = qrNumDataCodewords(version, ecl) * 8;
    var bits = [];
    function push(val, len) { for (var i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1); }

    push(4, 4);                                            // 字节模式
    push(bytes.length, version <= 9 ? 8 : 16);             // 字符计数
    for (var i = 0; i < bytes.length; i++) push(bytes[i], 8);
    push(0, Math.min(4, capBits - bits.length));           // 终止符
    push(0, (8 - bits.length % 8) % 8);                    // 补齐到字节

    for (var pad = 0xEC; bits.length < capBits; pad ^= 0xEC ^ 0x11) push(pad, 8);

    var dataCodewords = [];
    for (var b = 0; b < bits.length; b += 8) {
      var byteVal = 0;
      for (var k = 0; k < 8; k++) byteVal = (byteVal << 1) | bits[b + k];
      dataCodewords.push(byteVal);
    }

    // ---- 分块 + 纠错 ----
    var numBlocks = NUM_EC_BLOCKS[ecl][version];
    var blockEccLen = ECC_CODEWORDS_PER_BLOCK[ecl][version];
    var rawCodewords = Math.floor(qrRawDataModules(version) / 8);
    var numShort = numBlocks - rawCodewords % numBlocks;
    var shortLen = Math.floor(rawCodewords / numBlocks);

    var divisor = rsDivisor(blockEccLen);
    var blocks = [];
    for (var bi = 0, off = 0; bi < numBlocks; bi++) {
      var datLen = shortLen - blockEccLen + (bi < numShort ? 0 : 1);
      var dat = dataCodewords.slice(off, off + datLen);
      off += datLen;
      var eccv = rsRemainder(dat, divisor);
      if (bi < numShort) dat.push(0);                      // 交织占位
      blocks.push(dat.concat(eccv));
    }
    var all = [];
    for (var ci = 0; ci < blocks[0].length; ci++) {
      for (var bj = 0; bj < blocks.length; bj++) {
        if (ci !== shortLen - blockEccLen || bj >= numShort) all.push(blocks[bj][ci]);
      }
    }

    // ---- 矩阵 ----
    var size = version * 4 + 17;
    var mod = [], fn = [];
    for (var y = 0; y < size; y++) {
      mod.push(new Array(size).fill(false));
      fn.push(new Array(size).fill(false));
    }
    function setFn(x, y, dark) {
      if (x < 0 || y < 0 || x >= size || y >= size) return;
      mod[y][x] = dark; fn[y][x] = true;
    }
    function drawFinder(cx, cy) {
      for (var dy = -4; dy <= 4; dy++) {
        for (var dx = -4; dx <= 4; dx++) {
          var d = Math.max(Math.abs(dx), Math.abs(dy));
          setFn(cx + dx, cy + dy, d !== 2 && d !== 4);
        }
      }
    }
    function drawAlign(cx, cy) {
      for (var dy = -2; dy <= 2; dy++)
        for (var dx = -2; dx <= 2; dx++)
          setFn(cx + dx, cy + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
    }

    for (var t = 0; t < size; t++) { setFn(6, t, t % 2 === 0); setFn(t, 6, t % 2 === 0); }
    drawFinder(3, 3); drawFinder(size - 4, 3); drawFinder(3, size - 4);

    var ap = qrAlignPositions(version), na = ap.length;
    for (var ai = 0; ai < na; ai++) {
      for (var aj = 0; aj < na; aj++) {
        if ((ai === 0 && aj === 0) || (ai === 0 && aj === na - 1) || (ai === na - 1 && aj === 0)) continue;
        drawAlign(ap[ai], ap[aj]);
      }
    }

    function drawFormat(mask) {
      var data = (ECL_FORMAT_BITS[ecl] << 3) | mask;
      var rem = data;
      for (var i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
      var bts = ((data << 10) | rem) ^ 0x5412;
      for (var a = 0; a <= 5; a++) setFn(8, a, bitAt(bts, a));
      setFn(8, 7, bitAt(bts, 6));
      setFn(8, 8, bitAt(bts, 7));
      setFn(7, 8, bitAt(bts, 8));
      for (var c = 9; c < 15; c++) setFn(14 - c, 8, bitAt(bts, c));
      for (var d = 0; d < 8; d++) setFn(size - 1 - d, 8, bitAt(bts, d));
      for (var e = 8; e < 15; e++) setFn(8, size - 15 + e, bitAt(bts, e));
      setFn(8, size - 8, true);
    }
    drawFormat(0);

    if (version >= 7) {
      var vrem = version;
      for (var vi = 0; vi < 12; vi++) vrem = (vrem << 1) ^ ((vrem >>> 11) * 0x1F25);
      var vbits = (version << 12) | vrem;
      for (var vk = 0; vk < 18; vk++) {
        var bit = bitAt(vbits, vk);
        var pa = size - 11 + vk % 3, pb = Math.floor(vk / 3);
        setFn(pa, pb, bit); setFn(pb, pa, bit);
      }
    }

    // ---- 数据放置（之字形）----
    var idx = 0, total = all.length * 8;
    for (var right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (var vert = 0; vert < size; vert++) {
        for (var jj = 0; jj < 2; jj++) {
          var xx = right - jj;
          var up = ((right + 1) & 2) === 0;
          var yy = up ? size - 1 - vert : vert;
          if (!fn[yy][xx] && idx < total) {
            mod[yy][xx] = bitAt(all[idx >>> 3], 7 - (idx & 7));
            idx++;
          }
        }
      }
    }

    // ---- 掩码：8 种全算，取罚分最低 ----
    function applyMask(m) {
      for (var y = 0; y < size; y++) {
        for (var x = 0; x < size; x++) {
          if (fn[y][x]) continue;
          var inv;
          switch (m) {
            case 0: inv = (x + y) % 2 === 0; break;
            case 1: inv = y % 2 === 0; break;
            case 2: inv = x % 3 === 0; break;
            case 3: inv = (x + y) % 3 === 0; break;
            case 4: inv = (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0; break;
            case 5: inv = (x * y) % 2 + (x * y) % 3 === 0; break;
            case 6: inv = ((x * y) % 2 + (x * y) % 3) % 2 === 0; break;
            default: inv = ((x + y) % 2 + (x * y) % 3) % 2 === 0; break;
          }
          if (inv) mod[y][x] = !mod[y][x];
        }
      }
    }
    function penalty() {
      var result = 0;
      // 规则1：行/列同色连续
      for (var y = 0; y < size; y++) {
        var runColor = false, runX = 0;
        for (var x = 0; x < size; x++) {
          if (x === 0 || mod[y][x] !== runColor) { runColor = mod[y][x]; runX = 1; }
          else { runX++; if (runX === 5) result += 3; else if (runX > 5) result++; }
        }
      }
      for (var x2 = 0; x2 < size; x2++) {
        var rc = false, runY = 0;
        for (var y2 = 0; y2 < size; y2++) {
          if (y2 === 0 || mod[y2][x2] !== rc) { rc = mod[y2][x2]; runY = 1; }
          else { runY++; if (runY === 5) result += 3; else if (runY > 5) result++; }
        }
      }
      // 规则2：2×2 同色块
      for (var y3 = 0; y3 < size - 1; y3++) {
        for (var x3 = 0; x3 < size - 1; x3++) {
          var c = mod[y3][x3];
          if (c === mod[y3][x3 + 1] && c === mod[y3 + 1][x3] && c === mod[y3 + 1][x3 + 1]) result += 3;
        }
      }
      // 规则3：1:1:3:1:1 型图案
      for (var y4 = 0; y4 < size; y4++) {
        for (var x4 = 0; x4 < size; x4++) {
          var run = '';
          for (var k = 0; k < 11; k++) {
            var px = x4 + k, py = y4;
            run += (px < size) ? (mod[py][px] ? '1' : '0') : '';
          }
          if (run.length === 11 && (run === '10111010000' || run === '00001011101')) result += 40;
        }
      }
      for (var y5 = 0; y5 < size; y5++) {
        for (var x5 = 0; x5 < size; x5++) {
          var col = '';
          for (var k2 = 0; k2 < 11; k2++) {
            var px2 = x5, py2 = y5 + k2;
            col += (py2 < size) ? (mod[py2][px2] ? '1' : '0') : '';
          }
          if (col.length === 11 && (col === '10111010000' || col === '00001011101')) result += 40;
        }
      }
      // 规则4：黑白比例偏离 50%（整数运算，等价于标准 ceil(dev/total) - 1）
      var dark = 0;
      for (var yy = 0; yy < size; yy++) {
        for (var xx2 = 0; xx2 < size; xx2++) if (mod[yy][xx2]) dark++;
      }
      var totalMod = size * size;
      var k3 = Math.ceil(Math.abs(dark * 20 - totalMod * 10) / totalMod) - 1;
      if (k3 > 0) result += k3 * 10;
      return result;
    }

    var bestMask = 0, bestScore = Infinity;
    var snapshot = null;
    for (var mask = 0; mask < 8; mask++) {
      applyMask(mask); drawFormat(mask);
      var sc = penalty();
      if (sc < bestScore) { bestScore = sc; bestMask = mask; snapshot = mod.map(function (r) { return r.slice(); }); }
      applyMask(mask); // 再异或一次 = 还原（同一掩码两次等于原地复原）
    }
    mod = snapshot;
    // 快照里已含正确格式信息（最后一轮 drawFormat(mask) 可能覆盖成别的 mask，故重画一次）
    drawFormat(bestMask);

    return { size: size, version: version, modules: mod, mask: bestMask };
  }

  /* ---- Node 单测出口：不碰 DOM，导出后直接 return ---- */
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      qrEncode: qrEncode,
      qrRawDataModules: qrRawDataModules,
      qrNumDataCodewords: qrNumDataCodewords,
      qrAlignPositions: qrAlignPositions,
      ECC_ORDER: ECC_ORDER
    };
    return;
  }

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
     1b. 最小 PDF 合成器（自己的实现，不加载任何 PDF 库）
     JPEG 可以直接以 DCTDecode 过滤器嵌进 PDF，不需要重新编码成像素数据，
     所以体积和画质都保持原样。
     ====================================================================== */
  var PT_PER_MM = 72 / 25.4;

  /**
   * @param {Array<{bytes:Uint8Array, w:number, h:number}>} items 已编码好的 JPEG
   * @param {{mode:'fit'|'a4p'|'a4l', marginMM:number}} opt
   */
  function buildPdf(items, opt) {
    var enc = new TextEncoder();
    var chunks = [];
    var total = 0;
    var offsets = [];
    var nObj = 3 + items.length * 3;

    function put(bytes) { chunks.push(bytes); total += bytes.length; }
    function puts(s) { put(enc.encode(s)); }
    function obj(num, body) { offsets[num] = total; puts(num + ' 0 obj\n' + body + '\nendobj\n'); }
    function objBytes(num, dict, bytes) {
      offsets[num] = total;
      puts(num + ' 0 obj\n<< ' + dict + ' /Length ' + bytes.length + ' >>\nstream\n');
      put(bytes);
      puts('\nendstream\nendobj\n');
    }
    function num2(v) { return (Math.round(v * 100) / 100).toString(); }

    put(new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2D, 0x31, 0x2E, 0x34, 0x0A]));  // %PDF-1.4
    put(new Uint8Array([0x25, 0xE2, 0xE3, 0xCF, 0xD3, 0x0A]));                    // 二进制标记

    obj(1, '<< /Type /Catalog /Pages 2 0 R >>');

    var kids = [];
    for (var i = 0; i < items.length; i++) kids.push((3 + i * 3) + ' 0 R');
    obj(2, '<< /Type /Pages /Kids [' + kids.join(' ') + '] /Count ' + items.length + ' >>');

    for (var k = 0; k < items.length; k++) {
      var it = items[k];
      var pageObj = 3 + k * 3, contentObj = pageObj + 1, imageObj = pageObj + 2;
      var pw, ph, dw, dh, dx, dy;
      var m = Math.max(0, opt.marginMM || 0) * PT_PER_MM;

      if (opt.mode === 'fit') {
        pw = it.w; ph = it.h;
        dw = pw - m * 2; dh = ph - m * 2;
        dx = m; dy = m;
      } else {
        var a4 = opt.mode === 'a4l' ? [841.89, 595.28] : [595.28, 841.89];
        pw = a4[0]; ph = a4[1];
        var availW = pw - m * 2, availH = ph - m * 2;
        var sc = Math.min(availW / it.w, availH / it.h);   // 等比缩放，不裁切不变形
        dw = it.w * sc; dh = it.h * sc;
        dx = (pw - dw) / 2; dy = (ph - dh) / 2;
      }

      var content = 'q\n' + num2(dw) + ' 0 0 ' + num2(dh) + ' ' + num2(dx) + ' ' + num2(dy) +
        ' cm\n/Im0 Do\nQ\n';
      objBytes(contentObj, '', enc.encode(content));
      obj(pageObj,
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ' + num2(pw) + ' ' + num2(ph) + '] ' +
        '/Resources << /XObject << /Im0 ' + imageObj + ' 0 R >> /ProcSet [/PDF /ImageC] >> ' +
        '/Contents ' + contentObj + ' 0 R >>');
      objBytes(imageObj,
        '/Type /XObject /Subtype /Image /Width ' + it.w + ' /Height ' + it.h +
        ' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode',
        it.bytes);
    }

    var xrefPos = total;
    var xref = 'xref\n0 ' + (nObj + 1) + '\n0000000000 65535 f \n';
    for (var n = 1; n <= nObj; n++) {
      xref += ('0000000000' + (offsets[n] || 0)).slice(-10) + ' 00000 n \n';
    }
    puts(xref);
    puts('trailer\n<< /Size ' + (nObj + 1) + ' /Root 1 0 R >>\nstartxref\n' + xrefPos + '\n%%EOF\n');

    var out = new Uint8Array(total), p = 0;
    for (var c = 0; c < chunks.length; c++) { out.set(chunks[c], p); p += chunks[c].length; }
    return out;
  }

  /* ======================================================================
     1c. WAV 编码器（PCM 16bit；重采样与下混交给 OfflineAudioContext）
     ====================================================================== */
  function encodeWav(channels, sampleRate) {
    var nch = channels.length;
    var frames = channels[0].length;
    var dataBytes = frames * nch * 2;
    var buf = new ArrayBuffer(44 + dataBytes);
    var v = new DataView(buf);
    var pos = 0;

    function str(s) { for (var i = 0; i < s.length; i++) v.setUint8(pos++, s.charCodeAt(i)); }
    function u32(n) { v.setUint32(pos, n, true); pos += 4; }
    function u16(n) { v.setUint16(pos, n, true); pos += 2; }

    str('RIFF'); u32(36 + dataBytes); str('WAVE');
    str('fmt '); u32(16); u16(1); u16(nch);
    u32(sampleRate); u32(sampleRate * nch * 2); u16(nch * 2); u16(16);
    str('data'); u32(dataBytes);

    for (var i = 0; i < frames; i++) {
      for (var c = 0; c < nch; c++) {
        var s = channels[c][i];
        if (s > 1) s = 1; else if (s < -1) s = -1;
        v.setInt16(pos, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        pos += 2;
      }
    }
    return new Uint8Array(buf);
  }

  function peakOf(channels) {
    var peak = 0;
    for (var c = 0; c < channels.length; c++) {
      var d = channels[c];
      for (var i = 0; i < d.length; i++) {
        var a = d[i] < 0 ? -d[i] : d[i];
        if (a > peak) peak = a;
      }
    }
    return peak;
  }

  /** 把 AudioBuffer 转成 16bit PCM 通道数组（含可选重采样 / 单声道 / 归一化） */
  function audioBufferToPcm(buf, opt) {
    var rate = opt.rate > 0 ? opt.rate : buf.sampleRate;
    var nch = opt.mono ? 1 : Math.min(2, buf.numberOfChannels);

    function pack(rendered) {
      var chans = [];
      for (var c = 0; c < rendered.numberOfChannels; c++) chans.push(rendered.getChannelData(c));
      if (opt.norm) {
        var peak = peakOf(chans);
        if (peak > 0.0001) {
          var g = 0.891 / peak;   // -1 dBFS
          for (var c2 = 0; c2 < chans.length; c2++) {
            for (var i = 0; i < chans[c2].length; i++) chans[c2][i] *= g;
          }
        }
      }
      return chans;
    }

    var needResample = (rate !== buf.sampleRate) || (opt.mono && buf.numberOfChannels > 1);
    var OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    if (!needResample || !OAC) {
      var chans = [];
      for (var c = 0; c < nch; c++) chans.push(buf.getChannelData(c));
      if (opt.norm) {
        var peak = peakOf(chans);
        if (peak > 0.0001) {
          var g = 0.891 / peak;
          for (var c3 = 0; c3 < chans.length; c3++) {
            for (var j = 0; j < chans[c3].length; j++) chans[c3][j] *= g;
          }
        }
      }
      return Promise.resolve({ channels: chans, rate: buf.sampleRate });
    }

    var frames = Math.max(1, Math.ceil(buf.duration * rate));
    var ctx = new OAC(nch, frames, rate);
    var src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(ctx.destination);
    src.start();
    return ctx.startRendering().then(function (rendered) {
      return { channels: pack(rendered), rate: rate };
    });
  }

  /* ======================================================================
     1d. EXIF 解析（只读 JPEG 的 APP1 段；不联网、不写回）
     ====================================================================== */
  var TYPE_SIZE = [0, 1, 1, 2, 4, 8, 1, 1, 2, 4, 8, 4, 8];

  var TAG_NAMES = {
    0x010E: '图像说明', 0x010F: '相机品牌', 0x0110: '相机型号', 0x0112: '方向',
    0x011A: '水平分辨率', 0x011B: '垂直分辨率', 0x0128: '分辨率单位',
    0x0131: '生成软件', 0x0132: '修改时间', 0x013B: '作者',
    0x829A: '曝光时间', 0x829D: '光圈值', 0x8822: '曝光程序', 0x8827: 'ISO', 
    0x9003: '拍摄时间', 0x9004: '数字化时间', 0x9201: '快门速度',
    0x9202: '光圈', 0x9204: '曝光补偿', 0x9207: '测光模式', 0x9209: '闪光灯',
    0x920A: '焦距', 0x9290: '副秒（原）', 0xA002: '像素宽', 0xA003: '像素高',
    0xA405: '等效焦距', 0xA430: '相机所有者', 0xA431: '机身序列号',
    0xA432: '镜头规格', 0xA433: '镜头品牌', 0xA434: '镜头型号',
    0x9C9B: '标题', 0x9C9C: '备注', 0x9C9D: '评级', 0x9C9E: '关键词'
  };

  var GPS_TAG_NAMES = {
    0x0000: 'GPS 版本', 0x0001: '纬度方向', 0x0002: '纬度', 0x0003: '经度方向',
    0x0004: '经度', 0x0005: '海拔方向', 0x0006: '海拔', 0x0007: 'GPS 时间',
    0x0008: '定位卫星', 0x0009: '定位状态', 0x001D: 'GPS 日期'
  };

  var EXPOSURE_PROGRAM = { 0: '未定义', 1: '手动', 2: '程序自动', 3: '光圈优先', 4: '快门优先', 5: '创意', 6: '运动', 7: '肖像', 8: '风景' };
  var METERING = { 0: '未知', 1: '平均', 2: '中央重点', 3: '点测光', 4: '多点', 5: '评价', 6: '局部' };
  var ORIENTATION = { 1: '正常', 2: '水平镜像', 3: '旋转 180°', 4: '垂直镜像', 5: '镜像后转 90°CW', 6: '顺时针 90°', 7: '镜像后转 90°CCW', 8: '逆时针 90°' };

  function exifSegments(bytes) {
    if (bytes.length < 4 || bytes[0] !== 0xFF || bytes[1] !== 0xD8) return null;
    var off = 2, segs = [];
    while (off + 4 <= bytes.length) {
      if (bytes[off] !== 0xFF) break;
      var marker = bytes[off + 1];
      if (marker === 0xD8 || marker === 0x01 || (marker >= 0xD0 && marker <= 0xD7)) { off += 2; continue; }
      if (marker === 0xDA || marker === 0xD9) break;
      var segLen = (bytes[off + 2] << 8) | bytes[off + 3];
      if (segLen < 2) break;
      segs.push({ marker: marker, start: off, len: segLen + 2 });
      off += 2 + segLen;
    }
    return segs;
  }

  function parseExif(bytes) {
    var segs = exifSegments(bytes);
    if (!segs) return null;
    for (var i = 0; i < segs.length; i++) {
      var s = segs[i];
      if (s.marker !== 0xE1) continue;
      var p = s.start + 4;
      if (bytes[p] === 0x45 && bytes[p + 1] === 0x78 && bytes[p + 2] === 0x69 && bytes[p + 3] === 0x66) {
        return parseTiff(bytes, p + 6);   // "Exif\x00\x00" 之后紧跟 TIFF 头
      }
    }
    return null;
  }

  function parseTiff(bytes, base) {
    var le;
    if (bytes[base] === 0x49 && bytes[base + 1] === 0x49) le = true;
    else if (bytes[base] === 0x4D && bytes[base + 1] === 0x4D) le = false;
    else return null;

    function u16(p) { return le ? (bytes[p] | (bytes[p + 1] << 8)) : ((bytes[p] << 8) | bytes[p + 1]); }
    function u32(p) {
      return le
        ? ((bytes[p] | (bytes[p + 1] << 8) | (bytes[p + 2] << 16) | (bytes[p + 3] << 24)) >>> 0)
        : (((bytes[p] << 24) | (bytes[p + 1] << 16) | (bytes[p + 2] << 8) | bytes[p + 3]) >>> 0);
    }
    function s32(p) { var v = u32(p); return v > 0x7FFFFFFF ? v - 0x100000000 : v; }
    if (u16(base + 2) !== 0x2A) return null;

    var rows = [];
    function readValue(entryPos) {
      var type = u16(entryPos + 2), count = u32(entryPos + 4);
      var size = TYPE_SIZE[type] || 1;
      var dataLen = size * count;
      var vp = dataLen <= 4 ? entryPos + 8 : base + u32(entryPos + 8);
      if (vp < 0 || vp + dataLen > bytes.length) return null;
      var arr = [], i;
      if (type === 2) {
        var str = '';
        for (i = 0; i < count; i++) {
          var ch = bytes[vp + i];
          if (ch === 0) break;
          str += String.fromCharCode(ch);
        }
        return str.replace(/\0+$/, '').trim();
      }
      for (i = 0; i < count; i++) {
        var p = vp + i * size;
        if (type === 1 || type === 7) arr.push(bytes[p]);
        else if (type === 3) arr.push(u16(p));
        else if (type === 8) { var a = u16(p); arr.push(a > 0x7FFF ? a - 0x10000 : a); }
        else if (type === 4) arr.push(u32(p));
        else if (type === 9) arr.push(s32(p));
        else if (type === 5) arr.push({ n: u32(p), d: u32(p + 4) });
        else if (type === 10) arr.push({ n: s32(p), d: s32(p + 4) });
      }
      return arr;
    }

    function toScalar(v) { return Array.isArray(v) ? v[0] : v; }

    /** 读一个 IFD；子 IFD 的指针写进 sub，返回下一个 IFD 的偏移 */
    function readIfd(ifdOff, names, prefix, sub) {
      if (ifdOff <= 0 || ifdOff + 2 > bytes.length) return 0;
      var count = u16(ifdOff);
      if (count > 512) return 0;
      for (var i = 0; i < count; i++) {
        var ep = ifdOff + 2 + i * 12;
        if (ep + 12 > bytes.length) break;
        var tag = u16(ep);
        var val = readValue(ep);
        if (val === null || val === '' || (Array.isArray(val) && !val.length)) continue;
        if (tag === 0x8769) { sub.exif = toScalar(val); continue; }   // Exif 子 IFD
        if (tag === 0x8825) { sub.gps = toScalar(val); continue; }    // GPS 子 IFD
        rows.push({ tag: tag, name: names[tag] || (prefix + '0x' + tag.toString(16).toUpperCase()), value: val });
      }
      var nx = ifdOff + 2 + count * 12;
      if (nx + 4 <= bytes.length) return u32(nx);
      return 0;
    }

    var sub = {};
    readIfd(base + u32(base + 4), TAG_NAMES, '标签 ', sub);   // IFD0
    if (sub.exif) readIfd(base + sub.exif, TAG_NAMES, '标签 ', sub);
    if (sub.gps) readIfd(base + sub.gps, GPS_TAG_NAMES, 'GPS ', sub);

    return { rows: rows };
  }

  /** EXIF 里取一个数值：理数值可能是 {n,d}，也可能被包在长度为 1 的数组里
      （RATIONAL 且计数为 1 时读出来就是 [{n,d}]），两种形状都要吃得下 */
  function toNum(x) {
    if (Array.isArray(x)) return toNum(x[0]);
    if (x && typeof x === 'object') return x.d ? x.n / x.d : 0;
    return x;
  }

  function dmsToString(v) {
    if (!Array.isArray(v) || v.length < 3) {
      // 形状不标准（比如只给了一个值）也别吐 [object Object]，能读成数就当成度数
      var only = toNum(v);
      return isFinite(only) ? only + '°' : String(v);
    }
    var d = toNum(v[0]), m = toNum(v[1]), s = toNum(v[2]);
    return d + '° ' + m + "' " + s.toFixed(2) + '"';
  }

  function scalar(v) { return Array.isArray(v) ? v[0] : v; }

  /** 把原始值格式化成人类可读字符串 */
  function exifPretty(name, val) {
    if (val === undefined || val === null) return '';
    if (name === '曝光时间') {
      var t = toNum(val);
      if (t && t < 1) return '1/' + Math.round(1 / t) + ' 秒';
      return t + ' 秒';
    }
    if (name === '光圈值' || name === '光圈') {
      var f = toNum(val);
      if (name === '光圈') f = Math.pow(2, f / 2);
      return 'ƒ/' + (Math.round(f * 10) / 10);
    }
    if (name === '焦距' || name === '等效焦距') {
      var fl = Array.isArray(val) ? val.map(function (x) { return (typeof x === 'object') ? x.n / x.d : x; }) : [val];
      return fl.map(function (x) { return Math.round(x * 10) / 10; }).join(', ') + ' mm';
    }
    if (name === '曝光补偿') {
      var e = toNum(val);
      return (e > 0 ? '+' : '') + (Math.round(e * 100) / 100) + ' EV';
    }
    if (name === '纬度' || name === '经度') return dmsToString(val);
    if (name === '海拔') {
      var alt = toNum(val);
      return (Math.round(alt * 10) / 10) + ' m';
    }
    if (name === 'GPS 时间') {
      var g = Array.isArray(val) ? val.map(function (x) { return (typeof x === 'object') ? x.n / x.d : x; }) : [val];
      return g.map(function (x) { return String(Math.round(x)).padStart(2, '0'); }).join(':') + ' UTC';
    }
    if (name === '方向') return ORIENTATION[scalar(val)] || val;
    if (name === '曝光程序') return EXPOSURE_PROGRAM[scalar(val)] || val;
    if (name === '测光模式') return METERING[scalar(val)] || val;
    if (name === '闪光灯') { var fv = scalar(val); return (fv & 1) ? '闪光灯已触发' : '未使用闪光灯'; }
    if (name === '水平分辨率' || name === '垂直分辨率') {
      var r = toNum(val);
      return Math.round(r * 100) / 100;
    }
    if (Array.isArray(val)) {
      return val.map(function (x) {
        if (typeof x === 'object' && x.n !== undefined) return (x.d ? Math.round(x.n / x.d * 1000) / 1000 : x.n);
        return x;
      }).join(', ');
    }
    return String(val);
  }

  /** 去掉所有 APP 段与 COM 段，保留画面数据（即"清除 EXIF"） */
  function stripMetadata(bytes) {
    var out = [bytes.slice(0, 2)];
    var off = 2;
    // 从 SOI 之后逐段扫描，只保留非 APPn（0xE0-0xEF）且非 COM（0xFE）的段
    while (off + 4 <= bytes.length) {
      if (bytes[off] !== 0xFF) break;
      var marker = bytes[off + 1];
      if (marker === 0xDA) { out.push(bytes.slice(off)); return concatBytes(out); }
      if (marker === 0xD9) { out.push(bytes.slice(off)); break; }
      var segLen = (bytes[off + 2] << 8) | bytes[off + 3];
      var segEnd = off + 2 + segLen;
      var isMeta = (marker >= 0xE0 && marker <= 0xEF) || marker === 0xFE;
      if (!isMeta) out.push(bytes.slice(off, segEnd));
      off = segEnd;
    }
    return concatBytes(out);
  }

  function concatBytes(arrs) {
    var len = 0, i;
    for (i = 0; i < arrs.length; i++) len += arrs[i].length;
    var out = new Uint8Array(len), p = 0;
    for (i = 0; i < arrs.length; i++) { out.set(arrs[i], p); p += arrs[i].length; }
    return out;
  }

  /* ======================================================================
     1e. 二维码矩阵 → Canvas / SVG
     ====================================================================== */
  function qrToCanvas(qr, opts) {
    var quiet = 4, scale = Math.max(1, Math.floor(opts.size / (qr.size + quiet * 2)));
    var dim = (qr.size + quiet * 2) * scale;
    var c = newCanvas(dim, dim);
    var ctx = c.getContext('2d');
    ctx.fillStyle = opts.bg;
    if (!opts.transparent) ctx.fillRect(0, 0, dim, dim);
    ctx.fillStyle = opts.fg;
    for (var y = 0; y < qr.size; y++) {
      for (var x = 0; x < qr.size; x++) {
        if (qr.modules[y][x]) {
          ctx.fillRect((x + quiet) * scale, (y + quiet) * scale, scale, scale);
        }
      }
    }
    return c;
  }

  function qrToSvg(qr, opts) {
    var quiet = 4, dim = qr.size + quiet * 2;
    var path = [];
    for (var y = 0; y < qr.size; y++) {
      for (var x = 0; x < qr.size; x++) {
        if (qr.modules[y][x]) path.push('M' + (x + quiet) + ' ' + (y + quiet) + 'h1v1h-1z');
      }
    }
    return '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + dim + ' ' + dim + '" ' +
      'width="' + opts.size + '" height="' + opts.size + '" shape-rendering="crispEdges">' +
      (opts.transparent ? '' : '<rect width="' + dim + '" height="' + dim + '" fill="' + opts.bg + '"/>') +
      '<path d="' + path.join('') + '" fill="' + opts.fg + '"/></svg>\n';
  }

  /* ======================================================================
     1f. 主色提取（简单版中位切分，够做配色参考）
     ====================================================================== */
  function extractPalette(bmp, count) {
    var maxSide = 160;
    var s = bitmapSize(bmp);
    var sc = Math.min(1, maxSide / Math.max(s.w, s.h));
    var c = newCanvas(s.w * sc, s.h * sc);
    var ctx = c.getContext('2d');
    ctx.drawImage(bmp, 0, 0, c.width, c.height);
    var data = ctx.getImageData(0, 0, c.width, c.height).data;

    var px = [];
    for (var i = 0; i < data.length; i += 4) {
      if (data[i + 3] < 128) continue;                       // 忽略近透明像素
      px.push([data[i], data[i + 1], data[i + 2]]);
    }
    if (!px.length) return [];

    function avg(list) {
      var r = 0, g = 0, b = 0;
      for (var i = 0; i < list.length; i++) { r += list[i][0]; g += list[i][1]; b += list[i][2]; }
      var n = list.length;
      return [Math.round(r / n), Math.round(g / n), Math.round(b / n)];
    }
    function rank(list) {
      var min = [255, 255, 255], max = [0, 0, 0];
      list.forEach(function (p) {
        for (var k = 0; k < 3; k++) {
          if (p[k] < min[k]) min[k] = p[k];
          if (p[k] > max[k]) max[k] = p[k];
        }
      });
      var ranges = [max[0] - min[0], max[1] - min[1], max[2] - min[2]];
      var ch = ranges.indexOf(Math.max(ranges[0], ranges[1], ranges[2]));
      return { ch: ch, range: ranges[ch] };
    }

    var boxes = [px];
    while (boxes.length < count) {
      var bi = -1, best = 0;
      for (var k = 0; k < boxes.length; k++) {
        if (boxes[k].length < 2) continue;
        var r = rank(boxes[k]);
        if (r.range > best) { best = r.range; bi = k; }
      }
      if (bi < 0 || best < 8) break;
      var box = boxes[bi];
      var ch = rank(box).ch;
      box.sort(function (a, b) { return a[ch] - b[ch]; });
      var mid = Math.floor(box.length / 2);
      boxes.splice(bi, 1, box.slice(0, mid), box.slice(mid));
    }

    return boxes.filter(function (b) { return b.length; })
      .map(function (b) {
        var c2 = avg(b);
        return { r: c2[0], g: c2[1], b: c2[2], hex: rgbToHex(c2[0], c2[1], c2[2]), weight: b.length };
      })
      .sort(function (a, b) { return b.weight - a.weight; })
      .slice(0, count);
  }

  /* ======================================================================
     2. 十个工具
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

  /* ---------------- 01 图片压缩 ---------------- */
  function setupCompress() {
    var P = panelOf('compress');
    if (!P) return;
    var items = [];
    bindOutputs(P);
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); scrollPanel(P); } });

    function refresh() {
      renderList(P, items, {
        onChange: refresh,
        meta: function (it) {
          var s = it.meta || '';
          if (it.out) {
            s += ' · ' + fmtBytes(it.file.size) + ' → <span class="up">' + fmtBytes(it.out.size) +
              '</span>（-' + Math.round((1 - it.out.size / it.file.size) * 100) + '%）';
          } else s += ' · ' + fmtBytes(it.file.size);
          return s;
        }
      });
      btnOf(P, 'zip').disabled = !items.some(function (it) { return it.out; });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选几张图片', 'err');
      var q = numOf(P, 'q', 80) / 100;
      var limit = parseInt(valOf(P, 'max'), 10) || 0;
      var fmt = valOf(P, 'fmt');
      var before = 0, after = 0, errs = 0;
      btnOf(P, 'run').disabled = true;
      runSeq(items, function (it) {
        it.out = null;
        return loadBitmap(it.file).then(function (bmp) {
          var s = bitmapSize(bmp);
          var t = fitSize(s.w, s.h, limit);
          var type = fmt === 'auto' ? (it.file.type || 'image/jpeg') : fmt;
          if (type === 'image/png' && fmt === 'auto') type = 'image/png';
          var bg = type === 'image/jpeg' ? '#ffffff' : null;
          var cv = drawToCanvas(bmp, t.w, t.h, bg);
          if (bmp.close) bmp.close();
          return canvasToBlob(cv, type, type === 'image/png' ? undefined : q).then(function (blob) {
            it.out = blob;
            it.thumb = it.thumb || thumbOf(cv);
            var ext = type === 'image/webp' ? 'webp' : (type === 'image/png' ? 'png' : 'jpg');
            it.outName = baseName(it.file.name) + '-min.' + ext;
            it.meta = t.w + '×' + t.h;
            before += it.file.size; after += blob.size;
          });
        }).catch(function (e) {
          errs++;
          it.meta = '<span class="tl-warn">' + esc(plainErr(e, '处理失败')) + '</span>';
        });
      }).then(function () {
        btnOf(P, 'run').disabled = false;
        refresh();
        setStat(P, sizeCell(before, after),
          errs ? '<b>' + errs + '</b> 个文件处理失败（可能是浏览器不支持该格式的解码）。' :
            '体积为「所有原图之和 → 所有结果之和」。质量越接近 95 越接近原图，80 左右通常已看不出差别。');
        toast(P, errs ? ('完成，' + errs + ' 个失败') : '压缩完成', errs ? 'err' : 'ok');
      });
    });

    btnOf(P, 'zip').addEventListener('click', function () {
      zipItems(items, 'compressed.zip').catch(function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
    });
    btnOf(P, 'clear').addEventListener('click', function () { box.clear(); items.length = 0; refresh(); setStat(P, null); });
    refresh();
  }

  /* ---------------- 02 格式转换 ---------------- */
  function setupConvert() {
    var P = panelOf('convert');
    if (!P) return;
    var items = [];
    bindOutputs(P);
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); } });

    function refresh() {
      renderList(P, items, {
        onChange: refresh,
        meta: function (it) {
          var s = it.meta || extOf(it.file.name).toUpperCase();
          if (it.failed) return s;
          if (it.out) {
            s += ' · ' + fmtBytes(it.file.size) + ' → <span class="up">' + fmtBytes(it.out.size) + '</span>';
            var d = it.file.size ? Math.round((it.out.size / it.file.size - 1) * 100) : 0;
            // 变小是常态，变大也如实说：PNG 转 WebP 遇到大片纯色反而可能更大
            s += '（' + (d >= 0 ? '+' : '') + d + '%）';
          } else s += ' · ' + fmtBytes(it.file.size);
          return s;
        }
      });
      btnOf(P, 'zip').disabled = !items.some(function (it) { return it.out; });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选几张图片', 'err');
      var type = valOf(P, 'fmt');
      var q = numOf(P, 'q', 90) / 100;
      var bg = type === 'image/jpeg' ? valOf(P, 'bg') : null;
      var ext = type === 'image/webp' ? 'webp' : (type === 'image/png' ? 'png' : 'jpg');
      var before = 0, after = 0, errs = 0;
      btnOf(P, 'run').disabled = true;
      runSeq(items, function (it) {
        it.out = null;
        it.failed = false;
        return loadBitmap(it.file).then(function (bmp) {
          var s = bitmapSize(bmp);
          var cv = drawToCanvas(bmp, s.w, s.h, bg);
          if (bmp.close) bmp.close();
          return canvasToBlob(cv, type, type === 'image/png' ? undefined : q).then(function (blob) {
            it.out = blob;
            it.thumb = it.thumb || thumbOf(cv);
            it.outName = baseName(it.file.name) + '.' + ext;
            it.meta = extOf(it.file.name).toUpperCase() + ' → ' + ext.toUpperCase();
            before += it.file.size; after += blob.size;
          });
        }).catch(function (e) {
          errs++;
          it.failed = true;
          it.meta = '<span class="tl-warn">' + esc(plainErr(e, '转换失败')) + '</span>';
        });
      }).then(function () {
        btnOf(P, 'run').disabled = false;
        refresh();
        setStat(P, sizeCell(before, after),
          errs ? '<b>' + errs + '</b> 个文件转换失败（可能是浏览器不支持该格式的解码）。' :
            '体积为「所有原图之和 → 所有结果之和」。转出来不一定更小：照片转 WebP 通常小很多，' +
            '而大片纯色的图（截图、图标）转 WebP 反而可能变大，那种图保留 PNG 更划算。');
        toast(P, errs ? ('完成，' + errs + ' 个失败') : '转换完成', errs ? 'err' : 'ok');
      });
    });

    btnOf(P, 'zip').addEventListener('click', function () {
      zipItems(items, 'converted.zip').catch(function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
    });
    btnOf(P, 'clear').addEventListener('click', function () {
      box.clear(); items.length = 0; refresh(); setStat(P, null);
    });
    refresh();
  }

  /* ---------------- 03 尺寸与 DPI ---------------- */
  var PNG_CHUNK_PHYS = [0x70, 0x48, 0x59, 0x73];   // 'pHYs'

  function pngSetDpi(bytes, dpi) {
    var ppm = Math.round(dpi / 0.0254);
    var chunksList = [];
    var pos = 8;
    while (pos + 8 <= bytes.length) {
      var len = ((bytes[pos] << 24) | (bytes[pos + 1] << 16) | (bytes[pos + 2] << 8) | bytes[pos + 3]) >>> 0;
      var type = String.fromCharCode(bytes[pos + 4], bytes[pos + 5], bytes[pos + 6], bytes[pos + 7]);
      var end = pos + 12 + len;
      if (end > bytes.length) break;
      if (type !== 'pHYs') chunksList.push(bytes.slice(pos, end));
      pos = end;
      if (type === 'IEND') break;
    }
    if (!chunksList.length) return bytes;

    var data = new Uint8Array(9);
    var dv = new DataView(data.buffer);
    dv.setUint32(0, ppm);
    dv.setUint32(4, ppm);
    dv.setUint8(8, 1);                               // 单位：米
    var td = concatBytes([new Uint8Array(PNG_CHUNK_PHYS), data]);
    var c = crc32(td);
    var phys = concatBytes([
      new Uint8Array([0, 0, 0, 9]), td,
      new Uint8Array([(c >>> 24) & 255, (c >>> 16) & 255, (c >>> 8) & 255, c & 255])
    ]);

    var out = [bytes.slice(0, 8)];
    chunksList.forEach(function (ch) {
      out.push(ch);
      // 紧跟 IHDR 之后插入 pHYs（规范要求 pHYs 在 IDAT 之前）
      if (ch[4] === 0x49 && ch[5] === 0x48 && ch[6] === 0x44 && ch[7] === 0x52) out.push(phys);
    });
    return concatBytes(out);
  }

  function jpegSetDpi(bytes, dpi) {
    if (bytes[0] !== 0xFF || bytes[1] !== 0xD8) return bytes;
    var pos = 2;
    while (pos + 4 <= bytes.length) {
      if (bytes[pos] !== 0xFF) break;
      var marker = bytes[pos + 1];
      if (marker === 0xE0) {
        var segLen = (bytes[pos + 2] << 8) | bytes[pos + 3];
        if (bytes[pos + 4] === 0x4A && bytes[pos + 5] === 0x46 && bytes[pos + 6] === 0x49 &&
            bytes[pos + 7] === 0x46 && bytes[pos + 8] === 0x00 && segLen >= 14) {
          var cp = bytes.slice();
          var u = pos + 4 + 5 + 2;                  // identifier(5) + version(2)
          cp[u] = 1;                                // units = 每英寸点数
          cp[u + 1] = (dpi >> 8) & 255; cp[u + 2] = dpi & 255;
          cp[u + 3] = (dpi >> 8) & 255; cp[u + 4] = dpi & 255;
          return cp;
        }
        break;
      }
      if (marker === 0xDA || marker === 0xD9) break;
      var sl = (bytes[pos + 2] << 8) | bytes[pos + 3];
      if (sl < 2) break;
      pos += 2 + sl;
    }
    // 没有 JFIF 段就自己补一段（浏览器导出的 JPEG 有时不带 APP0）
    var app0 = new Uint8Array(18);
    app0[0] = 0xFF; app0[1] = 0xE0; app0[2] = 0x00; app0[3] = 0x10;
    app0[4] = 0x4A; app0[5] = 0x46; app0[6] = 0x49; app0[7] = 0x46; app0[8] = 0x00;
    app0[9] = 0x01; app0[10] = 0x01; app0[11] = 1;
    app0[12] = (dpi >> 8) & 255; app0[13] = dpi & 255;
    app0[14] = (dpi >> 8) & 255; app0[15] = dpi & 255;
    return concatBytes([bytes.slice(0, 2), app0, bytes.slice(2)]);
  }

  function setupResize() {
    var P = panelOf('resize');
    if (!P) return;
    var items = [];
    bindOutputs(P);
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); } });

    var modeEl = field(P, 'mode');
    function syncMode() {
      var m = modeEl.value;
      fill(P, 'pct').parentNode.style.opacity = m === 'percent' ? 1 : .35;
      fill(P, 'w').parentNode.style.opacity = (m === 'percent') ? .35 : 1;
      fill(P, 'h').parentNode.style.opacity = (m === 'wh') ? 1 : .35;
      fill(P, 'h').disabled = (m !== 'wh');
    }
    function fill(P, n) { return field(P, n).closest('.tl-opt') || field(P, n); }
    modeEl.addEventListener('change', syncMode);
    syncMode();

    function refresh() {
      renderList(P, items, {
        onChange: refresh,
        meta: function (it) {
          var s = it.meta || (it.dim || '');
          if (it.failed) return s;
          if (it.out) {
            s += ' · ' + fmtBytes(it.file.size) + ' → <span class="up">' + fmtBytes(it.out.size) + '</span>';
          } else s += ' · ' + fmtBytes(it.file.size);
          return s;
        }
      });
      btnOf(P, 'zip').disabled = !items.some(function (it) { return it.out; });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选几张图片', 'err');
      var mode = valOf(P, 'mode'), pct = numOf(P, 'pct', 100) / 100;
      var lockW = parseInt(valOf(P, 'w'), 10) || 0, lockH = parseInt(valOf(P, 'h'), 10) || 0;
      var dpi = parseInt(valOf(P, 'dpi'), 10) || 0;
      var errs = 0;
      btnOf(P, 'run').disabled = true;
      runSeq(items, function (it) {
        it.out = null;
        it.failed = false;
        return loadBitmap(it.file).then(function (bmp) {
          var s = bitmapSize(bmp);
          it.dim = s.w + '×' + s.h;
          var tw, th;
          if (mode === 'percent') { tw = Math.round(s.w * pct); th = Math.round(s.h * pct); }
          else if (mode === 'width') { tw = lockW; th = Math.round(s.h * (lockW / s.w)); }
          else { tw = lockW; th = lockH; }
          tw = Math.max(1, tw); th = Math.max(1, th);
          var type = (it.file.type === 'image/png') ? 'image/png' : 'image/jpeg';
          var cv = drawToCanvas(bmp, tw, th, type === 'image/jpeg' ? '#ffffff' : null);
          if (bmp.close) bmp.close();
          return canvasToBlob(cv, type, 0.92).then(function (blob) {
            it.thumb = it.thumb || thumbOf(cv);
            var ext = type === 'image/png' ? 'png' : 'jpg';
            it.outName = baseName(it.file.name) + '-' + tw + 'x' + th + '.' + ext;
            it.meta = it.dim + ' → ' + tw + '×' + th + ' · ' + dpi + ' DPI';
            return blobToBytes(blob).then(function (bts) {
              var patched = dpi
                ? (type === 'image/png' ? pngSetDpi(bts, dpi) : jpegSetDpi(bts, dpi))
                : bts;
              it.out = new Blob([patched], { type: type });
              // 体积交给列表统一渲染，这里不再拼，免得同一个数字显示两遍
            });
          });
        }).catch(function (e) {
          errs++;
          it.failed = true;
          it.meta = '<span class="tl-warn">' + esc(plainErr(e, '处理失败')) + '</span>';
        });
      }).then(function () {
        btnOf(P, 'run').disabled = false;
        refresh();
        toast(P, errs ? ('完成，' + errs + ' 个失败') : '处理完成', errs ? 'err' : 'ok');
        setStat(P, [['已处理', items.filter(function (i) { return i.out; }).length + ' / ' + items.length]],
          dpi ? 'DPI 已写进文件头（PNG 用 pHYs 块、JPG 用 JFIF 段），打印软件会按它换算实际尺寸；像素数没变。' : '');
      });
    });

    btnOf(P, 'zip').addEventListener('click', function () {
      zipItems(items, 'resized.zip').catch(function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
    });
    btnOf(P, 'clear').addEventListener('click', function () { box.clear(); items.length = 0; refresh(); setStat(P, null); });
    refresh();
  }

  /* ---------------- 04 图片转 PDF ---------------- */
  function setupPdf() {
    var P = panelOf('pdf');
    if (!P) return;
    var items = [];
    bindOutputs(P);
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); } });

    function refresh() {
      renderList(P, items, {
        reorder: true,
        onChange: refresh,
        meta: function (it, i) {
          return '第 ' + (i + 1) + ' 页 · ' + (it.dim || '') + ' · ' + fmtBytes(it.file.size);
        }
      });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选几张图片', 'err');
      var q = numOf(P, 'q', 88) / 100;
      var mode = valOf(P, 'size');
      var margin = numOf(P, 'margin', 0);
      var failed = 0;
      btnOf(P, 'run').disabled = true;

      runSeq(items, function (it) {
        it._pdf = null;
        it.out = null;
        return loadBitmap(it.file).then(function (bmp) {
          var s = bitmapSize(bmp);
          it.dim = s.w + '×' + s.h;
          it.thumb = it.thumb || thumbOf(bmp);
          // PDF 里嵌 JPEG 最省体积，所以统一转成 JPEG（PNG 的透明处补白底）
          var cv = drawToCanvas(bmp, s.w, s.h, '#ffffff');
          if (bmp.close) bmp.close();
          return canvasToBlob(cv, 'image/jpeg', q).then(function (blob) {
            return blobToBytes(blob).then(function (bts) {
              it._pdf = { bytes: bts, w: s.w, h: s.h };
            });
          });
        }).catch(function (e) {
          failed++;
          it.dim = '<span class="tl-warn">' + esc(plainErr(e, '无法读取')) + '</span>';
          return null;
        });
      }).then(function () {
        // 列表里 ↑↓ 调过的顺序就是页序（items 本身已被换过位置）
        var ready = [];
        items.forEach(function (it) { if (it._pdf) ready.push(it._pdf); });
        if (!ready.length) throw new Error('没有可用的图片');
        var bytes = buildPdf(ready, { mode: mode, marginMM: margin });
        download(new Blob([bytes], { type: 'application/pdf' }),
          'images-' + new Date().toISOString().slice(0, 10) + '.pdf');
        setStat(P, [
          ['页数', String(ready.length)],
          ['PDF 体积', fmtBytes(bytes.length)],
          ['页面尺寸', mode === 'fit' ? '贴合图片' : (mode === 'a4l' ? 'A4 横版' : 'A4 竖版')]
        ], failed
          ? '<b>' + failed + '</b> 张图片无法读取，已跳过。'
          : '合成引擎是本站自己实现的：图片以原始 JPEG 数据直接嵌进 PDF，不做二次转码。');
        toast(P, 'PDF 已生成');
      }).catch(function (e) {
        toast(P, plainErr(e, '生成失败'), 'err');
      }).then(function () {
        btnOf(P, 'run').disabled = false;
        refresh();
      });
    });

    btnOf(P, 'clear').addEventListener('click', function () { box.clear(); items.length = 0; refresh(); setStat(P, null); });
    refresh();
  }

  /* ---------------- 05 批量加水印 ---------------- */
  function setupWatermark() {
    var P = panelOf('watermark');
    if (!P) return;
    var items = [];
    var posIdx = 8;
    bindOutputs(P);
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); } });

    $$('[data-pos] button', P).forEach(function (b) {
      b.addEventListener('click', function () {
        posIdx = +b.getAttribute('data-p');
        $$('[data-pos] button', P).forEach(function (x) { x.classList.remove('on'); });
        b.classList.add('on');
      });
    });
    var last = $('[data-pos] button[data-p="8"]', P);
    if (last) last.classList.add('on');

    function refresh() {
      renderList(P, items, {
        onChange: refresh,
        meta: function (it) {
          var s = it.meta || (it.dim || '');
          if (it.failed) return s;
          if (it.out) {
            s += ' · ' + fmtBytes(it.file.size) + ' → <span class="up">' + fmtBytes(it.out.size) + '</span>';
          } else s += ' · ' + fmtBytes(it.file.size);
          return s;
        }
      });
      btnOf(P, 'zip').disabled = !items.some(function (it) { return it.out; });
    }

    function drawWatermark(bmp, text, opts) {
      var s = bitmapSize(bmp);
      var cv = drawToCanvas(bmp, s.w, s.h, null);
      var ctx = cv.getContext('2d');
      var fs = Math.max(10, s.w * opts.size / 100);
      ctx.font = '700 ' + fs + 'px -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif';
      ctx.textBaseline = 'middle';
      ctx.globalAlpha = opts.alpha / 100;

      function paint(x, y, rot) {
        ctx.save();
        ctx.translate(x, y);
        if (rot) ctx.rotate(rot * Math.PI / 180);
        if (opts.shadow) {
          ctx.lineWidth = Math.max(1, fs * 0.07);
          ctx.strokeStyle = opts.color === '#ffffff' ? 'rgba(0,0,0,.55)' : 'rgba(255,255,255,.55)';
          ctx.lineJoin = 'round';
          ctx.strokeText(text, -ctx.measureText(text).width / 2, 0);
        }
        ctx.fillStyle = opts.color;
        ctx.fillText(text, -ctx.measureText(text).width / 2, 0);
        ctx.restore();
      }

      if (opts.tile) {
        var tw = ctx.measureText(text).width + fs * 1.6;
        var th = fs * 4;
        ctx.globalAlpha = opts.alpha / 100 * 0.75;
        for (var y = th / 2; y < s.h + th; y += th) {
          for (var x = tw / 2; x < s.w + tw; x += tw) paint(x, y, -opts.rot);
        }
      } else {
        var pad = s.w * opts.pad / 100 + fs * 0.7;
        var col = opts.pos % 3, row = Math.floor(opts.pos / 3);
        var w2 = ctx.measureText(text).width / 2;
        var x2 = col === 0 ? pad + w2 : (col === 1 ? s.w / 2 : s.w - pad - w2);
        var y2 = row === 0 ? pad + fs / 2 : (row === 1 ? s.h / 2 : s.h - pad - fs / 2);
        paint(x2, y2, opts.rot);
      }
      ctx.globalAlpha = 1;
      return cv;
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选几张图片', 'err');
      var text = String(valOf(P, 'text') || '').trim();
      if (!text) return toast(P, '先写点水印文字', 'err');
      var opts = {
        size: numOf(P, 'size', 4.5), color: valOf(P, 'color'),
        alpha: numOf(P, 'alpha', 55), rot: numOf(P, 'rot', 0),
        pad: numOf(P, 'pad', 3), pos: posIdx,
        tile: !!valOf(P, 'tile'), shadow: !!valOf(P, 'shadow')
      };
      var type = 'image/jpeg', errs = 0;
      btnOf(P, 'run').disabled = true;
      runSeq(items, function (it) {
        it.out = null;
        it.failed = false;
        return loadBitmap(it.file).then(function (bmp) {
          var s = bitmapSize(bmp);
          it.dim = s.w + '×' + s.h;
          var cv = drawWatermark(bmp, text, opts);
          if (bmp.close) bmp.close();
          var keepPng = it.file.type === 'image/png';
          return canvasToBlob(cv, keepPng ? 'image/png' : type, keepPng ? undefined : 0.92)
            .then(function (blob) {
              it.out = blob;
              it.thumb = it.thumb || thumbOf(cv);
              it.outName = baseName(it.file.name) + '-wm.' + (keepPng ? 'png' : 'jpg');
              it.meta = it.dim;
            });
        }).catch(function (e) {
          errs++;
          it.failed = true;
          it.meta = '<span class="tl-warn">' + esc(plainErr(e, '处理失败')) + '</span>';
        });
      }).then(function () {
        btnOf(P, 'run').disabled = false;
        refresh();
        setStat(P, [['已加水印', items.filter(function (i) { return i.out; }).length + ' / ' + items.length]],
          '水印是画在像素上的，导出的图就长这样，别人拿到的就是带水印的版本；' +
          '原图不会被改动（本站不保存任何文件）。');
        toast(P, errs ? ('完成，' + errs + ' 个失败') : '水印已加好，可逐张下载或打包', errs ? 'err' : 'ok');
      });
    });

    btnOf(P, 'zip').addEventListener('click', function () {
      zipItems(items, 'watermarked.zip').catch(function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
    });
    btnOf(P, 'clear').addEventListener('click', function () {
      box.clear(); items.length = 0; refresh(); setStat(P, null);
    });
    refresh();
  }

  /** 清掉面板上的提示条 */
  function clearToast(P) {
    var msg = $('[data-msg]', P);
    if (!msg) return;
    clearTimeout(msg._t);
    msg.className = 'tl-msg';
    msg.textContent = '';
  }

  /* ---------------- 06 长图拼接 ---------------- */
  function setupStitch() {
    var P = panelOf('stitch');
    if (!P) return;
    var items = [];
    var preview = $('[data-preview]', P);
    bindOutputs(P);
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); } });

    function resetPreview() {
      if (!preview) return;
      preview.innerHTML = '';
      preview.hidden = true;
    }

    function refresh() {
      renderList(P, items, {
        reorder: true,
        onChange: refresh,
        meta: function (it) {
          if (it.meta) return it.meta;
          var s = bitmapSizeLabel(it);
          return s + ' · ' + fmtBytes(it.file.size);
        }
      });
      if (!items.length) { resetPreview(); setStat(P, null); }
    }

    function bitmapSizeLabel(it) {
      return it.dim || extOf(it.file.name).toUpperCase();
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (items.length < 2) return toast(P, '至少选两张图片才能拼接', 'err');
      var dir = valOf(P, 'dir') === 'h' ? 'h' : 'v';
      var gap = Math.max(0, Math.round(numOf(P, 'gap', 0)));
      var bg = valOf(P, 'bg') || '#ffffff';
      var align = valOf(P, 'align') || 'center';
      var uniform = !!valOf(P, 'uniform');
      var btn = btnOf(P, 'run');
      btn.disabled = true;
      resetPreview();

      var sizes = [];
      runSeq(items, function (it, i) {
        it.dim = '';
        return loadBitmap(it.file).then(function (bmp) {
          var s = bitmapSize(bmp);
          sizes[i] = { w: s.w, h: s.h };
          it._bmp = bmp;
          it.dim = s.w + '×' + s.h;
          it.thumb = it.thumb || thumbOf(bmp);
        }).catch(function (e) {
          sizes[i] = null;
          it._bmp = null;
          it.meta = '<span class="tl-warn">' + esc(plainErr(e, '读取失败')) + '</span>';
        });
      }).then(function () {
        var use = [];
        items.forEach(function (it, i) { if (sizes[i]) use.push(i); });
        if (use.length < 2) {
          freeBitmaps();
          btn.disabled = false;
          refresh();
          return toast(P, '能用的图片不足两张（其余可能不是浏览器认识的照片格式）', 'err');
        }

        // 参差不齐时先统一到最长边，避免留白或拉伸
        var target = 0;
        if (uniform) {
          use.forEach(function (i) {
            var t = dir === 'v' ? sizes[i].w : sizes[i].h;
            if (t > target) target = t;
          });
        }
        var dims = use.map(function (i) {
          var s = sizes[i];
          if (!uniform) return { w: s.w, h: s.h };
          var sc = target / (dir === 'v' ? s.w : s.h);
          return { w: Math.max(1, Math.round(s.w * sc)), h: Math.max(1, Math.round(s.h * sc)) };
        });

        var totalW, totalH;
        if (dir === 'v') {
          totalW = Math.max.apply(null, dims.map(function (d) { return d.w; }));
          totalH = dims.reduce(function (a, d) { return a + d.h; }, 0) + gap * (use.length - 1);
        } else {
          totalH = Math.max.apply(null, dims.map(function (d) { return d.h; }));
          totalW = dims.reduce(function (a, d) { return a + d.w; }, 0) + gap * (use.length - 1);
        }

        // 只在超出浏览器画布硬上限时才整体缩小，并明确告知
        var MAXDIM = 16000, MAXAREA = 80 * 1e6;
        var shrink = 1, forced = false;
        if (Math.max(totalW, totalH) > MAXDIM) { shrink = MAXDIM / Math.max(totalW, totalH); forced = true; }
        if (totalW * totalH * shrink * shrink > MAXAREA) { shrink = Math.sqrt(MAXAREA / (totalW * totalH)); forced = true; }
        var cvW = Math.max(1, Math.round(totalW * shrink));
        var cvH = Math.max(1, Math.round(totalH * shrink));

        var cv = newCanvas(cvW, cvH);
        var ctx = cv.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, cvW, cvH);

        var cursor = 0;
        use.forEach(function (i, k) {
          var d = dims[k];
          var w = Math.max(1, Math.round(d.w * shrink));
          var h = Math.max(1, Math.round(d.h * shrink));
          // 交叉轴 = 垂直于拼接方向的那条边，用来算居中/靠前/靠后的偏移；
          // 前进轴 = 沿拼接方向的那条边，用来把游标推到下一张的起点。两者别混用
          // （竖拼按高度前进、按宽度居中；横拼反过来），混了会让图片互相压住或隔出空白。
          var cross = dir === 'v' ? cvW : cvH;
          var crossOwn = dir === 'v' ? w : h;
          var stepOwn = dir === 'v' ? h : w;
          var off = align === 'start' ? 0 : (align === 'end' ? cross - crossOwn : Math.round((cross - crossOwn) / 2));
          if (dir === 'v') ctx.drawImage(items[i]._bmp, off, cursor, w, h);
          else ctx.drawImage(items[i]._bmp, cursor, off, w, h);
          cursor += stepOwn + (k < use.length - 1 ? Math.round(gap * shrink) : 0);
        });

        freeBitmaps();

        // 像素特别多时 PNG 会大到浏览器都吐不出来，改用高质量的 JPG
        var bigPixels = cvW * cvH > 40e6;
        var type = bigPixels ? 'image/jpeg' : 'image/png';
        return canvasToBlob(cv, type, bigPixels ? 0.95 : undefined).then(function (blob) {
          if (!blob) throw new Error('浏览器拒绝了这张超长图的生成，请减少张数或先压缩');
          var ext = bigPixels ? 'jpg' : 'png';
          var name = 'long-' + cvW + 'x' + cvH + '.' + ext;
          if (preview) {
            var pv = newCanvas(cv.width, cv.height);
            var pctx = pv.getContext('2d');
            var psc = Math.min(1, 1200 / Math.max(cv.width, cv.height));
            pv.width = Math.max(1, Math.round(cv.width * psc));
            pv.height = Math.max(1, Math.round(cv.height * psc));
            pctx.imageSmoothingQuality = 'high';
            pctx.drawImage(cv, 0, 0, pv.width, pv.height);
            pv.style.cursor = 'default';
            preview.innerHTML = '';
            preview.appendChild(pv);
            preview.hidden = false;
          }
          setStat(P, [
            ['拼接张数', use.length + ' 张'],
            ['成品尺寸', cvW + ' × ' + cvH],
            ['成品体积', fmtBytes(blob.size)]
          ], '预览已显示在上方（最长边缩到 1200 px，只为显示；下载的是完整尺寸）。' +
            (forced ? '<b>注意：</b>原始拼接尺寸超出浏览器的画布上限，已整体等比缩小 ' +
              (Math.round(shrink * 1000) / 10) + '%。要保留原尺寸请分批拼接。' : '') +
            (bigPixels ? '这张图像素太多，PNG 会大到存不下来，所以输出的是高质量 JPG。' : ''));
          download(blob, name);
          toast(P, '拼接完成，已开始下载 ' + name, 'ok');
        });
      }).catch(function (e) {
        freeBitmaps();
        toast(P, plainErr(e, '拼接失败'), 'err');
      }).then(function () {
        btn.disabled = false;
        refresh();
      });
    });

    function freeBitmaps() {
      items.forEach(function (it) {
        if (it._bmp && it._bmp.close) it._bmp.close();
        it._bmp = null;
      });
    }

    btnOf(P, 'clear').addEventListener('click', function () {
      freeBitmaps();
      box.clear();
      items.length = 0;
      refresh();
    });
    refresh();
  }

  /* ---------------- 07 EXIF 查看与清除 ---------------- */
  function setupExif() {
    var P = panelOf('exif');
    if (!P) return;
    var items = [];
    var list = $('[data-list]', P);
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); scrollPanel(P); } });

    function refresh() {
      var has = items.length > 0;
      btnOf(P, 'run').disabled = !has;
      btnOf(P, 'strip').disabled = !has;
      if (!has) {
        list.innerHTML = '';
        setStat(P, null);
        clearToast(P);
        return;
      }
      list.innerHTML = items.map(function (it, i) {
        var th = it.thumb ? '<img class="tl-item-th" src="' + it.thumb + '" alt="">' : '<span class="tl-item-th"></span>';
        return '<div class="tl-item">' + th +
          '<div class="tl-item-main"><div class="tl-item-nm" title="' + esc(it.file.name) + '">' +
          esc(it.file.name) + '</div><div class="tl-item-mt">' +
          (it.meta || (extOf(it.file.name).toUpperCase() + ' · ' + fmtBytes(it.file.size))) +
          '</div></div><div class="tl-item-act">' +
          '<button class="tl-mini" type="button" data-del="' + i + '" aria-label="移除">×</button>' +
          '</div></div>' + (it.exifHtml || '');
      }).join('');
      $$('[data-del]', list).forEach(function (b) {
        b.addEventListener('click', function () {
          var i = +b.getAttribute('data-del');
          if (items[i] && items[i].thumb) URL.revokeObjectURL(items[i].thumb);
          items.splice(i, 1);
          refresh();
        });
      });
    }

    function exifBlock(res) {
      if (!res || !res.rows || !res.rows.length) {
        return '<div class="tl-note">这张图里没读到 EXIF。常见原因：被微信、微博等平台重新压过一次' +
          '（元数据在那一步就被抹掉了），或者本来就不是相机／手机直出的照片。</div>';
      }
      var hasGps = res.rows.some(function (r) { return r.name.indexOf('GPS ') === 0; });
      var h = '';
      if (hasGps) {
        h += '<div class="tl-note tl-warn">⚠ 这张图带着 GPS 坐标，' +
          '能定位到拍摄地点。要发到公开场合，建议先用下面的按钮清一遍。</div>';
      }
      h += '<table class="tl-tbl"><tbody>';
      res.rows.forEach(function (r) {
        h += '<tr><th>' + esc(r.name) + '</th><td>' + esc(exifPretty(r.name, r.value)) + '</td></tr>';
      });
      return h + '</tbody></table>';
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选照片', 'err');
      var btn = btnOf(P, 'run');
      btn.disabled = true;
      var withExif = 0;
      runSeq(items, function (it) {
        return blobToBytes(it.file).then(function (bytes) {
          var isJpeg = bytes.length > 3 && bytes[0] === 0xFF && bytes[1] === 0xD8;
          it.meta = extOf(it.file.name).toUpperCase() + ' · ' + fmtBytes(it.file.size);
          if (!isJpeg) {
            it.exifHtml = '<div class="tl-note">不是 JPG 文件，读不到 EXIF。' +
              '需要的话先用「格式转换」转成 JPG 再回来读。</div>';
          } else {
            var res = parseExif(bytes);
            it.exifHtml = exifBlock(res);
            if (res && res.rows && res.rows.length) withExif++;
          }
          if (it.thumb) return;
          return loadBitmap(it.file).then(function (bmp) {
            it.thumb = thumbOf(bmp);
            if (bmp.close) bmp.close();
          }).catch(function () { /* 缩略图失败无所谓 */ });
        });
      }).then(function () {
        btn.disabled = false;
        refresh();
        setStat(P, [
          ['已读取', items.length + ' 张'],
          ['含 EXIF', withExif + ' 张'],
          ['不含', (items.length - withExif) + ' 张']
        ], 'EXIF 是相机或手机写进照片里的描述信息，含拍摄时间、机型，有时还有拍摄地点的经纬度。' +
          '「导出已清除副本」会生成一张把这些信息去掉的新图，画面本身一个像素都不动。');
        toast(P, '读取完成：' + items.length + ' 张里 ' + withExif + ' 张含 EXIF 信息', 'ok');
      }).catch(function (e) {
        btn.disabled = false;
        toast(P, plainErr(e, '读取失败'), 'err');
      });
    });

    btnOf(P, 'strip').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选照片', 'err');
      var btn = btnOf(P, 'strip');
      btn.disabled = true;
      var out = [], used = {}, cleared = 0, skipped = 0;
      runSeq(items, function (it) {
        return blobToBytes(it.file).then(function (bytes) {
          if (!(bytes.length > 3 && bytes[0] === 0xFF && bytes[1] === 0xD8)) { skipped++; return; }
          var nm = baseName(it.file.name) + '-clean.jpg';
          if (used[nm]) nm = baseName(nm) + '-' + (++used[nm]) + '.jpg';
          else used[nm] = 1;
          out.push({ name: nm, bytes: stripMetadata(bytes) });
          cleared++;
        });
      }).then(function () {
        btn.disabled = false;
        if (!out.length) return toast(P, '这些文件都不是 JPG，清除只对 JPG 有效', 'err');
        if (out.length === 1) {
          download(new Blob([out[0].bytes], { type: 'image/jpeg' }), out[0].name);
        } else {
          download(new Blob([zipStore(out)], { type: 'application/zip' }), 'exif-cleared.zip');
        }
        toast(P, '已清除 ' + cleared + ' 张' + (skipped ? '，跳过 ' + skipped + ' 张非 JPG' : '') +
          (out.length > 1 ? '，已打包为 exif-cleared.zip' : ''), 'ok');
      }).catch(function (e) {
        btn.disabled = false;
        toast(P, plainErr(e, '处理失败'), 'err');
      });
    });

    btnOf(P, 'clear').addEventListener('click', function () {
      box.clear();
      items.length = 0;
      refresh();
    });
    refresh();
  }

  /* ---------------- 08 取色与色板 ---------------- */
  function rgbToHsl(r, g, b) {
    var rr = r / 255, gg = g / 255, bb = b / 255;
    var max = Math.max(rr, gg, bb), min = Math.min(rr, gg, bb);
    var h = 0, s = 0, l = (max + min) / 2;
    var d = max - min;
    if (d > 0) {
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      if (max === rr) h = ((gg - bb) / d) % 6;
      else if (max === gg) h = (bb - rr) / d + 2;
      else h = (rr - gg) / d + 4;
      h *= 60;
      if (h < 0) h += 360;
    }
    return { h: Math.round(h), s: Math.round(s * 100), l: Math.round(l * 100) };
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

  function setupColor() {
    var P = panelOf('color');
    if (!P) return;
    var items = [];
    var wrap = $('[data-canvas]', P);
    var picked = $('[data-picked]', P);
    var swatches = $('[data-swatches]', P);
    var curBmp = null, curCv = null;
    var box = bindDrop(P, { items: items, multiple: false, onAdd: function () { open(); } });

    function releaseBmp() {
      if (curBmp && curBmp.close) curBmp.close();
      curBmp = null;
    }

    function open() {
      var it = items[0];
      releaseBmp();
      picked.hidden = true;
      swatches.innerHTML = '';
      wrap.innerHTML = '';
      wrap.hidden = true;
      setStat(P, null);
      clearToast(P);
      if (!it) return;
      loadBitmap(it.file).then(function (bmp) {
        curBmp = bmp;
        var s = bitmapSize(bmp);
        var sc = Math.min(1, 700 / Math.max(s.w, s.h));
        curCv = drawToCanvas(bmp, Math.max(1, Math.round(s.w * sc)), Math.max(1, Math.round(s.h * sc)), null);
        curCv.title = '在图上点一下取这个点的颜色';
        curCv.addEventListener('click', onPick);
        wrap.appendChild(curCv);
        wrap.hidden = false;
        toast(P, '图片已就位（显示尺寸 ' + curCv.width + '×' + curCv.height + '）· 在图上点一下取色，' +
          '或点「提取主色板」看整张图的主色调', 'ok');
      }).catch(function (e) {
        toast(P, plainErr(e, '这张图读不出来'), 'err');
      });
    }

    function onPick(e) {
      var rect = curCv.getBoundingClientRect();
      var x = Math.round((e.clientX - rect.left) * curCv.width / rect.width);
      var y = Math.round((e.clientY - rect.top) * curCv.height / rect.height);
      x = Math.max(0, Math.min(curCv.width - 1, x));
      y = Math.max(0, Math.min(curCv.height - 1, y));
      var d;
      try { d = curCv.getContext('2d').getImageData(x, y, 1, 1).data; }
      catch (err) { return toast(P, '取色失败：这张图跨域了，浏览器不允许读它的像素', 'err'); }
      showPicked(d[0], d[1], d[2], x, y);
    }

    function showPicked(r, g, b, x, y) {
      var hex = rgbToHex(r, g, b);
      var hsl = rgbToHsl(r, g, b);
      var rgbStr = 'rgb(' + r + ', ' + g + ', ' + b + ')';
      var hslStr = 'hsl(' + hsl.h + ', ' + hsl.s + '%, ' + hsl.l + '%)';
      picked.innerHTML =
        '<div class="tl-picked-c" style="background:' + hex + '"></div>' +
        '<div class="tl-picked-t">' +
        '取样点：第 ' + (x + 1) + ' 列、第 ' + (y + 1) + ' 行（按显示尺寸）<br>' +
        'HEX <b>' + hex + '</b> · RGB <b>' + rgbStr + '</b> · HSL <b>' + hslStr + '</b>' +
        '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">' +
        '<button class="tl-mini" type="button" data-copyhex="' + hex + '">复制 HEX</button>' +
        '<button class="tl-mini" type="button" data-copyrgb="' + rgbStr + '">复制 RGB</button>' +
        '<button class="tl-mini" type="button" data-copyhsl="' + hslStr + '">复制 HSL</button>' +
        '</div></div>';
      picked.hidden = false;
      $$('[data-copyhex],[data-copyrgb],[data-copyhsl]', picked).forEach(function (btn) {
        btn.addEventListener('click', function () {
          var v = btn.getAttribute('data-copyhex') || btn.getAttribute('data-copyrgb') ||
            btn.getAttribute('data-copyhsl');
          copyText(v).then(function () { toast(P, '已复制 ' + v, 'ok'); },
            function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
        });
      });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选一张图片', 'err');
      if (!curBmp) return open();
      var pal = extractPalette(curBmp, 8);
      if (!pal.length) return toast(P, '这张图取不出颜色（可能是全透明或纯色）', 'err');
      swatches.innerHTML = pal.map(function (c, i) {
        return '<button class="tl-sw" type="button" data-hex="' + c.hex + '" ' +
          'title="点击复制 ' + c.hex + '">' +
          '<span class="tl-sw-c" style="display:block;background:' + c.hex + '"></span>' +
          '<span class="tl-sw-t">' + c.hex + (i === 0 ? '（最多）' : '') + '</span></button>';
      }).join('') +
        '<div class="tl-note" style="grid-column:1/-1">' +
        '<button class="tl-mini" type="button" data-copyall>复制全部色值</button></div>';
      $$('[data-hex]', swatches).forEach(function (b) {
        b.addEventListener('click', function () {
          var hex = b.getAttribute('data-hex');
          copyText(hex).then(function () { toast(P, '已复制 ' + hex, 'ok'); },
            function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
        });
      });
      var allBtn = $('[data-copyall]', swatches);
      if (allBtn) {
        allBtn.addEventListener('click', function () {
          var lines = pal.map(function (c) {
            var hsl = rgbToHsl(c.r, c.g, c.b);
            return c.hex + '  rgb(' + c.r + ', ' + c.g + ', ' + c.b + ')  hsl(' +
              hsl.h + ', ' + hsl.s + '%, ' + hsl.l + '%)';
          }).join('\n');
          copyText(lines).then(function () { toast(P, '已复制 ' + pal.length + ' 个色值', 'ok'); },
            function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
        });
      }
      setStat(P, [
        ['提取颜色', pal.length + ' 个'],
        ['最主色', pal[0].hex]
      ], '按面积占比从大到小排。点任意色块复制色值，做设计抄色时很方便。');
      toast(P, '主色板已提取', 'ok');
    });

    btnOf(P, 'clear').addEventListener('click', function () {
      releaseBmp();
      box.clear();
      items.length = 0;
      curCv = null;
      wrap.innerHTML = '';
      wrap.hidden = true;
      picked.hidden = true;
      picked.innerHTML = '';
      swatches.innerHTML = '';
      setStat(P, null);
      clearToast(P);
    });
  }

  /* ---------------- 09 二维码生成 ---------------- */
  function setupQr() {
    var P = panelOf('qr');
    if (!P) return;
    var qrBox = $('[data-qrbox]', P);
    var textWrap = $('[data-qr-text]', P);
    var last = null;

    /** WiFi 二维码的字段分隔符要转义，否则读出来会串位 */
    function wifiEsc(s) {
      return String(s).replace(/([\\;,:"])/g, '\\$1');
    }

    function payload() {
      if (valOf(P, 'kind') === 'wifi') {
        var ssid = String(valOf(P, 'ssid') || '').trim();
        if (!ssid) return { err: '先填 WiFi 名称（SSID）' };
        var sec = valOf(P, 'sec') || 'WPA';
        var s = 'WIFI:T:' + sec + ';S:' + wifiEsc(ssid) + ';';
        if (sec !== 'nopass') s += 'P:' + wifiEsc(String(valOf(P, 'pass') || '')) + ';';
        return { text: s + 'H:false;;' };
      }
      var t = String(valOf(P, 'text') || '').trim();
      if (!t) return { err: '先写点要放进二维码的内容' };
      return { text: t };
    }

    function syncKind() {
      var isWifi = valOf(P, 'kind') === 'wifi';
      $$('[data-qr-bg]', P).forEach(function (el) { el.classList.toggle('tl-hidden', !isWifi); });
      if (textWrap) textWrap.classList.toggle('tl-hidden', isWifi);
    }

    function clearResult() {
      last = null;
      qrBox.innerHTML = '';
      qrBox.hidden = true;
      ['png', 'svg', 'copy'].forEach(function (a) { btnOf(P, a).disabled = true; });
      setStat(P, null);
    }

    function build(quiet) {
      var p = payload();
      if (p.err) {
        if (!quiet) toast(P, p.err, 'err'); else clearResult();
        return null;
      }
      var size = parseInt(valOf(P, 'size'), 10) || 512;
      var ec = valOf(P, 'ec') || 'M';
      var fg = valOf(P, 'fg') || '#000000';
      var bg = valOf(P, 'bg') || '#ffffff';
      var trans = !!valOf(P, 'trans');
      var qr;
      try {
        qr = qrEncode(p.text, ec);
      } catch (e) {
        clearResult();
        if (!quiet) {
          toast(P, '这段内容装不进一张二维码（上限约 2900 字节）。' +
            '请精简内容，或把容错等级降到 L 再多塞一点', 'err');
        }
        return null;
      }
      var cv = qrToCanvas(qr, { size: size, fg: fg, bg: bg, transparent: trans });
      var svg = qrToSvg(qr, { size: size, fg: fg, bg: bg, transparent: trans });
      last = { cv: cv, svg: svg, qr: qr, bytes: qrUtf8Bytes(p.text).length };
      qrBox.innerHTML = '';
      qrBox.appendChild(cv);
      qrBox.hidden = false;
      ['png', 'svg', 'copy'].forEach(function (a) { btnOf(P, a).disabled = false; });
      setStat(P, [
        ['版本', 'v' + qr.version],
        ['容错', ec],
        ['掩码', '#' + qr.mask],
        ['矩阵', qr.size + '×' + qr.size],
        ['内容', last.bytes + ' 字节']
      ], '版本号越小方块越大、越好扫；内容一长会自动升版本。容错等级越高越抗污损和反光，' +
        '但同样内容需要更大的版本。生成和纠错都在你的浏览器里算，内容不会发到任何服务器。');
      return last;
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (build(false)) toast(P, '二维码已生成，可下载 PNG / SVG 或直接复制图片', 'ok');
    });

    btnOf(P, 'png').addEventListener('click', function () {
      if (!last) return;
      canvasToBlob(last.cv, 'image/png').then(function (b) {
        if (!b) throw new Error('生成图片失败');
        download(b, 'qrcode-' + last.cv.width + '.png');
      }).catch(function (e) { toast(P, plainErr(e, '下载失败'), 'err'); });
    });

    btnOf(P, 'svg').addEventListener('click', function () {
      if (!last) return;
      var size = parseInt(valOf(P, 'size'), 10) || 512;
      download(new Blob([last.svg], { type: 'image/svg+xml;charset=utf-8' }), 'qrcode-' + size + '.svg');
    });

    btnOf(P, 'copy').addEventListener('click', function () {
      if (!last) return;
      copyCanvas(last.cv).then(function () {
        toast(P, '已复制到剪贴板，可以直接粘到聊天窗口或文档里', 'ok');
      }, function (e) {
        toast(P, plainErr(e, '复制失败，请改用「下载 PNG」'), 'err');
      });
    });

    $$('[data-in]', P).forEach(function (el) {
      el.addEventListener('change', function () {
        if (el === field(P, 'kind')) syncKind();
        if (last) build(true);
      });
    });

    syncKind();
    clearResult();
  }

  /* ---------------- 10 音频转 WAV ---------------- */
  function setupAudio() {
    var P = panelOf('audio');
    if (!P) return;
    var items = [];
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); scrollPanel(P); } });

    function refresh() {
      renderList(P, items, {
        onChange: refresh,
        meta: function (it) {
          return it.meta || (extOf(it.file.name).toUpperCase() + ' · ' + fmtBytes(it.file.size));
        }
      });
      btnOf(P, 'zip').disabled = !items.some(function (it) { return it.out; });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选几个音频文件', 'err');
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return toast(P, '这个浏览器不支持音频解码，换 Chrome 或 Safari 新版本试试', 'err');

      var rate = parseInt(valOf(P, 'rate'), 10) || 0;
      var mono = !!valOf(P, 'mono');
      var norm = !!valOf(P, 'norm');
      var btn = btnOf(P, 'run');
      btn.disabled = true;
      toast(P, '正在解码，长音频要等一会儿…', 'ok');

      var ctx = new AC();
      var before = 0, after = 0, errs = 0;
      runSeq(items, function (it) {
        it.out = null;
        return it.file.arrayBuffer().then(function (ab) {
          return new Promise(function (res, rej) {
            var pr = ctx.decodeAudioData(ab, res, rej);   // 老 Safari 只认回调式签名
            if (pr && pr.then) pr.then(res, rej);
          });
        }).then(function (buf) {
          return audioBufferToPcm(buf, { rate: rate, mono: mono, norm: norm });
        }).then(function (pcm) {
          it.out = new Blob([encodeWav(pcm.channels, pcm.rate)], { type: 'audio/wav' });
          it.outName = baseName(it.file.name) + '.wav';
          it.meta = pcm.channels.length + ' 声道 · ' + pcm.rate + ' Hz · ' +
            fmtNum(pcm.channels[0].length / pcm.rate, 1) + ' 秒 · ' + fmtBytes(it.out.size);
          before += it.file.size;
          after += it.out.size;
        }).catch(function (e) {
          errs++;
          it.meta = '<span class="tl-warn">' + esc(plainErr(e, '这个文件浏览器解不开，可能不是常见音频格式，也可能文件损坏')) + '</span>';
        });
      }).then(function () {
        btn.disabled = false;
        if (ctx.close) ctx.close();
        refresh();
        setStat(P, sizeCell(before, after),
          errs ? '<b>' + errs + '</b> 个文件解码失败。浏览器能解的取决于系统解码器，' +
            'mp3、m4a(AAC)、wav 基本都能过，flac、ape 之类不一定。' :
            '转出来的就是标准 PCM WAV（16 位），老设备、老软件都能直接读。');
        toast(P, errs ? ('完成，' + errs + ' 个失败') : '转换完成，可逐个下载或一次打包', errs ? 'err' : 'ok');
      });
    });

    btnOf(P, 'zip').addEventListener('click', function () {
      zipItems(items, 'wav.zip').catch(function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
    });

    btnOf(P, 'clear').addEventListener('click', function () {
      box.clear();
      items.length = 0;
      refresh();
      setStat(P, null);
    });
    refresh();
  }

  /* ======================================================================
     3. 面板展开／收起 + 启动
     十个面板默认是全部展开的（JS 没跑也不丢内容），
     只有这里成功绑好开关之后，才给 <html> 加上 tools-js 把面板收起来。
     ====================================================================== */
  var currentTool = '';

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
    P.classList.add('tl-hl');
    setTimeout(function () { P.classList.remove('tl-hl'); }, 1800);
    if (doScroll) scrollPanel(P);
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
    var setups = [
      setupCompress, setupConvert, setupResize, setupPdf, setupWatermark,
      setupStitch, setupExif, setupColor, setupQr, setupAudio
    ];
    var failed = [];
    // 逐个兜底：某一个工具坏了，不影响其余九个
    setups.forEach(function (fn) {
      try { fn(); }
      catch (e) {
        failed.push(fn.name || '匿名工具');
        if (window.console && console.error) console.error('[tools] ' + (fn.name || '') + ' 初始化失败：', e);
      }
    });

    try {
      wireTiles();
    } catch (e) {
      // 折叠开关没装上就绝不加 tools-js：宁可十个面板全部平铺，也不让内容被藏起来
      if (window.console && console.error) console.error('[tools] 折叠开关绑定失败，已保持全部展开：', e);
      return;
    }
    doc.documentElement.classList.add('tools-js');

    if (failed.length && window.console && console.warn) {
      console.warn('[tools] 以下工具初始化失败，其余仍可使用：' + failed.join('、'));
    }

    window.addEventListener('hashchange', function () { openPanel(fromHash(), true); });
    var init = fromHash();
    if (init) openPanel(init, true);
  }

  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
