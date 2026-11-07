/*!
 * tools/pdf.js — 04 图片转 PDF（工具箱·按需加载子模块）
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
  var bindDrop = _.bindDrop, bindOutputs = _.bindOutputs, bitmapSize = _.bitmapSize, 
    blobToBytes = _.blobToBytes, btnOf = _.btnOf, canvasToBlob = _.canvasToBlob, 
    download = _.download, drawToCanvas = _.drawToCanvas, esc = _.esc, fmtBytes = _.fmtBytes, 
    loadBitmap = _.loadBitmap, numOf = _.numOf, panelOf = _.panelOf, plainErr = _.plainErr, 
    renderList = _.renderList, runSeq = _.runSeq, setStat = _.setStat, thumbOf = _.thumbOf, 
    toast = _.toast, valOf = _.valOf;

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
    // 对象编号：1 = Catalog，2 = Pages，之后每张图片占 3 个（页 / 内容流 / 图像 XObject），
    // 所以最大编号是 2 + 3n。这里以前写成 3 + 3n，会让 xref 多出一个指向偏移 0 的幽灵条目
    // （pypdf 会报 "wrong pointing object ... offset 0"，严格校验器也判为文件结构错误）。
    var nObj = 2 + items.length * 3;

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
  window.LXTools.define('pdf', setupPdf);
})();
