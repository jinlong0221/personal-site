(function () {
  var tabs = document.querySelectorAll('.arcade-tab');
  var panels = document.querySelectorAll('.game-panel');
  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      var name = t.getAttribute('data-tab');
      tabs.forEach(function (x) { x.classList.toggle('active', x === t); });
      panels.forEach(function (p) {
        p.classList.toggle('active', p.getAttribute('data-panel') === name);
      });
    });
  });
})();
