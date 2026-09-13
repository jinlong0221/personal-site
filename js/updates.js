/**
 * updates.js - 板块最后更新日期
 */
(function () {
  function loadUpdates() {
    var containers = document.querySelectorAll('[data-update-key]');
    if (!containers.length) return;

    var base = '';
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var m = scripts[i].src.match(/(.*\/)js\/.+/);
      if (m) { base = m[1]; break; }
    }

    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/updates.json', true);
    xhr.responseType = 'json';
    xhr.onload = function () {
      if (xhr.status !== 200) return;
      var data = xhr.response;
      if (!data) return;

      containers.forEach(function (el) {
        var key = el.getAttribute('data-update-key');
        var info = data[key];
        if (info && info.lastUpdate) {
          el.textContent = '最后更新：' + info.lastUpdate;
          el.style.display = 'block';
        }
      });
    };
    xhr.send();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadUpdates);
  } else {
    loadUpdates();
  }
})();
