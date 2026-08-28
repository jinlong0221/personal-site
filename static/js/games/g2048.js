(function () {
  var wrap = document.getElementById('game-g2048');
  if (!wrap) return;
  var grid = wrap.querySelector('.g24-grid');
  var scoreEl = wrap.querySelector('.gc-score-val');
  var bestEl = wrap.querySelector('.gc-best-val');
  var startBtn = wrap.querySelector('.gc-start');
  var hint = wrap.querySelector('.gc-hint');

  var SIZE = 4;
  var board, score, best = 0;
  try { best = parseInt(localStorage.getItem('arcade_2048_best') || '0', 10) || 0; } catch (e) {}
  if (bestEl) bestEl.textContent = best;

  var cells = [];
  for (var i = 0; i < SIZE * SIZE; i++) {
    var c = document.createElement('div');
    c.className = 'g24-cell';
    grid.appendChild(c);
    cells.push(c);
  }

  function render() {
    for (var i = 0; i < SIZE * SIZE; i++) {
      var v = board[i];
      var c = cells[i];
      c.textContent = v ? v : '';
      c.className = 'g24-cell' + (v ? ' v' + Math.min(12, Math.round(Math.log2(v))) : '');
      c.setAttribute('data-v', v || '');
    }
    scoreEl.textContent = score;
  }

  function emptyCells() {
    var e = [];
    for (var i = 0; i < board.length; i++) if (!board[i]) e.push(i);
    return e;
  }

  function addTile() {
    var e = emptyCells();
    if (!e.length) return;
    var idx = e[(Math.random() * e.length) | 0];
    board[idx] = Math.random() < 0.9 ? 2 : 4;
  }

  function reset() {
    board = new Array(SIZE * SIZE).fill(0);
    score = 0;
    addTile(); addTile();
    render();
  }

  function slide(row) {
    var arr = row.filter(function (x) { return x; });
    for (var i = 0; i < arr.length - 1; i++) {
      if (arr[i] === arr[i + 1]) { arr[i] *= 2; score += arr[i]; arr.splice(i + 1, 1); }
    }
    while (arr.length < SIZE) arr.push(0);
    return arr;
  }

  function rotate() {
    var n = SIZE, b = board.slice();
    for (var r = 0; r < n; r++) for (var c = 0; c < n; c++) board[c * n + (n - 1 - r)] = b[r * n + c];
  }

  function move(dir) {
    var before = board.slice();
    for (var t = 0; t < dir; t++) rotate();
    for (var r = 0; r < SIZE; r++) {
      var row = [];
      for (var c = 0; c < SIZE; c++) row.push(board[r * SIZE + c]);
      var slid = slide(row);
      for (var c2 = 0; c2 < SIZE; c2++) board[r * SIZE + c2] = slid[c2];
    }
    for (var t2 = 0; t2 < (4 - dir) % 4; t2++) rotate();
    if (board.join() !== before.join()) {
      addTile();
      if (score > best) { best = score; bestEl.textContent = best; try { localStorage.setItem('arcade_2048_best', best); } catch (e) {} }
      render();
      if (isOver() && hint) hint.textContent = '没地方走啦，本局得分 ' + score;
    }
  }

  function isOver() {
    if (emptyCells().length) return false;
    for (var r = 0; r < SIZE; r++) for (var c = 0; c < SIZE; c++) {
      var v = board[r * SIZE + c];
      if (c < SIZE - 1 && board[r * SIZE + c + 1] === v) return false;
      if (r < SIZE - 1 && board[(r + 1) * SIZE + c] === v) return false;
    }
    return true;
  }

  function onKey(e) {
    if (wrap.offsetParent === null) return;
    var k = e.key;
    var map = { ArrowUp: 0, ArrowRight: 1, ArrowDown: 2, ArrowLeft: 3, w: 0, d: 1, s: 2, a: 3, W: 0, D: 1, S: 2, A: 3 };
    if (!(k in map)) return;
    e.preventDefault();
    move(map[k]);
  }

  var tsx = 0, tsy = 0;
  grid.addEventListener('touchstart', function (e) { var t = e.touches[0]; tsx = t.clientX; tsy = t.clientY; }, { passive: true });
  grid.addEventListener('touchend', function (e) {
    var t = e.changedTouches[0]; var dx = t.clientX - tsx, dy = t.clientY - tsy;
    if (Math.abs(dx) < 20 && Math.abs(dy) < 20) return;
    if (Math.abs(dx) > Math.abs(dy)) move(dx > 0 ? 1 : 3); else move(dy > 0 ? 2 : 0);
  }, { passive: true });

  document.addEventListener('keydown', onKey);
  startBtn.addEventListener('click', function () { reset(); if (hint) hint.textContent = '方向键 / 滑动合并相同数字，凑出 2048'; });

  reset();
  if (hint) hint.textContent = '方向键 / 滑动合并相同数字，凑出 2048';
})();
