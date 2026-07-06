/**
 * share.js - 微信分享弹窗
 * Task 11
 */
(function () {
  var overlayId = 'shareOverlay';
  var QR_API = 'https://api.qrserver.com/v1/create-qr-code/';

  function openShareModal() {
    var existing = document.getElementById(overlayId);
    if (existing) { existing.remove(); }

    var url = window.location.href;
    var title = document.title || '龙兄知识库';
    var qrUrl = QR_API + '?size=200x200&data=' + encodeURIComponent(url);

    var overlay = document.createElement('div');
    overlay.className = 'share-overlay';
    overlay.id = overlayId;
    overlay.innerHTML =
      '<div class="share-panel" role="dialog" aria-label="分享到微信">' +
        '<div class="share-panel-header">' +
          '<span class="share-panel-title">' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="var(--gold)" xmlns="http://www.w3.org/2000/svg">' +
              '<path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 0 1 .598.082l1.584.926a.272.272 0 0 0 .14.047c.134 0 .24-.11.24-.245 0-.06-.024-.12-.038-.177l-.327-1.233a.582.582 0 0 1-.023-.156.49.49 0 0 1 .201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-6.656-6.088V8.87c-.135-.004-.27-.018-.406-.012zm-1.835 2.26c.536 0 .97.44.97.983a.976.976 0 0 1-.97.983.976.976 0 0 1-.97-.983c0-.542.434-.983.97-.983zm4.857 0c.536 0 .97.44.97.983a.976.976 0 0 1-.97.983.976.976 0 0 1-.97-.983c0-.542.434-.983.97-.983z"/>' +
            '</svg>' +
            '分享到微信' +
          '</span>' +
          '<button class="share-close-btn" id="shareCloseBtn" aria-label="关闭">&times;</button>' +
        '</div>' +
        '<div class="share-panel-body">' +
          '<p class="share-qr-label">' + escHtml(title) + '</p>' +
          '<div class="share-qr-wrap">' +
            '<img src="' + qrUrl + '" alt="二维码" width="200" height="200" loading="lazy" onerror="this.style.display=\'none\'">' +
          '</div>' +
          '<div class="share-url-row">' +
            '<textarea class="share-url-input" rows="2" readonly aria-label="页面链接">' + escHtml(url) + '</textarea>' +
            '<button class="share-copy-btn" id="shareCopyBtn">' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>' +
              '复制' +
            '</button>' +
          '</div>' +
          '<p class="share-tip">微信扫码或复制链接后发送给我 → 右上角「三个点」→「分享到朋友圈」</p>' +
        '</div>' +
      '</div>';

    document.body.appendChild(overlay);

    // 动画：requestAnimationFrame 触发重排后加 open
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        overlay.classList.add('open');
      });
    });

    // 关闭事件
    document.getElementById('shareCloseBtn').addEventListener('click', closeShareModal);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeShareModal();
    });

    // 复制按钮
    document.getElementById('shareCopyBtn').addEventListener('click', function () {
      var btn = this;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
          btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已复制';
          btn.classList.add('copied');
          setTimeout(function () {
            btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> 复制';
            btn.classList.remove('copied');
          }, 2000);
        }).catch(function () { fallbackCopy(url, btn); });
      } else {
        fallbackCopy(url, btn);
      }
    });

    // ESC 关闭
    document.addEventListener('keydown', escHandler);
  }

  function closeShareModal() {
    var overlay = document.getElementById(overlayId);
    if (!overlay) return;
    overlay.classList.remove('open');
    overlay.addEventListener('transitionend', function () { overlay.remove(); }, { once: true });
    document.removeEventListener('keydown', escHandler);
  }

  function escHandler(e) {
    if (e.key === 'Escape') closeShareModal();
  }

  function fallbackCopy(text, btn) {
    var ta = document.querySelector('.share-url-input');
    if (ta) { ta.select(); }
    try { document.execCommand('copy'); } catch (err) {}
    btn.textContent = '已复制';
    btn.classList.add('copied');
    setTimeout(function () {
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> 复制';
      btn.classList.remove('copied');
    }, 2000);
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // 绑定按钮（如果有）
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('shareBtn');
    if (btn) {
      btn.addEventListener('click', openShareModal);
    }
  });

  // 暴露给全局（供外链调用）
  window.openShareModal = openShareModal;
})();
