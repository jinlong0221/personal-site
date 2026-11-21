/*!
 * tools/resize.js — 03 尺寸与 DPI（工具箱·按需加载子模块）
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
  var baseName = _.baseName, bindDrop = _.bindDrop, bindOutputs = _.bindOutputs, 
    bitmapSize = _.bitmapSize, blobToBytes = _.blobToBytes, btnOf = _.btnOf, 
    canvasToBlob = _.canvasToBlob, concatBytes = _.concatBytes, crc32 = _.crc32, 
    drawToCanvas = _.drawToCanvas, esc = _.esc, field = _.field, fmtBytes = _.fmtBytes, 
    loadBitmap = _.loadBitmap, numOf = _.numOf, panelOf = _.panelOf, plainErr = _.plainErr, 
    renderList = _.renderList, runSeq = _.runSeq, setStat = _.setStat, thumbOf = _.thumbOf, 
    toast = _.toast, valOf = _.valOf, zipItems = _.zipItems;

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
  window.LXTools.define('resize', setupResize);
})();
