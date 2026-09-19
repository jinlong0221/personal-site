/*!
 * tools/stitch.js — 06 长图拼接（工具箱·按需加载子模块）
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
  var bindDrop = _.bindDrop, bindOutputs = _.bindOutputs, bitmapSize = _.bitmapSize, 
    btnOf = _.btnOf, canvasToBlob = _.canvasToBlob, download = _.download, esc = _.esc, 
    extOf = _.extOf, fmtBytes = _.fmtBytes, loadBitmap = _.loadBitmap, newCanvas = _.newCanvas, 
    numOf = _.numOf, panelOf = _.panelOf, plainErr = _.plainErr, renderList = _.renderList, 
    runSeq = _.runSeq, setStat = _.setStat, thumbOf = _.thumbOf, toast = _.toast, 
    valOf = _.valOf;

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
  window.LXTools.define('stitch', setupStitch);
})();
