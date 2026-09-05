/**
 * home-feed.js — 首页「今日更新」+「热门精选」渲染
 *
 * 今日更新：聚合各板块最新新闻（/home-feed.json，由 scripts/build_home_feed.py 在部署前生成，
 *           CI 每次构建都会基于最新新闻重算，确保随自动化每天三班刷新而自动保鲜）。
 * 热门精选：编辑精选招牌专题（/hot-picks.json，均为仓库内真实封面图，严禁 AI 生成图）。
 *
 * 设计约束：
 *  - 首页直接读取静态 JSON，不并发拉 12 个 news 文件，降低请求数。
 *  - 10 分钟缓存窗口（?t=），避免 CDN/浏览器长期陈旧，又不过度频繁请求。
 *  - 任何加载失败均给出温和降级文案，不白屏。
 */
(function () {
  var CACHE = '?t=' + Math.floor(Date.now() / 600000); // 10 分钟窗口

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function renderToday(items) {
    var grid = document.getElementById('updGrid');
    if (!grid) return;
    if (!items || !items.length) {
      grid.innerHTML = '<div class="upd-card" style="grid-column:1/-1"><div class="upd-sum">各板块今日暂未抓取到新动态，自动化会在每天 08:00 / 14:00 / 21:00 自动补新。</div></div>';
      return;
    }
    grid.innerHTML = items.map(function (it) {
      var link = it.url
        ? '<a class="upd-link" href="' + esc(it.url) + '" target="_blank" rel="noopener">阅读原文 →</a>'
        : '';
      return '<div class="upd-card" tabindex="0">' +
        '<div class="upd-meta"><span class="upd-board">' + esc(it.board) + '</span>' +
        '<span class="upd-date">' + esc(it.date) + '</span></div>' +
        '<div class="upd-sum">' + esc(it.content) + '</div>' + link +
        '</div>';
    }).join('');
  }

  function renderPicks(items) {
    var grid = document.getElementById('hotGrid');
    if (!grid) return;
    if (!items || !items.length) {
      grid.innerHTML = '<article class="hot-card" style="grid-column:1/-1"><div class="hot-body"><div class="hot-title">精选筹备中</div><div class="hot-desc">编辑精选招牌专题即将上线。</div></div></article>';
      return;
    }
    grid.innerHTML = items.map(function (it) {
      var img = it.img
        ? '<img src="' + esc(it.img) + '" alt="' + esc(it.title) + '" loading="lazy" width="320" height="180">'
        : '';
      var tag = it.board
        ? '<span class="hot-pick-tag">编辑推荐 · ' + esc(it.board) + '</span>'
        : '<span class="hot-pick-tag">编辑推荐</span>';
      return '<article class="hot-card">' +
        '<a class="hot-thumb" href="' + esc(it.url) + '" aria-label="' + esc(it.title) + '">' + img + '</a>' +
        '<div class="hot-body">' +
        '<div class="hot-title"><a href="' + esc(it.url) + '">' + esc(it.title) + '</a></div>' +
        '<div class="hot-desc">' + esc(it.desc) + '</div>' + tag +
        '</div></article>';
    }).join('');
  }

  function loadJSON(url, ok) {
    fetch(url + CACHE)
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (d) { ok(d && d.items ? d.items : d); })
      .catch(function (e) { console.log('[home-feed] 加载失败:', url, e); });
  }

  function init() {
    loadJSON('/home-feed.json', renderToday);
    loadJSON('/hot-picks.json', renderPicks);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
