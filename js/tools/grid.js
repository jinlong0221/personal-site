/*!
 * tools/grid.js — 13 九宫格切图（工具箱·按需加载子模块）
 *
 * 由 tools.js 框架在用户点开对应卡片时才注入执行，不参与首屏加载。
 * 与主文件同一套红线：零外部依赖、零 CDN、零网络请求，文件不离开浏览器。
 * 用到的公共函数全部经顶部解构自 window.LXTools.api 取得；
 * 不要在 IIFE 之外挂任何全局，也不要依赖别的子模块。
 *
 * 切法说明（这是本工具最容易做错的地方）：
 *   1) 等分边界用「按比例四舍五入」算出来，而不是用 Math.floor(宽/列) 当每格宽。
 *      1000 宽切 3 列时每格宽并不相等（333/334/333），用固定宽会有 1 像素的缝或溢出，
 *      边界法保证第 0 列从 0 开始、最后一列正好落到原图右边缘。
 *   2) 先切像素（源区域）、再缩放，绝不先整体缩放再切 —— 后者会因为取整把边缘的行漏掉。
 */
(function () {
  'use strict';
  var _ = (window.LXTools || {}).api;
  if (!_) return;
  var $ = _.$;
  var bindDrop = _.bindDrop, bindOutputs = _.bindOutputs, bitmapSize = _.bitmapSize,
    btnOf = _.btnOf, canvasToBlob = _.canvasToBlob, doc = _.doc, download = _.download,
    esc = _.esc, fmtBytes = _.fmtBytes, loadBitmap = _.loadBitmap, newCanvas = _.newCanvas,
    numOf = _.numOf, panelOf = _.panelOf, plainErr = _.plainErr, renderList = _.renderList,
    runSeq = _.runSeq, setStat = _.setStat, thumbOf = _.thumbOf, toast = _.toast,
    valOf = _.valOf, zipItems = _.zipItems;

  var MODES = {
    '3x3': { cols: 3, rows: 3, label: '3 × 3 九宫格' },
    '2x2': { cols: 2, rows: 2, label: '2 × 2 四宫格' },
    '1x3': { cols: 1, rows: 3, label: '上下三条' },
    '3x1': { cols: 3, rows: 1, label: '左右三条' }
  };

  var FONT = '"PingFang SC","Hiragino Sans GB","Microsoft YaHei",-apple-system,sans-serif';

  /* ---------------- 排版计算 ---------------- */

  /**
   * 算出每一格在「原图像素坐标」里的位置。
   * square=true 时先从中间裁一个最大的正方形，再等分。
   */
  function planTiles(sw, sh, cols, rows, square) {
    var sx = 0, sy = 0, w = sw, h = sh;
    if (square) {
      var side = Math.min(sw, sh);
      sx = Math.floor((sw - side) / 2);
      sy = Math.floor((sh - side) / 2);
      w = side;
      h = side;
    }
    var xs = [], ys = [], i;
    for (i = 0; i <= cols; i++) xs.push(sx + Math.round(w * i / cols));
    for (i = 0; i <= rows; i++) ys.push(sy + Math.round(h * i / rows));
    var tiles = [], r, c;
    for (r = 0; r < rows; r++) {
      for (c = 0; c < cols; c++) {
        tiles.push({
          x: xs[c], y: ys[r],
          w: xs[c + 1] - xs[c], h: ys[r + 1] - ys[r],
          idx: r * cols + c + 1, row: r, col: c
        });
      }
    }
    return { tiles: tiles, cols: cols, rows: rows, box: { x: sx, y: sy, w: w, h: h }, cropped: !!square };
  }

  /* ---------------- 角标 ---------------- */

  /** numMode: 1 = 小号圆底数字（左上角）；2 = 大号数字（右下角） */
  function drawBadge(ctx, W, H, n, big) {
    var s = Math.min(W, H);
    var txt = String(n);
    if (big) {
      var fs = Math.max(18, Math.round(s * 0.30));
      var pad = Math.round(s * 0.05) + fs * 0.12;
      ctx.font = '700 ' + fs + 'px ' + FONT;
      ctx.textAlign = 'right';
      ctx.textBaseline = 'alphabetic';
      ctx.lineJoin = 'round';
      ctx.lineWidth = Math.max(2, fs / 7);
      ctx.strokeStyle = 'rgba(0,0,0,.62)';
      ctx.strokeText(txt, W - pad, H - pad);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(txt, W - pad, H - pad);
      return;
    }
    var f2 = Math.max(12, Math.round(s * 0.085));
    var r = f2 * 1.05;
    var gap = Math.round(r * 0.55);
    var cx = gap + r, cy = gap + r;
    ctx.font = '700 ' + f2 + 'px ' + FONT;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0,0,0,.55)';
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.fillText(txt, cx, cy + f2 * 0.05);
  }

  /* ---------------- 预览 ---------------- */

  /**
   * 预览用的缩略尺寸：只缩不放，长边最多 360 像素。
   * 用画布而不是 <img src="blob:…">：页面的图片白名单里没有 blob:，
   * 浏览器会把这种图片整张挡掉（图标位置一片空白）；画布不走网络加载，天生不受影响。
   */
  function previewSize(w, h) {
    var m = Math.max(w, h);
    var k = m > 360 ? 360 / m : 1;
    return { w: Math.max(1, Math.round(w * k)), h: Math.max(1, Math.round(h * k)) };
  }

  /* ---------------- 面板 ---------------- */

  function setupGrid() {
    var P = panelOf('grid');
    if (!P) return;
    var items = [];
    var tiles = [];
    var cut = $('[data-cut]', P);
    var cutWrap = $('[data-cutwrap]', P) || cut;   // 连标题一起藏，空着的时候不占位
    var zipBtn = btnOf(P, 'zip');
    bindOutputs(P);
    var box = bindDrop(P, {
      items: items, multiple: false,
      onAdd: function () {
        dropTiles();
        items.forEach(function (it) { it.dim = ''; it.thumb = ''; it.meta = ''; });
        refresh();
        probe();
      }
    });

    function refresh() {
      renderList(P, items, {
        meta: function (it) {
          if (it.meta) return it.meta;
          return (it.dim ? it.dim + ' · ' : '') + fmtBytes(it.file.size);
        }
      });
      if (!items.length) {
        setStat(P, null);
        dropTiles();
      }
    }

    function probe() {
      if (!items.length) return;
      loadBitmap(items[0].file).then(function (b) {
        var s = bitmapSize(b);
        items[0].dim = s.w + '×' + s.h;
        items[0].thumb = items[0].thumb || thumbOf(b);
        items[0].meta = '';
        if (b.close) b.close();
        refresh();
      }).catch(function (e) {
        items[0].meta = '<span class="tl-warn">' + esc(plainErr(e, '这张图浏览器读不出来')) + '</span>';
        refresh();
      });
    }

    function dropTiles() {
      tiles.forEach(function (t) { t.cv = null; });
      tiles.length = 0;
      if (cut) cut.innerHTML = '';
      if (cutWrap) cutWrap.hidden = true;
      if (zipBtn) zipBtn.disabled = true;
    }

    function paint(m) {
      if (!cut) return;
      if (cutWrap) cutWrap.hidden = false;
      cut.style.gridTemplateColumns = 'repeat(' + m.cols + ',minmax(0,1fr))';
      cut.innerHTML = '';
      tiles.forEach(function (t, i) {
        var cell = doc.createElement('div');
        cell.className = 'tl-cutc';
        var pv = previewSize(t.w, t.h);
        var cv = doc.createElement('canvas');
        cv.className = 'tl-cutcv';
        cv.width = pv.w;
        cv.height = pv.h;
        cv.title = '第' + t.idx + '张 · ' + t.w + '×' + t.h;
        if (t.cv) {
          var g = cv.getContext('2d');
          g.imageSmoothingEnabled = true;
          g.imageSmoothingQuality = 'high';
          g.drawImage(t.cv, 0, 0, pv.w, pv.h);
        }
        var cap = doc.createElement('span');
        cap.className = 'tl-cutcap';
        cap.textContent = '第' + t.idx + '张 · ' + t.w + '×' + t.h;
        var b = doc.createElement('button');
        b.type = 'button';
        b.className = 'tl-mini';
        b.textContent = '下载';
        b.setAttribute('data-tsave', String(i));
        cell.appendChild(cv);
        cell.appendChild(cap);
        cell.appendChild(b);
        cut.appendChild(cell);
      });
    }

    if (cut) {
      cut.addEventListener('click', function (ev) {
        var el = ev.target;
        while (el && el !== cut && !el.getAttribute('data-tsave')) el = el.parentNode;
        if (!el || el === cut) return;
        var t = tiles[+el.getAttribute('data-tsave')];
        if (t) download(t.blob, t.name);
      });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选一张图片', 'err');
      var m = MODES[valOf(P, 'mode')] || MODES['3x3'];
      var square = !!valOf(P, 'square');
      var numMode = +valOf(P, 'num') || 0;
      var fmt = valOf(P, 'fmt') === 'image/png' ? 'image/png' : 'image/jpeg';
      var jpg = fmt === 'image/jpeg';
      var q = Math.min(1, Math.max(0.5, numOf(P, 'q', 92) / 100));
      var btn = btnOf(P, 'run');
      btn.disabled = true;
      dropTiles();

      var bmpRef = null;
      loadBitmap(items[0].file).then(function (bmp) {
        bmpRef = bmp;
        var s = bitmapSize(bmp);
        var plan = planTiles(s.w, s.h, m.cols, m.rows, square);
        if (plan.tiles.some(function (t) { return t.w < 2 || t.h < 2; })) {
          throw new Error('这张图切 ' + m.cols + '×' + m.rows + ' 之后每格不到 2 像素，换一张大一点的再切');
        }
        return runSeq(plan.tiles, function (t) {
          var cv = newCanvas(t.w, t.h);
          var ctx = cv.getContext('2d');
          ctx.imageSmoothingEnabled = true;
          ctx.imageSmoothingQuality = 'high';
          if (jpg) { ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, cv.width, cv.height); }
          ctx.drawImage(bmp, t.x, t.y, t.w, t.h, 0, 0, t.w, t.h);
          if (numMode) drawBadge(ctx, t.w, t.h, t.idx, numMode === 2);
          t.cv = cv;                       // 预览直接复用这张画布，省一次解码
          return canvasToBlob(cv, fmt, jpg ? q : undefined).then(function (blob) {
            if (!blob) throw new Error('浏览器没能生成第 ' + t.idx + ' 张，先换成小一点的图');
            t.blob = blob;
          });
        }).then(function () { finish(plan, m, fmt, s); });
      }).then(function () {
        if (bmpRef && bmpRef.close) bmpRef.close();
        btn.disabled = false;
      }, function (e) {
        if (bmpRef && bmpRef.close) bmpRef.close();
        btn.disabled = false;
        toast(P, plainErr(e, '切图没做成'), 'err');
      });
    });

    function finish(plan, m, fmt, s) {
      var ext = fmt === 'image/png' ? 'png' : 'jpg';
      var total = 0;
      plan.tiles.forEach(function (t) {
        t.name = '第' + t.idx + '张.' + ext;
        t.item = { file: { name: t.name, size: t.blob.size }, out: t.blob, outName: t.name };
        tiles.push(t);
        total += t.blob.size;
      });
      paint(m);
      if (zipBtn) zipBtn.disabled = false;

      var note = '顺序就是朋友圈里从左上到右下的排列，打包或逐张下载都行。';
      if (plan.cropped) {
        var cutW = Math.round((s.w - plan.box.w) / 2);
        var cutH = Math.round((s.h - plan.box.h) / 2);
        note += '<b>已按正方形从中间裁过：</b>左右各裁掉 ' + cutW + ' px、上下各裁掉 ' + cutH +
          ' px。不想要这一步就把上面的勾去掉。';
      } else {
        note += '这 ' + tiles.length + ' 张拼回去就是原图本来的比例，没有裁掉任何内容。';
      }
      if (fmt === 'image/jpeg') note += ' JPG 是有损压缩，质量调到 90 以上基本看不出差别。';
      setStat(P, [
        ['原图尺寸', s.w + ' × ' + s.h],
        ['切出', tiles.length + ' 张（' + m.label + '）'],
        ['每张尺寸', plan.tiles[0].w + ' × ' + plan.tiles[0].h],
        ['合计体积', fmtBytes(total)]
      ], note);
      toast(P, '切好了：' + tiles.length + ' 张，下面逐张下载或打成一个压缩包', 'ok');
    }

    if (zipBtn) {
      zipBtn.addEventListener('click', function () {
        if (!tiles.length) return toast(P, '先点一次「开始切图」', 'err');
        zipItems(tiles.map(function (t) { return t.item; }), '九宫格切图.zip')
          .then(function (n) { toast(P, '已把 ' + n + ' 张打成一个压缩包，开始下载', 'ok'); })
          .catch(function (e) { toast(P, plainErr(e, '打包没做成'), 'err'); });
      });
    }

    btnOf(P, 'clear').addEventListener('click', function () {
      box.clear();
      items.length = 0;
      dropTiles();
      refresh();
    });
    refresh();
  }

  window.LXTools.define('grid', setupGrid);
})();
