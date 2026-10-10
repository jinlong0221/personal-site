/*
 * bookmark.js — 浏览器本地收藏（纯前端，无登录、无后端）
 * 存储：localStorage['lx_bookmarks'] = [{url, title, ts}, ...]
 * 功能：
 *   1. 文章页「收藏」按钮（[data-bm-btn]）一键收藏/取消，状态随页面实时更新
 *   2. /bookmarks.html 列表页渲染（#bmList），支持单条移除 + 清空
 *   3. 导航角标（[data-bm-count]）显示已收藏数量
 * 说明：收藏仅存于当前浏览器，换设备/清缓存会丢失，符合“无后端”约束。
 */
(function () {
  'use strict';

  var KEY = 'lx_bookmarks';

  function getList() {
    try {
      var v = JSON.parse(localStorage.getItem(KEY));
      return Array.isArray(v) ? v : [];
    } catch (e) {
      return [];
    }
  }
  function save(list) {
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) {}
  }

  // 去掉标题尾部的站点品牌后缀，列表展示更干净
  function cleanTitle(t) {
    return (t || document.title || '')
      .replace(/\s*[｜|]\s*龙兄知识库\s*$/, '')
      .replace(/\s*-\s*龙兄知识库\s*$/, '')
      .trim() || '未命名页面';
  }

  // 用 pathname 作为收藏键，跨域名/子目录都稳定
  function pathKey() {
    var p = location.pathname;
    if (p === '/' || p === '') return '/index.html';
    return p;
  }

  function isMarked() {
    var k = pathKey();
    return getList().some(function (x) { return x.url === k; });
  }

  function toggle() {
    var list = getList();
    var k = pathKey();
    var i = -1;
    for (var j = 0; j < list.length; j++) { if (list[j].url === k) { i = j; break; } }
    if (i >= 0) {
      list.splice(i, 1);
    } else {
      list.unshift({ url: k, title: cleanTitle(), ts: Date.now() });
    }
    save(list);
  }

  function fmtDate(ts) {
    var d = new Date(ts);
    function p(n) { return (n < 10 ? '0' : '') + n; }
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }

  // 根据当前页面深度计算相对前缀，保证列表链接在任意目录都能正确跳转
  function relPrefix() {
    var p = location.pathname;
    if (p === '/' || p === '') return '';
    var seg = p.split('/').filter(Boolean);
    var depth = seg.length - 1;
    return depth > 0 ? new Array(depth + 1).join('../') : '';
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function refreshButtons() {
    var on = isMarked();
    var nodes = document.querySelectorAll('[data-bm-btn]');
    for (var i = 0; i < nodes.length; i++) {
      var btn = nodes[i];
      btn.classList.toggle('on', on);
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      var lbl = btn.querySelector('.bm-label');
      if (lbl) lbl.textContent = on ? '已收藏' : '收藏';
    }
  }

  function refreshBadges() {
    var n = getList().length;
    var nodes = document.querySelectorAll('[data-bm-count]');
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].textContent = n ? String(n) : '';
      nodes[i].style.display = n ? '' : 'none';
    }
  }

  function renderList() {
    var box = document.getElementById('bmList');
    if (!box) return;
    var list = getList();
    var pf = relPrefix();
    if (!list.length) {
      box.innerHTML = '<div class="bm-empty">还没有收藏任何文章。<br>在任意文章页点击「收藏」按钮，即可把文章存到这里（仅保存在本机浏览器）。</div>';
      return;
    }
    var html = '<div class="bm-grid">';
    for (var i = 0; i < list.length; i++) {
      var it = list[i];
      var url = pf + it.url.replace(/^\//, '');
      html += '<div class="bm-card">' +
        '<a class="bm-card-link" href="' + escapeHtml(url) + '">' + escapeHtml(it.title) + '</a>' +
        '<div class="bm-card-meta"><span class="bm-card-date">' + fmtDate(it.ts) + ' 收藏</span>' +
        '<button class="bm-remove" type="button" data-bm-remove="' + escapeHtml(it.url) + '" aria-label="移除收藏">移除</button></div>' +
        '</div>';
    }
    html += '</div>';
    box.innerHTML = html;
  }

  function afterChange() {
    refreshButtons();
    refreshBadges();
    renderList();
  }

  function clearAll() {
    if (!getList().length) return;
    if (window.confirm('确定清空全部收藏？此操作不可恢复（仅影响本机浏览器）。')) {
      save([]);
      afterChange();
    }
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (!(t instanceof Element)) return;

    var btn = t.closest('[data-bm-btn]');
    if (btn) { e.preventDefault(); toggle(); afterChange(); return; }

    var rm = t.closest('[data-bm-remove]');
    if (rm) {
      e.preventDefault();
      var url = rm.getAttribute('data-bm-remove');
      var list = getList().filter(function (x) { return x.url !== url; });
      save(list);
      afterChange();
      return;
    }

    if (t.closest('#bmClear')) { clearAll(); }
  });

  function init() { afterChange(); }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 暴露给书签页/调试用
  window.LXBookmark = { list: getList, render: renderList, toggle: toggle };
})();
