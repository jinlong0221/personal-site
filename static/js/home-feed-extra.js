/**
 * home-feed-extra.js — 首页「今日更新」未读标记
 * 延迟加载，零依赖。记录上次访问时间（localStorage），若聚合源生成时刻比上次访问新，
 * 则在「今日更新」小标题后标一枚「新」徽标，提示访客有新鲜内容。
 *
 * 设计约束：
 *  - generated_at 为带 +08:00 的 ISO 时间戳（build_home_feed.py 产出），可直接比较。
 *  - 首次访问（无记录）也标「新」，避免永远不提示。
 *  - 标记只加一次（判重 .lx-new-badge），不重复堆叠。
 */
(function () {
  var KEY = 'lx_last_visit';
  function mark() {
    var sec = document.getElementById('today-updates');
    if (!sec) return;
    var now = Date.now();
    var last = 0;
    try { last = parseInt(localStorage.getItem(KEY) || '0', 10) || 0; } catch (e) {}
    var CACHE = '?t=' + Math.floor(Date.now() / 600000);
    fetch('/home-feed.json' + CACHE)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        var fresh = false;
        if (d && d.generated_at) {
          var t = new Date(d.generated_at).getTime();
          if (!isNaN(t) && t > last) fresh = true;
        } else if (last === 0) {
          fresh = true;
        }
        if (fresh) {
          var sub = sec.querySelector('.lx-mod-sub');
          if (sub && !sub.querySelector('.lx-new-badge')) {
            var b = document.createElement('span');
            b.className = 'lx-new-badge';
            b.textContent = '新';
            sub.appendChild(b);
          }
        }
      })
      .catch(function () {});
    try { localStorage.setItem(KEY, String(now)); } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mark);
  else mark();
})();
