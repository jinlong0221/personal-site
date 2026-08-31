/*!
 * ev-charge.js — 新能源充电桩实时查询（高德地图 POI 驱动）
 * 龙兄知识库 · longxiong.vip
 *
 * 设计要点：
 * 1. 定位：高德 AMap.Geolocation 优先，浏览器原生 navigator.geolocation 兜底，再降级到手动输入。
 * 2. 检索：高德 PlaceSearch 周边搜索，多关键词并集去重（提高召回，尽量"全"）。
 * 3. 价格：三层策略——本站核实库命中直显 / 未命中明写"以现场为准" / 一键跳转查实时价。绝不编造数字。
 * 4. 无 Key 时：降级到内置射阳本地数据，页面仍有内容可用。
 */
(function () {
  'use strict';

  /* ============================================================
   * 【配置】高德地图 Key —— 未配置时页面自动降级
   * 申请地址 https://console.amap.com/dev/key/app
   * 服务平台选「Web端(JS API)」，不要选「Web服务 API」
   * ============================================================ */
  var AMAP_KEY = '';          // ← 填入 Web端(JS API) 的 Key
  var AMAP_SECURITY = '';     // ← 填入安全密钥 securityJsCode（2021-12-02 后申请的 Key 必填）

  /* ---------- 本站核实过的价格库（有据可查才写进来，绝不编造） ---------- */
  // match: 站名需包含的关键词（全部命中才算）；region: 仅在定位到该地区时启用，避免全国同名站误匹配
  var VERIFIED_PRICES = [
    { kw: ['吾悦广场'], region: '射阳县', price: 1.11, op: '国家电网', note: '停车费参照停车场标准', src: '无敌电动网', date: '2026-08' },
    { kw: ['千鹤湖'], region: '射阳县', price: 1.14, op: '特来电', note: '停车免费', src: '无敌电动网', date: '2026-08' },
    { kw: ['新城实验幼儿园'], region: '射阳县', price: 1.14, op: '特来电', note: '停车免费', src: '无敌电动网', date: '2026-08' },
    { kw: ['晨光路'], region: '射阳县', price: 1.20, op: '国家电网', note: '停车费参照停车场标准', src: '无敌电动网', date: '2026-08' },
    { kw: ['黄海路'], region: '射阳县', price: 1.20, op: '国家电网', note: '停车费参照停车场标准', src: '无敌电动网', date: '2026-08' },
    { kw: ['合德供电所'], region: '射阳县', price: 1.20, op: '国家电网', note: '停车免费', src: '无敌电动网', date: '2026-08' },
    { kw: ['潇洋'], region: '射阳县', price: 1.62, op: '特来电', note: '停车免费', src: '无敌电动网', date: '2026-08' }
  ];

  /* ---------- 无 Key 时的兜底数据（射阳县，来源：县政府《"十四五"电动汽车充电设施布局规划》表 2-3） ---------- */
  var FALLBACK_STATIONS = [
    { name: '滨湖大道充电站（万帮充电）', addr: '射阳县滨湖大道9号', op: '万帮充电', n: '6台快充', kw: 720, kind: '公用' },
    { name: '机场路罾塘居委会充电站（万帮充电）', addr: '射阳县机场路罾塘居委会', op: '万帮充电', n: '5台快充', kw: 600, kind: '公用' },
    { name: '海河镇高铁站北充电站', addr: '射阳县海河镇高铁站北边', op: '国家电网', n: '9台快充', kw: 960, kind: '公用' },
    { name: '海河镇高铁站南充电站', addr: '射阳县海河镇高铁站南边', op: '国家电网', n: '4台快充', kw: 480, kind: '公用' },
    { name: '汽车客运站充电站', addr: '射阳县汽车客运站', op: '国家电网', n: '5台快充', kw: 480, kind: '公用' },
    { name: 'S226省道三维公交公司充电站', addr: '射阳县S226省道三维公交公司', op: '国家电网', n: '10台快充', kw: 2400, kind: '内部' },
    { name: '晨光路停车场充电站', addr: '射阳县晨光路', op: '国家电网', n: '6条快充', kw: 720, kind: '公用' },
    { name: '黄海路停车场公共充电站', addr: '射阳县黄海路', op: '国家电网', n: '4台快充', kw: 480, kind: '公用' },
    { name: '合德供电所充电点', addr: '解放东路中联公寓东侧合德供电所', op: '国家电网', n: '2快2慢', kw: 134, kind: '公用' },
    { name: '经济开发区管委会充电站', addr: '幸福大道经济开发区管委会', op: '国家电网', n: '8台快充', kw: 480, kind: '公用' },
    { name: '兴桥供电所充电点', addr: '兴桥镇冈合路兴桥供电所', op: '国家电网', n: '2快2慢', kw: 134, kind: '公用' },
    { name: '沈海高速射阳服务区充电站（沈阳方向）', addr: '沈海高速射阳服务区', op: '国家电网', n: '4台快充', kw: 240, kind: '公用·高速' },
    { name: '沈海高速射阳服务区充电站（海口方向）', addr: '沈海高速射阳服务区', op: '国家电网', n: '4台快充', kw: 240, kind: '公用·高速' },
    { name: '陈洋镇人民西路充电站', addr: '射阳县陈洋镇人民西路27#', op: '国家电网', n: '8台快充', kw: 480, kind: '公用' },
    { name: '西开发区枫西路充电站', addr: '射阳县西开发区枫西路2#', op: '国家电网', n: '14台快充', kw: 920, kind: '内部' },
    { name: '临海供电所停车场充电点', addr: '临海供电所停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' },
    { name: '河湾家园集中居住区充电点', addr: '河湾家园集中居住区停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' },
    { name: '四明镇通洋供电所充电点', addr: '四明镇通洋供电所停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' },
    { name: '海通供电所停车场充电点', addr: '海通供电所停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' },
    { name: '新潮集中居住区充电点', addr: '新潮集中居住区停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' },
    { name: '长荡政府文化宫充电点', addr: '长荡政府文化宫门口停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' },
    { name: '特庸供电所门口充电点', addr: '特庸供电所门口停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' },
    { name: '洋马政府西侧充电点', addr: '洋马政府西侧停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' },
    { name: '黄沙港政府大院充电点', addr: '黄沙港政府大院内停车场', op: '国家电网', n: '1快1慢', kw: 67, kind: '公用' }
  ];

  /* ---------- 运营商识别（从站名反推品牌） ---------- */
  var OP_RULES = [
    [/国家电网|国网|e充电/i, '国家电网'],
    [/特来电|TELD/i, '特来电'],
    [/星星充电|万城万充|万帮数字/i, '星星充电'],
    [/小桔|滴滴/i, '小桔充电'],
    [/蔚来|NIO/i, '蔚来'],
    [/特斯拉|Tesla/i, '特斯拉'],
    [/理想/i, '理想汽车'],
    [/小鹏|XPeng/i, '小鹏汽车'],
    [/比亚迪|BYD/i, '比亚迪'],
    [/极氪|ZEEKR/i, '极氪'],
    [/云快充/i, '云快充'],
    [/三维|悦充/i, '三维悦充'],
    [/石化易电|中石化|易捷/i, '石化易电'],
    [/中石油/i, '中石油'],
    [/开迈斯|CAMS/i, '开迈斯'],
    [/依威/i, '依威能源'],
    [/普诺得/i, '普诺得'],
    [/汇充电/i, '汇充电'],
    [/南方电网|南网/i, '南方电网'],
    [/万帮/i, '万帮充电'],
    [/华为|数字能源/i, '华为数字能源']
  ];

  function guessOp(name) {
    for (var i = 0; i < OP_RULES.length; i++) {
      if (OP_RULES[i][0].test(name)) return OP_RULES[i][1];
    }
    return '其他';
  }

  /* ---------- 工具 ---------- */
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmtDist(m) {
    m = Number(m);
    if (!isFinite(m)) return '';
    return m < 1000 ? Math.round(m) + ' m' : (m / 1000).toFixed(1) + ' km';
  }
  function haversine(a, b) {
    var R = 6371000, r = Math.PI / 180;
    var dLat = (b.lat - a.lat) * r, dLng = (b.lng - a.lng) * r;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  /* ---------- 状态 ---------- */
  var state = {
    center: null,        // {lng, lat}
    city: '',            // 定位到的城市名
    district: '',        // 区县名
    address: '',         // 详细地址
    stations: [],        // 全量站点
    radius: 3000,
    sort: 'dist',
    view: 'list',
    op: '',
    fallback: false,
    map: null,
    markers: [],
    amapReady: false
  };

  /* ============================================================
   * 高德 SDK 加载
   * ============================================================ */
  function loadAmap() {
    return new Promise(function (resolve, reject) {
      if (window.AMap) { resolve(window.AMap); return; }
      if (AMAP_SECURITY) window._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY };
      var s = document.createElement('script');
      s.src = 'https://webapi.amap.com/maps?v=2.0&key=' + encodeURIComponent(AMAP_KEY) + '&plugin=AMap.Geolocation,AMap.PlaceSearch,AMap.Geocoder';
      s.async = true;
      s.onload = function () { window.AMap ? resolve(window.AMap) : reject(new Error('AMap 未挂载')); };
      s.onerror = function () { reject(new Error('高德 SDK 加载失败')); };
      document.head.appendChild(s);
    });
  }

  function amapPlugin(names) {
    return new Promise(function (resolve, reject) {
      window.AMap.plugin(names, function () { resolve(); });
      setTimeout(function () { reject(new Error('插件超时')); }, 15000);
    });
  }

  /* ============================================================
   * 定位
   * ============================================================ */
  function locateByBrowser() {
    return new Promise(function (resolve, reject) {
      if (!navigator.geolocation) { reject(new Error('浏览器不支持定位')); return; }
      navigator.geolocation.getCurrentPosition(function (pos) {
        resolve({ lng: pos.coords.longitude, lat: pos.coords.latitude, acc: pos.coords.accuracy });
      }, function (e) {
        reject(new Error(e.code === 1 ? '你拒绝了定位授权' : '定位失败：' + (e.message || '')));
      }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
    });
  }

  function locateByAmap() {
    return new Promise(function (resolve, reject) {
      var geo = new window.AMap.Geolocation({
        enableHighAccuracy: true, timeout: 12000, maximumAge: 60000,
        convert: true, showButton: false, panToLocation: false, zoomToAccuracy: false
      });
      geo.getCurrentPosition(function (status, result) {
        if (status === 'complete') {
          resolve({ lng: result.position.lng, lat: result.position.lat, acc: result.accuracy, formatted: result.formattedAddress });
        } else {
          reject(new Error(typeof result === 'string' ? result : (result && result.info) || '定位失败'));
        }
      });
    });
  }

  function reverseGeocode(lng, lat) {
    return new Promise(function (resolve) {
      var gc = new window.AMap.Geocoder({ radius: 1000, extensions: 'all' });
      gc.getAddress([lng, lat], function (status, result) {
        if (status === 'complete' && result.regeocode) {
          var c = result.regeocode.addressComponent || {};
          resolve({
            address: result.regeocode.formattedAddress || '',
            city: c.city || c.province || '',
            district: c.district || ''
          });
        } else { resolve({ address: '', city: '', district: '' }); }
      });
    });
  }

  function geocodeAddress(text) {
    return new Promise(function (resolve, reject) {
      var gc = new window.AMap.Geocoder({ city: '全国' });
      gc.getLocation(text, function (status, result) {
        if (status === 'complete' && result.geocodes && result.geocodes.length) {
          var g = result.geocodes[0];
          var c = g.addressComponent || {};
          resolve({
            lng: g.location.lng, lat: g.location.lat,
            address: g.formattedAddress || text,
            city: c.city || c.province || '',
            district: c.district || ''
          });
        } else { reject(new Error('没找到这个地方，换个说法试试（如"射阳县吾悦广场"）')); }
      });
    });
  }

  async function doLocate(manualText) {
    var t = $('evLocTitle'), s = $('evLocSub');
    t.innerHTML = '<span class="ev-spinner"></span>正在获取位置…';
    s.textContent = '';
    hide($('evWarn'));

    try {
      var pos;
      if (manualText) {
        if (!AMAP_KEY) throw new Error('手动搜索需要配置地图 Key');
        pos = await geocodeAddress(manualText);
      } else if (AMAP_KEY) {
        try { pos = await locateByAmap(); }
        catch (e) { pos = await locateByBrowser(); }
        if (!pos.address) {
          var rg = await reverseGeocode(pos.lng, pos.lat);
          pos.address = rg.address; pos.city = rg.city; pos.district = rg.district;
        }
      } else {
        pos = await locateByBrowser();
        pos.address = ''; pos.city = ''; pos.district = '';
      }

      state.center = { lng: pos.lng, lat: pos.lat };
      state.address = pos.address || '';
      state.city = pos.city || '';
      state.district = pos.district || '';

      var where = state.district || state.city || (state.address || '已定位');
      t.textContent = '📍 ' + (state.address || (pos.lng.toFixed(5) + ', ' + pos.lat.toFixed(5)));
      s.textContent = '定位成功 · ' + where + (AMAP_KEY ? '' : '（未配置地图 Key，当前显示内置射阳数据）');
      s.className = 'ev-locate-sub ok';

      await search();
    } catch (e) {
      t.textContent = '⚠️ ' + (e && e.message ? e.message : '定位失败');
      s.textContent = '可在下方输入框手动输入地点，或点「重新定位」再试一次';
      s.className = 'ev-locate-sub';
      // 定位失败也要给内容：直接上兜底数据
      renderFallback();
    }
  }

  /* ============================================================
   * 搜索（多关键词并集，提高召回）
   * ============================================================ */
  var KEYWORDS = ['充电站', '充电桩', '电动汽车充电', '新能源充电'];

  function searchNear(kw, page) {
    return new Promise(function (resolve) {
      var ps = new window.AMap.PlaceSearch({
        pageSize: 50, pageIndex: page, extensions: 'all',
        city: state.city || '全国', citylimit: false, autoFitView: false
      });
      ps.searchNearBy(kw, [state.center.lng, state.center.lat], state.radius, function (status, result) {
        if (status === 'complete' && result.poiList && result.poiList.pois) {
          resolve({ list: result.poiList.pois, count: parseInt(result.poiList.count, 10) || 0 });
        } else { resolve({ list: [], count: 0 }); }
      });
    });
  }

  async function search() {
    if (!AMAP_KEY) { renderFallback(); return; }
    if (!state.center) return;

    $('evList').innerHTML = '<div class="ev-skel"></div><div class="ev-skel"></div><div class="ev-skel"></div>';
    hide($('evSummary'));

    var seen = {}, all = [];
    for (var i = 0; i < KEYWORDS.length; i++) {
      for (var p = 1; p <= 2; p++) {
        var r = await searchNear(KEYWORDS[i], p);
        r.list.forEach(function (poi) {
          if (!poi || seen[poi.id]) return;
          seen[poi.id] = 1;
          var loc = (poi.location || '').toString().split(',');
          if (loc.length !== 2) return;
          var lng = parseFloat(loc[0]), lat = parseFloat(loc[1]);
          if (!isFinite(lng) || !isFinite(lat)) return;
          var d = haversine({ lat: state.center.lat, lng: state.center.lng }, { lat: lat, lng: lng });
          if (d > state.radius * 1.05) return;   // 高德偶有超半径回传，滤掉
          var name = poi.name || '';
          var vp = matchVerified(name);
          all.push({
            id: poi.id, name: name, addr: poi.address || '',
            lng: lng, lat: lat, dist: d,
            op: vp ? vp.op : guessOp(name),
            tel: poi.tel || '',
            price: vp ? vp.price : null,
            priceNote: vp ? vp.note : '',
            priceSrc: vp ? vp.src : '',
            priceDate: vp ? vp.date : '',
            verified: !!vp
          });
        });
        if (r.list.length < 50) break;   // 这页没满，说明没更多了
      }
    }
    state.fallback = false;
    hide($('evWarn'));
    state.stations = all;
    buildOpBar();
    render();
  }

  /* ---------- 价格匹配：站名关键词 + 地区限定，避免全国同名误匹配 ---------- */
  function matchVerified(name) {
    if (!state.district && !state.city) return null;
    var here = state.district || '';
    var city = state.city || '';
    for (var i = 0; i < VERIFIED_PRICES.length; i++) {
      var v = VERIFIED_PRICES[i];
      // 地区门槛：本条价格只在对应地区生效
      var regionHit = (v.region === here) || (v.region === city) ||
        (here && v.region.indexOf(here) === 0) || (city && city.indexOf(v.region) === 0);
      if (!regionHit) continue;
      var allHit = v.kw.every(function (k) { return name.indexOf(k) !== -1; });
      if (allHit) return v;
    }
    return null;
  }

  /* ============================================================
   * 渲染
   * ============================================================ */
  function buildOpBar() {
    var bar = $('evOpBar');
    var counts = {};
    state.stations.forEach(function (s) { counts[s.op] = (counts[s.op] || 0) + 1; });
    var ops = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
    var html = '<span class="ev-bar-label">品牌</span><button type="button" class="ev-chip' +
      (state.op === '' ? ' on' : '') + '" data-op="">全部 ' + state.stations.length + '</button>';
    ops.forEach(function (o) {
      html += '<button type="button" class="ev-chip' + (state.op === o ? ' on' : '') +
        '" data-op="' + esc(o) + '">' + esc(o) + ' ' + counts[o] + '</button>';
    });
    bar.innerHTML = html;
  }

  function sorted() {
    var list = state.stations.filter(function (s) { return !state.op || s.op === state.op; });
    if (state.sort === 'dist') {
      list.sort(function (a, b) { return a.dist - b.dist; });
    } else if (state.sort === 'price') {
      // 有价的排前面（由低到高），无价的沉底仍按距离
      list.sort(function (a, b) {
        if (a.price != null && b.price != null) return a.price - b.price || a.dist - b.dist;
        if (a.price != null) return -1;
        if (b.price != null) return 1;
        return a.dist - b.dist;
      });
    } else {
      list.sort(function (a, b) {
        if (a.price != null && b.price != null) return b.price - a.price || a.dist - b.dist;
        if (a.price != null) return -1;
        if (b.price != null) return 1;
        return a.dist - b.dist;
      });
    }
    return list;
  }

  function navUri(s) {
    return 'https://uri.amap.com/navigation?to=' + s.lng + ',' + s.lat + ',' +
      encodeURIComponent(s.name) + '&mode=car&coordinate=gaode&callnative=1&src=longxiong';
  }
  function poiUri(s) {
    if (s.id) return 'https://uri.amap.com/poi?id=' + encodeURIComponent(s.id) + '&src=longxiong&callnative=1';
    return 'https://uri.amap.com/marker?position=' + s.lng + ',' + s.lat + '&name=' +
      encodeURIComponent(s.name) + '&coordinate=gaode&src=longxiong&callnative=1';
  }

  function cardHtml(s, i) {
    var priceHtml = s.price != null
      ? '<span class="ev-price">' + s.price.toFixed(2) + ' <span style="font-size:.75rem;font-weight:400">元/度</span></span>' +
        '<span class="ev-pill fast">本站核实</span>'
      : '<span class="ev-price none">价格以现场为准</span>';

    var meta = '<div class="ev-meta">' +
      (isFinite(s.dist) ? '<div><span class="k">距离</span> <span class="ev-dist">' + fmtDist(s.dist) + '</span></div>' : '') +
      (s.addr ? '<div><span class="k">地址</span> ' + esc(s.addr) + '</div>' : '') +
      (s.tel ? '<div><span class="k">电话</span> ' + esc(s.tel) + '</div>' : '') +
      (s.priceNote ? '<div><span class="k">备注</span> ' + esc(s.priceNote) +
        (s.priceDate ? '（' + esc(s.priceDate) + '采集）' : '') + '</div>' : '') +
      '</div>';

    return '<article class="ev-card">' +
      '<div class="ev-card-top"><div class="ev-rank">' + (i + 1) + '</div>' +
      '<div style="flex:1;min-width:0"><div class="ev-name">' + esc(s.name) + '</div>' +
      '<span class="ev-op">' + esc(s.op) + '</span></div></div>' +
      '<div style="margin:8px 0">' + priceHtml + '</div>' + meta +
      '<div class="ev-actions">' +
      '<a href="' + navUri(s) + '" target="_blank" rel="noopener">🧭 导航去这里</a>' +
      '<a href="' + poiUri(s) + '" target="_blank" rel="noopener">💰 查实时价</a>' +
      '</div></article>';
  }

  function render() {
    var list = sorted();
    var box = $('evList');

    var withPrice = list.filter(function (s) { return s.price != null; }).length;
    var sum = $('evSummary');
    sum.hidden = false;
    sum.innerHTML = '找到 <b>' + list.length + '</b> 个充电站' +
      (state.fallback ? '' : '（半径 ' + (state.radius / 1000) + ' km）') +
      (state.op ? ' · 品牌筛选：' + esc(state.op) : '') +
      ' · 其中 <b>' + withPrice + '</b> 个有本站核实价，其余点「查实时价」看当前真实价格。' +
      (state.sort !== 'dist' && withPrice === 0 ? '<br>⚠️ 当前范围内没有已核实价格的站点，已按距离排列。' : '');

    if (!list.length) {
      box.innerHTML = '<div class="ev-empty">这个范围内没找到充电站。<br>试试把半径调大，或换个地点搜。</div>';
    } else {
      box.innerHTML = list.map(cardHtml).join('');
    }
    renderMap(list);
  }

  /* ---------- 地图 ---------- */
  function renderMap(list) {
    var el = $('evMap');
    if (state.view !== 'map') { el.classList.remove('show'); return; }
    el.classList.add('show');
    if (!window.AMap) return;

    if (!state.map) {
      state.map = new window.AMap.Map(el, {
        zoom: 14,
        center: [state.center.lng, state.center.lat],
        mapStyle: currentStyle()
      });
    } else {
      state.map.setCenter([state.center.lng, state.center.lat]);
      state.map.setMapStyle(currentStyle());
    }
    state.map.clearMap();
    state.markers = [];

    list.forEach(function (s, i) {
      var mk = new window.AMap.Marker({
        position: [s.lng, s.lat],
        title: s.name,
        label: { content: (i + 1) + '', direction: 'top' },
        offset: new window.AMap.Pixel(-10, -30)
      });
      mk.on('click', function () {
        new window.AMap.InfoWindow({
          content: '<div style="padding:8px 10px;font-size:13px;line-height:1.7;max-width:240px">' +
            '<b>' + esc(s.name) + '</b><br>' + esc(s.op) + ' · ' + fmtDist(s.dist) + '<br>' +
            (s.price != null ? '<b style="color:#c9a84c">' + s.price.toFixed(2) + ' 元/度</b>' : '价格以现场为准') +
            '<br><a href="' + navUri(s) + '" target="_blank" rel="noopener">导航去这里</a>' +
            '</div>',
          offset: new window.AMap.Pixel(0, -32)
        }).open(state.map, [s.lng, s.lat]);
      });
      state.map.add(mk);
      state.markers.push(mk);
    });
  }

  function currentStyle() {
    var dark = document.documentElement.getAttribute('data-theme') !== 'light';
    return dark ? 'amap://styles/dark' : 'amap://styles/normal';
  }

  /* ---------- 无 Key / 定位失败兜底 ---------- */
  function renderFallback() {
    state.fallback = true;
    var warn = $('evWarn');
    warn.hidden = false;
    warn.innerHTML = AMAP_KEY
      ? '⚠️ 定位没成功，下面先显示<b>射阳县</b>的已知充电站（来源：县政府《"十四五"电动汽车充电设施布局规划》）。手动输入地点可查别处。'
      : '⚠️ 本页的实时定位检索需要地图服务授权，眼下未启用，下面先显示<b>射阳县</b>的已知充电站（来源：县政府《"十四五"电动汽车充电设施布局规划》表 2-3）。这些站点没有在线坐标，故按列表呈现、不做距离和地图。';

    if (!AMAP_KEY) {
      $('evLocTitle').textContent = '📋 当前为内置数据模式';
      $('evLocSub').textContent = '实时定位检索需配置地图服务授权，启用后可查全国任意地点';
      $('evLocSub').className = 'ev-locate-sub';
    }

    state.stations = FALLBACK_STATIONS.map(function (s, i) {
      var vp = null;
      for (var j = 0; j < VERIFIED_PRICES.length; j++) {
        var v = VERIFIED_PRICES[j];
        if (v.kw.every(function (k) { return s.name.indexOf(k) !== -1; })) { vp = v; break; }
      }
      return {
        id: 'fb' + i, name: s.name, addr: s.addr, lng: null, lat: null, dist: Infinity,
        op: s.op, tel: '',
        price: vp ? vp.price : null,
        priceNote: [s.n, (s.kw ? s.kw + ' kW' : ''), s.kind, (vp ? vp.note : '')].filter(Boolean).join(' · '),
        priceSrc: vp ? vp.src : '', priceDate: vp ? vp.date : '', verified: !!vp
      };
    });
    buildOpBar();
    render();
  }

  function hide(el) { if (el) el.hidden = true; }

  /* ============================================================
   * 事件绑定
   * ============================================================ */
  function bind() {
    $('evRelocate').addEventListener('click', function () { doLocate(); });

    $('evAddrGo').addEventListener('click', function () {
      var v = $('evAddrInput').value.trim();
      if (v) doLocate(v);
    });
    $('evAddrInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { var v = this.value.trim(); if (v) doLocate(v); }
    });

    document.addEventListener('click', function (e) {
      var chip = e.target.closest ? e.target.closest('.ev-chip') : null;
      if (!chip) return;

      if (chip.hasAttribute('data-radius')) {
        state.radius = parseInt(chip.getAttribute('data-radius'), 10);
        setOn(chip.parentNode, chip, 'data-radius');
        if (state.center && AMAP_KEY) search();
        return;
      }
      if (chip.hasAttribute('data-sort')) {
        state.sort = chip.getAttribute('data-sort');
        setOn(chip.parentNode, chip, 'data-sort');
        render();
        return;
      }
      if (chip.hasAttribute('data-view')) {
        state.view = chip.getAttribute('data-view');
        setOn(chip.parentNode, chip, 'data-view');
        render();
        return;
      }
      if (chip.hasAttribute('data-op')) {
        state.op = chip.getAttribute('data-op');
        var bar = $('evOpBar');
        Array.prototype.forEach.call(bar.querySelectorAll('.ev-chip'), function (c) { c.classList.remove('on'); });
        chip.classList.add('on');
        render();
        return;
      }
    });

    // 主题切换后同步地图配色
    var tbtn = $('themeToggle');
    if (tbtn) tbtn.addEventListener('click', function () {
      setTimeout(function () { if (state.map && window.AMap) state.map.setMapStyle(currentStyle()); }, 60);
    });
  }

  function setOn(scope, chip, attr) {
    Array.prototype.forEach.call(scope.querySelectorAll('.ev-chip'), function (c) {
      if (c.hasAttribute(attr)) c.classList.remove('on');
    });
    chip.classList.add('on');
  }

  /* ============================================================
   * 启动
   * ============================================================ */
  function init() {
    bind();
    if (AMAP_KEY) {
      loadAmap().then(function () {
        state.amapReady = true;
        return amapPlugin(['AMap.Geolocation', 'AMap.PlaceSearch', 'AMap.Geocoder']);
      }).then(function () {
        doLocate();
      }).catch(function (e) {
        var t = $('evLocTitle');
        t.textContent = '⚠️ 地图服务加载失败：' + (e && e.message ? e.message : '未知错误');
        $('evLocSub').textContent = '已切换为内置的射阳县充电站数据';
        renderFallback();
      });
    } else {
      renderFallback();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();
