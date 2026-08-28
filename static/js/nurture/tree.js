// 灵圃·沉香树 —— 真实感渲染模块
// 思路：SVG defs 复用（叶/木/地面/雪），按 5 阶段各画一套真实形态：
//   seed    种子刚出土
//   sprout  幼苗（重点）：对生披针叶·渐变木皮·节点·叶脉·土壤影·小石
//   sapling 树苗：主茎 + 多分枝 + 簇叶
//   tree    成树：粗干·多层树冠·树脂斑·奇花
//   ancient 古木：巨干·苔痕·寄生藤·裂缝·丛冠
// 额外：dead 枯木（含残叶与干土裂纹）、winter 飘雪、petalSkin 奇花点缀
(function () {
  var W = 280, H = 320, GY = 270;

  // 四季色板（活树阶段用，更细腻）
  var SEASONS = {
    spring: { leaf: '#7bc26b', leafHi: '#c8efb1', leafSh: '#3a6e2c', bark: '#5e7e4a', barkSh: '#3a4e2c', petal: '#f4c1d4', ground: '#5a4a3a', stone: '#8b7c6a' },
    summer: { leaf: '#4f9b3d', leafHi: '#9bd672', leafSh: '#1f4d18', bark: '#6e8d52', barkSh: '#3a5230', petal: '#f6e3a3', ground: '#53402f', stone: '#7a6857' },
    autumn: { leaf: '#c98f3a', leafHi: '#ecc46a', leafSh: '#7b4a1c', bark: '#7a5230', barkSh: '#3a2818', petal: '#e7602f', ground: '#5a4030', stone: '#7a6552' },
    winter: { leaf: '#86a378', leafHi: '#b8cda3', leafSh: '#46593c', bark: '#5a5a4a', barkSh: '#2a2a22', petal: '#ffffff', ground: '#3a322a', stone: '#5d5048' }
  };

  // ---- defs：渐变 + 叶 symbol ----
  function defs(c) {
    return '<defs>' +
      // 叶面渐变（上亮下暗）
      '<linearGradient id="leafG" x1="0" x2="0" y1="0" y2="1">' +
        '<stop offset="0%" stop-color="' + c.leafHi + '"/>' +
        '<stop offset="55%" stop-color="' + c.leaf + '"/>' +
        '<stop offset="100%" stop-color="' + c.leafSh + '"/>' +
      '</linearGradient>' +
      // 木皮渐变（中间亮两侧暗，模拟圆柱）
      '<linearGradient id="barkG" x1="0" x2="1" y1="0" y2="0">' +
        '<stop offset="0%" stop-color="' + c.barkSh + '"/>' +
        '<stop offset="50%" stop-color="' + c.bark + '"/>' +
        '<stop offset="100%" stop-color="' + c.barkSh + '"/>' +
      '</linearGradient>' +
      // 树影渐变
      '<radialGradient id="shadowG" cx="0.5" cy="0.5">' +
        '<stop offset="0%" stop-color="rgba(0,0,0,.42)"/>' +
        '<stop offset="80%" stop-color="rgba(0,0,0,0)"/>' +
      '</radialGradient>' +
      // 单片披针叶 symbol：左尖右根，中肋+侧脉
      '<symbol id="leaf" viewBox="0 0 40 16" overflow="visible">' +
        '<path d="M2 8 Q10 1 38 8 Q10 15 2 8 Z" fill="url(#leafG)"/>' +
        // 中肋
        '<path d="M2 8 L38 8" stroke="' + c.leafSh + '" stroke-width="0.6" opacity="0.55"/>' +
        // 侧脉
        '<path d="M8 8 q3 -2 6 0 M16 8 q3 -2 6 0 M24 8 q3 -2 6 0 M8 8 q3 2 6 0 M16 8 q3 2 6 0 M24 8 q3 2 6 0" stroke="' + c.leafSh + '" stroke-width="0.35" fill="none" opacity="0.4"/>' +
      '</symbol>' +
    '</defs>';
  }

  // ---- 地面 ----
  function ground(c, dead) {
    var g = '<ellipse cx="' + (W/2) + '" cy="' + (GY+5) + '" rx="120" ry="14" fill="url(#shadowG)"/>';
    if (!dead) {
      g += '<ellipse cx="' + (W/2) + '" cy="' + GY + '" rx="50" ry="6" fill="' + c.ground + '" opacity="0.78"/>';
      g += '<ellipse cx="92" cy="' + (GY+3) + '" rx="6" ry="2.5" fill="' + c.stone + '" opacity="0.9"/>';
      g += '<ellipse cx="178" cy="' + (GY+4) + '" rx="4" ry="2" fill="' + c.stone + '" opacity="0.85"/>';
      g += '<ellipse cx="155" cy="' + (GY+8) + '" rx="5" ry="2" fill="' + c.stone + '" opacity="0.7"/>';
      // 一片落叶
      g += '<path d="M180 ' + (GY-2) + ' q6 -3 12 1 q-6 3 -12 -1 Z" fill="' + c.leaf + '" opacity="0.7"/>';
      // 草芽
      g += '<path d="M75 ' + GY + ' q1 -8 -2 -14 M80 ' + GY + ' q0 -7 2 -12" stroke="' + c.leaf + '" stroke-width="1.2" fill="none" stroke-linecap="round" opacity="0.85"/>';
    } else {
      g += '<ellipse cx="' + (W/2) + '" cy="' + GY + '" rx="52" ry="5" fill="#3a2a1d" opacity="0.9"/>';
      // 干裂纹
      g += '<path d="M108 ' + GY + ' L165 ' + GY + '" stroke="#221811" stroke-width="0.9" opacity="0.7"/>';
      g += '<path d="M115 ' + (GY+3) + ' L150 ' + (GY+3) + '" stroke="#221811" stroke-width="0.7" opacity="0.6"/>';
    }
    return g;
  }

  // ---- 单片叶子 use ----
  function leafUse(x, y, rot, scale) {
    var w = 40 * scale, h = 16 * scale;
    // x,y 是叶子中心
    return '<use href="#leaf" x="' + (x - w/2) + '" y="' + (y - h/2) + '" width="' + w + '" height="' + h + '" transform="rotate(' + rot + ' ' + x + ' ' + y + ')"/>';
  }

  // ========= 阶段：种子 =========
  function stage_seed(c) {
    var cx = W/2;
    return (
      ground(c, false) +
      // 土中种子
      '<ellipse cx="' + cx + '" cy="' + (GY-3) + '" rx="9" ry="5" fill="#5a3a1f"/>' +
      // 拱破土面的小芽
      '<path d="M' + cx + ' ' + (GY-5) + ' q-4 -14 4 -26" stroke="' + c.leaf + '" stroke-width="3" fill="none" stroke-linecap="round"/>' +
      '<circle cx="' + (cx+4) + '" cy="' + (GY-32) + '" r="5" fill="' + c.leafHi + '"/>'
    );
  }

  // ========= 阶段：幼苗（重点）=========
  function stage_sprout(c) {
    var cx = W/2, baseY = GY;
    var s = '';
    s += ground(c, false);
    // 主茎：圆头线 + 木皮渐变（中间亮两侧暗）
    s += '<path d="M' + cx + ' ' + baseY + ' Q' + (cx-1.2) + ' ' + (baseY-42) + ' ' + cx + ' ' + (baseY-82) + '" stroke="url(#barkG)" stroke-width="3.4" stroke-linecap="round" fill="none"/>';
    // 节间纹痕
    s += '<path d="M' + (cx-1.2) + ' ' + (baseY-22) + ' q3 -1 6 0 M' + (cx-1.2) + ' ' + (baseY-50) + ' q3 -1 6 0" stroke="#3e2818" stroke-width="0.6" fill="none" opacity="0.6"/>';
    // 顶芽（嫩红尖）
    s += '<ellipse cx="' + cx + '" cy="' + (baseY-83) + '" rx="2" ry="3" fill="#d7a35f" opacity="0.95"/>';

    // 3 节对生叶（披针形，渐变 + 叶脉）
    var nodes = [
      { y: baseY - 26, big: 0.85 },   // 下节
      { y: baseY - 52, big: 1.0  },   // 中节（标准）
      { y: baseY - 74, big: 0.9  }    // 顶节
    ];
    nodes.forEach(function (n) {
      var sy = n.y;
      // 左叶：往上抬，落叶角度
      s += leafUse(cx - 1.5, sy,  -72, n.big);
      // 右叶
      s += leafUse(cx + 1.5, sy,   72, n.big);
    });
    return s;
  }

  // ========= 阶段：树苗 =========
  function stage_sapling(c) {
    var cx = W/2, baseY = GY;
    var s = '';
    s += ground(c, false);
    // 主干（双线叠加）=中间亮两侧暗
    s += '<path d="M' + (cx-4) + ' ' + baseY + ' Q' + (cx-2) + ' ' + (baseY-60) + ' ' + cx + ' ' + (baseY-115) + '" stroke="url(#barkG)" stroke-width="7" stroke-linecap="round" fill="none"/>';
    s += '<path d="M' + (cx+4) + ' ' + baseY + ' Q' + (cx+2) + ' ' + (baseY-60) + ' ' + cx + ' ' + (baseY-115) + '" stroke="url(#barkG)" stroke-width="7" stroke-linecap="round" fill="none" opacity="0.55"/>';

    // 5 条分枝（4 侧 + 1 顶）
    var branches = [
      { x: cx-2, y: baseY-70,  ang: -50, len: 34, n: 2 },
      { x: cx+2, y: baseY-70,  ang:  50, len: 34, n: 2 },
      { x: cx,   y: baseY-92,  ang: -78, len: 24, n: 2 },
      { x: cx,   y: baseY-92,  ang:  78, len: 24, n: 2 },
      { x: cx,   y: baseY-115, ang:   0, len: 16, n: 3 }
    ];
    branches.forEach(function (b) {
      var ex = b.x + Math.cos(b.ang * Math.PI/180) * b.len;
      var ey = b.y + Math.sin(b.ang * Math.PI/180) * b.len;
      // 折线分枝（带一点弧度）
      var mx = b.x + (ex - b.x) * 0.55;
      var my = b.y + (ey - b.y) * 0.55 + Math.sin(b.ang*Math.PI/180) * 3;
      s += '<path d="M' + b.x + ' ' + b.y + ' Q' + mx + ' ' + my + ' ' + ex + ' ' + ey + '" stroke="#7a5a3a" stroke-width="2.6" fill="none" stroke-linecap="round"/>';
      // 末梢叶
      for (var i = 0; i < b.n; i++) {
        var off = (i - (b.n - 1)/2) * 28;
        s += leafUse(ex, ey, off, 0.85);
      }
    });
    return s;
  }

  // ========= 阶段：成树 =========
  function stage_tree(c, S) {
    var cx = W/2, baseY = GY;
    var s = '';
    s += ground(c, false);
    // 粗主干
    s += '<path d="M' + (cx-8) + ' ' + baseY + ' Q' + (cx-5) + ' ' + (baseY-70) + ' ' + (cx-2) + ' ' + (baseY-135) + '" stroke="url(#barkG)" stroke-width="15" stroke-linecap="round" fill="none"/>';
    s += '<path d="M' + (cx+8) + ' ' + baseY + ' Q' + (cx+5) + ' ' + (baseY-70) + ' ' + (cx+2) + ' ' + (baseY-135) + '" stroke="url(#barkG)" stroke-width="15" stroke-linecap="round" fill="none" opacity="0.55"/>';
    // 木纹细纹
    for (var k = 0; k < 4; k++) {
      s += '<path d="M' + (cx-7) + ' ' + (baseY-30-k*22) + ' Q' + cx + ' ' + (baseY-25-k*22) + ' ' + (cx+7) + ' ' + (baseY-30-k*22) + '" stroke="#3a2818" stroke-width="0.7" fill="none" opacity="0.45"/>';
    }
    // 树脂斑（参考真实：创伤结疤纹理）
    if (S && S.resin > 0) {
      var n = Math.max(1, Math.min(5, Math.round(S.resin / 20)));
      var spots = [[cx-3, baseY-58], [cx+5, baseY-72], [cx-6, baseY-90], [cx+4, baseY-105], [cx, baseY-122]];
      for (var j = 0; j < n; j++) {
        var p = spots[j];
        s += '<ellipse cx="' + p[0] + '" cy="' + p[1] + '" rx="' + (5 + S.resin/25) + '" ry="' + (4 + S.resin/30) + '" fill="#3d1a0c" opacity="0.95"/>';
        s += '<ellipse cx="' + (p[0]-1.8) + '" cy="' + (p[1]-1.8) + '" rx="2" ry="1.5" fill="#c98a3a" opacity="0.85"/>';
      }
    }
    // 多层树冠
    var layers = [
      { x: cx,    y: baseY-155, r: 38, c: c.leafSh, o: 0.85 },
      { x: cx-32, y: baseY-145, r: 30, c: c.leafSh, o: 0.85 },
      { x: cx+34, y: baseY-150, r: 32, c: c.leafSh, o: 0.85 },
      { x: cx-12, y: baseY-175, r: 32, c: c.leaf, o: 0.9 },
      { x: cx+20, y: baseY-182, r: 30, c: c.leaf, o: 0.9 },
      { x: cx,    y: baseY-200, r: 24, c: c.leafHi, o: 0.9 }
    ];
    layers.forEach(function (l) {
      s += '<circle cx="' + l.x + '" cy="' + l.y + '" r="' + l.r + '" fill="' + l.c + '" opacity="' + l.o + '"/>';
    });
    // 树冠边缘高光叶
    s += leafUse(cx-32, baseY-160, -45, 0.8);
    s += leafUse(cx+34, baseY-165,  45, 0.8);
    s += leafUse(cx,     baseY-210,   0, 0.65);

    // 奇花
    if (S && S.petalSkin) {
      s += '<g transform="translate(' + (cx+30) + ',' + (baseY-195) + ')">' +
        '<circle r="3" fill="#f6c5e0"/><circle cx="6" r="3" fill="#f6c5e0"/><circle cx="3" cy="6" r="3" fill="#f6c5e0"/><circle cx="-3" cy="6" r="3" fill="#f6c5e0"/><circle cx="3" cy="3" r="2.2" fill="#ffd35a"/></g>';
    }
    return s;
  }

  // ========= 阶段：古木 =========
  function stage_ancient(c, S) {
    var cx = W/2, baseY = GY;
    var s = '';
    s += ground(c, false);
    // 巨粗主干
    s += '<path d="M' + (cx-15) + ' ' + baseY + ' Q' + (cx-9) + ' ' + (baseY-60) + ' ' + (cx-3) + ' ' + (baseY-135) + '" stroke="url(#barkG)" stroke-width="24" stroke-linecap="round" fill="none"/>';
    s += '<path d="M' + (cx+15) + ' ' + baseY + ' Q' + (cx+9) + ' ' + (baseY-60) + ' ' + (cx+3) + ' ' + (baseY-135) + '" stroke="url(#barkG)" stroke-width="24" stroke-linecap="round" fill="none" opacity="0.5"/>';
    // 树皮深裂纹
    for (var k = 0; k < 6; k++) {
      s += '<path d="M' + (cx-10) + ' ' + (baseY-20-k*20) + ' Q' + cx + ' ' + (baseY-15-k*20) + ' ' + (cx+10) + ' ' + (baseY-20-k*20) + '" stroke="#221511" stroke-width="0.9" fill="none" opacity="0.55"/>';
    }
    // 苔痕（朝阴面）
    s += '<path d="M' + (cx-11) + ' ' + (baseY-30) + ' q-2 12 4 28" stroke="#5a8050" stroke-width="6" fill="none" opacity="0.75" stroke-linecap="round"/>';
    s += '<path d="M' + (cx-11) + ' ' + (baseY-70) + ' q-3 14 3 24" stroke="#5a8050" stroke-width="5" fill="none" opacity="0.65" stroke-linecap="round"/>';
    // 树脂斑
    if (S && S.resin > 0) {
      var n = Math.max(1, Math.min(5, Math.round(S.resin / 18)));
      var spots = [[cx-5, baseY-58], [cx+6, baseY-75], [cx-9, baseY-95], [cx+5, baseY-112], [cx, baseY-128]];
      for (var j = 0; j < n; j++) {
        var p = spots[j];
        s += '<ellipse cx="' + p[0] + '" cy="' + p[1] + '" rx="' + (7 + S.resin/20) + '" ry="' + (5 + S.resin/25) + '" fill="#3a1808" opacity="0.95"/>';
        s += '<ellipse cx="' + (p[0]-2) + '" cy="' + (p[1]-2) + '" rx="2.5" ry="2" fill="#c98a3a"/>';
      }
    }
    // 巨冠
    var layers = [
      { x: cx,    y: baseY-165, r: 62, c: c.leafSh, o: 0.9 },
      { x: cx-55, y: baseY-150, r: 44, c: c.leafSh, o: 0.85 },
      { x: cx+55, y: baseY-155, r: 46, c: c.leafSh, o: 0.85 },
      { x: cx-28, y: baseY-190, r: 40, c: c.leaf, o: 0.9 },
      { x: cx+30, y: baseY-195, r: 42, c: c.leaf, o: 0.9 },
      { x: cx,    y: baseY-220, r: 32, c: c.leafHi, o: 0.9 }
    ];
    layers.forEach(function (l) {
      s += '<circle cx="' + l.x + '" cy="' + l.y + '" r="' + l.r + '" fill="' + l.c + '" opacity="' + l.o + '"/>';
    });
    // 寄生藤
    s += '<path d="M' + (cx+14) + ' ' + (baseY-155) + ' q5 14 -2 30 q-4 12 4 22" stroke="#3a5a30" stroke-width="2" fill="none" opacity="0.85" stroke-linecap="round"/>';
    // 顶叶
    s += leafUse(cx-55, baseY-160, -65, 0.85);
    s += leafUse(cx+57, baseY-165,  65, 0.85);
    s += leafUse(cx,     baseY-230,   0, 0.7);

    // 奇花
    if (S && S.petalSkin) {
      s += '<g transform="translate(' + (cx+32) + ',' + (baseY-205) + ')">' +
        '<circle r="3" fill="#f6c5e0"/><circle cx="6" r="3" fill="#f6c5e0"/><circle cx="3" cy="6" r="3" fill="#f6c5e0"/><circle cx="-3" cy="6" r="3" fill="#f6c5e0"/><circle cx="3" cy="3" r="2.2" fill="#ffd35a"/></g>';
    }
    return s;
  }

  // ========= 枯木 =========
  function stage_dead(c) {
    var cx = W/2, baseY = GY;
    var s = '';
    s += ground(c, true);
    s += '<path d="M' + (cx-4) + ' ' + baseY + ' L' + (cx-3) + ' ' + (baseY-50) + ' Q' + (cx-2) + ' ' + (baseY-80) + ' ' + (cx+5) + ' ' + (baseY-118) + '" stroke="#8a7666" stroke-width="13" fill="none" stroke-linecap="round"/>';
    s += '<path d="M' + (cx+5) + ' ' + baseY + ' L' + (cx+5) + ' ' + (baseY-48) + '" stroke="#7a6656" stroke-width="11" fill="none" stroke-linecap="round" opacity="0.7"/>';
    // 光秃分枝
    s += '<path d="M' + (cx-1) + ' ' + (baseY-70) + ' L' + (cx-25) + ' ' + (baseY-92) + '" stroke="#8a7666" stroke-width="4" fill="none" stroke-linecap="round"/>';
    s += '<path d="M' + (cx+3) + ' ' + (baseY-92) + ' L' + (cx+32) + ' ' + (baseY-108) + '" stroke="#8a7666" stroke-width="4" fill="none" stroke-linecap="round"/>';
    s += '<path d="M' + (cx+5) + ' ' + (baseY-118) + ' L' + (cx+10) + ' ' + (baseY-135) + '" stroke="#8a7666" stroke-width="3" fill="none" stroke-linecap="round"/>';
    // 残叶
    s += leafUse(cx+32, baseY-110, 65, 0.55);
    s += leafUse(cx-25, baseY-94, -65, 0.5);
    return s;
  }

  // 冬日飘雪（叠加）
  function snowOverlay() {
    var s = '';
    for (var i = 0; i < 9; i++) {
      var x = 30 + i * 28, y = 60 + (i % 2) * 50;
      s += '<circle cx="' + x + '" cy="' + y + '" r="2.5" fill="#fff" opacity="0.85"/>';
    }
    return s;
  }

  // 对外 API
  function render(opts) {
    opts = opts || {};
    var season = SEASONS[opts.season || 'summer'];
    var stage = opts.stage || 'sprout';
    var dead = !!opts.dead;
    var S = opts.S || {};
    var out = '<svg viewBox="0 0 ' + W + ' ' + H + '" class="tree-svg' + (dead ? ' is-dead' : '') + '" aria-label="沉香树">';
    out += defs(season);

    var body;
    if (dead) body = stage_dead(season);
    else if (stage === 'seed') body = stage_seed(season);
    else if (stage === 'sprout') body = stage_sprout(season);
    else if (stage === 'sapling') body = stage_sapling(season);
    else if (stage === 'tree') body = stage_tree(season, S);
    else if (stage === 'ancient') body = stage_ancient(season, S);
    else body = stage_sprout(season);
    out += body;

    if (opts.season === 'winter' && !dead) out += snowOverlay();
    out += '</svg>';
    return out;
  }

  window.Tree = { render: render };
})();
