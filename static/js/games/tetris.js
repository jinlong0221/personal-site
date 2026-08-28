// 俄罗斯方块：方向键/触屏控制，消行计分，结束记录最高分
window.initTetris = function () {
  var root = document.getElementById('game-tetris');
  if (!root || root.dataset.inited) return;
  root.dataset.inited = '1';

  var canvas = root.querySelector('.tt-canvas');
  var ctx = canvas.getContext('2d');
  var nextCv = root.querySelector('.tt-next');
  var nctx = nextCv.getContext('2d');
  var scoreEl = root.querySelector('.tt-score');
  var levelEl = root.querySelector('.tt-level');
  var linesEl = root.querySelector('.tt-lines');
  var msg = root.querySelector('.tt-msg');
  var pauseBtn = root.querySelector('.tt-pause');

  var COLS = 10, ROWS = 20, CELL = 24;
  var dpr = window.devicePixelRatio || 1;
  canvas.width = COLS * CELL * dpr; canvas.height = ROWS * CELL * dpr;
  nextCv.width = 4 * CELL * dpr; nextCv.height = 4 * CELL * dpr;

  var COLORS = ['', '#5ad1c8', '#f0a04b', '#e85d75', '#7b6cf0', '#f0d04b', '#5ab0f0', '#9bdc52'];
  var SHAPES = [
    null,
    [[1,1,1,1]],                         // I
    [[1,1],[1,1]],                       // O
    [[0,1,0],[1,1,1]],                   // T
    [[1,0,0],[1,1,1]],                   // J
    [[0,0,1],[1,1,1]],                   // L
    [[0,1,1],[1,1,0]],                   // S
    [[1,1,0],[0,1,1]]                    // Z
  ];

  var grid, cur, next, score, level, lines, over, paused, dropTimer, speed;

  function setBest() { if (window.refreshArcadeBest) window.refreshArcadeBest(); }

  function emptyGrid() {
    var g = []; for (var r = 0; r < ROWS; r++) { g.push([]); for (var c = 0; c < COLS; c++) g[r].push(0); }
    return g;
  }

  function randShape() { return Math.floor(Math.random() * 7) + 1; }

  function spawn() {
    cur = { type: next || randShape(), x: 3, y: 0 };
    next = randShape();
    drawNext();
    if (collide(cur.x, cur.y, SHAPES[cur.type])) { gameOver(); }
  }

  function collide(x, y, mat) {
    for (var r = 0; r < mat.length; r++) for (var c = 0; c < mat[r].length; c++) {
      if (!mat[r][c]) continue;
      var nx = x + c, ny = y + r;
      if (nx < 0 || nx >= COLS || ny >= ROWS) return true;
      if (ny >= 0 && grid[ny][nx]) return true;
    }
    return false;
  }

  function rotate() {
    var m = SHAPES[cur.type];
    var N = m.length, M = m[0].length;
    var rot = []; for (var r = 0; r < M; r++) { rot.push([]); for (var c = 0; c < N; c++) rot[r].push(m[N - 1 - c][r]); }
    if (!collide(cur.x, cur.y, rot)) { SHAPES[cur.type] = rot; }
  }

  function move(dx) { if (!collide(cur.x + dx, cur.y, SHAPES[cur.type])) cur.x += dx; }

  function drop() {
    if (!collide(cur.x, cur.y + 1, SHAPES[cur.type])) { cur.y++; return true; }
    lock(); return false;
  }

  function hardDrop() {
    while (drop()) {}
    draw();
  }

  function lock() {
    var m = SHAPES[cur.type];
    for (var r = 0; r < m.length; r++) for (var c = 0; c < m[r].length; c++) {
      if (m[r][c]) { var ny = cur.y + r; if (ny >= 0) grid[ny][cur.x + c] = cur.type; }
    }
    clearLines();
    spawn();
  }

  function clearLines() {
    var cleared = 0;
    for (var r = ROWS - 1; r >= 0; r--) {
      var full = true;
      for (var c = 0; c < COLS; c++) if (!grid[r][c]) { full = false; break; }
      if (full) { grid.splice(r, 1); grid.unshift(new Array(COLS).fill(0)); cleared++; r++; }
    }
    if (cleared) {
      var pts = [0, 100, 300, 500, 800][cleared] * level;
      score += pts; lines += cleared; level = Math.floor(lines / 10) + 1;
      speed = Math.max(120, 800 - (level - 1) * 70);
      restartTimer();
      scoreEl.textContent = score; levelEl.textContent = level; linesEl.textContent = lines;
    }
  }

  function drawCell(g, x, y, t) {
    g.fillStyle = COLORS[t] || '#333';
    g.fillRect(x * CELL + 1, y * CELL + 1, CELL - 2, CELL - 2);
  }

  function draw() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#14110f'; ctx.fillRect(0, 0, COLS * CELL, ROWS * CELL);
    for (var r = 0; r < ROWS; r++) for (var c = 0; c < COLS; c++) if (grid[r][c]) drawCell(ctx, c, r, grid[r][c]);
    if (cur) {
      var m = SHAPES[cur.type];
      for (var r2 = 0; r2 < m.length; r2++) for (var c2 = 0; c2 < m[r2].length; c2++) {
        if (m[r2][c2]) { var ny = cur.y + r2; if (ny >= 0) drawCell(ctx, cur.x + c2, ny, cur.type); }
      }
    }
  }

  function drawNext() {
    nctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    nctx.fillStyle = '#14110f'; nctx.fillRect(0, 0, 4 * CELL, 4 * CELL);
    var m = SHAPES[next], off = (4 - m[0].length) / 2;
    for (var r = 0; r < m.length; r++) for (var c = 0; c < m[r].length; c++) {
      if (m[r][c]) { nctx.fillStyle = COLORS[next]; nctx.fillRect((c + off) * CELL + 1, (r + 1) * CELL + 1, CELL - 2, CELL - 2); }
    }
  }

  function loop() { if (!over && !paused) { if (!drop()) {} draw(); } }

  function restartTimer() {
    if (dropTimer) clearInterval(dropTimer);
    dropTimer = setInterval(loop, speed);
  }

  function gameOver() {
    over = true; clearInterval(dropTimer);
    var isNew = window.Visitor ? window.Visitor.record('tetris', score, { higherBetter: true }) : false;
    msg.textContent = '游戏结束 · 得分 ' + score + (isNew ? '（新纪录！）' : '');
    setBest();
  }

  function newGame() {
    grid = emptyGrid(); score = 0; level = 1; lines = 0; over = false; paused = false;
    speed = 800; next = randShape();
    if (pauseBtn) pauseBtn.textContent = '⏸';
    scoreEl.textContent = 0; levelEl.textContent = 1; linesEl.textContent = 0; msg.textContent = '';
    spawn(); draw(); restartTimer();
  }

  function togglePause() {
    if (over) return;
    paused = !paused;
    if (pauseBtn) pauseBtn.textContent = paused ? '▶' : '⏸';
    msg.textContent = paused ? '已暂停' : '';
  }

  // 键盘（仅本 tab 激活时）
  document.addEventListener('keydown', function (e) {
    if (window.__activeGame !== 'tetris' || over || paused) return;
    var k = e.key;
    if (k === 'ArrowLeft') { move(-1); draw(); }
    else if (k === 'ArrowRight') { move(1); draw(); }
    else if (k === 'ArrowUp') { rotate(); draw(); }
    else if (k === 'ArrowDown') { drop(); draw(); }
    else if (k === ' ') { e.preventDefault(); hardDrop(); draw(); }
    else if (k === 'p' || k === 'P') { togglePause(); }
    else return;
    e.preventDefault();
  });

  // 触屏按钮
  root.querySelector('.tt-left').addEventListener('click', function () { if (!over && !paused) { move(-1); draw(); } });
  root.querySelector('.tt-right').addEventListener('click', function () { if (!over && !paused) { move(1); draw(); } });
  root.querySelector('.tt-rot').addEventListener('click', function () { if (!over && !paused) { rotate(); draw(); } });
  root.querySelector('.tt-down').addEventListener('click', function () { if (!over && !paused) { drop(); draw(); } });
  root.querySelector('.tt-hard').addEventListener('click', function () { if (!over && !paused) { hardDrop(); draw(); } });
  if (pauseBtn) pauseBtn.addEventListener('click', togglePause);
  root.querySelector('.tt-restart').addEventListener('click', newGame);

  newGame();
  setBest();
};
