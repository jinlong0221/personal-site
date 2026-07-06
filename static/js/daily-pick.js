/**
 * daily-pick.js - 今日推荐 + 热门搜索
 * 本地图片 + 加载淡入动画
 */
(function () {
  // ===== 推荐池（本地图片，无外部依赖）=====
  const pickPool = [
    {
      name: '沉香鉴别指南',
      desc: '天然沉香四大鉴别方法，告别假货少走弯路',
      tag: '🔬 药材与手串',
      url: 'herbs/chenxiang.html',
      img: 'img/zisha/wht2026_p1_0.webp'
    },
    {
      name: '特斯拉 Model Y',
      desc: '用车科普·充电指南·配件推荐一网打尽',
      tag: '🚗 数码科技',
      url: 'tesla.html',
      img: 'img/tesla/modely/front.webp'
    },
    {
      name: '中药养生茶',
      desc: '30+经典配方，按体质喝对茶',
      tag: '🌿 生活百科',
      url: 'health-tea.html',
      img: 'img/zisha/wht2026_p1_1.webp'
    },
    {
      name: 'PlayStation 5',
      desc: '超高速SSD·DualSense手柄·次世代游戏体验',
      tag: '🎮 游戏主机',
      url: 'console-playstation-5.html',
      img: 'img/consoles/ps5.webp'
    },
    {
      name: '漫威观影顺序',
      desc: 'MCU全阶段观影指南，收藏慢慢看',
      tag: '🎭 流行文化',
      url: 'marvel.html',
      img: 'img/marvel/iron-man-1.jpg'
    },
    {
      name: '紫砂壶鉴赏',
      desc: '95件紫砂艺术品，品味东方美学',
      tag: '🏺 传统文化',
      url: 'zisha.html',
      img: 'img/zisha/wht2026_p1_3.webp'
    },
    {
      name: '射阳天气预报',
      desc: '新坍镇实时天气，出行无忧',
      tag: '⛅ 生活服务',
      url: 'xintan-weather.html',
      img: 'img/zisha/wht2026_p1_4.webp'
    },
    {
      name: 'Nintendo Switch 2',
      desc: '独占大作+多人派对，动森/塞尔达/马车8',
      tag: '🎮 游戏主机',
      url: 'console-switch-2.html',
      img: 'img/consoles/switch-2.webp'
    },
    {
      name: '中药材香料',
      desc: '10种名贵药材香料知识，从入门到精通',
      tag: '🌿 生活百科',
      url: 'herbs.html',
      img: 'img/zisha/wht2026_p1_6.webp'
    },
    {
      name: '高考查分入口',
      desc: '2026年高考成绩查询，收藏备用',
      tag: '📚 实用工具',
      url: 'gaokao.html',
      img: 'img/zisha/wht2026_p1_7.webp'
    }
  ];

  // ===== 热门搜索词 =====
  const hotKeywords = [
    '沉香怎么辨真假',
    'Model Y 充电攻略',
    '2026高考分数线',
    'PS5 必玩游戏',
    '中药养生茶配方',
    '漫威观影顺序',
    '紫砂壶怎么养',
    '文玩手串真假分辨',
    '射阳天气预报',
    'Switch 2 配置'
  ];

  // ===== 今日推荐逻辑 =====
  let currentPickIndex = -1;

  function renderPick(animate) {
    animate = (animate !== false);
    var card = document.getElementById('pick-card');
    if (!card) return;

    // 随机选一个（避免连续重复）
    var newIndex;
    do {
      newIndex = Math.floor(Math.random() * pickPool.length);
    } while (newIndex === currentPickIndex && pickPool.length > 1);
    currentPickIndex = newIndex;

    var item = pickPool[newIndex];

    if (animate) {
      card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      card.style.opacity = '0';
      card.style.transform = 'translateY(12px)';
    }

    // 更新内容
    card.href = item.url;
    card.target = '_self';
    card.onclick = null; // <a> 标签直接跳转，清除旧 JS

    var img = document.getElementById('pick-img');
    if (img) {
      img.src = item.img;
      img.alt = item.name;
      img.onerror = function() {
        // 本地图片加载失败，显示 emoji 占位
        this.style.display = 'none';
        var fb = document.createElement('div');
        fb.style.cssText = 'width:80px;height:80px;display:flex;align-items:center;justify-content:center;font-size:36px;background:var(--dark-tile);border-radius:8px;flex-shrink:0;';
        fb.textContent = item.tag.split(' ')[0];
        this.parentNode.insertBefore(fb, this.nextSibling);
      };
    }

    var nameEl = document.getElementById('pick-name');
    if (nameEl) nameEl.textContent = item.name;

    var descEl = document.getElementById('pick-desc');
    if (descEl) descEl.textContent = item.desc;

    var tagEl = document.getElementById('pick-tag');
    if (tagEl) tagEl.textContent = item.tag;

    if (animate) {
      var _card = card;
      setTimeout(function() {
        _card.style.opacity = '1';
        _card.style.transform = 'translateY(0)';
      }, 50);
    }
  }

  // ===== 热门搜索 =====
  function renderHotTags() {
    var container = document.getElementById('hot-tags');
    if (!container) return;
    container.innerHTML = hotKeywords.map(function(kw) {
      return '<a class="hot-tag" onclick="doSearch(\'' + kw + '\')">' + kw + '</a>';
    }).join('');
  }

  window.doSearch = function(kw) {
    var searchInput = document.getElementById('homeSearchInput');
    if (searchInput) {
      searchInput.value = kw;
      searchInput.focus();
      searchInput.dispatchEvent(new Event('input'));
      var hot = document.getElementById('search-hot');
      if (hot) hot.classList.remove('active');
    }
  };

  // ===== 初始化 =====
  function init() {
    renderPick(true); // 首次加载带淡入
    renderHotTags();

    var refreshBtn = document.getElementById('pick-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        var icon = this;

        // 按钮旋转动画
        icon.style.transition = 'transform 0.5s ease';
        icon.style.transform = 'rotate(360deg)';
        setTimeout(function() { icon.style.transform = ''; }, 500);

        var card = document.getElementById('pick-card');
        if (card) {
          card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
          card.style.opacity = '0';
          card.style.transform = 'translateY(10px)';
          setTimeout(function() {
            renderPick(false); // 内容替换
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
          }, 300);
        } else {
          renderPick(true);
        }
      });
    }

    // 搜索框聚焦/失焦
    var searchInput = document.getElementById('homeSearchInput');
    var searchHot = document.getElementById('search-hot');
    if (searchInput && searchHot) {
      searchInput.addEventListener('focus', function() { searchHot.classList.add('active'); });
      searchInput.addEventListener('blur', function() {
        setTimeout(function() { searchHot.classList.remove('active'); }, 200);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
