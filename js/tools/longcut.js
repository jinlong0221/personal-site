/*!
 * tools/longcut.js — 14 长图切段（工具箱·按需加载子模块）
 *
 * 由 tools.js 框架在用户点开对应卡片时才注入执行，不参与首屏加载。
 * 与主文件同一套红线：零外部依赖、零 CDN、零网络请求，文件不离开浏览器。
 * 用到的公共函数全部经顶部解构自 window.LXTools.api 取得；
 * 不要在 IIFE 之外挂任何全局，也不要依赖别的子模块。
 *
 * 切法说明：
 *   1)「按每段的高度切」不是简单地一段段切到剩下的不足为止 —— 那样最后一段可能只剩
 *      二三十像素，细得像根线。这里改成先算「要几段」= Math.ceil(总高 / 每段上限)，
 *      再把这 N 段尽量均分。这样每段都不超过上限，也不会出现孤零零的一条。
 *   2) 先按原图像素切、再整体缩放，绝不先把整张图缩小再切 —— 缩完再切会因为取整
 *      把边缘的行丢掉，几张拼回去能看出接缝。
 */
(function () {
  'use strict';
  var _ = (window.LXTools || {}).api;
  if (!_) return;
  var $ = _.$;
  var baseName = _.baseName, bindDrop = _.bindDrop, bindOutputs = _.bindOutputs,
    bitmapSize = _.bitmapSize, btnOf = _.btnOf, canvasToBlob = _.canvasToBlob,
    download = _.download, esc = _.esc, fmtBytes = _.fmtBytes,
    loadBitmap = _.loadBitmap, newCanvas = _.newCanvas, numOf = _.numOf, panelOf = _.panelOf,
    plainErr = _.plainErr, renderList = _.renderList, runSeq = _.runSeq, setStat = _.setStat,
    thumbOf = _.thumbOf, toast = _.toast, valOf = _.valOf, zipItems = _.zipItems;

  var MAX_SEGS = 200;          // 单张图最多切多少段，防呆
  var MIN_PER_H = 200;         // 每段高度下限（像素）

  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  /**
   * 返回 [{ y, h }]，按原图像素坐标，覆盖 0..H 且不重叠、不留缝。
   * mode='h'：perH 是「每段最多多高」；mode='n'：n 是要切成几段。
   */
  function segRanges(H, mode, perH, n) {
    var count, i, ys = [], out = [];
    if (mode === 'n') {
      count = Math.max(2, Math.min(MAX_SEGS, Math.round(n)));
      if (count > H) count = H;
    } else {
      perH = Math.max(MIN_PER_H, Math.round(perH));
      count = Math.max(1, Math.ceil(H / perH));
      if (count > MAX_SEGS) count = MAX_SEGS;
    }
    for (i = 0; i <= count; i++) ys.push(Math.round(H * i / count));
    for (i = 0; i < count; i++) {
      if (ys[i + 1] - ys[i] > 0) out.push({ y: ys[i], h: ys[i + 1] - ys[i] });
    }
    return out;
  }

  /** 段的列表缩略图：把该段缩小到 76 px 以内，高宽比再夸张也塞得下 */
  function segThumb(bmp, y, h, w) {
    var sc = Math.min(1, 76 / Math.max(1, Math.max(w, h)));
    var c = newCanvas(Math.max(1, Math.round(w * sc)), Math.max(1, Math.round(h * sc)));
    var ctx = c.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(bmp, 0, y, w, h, 0, 0, c.width, c.height);
    try { return c.toDataURL('image/jpeg', 0.7); } catch (e) { return ''; }
  }

  function setupLongcut() {
    var P = panelOf('longcut');
    if (!P) return;
    var items = [];
    var segs = [];
    var segList = $('[data-segs]', P);
    var segWrap = $('[data-segswrap]', P) || segList;
    var zipBtn = btnOf(P, 'zip');
    bindOutputs(P);
    var box = bindDrop(P, {
      items: items, multiple: true,
      onAdd: function () { dropSegs(); refresh(); probe(); }
    });

    function refresh() {
      renderList(P, items, {
        reorder: true,
        onChange: function () { dropSegs(); refresh(); },
        meta: function (it) {
          if (it.meta) return it.meta;
          return (it.dim ? it.dim + ' · ' : '') + fmtBytes(it.file.size);
        }
      });
      if (!items.length) { setStat(P, null); dropSegs(); }
    }

    /** 逐张量一下尺寸（长图高度是选参数的关键，列表里得先看得见） */
    function probe() {
      runSeq(items, function (it) {
        if (it.dim || it.meta) return null;
        return loadBitmap(it.file).then(function (b) {
          var s = bitmapSize(b);
          it.dim = s.w + '×' + s.h;
          it.thumb = it.thumb || thumbOf(b);
          if (b.close) b.close();
        }).catch(function (e) {
          it.meta = '<span class="tl-warn">' + esc(plainErr(e, '这张图浏览器读不出来')) + '</span>';
        });
      }).then(refresh, refresh);
    }

    function dropSegs() {
      segs.length = 0;
      if (segList) segList.innerHTML = '';
      if (segWrap) segWrap.hidden = true;
      if (zipBtn) zipBtn.disabled = true;
    }

    function paintSegs() {
      if (!segList) return;
      if (segWrap) segWrap.hidden = false;
      var html = '';
      segs.forEach(function (s, i) {
        html += '<div class="tl-cutrow">' +
          '<img class="tl-cutth" src="' + s.thumb + '" alt="">' +
          '<span class="tl-cutnm" title="' + esc(s.name) + '">' + esc(s.name) + '</span>' +
          '<span class="tl-cutsz">' + s.w + '×' + s.h + ' · ' + fmtBytes(s.blob.size) + '</span>' +
          '<button class="tl-mini" type="button" data-ssave="' + i + '">下载</button>' +
          '</div>';
      });
      segList.innerHTML = html;
    }

    if (segList) {
      segList.addEventListener('click', function (ev) {
        var el = ev.target;
        while (el && el !== segList && !el.getAttribute('data-ssave')) el = el.parentNode;
        if (!el || el === segList) return;
        var s = segs[+el.getAttribute('data-ssave')];
        if (s) download(s.blob, s.name);
      });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选一张（或多张）长图', 'err');
      var mode = valOf(P, 'mode') === 'n' ? 'n' : 'h';
      var perH = Math.round(numOf(P, 'h', 2000));
      var want = Math.round(numOf(P, 'n', 3));
      var fmt = valOf(P, 'fmt') === 'image/png' ? 'image/png' : 'image/jpeg';
      var jpg = fmt === 'image/jpeg';
      var q = Math.min(1, Math.max(0.5, numOf(P, 'q', 92) / 100));
      var wmax = Math.max(0, Math.round(numOf(P, 'wmax', 0)));
      var btn = btnOf(P, 'run');
      btn.disabled = true;
      dropSegs();

      var skipped = [];
      var plan = [];
      runSeq(items, function (it) {
        var bmpRef = null;
        return loadBitmap(it.file).then(function (bmp) {
          bmpRef = bmp;
          var s = bitmapSize(bmp);
          it.dim = s.w + '×' + s.h;
          var k = (wmax > 0 && s.w > wmax) ? wmax / s.w : 1;
          var ranges = segRanges(s.h, mode, perH, want);
          var base = baseName(it.file.name) || '长图';
          var ext = jpg ? 'jpg' : 'png';
          plan.push({ name: it.file.name, count: ranges.length, h: s.h });
          return runSeq(ranges, function (rg, idx) {
            var cvW = Math.max(1, Math.round(s.w * k));
            var cvH = Math.max(1, Math.round(rg.h * k));
            var cv = newCanvas(cvW, cvH);
            var ctx = cv.getContext('2d');
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';
            if (jpg) { ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, cvW, cvH); }
            ctx.drawImage(bmp, 0, rg.y, s.w, rg.h, 0, 0, cvW, cvH);
            return canvasToBlob(cv, fmt, jpg ? q : undefined).then(function (blob) {
              if (!blob) throw new Error('浏览器没能生成「' + base + '」的第 ' + (idx + 1) + ' 段');
              var nm = base + '-' + pad2(idx + 1) + '.' + ext;
              segs.push({
                name: nm, blob: blob, w: cvW, h: cvH,
                thumb: segThumb(bmp, rg.y, rg.h, s.w)
              });
            });
          });
        }).then(function () {
          if (bmpRef && bmpRef.close) bmpRef.close();
        }, function (e) {
          if (bmpRef && bmpRef.close) bmpRef.close();
          skipped.push(it.file.name + '：' + plainErr(e, '处理失败'));
        });
      }).then(function () {
        btn.disabled = false;
        refresh();
        if (!segs.length) {
          return toast(P, skipped.length ? skipped[0] : '一段都没切出来，换个文件再试', 'err');
        }
        paintSegs();
        if (zipBtn) zipBtn.disabled = false;
        var total = segs.reduce(function (a, s) { return a + s.blob.size; }, 0);
        var first = segs[0];
        var nSrc = items.length;
        var note = '每段用的是' + (wmax > 0 ? '按你设的宽度上限缩放后的' : '原图') +
          '像素尺寸，切缝落在整像素上，几张拼回去不会有接缝。';
        if (mode === 'h') {
          note += '按「每段不超过 ' + Math.max(MIN_PER_H, Math.round(numOf(P, 'h', 2000))) + ' px 高」自动分段的实际结果：' +
            plan.map(function (p) { return esc(p.name) + ' 切成 ' + p.count + ' 段'; }).join('、') +
            '。这里是先算要几段再均分，所以最后一段不会剩成一条细线。';
        } else {
          note += '每张图都按你填的段数平均切，段与段的高度最多差 1 像素。';
        }
        if (skipped.length) note += '<b>有 ' + skipped.length + ' 个文件没处理成功：</b>' + esc(skipped.join('；'));
        setStat(P, [
          ['处理图片', nSrc + ' 张'],
          ['切出', segs.length + ' 段'],
          ['每段尺寸', first.w + ' × ' + first.h],
          ['合计体积', fmtBytes(total)]
        ], note);
        toast(P, '切好了：共 ' + segs.length + ' 段，下面逐段下载或打成一个压缩包', 'ok');
      });
    });

    if (zipBtn) {
      zipBtn.addEventListener('click', function () {
        if (!segs.length) return toast(P, '先点一次「开始切段」', 'err');
        zipItems(segs.map(function (s) {
          return { file: { name: s.name, size: s.blob.size }, out: s.blob, outName: s.name };
        }), '长图切段.zip')
          .then(function (n) { toast(P, '已把 ' + n + ' 段打成一个压缩包，开始下载', 'ok'); })
          .catch(function (e) { toast(P, plainErr(e, '打包没做成'), 'err'); });
      });
    }

    btnOf(P, 'clear').addEventListener('click', function () {
      box.clear();
      items.length = 0;
      dropSegs();
      refresh();
    });
    refresh();
  }

  window.LXTools.define('longcut', setupLongcut);
})();
