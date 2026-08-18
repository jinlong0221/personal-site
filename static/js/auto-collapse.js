/*
 * auto-collapse.js — 通用「板块 > 阈值条数则默认折叠」组件
 * 用法：在任意容器上加 data-ac，并通过属性声明 body / items / 阈值：
 *   data-ac                开启自动折叠
 *   data-ac-body=".lx-deck"  折叠区选择器（必填）
 *   data-ac-items=".lx-card" 计数与折叠判定的子项选择器（默认 :scope > *）
 *   data-ac-head=".lx-vol-hd" 点击折叠的头部选择器（默认容器首个子元素）
 *   data-ac-threshold="2"  超过该条数才折叠（默认 2）
 *   data-ac-default="auto|open|collapsed"  默认状态；auto=超过阈值才折叠（默认）
 *   data-ac-count="true|false"  是否显示条数徽标（默认 true）
 * 组件会在头部注入「展开/收起」按钮；点击头部或按钮切换。支持页内锚点/# 直达自动展开。
 */
(function () {
  'use strict';

  function initAutoCollapse() {
    var boards = document.querySelectorAll('[data-ac]');
    Array.prototype.forEach.call(boards, function (board) {
      var bodySel = board.getAttribute('data-ac-body');
      var body = bodySel ? board.querySelector(bodySel) : null;
      if (bodySel && !body && board.matches(bodySel)) body = board; // body 即自身（无包裹模式）
      if (!body) body = board;

      var itemSel = board.getAttribute('data-ac-items') || ':scope > *';
      var headSel = board.getAttribute('data-ac-head');
      var threshold = parseInt(board.getAttribute('data-ac-threshold') || '2', 10);
      var def = board.getAttribute('data-ac-default') || 'auto';
      var showCount = (board.getAttribute('data-ac-count') || 'true') !== 'false';

      var items = body.querySelectorAll(itemSel);
      var count = items.length;

      // 判定是否折叠
      var collapsed;
      if (def === 'open') collapsed = false;
      else if (def === 'collapsed') collapsed = true;
      else collapsed = count > threshold;

      // 自动模式且未超阈值：保持展开、不加折叠控件
      if (def === 'auto' && count <= threshold) {
        board.setAttribute('data-ac-state', 'open');
        return;
      }

      board.classList.add('lx-ac');
      body.classList.add('lx-ac-body');

      var head = null;
      if (headSel) {
        head = board.querySelector(headSel);
        if (!head && board.previousElementSibling && board.previousElementSibling.matches &&
            board.previousElementSibling.matches(headSel)) {
          head = board.previousElementSibling; // 头部为前一个兄弟节点（无包裹模式）
        }
      }
      if (!head) head = board.firstElementChild;
      if (!head) head = board;
      head.classList.add('lx-ac-head', 'lx-ac-head-click');

      var toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'lx-ac-toggle';
      toggle.setAttribute('aria-expanded', 'false');
      toggle.innerHTML =
        (showCount ? '<span class="lx-ac-count"></span>' : '') +
        '<span class="lx-ac-label"></span>' +
        '<span class="lx-ac-arrow" aria-hidden="true"></span>';

      var label = toggle.querySelector('.lx-ac-label');
      var arrow = toggle.querySelector('.lx-ac-arrow');
      var countBadge = toggle.querySelector('.lx-ac-count');

      function setState(state) {
        board.setAttribute('data-ac-state', state);
        var isOpen = state === 'open';
        toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        label.textContent = isOpen ? '收起' : '展开';
        arrow.textContent = isOpen ? '▴' : '▾';
        if (countBadge) countBadge.textContent = String(count);
      }

      head.appendChild(toggle);
      setState(collapsed ? 'collapsed' : 'open');

      function toggleState() {
        setState(board.getAttribute('data-ac-state') === 'open' ? 'collapsed' : 'open');
      }
      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        toggleState();
      });
      head.addEventListener('click', function (e) {
        if (e.target.closest('.lx-ac-toggle')) return;
        toggleState();
      });
    });

    // 页内锚点 / # 直达：自动展开目标板块
    function expandTarget(id) {
      if (!id) return;
      var el = document.getElementById(id);
      if (!el) return;
      var board = el.hasAttribute('data-ac') ? el : el.closest('[data-ac]');
      if (board) board.setAttribute('data-ac-state', 'open');
    }
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href^="#"]');
      if (!a) return;
      var href = a.getAttribute('href');
      if (href && href.length > 1) expandTarget(decodeURIComponent(href.slice(1)));
    });
    if (location.hash && location.hash.length > 1) {
      setTimeout(function () { expandTarget(decodeURIComponent(location.hash.slice(1))); }, 0);
    }
  }

  if (document.readyState !== 'loading') initAutoCollapse();
  else document.addEventListener('DOMContentLoaded', initAutoCollapse);
})();
