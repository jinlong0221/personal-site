// 灵圃·沉香养成 —— 核心逻辑（状态 / 养成 / 结香 / 收藏 / 成就 / 彩蛋）
// 纯逻辑层：不碰 DOM，所有结果通过返回值与 state 暴露给 ui.js。
// 数据全部存 localStorage（key: lx_nurture_v1），零后端。
(function () {
  'use strict';

  var KEY = 'lx_nurture_v1';

  // ---------- 可调参数 ----------
  var CFG = {
    offlineGrowthPerSec: 1 / 30,   // 离线/挂机成长：每 30 秒 +1
    offlineGrowthCap: 120,         // 单次回到页面最多补的成长
    vigorRegenPerSec: 1 / 60,      // 元气自然恢复：每 60 秒 +1
    vigorRegenCap: 40,
    incenseUnlockGrowth: 400,      // 达到此成长值（成树）解锁造香
    ancientGrowth: 760,            // 古木阶阈值
    harvestMinResin: 50,           // 结香达到此值可采收
    clickEggNeeded: 50,            // 连点彩蛋触发次数
    clickEggWindow: 8000          // 连点窗口（毫秒）
  };

  // 成长阶段：阈值递增
  var STAGES = [
    { key: 'seed',    name: '一粒种子', min: 0,   tip: '埋入灵圃，静待破土。' },
    { key: 'sprout',  name: '初生幼苗', min: 60,  tip: '两片子叶怯生生探出泥土。' },
    { key: 'sapling', name: '青葱树苗', min: 200, tip: '枝干渐直，已能遮一小片荫。' },
    { key: 'tree',    name: '亭亭成树', min: 400, tip: '可以动手“造香”了——沉香生于伤。' },
    { key: 'ancient', name: '参天古木', min: 760, tip: '百年气质，结香愈醇。' }
  ];

  // 日常打理：growth 增、vigor 增、冷却（秒）
  var CARE = {
    water: { name: '浇水', icon: '💧', growth: 8,  vigor: 6,  cd: 18, note: '清泉一瓢，元气稍复。' },
    sun:   { name: '沐阳', icon: '☀️', growth: 6,  vigor: 8,  cd: 24, note: '向阳而生，白日方好。', dayOnly: true, nightVigor: 2 },
    pest:  { name: '驱虫', icon: '🍃', growth: 10, vigor: 3,  cd: 45, note: '驱去啃噬之患，护住生气。' },
    wind:  { name: '听风', icon: '🎐', growth: 5,  vigor: 4,  cd: 22, note: '夜阑听风，心境清宁。', nightOnly: true, dayVigor: 2 }
  };

  // 造香方法：cost 元气、yield 结香、prefer 偏好品类、risk 折损风险
  var INCENSE = {
    nail: { name: '打钉', icon: '🔨', cost: 8,  yield: 6,  prefer: '生结', risk: 0.02, tip: '铁钉入干，徐徐泌脂，最是稳妥。' },
    burn: { name: '火灼', icon: '🔥', cost: 14, yield: 11, prefer: '熟结', risk: 0.06, tip: '火痕灼处，脂液奔涌，险中得快。' },
    chop: { name: '砍伤', icon: '🪓', cost: 20, yield: 17, prefer: '生结', risk: 0.12, tip: '利斧斫伤，重伤换厚脂，最是凶险。' },
    ant:  { name: '蚁蛀', icon: '🐜', cost: 10, yield: 8,  prefer: '虫漏', risk: 0.04, tip: '引蚁蛀蚀，蜿蜒成漏，罕得虫漏。' }
  };

  // 品类与品级
  var TYPES = ['生结', '熟结', '虫漏', '脱落', '奇楠'];
  var GRADES = ['下', '中', '上', '特级', '奇楠'];

  // 香道等级（按收藏总数）
  var RANKS = [
    { min: 0,   name: '初学弟子' },
    { min: 8,   name: '香童' },
    { min: 24,  name: '香人' },
    { min: 56,  name: '香师' },
    { min: 100, name: '香宗' },
    { min: 200, name: '香圣' }
  ];

  // 成就（icon 用 emoji，纯展示）
  var ACHV = [
    { id: 'first',   name: '初结香',   icon: '🌱', desc: '第一次采收沉香' },
    { id: 'ten',     name: '一炷清香', icon: '🕯️', desc: '累计采收 10 块' },
    { id: 'hundred', name: '香阁百珍', icon: '🗄️', desc: '收藏达到 100 块' },
    { id: 'tree',    name: '亭亭如盖', icon: '🌳', desc: '养成树长成“成树”' },
    { id: 'ancient', name: '古木参天', icon: '🏯', desc: '养成树长成“古木”' },
    { id: 'qinan',   name: '奇楠现世', icon: '💎', desc: '采得一块奇楠' },
    { id: 'streak5', name: '五木同春', icon: '🤝', desc: '连续 5 天来照料' },
    { id: 'night',   name: '夜访',     icon: '🐱', desc: '遇见深夜来访的小兽' },
    { id: 'petal',   name: '落英',     icon: '🌸', desc: '惹得树精落英缤纷' },
    { id: 'fest',    name: '节气之子', icon: '📅', desc: '赶上任一节气彩蛋' },
    { id: 'worm',    name: '虫师',     icon: '🐛', desc: '用“蚁蛀”采收 10 次' },
    { id: 'master',  name: '香道大宗', icon: '👑', desc: '香道等级达“香宗”' }
  ];

  // 24 节气（近似公历，2026）—— 当天首访触发彩蛋
  var FESTIVALS = {
    '01-05': { n: '小寒', t: '小寒料峭，围炉待香。' },
    '01-20': { n: '大寒', t: '大寒至极，藏养其根。' },
    '02-04': { n: '立春', t: '立春阳气转，新绿将萌。' },
    '02-18': { n: '雨水', t: '雨水润物，最宜浇灌。' },
    '03-05': { n: '惊蛰', t: '惊蛰雷动，百虫始醒——留意驱虫。' },
    '03-20': { n: '春分', t: '春分昼夜均，灵圃生机最盛。' },
    '04-05': { n: '清明', t: '清明前后，种树恰逢其时。' },
    '04-20': { n: '谷雨', t: '雨生百谷，树沐甘霖，元气大涨。' },
    '05-05': { n: '立夏', t: '立夏风暖，枝叶舒张。' },
    '05-21': { n: '小满', t: '小满未满，脂意初盈。' },
    '06-05': { n: '芒种', t: '芒种忙种，亦忙照料。' },
    '06-21': { n: '夏至', t: '夏至阳极，白昼最长，沐阳最宜。' },
    '07-07': { n: '小暑', t: '小暑温风，莫教树中暑。' },
    '07-22': { n: '大暑', t: '大暑酷烈，多浇清水。' },
    '08-07': { n: '立秋', t: '立秋凉意生，一岁将收。' },
    '08-23': { n: '处暑', t: '处暑暑气止，夜风渐清。' },
    '09-07': { n: '白露', t: '白露凝霜，听风正好。' },
    '09-23': { n: '秋分', t: '秋分又均，桂香浮动的时节。' },
    '10-08': { n: '寒露', t: '寒露清寒，脂更凝润。' },
    '10-23': { n: '霜降', t: '霜降叶染，古木愈醇。' },
    '11-07': { n: '立冬', t: '立冬藏养，静待来春。' },
    '11-22': { n: '小雪', t: '小雪初寒，围炉亦暖。' },
    '12-07': { n: '大雪', t: '大雪纷扬，灵圃披素。' },
    '12-21': { n: '冬至', t: '冬至阳生，一线生机始于此。' }
  };

  // 深夜小兽（23:00–05:00 可能来访）
  var NIGHT_BEASTS = [
    { icon: '🐱', name: '狸奴', say: '夜深了，我替你守着这圃沉香。' },
    { icon: '🦊', name: '玄狐', say: '听风的人，才听得见树说话。' },
    { icon: '🦉', name: '青鸮', say: '咕——月色正好，莫负清宵。' },
    { icon: '🐇', name: '雪兔', say: '我偷来一点夜露，予你养树。' },
    { icon: '🦌', name: '白泽', say: '通万物之情者，方知沉香之贵。', rare: true }
  ];

  // 连点彩蛋：树精低语（古卷一句）
  var TREE_WHISPER = [
    '树精低语：世人爱香，却怕树伤；殊不知伤处，方结奇香。',
    '树精低语：百年一木，一木一生。你待它真心，它报你以香。',
    '树精低语：落英不是凋零，是把气力还给了根。'
  ];

  // 沉香小识（科普，折叠展示）
  var LORE = [
    { q: '沉香到底是什么？', a: '沉香并非普通木材，而是瑞香科沉香属树木（如土沉香）受伤后，伤口处分泌树脂、经真菌感染与长年醇化，形成的含有芳香油脂的“结香”部分。木质疏松处朽去，留下的油润香脂才是沉香。' },
    { q: '为什么“受伤”才结香？', a: '健康树木不结香。雷击、风折、虫蛀、兽咬或人为砍伤打钉，都会触发树木的自我保护——伤口泌出树脂抗菌愈伤，久而久之油脂沉积、醇化变色，便是沉香。故有“沉香生于伤”之说。' },
    { q: '生结 / 熟结 / 虫漏 有何不同？', a: '生结：活树受伤即时结香；熟结：树死之后，树干朽烂、香脂醇化留存；虫漏：虫蚁蛀蚀蜿蜒成香，纹路奇巧；脱落：枝干自然断落处结香。古法更有“打钉”“火灼”“砍伤”等人为催香之法。' },
    { q: '奇楠（伽楠）为何最贵？', a: '奇楠是沉香中的极品，质软、油润、入口有凉甜感，常温下亦香韵悠长。成因多与特殊菌种、漫长醇化有关，产量极稀，故有“一片万钱”之说。' },
    { q: '品级怎么看？', a: '行家看“油脂含量、香气、产地、熟化程度”。本课以结香饱满度与采收时树之状态拟分：下、中、上、特级，与极少数奇楠。重在趣味，不作交易依据。' }
  ];

  // ---------- 工具 ----------
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function now() { return Date.now(); }
  function dayKey(ts) {
    var d = new Date(ts);
    return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
  }
  function isNight(ts) {
    var h = new Date(ts).getHours();
    return h >= 23 || h < 5;
  }
  function seasonOf(ts) {
    var m = new Date(ts).getMonth() + 1;
    if (m >= 3 && m <= 5) return 'spring';
    if (m >= 6 && m <= 8) return 'summer';
    if (m >= 9 && m <= 11) return 'autumn';
    return 'winter';
  }
  function festivalKey(ts) {
    var d = new Date(ts);
    var m = ('0' + (d.getMonth() + 1)).slice(-2);
    var day = ('0' + d.getDate()).slice(-2);
    return m + '-' + day;
  }
  function pick(a) { return a[Math.floor(Math.random() * a.length)]; }

  // ---------- 状态 ----------
  var S = null;

  function freshState() {
    var t = now();
    return {
      v: 1,
      plantedAt: t,
      lastSeen: t,
      growth: 0,
      vigor: 100,
      resin: 0,
      dead: false,
      deaths: 0,
      totalHarvest: 0,
      antHarvest: 0,
      collection: [],          // {id,type,grade,weight,ts,ageDays,method}
      achv: {},                // id -> ts
      lastCare: {},            // action -> ts
      careStreak: 0,
      lastCareDay: '',
      clicks: 0,
      clickAt: 0,
      nightSeen: {},           // dayKey -> true
      festSeen: {},            // 'MM-DD' -> true
      log: [],                 // {t, text, kind}
      beast: null,             // 当前/上次来访小兽
      petalSkin: 0             // 夜兽赠予的装饰（0 无 / 1 奇花）
    };
  }

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (raw) {
        var s = JSON.parse(raw);
        if (s && s.v === 1) return s;
      }
    } catch (e) {}
    return null;
  }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {}
    // 通知外部（云端同步等）：本地存档已更新
    try { window.dispatchEvent(new CustomEvent('nurture:save', { detail: S })); } catch (e) {}
  }

  function init() {
    S = load();
    if (!S) { S = freshState(); save(); }
    return S;
  }

  function get() { return S; }

  function logPush(text, kind) {
    S.log.unshift({ t: now(), text: text, kind: kind || 'info' });
    if (S.log.length > 60) S.log.length = 60;
  }

  function achieve(id) {
    if (S.achv[id]) return false;
    S.achv[id] = now();
    var a = ACHV.filter(function (x) { return x.id === id; })[0];
    if (a) logPush('成就达成 · ' + a.name + '（' + a.desc + '）', 'achv');
    return true;
  }

  // ---------- 阶段 / 等级 ----------
  function stageOf(growth) {
    var st = STAGES[0];
    for (var i = 0; i < STAGES.length; i++) if (growth >= STAGES[i].min) st = STAGES[i];
    return st;
  }
  function nextStage(growth) {
    for (var i = 0; i < STAGES.length; i++) if (growth < STAGES[i].min) return STAGES[i];
    return null;
  }
  function rankOf(total) {
    var r = RANKS[0];
    for (var i = 0; i < RANKS.length; i++) if (total >= RANKS[i].min) r = RANKS[i];
    return r.name;
  }
  function ageDays() { return Math.floor((now() - S.plantedAt) / 86400000); }

  // ---------- 冷却 ----------
  function cdLeft(action) {
    var def = CARE[action] || INCENSE[action];
    if (!def) return 0;
    var last = S.lastCare[action] || 0;
    var left = def.cd - (now() - last) / 1000;
    return left > 0 ? Math.ceil(left) : 0;
  }

  // ---------- 打理 ----------
  function care(action) {
    if (S.dead) return { ok: false, msg: '树已枯，先重新栽一株吧。' };
    var def = CARE[action];
    if (!def) return { ok: false, msg: '未知操作。' };
    var left = cdLeft(action);
    if (left > 0) return { ok: false, msg: def.name + '冷却中，还需 ' + left + ' 秒。' };

    var night = isNight(now());
    if (def.dayOnly && night) return { ok: false, msg: '夜深露重，白日方可沐阳。' };
    if (def.nightOnly && !night) return { ok: false, msg: '白日风噪，入夜方能听风。' };

    var vigorGain = def.vigor;
    if (def.dayOnly && night) vigorGain = def.nightVigor;
    if (def.nightOnly && !night) vigorGain = def.dayVigor;

    S.growth = clamp(S.growth + def.growth, 0, 99999);
    S.vigor = clamp(S.vigor + vigorGain, 0, 100);
    S.lastCare[action] = now();

    // 连续养护天数
    var dk = dayKey(now());
    if (S.lastCareDay !== dk) {
      var prev = new Date(now() - 86400000);
      var prevKey = prev.getFullYear() + '-' + (prev.getMonth() + 1) + '-' + prev.getDate();
      S.careStreak = (S.lastCareDay === prevKey) ? (S.careStreak + 1) : 1;
      S.lastCareDay = dk;
      if (S.careStreak >= 5) achieve('streak5');
    }

    var before = stageOf(S.growth - def.growth);
    var after = stageOf(S.growth);
    var msg = def.note;
    if (after.key !== before.key) {
      msg = '🌿 长大了！现在是「' + after.name + '」——' + after.tip;
      if (after.key === 'tree') achieve('tree');
      if (after.key === 'ancient') achieve('ancient');
    }
    logPush(def.name + '：' + def.note, 'care');
    save();
    return { ok: true, msg: msg, stageUp: after.key !== before.key };
  }

  // ---------- 造香 ----------
  function incense(method) {
    if (S.dead) return { ok: false, msg: '树已枯。' };
    if (S.growth < CFG.incenseUnlockGrowth) return { ok: false, msg: '树还太小，成树方能造香。' };
    var def = INCENSE[method];
    if (!def) return { ok: false, msg: '未知造香法。' };
    var left = cdLeft(method);
    if (left > 0) return { ok: false, msg: def.name + '冷却中，还需 ' + left + ' 秒。' };
    if (S.vigor < def.cost) return { ok: false, msg: '元气不足（需 ' + def.cost + '），先浇水沐阳养一养。' };

    S.vigor = clamp(S.vigor - def.cost, 0, 100);
    S.lastCare[method] = now();

    // 折损风险：元气被掏空或概率触发 → 枯
    var dead = (S.vigor <= 0) || (Math.random() < def.risk);
    if (dead) {
      S.dead = true;
      S.deaths += 1;
      S.resin = 0;
      logPush('⚠️ ' + def.name + '过度，树身枯槁……灵圃暂寂。可重新栽一株，旧藏仍在。', 'bad');
      save();
      return { ok: false, dead: true, msg: '树枯了。伤其躯，亦伤其心——重新栽一株吧，收藏阁会替你留住过往。' };
    }

    var vf = 0.6 + 0.4 * (S.vigor / 100);
    S.resin = clamp(S.resin + def.yield * vf, 0, 100);
    var msg = def.tip + '（结香 +' + Math.round(def.yield * vf) + '）';
    if (S.resin >= 95) msg += ' 脂已将满，可采收了。';
    logPush(def.name + '造香，结香至 ' + Math.round(S.resin) + '。', 'incense');
    save();
    return { ok: true, msg: msg, resin: S.resin };
  }

  // ---------- 采收 ----------
  function harvest() {
    if (S.dead) return { ok: false, msg: '树已枯。' };
    if (S.resin < CFG.harvestMinResin) return { ok: false, msg: '结香尚浅（' + Math.round(S.resin) + '%），满 ' + CFG.harvestMinResin + '% 方可采收。' };

    var r = S.resin;
    // 品类：以最后一种造香法偏好为主，未记录则取生结
    var method = lastIncenseMethod();
    var def = method ? INCENSE[method] : null;
    var type = def ? def.prefer : '生结';

    // 品级由结香饱满度决定
    var gradeIdx;
    if (r >= 95) gradeIdx = 3;        // 特级
    else if (r >= 85) gradeIdx = 2;   // 上
    else if (r >= 70) gradeIdx = 1;   // 中
    else gradeIdx = 0;                // 下

    // 奇楠概率：基础 + 蚁蛀/古木加成 + 怜悯（久无奇楠递增）
    var qnChance = 0.01;
    if (method === 'ant') qnChance += 0.05;
    if (stageOf(S.growth).key === 'ancient') qnChance += 0.03;
    var pity = Math.min(0.06, S.totalHarvest > 0 ? (S.totalHarvest % 25) * 0.002 : 0);
    qnChance += pity;
    var isQinan = Math.random() < qnChance;

    var grade, weight, typeFinal;
    if (isQinan) {
      grade = '奇楠'; typeFinal = '奇楠'; weight = Math.round((3 + Math.random() * 9) * 10) / 10;
    } else {
      grade = GRADES[gradeIdx]; typeFinal = type;
      var base = [1, 4, 8, 15][gradeIdx];
      var top = [5, 10, 18, 30][gradeIdx];
      weight = Math.round((base + Math.random() * (top - base)) * 10) / 10;
    }

    var piece = {
      id: 'p' + now() + Math.floor(Math.random() * 1000),
      type: typeFinal, grade: grade, weight: weight,
      ts: now(), ageDays: ageDays(), method: method || 'natural'
    };
    S.collection.unshift(piece);
    S.totalHarvest += 1;
    if (method === 'ant') S.antHarvest += 1;
    S.resin = 0;

    logPush('🌟 采收：' + typeFinal + '·' + grade + ' ' + weight + 'g（树龄 ' + piece.ageDays + ' 天）', 'harvest');
    achieve('first');
    if (S.totalHarvest >= 10) achieve('ten');
    if (S.totalHarvest >= 100) achieve('hundred');
    if (isQinan) achieve('qinan');
    if (S.antHarvest >= 10) achieve('worm');
    if (rankOf(S.totalHarvest) === '香宗') achieve('master');

    save();
    return { ok: true, piece: piece, isQinan: isQinan };
  }

  function lastIncenseMethod() {
    // 找最近一次造香时间戳
    var best = null, bestT = 0;
    for (var k in INCENSE) {
      var t = S.lastCare[k] || 0;
      if (t > bestT) { bestT = t; best = k; }
    }
    return best;
  }

  // ---------- 重新栽 ----------
  function replant() {
    var keep = {
      v: 1,
      plantedAt: now(),
      lastSeen: now(),
      growth: 0, vigor: 100, resin: 0, dead: false,
      deaths: S.deaths,
      totalHarvest: S.totalHarvest,
      antHarvest: S.antHarvest,
      collection: S.collection,    // 收藏阁永存
      achv: S.achv,
      lastCare: {}, careStreak: S.careStreak, lastCareDay: S.lastCareDay,
      clicks: 0, clickAt: 0,
      nightSeen: {}, festSeen: {},
      log: S.log, beast: null, petalSkin: S.petalSkin
    };
    S = keep;
    logPush('🌱 新株入土。旧香犹在阁中，来日再结新香。', 'info');
    save();
    return S;
  }

  // ---------- 回到页面：离线成长 + 彩蛋 ----------
  // 返回本帧发生的“事件”数组，供 ui 弹层/动画
  function tick() {
    var events = [];
    var t = now();
    var elapsed = (t - S.lastSeen) / 1000;
    if (elapsed > 5 && !S.dead) {
      var g = Math.min(CFG.offlineGrowthCap, CFG.offlineGrowthPerSec * elapsed);
      if (g > 0.5) {
        S.growth = clamp(S.growth + g, 0, 99999);
        events.push({ type: 'offline', text: '离圃期间，树自生长 +' + Math.round(g) + ' 成长。' });
      }
      var v = Math.min(CFG.vigorRegenCap, CFG.vigorRegenPerSec * elapsed);
      if (v > 0.5) S.vigor = clamp(S.vigor + v, 0, 100);
    }

    // 节气彩蛋（当天首访）
    var fk = festivalKey(t);
    if (FESTIVALS[fk] && !S.festSeen[fk]) {
      S.festSeen[fk] = true;
      S.growth = clamp(S.growth + 30, 0, 99999);
      S.vigor = clamp(S.vigor + 15, 0, 100);
      var f = FESTIVALS[fk];
      logPush('📅 ' + f.n + '：' + f.t, 'fest');
      achieve('fest');
      events.push({ type: 'fest', title: f.n, text: f.t });
    }

    // 深夜小兽（23:00–05:00，当天未访，60% 概率）
    var dk = dayKey(t);
    if (isNight(t) && !S.nightSeen[dk] && Math.random() < 0.6) {
      S.nightSeen[dk] = true;
      var beast = pick(NIGHT_BEASTS);
      S.beast = beast;
      S.vigor = clamp(S.vigor + 8, 0, 100);
      if (beast.rare) S.petalSkin = 1;
      logPush(beast.icon + ' ' + beast.name + '夜访：' + beast.say, 'night');
      achieve('night');
      events.push({ type: 'night', beast: beast });
    }

    S.lastSeen = t;
    save();
    return events;
  }

  // ---------- 连点彩蛋 ----------
  function registerClick() {
    var t = now();
    if (t - S.clickAt > CFG.clickEggWindow) { S.clicks = 0; }
    S.clicks += 1; S.clickAt = t;
    if (S.clicks >= CFG.clickEggNeeded) {
      S.clicks = 0;
      var w = pick(TREE_WHISPER);
      logPush(w, 'petal');
      achieve('petal');
      save();
      return { triggered: true, text: w };
    }
    save();
    return { triggered: false };
  }

  // ---------- 导出 ----------
  window.Nurture = {
    CFG: CFG, STAGES: STAGES, CARE: CARE, INCENSE: INCENSE,
    TYPES: TYPES, GRADES: GRADES, RANKS: RANKS, ACHV: ACHV,
    FESTIVALS: FESTIVALS, NIGHT_BEASTS: NIGHT_BEASTS, LORE: LORE,
    init: init, get: get, save: save,
    stageOf: stageOf, nextStage: nextStage, rankOf: rankOf, ageDays: ageDays,
    cdLeft: cdLeft, care: care, incense: incense, harvest: harvest,
    replant: replant, tick: tick, registerClick: registerClick,
    isNight: isNight, seasonOf: seasonOf, festivalKey: festivalKey,
    achieve: achieve, logPush: logPush,
    dayKey: dayKey
  };
})();
