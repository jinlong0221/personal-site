/*!
 * tools/exif.js — 07 EXIF 查看与清除（工具箱·按需加载子模块）
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
  var baseName = _.baseName, bindDrop = _.bindDrop, blobToBytes = _.blobToBytes, 
    btnOf = _.btnOf, clearToast = _.clearToast, concatBytes = _.concatBytes, 
    download = _.download, esc = _.esc, extOf = _.extOf, fmtBytes = _.fmtBytes, 
    loadBitmap = _.loadBitmap, panelOf = _.panelOf, plainErr = _.plainErr, runSeq = _.runSeq, 
    scrollPanel = _.scrollPanel, setStat = _.setStat, thumbOf = _.thumbOf, toast = _.toast, 
    zipStore = _.zipStore;

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
  window.LXTools.define('exif', setupExif);
})();
