(function () {
  var wrap = document.getElementById('game-sudoku');
  if (!wrap) return;
  var boardEl = wrap.querySelector('.sd-board');
  var checkBtn = wrap.querySelector('.sd-check');
  var hint = wrap.querySelector('.gc-hint');
  var pad = wrap.querySelector('.sd-pad');

  var puzzle = [
    5,3,0,0,7,0,0,0,0,
    6,0,0,1,9,5,0,0,0,
    0,9,8,0,0,0,0,6,0,
    8,0,0,0,6,0,0,0,3,
    4,0,0,8,0,3,0,0,1,
    7,0,0,0,2,0,0,0,6,
    0,6,0,0,0,0,2,8,0,
    0,0,0,4,1,9,0,0,5,
    0,0,0,0,8,0,0,7,9
  ];
  var solution = [
    5,3,4,6,7,8,9,1,2,
    6,7,2,1,9,5,3,4,8,
    1,9,8,3,4,2,5,6,7,
    8,5,9,7,6,1,4,2,3,
    4,2,6,8,5,3,7,9,1,
    7,1,3,9,2,4,8,5,6,
    9,6,1,5,3,7,2,8,4,
    2,8,7,4,1,9,6,3,5,
    3,4,5,2,8,6,1,7,9
  ];
  var user = puzzle.slice();
  var selected = -1;
  var inputs = [];

  for (var i = 0; i < 81; i++) {
    var inp = document.createElement('div');
    inp.className = 'sd-cell' + (puzzle[i] ? ' fixed' : '');
    if (puzzle[i]) inp.textContent = puzzle[i];
    (function (idx) {
      inp.addEventListener('click', function () {
        selected = idx;
        inputs.forEach(function (c) { c.classList.remove('sel'); });
        inp.classList.add('sel');
      });
    })(i);
    boardEl.appendChild(inp);
    inputs.push(inp);
  }

  function refresh() {
    for (var i = 0; i < 81; i++) {
      if (puzzle[i]) { inputs[i].textContent = puzzle[i]; inputs[i].classList.add('fixed'); }
      else { inputs[i].textContent = user[i] ? user[i] : ''; inputs[i].classList.remove('fixed'); }
      inputs[i].classList.remove('wrong');
    }
  }

  for (var n = 1; n <= 9; n++) {
    var b = document.createElement('button');
    b.className = 'sd-num'; b.textContent = n;
    b.addEventListener('click', function () {
      if (selected < 0 || puzzle[selected]) return;
      var v = parseInt(this.textContent, 10);
      user[selected] = (user[selected] === v) ? 0 : v;
      refresh();
    });
    pad.appendChild(b);
  }
  var eraser = document.createElement('button');
  eraser.className = 'sd-num sd-erase'; eraser.textContent = '✕';
  eraser.addEventListener('click', function () {
    if (selected < 0 || puzzle[selected]) return;
    user[selected] = 0; refresh();
  });
  pad.appendChild(eraser);

  checkBtn.addEventListener('click', function () {
    var ok = true, filled = 0;
    for (var i = 0; i < 81; i++) {
      inputs[i].classList.remove('wrong');
      if (!puzzle[i] && user[i]) {
        filled++;
        if (user[i] !== solution[i]) { inputs[i].classList.add('wrong'); ok = false; }
      }
    }
    if (!filled) { if (hint) hint.textContent = '先填几个数字，再点「检查」～'; return; }
    if (ok) { if (hint) hint.textContent = '👏 目前填的都对了，继续加油！'; }
    else { if (hint) hint.textContent = '标红的格子填错了，再想想'; }
  });

  refresh();
  if (hint) hint.textContent = '点格子 → 点数字键填数，点「检查」看对错';
})();
