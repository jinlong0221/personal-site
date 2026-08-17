(function () {
  'use strict';

  var ROTATE_MS = 7000;

  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else { fn(); }
  }

  function init() {
    var hero = document.querySelector('.lx-hero');
    var link = document.getElementById('heroLink');
    var imgA = document.getElementById('heroImgA');
    var imgB = document.getElementById('heroImgB');
    var kicker = document.getElementById('heroKicker');
    var title = document.getElementById('heroTitle');
    var sub = document.getElementById('heroSub');
    var cta = document.getElementById('heroCta');
    var dotsWrap = document.getElementById('heroDots');
    if (!hero || !link || !imgA || !imgB || !dotsWrap) return;

    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    fetch('/hero.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error('bad'); return r.json(); })
      .then(function (slides) {
        if (!slides || !slides.length) throw new Error('empty');
        setup(slides);
      })
      .catch(function () { /* 拉取失败则保留静态首屏，不报错 */ });

    function setup(slides) {
      // 预加载全部图片，避免切换时闪烁
      slides.forEach(function (s) { var im = new Image(); im.src = s.img; });

      var idx = 0;
      var cur = imgA, nxt = imgB; // 两层交替
      var timer = null;
      var hovering = false;

      slides.forEach(function (s, i) {
        var b = document.createElement('button');
        b.className = 'lx-hero-dot' + (i === 0 ? ' is-active' : '');
        b.type = 'button';
        b.setAttribute('role', 'tab');
        b.setAttribute('aria-label', (s.kicker || ('专题 ' + (i + 1))));
        b.addEventListener('click', function (e) { e.preventDefault(); go(i, true); });
        dotsWrap.appendChild(b);
      });
      var dots = dotsWrap.querySelectorAll('.lx-hero-dot');

      function apply(s) {
        link.setAttribute('href', s.link || '#');
        link.setAttribute('aria-label', (s.kicker || '') + (s.title ? '：' + s.title : ''));
        kicker.textContent = s.kicker || '';
        title.textContent = s.title || '';
        sub.textContent = s.sub || '';
        cta.textContent = s.cta || '查看专题 →';
        if (cur) cur.setAttribute('alt', (s.kicker || s.title || ''));
      }

      function swap() {
        nxt.classList.add('is-active');
        cur.classList.remove('is-active');
        var t = cur; cur = nxt; nxt = t; // 交换：cur 始终为可见层
      }

      function paint(s) {
        apply(s);
        if (reduce) {
          nxt.src = s.img; swap(); return;
        }
        nxt.removeAttribute('src');
        nxt.src = s.img;
        if (nxt.decode) {
          nxt.decode().then(swap).catch(swap);
        } else {
          nxt.onload = swap; nxt.onerror = swap;
        }
      }

      function go(n, manual) {
        n = (n + slides.length) % slides.length;
        if (n === idx) return;
        idx = n;
        paint(slides[idx]);
        for (var i = 0; i < dots.length; i++) {
          dots[i].classList.toggle('is-active', i === idx);
        }
        if (manual) restart();
      }

      function start() {
        if (timer || hovering || document.hidden) return;
        timer = setInterval(function () { go(idx + 1); }, ROTATE_MS);
      }
      function stop() { if (timer) { clearInterval(timer); timer = null; } }
      function restart() { stop(); start(); }

      hero.addEventListener('mouseenter', function () { hovering = true; stop(); });
      hero.addEventListener('mouseleave', function () { hovering = false; start(); });
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) stop(); else start();
      });
      // 首屏即启动自动轮播
      start();
    }
  }

  ready(init);
})();
