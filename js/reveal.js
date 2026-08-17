(function () {
  'use strict';

  // 首页滚动渐显：为关键区块/卡片自动注入 .reveal，IntersectionObserver 触发 .in
  var selectors = '.lx-hero, .lx-vol, .lx-mod, .lx-deck .lx-card, .upd-card, .hot-card, .sheyang-card, .lx-vital, .lx-masthead';

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
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
