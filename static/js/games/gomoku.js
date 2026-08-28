// 五子棋：玩家执黑先手，电脑执白。胜利累计记录胜场
window.initGomoku = function () {
  var root = document.getElementById('game-gomoku');
  if (!root || root.dataset.inited) return;
  root.dataset.inited = '1';

  var canvas = root.querySelector('.gm-canvas');
  var ctx = canvas.getContext('2d');
  var msg = root.querySelector('.gm-msg');
  var restart = root.querySelector('.gm-restart');

  var N = 15;               // 交叉点数
  var PAD = 20, GAP = 28;   // 边距、格距
  var SIZE = PAD * 2 + GAP * (N - 1);
  canvas.width = SIZE; canvas.height = SIZE;

  var board, over, myTurn;
  var EMPTY = 0, BLACK = 1, WHITE = 2;
  var winCount = (window.Visitor && window.Visitor.getBest('gomoku')) ? window.Visitor.getBest('gomoku').score : 0;

  function setBest() { if (window.refreshArcadeBest) window.refreshArcadeBest(); }

  function draw() {
    ctx.clearRect(0, 0, SIZE, SIZE);
    // 木色底
    ctx.fillStyle = '#e8c98f';
    ctx.fillRect(0, 0, SIZE, SIZE);
    // 网格
    ctx.strokeStyle = '#7a5a32'; ctx.lineWidth = 1;
    for (var i = 0; i < N; i++) {
      var p = PAD + i * GAP;
      ctx.beginPath(); ctx.moveTo(PAD, p); ctx.lineTo(SIZE - PAD, p); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p, PAD); ctx.lineTo(p, SIZE - PAD); ctx.stroke();
    }
    // 星位
    var stars = [3, 7, 11];
    ctx.fillStyle = '#7a5a32';
    stars.forEach(function (a) { stars.forEach(function (b) {
      ctx.beginPath(); ctx.arc(PAD + a * GAP, PAD + b * GAP, 3, 0, 7); ctx.fill();
    }); });
    // 棋子
    for (var r = 0; r < N; r++) for (var c = 0; c < N; c++) {
      if (board[r][c]) place(r, c, board[r][c]);
    }
  }

  function place(r, c, color) {
    var x = PAD + c * GAP, y = PAD + r * GAP;
    ctx.beginPath(); ctx.arc(x, y, GAP * 0.42, 0, 7);
    if (color === BLACK) { ctx.fillStyle = '#1a1a1a'; }
    else { ctx.fillStyle = '#f4f4f4'; }
    ctx.fill();
    if (color === WHITE) { ctx.strokeStyle = '#999'; ctx.lineWidth = 1; ctx.stroke(); }
  }

  function newGame() {
    board = []; for (var i = 0; i < N; i++) { board.push([]); for (var j = 0; j < N; j++) board[i].push(EMPTY); }
    over = false; myTurn = true;
    msg.textContent = '你执黑，先手落子';
    draw();
  }

  function winAt(r, c, color) {
    var dirs = [[0, 1], [1, 0], [1, 1], [1, -1]];
    for (var d = 0; d < dirs.length; d++) {
      var cnt = 1;
      for (var s = -1; s <= 1; s += 2) {
        var rr = r + dirs[d][0] * s, cc = c + dirs[d][1] * s;
        while (rr >= 0 && rr < N && cc >= 0 && cc < N && board[rr][cc] === color) { cnt++; rr += dirs[d][0]; cc += dirs[d][1]; }
      }
      if (cnt >= 5) return true;
    }
    return false;
  }

  // 评分：评估在(r,c)落 color 的价值
  function score(r, c, color) {
    var dirs = [[0, 1], [1, 0], [1, 1], [1, -1]];
    var total = 0;
    for (var d = 0; d < dirs.length; d++) {
      var cnt = 1, empty = 0;
      for (var s = -1; s <= 1; s += 2) {
        var rr = r + dirs[d][0] * s, cc = c + dirs[d][1] * s;
        while (rr >= 0 && rr < N && cc >= 0 && cc < N) {
          if (board[rr][cc] === color) { cnt++; rr += dirs[d][0]; cc += dirs[d][1]; }
          else if (board[rr][cc] === EMPTY) { empty++; break; }
          else break;
        }
      }
      if (cnt >= 5) total += 100000;
      else if (cnt === 4) total += 10000;
      else if (cnt === 3) total += (empty >= 2 ? 1000 : 100);
      else if (cnt === 2) total += 10;
    }
    return total;
  }

  function aiMove() {
    var best = -1, br = 7, bc = 7, bestScore = -1;
    for (var r = 0; r < N; r++) for (var c = 0; c < N; c++) {
      if (board[r][c] !== EMPTY) continue;
      var s = score(r, c, WHITE) * 1.0 + score(r, c, BLACK) * 1.2; // 重防守
      if (s > bestScore) { bestScore = s; br = r; bc = c; }
    }
    board[br][bc] = WHITE;
    draw();
    if (winAt(br, bc, WHITE)) { over = true; msg.textContent = '电脑赢了，再战一局？'; return; }
    myTurn = true; msg.textContent = '轮到你了';
  }

  function onPlay(e) {
    if (over || !myTurn) return;
    var rect = canvas.getBoundingClientRect();
    var x = (e.clientX - rect.left) * (canvas.width / rect.width);
    var y = (e.clientY - rect.top) * (canvas.height / rect.height);
    var c = Math.round((x - PAD) / GAP), r = Math.round((y - PAD) / GAP);
    if (r < 0 || r >= N || c < 0 || c >= N) return;
    if (board[r][c] !== EMPTY) return;
    board[r][c] = BLACK; draw();
    if (winAt(r, c, BLACK)) {
      over = true; winCount++;
      if (window.Visitor) window.Visitor.record('gomoku', winCount);
      msg.textContent = '🎉 你赢了！胜场 ' + winCount;
      setBest();
      return;
    }
    myTurn = false; msg.textContent = '电脑思考中…';
    setTimeout(aiMove, 250);
  }

  canvas.addEventListener('click', onPlay);
  restart.addEventListener('click', newGame);

  newGame();
  setBest();
};
