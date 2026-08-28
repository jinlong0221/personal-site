// 记忆翻牌（国风）：翻开两张，相同则留住，全部配对完成记录步数
window.initMemory = function () {
  var root = document.getElementById('game-memory');
  if (!root || root.dataset.inited) return;
  root.dataset.inited = '1';

  var ICONS = [
    { e: '🍵', n: '茶' }, { e: '🪷', n: '莲' }, { e: '🀄', n: '棋' },
    { e: '🐉', n: '龙' }, { e: '🏮', n: '灯' }, { e: '🎋', n: '竹' },
    { e: '🌸', n: '梅' }, { e: '🍂', n: '叶' }
  ];

  var grid, msg, movesEl, timeEl, btn;
  var deck, flipped, lock, moves, matched, started, timer, secs;

  grid = root.querySelector('.mem-grid');
  msg = root.querySelector('.mem-msg');
  movesEl = root.querySelector('.mem-moves');
  timeEl = root.querySelector('.mem-time');
  btn = root.querySelector('.mem-restart');

  function setBest() { if (window.refreshArcadeBest) window.refreshArcadeBest(); }

  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function newGame() {
    deck = shuffle(ICONS.concat(ICONS).map(function (x) { return x; }));
    flipped = []; lock = false; moves = 0; matched = 0; started = false; secs = 0;
    if (timer) clearInterval(timer);
    movesEl.textContent = '0';
    timeEl.textContent = '0';
    msg.textContent = '';
    render();
  }

  function render() {
    grid.innerHTML = '';
    deck.forEach(function (item, idx) {
      var card = document.createElement('button');
      card.className = 'mem-card';
      card.dataset.idx = idx;
      card.dataset.key = item.n;
      card.innerHTML = '<div class="mem-inner">' +
        '<div class="mem-front">？</div>' +
        '<div class="mem-back"><span class="mem-emoji">' + item.e + '</span><span class="mem-name">' + item.n + '</span></div>' +
        '</div>';
      grid.appendChild(card);
    });
  }

  function startTimer() {
    if (started) return;
    started = true;
    timer = setInterval(function () {
      secs++; timeEl.textContent = secs;
    }, 1000);
  }

  function onClick(e) {
    var card = e.target.closest('.mem-card');
    if (!card || lock) return;
    if (card.classList.contains('flipped') || card.classList.contains('matched')) return;
    startTimer();
    card.classList.add('flipped');
    flipped.push(card);
    if (flipped.length === 2) {
      moves++; movesEl.textContent = moves;
      var a = flipped[0], b = flipped[1];
      if (a.dataset.key === b.dataset.key) {
        a.classList.add('matched'); b.classList.add('matched');
        flipped = [];
        matched++;
        if (matched === ICONS.length) win();
      } else {
        lock = true;
        a.classList.add('shake'); b.classList.add('shake');
        setTimeout(function () {
          a.classList.remove('flipped', 'shake'); b.classList.remove('flipped', 'shake');
          flipped = []; lock = false;
        }, 800);
      }
    }
  }

  function win() {
    clearInterval(timer);
    var isNew = window.Visitor ? window.Visitor.record('memory', moves, { higherBetter: false, unit: '步' }) : false;
    msg.textContent = '🎉 全部配对！用了 ' + moves + ' 步 / ' + secs + ' 秒' + (isNew ? '（新纪录！）' : '');
    setBest();
  }

  grid.addEventListener('click', onClick);
  btn.addEventListener('click', newGame);

  newGame();
  setBest();
};
