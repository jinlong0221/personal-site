/* 苹果板块分栏切换：一次只显示一类内容，页面不再一眼望不到头。
   降级设计：本脚本没跑起来时 .ap-tabs-on 不会被加上，
   四个面板全部保持展开，内容一张不丢（只是没有分栏）。 */
(function () {
  var tabs = document.querySelectorAll('.ap-tab');
  var panels = document.querySelectorAll('.ap-panel');
  if (!tabs.length || !panels.length) return;

  document.documentElement.classList.add('ap-tabs-on');

  function activate(name, syncHash) {
    var i;
    for (i = 0; i < tabs.length; i++) {
      var t = tabs[i];
      var on = t.getAttribute('data-target') === name;
      t.classList.toggle('is-active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
    }
    for (i = 0; i < panels.length; i++) {
      var p = panels[i];
      p.classList.toggle('is-active', p.getAttribute('data-panel') === name);
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

  for (var i = 0; i < tabs.length; i++) {
    tabs[i].addEventListener('click', function () {
      activate(this.getAttribute('data-target'), true);
    });
    tabs[i].addEventListener('keydown', function (e) {
      var k = e.key;
      if (k !== 'ArrowRight' && k !== 'ArrowLeft') return;
      var idx = idxOf(this);
      if (idx < 0) return;
      e.preventDefault();
      var next = (idx + (k === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length;
      tabs[next].focus();
      activate(tabs[next].getAttribute('data-target'), true);
    });
  }

  var m = /^#tab-(new|gallery|spec|price)$/.exec(window.location.hash);
  activate(m ? m[1] : 'new', false);
})();
