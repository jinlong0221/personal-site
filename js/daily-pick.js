/**
 * daily-pick.js - 今日推荐 + 热门搜索
 */
(function () {
  // ===== 推荐池 =====
  const pickPool = [
    {
      name: '沉香鉴别指南',
      desc: '天然沉香四大鉴别方法，告别假货少走弯路',
      tag: '🔬 药材与手串',
      url: 'agarwood.html',
      img: 'https://images.unsplash.com/photo-1606041011872-596597976b25?w=160&h=160&fit=crop'
    },
    {
      name: '特斯拉 Model Y',
      desc: '用车科普·充电指南·配件推荐一网打尽',
      tag: '🚗 数码科技',
      url: 'tesla.html',
      img: 'https://images.unsplash.com/photo-1619316885535-9a8ab3ddf0f3?w=160&h=160&fit=crop'
    },
    {
      name: '中药养生茶',
      desc: '30+经典配方，按体质喝对茶',
      tag: '🌿 生活百科',
      url: 'health-tea.html',
      img: 'https://images.unsplash.com/photo-1563911302283-d2bc129e7570?w=160&h=160&fit=crop'
    },
    {
      name: 'PlayStation 5',
      desc: '超高速SSD·DualSense手柄·次世代游戏体验',
      tag: '🎮 游戏主机',
      url: 'console.html',
      img: 'https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?w=160&h=160&fit=crop'
    },
    {
      name: '漫威观影顺序',
      desc: 'MCU全阶段观影指南，收藏慢慢看',
      tag: '🎭 流行文化',
      url: 'marvel.html',
      img: 'https://images.unsplash.com/photo-1635805737707-575885ab0820?w=160&h=160&fit=crop'
    },
    {
      name: '星月菩提盘玩',
      desc: '从白富美到深老红，盘玩进阶指南',
      tag: '📿 文玩手串',
      url: 'star-moon.html',
      img: 'https://images.unsplash.com/photo-1573408301185-9519f94c55f4?w=160&h=160&fit=crop'
    },
    {
      name: '紫砂壶鉴赏',
      desc: '95件紫砂艺术品，品味东方美学',
      tag: '🏺 传统文化',
      url: 'zisha.html',
      img: 'https://images.unsplash.com/photo-1563195582-4e1ba7e41ae9?w=160&h=160&fit=crop'
    },
    {
      name: '射阳天气预报',
      desc: '新坍镇实时天气，出行无忧',
      tag: '⛅ 生活服务',
      url: 'xintan-weather.html',
      img: 'https://images.unsplash.com/photo-1504608524841-42584120d693?w=160&h=160&fit=crop'
    },
    {
      name: 'Switch 游戏推荐',
      desc: '独占大作+多人派对，动森/塞尔达/马车',
      tag: '🎮 游戏主机',
      url: 'console.html',
      img: 'https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?w=160&h=160&fit=crop'
    },
    {
      name: '中药材香料',
      desc: '10种名贵药材香料知识，从入门到精通',
      tag: '🌿 生活百科',
      url: 'herbs.html',
      img: 'https://images.unsplash.com/photo-1471188033229-46dc1bf3f90c?w=160&h=160&fit=crop'
    },
    {
      name: '特斯拉充电攻略',
      desc: '家用充电桩安装·公共充电站使用指南',
      tag: '🚗 数码科技',
      url: 'tesla.html',
      img: 'https://images.unsplash.com/photo-1593941707882-a5bba14938c7?w=160&h=160&fit=crop'
    },
    {
      name: '高考查分入口',
      desc: '2026年高考成绩查询，收藏备用',
      tag: '📚 实用工具',
      url: 'gaokao.html',
      img: 'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=160&h=160&fit=crop'
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

  function renderPick() {
    const container = document.getElementById('daily-pick');
    if (!container) return;

    // 随机选一个（避免重复）
    let newIndex;
    do {
      newIndex = Math.floor(Math.random() * pickPool.length);
    } while (newIndex === currentPickIndex && pickPool.length > 1);
    currentPickIndex = newIndex;

    const item = pickPool[newIndex];

    // 填充内容
    const card = document.getElementById('pick-card');
    const img = document.getElementById('pick-img');
    const name = document.getElementById('pick-name');
    const desc = document.getElementById('pick-desc');
    const tag = document.getElementById('pick-tag');

    if (card) card.href = item.url;
    if (img) {
      img.src = item.img;
      img.alt = item.name;
      // 图片加载失败时用占位图
      img.onerror = function() {
        this.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><rect fill="%23f0f0f0" width="80" height="80"/><text x="40" y="45" text-anchor="middle" font-size="30">📚</text></svg>';
      };
    }
    if (name) name.textContent = item.name;
    if (desc) desc.textContent = item.desc;
    if (tag) tag.textContent = item.tag;
  }

  // ===== 热门搜索逻辑 =====
  function renderHotTags() {
    const container = document.getElementById('hot-tags');
    if (!container) return;

    container.innerHTML = hotKeywords.map(function(kw) {
      return '<a class="hot-tag" onclick="doSearch(\'' + kw + '\')">' + kw + '</a>';
    }).join('');
  }

  // 触发搜索
  window.doSearch = function(kw) {
    const searchInput = document.getElementById('homeSearchInput');
    if (searchInput) {
      searchInput.value = kw;
      searchInput.focus();
      // 触发搜索事件
      searchInput.dispatchEvent(new Event('input'));
      // 隐藏热门搜索
      document.getElementById('search-hot').classList.remove('active');
    }
  };

  // ===== 初始化 =====
  function init() {
    // 初始化今日推荐
    renderPick();

    // 初始化热门搜索
    renderHotTags();

    // 刷新按钮点击事件
    const refreshBtn = document.getElementById('pick-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        // 旋转动画
        this.style.transform = 'rotate(360deg)';
        setTimeout(function() {
          refreshBtn.style.transform = 'rotate(0deg)';
        }, 500);

        // 卡片切换动画
        const card = document.getElementById('pick-card');
        if (card) {
          card.style.opacity = '0';
          card.style.transform = 'translateY(10px)';
          setTimeout(function() {
            renderPick();
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
          }, 300);
        } else {
          renderPick();
        }
      });
    }

    // 搜索框聚焦/失焦事件
    const searchInput = document.getElementById('homeSearchInput');
    const searchHot = document.getElementById('search-hot');

    if (searchInput && searchHot) {
      searchInput.addEventListener('focus', function() {
        searchHot.classList.add('active');
      });

      searchInput.addEventListener('blur', function() {
        setTimeout(function() {
          searchHot.classList.remove('active');
        }, 200);
      });
    }
  }

  // 页面加载完成后执行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
