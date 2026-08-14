/**
 * board_originals.js — 在板块页注入「本板块原创」
 * 读取 data/feed.json，按容器 data-board 筛选 type=原创 的条目并渲染。
 * 无 #boardOriginals 容器时零开销退出；数据缺失/失败静默隐藏，绝不报错中断。
 */
(function () {
  var wrap = document.getElementById('boardOriginals');
  if (!wrap) return;
  var board = wrap.getAttribute('data-board') || '';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  var base = '';
  var scripts = document.querySelectorAll('script[src]');
  for (var i = 0; i < scripts.length; i++) {
    var m = scripts[i].src.match(/(.*\/)js\/.+/);
    if (m) { base = m[1]; break; }
  }

  var xhr = new XMLHttpRequest();
  xhr.open('GET', base + 'data/feed.json?t=' + Date.now(), true);
  xhr.responseType = 'json';
  xhr.onload = function () {
    if (xhr.status !== 200 || !xhr.response || !Array.isArray(xhr.response.items)) {
      wrap.style.display = 'none';
      return;
    }
    var items = xhr.response.items.filter(function (it) { return it.board === board; });
    if (!items.length) { wrap.style.display = 'none'; return; }
    items.sort(function (a, b) { return String(b.date || '').localeCompare(String(a.date || '')); });
    var html = '<h2 class="bo-title">本板块原创</h2><div class="bo-list">';
    items.forEach(function (it) {
      var accent = it.accent || '#8B7FD6';
      var cover = it.cover
        ? '<div class="bo-card-cover"><img class="bo-cover" src="' + esc(it.cover) +
          '" alt="' + esc(it.title) + '" loading="lazy" decoding="async"></div>'
        : '';
      html += '<a class="bo-card" href="' + esc(it.link) + '">' +
        cover +
        '<div class="bo-card-body">' +
        '<div class="bo-card-head">' +
        '<span class="bo-badge" style="color:' + esc(accent) + ';border-color:' + esc(accent) + '66">' + esc(it.type) + '</span>' +
        '<time class="bo-date">' + esc(it.date) + '</time></div>' +
        (it.title ? '<h3 class="bo-card-title">' + esc(it.title) + '</h3>' : '') +
        '<p class="bo-card-text">' + esc(it.text || '') + '</p>' +
        '</div></a>';
    });
    html += '</div>';
    wrap.innerHTML = html;
  };
  xhr.onerror = function () { wrap.style.display = 'none'; };
  xhr.send();
})();
