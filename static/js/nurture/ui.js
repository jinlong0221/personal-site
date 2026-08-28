// 灵圃·沉香养成 —— 界面与交互层
// 依赖 window.Nurture（core.js）与 window.Visitor（visitor.js）
(function () {
  'use strict';

  function $(s, r) { return (r || document).querySelector(s); }
  function $all(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  var N, S;
  var SEASON_NAMES = { spring: '春', summer: '夏', autumn: '秋', winter: '冬' };
  var curSeason = 'spring';

  // ---------- 季节配色 ----------
  var CANOPY = {
    spring: { fill: '#9ed79b', edge: '#7cc079', snow: false },
    summer: { fill: '#5fae5f', edge: '#3f8f3f', snow: false },
    autumn: { fill: '#d98b3a', edge: '#b86a25', snow: false },
    winter: { fill: '#7d9b7a', edge: '#5d7a5a', snow: true }
  };
  var PETAL_COLOR = {
    spring: ['#f7c5d6', '#f9d6e2', '#ffffff'],
    summer: ['#bfe6a8', '#a9d98b', '#dff3c8'],
    autumn: ['#e6a85a', '#d9772f', '#c44f2a'],
    winter: ['#ffffff', '#e8f0ff', '#cfe0f5']
  };

  document.addEventListener('DOMContentLoaded', function () {
    if (!window.Nurture) { console.error('Nurture core 未加载'); return; }
    N = window.Nurture;
    N.init();
    S = N.get();

    buildActionButtons();
    buildLore();
    renderVisitor();
    renderAll();

    // 回到页面事件（离线成长 / 节气 / 深夜小兽）
    var events = N.tick();
    events.forEach(function (ev) { showEvent(ev); });
    renderAll();

    bindTreeClick();
    startParticles();
    startTicker();
    bindStaticButtons();
  });

  // ---------- 身份卡 ----------
  function renderVisitor() {
    var box = $('#visitor');
    if (!box || !window.Visitor) return;
    var v = window.Visitor.get();
    box.innerHTML =
      '<div class="vc-avatar">印</div>' +
      '<div><div class="vc-name">江湖雅号 · ' + v.name + '</div>' +
      '<div class="vc-id">编号 #' + v.id + ' · 结伴于 ' + window.Visitor.dateStr(v.joinedAt) + '</div></div>';
  }
  window.renderVisitorCard = renderVisitor;

  // ---------- 总渲染 ----------
  function renderAll() {
    S = N.get();
    curSeason = N.seasonOf(Date.now());
    renderGarden();
    renderStatus();
    renderCollection();
    renderAchv();
    renderLog();
    refreshActions();
  }

  // ---------- 花园 / 树 ----------
  function renderGarden() {
    var g = $('.garden');
    if (g) g.setAttribute('data-season', curSeason);
    var wrap = $('#tree');
    if (wrap && window.Tree) {
      var stage = N.stageOf(S.growth);
      wrap.innerHTML = window.Tree.render({ stage: stage.key, season: curSeason, dead: S.dead, S: S });
    }
  }

  // ---------- 状态条 ----------
  function renderStatus() {
    var stage = N.stageOf(S.growth);
    var next = N.nextStage(S.growth);
    $('#stageName').textContent = stage.name;
    $('#stageTip').textContent = stage.tip;
    $('#rankName').textContent = N.rankOf(S.totalHarvest);

    setBar('growth', S.growth, next ? next.min : null, '成长');
    setBar('vigor', S.vigor, 100, '元气');
    setBar('resin', S.resin, 100, '结香');

    $('#ageDays').textContent = N.ageDays();
    $('#totalHarvest').textContent = S.totalHarvest;
    $('#collCount').textContent = S.collection.length;

    var nextTxt = next ? ('距「' + next.name + '」还差 ' + Math.ceil(next.min - S.growth) + ' 成长') : '已至古木，再无更高';
    $('#stageNext').textContent = nextTxt;
  }

  function setBar(key, val, max, label) {
    var fill = $('#bar-' + key);
    var txt = $('#val-' + key);
    var pct = max ? Math.min(100, (val / max) * 100) : Math.min(100, val);
    if (fill) fill.style.width = pct + '%';
    if (txt) txt.textContent = (key === 'growth' && max) ? (Math.round(val) + ' / ' + max) : Math.round(val) + (key === 'growth' && !max ? '+' : '%');
  }

  // ---------- 操作按钮 ----------
  function buildActionButtons() {
    var careBox = $('#careActions');
    Object.keys(N.CARE).forEach(function (k) {
      var d = N.CARE[k];
      careBox.appendChild(makeBtn('care:' + k, d.icon + ' ' + d.name, 'act-care'));
    });
    var incBox = $('#incenseActions');
    Object.keys(N.INCENSE).forEach(function (k) {
      var d = N.INCENSE[k];
      incBox.appendChild(makeBtn('incense:' + k, d.icon + ' ' + d.name, 'act-incense'));
    });
  }

  function makeBtn(act, label, cls) {
    var b = el('button', cls, label);
    b.type = 'button';
    b.dataset.act = act;
    b.addEventListener('click', function () { onAction(act); });
    return b;
  }

  function onAction(act) {
    var r;
    if (act.indexOf('care:') === 0) r = N.care(act.slice(5));
    else if (act.indexOf('incense:') === 0) r = N.incense(act.slice(8));
    if (r) {
      msg(r.msg, r.ok ? 'ok' : (r.dead ? 'bad' : 'warn'));
      if (r.stageUp || r.resin != null || r.ok) renderAll();
      else refreshActions();
    }
  }

  function bindStaticButtons() {
    var h = $('#btn-harvest');
    if (h) h.addEventListener('click', function () {
      var r = N.harvest();
      if (r.ok) {
        msg(r.isQinan ? ('🌟 采得奇楠！' + r.piece.weight + 'g，收藏阁添一明珠。') : ('采收成功：' + r.piece.type + '·' + r.piece.grade + ' ' + r.piece.weight + 'g'), 'ok');
        if (r.isQinan) toast('💎 奇楠现世！', '极品沉香入阁，香道功力大涨。', 'achv');
        renderAll();
      } else msg(r.msg, 'warn');
    });
    var rp = $('#btn-replant');
    if (rp) rp.addEventListener('click', function () {
      if (!S.dead && !confirm('重新栽一株会清空当前树的成长，收藏阁保留。确定？')) return;
      N.replant();
      msg('🌱 新株已入土，旧藏犹在。', 'ok');
      renderAll();
    });
    var beastClose = $('#beastClose');
    if (beastClose) beastClose.addEventListener('click', function () { $('#beast').classList.remove('show'); });
  }

  function refreshActions() {
    S = N.get();
    $all('[data-act]').forEach(function (b) {
      var act = b.dataset.act;
      var key = act.indexOf('care:') === 0 ? act.slice(5) : act.slice(8);
      var left = N.cdLeft(key);
      var disabled = left > 0;
      // 造香需成树
      if (act.indexOf('incense:') === 0 && S.growth < N.CFG.incenseUnlockGrowth) disabled = true;
      b.disabled = disabled || S.dead;
      var base = b.getAttribute('data-label') || (b.dataset.label = b.innerHTML);
      b.innerHTML = disabled && left > 0 ? (base.replace(/<[^>]+>/g, '').trim() + ' <span class="cd">' + left + 's</span>') : base;
    });
    var h = $('#btn-harvest');
    if (h) h.disabled = S.dead || S.resin < N.CFG.harvestMinResin;
    var rp = $('#btn-replant');
    if (rp) rp.style.display = S.dead ? '' : 'none';
    var incHint = $('#incenseHint');
    if (incHint) incHint.style.display = S.growth < N.CFG.incenseUnlockGrowth ? '' : 'none';
  }

  // ---------- 收藏阁 ----------
  function renderCollection() {
    var box = $('#collection');
    if (!box) return;
    box.innerHTML = '';
    if (!S.collection.length) {
      box.appendChild(el('div', 'empty-hint', '收藏阁还空着。把树养到成树，动手“造香”，便能采收第一块沉香。'));
      return;
    }
    S.collection.slice(0, 60).forEach(function (p) {
      var qn = p.grade === '奇楠';
      var card = el('div', 'coll-card' + (qn ? ' qn' : ''));
      card.innerHTML =
        '<div class="coll-icon">' + (qn ? '💎' : '🪵') + '</div>' +
        '<div class="coll-type">' + p.type + '</div>' +
        '<div class="coll-grade">' + p.grade + '</div>' +
        '<div class="coll-weight">' + p.weight + ' g</div>' +
        '<div class="coll-meta">树龄 ' + p.ageDays + ' 天</div>' +
        '<button class="coll-share" data-pid="' + p.id + '" type="button">晒</button>';
      box.appendChild(card);
    });
  }

  // ---------- 成就 ----------
  function renderAchv() {
    var box = $('#achv');
    if (!box) return;
    box.innerHTML = '';
    N.ACHV.forEach(function (a) {
      var got = !!S.achv[a.id];
      var card = el('div', 'achv-card' + (got ? ' got' : ''));
      card.innerHTML =
        '<div class="achv-icon">' + a.icon + '</div>' +
        '<div class="achv-name">' + a.name + '</div>' +
        '<div class="achv-desc">' + a.desc + '</div>' +
        (got ? '<div class="achv-flag">✓</div>' : '');
      box.appendChild(card);
    });
  }

  // ---------- 夜话·古卷 ----------
  function renderLog() {
    var box = $('#log');
    if (!box) return;
    box.innerHTML = '';
    if (!S.log.length) { box.appendChild(el('div', 'empty-hint', '尚无夜话。深夜来访、狂点树身、赶上节气，都会留下印记。')); return; }
    S.log.forEach(function (l) {
      var row = el('div', 'log-row log-' + l.kind, '<span class="log-t">' + fmtTime(l.t) + '</span><span class="log-x">' + l.text + '</span>');
      box.appendChild(row);
    });
  }
  function fmtTime(ts) {
    var d = new Date(ts);
    return ('0' + d.getMonth() + 1).slice(-2) + '-' + ('0' + d.getDate()).slice(-2) + ' ' + ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }

  // ---------- 科普 ----------
  function buildLore() {
    var box = $('#lore');
    if (!box) return;
    box.innerHTML = '';
    N.LORE.forEach(function (item, i) {
      var d = el('details', 'lore-item');
      d.innerHTML = '<summary>' + item.q + '</summary><div class="lore-a">' + item.a + '</div>';
      if (i === 0) d.open = true;
      box.appendChild(d);
    });
  }

  // ---------- 消息 ----------
  function msg(text, kind) {
    var m = $('#msg');
    if (!m) return;
    m.textContent = text;
    m.className = 'nurture-msg ' + (kind || 'ok');
  }
  function toast(title, text, kind) {
    var c = $('#toast');
    if (!c) return;
    var t = el('div', 'toast toast-' + (kind || 'info'), '<div class="toast-t">' + title + '</div><div class="toast-x">' + text + '</div>');
    c.appendChild(t);
    requestAnimationFrame(function () { t.classList.add('show'); });
    setTimeout(function () { t.classList.remove('show'); setTimeout(function () { t.remove(); }, 400); }, 3600);
  }

  // ---------- 事件弹层（节气 / 深夜小兽） ----------
  function showEvent(ev) {
    if (ev.type === 'fest') {
      toast('📅 ' + ev.title, ev.text, 'fest');
    } else if (ev.type === 'night') {
      var b = ev.beast;
      var pop = $('#beast');
      if (pop) {
        $('#beastIcon').textContent = b.icon;
        $('#beastName').textContent = b.name + '夜访';
        $('#beastSay').textContent = b.say;
        pop.classList.add('show');
        setTimeout(function () { pop.classList.remove('show'); }, 6000);
      }
      toast(b.icon + ' ' + b.name + '夜访', b.say, 'night');
    } else if (ev.type === 'offline') {
      msg(ev.text, 'ok');
    }
  }

  // ---------- 连点彩蛋 ----------
  function bindTreeClick() {
    var wrap = $('#tree');
    if (!wrap) return;
    wrap.addEventListener('click', function () {
      var r = N.registerClick();
      if (r.triggered) {
        toast('🌸 落英缤纷', r.text, 'petal');
        petalBurst();
        renderAll();
      }
    });
  }
  function petalBurst() {
    var cv = $('#particles');
    if (!cv) return;
    var ctx = cv.getContext('2d');
    for (var i = 0; i < 30; i++) {
      bursts.push({ x: cv.width / 2 + (Math.random() - 0.5) * 40, y: cv.height * 0.4, vx: (Math.random() - 0.5) * 3, vy: -2 - Math.random() * 2, life: 1, c: pick(PETAL_COLOR[curSeason]) });
    }
  }

  // ---------- 粒子系统 ----------
  var bursts = [];
  function startParticles() {
    var cv = $('#particles');
    if (!cv) return;
    var ctx = cv.getContext('2d');
    var parts = [];
    function resize() {
      var r = cv.getBoundingClientRect();
      var dpr = window.devicePixelRatio || 1;
      cv.width = r.width * dpr; cv.height = r.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener('resize', resize);

    function spawn() {
      var r = cv.getBoundingClientRect();
      parts.push({
        x: Math.random() * r.width, y: -10,
        vy: 0.4 + Math.random() * 0.8, vx: (Math.random() - 0.5) * 0.6,
        s: 3 + Math.random() * 4, c: pick(PETAL_COLOR[curSeason]), rot: Math.random() * 6, vr: (Math.random() - 0.5) * 0.1
      });
    }
    var last = 0;
    function loop(ts) {
      var r = cv.getBoundingClientRect();
      ctx.clearRect(0, 0, r.width, r.height);
      if (ts - last > 220) { last = ts; if (parts.length < 26) spawn(); }
      for (var i = parts.length - 1; i >= 0; i--) {
        var p = parts[i];
        p.y += p.vy; p.x += p.vx + Math.sin(p.y / 30) * 0.3; p.rot += p.vr;
        if (p.y > r.height + 10) { parts.splice(i, 1); continue; }
        ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot);
        ctx.globalAlpha = 0.85; ctx.fillStyle = p.c;
        ctx.beginPath(); ctx.ellipse(0, 0, p.s, p.s * 0.6, 0, 0, 7); ctx.fill();
        ctx.restore();
      }
      for (var j = bursts.length - 1; j >= 0; j--) {
        var b = bursts[j];
        b.x += b.vx; b.y += b.vy; b.vy += 0.08; b.life -= 0.02;
        if (b.life <= 0) { bursts.splice(j, 1); continue; }
        ctx.save(); ctx.globalAlpha = Math.max(0, b.life); ctx.fillStyle = b.c;
        ctx.beginPath(); ctx.ellipse(b.x, b.y, 4, 2.4, 0, 0, 7); ctx.fill(); ctx.restore();
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }

  // ---------- 冷却倒计时 ----------
  function startTicker() {
    setInterval(function () { refreshActions(); }, 1000);
  }
})();
