/**
 * ext-link.js — 站外链接统一新标签页打开（同源不拦截）
 * 延迟加载（head.html requestIdleCallback），零依赖，CSP 同源允许。
 *
 * 设计约束：
 *  - 只处理绝对 http(s) 链接；站内相对链接（含 https://longxiong.vip/... 同源绝对链）跳过，
 *    避免把「同站绝对地址」误判成外链而新开空白窗。
 *  - 已显式设 target="_blank" 的（如首页「阅读原文」）只补 rel=noopener，不重复设置。
 *  - 动态渲染内容（首页今日更新等）在空闲与延时各补跑一次，确保都覆盖到。
 */
(function () {
  function apply() {
    var here = location.hostname;
    var links = document.querySelectorAll('a[href]');
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      var href = a.getAttribute('href') || '';
      if (!/^https?:\/\//i.test(href)) continue; // 仅处理绝对 http(s)
      try {
        var u = new URL(href, location.href);
        if (u.hostname === here) continue; // 同源跳过
        if (a.target && a.target.toLowerCase() === '_blank') {
          if (!/noopener/.test(a.rel || '')) a.rel = (a.rel ? a.rel + ' ' : '') + 'noopener noreferrer';
          continue;
        }
        a.target = '_blank';
        a.rel = (a.rel ? a.rel + ' ' : '') + 'noopener noreferrer';
      } catch (e) {}
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply);
  else apply();
  // 动态内容渲染后补跑一次（首页今日更新为 fetch 注入）
  if ('requestIdleCallback' in window) requestIdleCallback(apply, { timeout: 3000 });
  else setTimeout(apply, 1200);
})();
