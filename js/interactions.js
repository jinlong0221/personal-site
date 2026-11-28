/**
 * interactions.js - 全站交互函数外置
 *
 * 把原先写在各页面内联 <script> 里的折叠/复制等交互逻辑集中到外部文件，
 * 由 script-src 'self' 直接允许执行，不再依赖 CSP 内联哈希白名单。
 * 这样即使任何人改动脚本内容也无需重跑 compute_csp_hashes.py，
 * 彻底消除"内联哈希失效 → 点击无反应"的回归风险（fsd 折叠按钮的同款故障）。
 *
 * 触发方式：页面按钮通过 app.js 事件委托 data-act="X" → window[X]()。
 */
(function () {
  'use strict';

  // 折叠：zisha 紫砂详情卡片（data-act="toggleCollapse"）
  window.toggleCollapse = function (header) {
    var parent = header.parentNode;
    if (parent) parent.classList.toggle('open');
  };

  // 踩坑卡片折叠展开：typhoon（data-act="togglePitfall"，单开互斥）
  window.togglePitfall = function (header) {
    var card = header.closest('.pitfall-card');
    if (!card) return;
    var body = card.querySelector('.pitfall-body');
    if (!body) return;

    var wasOpen = body.classList.contains('open');

    // 关闭其他已展开的卡片
    document.querySelectorAll('.pitfall-body.open').forEach(function (b) {
      b.classList.remove('open');
      var c = b.closest('.pitfall-card');
      if (c) c.classList.remove('expanded');
    });

    // 切换当前卡片
    if (!wasOpen) {
      body.classList.add('open');
      card.classList.add('expanded');
    }
  };

  // 一键复制：心潭天气农事建议（data-act="xwCopy"）
  window.xwCopy = function () {
    var src = document.getElementById('xwCopySrc');
    if (!src) return;
    var text = src.value;
    var btn = document.querySelector('.xw-copy-btn');

    function markDone() {
      if (!btn) return;
      btn.textContent = '✅ 已复制';
      setTimeout(function () { btn.textContent = '📋 一键复制'; }, 2000);
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(markDone);
    } else {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;left:-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      markDone();
    }
  };

  // bfcache：从前进/后退缓存恢复时，强制刷新懒加载图片（zisha 等）
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      document.querySelectorAll('img[loading="lazy"]').forEach(function (img) {
        var src = img.src;
        img.src = '';
        img.src = src + (src.indexOf('?') > -1 ? '&' : '?') + '_t=' + Date.now();
      });
    }
  });
})();
