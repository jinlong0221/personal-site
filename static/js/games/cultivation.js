// 游艺修行体系：修为 / 等级 / 徽章 / 周课 / 联网天下榜
// 数据完全源自 visitor.js 的「各游戏最佳成绩」，对游戏本身零侵入。
// 在 lab.js 的 refreshArcadeBest 末尾调用 window.Cultivation.refresh() 即可刷新。
(function () {
  if (!window.Visitor) return;
  var GAMES = ['minesweeper', 'memory', 'gomoku', 'tetris'];
  var API = 'https://longxiong-nurture.longxiong-nurture.workers.dev';
  var ENROLL_KEY = 'lx_arcade_enrolled_v1';

  // —— 修为换算：每款最佳成绩 -> 修为分 ——
  function bestXiuwei(game, b) {
    if (!b || b.score == null) return 0;
    var s = b.score;
    if (game === 'tetris') return Math.floor(s / 50);
    if (game === 'gomoku') return s * 30;
    if (game === 'minesweeper') {
      var bonus = Math.max(0, 120 - s) * 2;        // ≤120秒起，每快1秒+2
      return Math.min(300, 200 + bonus);
    }
    if (game === 'memory') {
      var b2 = Math.max(0, 30 - s) * 3;             // ≤30步起，每少1步+3
      return Math.min(300, 200 + b2);
    }
    return 0;
  }
  function totalXiuwei(bests) {
    var xw = 0;
    GAMES.forEach(function (g) {
      xw += bestXiuwei(g, bests[g]);
      if (bests[g]) xw += 50;                        // 历练：每款有记录额外+50
    });
    return xw;
  }

  // —— 国风等级 ——
  var RANKS = [
    [0, '初学弟子'], [200, '渐入佳境'], [500, '小有所成'],
    [1000, '炉火纯青'], [1800, '登堂入室'], [3000, '一代宗师'], [5000, '游艺大宗师']
  ];
  function rankAt(xw) {
    var r = RANKS[0][1];
    for (var i = 0; i < RANKS.length; i++) if (xw >= RANKS[i][0]) r = RANKS[i][1];
    return r;
  }
  function prevThr(xw) { var p = 0; for (var i = 0; i < RANKS.length; i++) if (xw >= RANKS[i][0]) p = RANKS[i][0]; return p; }
  function nextThr(xw) {
    for (var i = 0; i < RANKS.length; i++) if (xw < RANKS[i][0]) return RANKS[i];
    return null;
  }

  // —— 徽章 ——
  var BADGES = [
    { id: 'first', name: '初窥门径', icon: '🌱', test: function (b) { return GAMES.some(function (g) { return b[g]; }); } },
    { id: 'allfour', name: '四艺皆通', icon: '🀄', test: function (b) { return GAMES.every(function (g) { return b[g]; }); } },
    { id: 'tetris', name: '叠香宗师', icon: '🧱', test: function (b) { return b.tetris && b.tetris.score >= 2000; } },
    { id: 'gomoku', name: '棋高一着', icon: '⚫', test: function (b) { return b.gomoku && b.gomoku.score >= 10; } },
    { id: 'mine', name: '排雷快手', icon: '💣', test: function (b) { return b.minesweeper && b.minesweeper.score <= 60; } },
    { id: 'mem', name: '过目不忘', icon: '🎴', test: function (b) { return b.memory && b.memory.score <= 20; } },
    { id: 'weekly', name: '周课', icon: '📜', test: function (b, ctx) { return ctx.weekDone; } }
  ];

  // —— 周课：按 ISO 周生成确定性目标，需「本周内」达成 ——
  function isoWeek(d) {
    var onejan = new Date(d.getFullYear(), 0, 1);
    var week = Math.ceil((((d - onejan) / 86400000) + onejan.getDay() + 1) / 7);
    return d.getFullYear() + '-W' + week;
  }
  function inThisWeek(ts) { return ts ? isoWeek(new Date(ts)) === isoWeek(new Date()) : false; }
  var WEEK_GOALS = [
    { game: 'tetris', label: '叠香 · 单局 ≥ 1500 分', test: function (b) { return b.tetris && b.tetris.score >= 1500; } },
    { game: 'gomoku', label: '对弈 · 胜 1 局', test: function (b) { return b.gomoku && b.gomoku.score >= 1; } },
    { game: 'minesweeper', label: '沉香探秘 · ≤ 90 秒通关', test: function (b) { return b.minesweeper && b.minesweeper.score <= 90; } },
    { game: 'memory', label: '香材辨识 · ≤ 28 步通关', test: function (b) { return b.memory && b.memory.score <= 28; } }
  ];
  function weekGoal() {
    var d = new Date();
    var onejan = new Date(d.getFullYear(), 0, 1);
    var week = Math.ceil((((d - onejan) / 86400000) + onejan.getDay() + 1) / 7);
    var idx = (d.getFullYear() * 53 + week) % WEEK_GOALS.length;
    return { key: isoWeek(d), goal: WEEK_GOALS[idx] };
  }

  function getBests() {
    var b = {};
    GAMES.forEach(function (g) { b[g] = window.Visitor.getBest(g); });
    return b;
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function setText(sel, txt) { var el = document.querySelector(sel); if (el) el.textContent = txt; }

  // —— 渲染修行面板 ——
  function render() {
    if (!document.querySelector('[data-cult="rank"]')) return; // 面板未挂载
    var bests = getBests();
    var w = weekGoal();
    var weekDone = !!(bests[w.goal.game] && w.goal.test(bests) && inThisWeek(bests[w.goal.game].at));

    var xw = totalXiuwei(bests);
    var earned = BADGES.filter(function (bd) { return bd.test(bests, { weekDone: weekDone }); });
    xw += earned.length * 40; // 每枚徽章 +40

    var nr = nextThr(xw), pr = prevThr(xw);

    setText('[data-cult="rank"]', rankAt(xw));
    setText('[data-cult="xiuwei"]', xw);
    var fill = document.querySelector('[data-cult="bar"]');
    if (fill) {
      if (nr) { var pct = Math.max(4, Math.min(100, Math.round((xw - pr) / (nr[0] - pr) * 100))); fill.style.width = pct + '%'; }
      else fill.style.width = '100%';
    }
    var tip = document.querySelector('[data-cult="tip"]');
    if (tip) tip.textContent = nr ? ('距「' + nr[1] + '」还差 ' + (nr[0] - xw) + ' 修为') : '已臻化境 · 游艺大宗师';

    // 徽章墙
    var wall = document.querySelector('[data-cult="badges"]');
    if (wall) {
      wall.innerHTML = '';
      BADGES.forEach(function (bd) {
        var got = bd.test(bests, { weekDone: weekDone });
        var el = document.createElement('div');
        el.className = 'badge' + (got ? ' on' : '');
        el.title = bd.name + (got ? '（已得）' : '（未得）');
        el.innerHTML = '<span class="badge-ico">' + bd.icon + '</span><span class="badge-name">' + bd.name + '</span>';
        wall.appendChild(el);
      });
    }

    // 周课
    setText('[data-cult="week-label"]', w.key + ' 课业');
    setText('[data-cult="week-goal"]', w.goal.label);
    var ws = document.querySelector('[data-cult="week-status"]');
    if (ws) {
      if (weekDone) { ws.textContent = '✅ 已完成 · 获 50 修为'; ws.className = 'cult-week-status done'; }
      else { ws.textContent = '进行中'; ws.className = 'cult-week-status'; }
    }

    // 登榜按钮态
    var enroll = document.querySelector('[data-cult="enroll"]');
    if (enroll) {
      var on = localStorage.getItem(ENROLL_KEY) === '1';
      enroll.textContent = on ? '✓ 已在天下榜' : '登上天下榜';
      enroll.classList.toggle('on', on);
    }

    loadRank();
  }

  // —— 联网天下榜（可降级：连不上静默失败）——
  function loadRank() {
    var box = document.querySelector('[data-cult="rank-list"]');
    if (!box) return;
    if (localStorage.getItem(ENROLL_KEY) !== '1') {
      box.innerHTML = '<div class="rank-empty">点「登上天下榜」，和全网游艺同好比一比修为</div>';
      return;
    }
    fetch(API + '/api/arcade/rank?limit=20', { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.ok || !d.list) { box.innerHTML = '<div class="rank-empty">榜单一时取不到，稍后再来</div>'; return; }
        if (!d.list.length) { box.innerHTML = '<div class="rank-empty">还没有人登榜，抢个头名？</div>'; return; }
        box.innerHTML = '';
        var meId = window.Visitor.get().id;
        d.list.slice(0, 20).forEach(function (e, i) {
          var row = document.createElement('div');
          row.className = 'rank-row' + (e.id === meId ? ' me' : '');
          row.innerHTML = '<span class="rank-no">' + (i + 1) + '</span>' +
            '<span class="rank-name">' + escapeHtml(e.name) + (e.id === meId ? '（你）' : '') + '</span>' +
            '<span class="rank-xw">' + (e.xiuwei || 0) + ' 修为</span>';
          box.appendChild(row);
        });
      })
      .catch(function () { box.innerHTML = '<div class="rank-empty">榜单一时取不到，稍后再来</div>'; });
  }

  function submitScore() {
    var v = window.Visitor.get();
    var bests = getBests();
    var xw = totalXiuwei(bests);
    var scores = {};
    GAMES.forEach(function (g) { scores[g] = bests[g] ? bests[g].score : null; });
    fetch(API + '/api/arcade/submit', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ id: v.id, token: v.token, name: v.name, xiuwei: xw, rank: rankAt(xw), scores: scores })
    }).catch(function () {});
  }

  function enroll() {
    var first = localStorage.getItem(ENROLL_KEY) !== '1';
    localStorage.setItem(ENROLL_KEY, '1');
    submitScore();
    if (first) render(); // 首次登榜立即刷新（显示空榜提示->榜单）
  }

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.querySelector('[data-cult="enroll"]');
    if (btn) btn.addEventListener('click', enroll);
    render();
  });

  window.Cultivation = { refresh: render, enroll: enroll, submit: submitScore };
})();
