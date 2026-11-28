/* 新能源车销量排行榜 —— 榜单 Tab 切换 + 车型榜搜索/折叠
 *
 * 三组 Tab：
 *   第壹节 新能源厂商榜（批发 / 零售）  -> data-evtab
 *   第贰节 新能源车型榜（零售 / 批发）  -> data-evtab3
 *   第陆节 乘用车总榜  （批发 / 零售）  -> data-evtab2
 *
 * 数据已在服务端静态渲染进 HTML，这里只负责显示/隐藏与过滤，不发起任何网络请求。
 * 全部走事件委托，兼容站内 app.js 的 data-act 机制。
 *
 * 渐进增强：页面默认所有面板都可见；本脚本初始化后给 <html> 加 .tabs-ready，
 * 才隐藏非激活面板。这样即便脚本加载失败，用户也绝不会丢数据。
 */
(function () {
  'use strict';

  function bindTabs(btnSel, panelMap) {
    var btns = document.querySelectorAll(btnSel);
    if (!btns.length) return;

    function show(key) {
      Array.prototype.forEach.call(btns, function (b) {
        var on = b.getAttribute(panelMap.attr) === key;
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      Object.keys(panelMap.ids).forEach(function (k) {
        var el = document.getElementById(panelMap.ids[k]);
        if (el) el.classList.toggle('active', k === key);
      });
    }

    Array.prototype.forEach.call(btns, function (btn) {
      btn.addEventListener('click', function () {
        show(btn.getAttribute(panelMap.attr));
      });
      // 方向键 / Home / End 切换（ARIA tabs 标准交互）
      btn.addEventListener('keydown', function (e) {
        var idx = Array.prototype.indexOf.call(btns, btn);
        var n = btns.length;
        var to = -1;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') to = (idx + 1) % n;
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') to = (idx - 1 + n) % n;
        else if (e.key === 'Home') to = 0;
        else if (e.key === 'End') to = n - 1;
        if (to >= 0 && to !== idx) {
          e.preventDefault();
          var t = btns[to];
          t.focus();
          show(t.getAttribute(panelMap.attr));
        }
      });
    });
  }

  // 车型榜：实时搜索 + 默认 TOP20 折叠（无 JS 时两张表都完整显示）
  function initModel() {
    var sec = document.getElementById('sec-nev-model');
    if (!sec) return;
    var CAP = 20;
    var inp = document.getElementById('evm-search');
    var boxes = sec.querySelectorAll('.ev-model-box');

    function applyCap() {
      Array.prototype.forEach.call(boxes, function (box) {
        var tbl = box.querySelector('table');
        if (!tbl) return;
        var rows = tbl.querySelectorAll('tbody tr');
        var btn = box.querySelector('.ev-more');
        var collapsed = box.getAttribute('data-collapsed') !== 'no';
        if (rows.length > CAP) {
          if (btn) btn.hidden = false;
          Array.prototype.forEach.call(rows, function (r, i) {
            r.hidden = collapsed && i >= CAP;
          });
          if (btn) btn.textContent = collapsed ? ('展开全部 ' + rows.length + ' 条') : '收起';
        } else {
          if (btn) btn.hidden = true;
          Array.prototype.forEach.call(rows, function (r) { r.hidden = false; });
        }
      });
    }

    applyCap();
    Array.prototype.forEach.call(boxes, function (box) {
      var btn = box.querySelector('.ev-more');
      if (!btn) return;
      btn.addEventListener('click', function () {
        box.setAttribute('data-collapsed', box.getAttribute('data-collapsed') === 'no' ? 'yes' : 'no');
        applyCap();
      });
    });

    if (inp) inp.addEventListener('input', function () {
      var q = (inp.value || '').trim().toLowerCase();
      Array.prototype.forEach.call(boxes, function (box) {
        var tbl = box.querySelector('table');
        var rows = tbl ? tbl.querySelectorAll('tbody tr') : [];
        var btn = box.querySelector('.ev-more');
        if (!q) {                       // 清空搜索：恢复 TOP20 折叠
          if (btn) btn.hidden = rows.length <= CAP;
          applyCap();
          return;
        }
        if (btn) btn.hidden = true;    // 搜索态下展示全部匹配行，隐藏展开按钮
        Array.prototype.forEach.call(rows, function (r) {
          r.hidden = r.textContent.toLowerCase().indexOf(q) < 0;
        });
      });
    });
  }

  function init() {
    // 关键：先标记 JS 可用，CSS 才会隐藏非激活面板（无 JS 则全部可见）
    document.documentElement.classList.add('tabs-ready');
    bindTabs('[data-evtab]', { attr: 'data-evtab', ids: { w: 'evp-w', r: 'evp-r' } });
    bindTabs('[data-evtab3]', { attr: 'data-evtab3', ids: { r: 'evm-r', w: 'evm-w' } });
    bindTabs('[data-evtab2]', { attr: 'data-evtab2', ids: { w: 'evt-w', r: 'evt-r' } });
    initModel();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
