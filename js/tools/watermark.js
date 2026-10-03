/*!
 * tools/watermark.js — 05 批量加水印（工具箱·按需加载子模块）
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
  var baseName = _.baseName, bindDrop = _.bindDrop, bindOutputs = _.bindOutputs, 
    bitmapSize = _.bitmapSize, btnOf = _.btnOf, canvasToBlob = _.canvasToBlob, 
    drawToCanvas = _.drawToCanvas, esc = _.esc, fmtBytes = _.fmtBytes, 
    loadBitmap = _.loadBitmap, numOf = _.numOf, panelOf = _.panelOf, plainErr = _.plainErr, 
    renderList = _.renderList, runSeq = _.runSeq, setStat = _.setStat, thumbOf = _.thumbOf, 
    toast = _.toast, valOf = _.valOf, zipItems = _.zipItems;

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
  window.LXTools.define('watermark', setupWatermark);
})();
