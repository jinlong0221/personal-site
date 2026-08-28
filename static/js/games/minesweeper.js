// 扫雷：左键翻开，右键/长按插旗，胜利记录用时
window.initMinesweeper = function () {
  var root = document.getElementById('game-minesweeper');
  if (!root || root.dataset.inited) return;
  root.dataset.inited = '1';

  var DIFF = {
    easy:   { r: 9,  c: 9,  m: 10 },
    medium: { r: 16, c: 16, m: 40 },
    hard:   { r: 16, c: 30, m: 99 }
  };
  var cur = DIFF.easy;

  var board, revealed, flagged, started, over, timer, secs, revealedCount, longPressTimer, pressedCell;

  var elMines  = root.querySelector('.ms-mines');
  var elTime   = root.querySelector('.ms-time');
  var elFace   = root.querySelector('.ms-face');
  var elGrid   = root.querySelector('.ms-grid');
  var elMsg    = root.querySelector('.ms-msg');

  function setBest() {
    if (window.refreshArcadeBest) window.refreshArcadeBest();
  }

  function newGame(key) {
    if (key) cur = DIFF[key];
    var r = cur.r, c = cur.c, m = cur.m;
    board = []; revealed = []; flagged = [];
    for (var i = 0; i < r; i++) {
      board.push([]); revealed.push([]); flagged.push([]);
      for (var j = 0; j < c; j++) { board[i].push(0); revealed[i].push(false); flagged[i].push(false); }
    }
    // 随机布雷
    var placed = 0;
    while (placed < m) {
      var ri = Math.floor(Math.random() * r), cj = Math.floor(Math.random() * c);
      if (board[ri][cj] !== -1) { board[ri][cj] = -1; placed++; }
    }
    // 计算数字
    for (var i2 = 0; i2 < r; i2++) for (var j2 = 0; j2 < c; j2++) {
      if (board[i2][j2] === -1) continue;
      var n = 0;
      for (var di = -1; di <= 1; di++) for (var dj = -1; dj <= 1; dj++) {
        var ni = i2 + di, nj = j2 + dj;
        if (ni >= 0 && ni < r && nj >= 0 && nj < c && board[ni][nj] === -1) n++;
      }
      board[i2][j2] = n;
    }
    started = false; over = false; secs = 0; revealedCount = 0;
    if (timer) clearInterval(timer);
    elTime.textContent = '000';
    elMines.textContent = String(m).padStart(3, '0');
    elFace.textContent = '🙂';
    elMsg.textContent = '';
    elGrid.style.gridTemplateColumns = 'repeat(' + c + ', 1fr)';
    render();
  }

  function render() {
    elGrid.innerHTML = '';
    for (var i = 0; i < cur.r; i++) for (var j = 0; j < cur.c; j++) {
      var b = document.createElement('button');
      b.className = 'ms-cell';
      b.dataset.r = i; b.dataset.c = j;
      if (revealed[i][j]) {
        b.classList.add('open');
        if (board[i][j] === -1) { b.classList.add('mine'); b.textContent = '💣'; }
        else if (board[i][j] > 0) { b.textContent = board[i][j]; b.dataset.n = board[i][j]; }
      } else if (flagged[i][j]) {
        b.textContent = '🚩';
      }
      elGrid.appendChild(b);
    }
  }

  function startTimer() {
    if (started) return;
    started = true;
    timer = setInterval(function () {
      secs++; if (secs > 999) secs = 999;
      elTime.textContent = String(secs).padStart(3, '0');
    }, 1000);
  }

  function reveal(i, j) {
    if (over || revealed[i][j] || flagged[i][j]) return;
    startTimer();
    if (board[i][j] === -1) { // 踩雷
      over = true; clearInterval(timer);
      revealed[i][j] = true;
      elFace.textContent = '😵';
      // 显示所有雷
      for (var a = 0; a < cur.r; a++) for (var b2 = 0; b2 < cur.c; b2++) if (board[a][b2] === -1) revealed[a][b2] = true;
      render();
      elMsg.textContent = '💥 踩雷了，再来一局？';
      return;
    }
    flood(i, j);
    render();
    checkWin();
  }

  function flood(i, j) {
    var stack = [[i, j]];
    while (stack.length) {
      var p = stack.pop(), ci = p[0], cj = p[1];
      if (ci < 0 || ci >= cur.r || cj < 0 || cj >= cur.c) continue;
      if (revealed[ci][cj] || flagged[ci][cj]) continue;
      revealed[ci][cj] = true; revealedCount++;
      if (board[ci][cj] === 0) {
        for (var di = -1; di <= 1; di++) for (var dj = -1; dj <= 1; dj++) {
          if (di === 0 && dj === 0) continue;
          stack.push([ci + di, cj + dj]);
        }
      }
    }
  }

  function toggleFlag(i, j) {
    if (over || revealed[i][j]) return;
    flagged[i][j] = !flagged[i][j];
    var f = 0; for (var a = 0; a < cur.r; a++) for (var b2 = 0; b2 < cur.c; b2++) if (flagged[a][b2]) f++;
    elMines.textContent = String(cur.m - f).padStart(3, '0');
    render();
  }

  function checkWin() {
    if (revealedCount === cur.r * cur.c - cur.m) {
      over = true; clearInterval(timer);
      elFace.textContent = '😎';
      var isNew = window.Visitor ? window.Visitor.record('minesweeper', secs, { higherBetter: false, unit: '秒' }) : false;
      elMsg.textContent = '🎉 通关！用时 ' + secs + ' 秒' + (isNew ? '（新纪录！）' : '');
      setBest();
    }
  }

  // 事件
  elGrid.addEventListener('click', function (e) {
    var t = e.target.closest('.ms-cell'); if (!t) return;
    if (pressedCell && pressedCell.flagged) return;
    reveal(+t.dataset.r, +t.dataset.c);
  });
  elGrid.addEventListener('contextmenu', function (e) {
    e.preventDefault();
    var t = e.target.closest('.ms-cell'); if (!t) return;
    toggleFlag(+t.dataset.r, +t.dataset.c);
  });
  // 手机长按插旗
  elGrid.addEventListener('touchstart', function (e) {
    var t = e.target.closest('.ms-cell'); if (!t) return;
    var r = +t.dataset.r, c = +t.dataset.c;
    pressedCell = { r: r, c: c, flagged: flagged[r][c] };
    longPressTimer = setTimeout(function () {
      longPressTimer = null;
      toggleFlag(r, c);
      pressedCell = null;
    }, 420);
  }, { passive: true });
  elGrid.addEventListener('touchend', function () {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  });
  elGrid.addEventListener('touchmove', function () {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  });

  root.querySelector('.ms-easy').addEventListener('click', function () { newGame('easy'); });
  root.querySelector('.ms-medium').addEventListener('click', function () { newGame('medium'); });
  root.querySelector('.ms-hard').addEventListener('click', function () { newGame('hard'); });
  elFace.addEventListener('click', function () { newGame(); });

  newGame('easy');
  setBest();
};
