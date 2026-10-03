/*!
 * tools/unit.js — 单位换算（工具箱·按需加载子模块）
 *
 * 长度 / 重量 / 温度 / 面积 / 体积 / 速度 / 时间 / 数据存储，选好类目与单位，
 * 填个数值就出结果。全部在用户设备上按基准单位换算，不联网、不读任何外部数据。
 *
 * 因子都按「基准单位 = 1」写死：先把原单位的值乘因子转成基准单位，再除以目标单位的
 * 因子得到目标值，所以任意两个单位之间都能直接换。温度是特例，按 ℃ 做线性换算。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $ = _.$, $$ = _.$$;
  var field = _.field, valOf = _.valOf, numOf = _.numOf,
      setStat = _.setStat, toast = _.toast, clearToast = _.clearToast, panelOf = _.panelOf;

  /* 每个类目：基准单位下的因子（value × 因子 = 基准单位值）。温度另行处理。 */
  var CATS = {
    length: { name: '长度', base: 'm', units: [
      ['km', 1000], ['m', 1], ['dm', 0.1], ['cm', 0.01], ['mm', 0.001], ['µm', 1e-6],
      ['里', 500], ['海里', 1852], ['英里', 1609.344], ['码', 0.9144], ['英尺', 0.3048], ['英寸', 0.0254]
    ] },
    weight: { name: '重量', base: 'g', units: [
      ['t', 1e6], ['kg', 1000], ['g', 1], ['mg', 0.001],
      ['斤', 500], ['两', 50], ['盎司', 28.349523], ['磅', 453.59237]
    ] },
    temp: { name: '温度', special: 'temp' },
    area: { name: '面积', base: 'm²', units: [
      ['km²', 1e6], ['m²', 1], ['cm²', 1e-4], ['公顷', 10000], ['亩', 666.6667],
      ['英亩', 4046.8564], ['平方英尺', 0.092903], ['平方英里', 2589988.11]
    ] },
    volume: { name: '体积', base: 'L', units: [
      ['m³', 1000], ['L', 1], ['mL', 0.001], ['加仑(美)', 3.7854118], ['加仑(英)', 4.54609], ['杯(美)', 0.236588]
    ] },
    speed: { name: '速度', base: 'm/s', units: [
      ['m/s', 1], ['km/h', 0.2777778], ['mph', 0.44704], ['节', 0.5144444], ['ft/s', 0.3048]
    ] },
    time: { name: '时间', base: 's', units: [
      ['周', 604800], ['天', 86400], ['时', 3600], ['分', 60], ['秒', 1], ['毫秒', 0.001]
    ] },
    data: { name: '数据存储', base: 'B', units: [
      ['bit', 0.125], ['B', 1], ['KB', 1024], ['MB', 1048576], ['GB', 1073741824], ['TB', 1099511627776]
    ] }
  };

  function optsHtml(catKey) {
    var c = CATS[catKey];
    if (c.special === 'temp') {
      return '<option value="C">摄氏度 ℃</option><option value="F">华氏度 ℉</option><option value="K">开尔文 K</option>';
    }
    return c.units.map(function (u) { return '<option value="' + u[0] + '">' + u[0] + '</option>'; }).join('');
  }

  function toBase(val, unit, catKey) {
    var c = CATS[catKey];
    if (c.special === 'temp') {
      if (unit === 'C') return val;
      if (unit === 'F') return (val - 32) / 1.8;
      return val - 273.15; // K
    }
    for (var i = 0; i < c.units.length; i++) if (c.units[i][0] === unit) return val * c.units[i][1];
    return val;
  }
  function fromBase(base, unit, catKey) {
    var c = CATS[catKey];
    if (c.special === 'temp') {
      if (unit === 'C') return base;
      if (unit === 'F') return base * 1.8 + 32;
      return base + 273.15;
    }
    for (var i = 0; i < c.units.length; i++) if (c.units[i][0] === unit) return base / c.units[i][1];
    return base;
  }
  function fmt(n) {
    if (!isFinite(n)) return '—';
    var a = Math.abs(n);
    if (a !== 0 && (a >= 1e15 || a < 1e-6)) return n.toExponential(6);
    return String(Math.round(n * 1e9) / 1e9);
  }

  function setupUnit() {
    var P = panelOf('unit');
    if (!P) return;

    var sel = field(P, 'cat');
    if (sel) {
      sel.innerHTML = Object.keys(CATS).map(function (k) {
        return '<option value="' + k + '">' + CATS[k].name + '</option>';
      }).join('');
    }

    function fillUnits() {
      var catKey = valOf(P, 'cat') || 'length';
      var f = field(P, 'from'), t = field(P, 'to');
      if (!f || !t) return;
      var h = optsHtml(catKey);
      f.innerHTML = h; t.innerHTML = h;
      if (t.options.length > 1) t.selectedIndex = 1; // 默认 to 选第二个，避免 from == to
    }
    fillUnits();

    function run() {
      clearToast(P);
      var catKey = valOf(P, 'cat') || 'length';
      var v = numOf(P, 'v', NaN);
      if (!isFinite(v)) { toast(P, '先填一个要换算的数值。', 'err'); return; }
      var f = valOf(P, 'from'), t = valOf(P, 'to');
      var out = fromBase(toBase(v, f, catKey), t, catKey);
      var c = CATS[catKey];
      var cells = [['原数值', fmt(v) + ' ' + f], ['换算结果', fmt(out) + ' ' + t]];
      var note = '换算在「' + c.base + '」基准上做：先转成基准单位，再转成目标单位，任意两个单位都能直接换。' +
        (c.special === 'temp' ? '温度是特例，按 ℃ 为基准线性换算，K 与 ℃ 差 273.15。' : '');
      setStat(P, cells, note);
    }

    sel && sel.addEventListener('change', function () { fillUnits(); run(); });
    $$('[data-act]', P).forEach(function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act');
        if (act === 'swap') {
          var f = field(P, 'from'), t = field(P, 'to');
          if (f && t) { var x = f.value; f.value = t.value; t.value = x; }
          return run();
        }
        if (act === 'conv') return run();
      });
    });
    var vi = field(P, 'v'); vi && vi.addEventListener('input', run);
    var fc = field(P, 'from'); fc && fc.addEventListener('change', run);
    var tc = field(P, 'to'); tc && tc.addEventListener('change', run);
    if (vi && !vi.value) vi.value = '1';
    run();
  }

  window.LXTools.define('unit', setupUnit);
})();
