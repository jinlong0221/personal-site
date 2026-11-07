/* 苹果板块分栏切换：一页两级「先分区、再分栏」。
   ── 一级分区：在售新品 / 产品发展史
      （显隐本身由 CSS 单选门控，本脚本只负责「开光」+ 深链 + aria）
   ── 二级分栏：新品半区内部 看新品 / 看图 / 看参数 / 看价格
   降级设计：本脚本没跑起来时 .ahub-on / .ap-tabs-on 都不会被加上，
   两个半区与四个面板全部保持展开，内容一张不丢（只是没有分区切换）。

   深链约定（供 apple-history.html 跳转壳与外部引用使用）：
     #tab-now                      → 在售新品
     #tab-hist                     → 产品发展史
     #tab-new|gallery|spec|price   → 在售新品 + 对应二级分栏
*/
(function () {
  var d = document.documentElement;
  var tabs = document.querySelectorAll('.ap-tab');
  var panels = document.querySelectorAll('.ap-panel');
  var hubRadios = document.querySelectorAll('.ahub-r');
  var halves = document.querySelectorAll('.ahub-half');

  var HALVES = { now: 1, hist: 1 };
  var SUBS = { new: 1, gallery: 1, spec: 1, price: 1 };
  var hasSub = !!(tabs.length && panels.length);
  var hasHub = !!hubRadios.length;

  if (!hasSub && !hasHub) return;
  if (hasSub) d.classList.add('ap-tabs-on');
  if (hasHub) d.classList.add('ahub-on');

  /* ---------------- 一级分区 ---------------- */
  function setHalf(name) {
    var i;
    for (i = 0; i < hubRadios.length; i++) {
      hubRadios[i].checked = hubRadios[i].id === 'ahub-' + name;
    }
    for (i = 0; i < halves.length; i++) {
      halves[i].setAttribute(
        'aria-hidden',
        halves[i].getAttribute('data-half') === name ? 'false' : 'true'
      );
    }
  }

  /* ---------------- 二级分栏 ---------------- */
  function setSub(name) {
    var i, t, p, on;
    for (i = 0; i < tabs.length; i++) {
      t = tabs[i];
      on = t.getAttribute('data-target') === name;
      t.classList.toggle('is-active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
    }
    for (i = 0; i < panels.length; i++) {
      p = panels[i];
      p.classList.toggle('is-active', p.getAttribute('data-panel') === name);
    }
  }

  /* ---------------- 统一入口 ---------------- */
  function go(name, syncHash) {
    if (HALVES[name]) {
      setHalf(name);
      if (hasSub) setSub('new');
    } else if (SUBS[name] && hasSub) {
      setHalf('now');
      setSub(name);
    } else {
      return;
    }
    if (syncHash && window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#tab-' + name);
    }
  }

  function idxOf(el) {
    for (var j = 0; j < tabs.length; j++) {
      if (tabs[j] === el) return j;
    }
    return -1;
  }

  var i;
  for (i = 0; i < tabs.length; i++) {
    tabs[i].addEventListener('click', function () {
      go(this.getAttribute('data-target'), true);
    });
    tabs[i].addEventListener('keydown', function (e) {
      var k = e.key;
      if (k !== 'ArrowRight' && k !== 'ArrowLeft') return;
      var idx = idxOf(this);
      if (idx < 0) return;
      e.preventDefault();
      var next = (idx + (k === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length;
      tabs[next].focus();
      go(tabs[next].getAttribute('data-target'), true);
    });
  }

  for (i = 0; i < hubRadios.length; i++) {
    hubRadios[i].addEventListener('change', function () {
      go(this.id.replace(/^ahub-/, ''), true);
    });
  }

  for (i = 0; i < halves.length; i++) {
    (function (el) {
      var lab = document.querySelector('.ahub-card[for="ahub-' + el.getAttribute('data-half') + '"]');
      if (lab) {
        lab.addEventListener('click', function () {
          go(el.getAttribute('data-half'), true);
        });
      }
    })(halves[i]);
  }

  /* ---------------- 首次进入：吃 URL 上的 hash ---------------- */
  var h = (window.location.hash || '').replace(/^#tab-/, '');
  if (HALVES[h]) go(h, false);
  else if (SUBS[h]) go(h, false);
  else go('now', false);
})();
