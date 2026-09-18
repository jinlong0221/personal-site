/* 龙兄农场 — 类星露谷种田小游戏（第一步可玩核心）
 * 纯前端 + Canvas，存档用 localStorage。美术：程序化像素 + 可选 AI 图覆盖。
 */
(function () {
  'use strict';

  // ---------- 基础配置 ----------
  var TILE = 48;
  var COLS = 14, ROWS = 10;
  var W = TILE * COLS, H = TILE * ROWS;
  var SAVE_KEY = 'longxiong_farm_v1';
  var MAX_STAGE = 3;            // 生长阶段 0..3，3=成熟
  var SEED_COST = 10, CROP_PRICE = 30, GOAL = 500;

  var canvas = document.getElementById('game');
  var ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;

  // ---------- 可选 AI 美术（失败自动退回程序化） ----------
  // 文件名对应 static/game/assets/ 下真实 PNG；不存在则走程序化绘制。
  var SPR = {};                    // name -> Image（加载成功才填）
  var SPR_URL = {
    grass: 'assets/grass.png',
    soil: 'assets/soil.png',
    player_down: 'assets/player_down.png',
    player_up: 'assets/player_up.png',
    player_side: 'assets/player_side.png',
    crop0: 'assets/crop_0.png', crop1: 'assets/crop_1.png',
    crop2: 'assets/crop_2.png', crop3: 'assets/crop_3.png'
  };
  Object.keys(SPR_URL).forEach(function (k) {
    var img = new Image();
    img.onload = function () { SPR[k] = img; };
    img.onerror = function () { /* 退回程序化 */ };
    img.src = SPR_URL[k] + '?v=20260918';
  });
  function has(name) { return !!SPR[name]; }

  // ---------- 游戏状态 ----------
  var state, player, keys = {}, toolIdx = 0, target = null;
  var TOOLS = ['锄', '种', '浇', '收'];
  var DIR = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

  function freshTiles() {
    var t = [];
    for (var r = 0; r < ROWS; r++) {
      t[r] = [];
      for (var c = 0; c < COLS; c++) t[r][c] = { type: 'grass', crop: null };
    }
    return t;
  }

  function load() {
    try {
      var raw = localStorage.getItem(SAVE_KEY);
      if (raw) {
        var s = JSON.parse(raw);
        if (s && s.tiles && s.tiles.length === ROWS) return s;
      }
    } catch (e) {}
    return { day: 1, money: 100, seeds: 3, crops: 0, tiles: freshTiles() };
  }

  function save() {
    try { localStorage.setItem(SAVE_KEY, JSON.stringify(state)); } catch (e) {}
  }

  function newGame() {
    state = { day: 1, money: 100, seeds: 3, crops: 0, tiles: freshTiles() };
    player = { x: W / 2, y: H / 2, dir: 'down', speed: 170 };
    toolIdx = 0;
    syncToolButtons();
    save();
    flash('新农场开张啦，去种第一棵菜吧！');
  }

  // ---------- 交互逻辑 ----------
  function tileAt(px, py) {
    var c = Math.floor(px / TILE), r = Math.floor(py / TILE);
    if (c < 0 || c >= COLS || r < 0 || r >= ROWS) return null;
    return { c: c, r: r };
  }
  function frontTile() {
    var t = tileAt(player.x, player.y);
    if (!t) return null;
    var d = DIR[player.dir];
    var c = t.c + d[0], r = t.r + d[1];
    if (c < 0 || c >= COLS || r < 0 || r >= ROWS) return t;
    return { c: c, r: r };
  }

  // 核心：对某个格子使用当前工具
  function act(tc, tr) {
    if (tc == null || tr == null) return;
    if (tc < 0 || tc >= COLS || tr < 0 || tr >= ROWS) return;
    var cell = state.tiles[tr][tc];
    if (toolIdx === 0) {                      // 锄：草地→耕地
      if (cell.type === 'grass') { cell.type = 'soil'; cell.crop = null; flash('开垦了一块耕地'); }
      else flash('这里已经是耕地了');
    } else if (toolIdx === 1) {               // 种
      if (cell.type === 'soil' && !cell.crop) {
        if (state.seeds > 0) { cell.crop = { stage: 0, watered: false }; state.seeds--; flash('播下种子（记得浇水）'); }
        else flash('没有种子了，先去商店买');
      } else if (cell.crop) flash('这块地已经种了');
      else flash('先用锄把草地开垦成耕地');
    } else if (toolIdx === 2) {               // 浇
      if (cell.crop && !cell.crop.watered) { cell.crop.watered = true; flash('浇水完成'); }
      else if (cell.crop && cell.crop.watered) flash('已经浇过水了');
      else flash('这里没有需要浇水的作物');
    } else if (toolIdx === 3) {               // 收
      if (cell.crop && cell.crop.stage >= MAX_STAGE) {
        state.crops++; cell.crop = null; cell.type = 'soil'; flash('收获一株成熟作物！');
        if (state.money + state.crops * CROP_PRICE >= GOAL) flash('🎉 已达成 500 金目标！');
      } else if (cell.crop) flash('还没成熟，继续浇水等它长大');
      else flash('这里没有可收获的作物');
    }
    updateHUD(); save();
  }

  function buySeed() {
    if (state.money >= SEED_COST) { state.money -= SEED_COST; state.seeds++; flash('买了一袋种子'); }
    else flash('金币不够，先去卖点作物');
    updateHUD(); save();
  }
  function sellCrops() {
    if (state.crops > 0) {
      var gain = state.crops * CROP_PRICE;
      state.money += gain; var n = state.crops; state.crops = 0;
      flash('卖出 ' + n + ' 个作物，+ ' + gain + ' 金');
    } else flash('背包里没有作物可卖');
    updateHUD(); save();
  }
  function nextDay() {
    state.day++;
    for (var r = 0; r < ROWS; r++) for (var c = 0; c < COLS; c++) {
      var crop = state.tiles[r][c].crop;
      if (crop && crop.watered) {
        if (crop.stage < MAX_STAGE) crop.stage++;
        crop.watered = false;
      }
    }
    flash('第 ' + state.day + ' 天，浇过水的作物长大了一级');
    updateHUD(); save();
  }

  // ---------- 绘制（程序化像素 + AI 图覆盖） ----------
  function px(x, y, w, h, color) { ctx.fillStyle = color; ctx.fillRect(x, y, w, h); }

  function drawGrass(c, r) {
    var x = c * TILE, y = r * TILE;
    if (has('grass')) { ctx.drawImage(SPR.grass, x, y, TILE, TILE); return; }
    var base = (c + r) % 2 ? '#5a9e3f' : '#549438';
    px(x, y, TILE, TILE, base);
    // 草点
    px(x + 8, y + 12, 3, 3, '#6fb84e'); px(x + 30, y + 20, 3, 3, '#6fb84e');
    px(x + 18, y + 34, 3, 3, '#6fb84e'); px(x + 38, y + 8, 2, 2, '#74c052');
  }
  function drawSoil(c, r, crop) {
    var x = c * TILE, y = r * TILE;
    if (has('soil')) { ctx.drawImage(SPR.soil, x, y, TILE, TILE); }
    else {
      px(x, y, TILE, TILE, crop && crop.watered ? '#5b3c22' : '#7a5230');
      // 犁沟
      ctx.strokeStyle = crop && crop.watered ? '#3f2916' : '#5e3e22';
      ctx.lineWidth = 2;
      for (var i = 1; i < 4; i++) {
        ctx.beginPath(); ctx.moveTo(x + 4, y + i * 12); ctx.lineTo(x + TILE - 4, y + i * 12); ctx.stroke();
      }
    }
    // 湿土高光：无论用 AI 图还是程序化都叠加
    if (crop && crop.watered) {
      ctx.fillStyle = 'rgba(90,150,220,.18)'; ctx.fillRect(x + 2, y + 2, TILE - 4, TILE - 4);
    }
  }
  function drawCrop(c, r, crop) {
    var x = c * TILE, y = r * TILE, cx = x + TILE / 2;
    var name = 'crop' + crop.stage;
    if (has(name)) { ctx.drawImage(SPR[name], x, y, TILE, TILE); return; }
    if (crop.stage === 0) { px(cx - 3, y + 30, 6, 6, '#6b4a2a'); return; }
    if (crop.stage === 1) { px(cx - 2, y + 22, 4, 12, '#3f8f3a'); px(cx - 6, y + 26, 5, 3, '#4ca544'); px(cx + 2, y + 26, 5, 3, '#4ca544'); return; }
    if (crop.stage === 2) {
      px(cx - 3, y + 14, 6, 22, '#3f8f3a');
      px(cx - 10, y + 18, 9, 4, '#57b24c'); px(cx + 2, y + 18, 9, 4, '#57b24c');
      px(cx - 10, y + 28, 9, 4, '#4ca544'); px(cx + 2, y + 28, 9, 4, '#4ca544');
      return;
    }
    // 成熟：茎 + 叶 + 红果
    px(cx - 3, y + 12, 6, 26, '#3f8f3a');
    px(cx - 11, y + 16, 10, 4, '#57b24c'); px(cx + 2, y + 16, 10, 4, '#57b24c');
    px(cx - 11, y + 28, 10, 4, '#4ca544'); px(cx + 2, y + 28, 10, 4, '#4ca544');
    px(cx - 7, y + 18, 7, 7, '#e0533a'); px(cx + 3, y + 24, 7, 7, '#f0703f');
    px(cx - 2, y + 30, 6, 6, '#e0533a');
  }

  function drawPlayer() {
    var x = player.x - TILE / 2, y = player.y - TILE / 2;
    var key = 'player_' + (player.dir === 'left' || player.dir === 'right' ? 'side' : player.dir);
    if (has(key)) {
      var flip = player.dir === 'left';
      if (flip) { ctx.save(); ctx.translate(player.x + TILE / 2, 0); ctx.scale(-1, 1); ctx.translate(-(player.x + TILE / 2), 0); }
      ctx.drawImage(SPR[key], x, y, TILE, TILE);
      if (flip) ctx.restore();
      return;
    }
    // 程序化小人（草帽农夫）
    px(x + 14, y + 6, 20, 8, '#e8c34a');        // 帽檐
    px(x + 17, y + 1, 14, 7, '#d4a93a');         // 帽顶
    px(x + 16, y + 14, 16, 12, '#f1c9a0');       // 脸
    px(x + 19, y + 19, 3, 3, '#3a2a1a');         // 眼
    px(x + 26, y + 19, 3, 3, '#3a2a1a');
    px(x + 14, y + 26, 20, 16, '#3f6fb0');       // 身体（蓝罩衫）
    px(x + 18, y + 30, 12, 8, '#2f5690');        // 围裙
    px(x + 13, y + 42, 7, 6, '#caa46a');         // 腿
    px(x + 28, y + 42, 7, 6, '#caa46a');
    // 朝向小指示
    if (player.dir === 'down') px(x + 22, y + 23, 4, 2, '#b06a4a');
    if (player.dir === 'up') { /* 背面 */ }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    for (var r = 0; r < ROWS; r++) for (var c = 0; c < COLS; c++) {
      var cell = state.tiles[r][c];
      if (cell.type === 'grass') drawGrass(c, r);
      else drawSoil(c, r, cell.crop);
      if (cell.crop) drawCrop(c, r, cell.crop);
    }
    // 目标格高亮
    var t = target || frontTile();
    if (t) {
      ctx.strokeStyle = '#ffd24a'; ctx.lineWidth = 3;
      ctx.strokeRect(t.c * TILE + 2, t.r * TILE + 2, TILE - 4, TILE - 4);
    }
    drawPlayer();
  }

  // ---------- 主循环 ----------
  var last = 0;
  function loop(ts) {
    var dt = last ? Math.min((ts - last) / 1000, 0.05) : 0; last = ts;
    var dx = 0, dy = 0;
    if (keys['arrowup'] || keys['w']) dy -= 1;
    if (keys['arrowdown'] || keys['s']) dy += 1;
    if (keys['arrowleft'] || keys['a']) dx -= 1;
    if (keys['arrowright'] || keys['d']) dx += 1;
    if (dx || dy) {
      var len = Math.hypot(dx, dy) || 1;
      player.x += (dx / len) * player.speed * dt;
      player.y += (dy / len) * player.speed * dt;
      player.x = Math.max(TILE / 2, Math.min(W - TILE / 2, player.x));
      player.y = Math.max(TILE / 2, Math.min(H - TILE / 2, player.y));
      if (Math.abs(dx) > Math.abs(dy)) player.dir = dx < 0 ? 'left' : 'right';
      else if (dy) player.dir = dy < 0 ? 'up' : 'down';
    }
    draw();
    requestAnimationFrame(loop);
  }

  // ---------- UI / 事件 ----------
  var msgTimer = null;
  function flash(text) {
    var el = document.getElementById('msg');
    el.textContent = text; el.classList.add('show');
    clearTimeout(msgTimer);
    msgTimer = setTimeout(function () { el.classList.remove('show'); }, 1400);
  }
  function updateHUD() {
    document.getElementById('hud-day').textContent = state.day;
    document.getElementById('hud-money').textContent = state.money;
    document.getElementById('hud-seed').textContent = state.seeds;
    document.getElementById('hud-crop').textContent = state.crops;
    document.getElementById('hud-tool').textContent = TOOLS[toolIdx];
  }
  function syncToolButtons() {
    document.querySelectorAll('.toolbar .btn').forEach(function (b, i) {
      b.classList.toggle('on', i === toolIdx);
    });
  }
  function selectTool(i) { toolIdx = i; syncToolButtons(); updateHUD(); }

  document.querySelectorAll('.toolbar .btn').forEach(function (b) {
    b.addEventListener('click', function () { selectTool(parseInt(b.dataset.tool, 10)); });
  });
  document.getElementById('btn-buy').addEventListener('click', buySeed);
  document.getElementById('btn-sell').addEventListener('click', sellCrops);
  document.getElementById('btn-day').addEventListener('click', nextDay);
  document.getElementById('btn-reset').addEventListener('click', function () {
    if (confirm('确定要清空农场、从头开始吗？')) newGame();
  });

  // 方向键（手机）按住持续移动
  var padTimer = null;
  document.querySelectorAll('#pad .btn[data-dir]').forEach(function (b) {
    var dir = b.dataset.dir;
    var press = function (e) {
      e.preventDefault();
      keys[dir === 'up' ? 'arrowup' : dir === 'down' ? 'arrowdown' : dir === 'left' ? 'arrowleft' : 'arrowright'] = true;
    };
    var release = function (e) {
      e.preventDefault();
      keys[dir === 'up' ? 'arrowup' : dir === 'down' ? 'arrowdown' : dir === 'left' ? 'arrowleft' : 'arrowright'] = false;
    };
    b.addEventListener('pointerdown', press);
    b.addEventListener('pointerup', release);
    b.addEventListener('pointerleave', release);
    b.addEventListener('pointercancel', release);
  });

  // 键盘
  window.addEventListener('keydown', function (e) {
    var k = e.key.toLowerCase();
    if (['arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' '].indexOf(k) >= 0) e.preventDefault();
    if (k === ' ') { act(frontTile().c, frontTile().r); return; }
    if (k >= '1' && k <= '4') { selectTool(parseInt(k, 10) - 1); return; }
    keys[k] = true;
  });
  window.addEventListener('keyup', function (e) { keys[e.key.toLowerCase()] = false; });

  // 点地图格子：选工具 + 直接对该格使用（手机友好）
  canvas.addEventListener('pointerdown', function (e) {
    var rect = canvas.getBoundingClientRect();
    var sx = canvas.width / rect.width, sy = canvas.height / rect.height;
    var px2 = (e.clientX - rect.left) * sx, py2 = (e.clientY - rect.top) * sy;
    var t = tileAt(px2, py2);
    if (t) { target = t; act(t.c, t.r); setTimeout(function () { target = null; }, 250); }
  });

  // ---------- 启动 ----------
  state = load();
  player = { x: W / 2, y: H / 2, dir: 'down', speed: 170 };
  syncToolButtons();
  updateHUD();
  requestAnimationFrame(loop);
})();
