/*!
 * tools/ts.js — 时间戳转换（工具箱·按需加载子模块）
 *
 * 时间戳 ↔ 日期互转：一串数字（秒或毫秒）换成人能读的时间，或反过来。
 * 全部用用户设备上的 Date 与本地时区算，不联网校时、不读任何外部数据。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $ = _.$, $$ = _.$$;
  var field = _.field, valOf = _.valOf, numOf = _.numOf, setStat = _.setStat, toast = _.toast, clearToast = _.clearToast, panelOf = _.panelOf;
  var WD = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

  function p2(n) { return (n < 10 ? '0' : '') + n; }

  function setupTs() {
    var P = panelOf('ts');
    if (!P) return;

    function runFwd() {
      clearToast(P);
      var ts = Math.floor(numOf(P, 'ts', NaN));
      if (!isFinite(ts)) { toast(P, '先填一个时间戳（一串数字）。', 'err'); return; }
      var unit = valOf(P, 'unit') === 'ms' ? 1 : 1000;
      var d = new Date(ts * unit);
      if (isNaN(d.getTime())) { toast(P, '这个时间戳超出范围了。', 'err'); return; }
      var cells = [
        ['本地时间', d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()) +
          ' ' + p2(d.getHours()) + ':' + p2(d.getMinutes()) + ':' + p2(d.getSeconds())],
        ['星期', WD[d.getDay()]],
        ['UTC', d.toISOString().replace('T', ' ').slice(0, 19)],
        ['毫秒时间戳', String(d.getTime())]
      ];
      var note = '你选了「' + (unit === 1 ? '毫秒' : '秒') + '」：秒级时间戳 ×1000 才是毫秒。本地时间按你设备的时区显示。';
      setStat(P, cells, note);
    }
    function runBack() {
      clearToast(P);
      var ls = valOf(P, 'dt');
      if (!ls) { toast(P, '先填一个日期时间。', 'err'); return; }
      var d = new Date(ls);
      if (isNaN(d.getTime())) { toast(P, '日期格式不对，照着 2026-09-20 14:30 这样填。', 'err'); return; }
      var cells = [
        ['秒级时间戳', String(Math.floor(d.getTime() / 1000))],
        ['毫秒时间戳', String(d.getTime())],
        ['UTC', d.toISOString().replace('T', ' ').slice(0, 19)]
      ];
      setStat(P, cells, '用 datetime-local 填的时间，按你设备时区转成时间戳。');
    }

    $$('[data-act]', P).forEach(function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act');
        if (act === 'fwd') return runFwd();
        if (act === 'back') return runBack();
      });
    });
    var tsi = field(P, 'ts'); tsi && tsi.addEventListener('input', runFwd);
    var uni = field(P, 'unit'); uni && uni.addEventListener('change', runFwd);
    var di = field(P, 'dt'); di && di.addEventListener('change', runBack);

    function p2b(n) { return (n < 10 ? '0' : '') + n; }
    var n = new Date();
    if (di && !di.value) di.value = n.getFullYear() + '-' + p2b(n.getMonth() + 1) + '-' + p2b(n.getDate()) +
      'T' + p2b(n.getHours()) + ':' + p2b(n.getMinutes());
    if (tsi && !tsi.value) tsi.value = String(Math.floor(n.getTime() / 1000));
    runFwd();
  }

  window.LXTools.define('ts', setupTs);
})();
