/**
 * 台风实时监测加载器
 * 读取 typhoon.json，渲染：当前状态卡 / 走向示意图(SVG) / 对射阳影响 / 防范措施 / 实时动态
 * 数据聚焦江苏省盐城市射阳县。
 */
(function () {
  var LON_MIN = 118, LON_MAX = 126, LAT_MIN = 24, LAT_MAX = 35;
  var VB_W = 640, VB_H = 480, PAD = 46;
  var PLOT_W = VB_W - PAD * 2, PLOT_H = VB_H - PAD * 2;
  var SHEYANG = { lat: 33.6, lon: 120.3, name: '射阳' };

  function lon2x(lon) { return PAD + (lon - LON_MIN) / (LON_MAX - LON_MIN) * PLOT_W; }
  function lat2y(lat) { return PAD + (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * PLOT_H; }

  // 中国东海岸简化轮廓（lat,lon，自南向北）
  var COAST = [
    [26.5, 119.5], [27.5, 121.0], [28.1, 121.3], [29.0, 121.8],
    [30.5, 121.8], [31.5, 121.9], [32.5, 120.8], [33.6, 120.3],
    [34.5, 119.8], [35.2, 119.2]
  ];

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function buildTrackSVG(track) {
    var i, p, x, y;
    var parts = [];
    // 海洋底色
    parts.push('<rect x="0" y="0" width="' + VB_W + '" height="' + VB_H + '" fill="#0d2233"/>');
    // 经纬网格
    for (i = 0; i <= 4; i++) {
      var gx = PAD + i * PLOT_W / 4;
      parts.push('<line x1="' + gx + '" y1="' + PAD + '" x2="' + gx + '" y2="' + (VB_H - PAD) + '" stroke="rgba(255,255,255,.06)" stroke-width="1"/>');
    }
    for (i = 0; i <= 4; i++) {
      var gy = PAD + i * PLOT_H / 4;
      parts.push('<line x1="' + PAD + '" y1="' + gy + '" x2="' + (VB_W - PAD) + '" y2="' + gy + '" stroke="rgba(255,255,255,.06)" stroke-width="1"/>');
    }
    // 陆地（海岸线左侧填充）
    var land = 'M ' + (PAD - 20) + ' ' + (VB_H - PAD + 20);
    for (i = 0; i < COAST.length; i++) {
      land += ' L ' + lon2x(COAST[i][1]).toFixed(1) + ' ' + lat2y(COAST[i][0]).toFixed(1);
    }
    land += ' L ' + (PAD - 20) + ' ' + (PAD - 20) + ' Z';
    parts.push('<path d="' + land + '" fill="#13351f" stroke="rgba(120,200,140,.5)" stroke-width="2"/>');
    // 海岸线高亮
    var coast = '';
    for (i = 0; i < COAST.length; i++) {
      coast += (i === 0 ? 'M ' : ' L ') + lon2x(COAST[i][1]).toFixed(1) + ' ' + lat2y(COAST[i][0]).toFixed(1);
    }
    parts.push('<path d="' + coast + '" fill="none" stroke="rgba(160,220,170,.9)" stroke-width="2.5" stroke-linejoin="round"/>');

    // 台风路径（实线=已发生，虚线=预报）
    var obs = [], fc = [];
    for (i = 0; i < track.length; i++) {
      (track[i].forecast ? fc : obs).push(track[i]);
    }
    function poly(arr) {
      var d = '';
      for (var k = 0; k < arr.length; k++) {
        d += (k === 0 ? 'M ' : ' L ') + lon2x(arr[k].lon).toFixed(1) + ' ' + lat2y(arr[k].lat).toFixed(1);
      }
      return d;
    }
    if (obs.length > 1) parts.push('<path d="' + poly(obs) + '" fill="none" stroke="#ff8c00" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>');
    if (fc.length) {
      var fcStart = obs.length ? obs[obs.length - 1] : fc[0];
      var fcPath = 'M ' + lon2x(fcStart.lon).toFixed(1) + ' ' + lat2y(fcStart.lat).toFixed(1);
      for (i = 0; i < fc.length; i++) fcPath += ' L ' + lon2x(fc[i].lon).toFixed(1) + ' ' + lat2y(fc[i].lat).toFixed(1);
      parts.push('<path d="' + fcPath + '" fill="none" stroke="#4da6e8" stroke-width="3" stroke-dasharray="7 6" stroke-linecap="round"/>');
    }
    // 站点标记
    for (i = 0; i < track.length; i++) {
      p = track[i]; x = lon2x(p.lon); y = lat2y(p.lat);
      var fill = p.forecast ? '#4da6e8' : (i === track.length - 1 - fc.length || i === 3 ? '#e81123' : '#ffb900');
      var r = p.forecast ? 4 : 5.5;
      parts.push('<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="' + r + '" fill="' + fill + '" stroke="#fff" stroke-width="1.2"/>');
      var lx = x + 8, ly = y - 8;
      if (lx > VB_W - 90) lx = x - 78;
      parts.push('<text x="' + lx.toFixed(1) + '" y="' + ly.toFixed(1) + '" fill="rgba(255,255,255,.85)" font-size="11">' + esc(p.t) + '</text>');
    }
    // 当前位置台风符号
    var cur = obs.length ? obs[obs.length - 1] : track[0];
    parts.push('<text x="' + lon2x(cur.lon).toFixed(1) + '" y="' + (lat2y(cur.lat) + 26).toFixed(1) + '" text-anchor="middle" font-size="20">🌀</text>');

    // 射阳标记（红圈 + 标签）
    var sx = lon2x(SHEYANG.lon), sy = lat2y(SHEYANG.lat);
    parts.push('<circle cx="' + sx.toFixed(1) + '" cy="' + sy.toFixed(1) + '" r="8" fill="#e81123" stroke="#fff" stroke-width="1.5"/>');
    parts.push('<circle cx="' + sx.toFixed(1) + '" cy="' + sy.toFixed(1) + '" r="13" fill="none" stroke="#e81123" stroke-width="1.2" stroke-opacity="0.7"/>');
    parts.push('<text x="' + sx + '" y="' + (sy - 18).toFixed(1) + '" text-anchor="middle" fill="#ff5a5a" font-size="12" font-weight="700">射阳</text>');

    // 图例
    parts.push('<g transform="translate(' + (PAD) + ',' + (VB_H - 26) + ')">');
    parts.push('<line x1="0" y1="0" x2="22" y2="0" stroke="#ff8c00" stroke-width="3.5"/><text x="28" y="4" fill="rgba(255,255,255,.8)" font-size="11">已发生路径</text>');
    parts.push('<line x1="120" y1="0" x2="142" y2="0" stroke="#4da6e8" stroke-width="3" stroke-dasharray="7 6"/><text x="148" y="4" fill="rgba(255,255,255,.8)" font-size="11">预报路径</text>');
    parts.push('<circle cx="252" cy="0" r="5" fill="#e81123"/><text x="262" y="4" fill="rgba(255,255,255,.8)" font-size="11">射阳（重点关注）</text>');
    parts.push('</g>');

    return '<svg viewBox="0 0 ' + VB_W + ' ' + VB_H + '" class="tf-track-svg" role="img" aria-label="台风白海豚走向示意图">' + parts.join('') + '</svg>';
  }

  function renderStatus(d) {
    var el = document.getElementById('tf-status');
    if (!el) return;
    var c = d.current || {};
    el.innerHTML =
      '<div class="tf-badge">🌀 今年第' + d.no + '号台风</div>' +
      '<h2 class="tf-name">' + esc(d.name) + ' <span class="tf-en">' + esc(d.nameEn) + '</span></h2>' +
      '<div class="tf-status-line">' + esc(d.status) + '</div>' +
      '<div class="tf-grid">' +
        '<div class="tf-cell"><span>当前中心</span><b>' + esc(c.location || '—') + '</b></div>' +
        '<div class="tf-cell"><span>最大风力</span><b>' + esc(c.intensity || '—') + '</b></div>' +
        '<div class="tf-cell"><span>中心气压</span><b>' + esc(c.pressure || '—') + '</b></div>' +
        '<div class="tf-cell"><span>移动方向</span><b>' + esc(c.move || '—') + '</b></div>' +
      '</div>';
  }

  function renderSheyang(d) {
    var el = document.getElementById('tf-sheyang');
    if (!el || !d.sheyang) return;
    var s = d.sheyang;
    var alerts = (s.alerts || []).map(function (a) { return '<span class="tf-chip tf-chip-warn">' + esc(a) + '</span>'; }).join('');
    var risks = (s.risk || []).map(function (r) { return '<li>' + esc(r) + '</li>'; }).join('');
    var tl = (s.timeline || []).map(function (t) {
      return '<div class="tf-tl-item"><div class="tf-tl-date">' + esc(t.date) + '</div><div class="tf-tl-text">' + esc(t.text) + '</div></div>';
    }).join('');
    el.innerHTML =
      '<div class="tf-chips">' + alerts + '</div>' +
      '<div class="tf-impact-grid">' +
        '<div class="tf-impact-card"><h4>影响时段</h4><p>' + esc(s.period) + '</p></div>' +
        '<div class="tf-impact-card"><h4>风力</h4><p>' + esc(s.wind) + '</p></div>' +
        '<div class="tf-impact-card"><h4>降雨</h4><p>' + esc(s.rain) + '</p></div>' +
        '<div class="tf-impact-card"><h4>实况（截至最新）</h4><p>' + esc(s.observed) + '</p></div>' +
      '</div>' +
      '<h4 class="tf-sub">主要风险</h4><ul class="tf-risk-list">' + risks + '</ul>' +
      '<h4 class="tf-sub">未来影响时间线</h4><div class="tf-timeline">' + tl + '</div>';
  }

  function renderPrevention(d) {
    var el = document.getElementById('tf-prevention');
    if (!el || !d.prevention) return;
    var p = d.prevention;
    var groups = [
      { key: 'home', title: '居家防范', icon: '🏠' },
      { key: 'outdoor', title: '户外出行', icon: '🚶' },
      { key: 'drive', title: '驾车注意', icon: '🚗' },
      { key: 'farm', title: '农渔生产', icon: '🌾' }
    ];
    var html = '';
    groups.forEach(function (g) {
      var items = (p[g.key] || []).map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('');
      html += '<div class="tf-prev-card">' +
        '<div class="tf-prev-head">' + g.icon + ' ' + esc(g.title) + '</div>' +
        '<ul class="tf-prev-list">' + items + '</ul></div>';
    });
    el.innerHTML = html;
  }

  function renderFeed(d) {
    var el = document.getElementById('autoNewsBody');
    if (!el || !d.feed || !d.feed.length) return;
    var html = '';
    d.feed.forEach(function (item) {
      var tagHtml = '';
      (item.tags || []).forEach(function (t) {
        tagHtml += '<span class="news-tag ' + (t.class || 'default') + '">' + esc(t.text) + '</span>';
      });
      var link = item.url
        ? '<a href="' + esc(item.url) + '" target="_blank" rel="noopener" style="font-size:0.78rem;margin-left:6px;">🔗原文</a>'
        : '';
      var src = item.source ? '<span class="tf-src">来源：' + esc(item.source) + '</span>' : '';
      html += '<div class="news-item">' +
        '<div class="news-date">' + esc(item.date) + '</div>' +
        '<div class="news-content">' + tagHtml +
        '<p>' + esc(item.content) + ' ' + link + ' ' + src + '</p>' +
        '</div></div>';
    });
    el.innerHTML = html;
    var wrap = document.getElementById('hc-auto-news');
    if (wrap) { wrap.style.display = 'grid'; wrap.classList.add('open'); }
    var cnt = document.getElementById('autoNewsCount');
    if (cnt) cnt.textContent = d.feed.length + '条';
  }

  function load() {
    fetch('typhoon.json?v=' + Date.now())
      .then(function (r) { if (!r.ok) throw new Error('not found'); return r.json(); })
      .then(function (d) {
        var upd = document.getElementById('lastNewsUpdate');
        if (upd && d.updated) upd.textContent = d.updated;
        var trackEl = document.getElementById('tf-track');
        if (trackEl && d.track) trackEl.innerHTML = buildTrackSVG(d.track);
        renderStatus(d);
        renderSheyang(d);
        renderPrevention(d);
        renderFeed(d);
      })
      .catch(function (e) { console.log('[typhoon] 加载失败:', e); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
