/* join.html 星球入口交互：先复制星球名到剪贴板，再尝试打开知识星球 */
(function () {
  'use strict';

  var PLANET_NAME = '龙兄私房-硬核爱好避坑圈';
  var btn = document.getElementById('joinBtn');
  if (!btn) return;

  function showToast(text) {
    var id = 'join-toast';
    var old = document.getElementById(id);
    if (old) old.remove();

    var el = document.createElement('div');
    el.id = id;
    el.textContent = text;
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    el.style.cssText = 'position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#191510;color:#E0C97A;border:1px solid #C9A84C;border-radius:999px;padding:10px 22px;font-size:.9rem;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,.4);opacity:0;transition:opacity .25s;pointer-events:none;';
    document.body.appendChild(el);

    requestAnimationFrame(function () {
      el.style.opacity = '1';
      setTimeout(function () {
        el.style.opacity = '0';
        setTimeout(function () { el.remove(); }, 260);
      }, 2200);
    });
  }

  function copyName() {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(PLANET_NAME);
    }
    var ta = document.createElement('textarea');
    ta.value = PLANET_NAME;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
    } catch (e) {
      // ignore
    }
    document.body.removeChild(ta);
    return Promise.resolve();
  }

  btn.addEventListener('click', function (e) {
    e.preventDefault();
    copyName().then(function () {
      showToast('已复制星球名，打开知识星球 App 搜索即可加入');
      // 同时尝试打开知识星球（网页/小程序入口），手机端可能唤起 App
      setTimeout(function () {
        window.open('https://wx.zsxq.com/', '_blank', 'noopener,noreferrer');
      }, 400);
    }).catch(function () {
      showToast('复制失败，请手动复制上方星球名');
    });
  });
})();
