/*!
 * tools/lottery.js — 彩票选号器（工具箱·按需加载子模块）
 *
 * 四种彩：双色球 / 大乐透 / 福彩3D / 排列3。
 * 三大块：① 随机选号（7 种趣味玩法）② 历年统计 ③ 往期查询。
 *
 * 规矩（用户硬要求）：
 *   - 同注内号码绝不重复（红球/前区/后区按「无放回抽样」；福彩3D/排列3 三位各自独立 0–9）。
 *   - 历史数据是打包好的静态快照（static/data/lottery/*.json），运行时不再联网，符合站点「不联网」原则。
 *   - 全部在浏览器里用 crypto 随机数生成，绝不联网、绝不上传、绝不留存。
 *
 * 数据来源：第三方聚合接口（按福彩/体彩官网口径交叉校验），页面明示「仅供参考，以官方为准」。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $ = _.$, $$ = _.$$;
  var panelOf = _.panelOf, toast = _.toast, clearToast = _.clearToast;

  // 彩种（与 JSON 的 groups 对应）。positions 给 3D/排列3 三位贴上百/十/个标签。
  var TYPES = [
    { id: 'ssq', name: '双色球' },
    { id: 'dlt', name: '大乐透' },
    { id: 'fc3d', name: '福彩3D' },
    { id: 'pls', name: '排列3' }
  ];

  // 7 种选法
  var MODES = [
    { id: 'rand', name: '纯随机', tip: '加密级随机，最干脆' },
    { id: 'drum', name: '摇奖机', tip: '号码球翻滚被摇出来' },
    { id: 'shake', name: '摇一摇', tip: '手机甩一甩 / 点按钮摇' },
    { id: 'dice', name: '骰子', tip: '骰子翻滚停下' },
    { id: 'slip', name: '抽签锦囊', tip: '国风签筒抽一支' },
    { id: 'date', name: '生日选号', tip: '用日期数字映射' },
    { id: 'hot', name: '冷热遗漏', tip: '追热 / 守冷 / 等遗漏' },
    { id: 'bal', name: '均衡型', tip: '区间分散 + 奇偶/大小配比 + 和值落常带' },
    { id: 'anti', name: '反人流大数', tip: '偏 32+ 大数，仅降低奖池平分' },
    { id: 'avoid', name: '避近期', tip: '排除最近 10 期已开号码' },
    { id: 'ai', name: '智能参谋', tip: '融合上述 + 每注附参谋说明' }
  ];

  // 智能策略玩法集合（区别于纯动画皮的玩法）
  var SMART = { bal: 1, anti: 1, avoid: 1, ai: 1 };

  var BIASES = [
    { id: 'hot', name: '追热号' },
    { id: 'cold', name: '守冷号' },
    { id: 'due', name: '等遗漏' }
  ];

  // 国风签文（抽签锦囊用），纯娱乐；扩池至 24 句 + 滑动窗口去重，连点不撞同一句
  var FORTUNES = [
    '上上签 · 时来天地皆同力，运去英雄不自由。',
    '上签 · 长风破浪会有时，直挂云帆济沧海。',
    '中签 · 沉舟侧畔千帆过，病树前头万木春。',
    '中签 · 山重水复疑无路，柳暗花明又一村。',
    '上上签 · 千淘万漉虽辛苦，吹尽狂沙始到金。',
    '平签 · 随风潜入夜，润物细无声。',
    '中签 · 会当凌绝顶，一览众山小。',
    '上签 · 春风得意马蹄疾，一日看尽长安花。',
    '平签 · 行到水穷处，坐看云起时。',
    '中签 · 宝剑锋从磨砺出，梅花香自苦寒来。',
    '上上签 · 海阔凭鱼跃，天高任鸟飞。',
    '平签 · 莫愁前路无知己，天下谁人不识君。',
    '上上签 · 大鹏一日同风起，扶摇直上九万里。',
    '上签 · 天生我材必有用，千金散尽还复来。',
    '上签 · 海内存知己，天涯若比邻。',
    '中签 · 千磨万击还坚劲，任尔东西南北风。',
    '中签 · 采得百花成蜜后，为谁辛苦为谁甜。',
    '中签 · 纸上得来终觉浅，绝知此事要躬行。',
    '平签 · 事了拂衣去，深藏身与名。',
    '平签 · 古今多少事，都付笑谈中。',
    '平签 · 醉卧沙场君莫笑，古来征战几人回。',
    '上签 · 落霞与孤鹜齐飞，秋水共长天一色。',
    '中签 · 欲买桂花同载酒，终不似少年游。',
    '上上签 · 福祸相依，转机在侧，静观其变。'
  ];

  var cache = {};      // id -> 已加载的 JSON
  var statCache = {};  // id -> 算好的统计
  var state = { type: 'ssq', tab: 'pick', mode: 'rand', bias: 'hot' };

  // ---------- 随机与抽样 ----------
  function rng(n) {                 // [0, n)
    var a = new Uint32Array(1);
    crypto.getRandomValues(a);
    return a[0] % n;
  }
  function pad2(n) { return n < 10 ? '0' + n : '' + n; }

  // 滑动窗口去重：从 pool 随机抽 1 条，避开最近 win 条用过的；窗口=池大小时即完美轮换（轮完一圈才允许重复）
  function pickDistinct(pool, recent, win) {
    win = win || pool.length;
    while (recent.length >= win) recent.shift(); // 先腾出窗口位：保证 avail 非空、窗口内永不重复
    var avail = pool.filter(function (x) { return recent.indexOf(x) < 0; });
    var pick = avail[rng(avail.length)];
    recent.push(pick);
    return pick;
  }

  // 灵魂签文案库：按调性分类、每类多条；interpret 按号码特征定型性后随机抽 + 去重，保留“按特征定调性”的灵魂
  var SOUL_LINES = {
    '孤勇型': ['宁为玉碎，不走寻常路。', '一身肝胆，独行其是。', '猛志逸四海，骞翮思远翥。', '虽千万人，吾往矣。'],
    '稳重型': ['四平八稳，步步为营。', '静水流深，稳者自安。', '安步当车，行稳致远。', '厚德载物，履道坦坦。'],
    '血脉相连型': ['同气连枝，携手并进。', '如竹有节，相倚而生。', '比目连枝，福祸相依。', '星月交辉，彼此成全。'],
    '情深型': ['数理相缠，缘分使然。', '不解之缘，妙手偶得。', '因缘际会，一往而深。', '心有灵犀，数亦相通。'],
    '凌云型': ['欲穷千里目，更上一层楼。', '长风破浪，云帆沧海。', '海到无边天作岸。', '九万里风鹏正举。'],
    '中庸型': ['执两用中，不偏不倚。', '过犹不及，中道而立。', '允执厥中，和而不同。', '不偏之谓中，不易之谓庸。'],
    '炽盛型': ['大鹏一日同风起，扶摇直上九万里。', '气吞万里如虎。', '烈火烹油，鲜花着锦。', '鸿鹄高翔，一举千里。'],
    '潜龙型': ['潜龙在渊，待时而动。', '藏器于身，待时而发。', '韬光养晦，静水流深。', '积厚流光，后发制人。'],
    '随缘型': ['命里有时终须有，随缘便是自在。', '云在青天水在瓶。', '竹杖芒鞋轻胜马，一蓑烟雨任平生。', '得之我幸，失之我命。']
  };
  var recentSoul = {};        // 调性名 -> 最近用过的文案（按类隔离的滑动窗口）
  var recentFortune = [];     // 锦囊最近用过的签文（滑动窗口）

  // 无放回抽样：从 [lo, lo+size-1] 取 count 个互不相同的数
  function sampleNoReplace(size, count, lo) {
    lo = lo || 0;
    var pool = [];
    for (var i = 0; i < size; i++) pool.push(lo + i);
    for (var k = 0; k < count; k++) {
      var j = k + rng(size - k);
      var t = pool[k]; pool[k] = pool[j]; pool[j] = t;
    }
    return pool.slice(0, count).sort(function (a, b) { return a - b; });
  }

  // 加权无放回抽样（冷热遗漏用）：weightOf(idx)->数值。加权挑选本身用 crypto 浮点，避免混用 RNG 源。
  function randFloat() {
    var a = new Uint32Array(2);
    crypto.getRandomValues(a);
    return (a[0] / 4294967296) + (a[1] / 4294967296) * (1 / 4294967296);
  }
  function weightedSampleNoReplace(size, count, lo, weightOf) {
    lo = lo || 0;
    var idx = [];
    for (var i = 0; i < size; i++) idx.push(i);
    var chosen = [];
    for (var c = 0; c < count; c++) {
      var total = 0, w = [];
      for (var k = 0; k < idx.length; k++) { var wv = Math.max(0.0001, weightOf(idx[k])); w.push(wv); total += wv; }
      var r = randFloat() * total, acc = 0, pick = 0;
      for (var m = 0; m < idx.length; m++) { acc += w[m]; if (r <= acc) { pick = m; break; } }
      chosen.push(idx[pick]);
      idx.splice(pick, 1);
    }
    return chosen.map(function (i) { return lo + i; }).sort(function (a, b) { return a - b; });
  }

  // 一个彩种的一组配置
  function groupsOf(data) { return (data && data.groups) || []; }

  // 生成一注：返回 {r:[...], b:[...]}，遵守「同注内不重复」规则
  function pickOne(data, mode, opts) {
    var groups = groupsOf(data);
    var res = { r: [], b: [] };
    var stats = statCache[data.type];
    groups.forEach(function (g) {
      var size = g.hi - g.lo + 1;
      if (g.sample) {
        var nums;
        if (mode === 'hot' && stats) {
          var w = function (i) {
            var n = lo_i(g, i);
            if (opts.bias === 'hot') return Math.pow(stats.freq[g.key][n] + 1, 1.6);
            if (opts.bias === 'cold') return Math.pow((stats.maxFreq[g.key] - (stats.freq[g.key][n] || 0)) + 1, 1.4);
            return Math.pow((stats.miss[g.key][n] || 0) + 1, 1.3); // due
          };
          nums = weightedSampleNoReplace(size, g.cnt, g.lo, w);
        } else if (mode === 'date' && opts.date) {
          nums = fromDate(g, opts.date);
        } else {
          nums = sampleNoReplace(size, g.cnt, g.lo);
        }
        if (g.key === 'b') res.b = nums; else res.r = nums.concat(res.r);
      } else {
        // 位置型（3D/排列3）：每位独立 0–9，允许跨位重复
        var pos = [];
        for (var p = 0; p < g.cnt; p++) pos.push(g.lo + rng(size));
        res.r = pos;
      }
    });
    return res;
  }
  function lo_i(g, i) { return g.lo + i; }

  // 生日/纪念日：从日期数字里挑落在 [lo,hi] 的候选，去重后补足
  function fromDate(g, dateStr) {
    var digits = String(dateStr).replace(/\D/g, '').split('').map(Number);
    var cand = [];
    var seen = {};
    digits.forEach(function (d) {
      // 年份四位拆开、月日两位拆开；直接把每个数字当候选，再考虑两位组合
      var v = d;
      if (v >= g.lo && v <= g.hi && !seen[v]) { seen[v] = 1; cand.push(v); }
    });
    // 两位组合（如 1990 -> 19,90, 05->5, 20->20）
    var parts = String(dateStr).match(/\d+/g) || [];
    parts.forEach(function (p) {
      if (p.length >= 2) {
        var v = parseInt(p, 10);
        if (v >= g.lo && v <= g.hi && !seen[v]) { seen[v] = 1; cand.push(v); }
      }
    });
    // 去重、截断或补足
    cand = cand.slice(0, g.cnt);
    var pool = [];
    for (var i = g.lo; i <= g.hi; i++) if (!seen[i]) pool.push(i);
    while (cand.length < g.cnt && pool.length) {
      var j = rng(pool.length);
      cand.push(pool[j]); pool.splice(j, 1);
    }
    return cand.sort(function (a, b) { return a - b; });
  }

  // ---------- 智能策略选号（启发式，娱乐向） ----------
  // 把 [lo,hi] 均分为 cnt 段，每段取 1 个，保证号码分散不扎堆
  function pickBalancedGroup(g) {
    var size = g.hi - g.lo + 1;
    var cnt = g.cnt;
    var segSize = Math.ceil(size / cnt);
    var chosen = [];
    for (var i = 0; i < cnt; i++) {
      var a = g.lo + i * segSize;
      var b = Math.min(g.hi, g.lo + (i + 1) * segSize - 1);
      if (a > g.hi) a = g.hi;
      if (b < a) b = a;
      var pool = [];
      for (var n = a; n <= b; n++) if (chosen.indexOf(n) < 0) pool.push(n);
      if (!pool.length) {
        for (var m = g.lo; m <= g.hi; m++) if (chosen.indexOf(m) < 0) pool.push(m);
      }
      chosen.push(pool[rng(pool.length)]);
    }
    return chosen.sort(function (x, y) { return x - y; });
  }

  // 反人流大数：仅对含 >31 的号池生效（双色球/大乐透前区），加权偏重大数
  function pickAntiCrowdGroup(g) {
    if (g.hi <= 31) return sampleNoReplace(g.hi - g.lo + 1, g.cnt, g.lo);
    var w = function (i) { var n = g.lo + i; return n > 31 ? 6 : 1; };
    return weightedSampleNoReplace(g.hi - g.lo + 1, g.cnt, g.lo, w);
  }

  // 避近期：排除最近 N 期该组已开出的号码，从剩余池抽（不够则减半 N 再试）
  function pickAvoidRecentGroup(g, data, opts) {
    var N = (opts && opts.nRecent) || 10;
    var draws = data.draws || [];
    var forbidden, allowed, end;
    while (N > 0) {
      forbidden = {};
      end = Math.min(N, draws.length);
      for (var k = draws.length - 1; k >= draws.length - end; k--) {
        var arr = (g.key === 'b') ? draws[k].b : draws[k].r;
        arr.forEach(function (n) { forbidden[n] = 1; });
      }
      allowed = [];
      for (var n2 = g.lo; n2 <= g.hi; n2++) if (!forbidden[n2]) allowed.push(n2);
      if (allowed.length >= g.cnt) break;
      N = Math.floor(N / 2);
    }
    var pick = [];
    for (var c = 0; c < g.cnt && allowed.length; c++) {
      var j = rng(allowed.length);
      pick.push(allowed[j]); allowed.splice(j, 1);
    }
    return pick.sort(function (x, y) { return x - y; });
  }

  // 综合智能参谋：以均衡为基，偶尔把一颗换成大数（反人流），并产出参谋说明
  function pickSmartGroup(g, data, opts) {
    var nums = pickBalancedGroup(g);
    if (g.hi > 31 && rng(2) === 0) {
      var largeAvail = [];
      for (var n = 32; n <= g.hi; n++) if (nums.indexOf(n) < 0) largeAvail.push(n);
      if (largeAvail.length) {
        nums[rng(nums.length)] = largeAvail[rng(largeAvail.length)];
        nums.sort(function (x, y) { return x - y; });
      }
    }
    return nums;
  }

  // 智能策略主入口：返回 {r,b,rationale}
  function pickSmart(data, mode, opts) {
    var groups = groupsOf(data);
    var res = { r: [], b: [], rationale: '' };
    groups.forEach(function (g) {
      var nums;
      if (g.sample) {
        if (mode === 'bal') nums = pickBalancedGroup(g);
        else if (mode === 'anti') nums = pickAntiCrowdGroup(g);
        else if (mode === 'avoid') nums = pickAvoidRecentGroup(g, data, opts);
        else nums = pickSmartGroup(g, data, opts); // ai
        if (g.key === 'b') res.b = nums; else res.r = nums.concat(res.r);
      } else {
        // 位置型（3D/排列3）：智能策略退化为每位随机，仍配性格签
        var pos = [];
        for (var p = 0; p < g.cnt; p++) pos.push(g.lo + rng(g.hi - g.lo + 1));
        res.r = pos;
      }
    });
    if (mode === 'ai') res.rationale = buildRationale(data, res);
    return res;
  }

  // 智能参谋说明：随机挑 2-3 个点评维度 + 随机结尾金句（每次表述不同），保留固定免责
  function buildRationale(data, res) {
    var groups = groupsOf(data);
    var rg = null;
    groups.forEach(function (g) { if (g.key !== 'b' && g.sample) rg = g; });
    var r = res.r;
    if (!r.length) return '';
    var odd = 0, even = 0, big = 0, small = 0;
    var mid = rg ? Math.floor((rg.lo + rg.hi) / 2) : 17;
    r.forEach(function (n) {
      if (n % 2 === 0) even++; else odd++;
      if (n > mid) big++; else small++;
    });
    var sum = r.reduce(function (a, b) { return a + b; }, 0);
    var large = r.some(function (n) { return n > 31; });
    var prime = r.filter(function (n) {
      if (n < 2) return false;
      for (var d = 2; d * d <= n; d++) if (n % d === 0) return false;
      return true;
    }).length;
    var span = Math.max.apply(null, r) - Math.min.apply(null, r);
    var tails = {}; r.forEach(function (n) { tails[n % 10] = 1; });
    var tailKinds = Object.keys(tails).length;

    var dims = [
      '奇偶 ' + odd + ':' + even,
      '大小 ' + big + ':' + small,
      '和值 ' + sum,
      '质合 ' + prime + ':' + (r.length - prime),
      '跨度 ' + span,
      '尾数 ' + tailKinds + '种'
    ];
    for (var i = dims.length - 1; i > 0; i--) { var j = rng(i + 1); var tmp = dims[i]; dims[i] = dims[j]; dims[j] = tmp; }
    var k = 2 + rng(2); // 随机 2 或 3 个维度
    var parts = dims.slice(0, k);
    if (large) parts.push('含大数避人流');
    var flavor = ['数字无心，取舍在你', '冷热皆概率，理性为上', '仅供参考，莫要上头', '一盘棋局，落子无悔', '天机不可尽泄，留三分余地'];
    var fl = flavor[rng(flavor.length)];
    return '参谋：' + parts.join(' · ') + '。' + fl + '（纯启发式，不提高中奖率）';
  }

  // ---------- 灵魂解读（混搭随缘：按号码特征自动选调性，每类调性下多条文案随机抽 + 去重） ----------
  function interpret(data, t) {
    var groups = groupsOf(data);
    var rg = null;
    groups.forEach(function (g) { if (g.key !== 'b') rg = g; });
    var nums = t.r.concat(t.b);
    var even = 0, odd = 0, big = 0, small = 0;
    var mid = rg ? Math.floor((rg.lo + rg.hi) / 2) : 17;
    nums.forEach(function (n) {
      if (n % 2 === 0) even++; else odd++;
      if (n > mid) big++; else small++;
    });
    var sum = nums.reduce(function (a, b) { return a + b; }, 0);
    var expected = nums.length * (rg ? (rg.lo + rg.hi) / 2 : 17);
    var rs = t.r.slice().sort(function (a, b) { return a - b; });
    var consec = false;
    for (var i = 1; i < rs.length; i++) if (rs[i] - rs[i - 1] === 1) { consec = true; break; }
    var pair = false;
    for (var x = 1; x < t.r.length; x++) if (t.r.indexOf(t.r[x]) !== x) { pair = true; break; }
    var large = nums.some(function (n) { return n > 31; });

    var name;
    if (odd === nums.length && nums.length > 1) name = '孤勇型';
    else if (even === nums.length && nums.length > 1) name = '稳重型';
    else if (consec) name = '血脉相连型';
    else if (pair) name = '情深型';
    else if (large && big >= small) name = '凌云型';
    else if (even === odd || Math.abs(big - small) <= 1) name = '中庸型';
    else if (sum > expected * 1.25) name = '炽盛型';
    else if (sum < expected * 0.75) name = '潜龙型';
    else name = '随缘型';

    var lines = SOUL_LINES[name] || SOUL_LINES['随缘型'];
    var rec = recentSoul[name] || (recentSoul[name] = []);
    return { name: name, text: pickDistinct(lines, rec, lines.length) };
  }

  // ---------- 统计 ----------
  function computeStats(data) {
    if (statCache[data.type]) return statCache[data.type];
    var groups = groupsOf(data);
    var draws = data.draws || [];
    var freq = {}, miss = {}, maxFreq = {};
    groups.forEach(function (g) {
      var size = g.hi - g.lo + 1;
      var f = {}, m = {};
      for (var n = g.lo; n <= g.hi; n++) { f[n] = 0; m[n] = 0; }
      var maxF = 0;
      // 频率（按 group 的每注号码）
      draws.forEach(function (dr) {
        var arr = (g.key === 'b') ? dr.b : dr.r;
        if (g.sample) {
          arr.forEach(function (n) { if (f[n] != null) f[n]++; });
        } else {
          // 位置型：每位分别统计；用 positions 下标
          var pos = g.positions || [];
          arr.forEach(function (n, pi) {
            var key = (pos[pi] || ('p' + pi));
            f[key] = f[key] || {};
            f[key][n] = (f[key][n] || 0) + 1;
          });
        }
      });
      if (g.sample) {
        for (var n = g.lo; n <= g.hi; n++) if (f[n] > maxF) maxF = f[n];
        // 当前遗漏：从最新一期往前数，直到该号出现
        for (var n2 = g.lo; n2 <= g.hi; n2++) {
          var c = 0;
          for (var k = draws.length - 1; k >= 0; k--) {
            var arr2 = (g.key === 'b') ? draws[k].b : draws[k].r;
            if (arr2.indexOf(n2) >= 0) break;
            c++;
          }
          m[n2] = c;
        }
      }
      freq[g.key] = f; miss[g.key] = m; maxFreq[g.key] = maxF;
    });
    var s = { freq: freq, miss: miss, maxFreq: maxFreq, draws: draws.length };
    statCache[data.type] = s;
    return s;
  }

  // ---------- 渲染 ----------
  function ball(n, kind) {
    var b = document.createElement('span');
    b.className = 'lx-ball' + (kind === 'b' ? ' lx-ball--b' : '');
    b.textContent = (kind === 'b' || n >= 10) ? pad2(n) : String(n);
    return b;
  }
  function renderTicket(cfg, t) {
    var box = document.createElement('div');
    box.className = 'lx-ticket';
    var groups = groupsOf(cfg);
    groups.forEach(function (g) {
      var wrap = document.createElement('div');
      wrap.className = 'lx-tk-group';
      var label = document.createElement('span');
      label.className = 'lx-tk-label';
      label.textContent = g.label + (g.positions ? '（' + g.positions.join('/') + '）' : '');
      wrap.appendChild(label);
      var nums = (g.key === 'b') ? t.b : t.r;
      if (g.sample || !g.positions) {
        nums.forEach(function (n) { wrap.appendChild(ball(n, g.key === 'b' ? 'b' : 'r')); });
      } else {
        // 位置型：每位一个小球，标百位/十位/个位
        nums.forEach(function (n, pi) {
          var bb = ball(n, 'r');
          var tag = document.createElement('sup');
          tag.className = 'lx-pos';
          tag.textContent = (g.positions[pi] || '');
          bb.appendChild(tag);
          wrap.appendChild(bb);
        });
      }
      box.appendChild(wrap);
    });
    if (t.soul) {
      var s = document.createElement('div');
      s.className = 'lx-soul';
      s.innerHTML = '<span class="lx-soul-name">' + t.soul.name + '</span><span class="lx-soul-text">' + t.soul.text + '</span>';
      box.appendChild(s);
    }
    if (t.rationale) {
      var ra = document.createElement('div');
      ra.className = 'lx-rationale';
      ra.textContent = t.rationale;
      box.appendChild(ra);
    }
    return box;
  }

  function renderTickets(cfg, tickets, animate) {
    var P = panelOf('lottery');
    var host = $('[data-tickets]', P);
    if (!host) return;
    host.innerHTML = '';
    tickets.forEach(function (t) { host.appendChild(renderTicket(cfg, t)); });
    if (animate === 'dice') playDice(host);
    else if (animate === 'slip') playSlip(host);
    else if (animate === 'drum') playDrum(host);
    else if (animate === 'shake') playShake(host);
  }

  // 骰子翻滚动画：数字球 3D 翻滚 + 数字快速闪变，保留 百/十/个 角标
  function playDice(host) {
    var balls = $$('.lx-ball', host);
    balls.forEach(function (b, i) {
      var hasSup = !!b.querySelector('sup');
      var finalText = hasSup
        ? (b.firstChild && b.firstChild.nodeType === 3 ? b.firstChild.textContent : b.textContent)
        : b.textContent;
      b.classList.add('lx-3d', 'lx-rolling');
      var steps = 0, max = 10 + i;
      var iv = setInterval(function () {
        if (!hasSup) b.textContent = String(rng(10));
        steps++;
        if (steps >= max) {
          clearInterval(iv);
          b.classList.remove('lx-rolling');
          if (hasSup) {
            if (b.firstChild && b.firstChild.nodeType === 3) b.firstChild.nodeValue = finalText;
            else b.insertBefore(document.createTextNode(finalText), b.firstChild);
          } else {
            b.textContent = finalText;
          }
          b.classList.remove('lx-3d');
          b.classList.add('lx-pop');
          setTimeout(function () { b.classList.remove('lx-pop'); }, 400);
        }
      }, 60);
    });
  }
  // 摇奖机：先画一台摇奖机转球，再让号码球逐颗从上方掉落
  function playDrum(host) {
    var stage = document.createElement('div');
    stage.className = 'lx-machine';
    stage.innerHTML = '<svg viewBox="0 0 128 112" fill="none" stroke="#C9A84C" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<circle cx="64" cy="44" r="36" opacity=".55"/>' +
      '<g class="lxb">' +
      '<circle cx="50" cy="38" r="5.5" fill="#c65b54" stroke="none"/>' +
      '<circle cx="78" cy="34" r="5.5" fill="#5fb0e8" stroke="none"/>' +
      '<circle cx="64" cy="54" r="5.5" fill="#c65b54" stroke="none"/>' +
      '<circle cx="52" cy="58" r="5.5" fill="#5fb0e8" stroke="none"/>' +
      '<circle cx="80" cy="56" r="5.5" fill="#c65b54" stroke="none"/>' +
      '</g>' +
      '<path d="M34 80h60l-9 28H43z" fill="rgba(201,168,76,.12)"/>' +
      '<path d="M58 108v4M70 108v4"/>' +
      '</svg>';
    host.insertBefore(stage, host.firstChild);
    var balls = $$('.lx-ball', host);
    balls.forEach(function (b) { b.classList.add('lx-hidden'); });
    setTimeout(function () {
      if (stage.parentNode) stage.parentNode.removeChild(stage);
      balls.forEach(function (b, i) {
        setTimeout(function () {
          b.classList.remove('lx-hidden');
          b.classList.add('lx-drop');
          setTimeout(function () { b.classList.remove('lx-drop'); }, 520);
        }, i * 70);
      });
    }, 1000);
  }
  // 抽签锦囊：先展开一支卷轴（签文由 generate 写入 [data-drum] 并自带滑入动画）
  function playSlip(host) {
    var stage = document.createElement('div');
    stage.className = 'lx-scroll';
    stage.innerHTML = '<svg viewBox="0 0 76 64" fill="none" stroke="#C9A84C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<rect x="24" y="8" width="28" height="48" rx="3" fill="rgba(201,168,76,.1)"/>' +
      '<path d="M24 16h28M24 48h28"/>' +
      '<path d="M52 32l18-7v22l-18-7z" fill="rgba(201,168,76,.18)"/>' +
      '<circle cx="38" cy="32" r="3" fill="#C9A84C" stroke="none"/>' +
      '</svg>';
    host.insertBefore(stage, host.firstChild);
    setTimeout(function () { if (stage.parentNode) stage.parentNode.removeChild(stage); }, 850);
  }
  // 摇一摇：手机晃动 + 号码球乱跳归位
  function playShake(host) {
    var stage = document.createElement('div');
    stage.className = 'lx-phone';
    stage.innerHTML = '<svg viewBox="0 0 52 52" fill="none" stroke="#C9A84C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<rect x="16" y="5" width="20" height="42" rx="4" fill="rgba(201,168,76,.12)"/>' +
      '<path d="M23 43h6"/>' +
      '</svg>';
    host.insertBefore(stage, host.firstChild);
    var balls = $$('.lx-ball', host);
    balls.forEach(function (b) { b.classList.add('lx-hidden'); });
    setTimeout(function () {
      if (stage.parentNode) stage.parentNode.removeChild(stage);
      balls.forEach(function (b, i) {
        setTimeout(function () {
          b.classList.remove('lx-hidden');
          b.classList.add('lx-drop');
          setTimeout(function () { b.classList.remove('lx-drop'); }, 520);
        }, i * 45);
      });
    }, 620);
  }

  // ---------- 统计渲染 ----------
  function renderStats(data) {
    var P = panelOf('lottery');
    var host = $('[data-stats]', P);
    if (!host) return;
    var s = computeStats(data);
    host.innerHTML = '';
    var groups = groupsOf(data);
    var load = $('[data-statload]', P); if (load) load.hidden = true;

    groups.forEach(function (g) {
      var block = document.createElement('div');
      block.className = 'lx-stat-block';
      var h = document.createElement('h4');
      h.className = 'lx-stat-h';
      h.textContent = g.label + ' 出现统计（共 ' + s.draws + ' 期）';
      block.appendChild(h);
      if (g.sample) {
        var tbl = document.createElement('div');
        tbl.className = 'lx-stat-grid';
        var maxF = s.maxFreq[g.key] || 1;
        for (var n = g.lo; n <= g.hi; n++) {
          var f = s.freq[g.key][n] || 0;
          var mi = s.miss[g.key][n] || 0;
          var cell = document.createElement('div');
          cell.className = 'lx-stat-cell';
          var hot = f >= maxF * 0.66 ? ' lx-hot' : (f <= maxF * 0.33 ? ' lx-cold' : '');
          cell.innerHTML = '<span class="lx-num' + hot + '">' + (n < 10 && g.hi >= 10 ? pad2(n) : n) + '</span>' +
            '<span class="lx-bar"><i style="width:' + Math.round(f / maxF * 100) + '%"></i></span>' +
            '<span class="lx-cnt">出 ' + f + ' 次</span>' +
            '<span class="lx-miss">遗漏 ' + mi + ' 期</span>';
          tbl.appendChild(cell);
        }
        block.appendChild(tbl);
      } else {
        var pos = g.positions || [];
        pos.forEach(function (pk, pi) {
          var sub = document.createElement('div');
          sub.className = 'lx-stat-sub';
          var sh = document.createElement('h5'); sh.textContent = pk + '位'; sub.appendChild(sh);
          var tbl2 = document.createElement('div'); tbl2.className = 'lx-stat-grid lx-stat-grid--pos';
          var fmap = s.freq[g.key][pk] || {};
          var maxP = 1; for (var d = g.lo; d <= g.hi; d++) if ((fmap[d] || 0) > maxP) maxP = fmap[d];
          for (var d2 = g.lo; d2 <= g.hi; d2++) {
            var f2 = fmap[d2] || 0;
            var cell2 = document.createElement('div'); cell2.className = 'lx-stat-cell';
            cell2.innerHTML = '<span class="lx-num">' + d2 + '</span>' +
              '<span class="lx-bar"><i style="width:' + Math.round(f2 / maxP * 100) + '%"></i></span>' +
              '<span class="lx-cnt">出 ' + f2 + ' 次</span>';
            tbl2.appendChild(cell2);
          }
          sub.appendChild(tbl2); block.appendChild(sub);
        });
      }
      host.appendChild(block);
    });
    var note = document.createElement('p');
    note.className = 'lx-statnote';
    note.innerHTML = '热号＝出现次数明显高于平均（金）；冷号＝明显偏少（蓝）；遗漏＝距上次开出已隔多少期。<b>纯历史规律，不构成任何预测建议。</b>';
    host.appendChild(note);
  }

  // ---------- 往期查询 ----------
  var histState = { page: 1, per: 50 };
  function renderHistory(data) {
    var P = panelOf('lottery');
    var host = $('[data-hist]', P); if (!host) return;
    var from = (fieldVal(P, 'from') || '').trim();
    var to = (fieldVal(P, 'to') || '').trim();
    var draws = (data.draws || []).filter(function (d) {
      if (from && d.d < from) return false;
      if (to && d.d > to) return false;
      return true;
    });
    var total = draws.length;
    var pages = Math.max(1, Math.ceil(total / histState.per));
    if (histState.page > pages) histState.page = pages;
    var start = (histState.page - 1) * histState.per;
    var slice = draws.slice(start, start + histState.per);

    host.innerHTML = '';
    var sum = document.createElement('div');
    sum.className = 'lx-hist-sum';
    sum.textContent = '共 ' + total + ' 期' + (from || to ? '（已按日期筛选）' : '') + '，每页 ' + histState.per + ' 期';
    host.appendChild(sum);

    var tbl = document.createElement('div');
    tbl.className = 'lx-hist-table';
    slice.forEach(function (d) {
      var row = document.createElement('div'); row.className = 'lx-hist-row';
      var iss = document.createElement('span'); iss.className = 'lx-hist-iss'; iss.textContent = d.i;
      var dt = document.createElement('span'); dt.className = 'lx-hist-date'; dt.textContent = d.d;
      var nums = document.createElement('span'); nums.className = 'lx-hist-nums';
      d.r.forEach(function (n) { nums.appendChild(ball(n, 'r')); });
      d.b.forEach(function (n) { nums.appendChild(ball(n, 'b')); });
      row.appendChild(iss); row.appendChild(dt); row.appendChild(nums);
      tbl.appendChild(row);
    });
    host.appendChild(tbl);

    var pager = document.createElement('div');
    pager.className = 'lx-pager';
    var prev = document.createElement('button'); prev.className = 'tl-btn ghost'; prev.textContent = '上一页'; prev.disabled = histState.page <= 1;
    var info = document.createElement('span'); info.className = 'lx-pager-info'; info.textContent = histState.page + ' / ' + pages;
    var next = document.createElement('button'); next.className = 'tl-btn ghost'; next.textContent = '下一页'; next.disabled = histState.page >= pages;
    prev.addEventListener('click', function () { histState.page--; renderHistory(data); });
    next.addEventListener('click', function () { histState.page++; renderHistory(data); });
    pager.appendChild(prev); pager.appendChild(info); pager.appendChild(next);
    host.appendChild(pager);
  }

  // ---------- 数据加载 ----------
  function loadData(id, cb) {
    if (cache[id]) { cb(cache[id]); return; }
    fetch('data/lottery/' + id + '.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (j) { cache[id] = j; cb(j); })
      .catch(function (e) { toast(panelOf('lottery'), '历史数据加载失败：' + e.message + '。请检查网络或刷新重试。', 'err'); });
  }

  // ---------- 工具主体 ----------
  function fieldVal(P, name) { var el = field(P, name); return el ? el.value : ''; }
  function field(P, name) { return $('[data-in="' + name + '"]', P); }

  function generate() {
    var P = panelOf('lottery');
    if (!P) return;
    clearToast(P);
    var cnt = Math.max(1, Math.min(10, Math.floor(Number(fieldVal(P, 'cnt')) || 5)));
    var mode = state.mode;
    var data = cache[state.type];
    if (!data) { toast(P, '数据还没准备好，稍等。', 'err'); return; }
    if (mode === 'hot' && !statCache[data.type]) computeStats(data);

    var tickets = [];
    for (var k = 0; k < cnt; k++) {
      var t = SMART[mode]
        ? pickSmart(data, mode, { nRecent: 10 })
        : pickOne(data, mode, { bias: state.bias, date: fieldVal(P, 'date') });
      t.soul = interpret(data, t);
      tickets.push(t);
    }

    var anim = (mode === 'dice') ? 'dice' : (mode === 'slip' ? 'slip' : (mode === 'drum' ? 'drum' : (mode === 'shake' ? 'shake' : null)));
    renderTickets(data, tickets, anim);
    compareHistory(data, tickets);

    if (mode === 'slip') {
      var dr = $('[data-drum]', P);
      if (dr) {
        dr.hidden = false;
        var f = pickDistinct(FORTUNES, recentFortune, FORTUNES.length);
        dr.innerHTML = '<div class="lx-slip lx-slipin"><span class="lx-slip-stick">签</span><span class="lx-slip-text">' + f + '</span></div>';
      }
    } else {
      var dr2 = $('[data-drum]', P); if (dr2) dr2.hidden = true;
    }
  }

  // 命中历史相似号：找出与你这组红球（前区）相同数最多的往期；命中 ≥ 六成红球则提示「历史神巧合」
  function compareHistory(data, tickets) {
    var P = panelOf('lottery');
    var host = $('[data-tickets]', P);
    if (!host || !tickets.length) return;
    var old = host.querySelector('.lx-coincide'); if (old) old.remove();
    var draws = data.draws || [];
    if (!draws.length) return;
    var best = null;
    tickets.forEach(function (t) {
      var tr = t.r || [];
      for (var k = 0; k < draws.length; k++) {
        var d = draws[k], dr = d.r || [], db = d.b || [];
        var same = 0; for (var i = 0; i < tr.length; i++) if (dr.indexOf(tr[i]) >= 0) same++;
        var sb = 0; var tb = t.b || []; for (var j = 0; j < tb.length; j++) if (db.indexOf(tb[j]) >= 0) sb++;
        var score = same * 10 + sb;
        if (!best || score > best.score) best = { score: score, iss: d.i, date: d.d, same: same, sb: sb };
      }
    });
    var need = Math.ceil((tickets[0] ? tickets[0].r.length : 0) * 0.6);
    if (best && best.same >= need) {
      var note = document.createElement('div');
      note.className = 'lx-coincide';
      note.innerHTML = '✦ 历史神巧合 · 第 <b>' + best.iss + '</b> 期（' + best.date + '）与你这组有 <b>' + best.same + '</b> 个红球相同' +
        (best.sb ? ('、<b>' + best.sb + '</b> 个蓝球相同') : '') + '。纯属概率，仅供一乐。';
      host.appendChild(note);
    }
  }

  // 最新开奖卡片：展示内置历史数据的最新一期；数据由 GitHub Actions 每日定时任务自动更新
  function renderLatest(data) {
    var P = panelOf('lottery');
    var host = $('[data-latest]', P);
    if (!host || !data) return;
    var draws = data.draws || [];
    if (!draws.length) { host.innerHTML = ''; return; }
    var last = draws[draws.length - 1];
    host.innerHTML = '';
    var card = document.createElement('div');
    card.className = 'lx-latest';
    var head = document.createElement('div');
    head.className = 'lx-latest-h';
    head.innerHTML = '<span class="lx-latest-name">' + data.name + '</span>最新开奖 · 第 <b>' + last.i + '</b> 期（' + last.d + '）';
    card.appendChild(head);
    var nums = document.createElement('div');
    nums.className = 'lx-latest-nums';
    last.r.forEach(function (n) { nums.appendChild(ball(n, 'r')); });
    (last.b || []).forEach(function (n) { nums.appendChild(ball(n, 'b')); });
    card.appendChild(nums);
    var note = document.createElement('div');
    note.className = 'lx-latest-note';
    note.textContent = '数据由每日定时任务自动更新 · 最近更新 ' + (data.updated || last.d);
    card.appendChild(note);
    host.appendChild(card);
  }


  function setupLottery() {
    var P = panelOf('lottery');
    if (!P) return;

    // 彩种 /  tab / 玩法 / 策略 分段控件
    function wireSeg(segName, onChange) {
      var seg = $('[data-seg="' + segName + '"]', P);
      if (!seg) return;
      $$('.lx-seg-btn', seg).forEach(function (btn) {
        btn.addEventListener('click', function () {
          $$('.lx-seg-btn', seg).forEach(function (b) { b.classList.remove('is-on'); });
          btn.classList.add('is-on');
          onChange(btn.getAttribute('data-val'));
        });
      });
    }

    wireSeg('type', function (v) {
      state.type = v;
      // 切彩种：统计/往期缓存按 type 隔离；若已开统计或往期，自动重算。
      // 选号 tab 也必须先确保该彩种数据已加载（首次切换时还没缓存），再生成，
      // 否则会命中「数据还没准备好」并残留上一彩种的号码。
      if (state.tab === 'stat') loadData(v, function (d) { renderLatest(d); renderStats(d); });
      else if (state.tab === 'history') loadData(v, function (d) { renderLatest(d); renderHistory(d); });
      else loadData(v, function (d) { renderLatest(d); if (state.tab === 'pick') generate(); });
    });
    wireSeg('tab', function (v) {
      state.tab = v;
      $$('[data-tabpane]', P).forEach(function (p) { p.hidden = (p.getAttribute('data-tabpane') !== v); });
      if (v === 'stat') loadData(state.type, renderStats);
      if (v === 'history') loadData(state.type, renderHistory);
    });
    wireSeg('mode', function (v) {
      state.mode = v;
      // 玩法相关控件显隐
      $$('[data-modectl]', P).forEach(function (el) { el.hidden = (el.getAttribute('data-modectl') !== v); });
      if (v === 'hot') {
        loadData(state.type, function () { computeStats(cache[state.type]); if (state.tab === 'pick') generate(); });
      } else if (state.tab === 'pick' && cache[state.type]) {
        generate();
      }
    });
    wireSeg('bias', function (v) { state.bias = v; });

    // 按钮
    $$('[data-act]', P).forEach(function (b) {
      var act = b.getAttribute('data-act');
      if (act === 'gen') b.addEventListener('click', generate);
      if (act === 'again') b.addEventListener('click', generate);
      if (act === 'qry') b.addEventListener('click', function () { loadData(state.type, renderHistory); });
    });

    // 注数变化实时重生成（仅在选号 tab）
    var cntEl = field(P, 'cnt'); if (cntEl) cntEl.addEventListener('input', function () { if (state.tab === 'pick') generate(); });
    var dateEl = field(P, 'date'); if (dateEl) dateEl.addEventListener('change', function () { if (state.tab === 'pick' && state.mode === 'date') generate(); });

    // 默认先备好当前彩种数据（不阻塞），首屏出一组示例
    loadData(state.type, function (data) {
      renderLatest(data);
      if (state.tab === 'pick') generate();
    });
  }

  window.LXTools.define('lottery', setupLottery);
})();
