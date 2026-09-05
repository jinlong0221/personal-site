(function () {
  'use strict';

  // 首页滚动渐显：为关键区块/卡片自动注入 .reveal，IntersectionObserver 触发 .in
  // 注意：.lx-hero 不在观察列表——首屏 hero 必须无条件可见，绝不依赖本脚本
  // （2026-08-19：hero 曾显式带 reveal，脚本失效时整块保持 opacity:0，露出页面背景空洞）
  var selectors = '.lx-vol, .lx-mod, .lx-deck .lx-card, .upd-card, .hot-card, .sheyang-card, .lx-vital, .lx-masthead';

  function init() {
    var nodes = document.querySelectorAll(selectors);
    nodes.forEach(function (el) { el.classList.add('reveal'); });

    if (!('IntersectionObserver' in window)) {
      nodes.forEach(function (el) { el.classList.add('in'); });
      return;
    }

    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          obs.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -50px 0px', threshold: 0.1 });

    nodes.forEach(function (el) { obs.observe(el); });

    // 兜底：页面 load 后 1s，已进入视口却仍未显形的元素强制加 .in
    // 防 IO 回调异常/竞争导致内容永久隐藏（视觉退化为直接可见，绝不留空洞）
    function forceInView() {
      nodes.forEach(function (el) {
        if (el.classList.contains('in')) return;
        var r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) el.classList.add('in');
      });
    }
    if (document.readyState === 'complete') {
      setTimeout(forceInView, 1000);
    } else {
      window.addEventListener('load', function () { setTimeout(forceInView, 1000); });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
