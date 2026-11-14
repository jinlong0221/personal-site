/* 射阳气象页 · 标签页切换 + 锚点直达
 * 纯 DOM 切换，无第三方依赖。无 JS 时默认显示第一个标签（.wh-panel.active 已在 HTML 写好）。
 */
(function () {
  'use strict';
  var TABS = ['sheyang', 'xintan', 'typhoon', 'solar'];

  function activate(name, record) {
    var ok = TABS.indexOf(name) >= 0;
    if (!ok) name = 'sheyang';
    var tabs = document.querySelectorAll('.wh-tab');
    var panels = document.querySelectorAll('.wh-panel');
    for (var i = 0; i < tabs.length; i++) {
      var on = tabs[i].getAttribute('data-tab') === name;
      tabs[i].classList.toggle('active', on);
      tabs[i].setAttribute('aria-selected', on ? 'true' : 'false');
    }
    for (var j = 0; j < panels.length; j++) {
      panels[j].classList.toggle('active', panels[j].getAttribute('data-panel') === name);
    }
    if (record !== false) {
      try { history.replaceState(null, '', '#sec-' + name); } catch (e) {}
    }
  }

  function fromHash() {
    var h = (location.hash || '').replace(/^#sec-/, '');
    activate(h || 'sheyang', false);
  }

  function bind() {
    var tabs = document.querySelectorAll('.wh-tab');
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener('click', function () {
        activate(this.getAttribute('data-tab'), true);
      });
    }
    fromHash();
    window.addEventListener('hashchange', fromHash);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
