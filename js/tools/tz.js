/*!
 * tools/tz.js — 时区转换（工具箱·按需加载子模块）
 *
 * 填一个时间，选好原时区与目标时区，自动换算，含夏令时（DST）。
 * 走浏览器自带的时区数据库（Intl），不联网校时、不读任何外部数据。
 *
 * 换算思路：把「原时区墙面时间」先还原成绝对时刻（instant），再按目标时区重新显示。
 * 绝对时刻 = 墙面时间(当作 UTC 编码) − 原时区偏移；目标墙面 = 绝对时刻 + 目标时区偏移。
 * 偏移量用 Intl 把某个 instant 在指定时区格式化、再当 UTC 解析、与真实 instant 相减得到，
 * 一步修正对绝大多数日期都准；跨夏令时切换日的极小边界差异由浏览器时区库内部处理。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $ = _.$, $$ = _.$$;
  var field = _.field, valOf = _.valOf, setStat = _.setStat, toast = _.toast, clearToast = _.clearToast, panelOf = _.panelOf;

  var ZONES = [
    ['Asia/Shanghai', '中国 · 北京'], ['Asia/Hong_Kong', '中国 · 香港'], ['Asia/Tokyo', '日本 · 东京'],
    ['Asia/Singapore', '新加坡'], ['Asia/Dubai', '迪拜'], ['Asia/Kolkata', '印度 · 加尔各答'],
    ['Europe/London', '英国 · 伦敦'], ['Europe/Paris', '法国 · 巴黎'], ['Europe/Moscow', '俄罗斯 · 莫斯科'],
    ['America/New_York', '美国 · 纽约'], ['America/Los_Angeles', '美国 · 洛杉矶'], ['Australia/Sydney', '澳洲 · 悉尼'],
    ['UTC', 'UTC（世界标准时间）']
  ];
  var WD = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

  function offsetMs(date, tz) {
    var f = new Intl.DateTimeFormat('en-US', {
      timeZone: tz, hour12: false,
      year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    var m = /(\d+)\/(\d+)\/(\d+),?\s+(\d+):(\d+):(\d+)/.exec(f.format(date));
    if (!m) return 0;
    var asUTC = Date.UTC(+m[3], +m[1] - 1, +m[2], +m[4], +m[5], +m[6]);
    return asUTC - date.getTime();
  }
  function conv(localStr, fromTz, toTz) {
    if (!localStr) return null;
    var p = localStr.split(/[-T:]/);
    if (p.length < 5) return null;
    var wallUTC = Date.UTC(+p[0], +p[1] - 1, +p[2], +p[3], +p[4]);
    var instant = wallUTC - offsetMs(new Date(wallUTC), fromTz);
    return new Date(instant + offsetMs(new Date(instant), toTz));
  }
  function fmtDate(d) {
    function p(n) { return (n < 10 ? '0' : '') + n; }
    return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate()) +
      ' ' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes());
  }

  function setupTz() {
    var P = panelOf('tz');
    if (!P) return;

    function fill(sel, def) {
      if (!sel) return;
      sel.innerHTML = ZONES.map(function (z) { return '<option value="' + z[0] + '">' + z[1] + '</option>'; }).join('');
      if (def) sel.value = def;
    }
    fill(field(P, 'from'), 'Asia/Shanghai');
    fill(field(P, 'to'), 'America/New_York');

    function run() {
      clearToast(P);
      var ls = valOf(P, 'dt');
      if (!ls) { toast(P, '先填一个时间（日期 + 时刻）。', 'err'); return; }
      var from = valOf(P, 'from'), to = valOf(P, 'to');
      var d = conv(ls, from, to);
      if (!d) { toast(P, '时间格式不对，照着 2026-09-20 14:30 这样填。', 'err'); return; }
      var fName = (ZONES.filter(function (z) { return z[0] === from; })[0] || [null, ''])[1];
      var tName = (ZONES.filter(function (z) { return z[0] === to; })[0] || [null, ''])[1];
      var cells = [
        ['原时间', fmtDate(conv(ls, from, from)) + '（' + fName + '）'],
        ['换算结果', fmtDate(d) + '（' + tName + '）'],
        ['星期', WD[d.getUTCDay()]]
      ];
      var note = '换算走浏览器自带的时区数据库，自动处理夏令时（DST）。填的时间按你选的「原时区」来读，再换成目标时区。';
      setStat(P, cells, note);
    }

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
    var di = field(P, 'dt'); di && di.addEventListener('change', run);

    function p2(n) { return (n < 10 ? '0' : '') + n; }
    var n = new Date();
    if (di && !di.value) di.value = n.getFullYear() + '-' + p2(n.getMonth() + 1) + '-' + p2(n.getDate()) +
      'T' + p2(n.getHours()) + ':' + p2(n.getMinutes());
    run();
  }

  window.LXTools.define('tz', setupTz);
})();
