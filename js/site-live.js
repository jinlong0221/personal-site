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
 * 落点（两处，先命中先用）：
 *   ① 正文页：页尾信息块 .page-meta 里「最后更新」那一行的下面（全站 177 个手写页）。
 *   ② 首页刊头：#siteLiveMast —— 首页按设计没有 .page-meta（它自带整块「今日更新」流），
 *      所以改挂刊头那枚常驻活标记。
 *
 * 🔴 为什么不显示「热门精选 / 头图」的人工策展日期了：
 *   那两份 JSON（hot-picks.json、hero.json）的 updated 是「文件最后一次被改动的 git 日期」，
 *   而这两份清单是「每板代表作」级别的长期内容，本来就极少改 → 日期只会一天天变旧。
 *   挂在首页上，访客读到的却是「这站好久没更新了」，与实际每天三班更新完全相反。
 *   现已换成真实的发布时刻（相对时间），并且每分钟自己走。
 *
 * 降级：拿不到数据就整行不插入 / 刊头标记保持隐藏（页面照旧），不会留下空壳或 0 值。
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

  // 落点①：页尾信息块的「最后更新」那一行下面。
  // 优先 .page-meta 里的 .update-time 之后；没有 .update-time 就退到 .page-meta 末尾。
  function insertPageMeta() {
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
    return { text: p.querySelector('strong'), tip: p };
  }

  // 落点②：首页刊头的 #siteLiveMast。默认带 .is-off 不显示，摘掉它的时机放在
  // 「已经确认拿到发布时间」之后 —— 否则脚本半途失败会留一枚空壳在刊头上。
  function insertMasthead() {
    var el = document.getElementById('siteLiveMast');
    if (!el) return null;
    var b = el.querySelector('b');
    if (!b) return null;
    el.classList.remove('is-off');
    return { text: b, tip: el };
  }

  // 两处都没有（跳转壳 / 法务页）→ null，整行不出现
  function target() {
    return insertPageMeta() || insertMasthead();
  }

  function load() {
    var url = base() + 'home-feed.json?t=' + Math.floor(Date.now() / 600000); // 与 home-feed.js 同键，浏览器只下载一次
    fetch(url, { credentials: 'omit' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        var t = parseTime(d.generated_at, '') || parseTime(d.generated, '+00:00');
        if (!t) return;
        var el = target();
        if (!el || !el.text) return;
        function paint() {
          el.text.textContent = ago(Date.now() - t.getTime());
          el.tip.title = '最近一次发布：' + stamp(t) + '（北京时间）';
        }
        paint();
        setInterval(paint, 60000);                                  // 每分钟自己走
        document.addEventListener('visibilitychange', function () { // 切回标签页立即校准
          if (!document.hidden) paint();
        });
      })
      .catch(function () { /* 拿不到就整行不出现 / 标记保持隐藏，页面照旧 */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
