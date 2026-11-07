/*!
 * tools/convert.js — 02 格式转换（工具箱·按需加载子模块）
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
    drawToCanvas = _.drawToCanvas, esc = _.esc, extOf = _.extOf, fmtBytes = _.fmtBytes, 
    loadBitmap = _.loadBitmap, numOf = _.numOf, panelOf = _.panelOf, plainErr = _.plainErr, 
    renderList = _.renderList, runSeq = _.runSeq, setStat = _.setStat, sizeCell = _.sizeCell, 
    thumbOf = _.thumbOf, toast = _.toast, valOf = _.valOf, zipItems = _.zipItems;

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
  window.LXTools.define('convert', setupConvert);
})();
