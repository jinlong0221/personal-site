// search.js - Pagefind 搜索集成（轻量化版）
// 2026-07-06: 旧弹窗搜索已废弃，统一跳转到 /search.html

document.addEventListener('DOMContentLoaded', function() {
  // 导航栏搜索按钮 → 跳转搜索页
  var sb = document.getElementById('searchBtn');
  if (sb) {
    sb.addEventListener('click', function(e) {
      e.preventDefault();
      window.location.href = '/search.html';
    });
  }

  // 首页搜索框 → 跳转搜索页（带上查询参数）
  var hi = document.getElementById('homeSearchInput');
  var hb = document.getElementById('homeSearchBtn');
  if (hi && hb) {
    hb.addEventListener('click', function() {
      var q = hi.value.trim();
      if (q) {
        window.location.href = '/search.html?q=' + encodeURIComponent(q);
      } else {
        window.location.href = '/search.html';
      }
    });
    hi.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        var q = hi.value.trim();
        window.location.href = '/search.html' + (q ? '?q=' + encodeURIComponent(q) : '');
      }
    });
  }

  // 搜索页：自动填充 URL 查询参数
  var params = new URLSearchParams(window.location.search);
  var q = params.get('q');
  if (q && document.getElementById('pagefind-search')) {
    // Pagefind UI 会自动聚焦，不需要手动填充
    // 触发一次搜索
    setTimeout(function() {
      var input = document.querySelector('.pagefind-ui__search-input');
      if (input && q) input.value = q;
    }, 500);
  }
});
