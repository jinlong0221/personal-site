/**
 * 龙兄知识库 · 全局 JavaScript
 * 纯原生，无框架依赖
 */

(function () {
  'use strict';

  // ============================================================
  // 1. Theme Toggle (深浅主题切换)
  //    规则：6:00-18:00 自动亮色，localStorage 记忆，按钮切换
  // ============================================================
  const THEME_KEY = 'theme';

  function getAutoTheme() {
    var h = new Date().getHours();
    return (h >= 6 && h < 18) ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    updateThemeIcon(theme);
  }

  function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
  }

  function updateThemeIcon(theme) {
    var btn = document.getElementById('themeToggle');
    if (btn) {
      btn.textContent = theme === 'dark' ? '☀️' : '🌙';
      btn.setAttribute('aria-label', theme === 'dark' ? '切换到亮色' : '切换到暗色');
    }
  }

  // Init theme
  (function initTheme() {
    var saved = localStorage.getItem(THEME_KEY);
    if (saved && (saved === 'dark' || saved === 'light')) {
      applyTheme(saved);
    } else {
      applyTheme(getAutoTheme());
    }

    var btn = document.getElementById('themeToggle');
    if (btn) {
      btn.addEventListener('click', function () {
        var cur = getCurrentTheme();
        applyTheme(cur === 'dark' ? 'light' : 'dark');
      });
    }

    // Watch for external theme changes
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(function () {
        updateThemeIcon(getCurrentTheme());
      }).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
      });
    }
  })();

  // ============================================================
  // 2. Hamburger Menu (汉堡菜单)
  // ============================================================
  (function initHamburger() {
    var hamburger = document.querySelector('.hamburger');
    var mobileNav = document.querySelector('.mobile-nav');

    if (!hamburger || !mobileNav) return;

    hamburger.addEventListener('click', function () {
      hamburger.classList.toggle('active');
      mobileNav.classList.toggle('open');
    });

    // Close on link click
    var links = mobileNav.querySelectorAll('a');
    links.forEach(function (link) {
      link.addEventListener('click', function () {
        hamburger.classList.remove('active');
        mobileNav.classList.remove('open');
      });
    });

    // Close on click outside
    document.addEventListener('click', function (e) {
      if (!hamburger.contains(e.target) && !mobileNav.contains(e.target)) {
        hamburger.classList.remove('active');
        mobileNav.classList.remove('open');
      }
    });
  })();

  // ============================================================
  // 3. Breadcrumb Auto-generation (面包屑自动生成)
  // ============================================================
  (function initBreadcrumb() {
    var container = document.getElementById('breadcrumb');
    if (!container) return;

    var path = window.location.pathname;
    var parts = path.replace(/\/$/, '').split('/').filter(Boolean);

    // GitHub Pages: last part before .html is the page
    var crumbs = [{ label: '首页', url: '/' }];

    // Map filenames to Chinese titles
    var titleMap = {
      'agarwood': '沉香鉴别',
      'bracelet': '文玩手串',
      'diguniu': '地牯牛',
      'dilong': '地龙',
      'herbs': '中药材与名贵香料',
      'huashicao': '化石草',
      'huashifen': '滑石粉',
      'jiangzhenxiang': '降真香',
      'kopi-luwak': '猫屎咖啡',
      'sheyang': '射阳天气',
      'shuizhi': '水蛭',
      'tesla': '新能源汽车',
      'model3': 'Model 3',
      'modely': 'Model Y',
      'models': 'Model S',
      'modelx': 'Model X',
      'cybertruck': '赛博皮卡',
      'charging': '充电指南',
      'accessories': '车载配件',
      'maintenance': '保养维修',
      'travel': '旅行',
      'wulingzhi': '五灵脂',
      'xiongdan': '熊胆',
      'changelog': '更新日志',
      'index': '首页'
    };

    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      var name = part.replace(/\.html?$/i, '');
      var label = titleMap[name] || name;
      var url = '';
      for (var j = 0; j <= i; j++) {
        url += '/' + parts[j];
      }

      if (name === 'index') continue; // skip index
      crumbs.push({ label: label, url: url });
    }

    // If only homepage, don't show breadcrumb
    if (crumbs.length <= 1) {
      container.style.display = 'none';
      return;
    }

    var html = '';
    for (var k = 0; k < crumbs.length; k++) {
      var isLast = k === crumbs.length - 1;
      if (!isLast) {
        html += '<a href="' + crumbs[k].url + '">' + crumbs[k].label + '</a>';
        html += '<span class="sep">›</span>';
      } else {
        html += '<span class="current">' + crumbs[k].label + '</span>';
      }
    }
    container.innerHTML = html;
    container.className = 'breadcrumb';
  })();

  // ============================================================
  // 4. Copy Button (一键复制)
  // ============================================================
  (function initCopyButtons() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.copy-btn');
      if (!btn) return;

      var target = btn.getAttribute('data-copy-target');
      var text;

      if (target) {
        var el = document.querySelector(target);
        text = el ? el.textContent || el.innerText : '';
      } else {
        text = btn.getAttribute('data-copy-text') || '';
      }

      if (!text) return;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          showCopied(btn);
        });
      } else {
        // Fallback
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand('copy');
          showCopied(btn);
        } catch (err) {
          // silently fail
        }
        document.body.removeChild(ta);
      }
    });

    function showCopied(btn) {
      var original = btn.textContent;
      btn.textContent = '已复制 ✓';
      btn.classList.add('copied');
      setTimeout(function () {
        btn.textContent = original;
        btn.classList.remove('copied');
      }, 1500);
    }
  })();

  // ============================================================
  // 5. Site Search (站内搜索)
  // ============================================================
  var searchIndex = [];

  function loadSearchIndex(callback) {
    var base = window.location.pathname.replace(/[^/]*\.html?$/, '');
    var url = base + 'search-index.json';

    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        searchIndex = data || [];
        if (callback) callback();
      })
      .catch(function () {
        // silently fail
      });
  }

  function performSearch(query) {
    if (!query || query.length < 1) return [];

    var q = query.toLowerCase().trim();
    var terms = q.split(/\s+/);

    return searchIndex.map(function (item) {
      var pool = (item.title + ' ' + (item.keywords || '')).toLowerCase();
      var score = 0;

      terms.forEach(function (term) {
        if (pool.indexOf(term) !== -1) {
          score += pool.indexOf(term) === 0 ? 2 : 1; // title match bonus
        }
      });

      return { item: item, score: score };
    })
    .filter(function (r) { return r.score > 0; })
    .sort(function (a, b) { return b.score - a.score; })
    .map(function (r) { return r.item; });
  }

  function renderSearchResults(results, container) {
    if (!container) return;

    if (results.length === 0) {
      container.innerHTML = '<div class="no-results">没有找到相关内容</div>';
      container.classList.add('has-results');
      return;
    }

    var html = '';
    results.forEach(function (item) {
      html += '<a href="' + item.url + '">' + item.title + '</a>';
    });
    container.innerHTML = html;
    container.classList.add('has-results');
  }

  (function initSearch() {
    var input = document.querySelector('.search-box input');
    var resultsContainer = document.querySelector('.search-results');

    if (!input) return;

    loadSearchIndex();

    var debounceTimer = null;
    input.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      var query = input.value;

      debounceTimer = setTimeout(function () {
        if (query.length < 1) {
          if (resultsContainer) {
            resultsContainer.innerHTML = '';
            resultsContainer.classList.remove('has-results');
          }
          return;
        }
        var results = performSearch(query);
        renderSearchResults(results, resultsContainer);
      }, 200);
    });

    // Close results on click outside
    document.addEventListener('click', function (e) {
      if (resultsContainer && !e.target.closest('.search-box')) {
        resultsContainer.classList.remove('has-results');
      }
    });

    // ESC to close
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && resultsContainer) {
        resultsContainer.classList.remove('has-results');
        input.blur();
      }
    });
  })();

  // ============================================================
  // 6. Utility: Add copy buttons to code/pre blocks
  // ============================================================
  (function autoAddCopyButtons() {
    var blocks = document.querySelectorAll('pre, .code-block');
    blocks.forEach(function (block) {
      var wrapper = document.createElement('div');
      wrapper.style.position = 'relative';

      block.parentNode.insertBefore(wrapper, block);
      wrapper.appendChild(block);

      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = '复制';
      btn.setAttribute('data-copy-target', block.tagName.toLowerCase() === 'pre' ? 'pre' : '.code-block');
      btn.style.position = 'absolute';
      btn.style.top = '4px';
      btn.style.right = '4px';

      wrapper.appendChild(btn);
    });
  })();

})();
