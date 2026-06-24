/* ===== 首页动画效果 JavaScript ===== */

// 等待 DOM 加载完成
document.addEventListener('DOMContentLoaded', function() {

  /* 1. 滚动渐入动画 - 使用 IntersectionObserver */
  const fadeElements = document.querySelectorAll('.tile, .section-block, .home-collapsible');
  
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const fadeObserver = new IntersectionObserver(function(entries) {
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

  console.log('✨ 首页动画效果已加载（含触屏适配）');
});
