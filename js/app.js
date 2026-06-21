/**
 * 龙兄知识库 · 全局 JavaScript
 * 纯原生，无框架依赖
 */

(function () {
  'use strict';

  // ============================================================
  // 0. XSS Protection - HTML Escape Utility
  // ============================================================
  function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

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
        html += '<a href="' + escapeHtml(crumbs[k].url) + '">' + escapeHtml(crumbs[k].label) + '</a>';
        html += '<span class="sep">›</span>';
      } else {
        html += '<span class="current">' + escapeHtml(crumbs[k].label) + '</span>';
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
        }).catch(function () {
          fallbackCopy(text, btn);
        });
      } else {
        fallbackCopy(text, btn);
      }
    });

    function fallbackCopy(text, btn) {
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

    function showCopied(btn) {
      var original = btn.textContent;
      btn.textContent = '已复制 ✓';
      btn.classList.add('copied');
      setTimeout(function () {
        btn.textContent = original;
        btn.classList.remove('copied');
      }, 2000);
    }
  })();

  // ============================================================
  // 5. Site Search (站内搜索 + Modal)
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
      var title = (item.title || '').toLowerCase();
      var keywords = (item.keywords || '').toLowerCase();
      var desc = (item.description || '').toLowerCase();
      var pool = title + ' ' + keywords + ' ' + desc;
      var score = 0;

      terms.forEach(function (term) {
        if (pool.indexOf(term) !== -1) {
          // title match gets higher score
          if (title.indexOf(term) !== -1) score += 3;
          // description match
          else if (desc.indexOf(term) !== -1) score += 2;
          // keywords match
          else score += 1;
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
      container.innerHTML = '<div class="search-no-results">没有找到相关内容</div>';
      return;
    }

    var html = '<div class="search-results-list">';
    results.forEach(function (item) {
      var desc = item.description ? item.description : (item.keywords ? item.keywords.substring(0, 50) + '...' : '');
      html += '<a href="' + escapeHtml(item.url) + '" class="search-result-item">';
      html += '<div class="search-result-title">' + escapeHtml(item.title) + '</div>';
      if (desc) {
        html += '<div class="search-result-desc">' + escapeHtml(desc) + '</div>';
      }
      html += '</a>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  // Create search modal if not exists
  function ensureSearchModal() {
    var existing = document.getElementById('searchModal');
    if (existing) return existing;

    var modal = document.createElement('div');
    modal.id = 'searchModal';
    modal.className = 'search-modal';
    modal.innerHTML =
      '<div class="search-modal-content">' +
        '<div class="search-modal-header">' +
          '<input type="text" class="search-modal-input" placeholder="搜索药材、手串、车型..." aria-label="搜索">' +
          '<button class="search-modal-close" aria-label="关闭搜索">&times;</button>' +
        '</div>' +
        '<div class="search-modal-results"></div>' +
      '</div>';

    document.body.appendChild(modal);
    return modal;
  }

  (function initSearch() {
    // Load search index
    loadSearchIndex();

    // Ensure modal exists
    var modal = ensureSearchModal();
    var input = modal.querySelector('.search-modal-input');
    var resultsContainer = modal.querySelector('.search-modal-results');
    var closeBtn = modal.querySelector('.search-modal-close');

    // Search button in navbar
    var searchBtn = document.getElementById('searchBtn');
    if (searchBtn) {
      searchBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        openSearchModal();
      });
    }

    // Also handle home page search entry
    var homeSearchInput = document.getElementById('homeSearchInput');
    var homeSearchBtn = document.getElementById('homeSearchBtn');
    if (homeSearchInput && homeSearchBtn) {
      homeSearchBtn.addEventListener('click', function () {
        openSearchModal(homeSearchInput.value);
      });
      homeSearchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          openSearchModal(homeSearchInput.value);
        }
      });
    }

    function openSearchModal(initialQuery) {
      modal.classList.add('active');
      setTimeout(function () {
        input.focus();
        if (initialQuery) {
          input.value = initialQuery;
          handleSearch(input.value);
        }
      }, 50);
    }

    function closeSearchModal() {
      modal.classList.remove('active');
      input.value = '';
      resultsContainer.innerHTML = '';
    }

    function handleSearch(query) {
      if (query.length < 1) {
        resultsContainer.innerHTML = '<div class="search-hint">输入关键词开始搜索</div>';
        return;
      }
      var results = performSearch(query);
      renderSearchResults(results, resultsContainer);
    }

    // Live search on input
    var debounceTimer = null;
    input.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        handleSearch(input.value);
      }, 150);
    });

    // Close button
    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        closeSearchModal();
      });
    }

    // Close on overlay click
    modal.addEventListener('click', function (e) {
      if (e.target === modal) {
        closeSearchModal();
      }
    });

    // ESC to close
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('active')) {
        closeSearchModal();
      }
    });

    // Initial hint
    resultsContainer.innerHTML = '<div class="search-hint">输入关键词开始搜索</div>';
  })();

  // ============================================================
  // 6. Auto Copy Buttons (自动添加复制按钮)
  // ============================================================
  (function autoAddCopyButtons() {
    // Wait for DOM ready
    function init() {
      // 1. Add copy button to pre code blocks (top-right corner)
      var codeBlocks = document.querySelectorAll('pre');
      codeBlocks.forEach(function (block) {
        // Check if already wrapped
        if (block.parentElement.classList.contains('code-block-wrapper')) return;

        var wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';
        wrapper.style.position = 'relative';

        block.parentNode.insertBefore(wrapper, block);
        wrapper.appendChild(block);

        var btn = document.createElement('button');
        btn.className = 'copy-btn code-copy-btn';
        btn.innerHTML = '📋 复制';
        btn.setAttribute('data-copy-text', block.textContent || block.innerText || '');
        btn.style.position = 'absolute';
        btn.style.top = '8px';
        btn.style.right = '8px';
        btn.style.zIndex = '10';

        wrapper.appendChild(btn);
      });

      // 2. Add copy button to .tip-box and .warning-box (bottom-right)
      var infoBoxes = document.querySelectorAll('.tip-box, .warning-box');
      infoBoxes.forEach(function (box) {
        if (box.querySelector('.copy-btn')) return; // already has button

        var btn = document.createElement('button');
        btn.className = 'copy-btn box-copy-btn';
        btn.textContent = '复制';
        btn.setAttribute('data-copy-text', box.textContent || box.innerText || '');
        btn.style.cssText = 'position:absolute;bottom:8px;right:8px;z-index:10;font-size:0.75rem;padding:4px 10px;';

        box.style.position = 'relative';
        box.appendChild(btn);
      });
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  })();

})();
