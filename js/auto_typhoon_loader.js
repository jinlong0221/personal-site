/* 台风实时监测 - 数据驱动渲染 + 动态走向示意图
 * 数据源: /typhoon.json（由每日自动化更新）
 * 无第三方依赖，纯 SVG + 原生 JS
 */
(function () {
  'use strict';

  /* ============ 投影参数 ============ */
  var LON_MIN = 115.5, LON_MAX = 128.0;
  var LAT_MIN = 24.5, LAT_MAX = 36.2;
  var VB_W = 760, VB_H = 620, PAD_L = 52, PAD_T = 30, PAD_R = 26, PAD_B = 34;
  var PLOT_W = VB_W - PAD_L - PAD_R;
  var PLOT_H = VB_H - PAD_T - PAD_B;
  var SHEYANG = { lat: 33.776, lon: 120.26, name: '射阳' };

  function lon2x(lon) { return PAD_L + (lon - LON_MIN) / (LON_MAX - LON_MIN) * PLOT_W; }
  function lat2y(lat) { return PAD_T + (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * PLOT_H; }
  function n(v) { return Math.round(v * 100) / 100; }

  /* 公里 -> 画布像素（按纬度方向换算，1° 纬度 ≈ 111km） */
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

  /* 内陆封口（西边界，让陆地成为闭合面） */
  var INLAND_CLOSE = [[24.70, LON_MIN], [37.4, LON_MIN]];

  /* 城市标注 */
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

    s.push('<svg class="tf-track-svg" viewBox="0 0 ' + VB_W + ' ' + VB_H + '" ' +
      'preserveAspectRatio="xMidYMid meet" role="img" ' +
      'aria-label="台风白海豚路径示意图，含射阳位置标注">');

    /* --- defs：渐变、滤镜、动画 --- */
    s.push('<defs>');
    s.push('<linearGradient id="tfSea" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#0d2b45"/><stop offset="100%" stop-color="#123a5c"/></linearGradient>');
    s.push('<linearGradient id="tfLand" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#243a2e"/><stop offset="100%" stop-color="#1d3026"/></linearGradient>');
    s.push('<radialGradient id="tfEye"><stop offset="0%" stop-color="#fff" stop-opacity=".95"/>' +
      '<stop offset="55%" stop-color="#ffd28a" stop-opacity=".55"/>' +
      '<stop offset="100%" stop-color="#ff6b35" stop-opacity="0"/></radialGradient>');
    s.push('<filter id="tfGlow" x="-60%" y="-60%" width="220%" height="220%">' +
      '<feGaussianBlur stdDeviation="3.2" result="b"/>' +
      '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>');
    s.push('<filter id="tfSoft" x="-40%" y="-40%" width="180%" height="180%">' +
      '<feGaussianBlur stdDeviation="1.6"/></filter>');
    s.push('</defs>');

    /* --- 海洋底 --- */
    s.push('<rect x="0" y="0" width="' + VB_W + '" height="' + VB_H + '" fill="url(#tfSea)"/>');

    /* --- 经纬网格 --- */
    var g = ['<g class="tf-grid" stroke="#ffffff" stroke-opacity=".07" stroke-width="1">'];
    var labels = [];
    for (var lo = 116; lo <= 128; lo += 2) {
      var gx = lon2x(lo);
      if (gx < PAD_L - 1 || gx > VB_W - PAD_R + 1) continue;
      g.push('<line x1="' + n(gx) + '" y1="' + PAD_T + '" x2="' + n(gx) + '" y2="' + (VB_H - PAD_B) + '"/>');
      labels.push('<text x="' + n(gx) + '" y="' + (VB_H - PAD_B + 16) + '" class="tf-axis" text-anchor="middle">' + lo + '°E</text>');
    }
    for (var la = 26; la <= 36; la += 2) {
      var gy = lat2y(la);
      if (gy < PAD_T - 1 || gy > VB_H - PAD_B + 1) continue;
      g.push('<line x1="' + PAD_L + '" y1="' + n(gy) + '" x2="' + (VB_W - PAD_R) + '" y2="' + n(gy) + '"/>');
      labels.push('<text x="' + (PAD_L - 8) + '" y="' + n(gy + 4) + '" class="tf-axis" text-anchor="end">' + la + '°N</text>');
    }
    g.push('</g>');
    s.push(g.join(''));

    /* --- 陆地 --- */
    var landPts = COAST.concat(INLAND_CLOSE);
    var landPath = landPts.map(function (p, i) {
      return (i ? 'L' : 'M') + n(lon2x(p[1])) + ' ' + n(lat2y(p[0]));
    }).join(' ') + ' Z';
    s.push('<path d="' + landPath + '" fill="url(#tfLand)" stroke="none"/>');
    /* 海岸高亮线 */
    var coastLine = COAST.map(function (p, i) {
      return (i ? 'L' : 'M') + n(lon2x(p[1])) + ' ' + n(lat2y(p[0]));
    }).join(' ');
    s.push('<path d="' + coastLine + '" fill="none" stroke="#7fd4c1" stroke-opacity=".55" stroke-width="1.6"/>');

    s.push(labels.join(''));

    /* --- 城市点 --- */
    var cg = ['<g class="tf-cities">'];
    CITIES.forEach(function (c) {
      var cx = lon2x(c.lon), cy = lat2y(c.lat);
      cg.push('<circle cx="' + n(cx) + '" cy="' + n(cy) + '" r="2.2" fill="#cfe4ff" fill-opacity=".7"/>');
      cg.push('<text x="' + n(cx + 5) + '" y="' + n(cy + 3.5) + '" class="tf-city">' + c.n + '</text>');
    });
    cg.push('</g>');
    s.push(cg.join(''));

    /* --- 风圈（以当前中心为圆心） --- */
    var ccx = lon2x(cur.lon), ccy = lat2y(cur.lat);
    if (wr.r7) {
      s.push('<g class="tf-rings">');
      s.push('<circle cx="' + n(ccx) + '" cy="' + n(ccy) + '" r="' + n(km2px(wr.r7)) +
        '" fill="#4da6e8" fill-opacity=".10" stroke="#7cc3f5" stroke-opacity=".45" stroke-width="1" stroke-dasharray="5 4">' +
        '<animate attributeName="fill-opacity" values=".10;.18;.10" dur="4s" repeatCount="indefinite"/></circle>');
      if (wr.r10) {
        s.push('<circle cx="' + n(ccx) + '" cy="' + n(ccy) + '" r="' + n(km2px(wr.r10)) +
          '" fill="#ffb02e" fill-opacity=".12" stroke="#ffc65c" stroke-opacity=".5" stroke-width="1" stroke-dasharray="4 3">' +
          '<animate attributeName="fill-opacity" values=".12;.22;.12" dur="3.2s" repeatCount="indefinite"/></circle>');
      }
      if (wr.r12) {
        s.push('<circle cx="' + n(ccx) + '" cy="' + n(ccy) + '" r="' + n(km2px(wr.r12)) +
          '" fill="#e81123" fill-opacity=".16" stroke="#ff5a68" stroke-opacity=".6" stroke-width="1">' +
          '<animate attributeName="fill-opacity" values=".16;.30;.16" dur="2.4s" repeatCount="indefinite"/></circle>');
      }
      s.push('</g>');
    }

    /* --- 路径：实况段 / 预报段 --- */
    var obs = [], fc = [];
    track.forEach(function (p) { (p.forecast ? fc : obs).push(p); });
    function toPath(arr) {
      return arr.map(function (p, i) {
        return (i ? 'L' : 'M') + n(lon2x(p.lon)) + ' ' + n(lat2y(p.lat));
      }).join(' ');
    }
    if (obs.length > 1) {
      var op = toPath(obs);
      s.push('<path class="tf-path-obs" d="' + op + '" fill="none" stroke="#ff8c00" ' +
        'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" filter="url(#tfGlow)"/>');
    }
    if (fc.length) {
      var bridge = obs.length ? [obs[obs.length - 1]].concat(fc) : fc;
      s.push('<path class="tf-path-fc" d="' + toPath(bridge) + '" fill="none" stroke="#5db8ff" ' +
        'stroke-width="2.6" stroke-dasharray="9 7" stroke-linecap="round"/>');
    }

    /* --- 射阳连线（当前中心 -> 射阳） --- */
    var sx = lon2x(SHEYANG.lon), sy = lat2y(SHEYANG.lat);
    var distKm = haversine(SHEYANG.lat, SHEYANG.lon, cur.lat, cur.lon);
    s.push('<line x1="' + n(ccx) + '" y1="' + n(ccy) + '" x2="' + n(sx) + '" y2="' + n(sy) + '" ' +
      'stroke="#ffffff" stroke-opacity=".28" stroke-width="1.2" stroke-dasharray="3 5"/>');
    var mx = (ccx + sx) / 2, my = (ccy + sy) / 2;
    s.push('<g><rect x="' + n(mx - 34) + '" y="' + n(my - 11) + '" width="68" height="19" rx="9.5" ' +
      'fill="#000" fill-opacity=".5"/><text x="' + n(mx) + '" y="' + n(my + 2.5) + '" ' +
      'class="tf-distlabel" text-anchor="middle">' + distKm + ' km</text></g>');

    /* --- 路径点 --- */
    var pg = ['<g class="tf-pts">'];
    track.forEach(function (p, i) {
      var x = lon2x(p.lon), y = lat2y(p.lat);
      var isFc = !!p.forecast, isLand = !!p.landfall, isCur = !!p.current;
      var r = isCur ? 0 : (isLand ? 5.5 : 4);
      var fill = isFc ? '#5db8ff' : (isLand ? '#e81123' : '#ffb02e');
      if (!isCur) {
        pg.push('<circle class="tf-pt" data-i="' + i + '" cx="' + n(x) + '" cy="' + n(y) + '" r="' + r +
          '" fill="' + fill + '" stroke="#fff" stroke-width="1.6" stroke-opacity=".9"/>');
      }
      /* 命中点的时间小标签（隔点显示避免拥挤） */
      if (isLand || isFc || i === 0) {
        var anchor = x > VB_W * 0.72 ? 'end' : 'start';
        var dx = anchor === 'end' ? -9 : 9;
        pg.push('<text x="' + n(x + dx) + '" y="' + n(y - 8) + '" class="tf-ptlabel" text-anchor="' + anchor + '">' +
          esc(p.t) + '</text>');
      }
    });
    pg.push('</g>');
    s.push(pg.join(''));

    /* --- 台风符号（旋转动画） --- */
    s.push('<g class="tf-eye" transform="translate(' + n(ccx) + ',' + n(ccy) + ')">');
    s.push('<circle r="26" fill="url(#tfEye)"/>');
    s.push('<g>');
    s.push('<animateTransform attributeName="transform" type="rotate" from="0" to="-360" dur="6s" repeatCount="indefinite"/>');
    /* 两条旋臂 */
    s.push('<path d="M0 0 C -3 -9, -11 -13, -18 -9 C -12 -16, -2 -15, 0 0 Z" fill="#ffffff" fill-opacity=".92"/>');
    s.push('<path d="M0 0 C 3 9, 11 13, 18 9 C 12 16, 2 15, 0 0 Z" fill="#ffffff" fill-opacity=".92"/>');
    s.push('<circle r="3.4" fill="#e81123"/>');
    s.push('</g>');
    /* 外圈脉冲 */
    s.push('<circle r="14" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="1.4">' +
      '<animate attributeName="r" values="14;30;14" dur="2.6s" repeatCount="indefinite"/>' +
      '<animate attributeName="stroke-opacity" values=".8;0;.8" dur="2.6s" repeatCount="indefinite"/></circle>');
    s.push('</g>');

    /* --- 射阳标记（重点） --- */
    s.push('<g class="tf-sy" transform="translate(' + n(sx) + ',' + n(sy) + ')">');
    s.push('<circle r="9" fill="none" stroke="#ff4757" stroke-width="1.5" stroke-opacity=".9">' +
      '<animate attributeName="r" values="9;20;9" dur="2.2s" repeatCount="indefinite"/>' +
      '<animate attributeName="stroke-opacity" values=".9;0;.9" dur="2.2s" repeatCount="indefinite"/></circle>');
    s.push('<circle r="6" fill="#ff4757" stroke="#fff" stroke-width="2"/>');
    s.push('<rect x="11" y="-11" width="46" height="21" rx="5" fill="#ff4757" fill-opacity=".95"/>');
    s.push('<text x="34" y="3.5" class="tf-sylabel" text-anchor="middle">射阳</text>');
    s.push('</g>');

    /* --- 图例 --- */
    var lx = PAD_L + 8, ly = PAD_T + 8;
    s.push('<g class="tf-legend" transform="translate(' + lx + ',' + ly + ')">');
    s.push('<rect x="0" y="0" width="150" height="112" rx="8" fill="#000" fill-opacity=".42" stroke="#fff" stroke-opacity=".12"/>');
    s.push('<line x1="12" y1="20" x2="34" y2="20" stroke="#ff8c00" stroke-width="3.2" stroke-linecap="round"/>');
    s.push('<text x="41" y="24" class="tf-lg">实况路径</text>');
    s.push('<line x1="12" y1="40" x2="34" y2="40" stroke="#5db8ff" stroke-width="2.6" stroke-dasharray="6 5" stroke-linecap="round"/>');
    s.push('<text x="41" y="44" class="tf-lg">预报路径</text>');
    s.push('<circle cx="23" cy="59" r="5" fill="#e81123" stroke="#fff" stroke-width="1.4"/>');
    s.push('<text x="41" y="63" class="tf-lg">登陆点</text>');
    s.push('<circle cx="23" cy="78" r="6" fill="none" stroke="#ffc65c" stroke-width="1.2" stroke-dasharray="3 2"/>');
    s.push('<text x="41" y="82" class="tf-lg">十级风圈</text>');
    s.push('<circle cx="23" cy="97" r="6" fill="none" stroke="#7cc3f5" stroke-width="1.2" stroke-dasharray="4 3"/>');
    s.push('<text x="41" y="101" class="tf-lg">七级风圈</text>');
    s.push('</g>');

    s.push('</svg>');
    return s.join('');
  }

  /* ============ 渲染：走向图区块 ============ */
  function renderTrack(d) {
    var box = document.getElementById('tf-track');
    if (!box) return;
    var cur = d.current || {};
    var wr = cur.windRadius || {};
    var html = '<div class="tf-track-wrap">' + buildTrackSVG(d) + '<div class="tf-tip" id="tfTip"></div></div>';

    /* 时间轴播放器 */
    var track = d.track || [];
    html += '<div class="tf-player">' +
      '<button type="button" class="tf-play" id="tfPlay" aria-label="播放路径">' +
      '<span class="tf-play-ico" id="tfPlayIco">▶</span><span id="tfPlayTxt">播放路径</span></button>' +
      '<input type="range" class="tf-range" id="tfRange" min="0" max="' + (track.length - 1) +
      '" value="' + (track.length - 1) + '" aria-label="台风路径时间轴">' +
      '<span class="tf-range-t" id="tfRangeT">—</span>' +
      '</div>';
    html += '<div class="tf-step" id="tfStep"></div>';

    if (wr.note) {
      html += '<p class="tf-note"><strong>风圈说明：</strong>' + esc(wr.note) + '</p>';
    }
    if (d.trackNote) {
      html += '<p class="tf-note tf-note-warn"><strong>路径不确定性：</strong>' + esc(d.trackNote) + '</p>';
    }
    box.innerHTML = html;

    bindTrackInteractions(d);
  }

  /* ============ 交互：时间轴 + 悬停 ============ */
  function bindTrackInteractions(d) {
    var track = d.track || [];
    var range = document.getElementById('tfRange');
    var stepBox = document.getElementById('tfStep');
    var rangeT = document.getElementById('tfRangeT');
    var playBtn = document.getElementById('tfPlay');
    var playIco = document.getElementById('tfPlayIco');
    var playTxt = document.getElementById('tfPlayTxt');
    var svg = document.querySelector('#tf-track .tf-track-svg');
    if (!range || !stepBox || !svg) return;

    var timer = null;

    function showStep(i) {
      var p = track[i];
      if (!p) return;
      var dist = haversine(SHEYANG.lat, SHEYANG.lon, p.lat, p.lon);
      var badge = p.forecast
        ? '<span class="tf-step-badge fc">预报</span>'
        : (p.landfall ? '<span class="tf-step-badge land">登陆</span>' : '<span class="tf-step-badge obs">实况</span>');
      stepBox.innerHTML =
        '<div class="tf-step-head">' + badge + '<strong>' + esc(p.t) + '</strong>' +
        '<span class="tf-step-dist">距射阳 ' + dist + ' km</span></div>' +
        '<div class="tf-step-body">' +
        '<span><i>位置</i>' + n(p.lat) + '°N, ' + n(p.lon) + '°E</span>' +
        '<span><i>强度</i>' + esc(p.intensity || '—') + '</span>' +
        '<span><i>气压</i>' + esc(p.pressure || '—') + '</span>' +
        '</div>' +
        '<div class="tf-step-desc">' + esc(p.desc || '') + '</div>';
      if (rangeT) rangeT.textContent = p.t;

      /* 高亮当前点 */
      var pts = svg.querySelectorAll('.tf-pt');
      Array.prototype.forEach.call(pts, function (el) {
        el.classList.toggle('on', parseInt(el.getAttribute('data-i'), 10) === i);
      });
    }

    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
      if (playIco) playIco.textContent = '▶';
      if (playTxt) playTxt.textContent = '播放路径';
      if (playBtn) playBtn.classList.remove('playing');
    }

    function play() {
      if (timer) { stop(); return; }
      var i = parseInt(range.value, 10);
      if (i >= track.length - 1) i = -1;
      if (playIco) playIco.textContent = '❚❚';
      if (playTxt) playTxt.textContent = '暂停';
      if (playBtn) playBtn.classList.add('playing');
      timer = setInterval(function () {
        i++;
        if (i >= track.length) { stop(); return; }
        range.value = i;
        showStep(i);
      }, 900);
    }

    range.addEventListener('input', function () { stop(); showStep(parseInt(range.value, 10)); });
    if (playBtn) playBtn.addEventListener('click', play);

    /* 路径点悬停/点击 */
    var tip = document.getElementById('tfTip');
    Array.prototype.forEach.call(svg.querySelectorAll('.tf-pt'), function (el) {
      var i = parseInt(el.getAttribute('data-i'), 10);
      el.style.cursor = 'pointer';
      el.addEventListener('mouseenter', function () {
        var p = track[i];
        if (!p || !tip) return;
        tip.innerHTML = '<b>' + esc(p.t) + '</b>' + esc(p.intensity || '') +
          '<br>' + esc(p.desc || '');
        tip.classList.add('show');
        var box = svg.getBoundingClientRect();
        var pr = el.getBoundingClientRect();
        tip.style.left = ((pr.left + pr.width / 2 - box.left) / box.width * 100) + '%';
        tip.style.top = ((pr.top - box.top) / box.height * 100) + '%';
      });
      el.addEventListener('mouseleave', function () { if (tip) tip.classList.remove('show'); });
      el.addEventListener('click', function () { stop(); range.value = i; showStep(i); });
    });

    /* 初始定位到"当前"点 */
    var curIdx = track.length - 1;
    for (var k = 0; k < track.length; k++) { if (track[k].current) { curIdx = k; break; } }
    range.value = curIdx;
    showStep(curIdx);
  }

  /* ============ 渲染：当前状态 ============ */
  function renderStatus(d) {
    var box = document.getElementById('tf-status');
    if (!box) return;
    var c = d.current || {};
    var dist = (c.lat != null) ? haversine(SHEYANG.lat, SHEYANG.lon, c.lat, c.lon) : null;

    var h = '';
    h += '<div class="tf-hero-card">';
    h += '<div class="tf-hero-main">';
    h += '<div class="tf-hero-name"><span class="tf-spin">🌀</span><b>' + esc(d.name) + '</b>' +
      '<span class="tf-hero-no">' + esc(d.year) + ' 年第 ' + esc(d.no) + ' 号台风 · ' + esc(d.nameEn) + '</span></div>';
    h += '<div class="tf-hero-status ' + esc(d.statusLevel || 'warn') + '">' + esc(d.status) + '</div>';
    if (d.headline) h += '<div class="tf-hero-headline">' + esc(d.headline) + '</div>';
    h += '</div>';
    if (dist != null) {
      h += '<div class="tf-hero-dist"><span class="tf-dist-num">' + dist + '</span>' +
        '<span class="tf-dist-unit">km</span><span class="tf-dist-label">距射阳直线距离</span></div>';
    }
    h += '</div>';

    var cells = [
      ['当前位置', c.location || '—', 'pin'],
      ['中心强度', c.intensity || '—', 'wind'],
      ['中心气压', c.pressure || '—', 'gauge'],
      ['移动方向', c.move || '—', 'arrow'],
      ['坐标', (c.lat != null ? n(c.lat) + '°N, ' + n(c.lon) + '°E' : '—'), 'globe'],
      ['后续趋势', c.trend || '—', 'clock']
    ];
    h += '<div class="tf-status-grid">';
    cells.forEach(function (it) {
      h += '<div class="tf-cell"><span class="tf-cell-k">' + it[0] + '</span>' +
        '<span class="tf-cell-v">' + esc(it[1]) + '</span></div>';
    });
    h += '</div>';

    if (d.summary) h += '<p class="tf-summary">' + esc(d.summary) + '</p>';
    box.innerHTML = h;
  }

  /* ============ 渲染：射阳影响 ============ */
  function renderSheyang(d) {
    var box = document.getElementById('tf-sheyang');
    if (!box) return;
    var sy = d.sheyang || {};
    var h = '';

    /* 风险总判 */
    h += '<div class="tf-verdict">' +
      '<div class="tf-verdict-badge">' + esc(sy.riskLevel || '—') + '</div>' +
      '<div class="tf-verdict-body"><b>' + esc(sy.riskLabel || '') + '</b>' +
      '<p>' + esc(sy.riskNote || '') + '</p></div></div>';

    /* 预警徽章 */
    if (sy.alerts && sy.alerts.length) {
      h += '<div class="tf-alerts">';
      sy.alerts.forEach(function (a) {
        if (typeof a === 'string') { h += '<span class="tf-alert blue">' + esc(a) + '</span>'; return; }
        h += '<span class="tf-alert ' + esc(a.color || 'blue') + '">' +
          '<b>' + esc(a.name) + '</b>' +
          (a.level ? '<i>' + esc(a.level) + '</i>' : '') +
          '<em>' + esc(a.issuer || '') + (a.time ? ' · ' + esc(a.time) : '') + '</em></span>';
      });
      h += '</div>';
    }

    /* 关键指标 */
    h += '<div class="tf-key">';
    if (sy.period) h += '<div class="tf-key-item"><span>影响时段</span><b>' + esc(sy.period) + '</b></div>';
    if (sy.peakWindow) h += '<div class="tf-key-item"><span>最强时段</span><b>' + esc(sy.peakWindow) + '</b></div>';
    if (sy.wind) h += '<div class="tf-key-item"><span>风力</span><b>' + esc(sy.wind) + '</b></div>';
    if (sy.rain) h += '<div class="tf-key-item"><span>降雨</span><b>' + esc(sy.rain) + '</b></div>';
    h += '</div>';

    /* 分日风力条形图 */
    if (sy.windDaily && sy.windDaily.length) {
      h += '<div class="tf-wind-chart"><div class="tf-chart-title">分日风力预报（江苏省气象台）</div>';
      sy.windDaily.forEach(function (w) {
        var seaPct = Math.min(100, (w.seaScale || 0) / 12 * 100);
        var landPct = Math.min(100, (w.landScale || 0) / 12 * 100);
        h += '<div class="tf-wrow' + (w.peak ? ' peak' : '') + '">' +
          '<span class="tf-wdate">' + esc(w.date) + (w.peak ? ' <i>峰值</i>' : '') + '</span>' +
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

    /* 实况 */
    if (sy.observed) {
      h += '<div class="tf-observed"><span class="tf-obs-k">本地实况</span><p>' + esc(sy.observed) + '</p></div>';
    }

    /* 风险清单 */
    if (sy.risk && sy.risk.length) {
      h += '<div class="tf-risk-grid">';
      sy.risk.forEach(function (r) {
        if (typeof r === 'string') { h += '<div class="tf-risk-card mid"><p>' + esc(r) + '</p></div>'; return; }
        h += '<div class="tf-risk-card ' + esc(r.level || 'mid') + '">' +
          '<b>' + esc(r.title) + '</b><p>' + esc(r.text) + '</p></div>';
      });
      h += '</div>';
    }

    /* 时间线 */
    if (sy.timeline && sy.timeline.length) {
      h += '<div class="tf-timeline">';
      sy.timeline.forEach(function (t) {
        h += '<div class="tf-tl-item ' + esc(t.state || 'future') + '">' +
          '<span class="tf-tl-dot"></span>' +
          '<span class="tf-tl-date">' + esc(t.date) + '</span>' +
          '<span class="tf-tl-text">' + esc(t.text) + '</span></div>';
      });
      h += '</div>';
    }

    box.innerHTML = h;
  }

  /* ============ 渲染：防范措施 ============ */
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
    var fallbackTitle = { home: '居家', outdoor: '外出', drive: '驾车', farm: '农渔' };
    var fallbackIcon = { home: 'home', outdoor: 'walk', drive: 'car', farm: 'leaf' };
    var h = '<div class="tf-prev-grid">';
    order.forEach(function (k) {
      var g = p[k];
      if (!g) return;
      var items = Array.isArray(g) ? g : (g.items || []);
      var title = (g && g.title) || fallbackTitle[k];
      var ico = ICONS[(g && g.icon) || fallbackIcon[k]] || ICONS.home;
      if (!items.length) return;
      h += '<div class="tf-prev-card">' +
        '<div class="tf-prev-head"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + ico + '</svg>' +
        '<h3>' + esc(title) + '</h3></div><ul class="tf-prev-list">';
      items.forEach(function (t) { h += '<li>' + esc(t) + '</li>'; });
      h += '</ul></div>';
    });
    h += '</div>';
    box.innerHTML = h;
  }

  /* ============ 渲染：实时动态 ============ */
  function renderFeed(d) {
    var box = document.getElementById('autoNewsBody');
    if (!box) return;
    var list = d.feed || [];
    if (!list.length) { box.innerHTML = '<p class="tf-empty">暂无动态</p>'; return; }
    var h = '';
    list.forEach(function (it) {
      var tags = '';
      (it.tags || []).forEach(function (t) {
        if (typeof t === 'string') tags += '<span class="news-tag">' + esc(t) + '</span>';
        else tags += '<span class="news-tag ' + esc(t.class || '') + '">' + esc(t.text) + '</span>';
      });
      h += '<div class="news-item">' +
        '<div class="news-meta"><span class="news-date">' + esc(it.date) + '</span>' + tags + '</div>' +
        '<div class="news-content">' + esc(it.content) + '</div>' +
        (it.source ? '<div class="tf-src">来源：' + esc(it.source) + '</div>' : '') +
        '</div>';
    });
    box.innerHTML = h;
    var cnt = document.getElementById('autoNewsCount');
    if (cnt) cnt.textContent = list.length;
    var sec = document.getElementById('hc-auto-news');
    if (sec) sec.style.display = '';
  }

  /* ============ 渲染：来源与免责 ============ */
  function renderSources(d) {
    var box = document.getElementById('tf-sources');
    if (!box) return;
    var h = '';
    if (d.sources && d.sources.length) {
      h += '<div class="tf-src-list"><span>权威数据源：</span>';
      d.sources.forEach(function (s) {
        h += '<a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.name) + '</a>';
      });
      h += '</div>';
    }
    if (d.disclaimer) h += '<p class="tf-disclaimer">' + esc(d.disclaimer) + '</p>';
    box.innerHTML = h;
  }

  /* ============ 更新时间 ============ */
  function renderUpdated(d) {
    var el = document.getElementById('lastNewsUpdate');
    if (!el || !d.updated) return;
    var dt = new Date(d.updated);
    if (isNaN(dt.getTime())) { el.textContent = d.updated; return; }
    var pad = function (v) { return v < 10 ? '0' + v : '' + v; };
    el.textContent = dt.getFullYear() + '-' + pad(dt.getMonth() + 1) + '-' + pad(dt.getDate()) +
      ' ' + pad(dt.getHours()) + ':' + pad(dt.getMinutes());
  }

  /* ============ 启动 ============ */
  function init() {
    fetch('typhoon.json?v=' + Date.now())
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (d) {
        renderUpdated(d);
        renderStatus(d);
        renderTrack(d);
        renderSheyang(d);
        renderPrevention(d);
        renderFeed(d);
        renderSources(d);
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
