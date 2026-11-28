/*!
 * tools/color.js — 08 取色与色板（工具箱·按需加载子模块）
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
  var bindDrop = _.bindDrop, bitmapSize = _.bitmapSize, btnOf = _.btnOf, 
    clearToast = _.clearToast, copyText = _.copyText, drawToCanvas = _.drawToCanvas, 
    loadBitmap = _.loadBitmap, newCanvas = _.newCanvas, panelOf = _.panelOf, 
    plainErr = _.plainErr, rgbToHex = _.rgbToHex, setStat = _.setStat, toast = _.toast;

  /* ======================================================================
     1f. 主色提取（简单版中位切分，够做配色参考）
     ====================================================================== */
  function extractPalette(bmp, count) {
    var maxSide = 160;
    var s = bitmapSize(bmp);
    var sc = Math.min(1, maxSide / Math.max(s.w, s.h));
    var c = newCanvas(s.w * sc, s.h * sc);
    var ctx = c.getContext('2d');
    ctx.drawImage(bmp, 0, 0, c.width, c.height);
    var data = ctx.getImageData(0, 0, c.width, c.height).data;

    var px = [];
    for (var i = 0; i < data.length; i += 4) {
      if (data[i + 3] < 128) continue;                       // 忽略近透明像素
      px.push([data[i], data[i + 1], data[i + 2]]);
    }
    if (!px.length) return [];

    function avg(list) {
      var r = 0, g = 0, b = 0;
      for (var i = 0; i < list.length; i++) { r += list[i][0]; g += list[i][1]; b += list[i][2]; }
      var n = list.length;
      return [Math.round(r / n), Math.round(g / n), Math.round(b / n)];
    }
    function rank(list) {
      var min = [255, 255, 255], max = [0, 0, 0];
      list.forEach(function (p) {
        for (var k = 0; k < 3; k++) {
          if (p[k] < min[k]) min[k] = p[k];
          if (p[k] > max[k]) max[k] = p[k];
        }
      });
      var ranges = [max[0] - min[0], max[1] - min[1], max[2] - min[2]];
      var ch = ranges.indexOf(Math.max(ranges[0], ranges[1], ranges[2]));
      return { ch: ch, range: ranges[ch] };
    }

    var boxes = [px];
    while (boxes.length < count) {
      var bi = -1, best = 0;
      for (var k = 0; k < boxes.length; k++) {
        if (boxes[k].length < 2) continue;
        var r = rank(boxes[k]);
        if (r.range > best) { best = r.range; bi = k; }
      }
      if (bi < 0 || best < 8) break;
      var box = boxes[bi];
      var ch = rank(box).ch;
      box.sort(function (a, b) { return a[ch] - b[ch]; });
      var mid = Math.floor(box.length / 2);
      boxes.splice(bi, 1, box.slice(0, mid), box.slice(mid));
    }

    return boxes.filter(function (b) { return b.length; })
      .map(function (b) {
        var c2 = avg(b);
        return { r: c2[0], g: c2[1], b: c2[2], hex: rgbToHex(c2[0], c2[1], c2[2]), weight: b.length };
      })
      .sort(function (a, b) { return b.weight - a.weight; })
      .slice(0, count);
  }
  /* ---------------- 08 取色与色板 ---------------- */
  function rgbToHsl(r, g, b) {
    var rr = r / 255, gg = g / 255, bb = b / 255;
    var max = Math.max(rr, gg, bb), min = Math.min(rr, gg, bb);
    var h = 0, s = 0, l = (max + min) / 2;
    var d = max - min;
    if (d > 0) {
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      if (max === rr) h = ((gg - bb) / d) % 6;
      else if (max === gg) h = (bb - rr) / d + 2;
      else h = (rr - gg) / d + 4;
      h *= 60;
      if (h < 0) h += 360;
    }
    return { h: Math.round(h), s: Math.round(s * 100), l: Math.round(l * 100) };
  }



  function setupColor() {
    var P = panelOf('color');
    if (!P) return;
    var items = [];
    var wrap = $('[data-canvas]', P);
    var picked = $('[data-picked]', P);
    var swatches = $('[data-swatches]', P);
    var curBmp = null, curCv = null;
    var box = bindDrop(P, { items: items, multiple: false, onAdd: function () { open(); } });

    function releaseBmp() {
      if (curBmp && curBmp.close) curBmp.close();
      curBmp = null;
    }

    function open() {
      var it = items[0];
      releaseBmp();
      picked.hidden = true;
      swatches.innerHTML = '';
      wrap.innerHTML = '';
      wrap.hidden = true;
      setStat(P, null);
      clearToast(P);
      if (!it) return;
      loadBitmap(it.file).then(function (bmp) {
        curBmp = bmp;
        var s = bitmapSize(bmp);
        var sc = Math.min(1, 700 / Math.max(s.w, s.h));
        curCv = drawToCanvas(bmp, Math.max(1, Math.round(s.w * sc)), Math.max(1, Math.round(s.h * sc)), null);
        curCv.title = '在图上点一下取这个点的颜色';
        curCv.addEventListener('click', onPick);
        wrap.appendChild(curCv);
        wrap.hidden = false;
        toast(P, '图片已就位（显示尺寸 ' + curCv.width + '×' + curCv.height + '）· 在图上点一下取色，' +
          '或点「提取主色板」看整张图的主色调', 'ok');
      }).catch(function (e) {
        toast(P, plainErr(e, '这张图读不出来'), 'err');
      });
    }

    function onPick(e) {
      var rect = curCv.getBoundingClientRect();
      var x = Math.round((e.clientX - rect.left) * curCv.width / rect.width);
      var y = Math.round((e.clientY - rect.top) * curCv.height / rect.height);
      x = Math.max(0, Math.min(curCv.width - 1, x));
      y = Math.max(0, Math.min(curCv.height - 1, y));
      var d;
      try { d = curCv.getContext('2d').getImageData(x, y, 1, 1).data; }
      catch (err) { return toast(P, '取色失败：这张图跨域了，浏览器不允许读它的像素', 'err'); }
      showPicked(d[0], d[1], d[2], x, y);
    }

    function showPicked(r, g, b, x, y) {
      var hex = rgbToHex(r, g, b);
      var hsl = rgbToHsl(r, g, b);
      var rgbStr = 'rgb(' + r + ', ' + g + ', ' + b + ')';
      var hslStr = 'hsl(' + hsl.h + ', ' + hsl.s + '%, ' + hsl.l + '%)';
      picked.innerHTML =
        '<div class="tl-picked-c" style="background:' + hex + '"></div>' +
        '<div class="tl-picked-t">' +
        '取样点：第 ' + (x + 1) + ' 列、第 ' + (y + 1) + ' 行（按显示尺寸）<br>' +
        'HEX <b>' + hex + '</b> · RGB <b>' + rgbStr + '</b> · HSL <b>' + hslStr + '</b>' +
        '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">' +
        '<button class="tl-mini" type="button" data-copyhex="' + hex + '">复制 HEX</button>' +
        '<button class="tl-mini" type="button" data-copyrgb="' + rgbStr + '">复制 RGB</button>' +
        '<button class="tl-mini" type="button" data-copyhsl="' + hslStr + '">复制 HSL</button>' +
        '</div></div>';
      picked.hidden = false;
      $$('[data-copyhex],[data-copyrgb],[data-copyhsl]', picked).forEach(function (btn) {
        btn.addEventListener('click', function () {
          var v = btn.getAttribute('data-copyhex') || btn.getAttribute('data-copyrgb') ||
            btn.getAttribute('data-copyhsl');
          copyText(v).then(function () { toast(P, '已复制 ' + v, 'ok'); },
            function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
        });
      });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选一张图片', 'err');
      if (!curBmp) return open();
      var pal = extractPalette(curBmp, 8);
      if (!pal.length) return toast(P, '这张图取不出颜色（可能是全透明或纯色）', 'err');
      swatches.innerHTML = pal.map(function (c, i) {
        return '<button class="tl-sw" type="button" data-hex="' + c.hex + '" ' +
          'title="点击复制 ' + c.hex + '">' +
          '<span class="tl-sw-c" style="display:block;background:' + c.hex + '"></span>' +
          '<span class="tl-sw-t">' + c.hex + (i === 0 ? '（最多）' : '') + '</span></button>';
      }).join('') +
        '<div class="tl-note" style="grid-column:1/-1">' +
        '<button class="tl-mini" type="button" data-copyall>复制全部色值</button></div>';
      $$('[data-hex]', swatches).forEach(function (b) {
        b.addEventListener('click', function () {
          var hex = b.getAttribute('data-hex');
          copyText(hex).then(function () { toast(P, '已复制 ' + hex, 'ok'); },
            function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
        });
      });
      var allBtn = $('[data-copyall]', swatches);
      if (allBtn) {
        allBtn.addEventListener('click', function () {
          var lines = pal.map(function (c) {
            var hsl = rgbToHsl(c.r, c.g, c.b);
            return c.hex + '  rgb(' + c.r + ', ' + c.g + ', ' + c.b + ')  hsl(' +
              hsl.h + ', ' + hsl.s + '%, ' + hsl.l + '%)';
          }).join('\n');
          copyText(lines).then(function () { toast(P, '已复制 ' + pal.length + ' 个色值', 'ok'); },
            function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
        });
      }
      setStat(P, [
        ['提取颜色', pal.length + ' 个'],
        ['最主色', pal[0].hex]
      ], '按面积占比从大到小排。点任意色块复制色值，做设计抄色时很方便。');
      toast(P, '主色板已提取', 'ok');
    });

    btnOf(P, 'clear').addEventListener('click', function () {
      releaseBmp();
      box.clear();
      items.length = 0;
      curCv = null;
      wrap.innerHTML = '';
      wrap.hidden = true;
      picked.hidden = true;
      picked.innerHTML = '';
      swatches.innerHTML = '';
      setStat(P, null);
      clearToast(P);
    });
  }
  window.LXTools.define('color', setupColor);
})();
