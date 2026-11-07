/**
 * reading-progress.js — 顶部阅读进度条（细金线）
 * 延迟加载，零依赖。监听滚动，按文档阅读百分比填充固定顶栏金线。
 * 与站点国风黑金主题一致（gold→cinnabar 渐变）。
 */
(function () {
  function init() {
    if (document.getElementById('lxReadBar')) return;
    var bar = document.createElement('div');
    bar.id = 'lxReadBar';
    bar.setAttribute('aria-hidden', 'true');
    document.body.appendChild(bar);
    var ticking = false;
    function update() {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      var top = h.scrollTop || document.body.scrollTop || 0;
      var p = max > 0 ? top / max : 0;
      if (p < 0) p = 0;
      if (p > 1) p = 1;
      bar.style.transform = 'scaleX(' + p + ')';
      ticking = false;
    }
    function onScroll() {
      if (!ticking) {
        ticking = true;
        (window.requestAnimationFrame || function (fn) { return setTimeout(fn, 16); })(update);
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    update();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
