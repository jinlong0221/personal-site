/* 台风实时监测 - 数据驱动渲染 + 动态走向图
 * 数据源: /typhoon.json（由每日自动化更新）
 * 无第三方依赖，纯 SVG + 原生 JS
 */
(function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';

  /* ============ 投影参数 ============ */
  var LON_MIN = 115.5, LON_MAX = 128.0;
  var LAT_MIN = 24.5, LAT_MAX = 36.2;
  var VB_W = 760, VB_H = 600, PAD_L = 48, PAD_T = 26, PAD_R = 22, PAD_B = 30;
  var PLOT_W = VB_W - PAD_L - PAD_R;
  var PLOT_H = VB_H - PAD_T - PAD_B;
  var SHEYANG = { lat: 33.48, lon: 120.27, name: '射阳' };

  function lon2x(lon) { return PAD_L + (lon - LON_MIN) / (LON_MAX - LON_MIN) * PLOT_W; }
  function lat2y(lat) { return PAD_T + (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * PLOT_H; }
  function n(v) { return Math.round(v * 100) / 100; }
  function km2px(km) { return km / 111 / (LAT_MAX - LAT_MIN) * PLOT_H; }

  function haversine(lat1, lon1, lat2, lon2) {
    var R = 6371, rad = Math.PI / 180;
    var dLat = (lat2 - lat1) * rad, dLon = (lon2 - lon1) * rad;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return Math.round(2 * R * Math.asin(Math.sqrt(a)));
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* 距离语义分级：决定颜色与措辞 */
  function distGrade(km) {
    if (km == null) return { cls: 'none', label: '—' };
    if (km < 150) return { cls: 'crit', label: '正面影响' };
    if (km < 400) return { cls: 'high', label: '距离很近' };
    if (km < 800) return { cls: 'mid', label: '外围影响' };
    return { cls: 'low', label: '距离较远' };
  }

  /* ============ 中国东部海岸线（简化，自北向南） ============ */
  var COAST = [
    [37.4, 122.7], [36.9, 122.5], [36.6, 121.4], [36.9, 120.3], [37.0, 119.4],
    [36.3, 119.2], [35.6, 119.6], [35.0, 119.2], [34.75, 119.45], [34.47, 119.80],
    [34.05, 120.25], [33.98, 120.50], [33.50, 120.75], [33.20, 120.90], [32.75, 121.20],
    [32.30, 121.40], [31.95, 121.65], [31.80, 121.85], [31.50, 121.85], [31.20, 121.75],
    [31.00, 121.90], [30.85, 121.85], [30.70, 121.30], [30.35, 120.85], [30.15, 120.90],
    [30.20, 121.30], [29.95, 121.55], [29.70, 121.80], [29.50, 121.85], [29.20, 121.60],
    [29.10, 121.75], [28.85, 121.40], [28.60, 121.60], [28.30, 121.30], [28.08, 121.29],
    [27.95, 120.85], [27.75, 120.75], [27.30, 120.50], [27.15, 120.35], [26.80, 119.90],
    [26.40, 119.80], [26.05, 119.65], [25.60, 119.75], [25.30, 119.30], [25.00, 118.80],
    [24.70, 118.30]
  ];
  var INLAND_CLOSE = [[24.70, LON_MIN], [37.4, LON_MIN]];

  var CITIES = [
    { n: '连云港', lat: 34.60, lon: 119.16 },
    { n: '盐城', lat: 33.35, lon: 120.16 },
    { n: '南通', lat: 31.98, lon: 120.89 },
    { n: '上海', lat: 31.23, lon: 121.47 },
    { n: '杭州', lat: 30.27, lon: 120.15 },
    { n: '宁波', lat: 29.87, lon: 121.55 },
    { n: '台州', lat: 28.66, lon: 121.42 },
    { n: '温州', lat: 27.99, lon: 120.70 },
    { n: '福州', lat: 26.07, lon: 119.30 }
  ];

  /* ============ SVG 走向图 ============ */
  function buildTrackSVG(d) {
    var track = d.track || [];
    if (!track.length) return '<p class="tf-empty">暂无路径数据</p>';

    var cur = d.current || {};
    var wr = cur.windRadius || {};
    var s = [];

    s.push('<svg class="tf-track-svg" id="tfSvg" viewBox="0 0 ' + VB_W + ' ' + VB_H + '" ' +
      'preserveAspectRatio="xMidYMid meet" role="img" ' +
      'aria-label="台风白海豚路径示意图，含射阳位置标注">');

    s.push('<defs>');
    s.push('<linearGradient id="tfSea" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#0d2b45"/><stop offset="100%" stop-color="#123a5c"/></linearGradient>');
    s.push('<linearGradient id="tfLand" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#243a2e"/><stop offset="100%" stop-color="#1d3026"/></linearGradient>');
    s.push('<radialGradient id="tfEyeG"><stop offset="0%" stop-color="#fff" stop-opacity=".95"/>' +
      '<stop offset="55%" stop-color="#9ec9e8" stop-opacity=".45"/>' +
      '<stop offset="100%" stop-color="#4da6e8" stop-opacity="0"/></radialGradient>');
    s.push('<filter id="tfGlow" x="-60%" y="-60%" width="220%" height="220%">' +
      '<feGaussianBlur stdDeviation="3" result="b"/>' +
      '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>');
    s.push('</defs>');

    s.push('<rect x="0" y="0" width="' + VB_W + '" height="' + VB_H + '" fill="url(#tfSea)"/>');

    /* 网格 */
    var g = ['<g stroke="#ffffff" stroke-opacity=".07" stroke-width="1">'];
    var labels = [];
    for (var lo = 116; lo <= 128; lo += 2) {
      var gx = lon2x(lo);
      if (gx < PAD_L - 1 || gx > VB_W - PAD_R + 1) continue;
      g.push('<line x1="' + n(gx) + '" y1="' + PAD_T + '" x2="' + n(gx) + '" y2="' + (VB_H - PAD_B) + '"/>');
      labels.push('<text x="' + n(gx) + '" y="' + (VB_H - PAD_B + 15) + '" class="tf-axis" text-anchor="middle">' + lo + '°E</text>');
    }
    for (var la = 26; la <= 36; la += 2) {
      var gy = lat2y(la);
      if (gy < PAD_T - 1 || gy > VB_H - PAD_B + 1) continue;
      g.push('<line x1="' + PAD_L + '" y1="' + n(gy) + '" x2="' + (VB_W - PAD_R) + '" y2="' + n(gy) + '"/>');
      labels.push('<text x="' + (PAD_L - 7) + '" y="' + n(gy + 4) + '" class="tf-axis" text-anchor="end">' + la + '°N</text>');
    }
    g.push('</g>');
    s.push(g.join(''));

    /* 陆地 + 海岸 */
    var landPath = COAST.concat(INLAND_CLOSE).map(function (p, i) {
      return (i ? 'L' : 'M') + n(lon2x(p[1])) + ' ' + n(lat2y(p[0]));
    }).join(' ') + ' Z';
    s.push('<path d="' + landPath + '" fill="url(#tfLand)"/>');
    var coastLine = COAST.map(function (p, i) {
      return (i ? 'L' : 'M') + n(lon2x(p[1])) + ' ' + n(lat2y(p[0]));
    }).join(' ');
    s.push('<path d="' + coastLine + '" fill="none" stroke="#7fd4c1" stroke-opacity=".5" stroke-width="1.5"/>');
    s.push(labels.join(''));

    /* 城市 */
    var cg = ['<g>'];
    CITIES.forEach(function (c) {
      var cx = lon2x(c.lon), cy = lat2y(c.lat);
      cg.push('<circle cx="' + n(cx) + '" cy="' + n(cy) + '" r="2.2" fill="#cfe4ff" fill-opacity=".65"/>');
      cg.push('<text x="' + n(cx + 5) + '" y="' + n(cy + 3.5) + '" class="tf-city">' + c.n + '</text>');
    });
    cg.push('</g>');
    s.push(cg.join(''));

    /* 风圈（group 可整体平移） */
    s.push('<g id="tfRings">');
    if (wr.r7) {
      s.push('<circle class="tf-ring r7" cx="0" cy="0" r="' + n(km2px(wr.r7)) +
        '" fill="#4da6e8" fill-opacity=".09" stroke="#7cc3f5" stroke-opacity=".4" stroke-width="1" stroke-dasharray="5 4"/>');
    }
    if (wr.r10) {
      s.push('<circle class="tf-ring r10" cx="0" cy="0" r="' + n(km2px(wr.r10)) +
        '" fill="#4faf9b" fill-opacity=".12" stroke="#7fd0bf" stroke-opacity=".5" stroke-width="1" stroke-dasharray="4 3"/>');
    }
    if (wr.r12) {
      s.push('<circle class="tf-ring r12" cx="0" cy="0" r="' + n(km2px(wr.r12)) +
        '" fill="#e81123" fill-opacity=".15" stroke="#ff5a68" stroke-opacity=".55" stroke-width="1"/>');
    }
    s.push('</g>');

    /* 路径：实况 / 预报 */
    var obs = [], fc = [];
    track.forEach(function (p) { (p.forecast ? fc : obs).push(p); });
    function toPath(arr) {
      return arr.map(function (p, i) {
        return (i ? 'L' : 'M') + n(lon2x(p.lon)) + ' ' + n(lat2y(p.lat));
      }).join(' ');
    }
    if (obs.length > 1) {
      s.push('<path id="tfPathObs" d="' + toPath(obs) + '" fill="none" stroke="#ff8c00" ' +
        'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" filter="url(#tfGlow)"/>');
    }
    if (fc.length) {
      var bridge = obs.length ? [obs[obs.length - 1]].concat(fc) : fc;
      s.push('<path id="tfPathFc" d="' + toPath(bridge) + '" fill="none" stroke="#5db8ff" ' +
        'stroke-width="2.6" stroke-dasharray="9 7" stroke-linecap="round"/>');
    }

    /* 射阳连线 + 距离标签（可动） */
    var sx = lon2x(SHEYANG.lon), sy = lat2y(SHEYANG.lat);
    s.push('<line id="tfLine" x1="0" y1="0" x2="' + n(sx) + '" y2="' + n(sy) + '" ' +
      'stroke="#ffffff" stroke-opacity=".26" stroke-width="1.2" stroke-dasharray="3 5"/>');
    s.push('<g id="tfDistG"><rect x="-34" y="-11" width="68" height="19" rx="9.5" fill="#000" fill-opacity=".55"/>' +
      '<text id="tfDistT" x="0" y="3" class="tf-distlabel" text-anchor="middle">— km</text></g>');

    /* 路径点 */
    var pg = ['<g id="tfPts">'];
    track.forEach(function (p, i) {
      var x = lon2x(p.lon), y = lat2y(p.lat);
      var isFc = !!p.forecast, isLand = !!p.landfall;
      var r = isLand ? 5.5 : 4;
      var fill = isFc ? '#5db8ff' : (isLand ? '#e81123' : '#ff8c00');
      pg.push('<circle class="tf-pt" data-i="' + i + '" data-r="' + r + '" cx="' + n(x) + '" cy="' + n(y) +
        '" r="' + r + '" fill="' + fill + '" stroke="#fff" stroke-width="1.6" stroke-opacity=".9"/>');
      if (isLand || i === 0 || i === track.length - 1) {
        var anchor = x > VB_W * 0.72 ? 'end' : 'start';
        pg.push('<text x="' + n(x + (anchor === 'end' ? -9 : 9)) + '" y="' + n(y - 8) +
          '" class="tf-ptlabel" text-anchor="' + anchor + '">' + esc(p.t) + '</text>');
      }
    });
    pg.push('</g>');
    s.push(pg.join(''));

    /* 台风符号（可动） */
    s.push('<g id="tfEye">');
    s.push('<circle r="24" fill="url(#tfEyeG)"/>');
    s.push('<g class="tf-eye-arms">');
    s.push('<path d="M0 0 C -3 -9, -11 -13, -18 -9 C -12 -16, -2 -15, 0 0 Z" fill="#ffffff" fill-opacity=".92"/>');
    s.push('<path d="M0 0 C 3 9, 11 13, 18 9 C 12 16, 2 15, 0 0 Z" fill="#ffffff" fill-opacity=".92"/>');
    s.push('<circle r="3.4" fill="#e81123"/>');
    s.push('</g>');
    s.push('<circle class="tf-eye-wave" r="13" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="1.4"/>');
    s.push('</g>');

    /* 射阳标记 */
    s.push('<g transform="translate(' + n(sx) + ',' + n(sy) + ')">');
    s.push('<circle class="tf-sy-wave" r="9" fill="none" stroke="#ff4757" stroke-width="1.5" stroke-opacity=".9"/>');
    s.push('<circle r="6" fill="#ff4757" stroke="#fff" stroke-width="2"/>');
    s.push('<rect x="11" y="-11" width="46" height="21" rx="5" fill="#ff4757" fill-opacity=".95"/>');
    s.push('<text x="34" y="3.5" class="tf-sylabel" text-anchor="middle">射阳</text>');
    s.push('</g>');

    /* 图例 */
    s.push('<g transform="translate(' + (PAD_L + 6) + ',' + (PAD_T + 6) + ')">');
    s.push('<rect x="0" y="0" width="142" height="92" rx="8" fill="#000" fill-opacity=".4" stroke="#fff" stroke-opacity=".1"/>');
    s.push('<line x1="11" y1="19" x2="31" y2="19" stroke="#ff8c00" stroke-width="3" stroke-linecap="round"/>');
    s.push('<text x="38" y="23" class="tf-lg">实况路径</text>');
    s.push('<line x1="11" y1="38" x2="31" y2="38" stroke="#5db8ff" stroke-width="2.4" stroke-dasharray="6 5" stroke-linecap="round"/>');
    s.push('<text x="38" y="42" class="tf-lg">预报路径</text>');
    s.push('<circle cx="21" cy="57" r="5" fill="#e81123" stroke="#fff" stroke-width="1.3"/>');
    s.push('<text x="38" y="61" class="tf-lg">登陆点</text>');
    s.push('<circle cx="21" cy="76" r="6" fill="none" stroke="#7fd0bf" stroke-width="1.2" stroke-dasharray="3 2"/>');
    s.push('<text x="38" y="80" class="tf-lg">风圈</text>');
    s.push('</g>');

    s.push('</svg>');
    return s.join('');
  }

  /* ============ 走向图区块 ============ */
  function renderTrack(d) {
    var box = document.getElementById('tf-track');
    if (!box) return;
    var track = d.track || [];
    var h = '<div class="tf-track-wrap">' + buildTrackSVG(d) + '<div class="tf-tip" id="tfTip"></div></div>';

    h += '<div class="tf-player">' +
      '<button type="button" class="tf-play" id="tfPlay" aria-label="播放台风路径">' +
      '<span class="tf-play-ico" id="tfPlayIco">▶</span><span id="tfPlayTxt">播放路径</span></button>' +
      '<input type="range" class="tf-range" id="tfRange" min="0" max="' + Math.max(0, track.length - 1) +
      '" step="0.01" value="' + Math.max(0, track.length - 1) + '" aria-label="台风路径时间轴">' +
      '<span class="tf-range-t" id="tfRangeT">—</span></div>';
    h += '<div class="tf-step" id="tfStep"></div>';

    var notes = [];
    if ((d.current || {}).windRadius && d.current.windRadius.note) notes.push('<b>风圈</b>' + esc(d.current.windRadius.note));
    if (d.trackNote) notes.push('<b>不确定性</b>' + esc(d.trackNote));
    if (notes.length) {
      h += '<details class="tf-details"><summary>图例说明与数据口径</summary><div class="tf-details-body">' +
        '<p><b>怎么看</b>橙色实线是已走过的实况路径，蓝色虚线是概率预报（会调整）。红点是射阳，白色虚线标出台风中心到射阳的实时直线距离。同心圈是风圈半径，圈扫到哪里哪里就有对应量级的风。</p>' +
        notes.map(function (t) { return '<p>' + t + '</p>'; }).join('') +
        '<p><b>免责</b>本图依据公开坐标绘制的简化走向，非官方精确底图。精确路径请查中央气象台台风网。</p>' +
        '</div></details>';
    }
    box.innerHTML = h;
    bindTrack(d);
  }

  /* ============ 动画播放器（真正驱动 SVG） ============ */
  function bindTrack(d) {
    var track = d.track || [];
    if (track.length < 2) return;
    var svg = document.getElementById('tfSvg');
    var range = document.getElementById('tfRange');
    var stepBox = document.getElementById('tfStep');
    var rangeT = document.getElementById('tfRangeT');
    var playBtn = document.getElementById('tfPlay');
    var playIco = document.getElementById('tfPlayIco');
    var playTxt = document.getElementById('tfPlayTxt');
    if (!svg || !range || !stepBox) return;

    var eye = document.getElementById('tfEye');
    var rings = document.getElementById('tfRings');
    var line = document.getElementById('tfLine');
    var distG = document.getElementById('tfDistG');
    var distT = document.getElementById('tfDistT');
    var pathObs = document.getElementById('tfPathObs');
    var pathFc = document.getElementById('tfPathFc');
    var pts = svg.querySelectorAll('.tf-pt');
    var tip = document.getElementById('tfTip');

    /* --- 预计算：各点画布坐标 + 累计弧长 --- */
    var XY = track.map(function (p) { return { x: lon2x(p.lon), y: lat2y(p.lat) }; });
    var seg = [], cum = [0], total = 0;
    for (var i = 1; i < XY.length; i++) {
      var dx = XY[i].x - XY[i - 1].x, dy = XY[i].y - XY[i - 1].y;
      var L = Math.sqrt(dx * dx + dy * dy);
      seg.push(L); total += L; cum.push(total);
    }
    var obsCount = 0;
    track.forEach(function (p) { if (!p.forecast) obsCount++; });
    var obsEndLen = cum[Math.max(0, obsCount - 1)];

    var LObs = pathObs ? pathObs.getTotalLength() : 0;
    var LFc = pathFc ? pathFc.getTotalLength() : 0;
    if (pathObs) { pathObs.style.animation = 'none'; pathObs.style.strokeDasharray = LObs; }
    if (pathFc) { pathFc.style.animation = 'none'; pathFc.style.opacity = '1'; }

    var sx = lon2x(SHEYANG.lon), sy = lat2y(SHEYANG.lat);

    /* --- 核心：按连续位置 t（0 ~ track.length-1）绘制一帧 --- */
    function setFrame(t) {
      t = Math.max(0, Math.min(track.length - 1, t));
      var i0 = Math.floor(t);
      var frac = t - i0;
      if (i0 >= track.length - 1) { i0 = track.length - 2; frac = 1; }
      var a = track[i0], b = track[i0 + 1];
      var lat = a.lat + (b.lat - a.lat) * frac;
      var lon = a.lon + (b.lon - a.lon) * frac;
      var x = lon2x(lon), y = lat2y(lat);

      /* 台风符号 + 风圈跟随 */
      if (eye) eye.setAttribute('transform', 'translate(' + n(x) + ',' + n(y) + ')');
      if (rings) rings.setAttribute('transform', 'translate(' + n(x) + ',' + n(y) + ')');

      /* 射阳连线 + 距离 */
      var km = haversine(SHEYANG.lat, SHEYANG.lon, lat, lon);
      if (line) { line.setAttribute('x1', n(x)); line.setAttribute('y1', n(y)); }
      if (distG) distG.setAttribute('transform', 'translate(' + n((x + sx) / 2) + ',' + n((y + sy) / 2) + ')');
      if (distT) distT.textContent = km + ' km';

      /* 路径逐段揭示 */
      var curLen = cum[i0] + (seg[i0] || 0) * frac;
      if (pathObs && LObs > 0) {
        var ro = obsEndLen > 0 ? Math.min(1, curLen / obsEndLen) : 1;
        pathObs.style.strokeDashoffset = LObs * (1 - ro);
      }
      if (pathFc && LFc > 0) {
        var fcSpan = total - obsEndLen;
        var rf = fcSpan > 0 ? Math.max(0, Math.min(1, (curLen - obsEndLen) / fcSpan)) : 0;
        pathFc.style.strokeDasharray = (LFc * rf) + ' ' + LFc;
      }

      /* 点的显隐与高亮 */
      Array.prototype.forEach.call(pts, function (el) {
        var idx = parseInt(el.getAttribute('data-i'), 10);
        var base = parseFloat(el.getAttribute('data-r'));
        var passed = idx <= t + 0.001;
        el.style.opacity = passed ? '1' : '0.22';
        var near = Math.abs(idx - t) < 0.5;
        el.setAttribute('r', near ? base + 3 : base);
        el.style.filter = near ? 'drop-shadow(0 0 6px rgba(255,255,255,.9))' : '';
      });

      /* 步骤卡（贴合最近的点） */
      var si = Math.round(t);
      renderStep(si, km);
      if (rangeT) rangeT.textContent = track[si].t;
    }

    function renderStep(i, kmLive) {
      var p = track[i];
      if (!p) return;
      var km = kmLive != null ? kmLive : haversine(SHEYANG.lat, SHEYANG.lon, p.lat, p.lon);
      var badge = p.forecast
        ? '<span class="tf-step-badge fc">预报</span>'
        : (p.landfall ? '<span class="tf-step-badge land">登陆</span>' : '<span class="tf-step-badge obs">实况</span>');
      stepBox.innerHTML =
        '<div class="tf-step-head">' + badge + '<strong>' + esc(p.t) + '</strong>' +
        '<span class="tf-step-dist">距射阳 <b>' + km + '</b> km</span></div>' +
        '<div class="tf-step-body">' +
        '<span><i>强度</i>' + esc(p.intensity || '—') + '</span>' +
        '<span><i>气压</i>' + esc(p.pressure || '—') + '</span>' +
        '<span><i>坐标</i>' + n(p.lat) + '°N ' + n(p.lon) + '°E</span></div>';
    }

    /* --- 播放控制（requestAnimationFrame 平滑插值） --- */
    var raf = null, playing = false;
    var SPEED = 0.9; // 每秒推进的"点"数

    function stop() {
      playing = false;
      if (raf) { cancelAnimationFrame(raf); raf = null; }
      if (playIco) playIco.textContent = '▶';
      if (playTxt) playTxt.textContent = '播放路径';
      if (playBtn) playBtn.classList.remove('playing');
    }

    function play() {
      if (playing) { stop(); return; }
      playing = true;
      if (playIco) playIco.textContent = '❚❚';
      if (playTxt) playTxt.textContent = '暂停';
      if (playBtn) playBtn.classList.add('playing');

      var t = parseFloat(range.value);
      /* 已在末尾 → 从头播 */
      if (t >= track.length - 1 - 0.01) t = 0;
      var last = null;
      function tick(ts) {
        if (!playing) return;
        if (last == null) last = ts;
        var dt = (ts - last) / 1000;
        last = ts;
        t += dt * SPEED;
        if (t >= track.length - 1) {
          t = track.length - 1;
          range.value = t; setFrame(t); stop(); return;
        }
        range.value = t;
        setFrame(t);
        raf = requestAnimationFrame(tick);
      }
      raf = requestAnimationFrame(tick);
    }

    if (playBtn) playBtn.addEventListener('click', play);
    range.addEventListener('input', function () { stop(); setFrame(parseFloat(range.value)); });

    /* 路径点交互 */
    Array.prototype.forEach.call(pts, function (el) {
      var idx = parseInt(el.getAttribute('data-i'), 10);
      el.style.cursor = 'pointer';
      el.addEventListener('mouseenter', function () {
        var p = track[idx];
        if (!p || !tip) return;
        tip.innerHTML = '<b>' + esc(p.t) + '</b>' + esc(p.intensity || '');
        tip.classList.add('show');
        var bb = svg.getBoundingClientRect(), pr = el.getBoundingClientRect();
        tip.style.left = ((pr.left + pr.width / 2 - bb.left) / bb.width * 100) + '%';
        tip.style.top = ((pr.top - bb.top) / bb.height * 100) + '%';
      });
      el.addEventListener('mouseleave', function () { if (tip) tip.classList.remove('show'); });
      el.addEventListener('click', function () { stop(); range.value = idx; setFrame(idx); });
    });

    /* 初始：停在"当前"点 */
    var curIdx = track.length - 1;
    for (var k = 0; k < track.length; k++) { if (track[k].current) { curIdx = k; break; } }
    range.value = curIdx;
    setFrame(curIdx);

    window.__tfStop = stop; /* 供静默轮询在重渲染前停掉旧动画，避免泄漏 */
  }

  /* ============ 当前状态 ============ */
  function renderStatus(d) {
    var box = document.getElementById('tf-status');
    if (!box) return;
    var c = d.current || {};
    var km = (c.lat != null) ? haversine(SHEYANG.lat, SHEYANG.lon, c.lat, c.lon) : null;
    var gr = distGrade(km);

    /* 状态徽标只显示短标签：优先用 statusShort（短徽标），否则按 statusLevel 映射。
       长文 status（监测续报）绝不进徽标，改为下方独立卡片渲染，避免"文字山"撑破布局。 */
    var STATUS_SHORT_MAP = { danger: '高风险预警', warn: '在效监测', info: '收尾/解除' };
    var statusBadge = (d.statusShort && String(d.statusShort).trim())
      ? String(d.statusShort).trim()
      : (STATUS_SHORT_MAP[d.statusLevel] || '监测中');

    var h = '<div class="tf-hero-card">';
    h += '<div class="tf-hero-main">';
    h += '<div class="tf-hero-name"><span class="tf-spin">🌀</span><b>' + esc(d.name) + '</b>' +
      '<span class="tf-hero-no">' + esc(d.year) + ' 年第 ' + esc(d.no) + ' 号</span>' +
      '<span class="tf-hero-status ' + esc(d.statusLevel || 'warn') + '">' + esc(statusBadge) + '</span></div>';
    h += '</div>';
    if (km != null) {
      h += '<div class="tf-hero-dist ' + gr.cls + '"><span class="tf-dist-num">' + km + '</span>' +
        '<span class="tf-dist-unit">km</span><span class="tf-dist-label">距射阳 · ' + gr.label + '</span></div>';
    }
    h += '</div>';

    /* 仅保留短字段（强度/气压）；长段 location/move/trend 不进首屏 */
    var cells = [
      ['中心强度', c.intensity || '—'],
      ['中心气压', c.pressure || '—']
    ];
    h += '<div class="tf-status-grid">';
    cells.forEach(function (it) {
      h += '<div class="tf-cell"><span class="tf-cell-k">' + it[0] + '</span>' +
        '<span class="tf-cell-v">' + esc(it[1]) + '</span></div>';
    });
    h += '</div>';
    box.innerHTML = h;

    /* 长文（背景研判 / 监测续报）彻底沉底，首屏一个字都不堆 */
    var lt = '';
    if (d.summary) {
      lt += '<details class="tf-details"><summary>台风背景与整体研判（点击展开）</summary>' +
        '<div class="tf-details-body"><p>' + esc(d.summary) + '</p></div></details>';
    }
    if (d.status) {
      lt += '<details class="tf-details"><summary>监测续报原文（点击展开）</summary>' +
        '<div class="tf-details-body"><p>' + esc(d.status) + '</p></div></details>';
    }
    window.__tfLongText = lt;
  }

  /* ============ 射阳影响 ============ */
  function renderSheyang(d) {
    var box = document.getElementById('tf-sheyang');
    if (!box) return;
    var sy = d.sheyang || {};
    var h = '';

    h += '<div class="tf-verdict">' +
      '<div class="tf-verdict-badge">' + esc(sy.riskLevel || '—') + '</div>' +
      '<div class="tf-verdict-body"><b>' + esc(sy.riskLabel || '') + '</b></div></div>';
    if (sy.riskNote) {
      h += '<details class="tf-details"><summary>影响说明（点击展开）</summary>' +
        '<div class="tf-details-body"><p>' + esc(sy.riskNote) + '</p></div></details>';
    }

    if (sy.alerts && sy.alerts.length) {
      h += '<div class="tf-alerts">';
      sy.alerts.forEach(function (a) {
        if (typeof a === 'string') { h += '<span class="tf-alert blue"><b>' + esc(a) + '</b></span>'; return; }
        h += '<span class="tf-alert ' + esc(a.color || 'blue') + '">' +
          '<b>' + esc(a.name) + '</b>' + (a.level ? '<i>' + esc(a.level) + '</i>' : '') +
          '<em>' + esc(a.issuer || '') + (a.time ? ' · ' + esc(a.time) : '') + '</em></span>';
      });
      h += '</div>';
    }

    h += '<div class="tf-key">';
    if (sy.period) h += '<div class="tf-key-item"><span>影响时段</span><b>' + esc(sy.period) + '</b></div>';
    if (sy.peakWindow) h += '<div class="tf-key-item"><span>最强时段</span><b>' + esc(sy.peakWindow) + '</b></div>';
    h += '</div>';

    if (sy.windDaily && sy.windDaily.length) {
      h += '<div class="tf-wind-chart"><div class="tf-chart-title">分日风力预报 <em>江苏省气象台 / 射阳县气象台</em></div>';
      sy.windDaily.forEach(function (w) {
        var seaPct = Math.min(100, (w.seaScale || 0) / 12 * 100);
        var landPct = Math.min(100, (w.landScale || 0) / 12 * 100);
        h += '<div class="tf-wrow' + (w.peak ? ' peak' : '') + '">' +
          '<span class="tf-wdate">' + esc(w.date) + (w.peak ? '<i>峰值</i>' : '') + '</span>' +
          '<div class="tf-wbars">' +
          '<div class="tf-wbar"><span class="tf-wtag">海上</span>' +
          '<div class="tf-wtrack"><div class="tf-wfill sea" style="width:' + seaPct + '%"></div></div>' +
          '<span class="tf-wval">' + esc(w.sea) + '</span></div>' +
          '<div class="tf-wbar"><span class="tf-wtag">陆上</span>' +
          '<div class="tf-wtrack"><div class="tf-wfill land" style="width:' + landPct + '%"></div></div>' +
          '<span class="tf-wval">' + esc(w.land) + '</span></div>' +
          '</div></div>';
      });
      h += '</div>';
    }

    /* 风险 + 实况 + 时间线：收进折叠，默认展开时间线（最实用） */
    if (sy.timeline && sy.timeline.length) {
      h += '<details class="tf-details"><summary>过程时间线（点击展开）</summary><div class="tf-details-body" style="padding-top:12px">';
      h += '<div class="tf-timeline">';
      sy.timeline.forEach(function (t) {
        h += '<div class="tf-tl-item ' + esc(t.state || 'future') + '">' +
          '<span class="tf-tl-dot"></span><span class="tf-tl-date">' + esc(t.date) + '</span>' +
          '<span class="tf-tl-text">' + esc(t.text) + '</span></div>';
      });
      h += '</div>';
      h += '</div></details>';
    }

    var extra = '';
    if (sy.risk && sy.risk.length) {
      extra += '<div class="tf-risk-grid">';
      sy.risk.forEach(function (r) {
        if (typeof r === 'string') { extra += '<div class="tf-risk-card mid"><p>' + esc(r) + '</p></div>'; return; }
        extra += '<div class="tf-risk-card ' + esc(r.level || 'mid') + '"><b>' + esc(r.title) + '</b><p>' + esc(r.text) + '</p></div>';
      });
      extra += '</div>';
    }
    if (sy.wind) extra += '<p class="tf-xline"><b>风力</b>' + esc(sy.wind) + '</p>';
    if (sy.rain) extra += '<p class="tf-xline"><b>降雨</b>' + esc(sy.rain) + '</p>';
    if (sy.observed) extra += '<p class="tf-xline"><b>本地实况</b>' + esc(sy.observed) + '</p>';
    if (extra) {
      h += '<details class="tf-details"><summary>展开风险清单与详细预报</summary>' +
        '<div class="tf-details-body">' + extra + '</div></details>';
    }

    box.innerHTML = h;
  }

  /* ============ 防范措施（Tab 切换） ============ */
  var ICONS = {
    home: '<path d="M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    walk: '<circle cx="13" cy="4" r="2"/><path d="M11 21l2-6-3-2 1-5 4 2 3 1M9 21l2-5"/>',
    car: '<path d="M5 16v3M19 16v3M3 16h18l-1.5-5.5A2 2 0 0 0 17.6 9H6.4a2 2 0 0 0-1.9 1.5z"/><circle cx="7" cy="16" r="1.6"/><circle cx="17" cy="16" r="1.6"/>',
    leaf: '<path d="M4 20c0-8 6-14 16-14 0 10-6 14-16 14z"/><path d="M4 20c4-4 8-6 12-7"/>'
  };

  function renderPrevention(d) {
    var box = document.getElementById('tf-prevention');
    if (!box) return;
    var p = d.prevention || {};
    var order = ['home', 'outdoor', 'drive', 'farm'];
    var fbTitle = { home: '居家', outdoor: '外出', drive: '驾车', farm: '农渔' };
    var fbIcon = { home: 'home', outdoor: 'walk', drive: 'car', farm: 'leaf' };
    var groups = [];
    order.forEach(function (k) {
      var g = p[k];
      if (!g) return;
      var items = Array.isArray(g) ? g : (g.items || []);
      if (!items.length) return;
      groups.push({ key: k, title: (g && g.title) || fbTitle[k], icon: (g && g.icon) || fbIcon[k], items: items });
    });
    if (!groups.length) return;

    var h = '<details class="tf-details"><summary>防台风措施（点击展开）</summary><div class="tf-details-body" style="padding-top:12px"><div class="tf-tabs" role="tablist">';
    groups.forEach(function (g, i) {
      h += '<button type="button" class="tf-tab' + (i === 0 ? ' on' : '') + '" data-k="' + g.key + '" role="tab">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" ' +
        'stroke-linecap="round" stroke-linejoin="round">' + (ICONS[g.icon] || ICONS.home) + '</svg>' +
        esc(g.title) + '</button>';
    });
    h += '</div>';
    groups.forEach(function (g, i) {
      h += '<ul class="tf-prev-list' + (i === 0 ? ' on' : '') + '" data-k="' + g.key + '">';
      g.items.forEach(function (t) { h += '<li>' + esc(t) + '</li>'; });
      h += '</ul>';
    });
    h += '</div></details>';
    box.innerHTML = h;

    var tabs = box.querySelectorAll('.tf-tab');
    var lists = box.querySelectorAll('.tf-prev-list');
    Array.prototype.forEach.call(tabs, function (btn) {
      btn.addEventListener('click', function () {
        var k = btn.getAttribute('data-k');
        Array.prototype.forEach.call(tabs, function (b) { b.classList.toggle('on', b === btn); });
        Array.prototype.forEach.call(lists, function (l) { l.classList.toggle('on', l.getAttribute('data-k') === k); });
      });
    });
  }

  /* ============ 实时动态（默认 3 条） ============ */
  function renderFeed(d) {
    var box = document.getElementById('autoNewsBody');
    if (!box) return;
    var list = d.feed || [];
    if (!list.length) { box.innerHTML = '<p class="tf-empty">暂无动态</p>'; return; }
    var SHOW = 3;
    function itemHtml(it, hidden) {
      var tags = '';
      (it.tags || []).forEach(function (t) {
        if (typeof t === 'string') tags += '<span class="news-tag">' + esc(t) + '</span>';
        else tags += '<span class="news-tag ' + esc(t.class || '') + '">' + esc(t.text) + '</span>';
      });
      return '<div class="news-item' + (hidden ? ' tf-hide' : '') + '">' +
        '<div class="news-meta"><span class="news-date">' + esc(it.date) + '</span>' + tags + '</div>' +
        (it.content ? '<details class="tf-details"><summary>动态详情（点击展开）</summary><div class="tf-details-body"><div class="news-content">' + esc(it.content) + '</div></div></details>' : '') +
        (it.source ? '<div class="tf-src">来源：' + esc(it.source) + '</div>' : '') + '</div>';
    }
    var h = '';
    list.forEach(function (it, i) { h += itemHtml(it, i >= SHOW); });
    if (list.length > SHOW) {
      h += '<button type="button" class="tf-more" id="tfMore">展开全部 ' + list.length + ' 条动态</button>';
    }
    box.innerHTML = h;
    var cnt = document.getElementById('autoNewsCount');
    if (cnt) cnt.textContent = list.length;

    var more = document.getElementById('tfMore');
    if (more) {
      more.addEventListener('click', function () {
        var hid = box.querySelectorAll('.news-item.tf-hide');
        if (hid.length) {
          Array.prototype.forEach.call(hid, function (el) { el.classList.remove('tf-hide'); });
          more.textContent = '收起';
        } else {
          Array.prototype.forEach.call(box.querySelectorAll('.news-item'), function (el, i) {
            if (i >= SHOW) el.classList.add('tf-hide');
          });
          more.textContent = '展开全部 ' + list.length + ' 条动态';
        }
      });
    }
  }

  /* ============ 来源与免责 ============ */
  function renderSources(d) {
    var box = document.getElementById('tf-sources');
    if (!box) return;
    var h = '';
    if (d.sources && d.sources.length) {
      h += '<div class="tf-src-list"><span>数据源</span>';
      d.sources.forEach(function (s) {
        h += '<a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.name) + '</a>';
      });
      h += '</div>';
    }
    if (d.disclaimer) h += '<p class="tf-disclaimer">' + esc(d.disclaimer) + '</p>';
    box.innerHTML = h;
  }

  /* 把长文统一渲染到页面底部，首屏只留可视化 */
  function renderLongText() {
    var box = document.getElementById('tf-longtext');
    if (!box) return;
    box.innerHTML = window.__tfLongText || '';
  }

  function renderUpdated(d) {
    var el = document.getElementById('lastNewsUpdate');
    if (!el || !d.updated) return;
    var dt = new Date(d.updated);
    if (isNaN(dt.getTime())) { el.textContent = d.updated; return; }
    var pad = function (v) { return v < 10 ? '0' + v : '' + v; };
    el.textContent = (dt.getMonth() + 1) + '月' + dt.getDate() + '日 ' + pad(dt.getHours()) + ':' + pad(dt.getMinutes());
  }

  /* ============ 折叠块 polyfill：兼容旧版 WebView / 微信，默认强制收起 ============ */
  function polyfillDetails() {
    var test = document.createElement('details');
    var ok = 'open' in test;
    if (ok) {
      /* 即使支持 details，也强制确保没有 open 属性的 .tf-details 都闭合 */
      Array.prototype.forEach.call(document.querySelectorAll('.tf-details:not([open])'), function (el) {
        el.open = false;
      });
    }
    /* 对 summary 做显式点击绑定，防止某些 WebView 不触发 toggle */
    Array.prototype.forEach.call(document.querySelectorAll('.tf-details>summary'), function (sum) {
      sum.addEventListener('click', function (e) {
        var det = sum.parentNode;
        if (det) {
          e.preventDefault();
          det.open = !det.open;
        }
      });
    });
  }

  /* ============ 启动 ============ */
  var lastSig = null;

  function renderAll(d) {
    renderUpdated(d);
    renderStatus(d);
    renderTrack(d);
    renderSheyang(d);
    renderPrevention(d);
    renderFeed(d);
    renderSources(d);
    renderLongText();
  }

  /* 抓取用户当前浏览状态，重渲染后无感还原 */
  function captureState() {
    var st = { scrollY: window.scrollY };
    var ds = document.querySelectorAll('.tf-details');
    st.details = Array.prototype.map.call(ds, function (d) { return d.open; });
    var onTab = document.querySelector('.tf-tab.on');
    st.tab = onTab ? onTab.getAttribute('data-k') : null;
    var more = document.getElementById('tfMore');
    st.feedOpen = !!(more && more.textContent.indexOf('收起') >= 0);
    var r = document.getElementById('tfRange');
    st.rangeT = r ? parseFloat(r.value) : null;
    var p = document.getElementById('tfPlay');
    st.playing = !!(p && p.classList.contains('playing'));
    return st;
  }

  function restoreState(st) {
    if (!st) return;
    var ds = document.querySelectorAll('.tf-details');
    st.details.forEach(function (open, i) { if (ds[i]) ds[i].open = open; });
    if (st.tab) {
      Array.prototype.forEach.call(document.querySelectorAll('.tf-tab'), function (b) {
        b.classList.toggle('on', b.getAttribute('data-k') === st.tab);
      });
      Array.prototype.forEach.call(document.querySelectorAll('.tf-prev-list'), function (l) {
        l.classList.toggle('on', l.getAttribute('data-k') === st.tab);
      });
    }
    if (st.feedOpen) {
      var more = document.getElementById('tfMore');
      if (more) more.click();
    }
    if (st.rangeT != null) {
      var r = document.getElementById('tfRange');
      if (r) { r.value = st.rangeT; r.dispatchEvent(new Event('input', { bubbles: true })); }
    }
    if (st.playing) {
      var p = document.getElementById('tfPlay');
      if (p) p.click();
    }
    window.scrollTo(0, st.scrollY);
  }

  function init() {
    polyfillDetails(); /* 先绑定折叠，避免数据回来前默认展开 */
    fetch('typhoon.json?v=' + Date.now())
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (d) {
        lastSig = JSON.stringify(d);
        renderAll(d);
        polyfillDetails(); /* 重新绑定渲染后新增的 details */
        /* 每 3 分钟静默轮询：仅当数据有变化才重渲染，且保留用户滚动/播放/展开状态 */
        if (!window.__tfPolling) {
          window.__tfPolling = true;
          setInterval(function () {
            fetch('typhoon.json?v=' + Date.now())
              .then(function (r) { if (!r.ok) return null; return r.json(); })
              .then(function (nd) {
                if (!nd) return;
                var sig = JSON.stringify(nd);
                if (sig === lastSig) return; /* 无变化，不打扰 */
                lastSig = sig;
                if (window.__tfStop) window.__tfStop(); /* 停掉旧播放动画，避免泄漏 */
                var st = captureState();
                renderAll(nd);
                polyfillDetails();
                restoreState(st);
              })
              .catch(function () {});
          }, 3 * 60 * 1000);
        }
      })
      .catch(function (e) {
        var box = document.getElementById('tf-status');
        if (box) box.innerHTML = '<p class="tf-empty">台风数据加载失败，请稍后刷新。（' + esc(e.message) + '）</p>';
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
