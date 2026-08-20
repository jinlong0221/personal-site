/* board-nav.js —— 全站通用的「粘性章节目录」
 * 用法：页面底部引入 <script defer src="/js/board-nav.js"></script>
 * 行为：
 *   1. 自动从内容区 h2 生成粘性目录（pill 样式），跳过导航/页眉/页脚内的 h2。
 *   2. 目录点击 → 平滑滚动到对应章节（避开粘性导航遮挡）。
 *   3. 滚动时高亮当前章节。
 * 仅用全站通用 CSS 变量，深浅色均安全，不依赖任何单板块主题色。
 * 注：大段折叠(section collapse)不在此处做——运行时 DOM 重包裹会丢内容，
 *     改由构建期方案处理，详见 scripts/。
 */
(function () {
  'use strict';
  if (window.__boardNavReady) return;
  window.__boardNavReady = true;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    var path = location.pathname;
    if (path === '/' || path.endsWith('/index.html')) return;

    // 收集内容区 h2（排除导航/页眉/页脚/目录自身）
    var allH2 = Array.prototype.slice.call(document.querySelectorAll('h2'));
    allH2 = allH2.filter(function (h) {
      var p = h;
      while (p) {
        if (
          p.tagName === 'NAV' ||
          p.tagName === 'HEADER' ||
          p.tagName === 'FOOTER' ||
          (p.className && /bn-toc/.test(p.className))
        )
          return false;
        p = p.parentNode;
      }
      return true;
    });
    if (allH2.length < 3) return;

    // 注入样式（自包含，仅用通用变量）
    if (!document.getElementById('bn-style')) {
      var css =
        'html{scroll-behavior:smooth}' +
        'h2[id]{scroll-margin-top:74px}' +
        '.bn-toc{position:sticky;top:62px;z-index:20;display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 10px;padding:10px 12px;background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow-sm)}' +
        '@media(max-width:768px){.bn-toc{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}.bn-toc::-webkit-scrollbar{display:none}.bn-toc a{flex-shrink:0}}' +
        '.bn-toc a{font-size:.82rem;padding:6px 13px;border-radius:999px;background:var(--bg-secondary);color:var(--text-secondary);text-decoration:none;transition:all .15s;cursor:pointer}' +
        '.bn-toc a:hover{background:var(--text-muted);color:var(--card)}' +
        '.bn-toc a.active{background:var(--accent);color:#1a1407}';
      var st = document.createElement('style');
      st.id = 'bn-style';
      st.textContent = css;
      document.head.appendChild(st);
    }

    // 生成目录
    var toc = document.createElement('nav');
    toc.className = 'bn-toc';
    toc.setAttribute('aria-label', '章节导航');
    allH2.forEach(function (h2, i) {
      if (!h2.id) h2.id = 'bn-sec-' + (i + 1);
      var a = document.createElement('a');
      a.href = '#' + h2.id;
      a.textContent = (h2.textContent || '').replace(/\s+/g, ' ').trim();
      a.dataset.target = h2.id;
      toc.appendChild(a);
    });
    allH2[0].parentNode.insertBefore(toc, allH2[0]);

    // 点击目录 → 平滑滚动（带细节守卫，兼容未来构建期折叠）
    toc.addEventListener('click', function (e) {
      var a = e.target.closest('a');
      if (!a) return;
      e.preventDefault();
      var id = a.dataset.target;
      var sec = document.getElementById(id);
      if (!sec) return;
      var det = sec.closest('details');
      if (det && !det.open) det.open = true;
      history.replaceState(null, '', '#' + id);
      sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    // 滚动高亮当前章节
    var links = Array.prototype.slice.call(toc.querySelectorAll('a'));
    if ('IntersectionObserver' in window && links.length) {
      var byId = {};
      links.forEach(function (a) {
        byId[a.dataset.target] = a;
      });
      var io = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (en) {
            if (en.isIntersecting) {
              links.forEach(function (l) {
                l.classList.remove('active');
              });
              var a = byId[en.target.id];
              if (a) a.classList.add('active');
            }
          });
        },
        { rootMargin: '-30% 0px -60% 0px', threshold: 0 }
      );
      allH2.forEach(function (h2) {
        io.observe(h2);
      });
    }
  });
})();
