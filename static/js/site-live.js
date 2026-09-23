/**
 * site-live.js — 「本站更新于 47 分钟前」这一行会自己走
 *
 * 为什么用 home-feed.json：
 *   它是全站唯一「小体积 + 分钟级时间戳 + CI 每次构建都重写」的数据文件（1.4 KB）。
 *   changelog.json / changelog-feed.json 虽然时间更精确，但前者 512 KB、后者 880 KB，
 *   每页拉它们不可接受。
 *
 * 时区（🔴 踩过）：
 *   CI 跑在 UTC 容器里，build_home_feed.py 早期用 datetime.now() 写出的 generated
 *   是 UTC 值——线上因此一直显示差 8 小时的时间（实测：构建于北京 10:20，
 *   文件里写的是 02:20）。现已在生成器里补了带 +08:00 偏移的 generated_at，
 *   本脚本优先用它；仅当它缺失时才回退读 generated，并按 UTC 解释（这正是 CI 的行为）。
 *
 * 降级：拿不到数据就整行不插入（页面照旧），不会留下空壳或 0 值。
 */
(function () {
  'use strict';

  // 与 updates.js 同一套取基址的办法：从自己的 script src 反推站点根
  function base() {
    var list = document.querySelectorAll('script[src]');
    for (var i = 0; i < list.length; i++) {
      var m = list[i].src.match(/(.*\/)js\/[^/]+\.js/);
      if (m) return m[1];
    }
    return '/';
  }

  // 'YYYY-MM-DD HH:MM' / ISO8601 → Date；无时区信息时按参数 tz 解释
  function parseTime(v, tz) {
    if (v == null) return null;
    var s = String(v).trim();
    if (!s) return null;
    var iso = s.replace(' ', 'T');
    if (!/([zZ]|[+-]\d{2}:?\d{2})$/.test(iso)) iso += tz;
    var d = new Date(iso);
    return isNaN(d.getTime()) ? null : d;
  }

  function ago(ms) {
    var sec = Math.floor(ms / 1000);
    if (sec < 90) return '刚刚';                      // 含轻微时钟偏差导致的负数
    var min = Math.floor(sec / 60);
    if (min < 60) return min + ' 分钟前';
    var hr = Math.floor(min / 60);
    if (hr < 24) return hr + ' 小时前';
    var day = Math.floor(hr / 24);
    if (day === 1) return '昨天';
    if (day < 30) return day + ' 天前';
    var mon = Math.floor(day / 30);
    if (mon < 12) return mon + ' 个月前';
    return Math.floor(mon / 12) + ' 年前';
  }

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function stamp(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
           ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  // 落点：页尾信息块的「最后更新」那一行下面。
  // 优先 .page-meta 里的 .update-time 之后；没有 .update-time 就退到 .page-meta 末尾。
  // 两处都没有（跳转壳 / 法务页）就返回 null，整行不出现。
  function insert() {
    var meta = document.querySelector('.page-meta');
    if (!meta) return null;
    var ut = meta.querySelector('.update-time');
    var p = document.createElement('p');
    p.className = 'ref-note site-live';
    p.innerHTML = '本站更新于 <strong></strong> · <a>更新记录</a>';
    var a = p.querySelector('a');
    a.href = base() + 'changelog.html';
    a.title = '站点的更新日志（永久规则：全站任何改动都会记在里面）';
    if (ut && ut.nextSibling) meta.insertBefore(p, ut.nextSibling);
    else meta.appendChild(p);
    return p;
  }

  function load() {
    var url = base() + 'home-feed.json?v=' + Date.now();
    fetch(url, { credentials: 'omit' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        var t = parseTime(d.generated_at, '') || parseTime(d.generated, '+00:00');
        if (!t) return;
        var el = insert();
        if (!el) return;
        var strong = el.querySelector('strong');
        function paint() {
          strong.textContent = ago(Date.now() - t.getTime());
          el.title = '最近一次发布：' + stamp(t) + '（北京时间）';
        }
        paint();
        setInterval(paint, 60000);                                  // 每分钟自己走
        document.addEventListener('visibilitychange', function () { // 切回标签页立即校准
          if (!document.hidden) paint();
        });
      })
      .catch(function () { /* 拿不到就整行不出现，页面照旧 */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
