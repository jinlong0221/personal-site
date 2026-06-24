/* ===== 首页动画效果 JavaScript ===== */

// 等待 DOM 加载完成
document.addEventListener('DOMContentLoaded', function() {

  // 存储所有 Observer 引用，用于清理
  const observers = [];

  /* 1. 滚动渐入动画 - 使用 IntersectionObserver */
  const fadeElements = document.querySelectorAll('.tile, .section-block, .home-collapsible');
  
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const fadeObserver = new IntersectionObserver(function(entries) {
    observers.push(fadeObserver);
    entries.forEach(function(entry, index) {
      if (entry.isIntersecting) {
        // 添加延迟，让卡片依次出现
        setTimeout(function() {
          entry.target.classList.add('visible');
        }, index * 100);
        fadeObserver.unobserve(entry.target);
      }
    });
  }, observerOptions);

  fadeElements.forEach(function(el) {
    el.classList.add('fade-in-up');
    fadeObserver.observe(el);
  });

  /* 2. 点击水波纹效果 - 同时支持鼠标和触摸 */
  function createRipple(e) {
    // 只在卡片和按钮上添加水波纹
    const target = e.target.closest('.tile, .btn, .icon-btn, .nav-links a');
    if (!target) return;

    // 防止重复创建
    const existingRipple = target.querySelector('.ripple');
    if (existingRipple) existingRipple.remove();

    const ripple = document.createElement('span');
    const rect = target.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    
    // 兼容触摸事件
    let x, y;
    if (e.touches) {
      x = e.touches[0].clientX - rect.left - size / 2;
      y = e.touches[0].clientY - rect.top - size / 2;
    } else {
      x = e.clientX - rect.left - size / 2;
      y = e.clientY - rect.top - size / 2;
    }

    ripple.style.cssText = `
      width: ${size}px;
      height: ${size}px;
      left: ${x}px;
      top: ${y}px;
    `;
    ripple.classList.add('ripple');

    target.style.position = 'relative';
    target.style.overflow = 'hidden';
    target.appendChild(ripple);

    setTimeout(function() {
      ripple.remove();
    }, 600);
  }

  // 同时监听 click 和 touchstart 事件
  document.addEventListener('click', createRipple);
  document.addEventListener('touchstart', createRipple, { passive: true });

  /* 3. 导航栏滚动效果 */
  const navbar = document.querySelector('.navbar');
  let lastScroll = 0;

  window.addEventListener('scroll', function() {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
    
    lastScroll = currentScroll;
  });

  /* 4. 数字动态效果 - 访问量统计 */
  const counters = document.querySelectorAll('#busuanzi_value_site_pv, #busuanzi_value_site_uv');
  
  const counterObserver = new IntersectionObserver(function(entries) {
    observers.push(counterObserver);
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate');
        setTimeout(function() {
          entry.target.classList.remove('animate');
        }, 300);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(function(counter) {
    counter.classList.add('counter');
    counterObserver.observe(counter);
  });

  /* 5. 主题色横条 - 动态添加到各板块 */
  const sections = document.querySelectorAll('.home-collapsible');
  
  sections.forEach(function(section) {
    const header = section.querySelector('.home-collapsible-header');
    if (header && !header.querySelector('.theme-color-bar')) {
      const bar = document.createElement('div');
      bar.classList.add('theme-color-bar');
      
      // 根据板块类型设置颜色
      const sectionId = section.id;
      if (sectionId.includes('herbs')) {
        bar.style.background = 'linear-gradient(90deg, #107c10, #4caf50)';
      } else if (sectionId.includes('life')) {
        bar.style.background = 'linear-gradient(90deg, #ff8c00, #ffb900)';
      } else if (sectionId.includes('tech')) {
        bar.style.background = 'linear-gradient(90deg, #0078d4, #4da6e8)';
      } else if (sectionId.includes('pop')) {
        bar.style.background = 'linear-gradient(90deg, #6b69d6, #9c27b0)';
      }
      
      header.insertBefore(bar, header.firstChild);
    }
  });

  /* 6. 平滑滚动增强 */
  document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  /* 7. 卡片点击反馈 - 触摸设备优化 */
  document.querySelectorAll('.tile').forEach(function(tile) {
    let isTouchDevice = 'ontouchstart' in window;
    
    if (isTouchDevice) {
      // 触摸设备：使用 touchstart 和 touchend
      tile.addEventListener('touchstart', function() {
        this.style.transform = 'translateY(-4px) scale(0.98)';
      });
      
      tile.addEventListener('touchend', function() {
        setTimeout(function() {
          tile.style.transform = '';
        }, 150);
      });
    } else {
      // 桌面设备：保留 hover 效果
      tile.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-8px) scale(1.02)';
      });
      
      tile.addEventListener('mouseleave', function() {
        this.style.transform = '';
      });
    }
  });

  /* 8. 数字滚动动画 - 从不蒜子获取真实数据 */
  function animateNumbers(targetValue, el) {
    const duration = 1500; // 1.5秒
    const step = targetValue / (duration / 16); // 60fps
    let current = 0;

    const timer = setInterval(function() {
      current += step;
      if (current >= targetValue) {
        current = targetValue;
        clearInterval(timer);
      }
      el.textContent = Math.floor(current);
    }, 16);
  }

  // 等待不蒜子数据加载
  function waitForBusuanzi() {
    const pvEl = document.getElementById('busuanzi_value_site_pv');
    const uvEl = document.getElementById('busuanzi_value_site_uv');
    
    // 检查不蒜子是否已加载数据
    if (pvEl && pvEl.textContent !== '' && pvEl.textContent !== '0') {
      // 不蒜子已加载，更新统计数据
      const statNumbers = document.querySelectorAll('.stat-number');
      statNumbers.forEach(function(el) {
        const label = el.nextElementSibling;
        if (label && label.textContent.includes('访问')) {
          // 次访问
          const pv = parseInt(pvEl.textContent.replace(/,/g, ''));
          if (!isNaN(pv)) {
            animateNumbers(pv, el);
          }
        } else if (label && label.textContent.includes('访客')) {
          // 位访客
          const uv = parseInt(uvEl.textContent.replace(/,/g, ''));
          if (!isNaN(uv)) {
            animateNumbers(uv, el);
          }
        }
      });
    } else {
      // 不蒜子未加载，500ms后重试
      setTimeout(waitForBusuanzi, 500);
    }
  }

  // 进入视口时触发
  const statsObserver = new IntersectionObserver(function(entries) {
    observers.push(statsObserver);
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        // 开始等待不蒜子数据
        waitForBusuanzi();
        statsObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  const statsEl = document.querySelector('.site-stats');
  if (statsEl) statsObserver.observe(statsEl);

  /* 6. 板块/页面计数器动画 - 基于 data-target 属性 */
  const targetCounters = document.querySelectorAll('.stat-number[data-target]');
  
  const targetCounterObserver = new IntersectionObserver(function(entries) {
    observers.push(targetCounterObserver);
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.getAttribute('data-target'));
        if (!isNaN(target) && target > 0) {
          animateNumbers(target, el);
        }
        targetCounterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  targetCounters.forEach(function(counter) {
    targetCounterObserver.observe(counter);
  });

  console.log('✨ 首页动画效果已加载（含触屏适配）');

  // 页面卸载时清理所有 Observer（防止内存泄漏）
  window.addEventListener('pagehide', function() {
    observers.forEach(function(observer) {
      if (observer && typeof observer.disconnect === 'function') {
        observer.disconnect();
      }
    });
    console.log('🧹 Observers 已清理');
  });
});
