/**
 * changelog.js - 加载并渲染更新日志
 *
 * 合并两份数据源（去重 + 按日期倒序）：
 *   - data/changelog.json : 手工维护的精选历史（人工补充的重大更新）
 *   - changelog.json      : 自动更新机器人每日写入的条目
 * 两份任一缺失都不影响另一份渲染，互不脱节。
 */
(function () {
  function loadChangelog() {
    var container = document.getElementById('weeklyChangelog');
    if (!container) return; // 非更新日志页不拉取，零开销

    var base = '';
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var m = scripts[i].src.match(/(.*\/)js\/.+/);
      if (m) { base = m[1]; break; }
    }

    var sources = ['data/changelog.json', 'changelog.json'];
    var results = [];
    var pending = sources.length;

    function render() {
      pending--;
      if (pending > 0) return;

      var seen = {};
      var merged = [];
      results.forEach(function (arr) {
        if (!Array.isArray(arr)) return;
        arr.forEach(function (item) {
          if (!item || !item.date) return;
          var key = item.date + ' ' + item.content;
          if (seen[key]) return;
          seen[key] = 1;
          merged.push(item);
        });
      });
      merged.sort(function (a, b) {
        return a.date < b.date ? 1 : (a.date > b.date ? -1 : 0);
      });

      var html = '';
      merged.forEach(function (item) {
        html += '<div class="timeline-item">' +
          '<div class="timeline-date">' + esc(item.date) + '</div>' +
          '<div class="timeline-content"><p>' + esc(item.content) + '</p></div>' +
          '</div>';
      });
      container.innerHTML = html;

      var badge = document.getElementById('update-count');
      if (badge) badge.textContent = merged.length + '条';
    }

    sources.forEach(function (src) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', base + src, true);
      xhr.responseType = 'json';
      xhr.onload = function () {
        results.push((xhr.status === 200 && Array.isArray(xhr.response)) ? xhr.response : []);
        render();
      };
      xhr.onerror = function () {
        results.push([]);
        render();
      };
      xhr.send();
    });
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
