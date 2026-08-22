/*
 * quick-toc.js — 全站悬浮固定栏目目录（纯前端）
 * 渲染挂载点：页面内的 <div id="quickToc"></div>
 * 行为：右下角固定悬浮按钮(FAB)，点击展开栏目面板，可随时跳转任意栏目；
 *       面板底部提供「我的收藏 / RSS 订阅」入口。
 * 链接前缀根据当前页面深度自动计算，子目录页面也能正确跳转。
 */
(function () {
  'use strict';

  var COLUMNS = [
    {
      title: '核心栏目',
      items: [
        ['沉香鉴别', 'herbs/chenxiang.html'],
        ['中药材', 'herbs.html'],
        ['养生茶', 'health-tea.html'],
        ['文玩手串', 'bracelet.html'],
        ['特斯拉', 'tesla.html'],
        ['苹果新品', 'apple.html'],
        ['漫威宇宙', 'marvel.html'],
        ['农田气象', 'xintan-weather.html'],
        ['紫砂艺术', 'zisha.html'],
        ['游戏主机', 'console.html']
      ]
    },
    {
      title: '更多栏目',
      items: [
        ['家庭旅行', 'travel.html'],
        ['标签聚合', 'tags.html'],
        ['ChinaJoy', 'chinajoy.html'],
        ['光辉电力', 'guanghui.html'],
        ['高考查分', 'gaokao.html'],
        ['踩坑记', 'pitfalls.html'],
        ['台风监测', 'typhoon.html'],
        ['游戏库', 'games.html'],
        ['站点状态', 'status-history.html'],
        ['关于本站', 'about.html']
      ]
    }
  ];

  var mount = document.getElementById('quickToc');
  if (!mount) return;

  function prefix() {
    var p = location.pathname;
    if (p === '/' || p === '') return '';
    var seg = p.split('/').filter(Boolean);
    var depth = seg.length - 1;
    return depth > 0 ? new Array(depth + 1).join('../') : '';
  }

  function build() {
    var pf = prefix();
    var html = '';
    html += '<button class="qt-fab" id="qtFab" type="button" aria-label="打开栏目目录" aria-expanded="false">';
    html += '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">';
    html += '<path d="M4 6h13M4 12h13M4 18h13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>';
    html += '<circle cx="8.5" cy="6" r="1.7" fill="currentColor"/>';
    html += '<circle cx="8.5" cy="12" r="1.7" fill="currentColor"/>';
    html += '<circle cx="8.5" cy="18" r="1.7" fill="currentColor"/>';
    html += '</svg></button>';
    html += '<div class="qt-panel" id="qtPanel" role="dialog" aria-label="栏目目录" hidden>';
    html += '<div class="qt-head"><span class="qt-title">栏目目录</span>';
    html += '<button class="qt-close" id="qtClose" type="button" aria-label="关闭目录">×</button></div>';
    html += '<div class="qt-body">';
    for (var g = 0; g < COLUMNS.length; g++) {
      var grp = COLUMNS[g];
      html += '<div class="qt-group"><div class="qt-group-title">' + grp.title + '</div><div class="qt-items">';
      for (var i = 0; i < grp.items.length; i++) {
        html += '<a class="qt-item" href="' + pf + grp.items[i][1] + '">' + grp.items[i][0] + '</a>';
      }
      html += '</div></div>';
    }
    html += '</div>';
    html += '<div class="qt-foot">';
    html += '<a class="qt-foot-link" href="' + pf + 'bookmarks.html">★ 我的收藏</a>';
    html += '<a class="qt-foot-link" href="' + pf + 'rss.xml">📰 RSS 订阅</a>';
    html += '</div>';
    html += '</div>';
    mount.innerHTML = html;
  }

  build();

  var fab = document.getElementById('qtFab');
  var panel = document.getElementById('qtPanel');

  function onKey(e) { if (e.key === 'Escape') closePanel(); }
  function openPanel() {
    panel.hidden = false;
    fab.setAttribute('aria-expanded', 'true');
    document.addEventListener('keydown', onKey);
  }
  function closePanel() {
    panel.hidden = true;
    fab.setAttribute('aria-expanded', 'false');
    document.removeEventListener('keydown', onKey);
  }

  fab.addEventListener('click', function () {
    if (panel.hidden) openPanel(); else closePanel();
  });
  document.getElementById('qtClose').addEventListener('click', closePanel);
  document.addEventListener('click', function (e) {
    if (panel.hidden) return;
    var t = e.target;
    if (!(t instanceof Element)) return;
    if (panel.contains(t) || fab.contains(t)) return;
    closePanel();
  });
})();
