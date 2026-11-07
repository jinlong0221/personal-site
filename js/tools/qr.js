/*!
 * tools/qr.js — 09 二维码生成（工具箱·按需加载子模块）
 *
 * 由 tools.js 框架在用户点开对应卡片时才注入执行，不参与首屏加载。
 * 与主文件同一套红线：零外部依赖、零 CDN、零网络请求，文件不离开浏览器。
 * 用到的公共函数全部经顶部解构自 window.LXTools.api 取得；
 * 不要在 IIFE 之外挂任何全局，也不要依赖别的子模块。
 */
(function () {
  'use strict';
  var _ = (window.LXTools || {}).api;
  if (!_) return;
  var $ = _.$;
  var $$ = _.$$;
  var btnOf = _.btnOf, canvasToBlob = _.canvasToBlob, copyCanvas = _.copyCanvas, 
    download = _.download, field = _.field, newCanvas = _.newCanvas, panelOf = _.panelOf, 
    plainErr = _.plainErr, setStat = _.setStat, toast = _.toast, valOf = _.valOf;

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
  window.LXTools.define('qr', setupQr);
})();
