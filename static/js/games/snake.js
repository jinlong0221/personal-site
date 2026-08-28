(function () {
  var wrap = document.getElementById('game-snake');
  if (!wrap) return;
  var canvas = wrap.querySelector('.gc-canvas');
  var ctx = canvas.getContext('2d');
  var scoreEl = wrap.querySelector('.gc-score-val');
  var bestEl = wrap.querySelector('.gc-best-val');
  var startBtn = wrap.querySelector('.gc-start');
  var hint = wrap.querySelector('.gc-hint');

  var GRID = 20, CELL = 15, W = GRID * CELL;
  var dpr = window.devicePixelRatio || 1;
  canvas.width = W * dpr; canvas.height = W * dpr;
  canvas.style.width = W + 'px'; canvas.style.height = W + 'px';
  ctx.scale(dpr, dpr);

  var snake, dir, nextDir, food, score, timer, running = false;
  var best = 0;
  try { best = parseInt(localStorage.getItem('arcade_snake_best') || '0', 10) || 0; } catch (e) {}
  bestEl.textContent = best;

  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function placeFood() {
    while (true) {
      var f = { x: (Math.random() * GRID) | 0, y: (Math.random() * GRID) | 0 };
      if (!snake.some(function (s) { return s.x === f.x && s.y === f.y; })) { food = f; return; }
    }
  }

  function reset() {
    snake = [{ x: 9, y: 10 }, { x: 8, y: 10 }, { x: 7, y: 10 }];
    dir = { x: 1, y: 0 }; nextDir = { x: 1, y: 0 };
    score = 0; scoreEl.textContent = '0';
    placeFood(); draw();
  }

  function step() {
    dir = nextDir;
    var head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };
    if (head.x < 0 || head.x >= GRID || head.y < 0 || head.y >= GRID ||
        snake.some(function (s) { return s.x === head.x && s.y === head.y; })) {
      return gameOver();
    }
    snake.unshift(head);
    if (head.x === food.x && head.y === food.y) {
      score++; scoreEl.textContent = score; placeFood();
    } else {
      snake.pop();
    }
    draw();
  }

  function draw() {
    ctx.fillStyle = css('--bg-secondary') || '#191510';
    ctx.fillRect(0, 0, W, W);
    ctx.strokeStyle = 'rgba(201,168,76,0.07)';
    ctx.lineWidth = 1;
    for (var i = 0; i <= GRID; i++) {
      ctx.beginPath(); ctx.moveTo(i * CELL, 0); ctx.lineTo(i * CELL, W); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * CELL); ctx.lineTo(W, i * CELL); ctx.stroke();
    }
    ctx.fillStyle = '#D14A36';
    roundRect(food.x * CELL + 2, food.y * CELL + 2, CELL - 4, CELL - 4, 4); ctx.fill();
    snake.forEach(function (s, idx) {
      ctx.fillStyle = idx === 0 ? '#E0C97A' : '#C9A84C';
      roundRect(s.x * CELL + 1, s.y * CELL + 1, CELL - 2, CELL - 2, 4); ctx.fill();
    });
  }

  function gameOver() {
    running = false; clearInterval(timer);
    if (score > best) { best = score; bestEl.textContent = best; try { localStorage.setItem('arcade_snake_best', best); } catch (e) {} }
    startBtn.textContent = '再来一局';
    if (hint) hint.textContent = '撞墙或咬到自己啦，本局得分 ' + score;
  }

  function start() {
    reset(); running = true; startBtn.textContent = '重新开始';
    if (hint) hint.textContent = '方向键 / 滑动屏幕控制方向';
    clearInterval(timer); timer = setInterval(step, 110);
  }

  function setDir(x, y) {
    if (!running || wrap.offsetParent === null) return;
    if (x === -dir.x && y === -dir.y) return;
    nextDir = { x: x, y: y };
  }

  document.addEventListener('keydown', function (e) {
    if (!running || wrap.offsetParent === null) return;
    var k = e.key;
    if (k === 'ArrowUp' || k === 'w' || k === 'W') setDir(0, -1);
    else if (k === 'ArrowDown' || k === 's' || k === 'S') setDir(0, 1);
    else if (k === 'ArrowLeft' || k === 'a' || k === 'A') setDir(-1, 0);
    else if (k === 'ArrowRight' || k === 'd' || k === 'D') setDir(1, 0);
    else return;
    e.preventDefault();
  });

  var tsx = 0, tsy = 0;
  canvas.addEventListener('touchstart', function (e) { var t = e.touches[0]; tsx = t.clientX; tsy = t.clientY; }, { passive: true });
  canvas.addEventListener('touchend', function (e) {
    if (!running) return;
    var t = e.changedTouches[0]; var dx = t.clientX - tsx, dy = t.clientY - tsy;
    if (Math.abs(dx) > Math.abs(dy)) setDir(dx > 0 ? 1 : -1, 0); else setDir(0, dy > 0 ? 1 : -1);
  }, { passive: true });

  startBtn.addEventListener('click', start);
  reset(); running = false;
  if (hint) hint.textContent = '点「开始」，用方向键或滑动屏幕来玩';
})();
