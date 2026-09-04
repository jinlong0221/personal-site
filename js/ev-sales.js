/* 新能源车销量排行榜 —— 榜单 Tab 切换
 *
 * 页面上有三组 Tab：
 *   第壹节 新能源厂商榜（批发 / 零售）  -> data-evtab
 *   第贰节 新能源车型榜（零售 / 批发）  -> data-evtab3
 *   第陆节 乘用车总榜  （批发 / 零售）  -> data-evtab2
 *
 * 数据已在服务端静态渲染进 HTML，这里只负责显示/隐藏，不发起任何网络请求。
 * 全部走事件委托，兼容站内 app.js 的 data-act 机制。
 */
(function () {
  'use strict';

  function bindTabs(btnSel, panelMap) {
    var btns = document.querySelectorAll(btnSel);
    if (!btns.length) return;
    Array.prototype.forEach.call(btns, function (btn) {
      btn.addEventListener('click', function () {
        var key = btn.getAttribute(panelMap.attr);
        // 按钮态
        Array.prototype.forEach.call(btns, function (b) {
          var on = b === btn;
          b.classList.toggle('active', on);
          b.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        // 面板态
        Object.keys(panelMap.ids).forEach(function (k) {
          var el = document.getElementById(panelMap.ids[k]);
          if (!el) return;
          var on = k === key;
          el.classList.toggle('active', on);
          if (on) { el.removeAttribute('hidden'); } else { el.setAttribute('hidden', ''); }
        });
      });
    });
  }

  function init() {
    bindTabs('[data-evtab]', { attr: 'data-evtab', ids: { w: 'evp-w', r: 'evp-r' } });
    bindTabs('[data-evtab3]', { attr: 'data-evtab3', ids: { r: 'evm-r', w: 'evm-w' } });
    bindTabs('[data-evtab2]', { attr: 'data-evtab2', ids: { w: 'evt-w', r: 'evt-r' } });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
