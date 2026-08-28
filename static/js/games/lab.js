// 游艺厅控制：渲染身份卡、切换游戏标签页、刷新最佳成绩
(function () {
  var GAMES = [
    { key: 'minesweeper', name: '扫雷', init: function () { if (window.initMinesweeper) window.initMinesweeper(); } },
    { key: 'memory',      name: '记忆翻牌', init: function () { if (window.initMemory) window.initMemory(); } },
    { key: 'gomoku',      name: '五子棋', init: function () { if (window.initGomoku) window.initGomoku(); } },
    { key: 'tetris',      name: '俄罗斯方块', init: function () { if (window.initTetris) window.initTetris(); } }
  ];

  function renderVisitor() {
    var v = window.Visitor ? window.Visitor.get() : { name: '访客', id: 0, joinedAt: Date.now() };
    var nm = document.querySelector('.vc-name');
    var id = document.querySelector('.vc-id');
    if (nm) nm.textContent = '江湖雅号 · ' + v.name;
    if (id) id.textContent = '编号 #' + v.id + ' · 结伴于 ' + (window.Visitor ? window.Visitor.dateStr(v.joinedAt) : '');
  }

  window.refreshArcadeBest = function () {
    document.querySelectorAll('[data-best]').forEach(function (el) {
      var key = el.dataset.best;
      var map = {
        minesweeper: { hb: false, unit: '秒' },
        memory: { hb: false, unit: '步' },
        gomoku: { hb: true, unit: '胜' },
        tetris: { hb: true, unit: '分' }
      };
      var opt = map[key] || { hb: true, unit: '' };
      el.textContent = window.Visitor ? window.Visitor.fmt(key, opt) : '暂无记录';
    });
  };

  document.addEventListener('DOMContentLoaded', function () {
    renderVisitor();
    window.refreshArcadeBest();

    var tabs = document.querySelectorAll('.arcade-tab');
    var panels = document.querySelectorAll('.arcade-panel');

    function activate(name) {
      window.__activeGame = name;
      tabs.forEach(function (t) { t.classList.toggle('active', t.dataset.game === name); });
      panels.forEach(function (p) { p.classList.toggle('active', p.dataset.game === name); });
      var g = GAMES.filter(function (x) { return x.key === name; })[0];
      if (g) g.init();
    }

    tabs.forEach(function (t) {
      t.addEventListener('click', function () { activate(t.dataset.game); });
    });

    activate('minesweeper');
  });
})();
