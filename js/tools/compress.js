/*!
 * tools/compress.js — 01 图片压缩（工具箱·按需加载子模块）
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
    bitmapSize = _.bitmapSize, btnOf = _.btnOf, canvasToBlob = _.canvasToBlob, 
    drawToCanvas = _.drawToCanvas, esc = _.esc, fitSize = _.fitSize, fmtBytes = _.fmtBytes, 
    loadBitmap = _.loadBitmap, numOf = _.numOf, panelOf = _.panelOf, plainErr = _.plainErr, 
    renderList = _.renderList, runSeq = _.runSeq, scrollPanel = _.scrollPanel, 
    setStat = _.setStat, sizeCell = _.sizeCell, thumbOf = _.thumbOf, toast = _.toast, 
    valOf = _.valOf, zipItems = _.zipItems;

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
  window.LXTools.define('compress', setupCompress);
})();
