/**
 * lightbox.js - 全站统一灯箱
 * 触发方式: <img data-lightbox data-caption="说明" src="...">
 * 或: <div data-lightbox data-src="大图" data-caption="说明"><img src="小图"></div>
 */
(function() {
  'use strict';

  // 创建灯箱 DOM（单例）
  function createLightbox() {
    if (document.getElementById('site-lightbox')) return;
    var lb = document.createElement('div');
    lb.id = 'site-lightbox';
    lb.className = 'site-lightbox';
    lb.innerHTML =
      '<div class="lb-backdrop"></div>' +
      '<button class="lb-btn lb-prev" aria-label="上一张">&#10094;</button>' +
      '<button class="lb-btn lb-next" aria-label="下一张">&#10095;</button>' +
      '<button class="lb-btn lb-close" aria-label="关闭">&#10005;</button>' +
      '<div class="lb-stage">' +
        '<img class="lb-img" src="" alt="">' +
        '<div class="lb-caption"></div>' +
      '</div>' +
      '<div class="lb-counter"></div>';
    document.body.appendChild(lb);

    var img = lb.querySelector('.lb-img');
    var caption = lb.querySelector('.lb-caption');
    var backdrop = lb.querySelector('.lb-backdrop');
    var prevBtn = lb.querySelector('.lb-prev');
    var nextBtn = lb.querySelector('.lb-next');
    var closeBtn = lb.querySelector('.lb-close');
    var counter = lb.querySelector('.lb-counter');

    var items = [];  // [{src, caption, el}]
    var index = 0;

    // 收集所有触发器
    function collect() {
      items = [];
      document.querySelectorAll('[data-lightbox]').forEach(function(el) {
        var src = el.dataset.src || (el.tagName === 'IMG' ? el.src : el.querySelector('img') ? el.querySelector('img').src : '');
        var caption = el.dataset.caption || el.title || '';
        if (src) items.push({ src: src, caption: caption, el: el });
      });
    }

    function show(idx) {
      if (!items.length) return;
      index = ((idx % items.length) + items.length) % items.length;
      var item = items[index];
      img.src = item.src;
      img.alt = item.caption;
      caption.textContent = item.caption;
      counter.textContent = items.length > 1 ? (index + 1) + ' / ' + items.length : '';
      prevBtn.style.display = items.length > 1 ? '' : 'none';
      nextBtn.style.display = items.length > 1 ? '' : 'none';
      lb.classList.add('active');
      document.body.style.overflow = 'hidden';
      // 预加载相邻图片
      [index - 1, index + 1].forEach(function(i) {
        var ii = ((i % items.length) + items.length) % items.length;
        if (ii !== index) new Image().src = items[ii].src;
      });
    }

    function close() {
      lb.classList.remove('active');
      document.body.style.overflow = '';
      img.src = '';
    }

    function prev() { show(index - 1); }
    function next() { show(index + 1); }

    // 点击空白/按钮关闭
    backdrop.addEventListener('click', close);
    closeBtn.addEventListener('click', close);
    prevBtn.addEventListener('click', prev);
    nextBtn.addEventListener('click', next);

    // 键盘
    document.addEventListener('keydown', function(e) {
      if (!lb.classList.contains('active')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') prev();
      if (e.key === 'ArrowRight') next();
    });

    // Touch swipe
    var touchStartX = 0;
    lb.addEventListener('touchstart', function(e) { touchStartX = e.touches[0].clientX; }, { passive: true });
    lb.addEventListener('touchend', function(e) {
      var dx = e.changedTouches[0].clientX - touchStartX;
      if (Math.abs(dx) > 50) dx < 0 ? next() : prev();
    });

    // 点击图片放大（双击或 pinch 暂不实现，用 CSS 缩放）
    var scale = 1;
    img.addEventListener('click', function(e) {
      if (scale === 1) {
        scale = 2;
        img.style.transform = 'scale(2)';
        img.style.cursor = 'zoom-out';
      } else {
        scale = 1;
        img.style.transform = '';
        img.style.cursor = 'zoom-in';
      }
      e.stopPropagation();
    });

    // 代理点击事件
    document.addEventListener('click', function(e) {
      var el = e.target.closest('[data-lightbox]');
      if (el) {
        e.preventDefault();
        collect();
        show(items.findIndex(function(i) { return i.el === el; }));
      }
    });

    collect();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createLightbox);
  } else {
    createLightbox();
  }
})();
