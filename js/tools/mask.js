/*!
 * tools/mask.js — 15 图片打码（工具箱·按需加载子模块）
 *
 * 由 tools.js 框架在用户点开对应卡片时才注入执行，不参与首屏加载。
 * 与主文件同一套红线：零外部依赖、零 CDN、零网络请求，文件不离开浏览器。
 * 用到的公共函数全部经顶部解构自 window.LXTools.api 取得；
 * 不要在 IIFE 之外挂任何全局，也不要依赖别的子模块。
 *
 * 三个关键设计：
 *   1) 遮挡区域用「归一化坐标」（0～1，相对整张图存）而不是像素坐标。
 *      预览画布和导出画布尺寸不一样，归一化之后同一份数据两边都能用，
 *      马赛克方块和模糊半径再乘以各自的缩放系数，所见即所得。
 *   2) 取样一律从「原图那张画布」取，绝不从正在画的那张画布取自己 ——
 *      画布读自己各家实现的行为不一致，而且重叠的两块会互相污染。
 *   3) 拖框只在预览画布上做，改的是叠加层的虚线框（DOM），
 *      松手才重画一次画布。拖动过程中不重画像素，所以大图也不卡。
 */
(function () {
  'use strict';
  var _ = (window.LXTools || {}).api;
  if (!_) return;
  var $ = _.$;
  var baseName = _.baseName, bindDrop = _.bindDrop, bindOutputs = _.bindOutputs,
    bitmapSize = _.bitmapSize, btnOf = _.btnOf, canvasToBlob = _.canvasToBlob,
    download = _.download, esc = _.esc, fmtBytes = _.fmtBytes, loadBitmap = _.loadBitmap,
    newCanvas = _.newCanvas, numOf = _.numOf, panelOf = _.panelOf, plainErr = _.plainErr,
    renderList = _.renderList, setStat = _.setStat, thumbOf = _.thumbOf, toast = _.toast,
    valOf = _.valOf;

  var VIEW_W = 1400;      // 预览画布宽度上限（像素）
  var VIEW_H = 2600;      // 预览画布高度上限（像素）
  var FONT = '"PingFang SC","Hiragino Sans GB","Microsoft YaHei",-apple-system,sans-serif';
  var MODE_CN = { mosaic: '马赛克', blur: '高斯模糊', solid: '纯色块' };

  /** 浏览器到底支不支持 canvas 的 filter（Safari 15.4 以前不支持） */
  var blurOK = (function () {
    try {
      var c = newCanvas(4, 4);
      var ctx = c.getContext('2d');
      ctx.filter = 'blur(2px)';
      return ctx.filter === 'blur(2px)';
    } catch (e) { return false; }
  })();

  /** 预览画布的缩放系数：只缩不放（放大会把图糊掉），且宽高都不超过上限 */
  function viewScale(w, h) {
    return Math.min(1, VIEW_W / Math.max(1, w), VIEW_H / Math.max(1, h));
  }

  /**
   * 把源画布上的一块区域按「面积平均」缩到 cols × rows。
   *
   * 🔴 绝不能一步缩到位。降采样倍数一大（十几倍），浏览器不保证给你做面积平均，
   *    实测 360×174 一步缩到 26×13 退化成「点采样」：每格只剩原来某一个像素的颜色，
   *    结果马赛克就是一堆原图杂色点，而不是「一块糊成一个色」——看着像糊了，其实没糊，
   *    原图里的号码/名字仍有可能从这些残留像素里认出来。
   *    改成逐级对半缩，每一级只缩 2 倍，浏览器一定做真正的平均，最后再收到目标格数。
   */
  function shrinkBlock(src, sx, sy, sw, sh, cols, rows) {
    var w = Math.max(1, Math.round(sw));
    var h = Math.max(1, Math.round(sh));
    var cur = null, nw, nh, c, g;

    while (w > cols * 2 || h > rows * 2) {
      nw = Math.max(cols, Math.round(w / 2));
      nh = Math.max(rows, Math.round(h / 2));
      if (nw === w && nh === h) break;             // 收不动了，防死循环
      c = newCanvas(nw, nh);
      g = c.getContext('2d');
      g.imageSmoothingEnabled = true;
      g.imageSmoothingQuality = 'high';
      // 第一级直接从原图取（只缩 2 倍，不用先铺一张原尺寸的中间画布，省内存）
      if (cur) g.drawImage(cur, 0, 0, w, h, 0, 0, nw, nh);
      else g.drawImage(src, sx, sy, sw, sh, 0, 0, nw, nh);
      cur = c; w = nw; h = nh;
    }

    var out = newCanvas(cols, rows);
    g = out.getContext('2d');
    g.imageSmoothingEnabled = true;
    g.imageSmoothingQuality = 'high';
    if (cur) g.drawImage(cur, 0, 0, w, h, 0, 0, cols, rows);
    else g.drawImage(src, sx, sy, sw, sh, 0, 0, cols, rows);
    return out;
  }

  /**
   * 把一块遮挡烧进画布。
   * src/tW/tH 是取样来源与目标画布；r 是归一化矩形；k = 目标宽 / 预览宽。
   */
  function applyRect(ctx, src, tW, tH, r, opt, k) {
    var dx = Math.round(r.x * tW), dy = Math.round(r.y * tH);
    var dw = Math.round(r.w * tW), dh = Math.round(r.h * tH);
    if (dw < 2 || dh < 2) return;

    if (opt.mode === 'solid') {
      ctx.fillStyle = opt.color;
      ctx.fillRect(dx, dy, dw, dh);
      return;
    }

    // 归一到取样画布上的源矩形（取样画布可能与目标同尺寸，也可能是全分辨率原图）
    var sx = r.x * src.width, sy = r.y * src.height;
    var sw = r.w * src.width, sh = r.h * src.height;
    var sc = src.width / tW;                      // 目标像素 -> 取样像素

    if (opt.mode === 'blur' && blurOK) {
      var padT = Math.ceil(opt.radius * k * 2.5);  // 往外多画一圈，免得边缘糊不开
      var padS = padT * sc;
      ctx.save();
      ctx.beginPath();
      ctx.rect(dx, dy, dw, dh);
      ctx.clip();
      ctx.filter = 'blur(' + (opt.radius * k).toFixed(2) + 'px)';
      ctx.drawImage(src, sx - padS, sy - padS, sw + padS * 2, sh + padS * 2,
        dx - padT, dy - padT, dw + padT * 2, dh + padT * 2);
      ctx.restore();
      return;
    }

    // 马赛克：先把这块区域按面积平均收到「格子数那么多个像素」，再关掉平滑放大回去。
    // 格子数是按「预览尺度下的像素数 ÷ 格子边长」算的，而不是先算导出画布上的格子边长再相除 ——
    // 后者会因为 Math.round 的误差算出「预览 210 格、导出 212 格」这种肉眼看不出来、
    // 但确实变了样的情况。换算到预览尺度之后，两边算出来的格子数严格一样。
    var wRef = Math.max(1, dw / k), hRef = Math.max(1, dh / k);
    var cols = Math.max(1, Math.ceil(wRef / opt.block));
    var rows = Math.max(1, Math.ceil(hRef / opt.block));
    var tmp = shrinkBlock(src, sx, sy, sw, sh, cols, rows);
    ctx.save();
    ctx.beginPath();
    ctx.rect(dx, dy, dw, dh);
    ctx.clip();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(tmp, 0, 0, cols, rows, dx, dy, dw, dh);
    ctx.restore();
  }

  /** 把一组遮挡按顺序烧进画布（取样来源始终是原图，后者覆盖前者） */
  function applyAll(ctx, src, tW, tH, rects, opt, k) {
    for (var i = 0; i < rects.length; i++) applyRect(ctx, src, tW, tH, rects[i], opt, k);
  }

  function setupMask() {
    var P = panelOf('mask');
    if (!P) return;
    var items = [];
    var rects = [];
    var srcCv = null;          // 原图，全分辨率
    var drag = null;
    var viewCv = $('[data-mkcanvas]', P);
    var stage = $('[data-mkstage]', P);
    var selBox = $('[data-mksel]', P);
    var wrap = $('[data-mk]', P);
    if (!viewCv || !stage) return;
    var undoBtn = btnOf(P, 'undo'), wipeBtn = btnOf(P, 'wipe'), saveBtn = btnOf(P, 'save');
    bindOutputs(P);

    var box = bindDrop(P, {
      items: items, multiple: false,
      onAdd: function () { load(); }
    });

    // 换遮法、调格子大小/模糊强度、改颜色都要立刻重画预览。
    // 否则拖完框再去调参数，预览一动不动，看着像「调了没反应」。
    ['mode', 'block', 'radius', 'color'].forEach(function (name) {
      var el = $('[data-in="' + name + '"]', P);
      if (!el) return;
      el.addEventListener('input', function () { render(); });
      el.addEventListener('change', function () { render(); });
    });

    if (!blurOK) {
      var sel = $('[data-in="mode"]', P);
      if (sel && sel.options) {
        for (var i = 0; i < sel.options.length; i++) {
          if (sel.options[i].value === 'blur') sel.options[i].text = '高斯模糊（这个浏览器不支持，已禁用）';
        }
      }
    }

    function refresh() {
      renderList(P, items, {
        meta: function (it) {
          if (it.meta) return it.meta;
          return (it.dim ? it.dim + ' · ' : '') + fmtBytes(it.file.size);
        }
      });
    }

    function opts() {
      var mode = valOf(P, 'mode');
      if (mode !== 'blur' && mode !== 'solid') mode = 'mosaic';
      if (mode === 'blur' && !blurOK) mode = 'mosaic';
      return {
        mode: mode,
        block: Math.max(4, numOf(P, 'block', 14)),
        radius: Math.max(2, numOf(P, 'radius', 16)),
        color: valOf(P, 'color') || '#1a1a1a'
      };
    }

    function updateActs() {
      var has = !!rects.length;
      if (undoBtn) undoBtn.disabled = !has;
      if (wipeBtn) wipeBtn.disabled = !has;
      if (saveBtn) saveBtn.disabled = !srcCv || !has;
    }

    /* ---------- 载入 / 重建 ---------- */

    function load() {
      rects.length = 0;
      drag = null;
      if (selBox) selBox.hidden = true;
      srcCv = null;
      if (saveBtn) saveBtn.disabled = true;
      if (!items.length) {
        if (wrap) wrap.hidden = true;
        setStat(P, null);
        refresh();
        return;
      }
      var it = items[0];
      it.meta = '';
      loadBitmap(it.file).then(function (bmp) {
        var s = bitmapSize(bmp);
        srcCv = newCanvas(s.w, s.h);
        srcCv.getContext('2d').drawImage(bmp, 0, 0);
        it.dim = s.w + '×' + s.h;
        it.thumb = it.thumb || thumbOf(bmp);
        if (bmp.close) bmp.close();

        var sc = viewScale(s.w, s.h);
        viewCv.width = Math.max(1, Math.round(s.w * sc));
        viewCv.height = Math.max(1, Math.round(s.h * sc));
        if (wrap) wrap.hidden = false;
        refresh();
        render();
        updateActs();
        toast(P, '在下面的图上按住拖一个框，框住哪儿就遮住哪儿', 'ok');
      }).catch(function (e) {
        it.meta = '<span class="tl-warn">' + esc(plainErr(e, '这张图浏览器读不出来')) + '</span>';
        refresh();
        toast(P, plainErr(e, '这张图读不出来'), 'err');
      });
    }

    /* ---------- 画预览 ---------- */

    function render() {
      if (!srcCv || !viewCv) return;
      var vw = viewCv.width, vh = viewCv.height;
      var opt = opts();
      var ctx = viewCv.getContext('2d');
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.filter = 'none';
      ctx.clearRect(0, 0, vw, vh);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(srcCv, 0, 0, vw, vh);

      applyAll(ctx, srcCv, vw, vh, rects, opt, 1);

      // 金色虚线框和序号只是给你看位置用的，导出时不会画上去
      var lw = Math.max(2, vw * 0.0025);
      var fs = Math.max(13, Math.round(vw * 0.022));
      ctx.save();
      ctx.setLineDash([7, 5]);
      ctx.lineWidth = lw;
      ctx.lineJoin = 'round';
      ctx.strokeStyle = 'rgba(201,168,76,.95)';
      for (var i = 0; i < rects.length; i++) {
        var r = rects[i];
        ctx.strokeRect(r.x * vw, r.y * vh, r.w * vw, r.h * vh);
      }
      ctx.setLineDash([]);
      ctx.font = '700 ' + fs + 'px ' + FONT;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      for (var j = 0; j < rects.length; j++) {
        var q = rects[j];
        var cx = q.x * vw + fs * 1.05, cy = q.y * vh + fs * 1.05;
        ctx.beginPath();
        ctx.arc(cx, cy, fs * 0.8, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(201,168,76,.94)';
        ctx.fill();
        ctx.fillStyle = '#171512';
        ctx.fillText(String(j + 1), cx, cy + fs * 0.05);
      }
      ctx.restore();
      showStat();
    }

    function showStat(extra) {
      if (!srcCv) { setStat(P, null); return; }
      var opt = opts();
      var cells = [
        ['已遮住', rects.length ? rects.length + ' 块' : '还没遮'],
        ['原图尺寸', srcCv.width + ' × ' + srcCv.height],
        ['遮法', MODE_CN[opt.mode] + (opt.mode === 'mosaic' ? '（' + opt.block + ' px 一格）' :
          (opt.mode === 'blur' ? '（半径 ' + opt.radius + ' px）' : ''))]
      ];
      if (extra) cells.push(extra);
      var note = '图上的金色虚线框和序号只是给你核对位置用的，导出时不会画上去。' +
        '导出走的是原图分辨率：预览画布缩过，但遮出来的位置和大小按同样的比例换算回去，所以所见即所得。';
      if (opt.mode === 'mosaic' && opt.block < 10) {
        note += '<b>马赛克格子偏小：</b>格子和字差不多大时，原图放大是可能被认出来的。' +
          '拿不准就把格子调到 14 px 以上，或者直接用纯色块。';
      }
      setStat(P, cells, note);
    }

    /* ---------- 拖框 ---------- */

    function ptOf(ev) {
      var r = viewCv.getBoundingClientRect();
      var sx = r.width ? viewCv.width / r.width : 1;
      var sy = r.height ? viewCv.height / r.height : 1;
      return { x: (ev.clientX - r.left) * sx, y: (ev.clientY - r.top) * sy };
    }

    function dragBox() {
      var a = drag, vx = Math.min(a.x0, a.x1), vy = Math.min(a.y0, a.y1);
      return { vx: vx, vy: vy, vw: Math.abs(a.x1 - a.x0), vh: Math.abs(a.y1 - a.y0) };
    }

    function showSel() {
      if (!selBox || !stage) return;
      var b = dragBox();
      var cr = viewCv.getBoundingClientRect();
      var sr = stage.getBoundingClientRect();
      var k = cr.width / viewCv.width;
      selBox.hidden = false;
      selBox.style.left = (cr.left - sr.left + b.vx * k) + 'px';
      selBox.style.top = (cr.top - sr.top + b.vy * k) + 'px';
      selBox.style.width = (b.vw * k) + 'px';
      selBox.style.height = (b.vh * k) + 'px';
    }

    function commit() {
      var b = dragBox();
      drag = null;
      if (selBox) selBox.hidden = true;
      if (b.vw < 8 || b.vh < 8) return;      // 手滑点一下不算
      rects.push({
        x: b.vx / viewCv.width, y: b.vy / viewCv.height,
        w: b.vw / viewCv.width, h: b.vh / viewCv.height
      });
      render();
      updateActs();
    }

    if (viewCv) {
      viewCv.addEventListener('pointerdown', function (ev) {
        if (!srcCv) return;
        if (ev.button) return;
        ev.preventDefault();
        try { viewCv.setPointerCapture(ev.pointerId); } catch (e) { /* 老浏览器忽略 */ }
        var p = ptOf(ev);
        drag = { x0: p.x, y0: p.y, x1: p.x, y1: p.y, id: ev.pointerId };
        showSel();
      });
      viewCv.addEventListener('pointermove', function (ev) {
        if (!drag || ev.pointerId !== drag.id) return;
        ev.preventDefault();
        var p = ptOf(ev);
        drag.x1 = p.x;
        drag.y1 = p.y;
        showSel();
      });
      viewCv.addEventListener('pointerup', function (ev) {
        if (!drag || ev.pointerId !== drag.id) return;
        ev.preventDefault();
        commit();
      });
      viewCv.addEventListener('pointercancel', function () {
        drag = null;
        if (selBox) selBox.hidden = true;
      });
    }

    /* ---------- 三个按钮 ---------- */

    if (undoBtn) {
      undoBtn.addEventListener('click', function () {
        if (!rects.length) return;
        rects.pop();
        render();
        updateActs();
        toast(P, rects.length ? '已撤销，还剩 ' + rects.length + ' 块' : '遮挡都撤掉了', 'ok');
      });
    }
    if (wipeBtn) {
      wipeBtn.addEventListener('click', function () {
        if (!rects.length) return;
        rects.length = 0;
        render();
        updateActs();
        toast(P, '遮挡都清掉了，图还是原来那张', 'ok');
      });
    }

    if (saveBtn) {
      saveBtn.addEventListener('click', function () {
        if (!srcCv) return toast(P, '先选一张图片', 'err');
        if (!rects.length) return toast(P, '还没遮住任何地方 —— 在图上按住拖一个框出来', 'err');
        var opt = opts();
        var jpg = valOf(P, 'fmt') !== 'image/png';
        var q = Math.min(1, Math.max(0.5, numOf(P, 'q', 92) / 100));
        var exp = newCanvas(srcCv.width, srcCv.height);
        var ctx = exp.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        if (jpg) { ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, exp.width, exp.height); }
        ctx.drawImage(srcCv, 0, 0);

        var k = viewCv.width ? exp.width / viewCv.width : 1;
        applyAll(ctx, srcCv, exp.width, exp.height, rects, opt, k);

        var nm = (baseName(items[0].file.name) || '图片') + '-已打码.' + (jpg ? 'jpg' : 'png');
        saveBtn.disabled = true;
        canvasToBlob(exp, jpg ? 'image/jpeg' : 'image/png', jpg ? q : undefined).then(function (blob) {
          if (!blob) throw new Error('浏览器没能导出这张图，先换一张小一点的试试');
          download(blob, nm);
          showStat(['导出体积', fmtBytes(blob.size)]);
          toast(P, '遮好了，已开始下载 ' + nm, 'ok');
        }).catch(function (e) {
          toast(P, plainErr(e, '导出没做成'), 'err');
        }).then(function () { saveBtn.disabled = false; updateActs(); });
      });
    }

    btnOf(P, 'clear').addEventListener('click', function () {
      box.clear();
      items.length = 0;
      rects.length = 0;
      srcCv = null;
      load();
    });

    refresh();
    updateActs();
    if (wrap) wrap.hidden = true;
  }

  window.LXTools.define('mask', setupMask);
})();
