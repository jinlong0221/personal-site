// 沉香·放置修炼 —— 国风 Idle / Incremental
// 你是一株沉香木的守护香农：汲水→结香(耗元气)→炼香→得香品与修为→突破境界→转生获香魂(永久加成)
// 纯前端 localStorage 存档；隐藏面板时仍由 setInterval 独立 tick；离线按 lastSeen 结算。
(function () {
  if (!window.Visitor) return;            // 依赖身份卡（已有）
  var KEY = 'lx_xiuxiang_v1';
  var SAVE_MS = 5000;
  var OFFLINE_CAP = 8 * 3600 * 1000;      // 离线结算上限 8h

  var REALMS = ['凡木', '引灵', '凝脂', '结香', '通幽', '香道大宗师'];
  var REALM_FLAVOR = [
    '一株幼苗，尚无香气。慢慢养。',
    '初引灵气，枝叶舒展。',
    '脂液初凝，已有微香。',
    '結香既成，香韵渐厚。',
    '通幽入微，可辨诸香。',
    '香道大宗师——一念生香。'
  ];
  var XP_NEED = [60, 200, 600, 1500, 4000];   // realm i -> i+1 所需修为
  var TECH = [
    { key: 'plant',  name: '种植', icon: '🌱', base: 20, desc: '灵泉产水 + 汲水效率' },
    { key: 'resin',  name: '结香', icon: '🩸', base: 30, desc: '结香产量 + 元气恢复' },
    { key: 'refine', name: '炼香', icon: '🔥', base: 50, desc: '炼香产量 + 修为' },
    { key: 'dao',    name: '香道', icon: '☯',  base: 80, desc: '全局产出加成' }
  ];
  var TECH_MAX = 6;

  var state, timer = null, inited = false, root = null, logs = [];

  function def() {
    return {
      water: 0, vigor: 50, vigorMax: 100,
      resin: 0, incense: 0, xp: 0, realm: 0,
      tech: { plant: 0, resin: 0, refine: 0, dao: 0 },
      soul: 0, totalIncense: 0, totalResin: 0,
      auto: false, lastSeen: Date.now(), bornAt: Date.now()
    };
  }
  function load() {
    try {
      var s = JSON.parse(localStorage.getItem(KEY));
      if (s && typeof s === 'object') {
        var d = def();
        for (var k in d) if (!(k in s)) s[k] = d[k];
        for (var t in d.tech) if (!(t in s.tech)) s.tech[t] = 0;
        return s;
      }
    } catch (e) {}
    return def();
  }
  function save() { state.lastSeen = Date.now(); localStorage.setItem(KEY, JSON.stringify(state)); }
  function report() {
    if (window.Visitor) window.Visitor.record('xiuxiang', Math.floor(state.totalIncense),
      { realm: state.realm, soul: state.soul, at: Date.now() });
    if (window.Cultivation && window.Cultivation.refresh) window.Cultivation.refresh();
  }
  function log(msg) {
    logs.unshift(msg);
    if (logs.length > 6) logs.pop();
    var box = root && root.querySelector('[data-xx="log"]');
    if (box) box.innerHTML = logs.map(function (l) { return '<div class="xx-log-line">' + l + '</div>'; }).join('');
  }

  // —— 倍率 ——
  function daoMult() { return 1 + 0.35 * state.tech.dao; }
  function realmMult() { return 1 + 0.4 * state.realm; }
  function soulMult() { return 1 + 0.12 * state.soul; }
  function globalMult() { return daoMult() * realmMult() * soulMult(); }

  // —— 产出 ——
  function waterPerClick() { return (1 + state.tech.plant * 1.5) * globalMult(); }
  function springRate() { return (0.15 + state.tech.plant * 0.25); }
  function resinYield() { return (4 + state.tech.resin * 4) * globalMult(); }
  function vigorCost() { return Math.max(3, 12 - state.tech.resin * 1.5); }
  function vigorRegen() { return 0.6 + state.tech.resin * 0.4; }
  function incenseYield() { return (1 + state.tech.refine * 1.2) * globalMult(); }
  function xpPerIncense() { return 4 + state.tech.refine * 2; }
  function resinPerRefine() { return 10; }
  function techCost(t) { return Math.floor(t.base * Math.pow(state.tech[t.key] + 1, 1.6)); }
  function xpNeed() { return state.realm < XP_NEED.length ? XP_NEED[state.realm] : Infinity; }
  function soulGain() { return Math.floor(Math.sqrt(state.totalIncense / 200)); }
  function canPrestige() { return state.realm >= 4 && soulGain() >= 1; }

  // —— 行为 ——
  function actDrawWater() { state.water += waterPerClick(); after(); }
  function actJie() {
    if (state.vigor < vigorCost()) { log('元气不足，先打坐恢复'); return; }
    state.vigor -= vigorCost();
    var g = resinYield();
    state.resin += g; state.totalResin += g;
    log('创伤结香，得香脂 ' + fmt(g));
    after();
  }
  function actRefine() {
    if (state.resin < resinPerRefine()) { log('香脂不足，需 ' + resinPerRefine() + ' 方可炼香'); return; }
    state.resin -= resinPerRefine();
    var inc = incenseYield();
    state.incense += inc; state.totalIncense += inc;
    var xp = inc * xpPerIncense();
    state.xp += xp;
    log('炼香成 ' + fmt(inc) + ' 香品，修为 +' + fmt(xp));
    after();
  }
  function actBreak() {
    if (state.xp < xpNeed()) { log('修为不足，距突破还差 ' + fmt(xpNeed() - state.xp)); return; }
    state.xp -= xpNeed();
    state.realm++;
    log('🌟 突破至【' + REALMS[state.realm] + '】' + REALM_FLAVOR[state.realm]);
    after();
  }
  function actPrestige() {
    if (!canPrestige()) { log('需达「通幽」且累计香品≥' + fmt(200) + '方可转生'); return; }
    var g = soulGain();
    var keep = { soul: state.soul + g, totalIncense: state.totalIncense, totalResin: state.totalResin, bornAt: state.bornAt };
    state = def();
    state.soul = keep.soul; state.totalIncense = keep.totalIncense;
    state.totalResin = keep.totalResin; state.bornAt = keep.bornAt;
    log('🕊 转生！获香魂 ' + g + '（永久 +' + (g * 12) + '% 全局产出）');
    after(true);
  }
  function actTech(t) {
    var c = techCost(t);
    if (state.incense < c) { log(t.name + '升级需 ' + fmt(c) + ' 香品'); return; }
    state.incense -= c;
    state.tech[t.key]++;
    log(t.icon + ' ' + t.name + ' 升至 Lv.' + state.tech[t.key]);
    after();
  }
  function toggleAuto() { state.auto = !state.auto; log(state.auto ? '自动修炼：开' : '自动修炼：关'); render(); save(); }

  function autoStep() {
    if (!state.auto) return;
    // 优先结香（元气够），再炼香（香脂够）
    if (state.vigor >= vigorCost() && state.resin < resinPerRefine() * 3) {
      state.vigor -= vigorCost();
      var g = resinYield(); state.resin += g; state.totalResin += g;
    }
    if (state.resin >= resinPerRefine()) {
      state.resin -= resinPerRefine();
      var inc = incenseYield(); state.incense += inc; state.totalIncense += inc;
      state.xp += inc * xpPerIncense();
    }
  }

  function tick() {
    var dt = 1000;
    state.water += springRate() * globalMult() * (dt / 1000);
    state.vigor = Math.min(state.vigorMax, state.vigor + vigorRegen());
    autoStep();
    render();
  }

  function after(force) {
    render(); report();
    if (force) save();
  }

  // —— 离线结算 ——
  function settleOffline() {
    var now = Date.now();
    var dt = now - (state.lastSeen || now);
    if (dt <= 60000) { state.lastSeen = now; return; }   // <1min 不算
    var capped = Math.min(dt, OFFLINE_CAP);
    var secs = capped / 1000;
    var eff = Math.min(1, 0.5 + 0.1 * state.tech.dao);
    var w = springRate() * globalMult() * secs * eff;
    state.water += w;
    state.vigor = Math.min(state.vigorMax, state.vigor + vigorRegen() * secs);
    var msg = '离线 ' + fmtTime(capped) + '：灵泉自涌得水 ' + fmt(w);
    if (state.auto) {
      // 自动修炼按半速结算
      var cycles = secs * 0.5;
      while (cycles-- > 0) {
        if (state.vigor >= vigorCost()) { state.vigor -= vigorCost(); var g = resinYield(); state.resin += g; state.totalResin += g; }
        if (state.resin >= resinPerRefine()) { state.resin -= resinPerRefine(); var inc = incenseYield(); state.incense += inc; state.totalIncense += inc; state.xp += inc * xpPerIncense(); }
      }
      msg += '，自动修炼亦有进益';
    }
    state.lastSeen = now;
    log('🌙 ' + msg);
  }

  // —— 渲染 ——
  function fmt(n) {
    n = Math.floor(n);
    if (n < 1000) return '' + n;
    if (n < 1e6) return (n / 1e3).toFixed(n < 1e4 ? 2 : 1).replace(/\.?0+$/, '') + 'k';
    if (n < 1e9) return (n / 1e6).toFixed(2).replace(/\.?0+$/, '') + 'M';
    return (n / 1e9).toFixed(2) + 'B';
  }
  function fmtTime(ms) {
    var s = Math.floor(ms / 1000);
    var h = Math.floor(s / 3600); s -= h * 3600;
    var m = Math.floor(s / 60); s -= m * 60;
    if (h) return h + '时' + m + '分';
    if (m) return m + '分' + s + '秒';
    return s + '秒';
  }
  function bar(sel, val, max) {
    var el = root.querySelector(sel);
    if (el) el.style.width = Math.max(0, Math.min(100, max ? val / max * 100 : 0)) + '%';
  }

  function render() {
    if (!root) return;
    var g = globalMult();
    // 资源
    setT('[data-xx="water"]', fmt(state.water));
    setT('[data-xx="vigor"]', fmt(state.vigor) + '/' + fmt(state.vigorMax));
    setT('[data-xx="resin"]', fmt(state.resin));
    setT('[data-xx="incense"]', fmt(state.incense));
    setT('[data-xx="soul"]', fmt(state.soul));
    bar('[data-xx="vigor-bar"]', state.vigor, state.vigorMax);

    // 境界 + 修为
    setT('[data-xx="realm"]', REALMS[state.realm]);
    setT('[data-xx="realm-flav"]', REALM_FLAVOR[state.realm]);
    setT('[data-xx="xp"]', fmt(state.xp) + ' / ' + (isFinite(xpNeed()) ? fmt(xpNeed()) : '∞'));
    bar('[data-xx="xp-bar"]', state.xp, isFinite(xpNeed()) ? xpNeed() : 1);
    setT('[data-xx="inc-total"]', fmt(state.totalIncense));
    setT('[data-xx="gm"]', '×' + g.toFixed(2));

    // 按钮态
    toggle('[data-xx="btn-jie"]', state.vigor >= vigorCost());
    toggle('[data-xx="btn-refine"]', state.resin >= resinPerRefine());
    toggle('[data-xx="btn-break"]', state.xp >= xpNeed());
    var pb = root.querySelector('[data-xx="btn-prestige"]');
    if (pb) { pb.style.display = canPrestige() ? '' : 'none'; pb.textContent = '🕊 转生（+' + soulGain() + ' 香魂）'; }

    // 科技树
    var tw = root.querySelector('[data-xx="tech"]');
    if (tw) {
      tw.innerHTML = TECH.map(function (t) {
        var lv = state.tech[t.key];
        var maxed = lv >= TECH_MAX;
        var c = techCost(t);
        var can = !maxed && state.incense >= c;
        return '<div class="xx-tech-cell' + (maxed ? ' maxed' : '') + '">' +
          '<div class="xx-tech-head"><span class="xx-tech-ico">' + t.icon + '</span>' +
          '<span class="xx-tech-name">' + t.name + ' <b>Lv.' + lv + '</b></span></div>' +
          '<div class="xx-tech-desc">' + t.desc + '</div>' +
          '<button class="xx-tech-btn' + (can ? ' on' : '') + '" data-act="tech" data-tech="' + t.key + '"' + (maxed ? ' disabled' : '') + '>' +
          (maxed ? '已至顶' : '升级 · ' + fmt(c) + ' 香品') + '</button></div>';
      }).join('');
    }
  }
  function setT(sel, t) { var el = root && root.querySelector(sel); if (el) el.textContent = t; }
  function toggle(sel, ok) { var el = root && root.querySelector(sel); if (el) el.classList.toggle('dim', !ok); }

  function buildLayout() {
    root.innerHTML =
      '<div class="xx-top">' +
        '<div class="xx-realm"><span class="xx-realm-name" data-xx="realm">凡木</span>' +
          '<span class="xx-gm" data-xx="gm">×1.00</span></div>' +
        '<div class="xx-flav" data-xx="realm-flav"></div>' +
        '<div class="xx-xp"><div class="xx-xp-bar"><div class="xx-xp-fill" data-xx="xp-bar"></div></div>' +
          '<span class="xx-xp-txt" data-xx="xp">0 / 60</span></div>' +
      '</div>' +
      '<div class="xx-res">' +
        res('💧', '水', 'water', false) +
        res('🩸', '元气', 'vigor', true) +
        res('🟤', '香脂', 'resin', false) +
        res('🪷', '香品', 'incense', false) +
      '</div>' +
      '<div class="xx-actions">' +
        '<button class="xx-act xx-draw" data-act="draw">汲水</button>' +
        '<button class="xx-act" data-act="jie" data-xx="btn-jie">结香<small>耗元气</small></button>' +
        '<button class="xx-act" data-act="refine" data-xx="btn-refine">炼香<small>耗香脂</small></button>' +
        '<button class="xx-act xx-break" data-act="break" data-xx="btn-break">突破</button>' +
        '<button class="xx-act xx-prestige" data-act="prestige" data-xx="btn-prestige" style="display:none">转生</button>' +
        '<button class="xx-act xx-auto" data-act="auto">自动修炼：关</button>' +
      '</div>' +
      '<div class="xx-tech-title">香道科技 <span class="xx-tech-sub">累计香品 <b data-xx="inc-total">0</b> · 香魂 <b data-xx="soul">0</b></span></div>' +
      '<div class="xx-tech" data-xx="tech"></div>' +
      '<div class="xx-log" data-xx="log"></div>';
    // 自动按钮文案同步
    syncAuto();
  }
  function res(ico, name, key, showBar) {
    return '<div class="xx-res-cell"><span class="xx-res-ico">' + ico + '</span>' +
      '<span class="xx-res-name">' + name + '</span>' +
      '<span class="xx-res-val" data-xx="' + key + '">0</span>' +
      (showBar ? '<div class="xx-vigor-bar"><div class="xx-vigor-fill" data-xx="vigor-bar"></div></div>' : '') +
      '</div>';
  }
  function syncAuto() {
    var b = root.querySelector('[data-act="auto"]');
    if (b) b.textContent = '自动修炼：' + (state.auto ? '开' : '关');
  }

  function onClick(e) {
    var btn = e.target.closest('[data-act]');
    if (!btn) return;
    var act = btn.dataset.act;
    if (act === 'draw') actDrawWater();
    else if (act === 'jie') actJie();
    else if (act === 'refine') actRefine();
    else if (act === 'break') actBreak();
    else if (act === 'prestige') actPrestige();
    else if (act === 'auto') { toggleAuto(); }
    else if (act === 'tech') {
      var t = TECH.filter(function (x) { return x.key === btn.dataset.tech; })[0];
      if (t) actTech(t);
    }
  }

  function init() {
    root = document.getElementById('xx-root');
    if (!root || inited) return;
    inited = true;
    state = load();
    settleOffline();
    buildLayout();
    render();
    log('🌿 沉香·放置修炼 · 已载入');
    root.addEventListener('click', onClick);
    timer = setInterval(tick, 1000);
    window.addEventListener('beforeunload', save);
    setInterval(save, SAVE_MS);
    report();
  }

  document.addEventListener('DOMContentLoaded', init);
  window.XiuXiang = { init: init };
})();
