/**
 * feed.js — 渲染首页/碎碎念页的时间线动态流
 *
 * 读取 data/feed.json（由 scripts/build_feed.js 聚合生成），按类型/标签筛选渲染。
 * 设计原则（对齐全站既有约定，避免回归）：
 *   - 用 XHR + 基址推导（同 changelog.js），兼容根页面与子目录；
 *   - 所有动态数据 esc() 转义，杜绝 XSS 与 HTML 注入；
 *   - 卡片用 flex + min-width:0 + word-break，长文绝不撑破布局；
 *   - 数据缺失/接口失败均有兜底空态，绝不白屏或报错中断。
 */
(function () {
  function init() {
    var feed = document.getElementById('mbFeed');
    if (!feed) return; // 非时间线页不拉取，零开销
    var chips = document.getElementById('mbChips');

    var base = '';
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var m = scripts[i].src.match(/(.*\/)js\/.+/);
      if (m) { base = m[1]; break; }
    }
    var defaultFilter =
      feed.getAttribute('data-default-filter') ||
      (chips && chips.getAttribute('data-default-filter')) || 'all';

    function esc(s) {
      return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function showError() {
      feed.innerHTML = '<div class="mb-empty">动态加载失败，请稍后刷新。也可直接前往 ' +
        '<a href="' + base + 'changelog.html">更新日志</a> 或 ' +
        '<a href="' + base + 'travel.html">旅行</a> 查看。</div>';
    }

    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/feed.json?t=' + Date.now(), true);
    xhr.responseType = 'json';
    xhr.onload = function () {
      if (xhr.status === 200 && xhr.response && Array.isArray(xhr.response.items)) {
        render(xhr.response.items);
      } else {
        showError();
      }
    };
    xhr.onerror = showError;
    xhr.send();

    function avatarChar(type) {
      return (type || '·').charAt(0);
    }

    function render(items) {
      if (!items.length) {
        feed.innerHTML = '<div class="mb-empty">还没有动态，回头再来逛逛。</div>';
        return;
      }
      var html = '';
      items.forEach(function (it) {
        var accent = it.accent || '#8B7FD6';
        var timeStr = (it.date + ' ' + (it.time || '')).trim();
        var body = it.text || it.title || '';
        var tagsHtml = '';
        if (Array.isArray(it.tags) && it.tags.length) {
          tagsHtml = '<div class="mb-tags">' + it.tags.map(function (t) {
            return '<button type="button" class="mb-tag" data-tag="' + esc(t) + '">#' + esc(t) + '</button>';
          }).join('') + '</div>';
        }
        var coverHtml = it.cover
          ? '<img class="mb-cover" src="' + esc(it.cover) + '" alt="' + esc(it.title || '配图') +
            '" loading="lazy" decoding="async">'
          : '';
        var linkHtml = it.link
          ? '<a class="mb-link" href="' + esc(it.link) + '">' + esc(it.linkText || '查看详情 →') + '</a>'
          : '';
        html += '<article class="mb-card" data-type="' + esc(it.type) + '"' +
          (it.tags && it.tags.length ? ' data-tags="' + esc(it.tags.join(',')) + '"' : '') + '>' +
          '<div class="mb-avatar" style="background:' + esc(accent) + '22;color:' + esc(accent) + '">' +
          esc(avatarChar(it.type)) + '</div>' +
          '<div class="mb-card-main">' +
          '<div class="mb-card-head">' +
          '<span class="mb-name">龙兄</span>' +
          '<span class="mb-badge" style="color:' + esc(accent) + ';border-color:' + esc(accent) + '66">' +
          esc(it.type) + '</span>' +
          '<span class="mb-time">' + esc(timeStr) + '</span>' +
          '</div>' +
          (it.title && it.title !== body ? '<h3 class="mb-title">' + esc(it.title) + '</h3>' : '') +
          '<div class="mb-text">' + esc(body) + '</div>' +
          coverHtml + tagsHtml + linkHtml +
          '</div></article>';
      });
      feed.innerHTML = html;

      if (chips) {
        var preset = chips.querySelector('.mb-chip');
        if (!preset) {
          var types = [];
          items.forEach(function (it) { if (types.indexOf(it.type) < 0) types.push(it.type); });
          var c = '<button type="button" class="mb-chip on" data-filter="all">全部</button>';
          types.forEach(function (t) {
            c += '<button type="button" class="mb-chip" data-filter="' + esc(t) + '">' + esc(t) + '</button>';
          });
          chips.innerHTML = c;
        }
        wireChips();
      }
    }

    function wireChips() {
      if (!chips) return;
      var chipEls = chips.querySelectorAll('.mb-chip');

      function apply(filter) {
        chipEls.forEach(function (c) {
          c.classList.toggle('on', c.getAttribute('data-filter') === filter);
        });
        var cards = feed.querySelectorAll('.mb-card');
        var anyVisible = false;
        cards.forEach(function (card) {
          var type = card.getAttribute('data-type');
          var tags = (card.getAttribute('data-tags') || '').split(',');
          var show = (filter === 'all') || (filter === type) || (tags.indexOf(filter) >= 0);
          card.style.display = show ? '' : 'none';
          if (show) anyVisible = true;
        });
        var empty = feed.querySelector('.mb-empty');
        if (!anyVisible && !empty) {
          var d = document.createElement('div');
          d.className = 'mb-empty';
          d.textContent = '这一分类下还没有动态。';
          feed.appendChild(d);
        } else if (anyVisible && empty) {
          empty.remove();
        }
      }

      chipEls.forEach(function (c) {
        c.addEventListener('click', function () { apply(c.getAttribute('data-filter')); });
      });
      feed.addEventListener('click', function (e) {
        var t = e.target.closest && e.target.closest('.mb-tag');
        if (t) apply(t.getAttribute('data-tag'));
      });
      apply(defaultFilter || 'all');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
