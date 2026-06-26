/**
 * changelog.js - 加载更新日志
 */
(function () {
  function loadChangelog() {
    var container = document.getElementById('weeklyChangelog');
    if (!container) return;

    var base = '';
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var m = scripts[i].src.match(/(.*\/)js\/.+/);
      if (m) { base = m[1]; break; }
    }

    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/changelog.json', true);
    xhr.responseType = 'json';
    xhr.onload = function () {
      if (xhr.status !== 200) return;
      var data = xhr.response;
      if (!Array.isArray(data)) return;

      var html = '';
      var count = 0;
      data.forEach(function (item) {
        if (count >= 5) return;
        html += '<div class="changelog-item">' +
          '<span class="changelog-date">' + esc(item.date) + '</span>' +
          '<span class="changelog-content">' + esc(item.content) + '</span>' +
          '</div>';
        count++;
      });
      container.innerHTML = html;

      // 更新条数 badge
      var badge = document.getElementById('update-count');
      if (badge) badge.textContent = count + '条';
    };
    xhr.send();
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadChangelog);
  } else {
    loadChangelog();
  }
})();
