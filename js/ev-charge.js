/*!
 * ev-charge.js — 新能源充电桩实时查询（高德 / 腾讯 双通道）
 * 龙兄知识库 · longxiong.vip
 *
 * 设计要点：
 * 1. 双通道：顶部填了哪家地图的 Key 就走哪家，两家都不填则降级到内置射阳数据。
 *    两家服务被抽象成同一套接口（适配器），下面的排序、筛选、渲染逻辑完全不关心用哪家。
 * 2. 定位：地图 SDK 定位优先 → 浏览器原生定位（WGS84 自动纠偏到 GCJ02）→ IP 粗略定位 → 手动输入地址。
 * 3. 检索：多关键词并集去重，尽量"全"。
 * 4. 价格：三层策略——本站核实库命中直显 / 未命中明写"以现场为准" / 一键跳转查实时价。绝不编造数字。
 * 5. 坐标：浏览器定位给的是 WGS84，国内地图用的是 GCJ02，不转换会偏 300~800 米，这里统一纠偏。
 */
(function () {
  'use strict';

  /* ============================================================
   * 【配置】地图服务 Key —— 两家都不填时页面自动降级到内置数据
   * 高德  https://console.amap.com/dev/key/app   （服务平台选「Web端(JS API)」）
   * 腾讯  https://lbs.qq.com/dev/console/application/mine （勾选 WebServiceAPI + JavaScript API GL）
   * ============================================================ */
  var AMAP_KEY = '8107d0f2327ecb922be1ff939336368f';   // 高德 Web端(JS API) Key
  var AMAP_SECURITY = '5fe18e3185a7c796ff9511894245b662'; // 高德安全密钥 securityJsCode
  var TENCENT_KEY = '';              // 腾讯位置服务 Key
  var TENCENT_REFERER = 'longxiong'; // 腾讯控制台里的「应用名称」（是应用名，不是域名）

  /* 优先高德；高德没配则用腾讯；都没配则降级 */
  var PROVIDER = AMAP_KEY ? 'amap' : (TENCENT_KEY ? 'tencent' : '');
  var HAS_KEY = !!PROVIDER;

  /* ============================================================
   * 价格库
   * 保底 7 条内置；若外部盐城完整库已加载（信息更全），则整体替换，避免同名重复
   * ============================================================ */
  var VERIFIED_PRICES = [
    { kw: ['吾悦广场'], region: '射阳县', price: 1.11, op: '国家电网', park: '参照停车场', src: '无敌电动网', date: '2026-08' },
    { kw: ['千鹤湖'], region: '射阳县', price: 1.14, op: '特来电', park: '免费', src: '无敌电动网', date: '2026-08' },
    { kw: ['新城实验幼儿园'], region: '射阳县', price: 1.14, op: '特来电', park: '免费', src: '无敌电动网', date: '2026-08' },
    { kw: ['晨光路'], region: '射阳县', price: 1.20, op: '国家电网', park: '参照停车场', src: '无敌电动网', date: '2026-08' },
    { kw: ['黄海路'], region: '射阳县', price: 1.20, op: '国家电网', park: '参照停车场', src: '无敌电动网', date: '2026-08' },
    { kw: ['合德供电所'], region: '射阳县', price: 1.20, op: '国家电网', park: '免费', src: '无敌电动网', date: '2026-08' },
    { kw: ['潇洋'], region: '射阳县', price: 1.62, op: '特来电', park: '免费', src: '无敌电动网', date: '2026-08' }
  ];

  // 盐城市 9 区县完整价格库（独立文件 js/ev-prices-yancheng.js，同步加载，先于本文件执行）
  if (window.EV_PRICES_YANCHENG && window.EV_PRICES_YANCHENG.length) {
    VERIFIED_PRICES = window.EV_PRICES_YANCHENG;
  }

  // 城市 → 下辖区县 映射：用于「城市级（IP）定位」时，仍能匹配该城市下各区县的核实价。
  // 价格库的 region 是区县名（射阳县/亭湖区…），而 IP 定位只给到城市名（盐城市），
  // 没有这层映射，regionHit 四项全 false，会导致「城市级定位下 0 条价格匹配」的致命 bug。
  var CITY_DISTRICTS = {
    '盐城市': ['亭湖区', '盐都区', '大丰区', '盐城经济技术开发区', '射阳县', '建湖县', '阜宁县', '滨海县', '响水县', '东台市']
  };

  // 停车费口径 → 页面上的说法
  var PARK_TEXT = {
    '免费': '停车免费',
    '充电免时长': '充电免停车时长',
    '参照停车场': '停车参照停车场标准',
    '收费': '停车收费（以现场公示为准）',
    '未公布': '停车费以现场为准'
  };

  /* ---------- 无 Key / 定位失败时的兜底数据（射阳县，来源：县政府《"十四五"电动汽车充电设施布局规划》表 2-3） ---------- */
  var FALLBACK_STATIONS = [
    { name: '滨湖大道充电站（万帮充电）', addr: '射阳县滨湖大道9号', op: '万帮充电', n: '6台快充', kw: 720, kind: '公用' },
    { name: '机场路罾塘居委会充电站（万帮充电）', addr: '射阳县机场路罾塘居委会', op: '万帮充电', n: '5台快充', kw: 600, kind: '公用' },
    { name: '海河镇高铁站北充电站', addr: '射阳县海河镇高铁站北边', op: '国家电网', n: '9台快充', kw: 960, kind: '公用' },
    { name: '海河镇高铁站南充电站', addr: '射阳县海河镇高铁站南边', op: '国家电网', n: '4台快充', kw: 480, kind: '公用' },
    { name: '汽车客运站充电站', addr: '射阳县汽车客运站', op: '国家电网', n: '5台快充', kw: 480, kind: '公用' },
    { name: '射阳县政府充电站', addr: '射阳县幸福大道', op: '国家电网', n: '5台快充', kw: 450, kind: '公用' },
    { name: '晨光路停车场充电站', addr: '射阳县合德镇晨光路17号', op: '国家电网', n: '12台快充', kw: 1080, kind: '公用' },
    { name: '黄海路停车场充电站', addr: '射阳县合德镇黄海路停车场', op: '国家电网', n: '8台快充', kw: 720, kind: '公用' },
    { name: '合德供电所充电站', addr: '射阳县解放东路合德供电所', op: '国家电网', n: '2快2慢', kw: 240, kind: '公用' },
    { name: '兴桥供电所充电站', addr: '射阳县兴桥镇冈合路', op: '国家电网', n: '2快2慢', kw: 240, kind: '公用' },
    { name: '陈洋供电所充电站', addr: '射阳县陈洋镇人民西路27号', op: '国家电网', n: '8台快充', kw: 720, kind: '公用' },
    { name: '经济开发区科技服务中心充电站', addr: '射阳县幸福大道经开区管委会', op: '国家电网', n: '8台快充', kw: 720, kind: '公用' },
    { name: '千鹤湖酒店充电站', addr: '射阳县千鹤湖酒店', op: '特来电', n: '6台快充', kw: 540, kind: '公用' },
    { name: '新城实验幼儿园充电站', addr: '射阳县开放大道新城实验幼儿园停车场', op: '特来电', n: '38台快充', kw: 3420, kind: '公用' },
    { name: '港城实验小学充电站', addr: '射阳县解放东路港城实验小学停车场', op: '特来电', n: '37台快充', kw: 3330, kind: '公用' },
    { name: '特庸镇卫生院充电站', addr: '射阳县特庸镇码中街171号', op: '特来电', n: '1快2慢', kw: 120, kind: '公用' },
    { name: '潇洋汽车销售公司充电站', addr: '射阳县人民东路100号', op: '特来电', n: '1台快充', kw: 90, kind: '公用' },
    { name: '吾悦广场停车场充电站', addr: '射阳县吾悦广场负一层', op: '国家电网', n: '6快6慢', kw: 660, kind: '公用' },
    { name: '滨湖会议中心充电站', addr: '射阳县滨湖会议中心', op: '星星充电', n: '12台快充', kw: 1080, kind: '公用' },
    { name: '三维交通场站充电站', addr: '射阳县合德镇江苏三维交通集团', op: '星星充电', n: '10台快充', kw: 900, kind: '公用' },
    { name: '景隆生态农业充电站', addr: '射阳县盘湾镇南沃村', op: '星星充电', n: '15台慢充', kw: 105, kind: '公用' },
    { name: '沈海高速射阳服务区充电站（沈阳方向）', addr: '沈海高速射阳服务区', op: '国家电网', n: '4台快充', kw: 480, kind: '高速服务区' },
    { name: '沈海高速射阳服务区充电站（海口方向）', addr: '沈海高速射阳服务区', op: '国家电网', n: '4台快充', kw: 480, kind: '高速服务区' },
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
    // 注意「中国石化」不能只写「中石化」——「中国石化」里「中」后接的是「国」，匹配不上
    [/石化易电|中国石化|中石化|易捷/i, '石化易电'],
    [/中石油/i, '中石油'],
    [/开迈斯|CAMS/i, '开迈斯'],
    [/依威/i, '依威能源'],
    [/普诺得/i, '普诺得'],
    [/汇充电/i, '汇充电'],
    [/南方电网|南网/i, '南方电网'],
    // 以下为实测中遇到的中小运营商，识别得越准，越能挡住「A 站的价套到 B 站」的误匹配
    [/新电途/i, '新电途'],
    [/能瑞/i, '南京能瑞'],
    [/世动云充|世动/i, '世动云充'],
    [/蔚景云/i, '蔚景云'],
    [/快电|能链智电/i, '快电'],
    [/驿充电/i, '驿充电'],
    [/绿能慧充|绿能/i, '绿能慧充'],
    [/安悦/i, '安悦充电'],
    [/普天新能源|普天/i, '普天新能源'],
    [/鼎充/i, '鼎充'],
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
  function hide(el) { if (el) el.hidden = true; }

  /* 并发受控的批量请求（腾讯个人开发者限 5 并发，这里保守用 4） */
  function mapLimit(tasks, n, fn) {
    return new Promise(function (resolve) {
      if (!tasks.length) { resolve([]); return; }
      var i = 0, out = [], settled = 0;
      function next() {
        if (i >= tasks.length) return;
        var idx = i++;
        fn(tasks[idx]).then(function (r) { out[idx] = r; }, function () { out[idx] = []; })
          .then(function () { settled++; next(); if (settled === tasks.length) resolve(out); });
      }
      for (var k = 0; k < Math.min(n, tasks.length); k++) next();
    });
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
    view: 'list',        // 已废弃：现改为地图与卡片栏常驻联动，不再二选一
    onlyPrice: false,    // 「仅显示有价」筛选
    onlyFast: false,     // 「仅快充」筛选（仅对已知功率的站点生效，绝不编造）
    op: '',
    lastList: [],        // 最近一次渲染的列表，供卡片→地图联动
    fallback: false,
    hiddenByStatus: 0,   // 因「暂停营业」被过滤掉的站点数
    map: null,
    markers: [],
    infoW: null
  };
  var mapPromise = null;
  var mapLoadErr = '';

  /* ============================================================
   * 坐标转换：WGS84（浏览器定位原始值）→ GCJ02（国内地图坐标系）
   * 两家地图都用 GCJ02，浏览器原生定位给的是 WGS84，不转换会偏 300~800 米。
   * ============================================================ */
  var GCJ_A = 6378245.0, GCJ_EE = 0.00669342162296594323;
  function outOfChina(lng, lat) {
    return (lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271);
  }
  function transLat(x, y) {
    var ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
    ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
    ret += (20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin(y / 3.0 * Math.PI)) * 2.0 / 3.0;
    ret += (160.0 * Math.sin(y / 12.0 * Math.PI) + 320 * Math.sin(y * Math.PI / 30.0)) * 2.0 / 3.0;
    return ret;
  }
  function transLng(x, y) {
    var ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
    ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
    ret += (20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin(x / 3.0 * Math.PI)) * 2.0 / 3.0;
    ret += (150.0 * Math.sin(x / 12.0 * Math.PI) + 300.0 * Math.sin(x / 30.0 * Math.PI)) * 2.0 / 3.0;
    return ret;
  }
  function wgs84ToGcj02(lng, lat) {
    if (outOfChina(lng, lat)) return { lng: lng, lat: lat };
    var dLat = transLat(lng - 105.0, lat - 35.0);
    var dLng = transLng(lng - 105.0, lat - 35.0);
    var radLat = lat / 180.0 * Math.PI;
    var magic = Math.sin(radLat);
    magic = 1 - GCJ_EE * magic * magic;
    var sqrtMagic = Math.sqrt(magic);
    dLat = (dLat * 180.0) / ((GCJ_A * (1 - GCJ_EE)) / (magic * sqrtMagic) * Math.PI);
    dLng = (dLng * 180.0) / (GCJ_A / sqrtMagic * Math.cos(radLat) * Math.PI);
    return { lng: lng + dLng, lat: lat + dLat };
  }

  /* 浏览器原生定位（统一纠偏后返回 GCJ02） */
  function locateByBrowser() {
    return new Promise(function (resolve, reject) {
      if (!navigator.geolocation) { reject(new Error('浏览器不支持定位')); return; }
      navigator.geolocation.getCurrentPosition(function (pos) {
        var g = wgs84ToGcj02(pos.coords.longitude, pos.coords.latitude);
        resolve({ lng: g.lng, lat: g.lat, acc: pos.coords.accuracy, src: 'gps' });
      }, function (e) {
        reject(new Error(e.code === 1 ? '你拒绝了定位授权' : '定位失败：' + (e.message || '')));
      }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
    });
  }

  /* ============================================================
   * 适配器：高德
   * 统一输出 {id, name, addr, lng, lat, tel, cat} 的 POI 数组
   * ============================================================ */
  var AMAP_PLUGINS = 'AMap.Geolocation,AMap.PlaceSearch,AMap.Geocoder,AMap.CitySearch';

  var Amap = {
    label: '高德地图',

    ready: function () {
      return new Promise(function (resolve, reject) {
        if (window.AMap) { resolve(window.AMap); return; }
        if (AMAP_SECURITY) window._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY };
        var s = document.createElement('script');
        s.src = 'https://webapi.amap.com/maps?v=2.0&key=' + encodeURIComponent(AMAP_KEY) +
          '&plugin=' + AMAP_PLUGINS;
        s.async = true;
        s.onload = function () {
          window.AMap ? resolve(window.AMap) : reject(new Error('高德地图组件未挂载'));
        };
        s.onerror = function () { reject(new Error('高德地图脚本加载失败')); };
        document.head.appendChild(s);
      });
    },

    // 高德 SDK 定位（自带 IP 融合定位，比浏览器原生更容易在手机上成功）
    locate: function () {
      return Amap.ready().then(function () {
        return new Promise(function (resolve, reject) {
          var geo = new window.AMap.Geolocation({
            enableHighAccuracy: true, timeout: 12000, maximumAge: 60000,
            convert: true, showButton: false, panToLocation: false, zoomToAccuracy: false
          });
          geo.getCurrentPosition(function (status, result) {
            if (status === 'complete' && result && result.position) {
              resolve({
                lng: result.position.lng, lat: result.position.lat,
                acc: result.accuracy, address: result.formattedAddress || '', src: 'gps'
              });
            } else {
              reject(new Error(typeof result === 'string' ? result : ((result && result.info) || '定位失败')));
            }
          });
        });
      });
    },

    // IP 兜底：先拿城市名，再地理编码出坐标
    ipLocate: function () {
      return Amap.ready().then(function () {
        return new Promise(function (resolve, reject) {
          var cs = new window.AMap.CitySearch();
          cs.getLocalCity(function (status, result) {
            if (status !== 'complete' || !result || !result.city) {
              reject(new Error('IP 定位失败')); return;
            }
            var cityName = result.city;
            Amap.geocode(cityName).then(function (g) {
              g.src = 'ip';
              resolve(g);
            }, function () { reject(new Error('IP 定位失败')); });
          });
        });
      });
    },

    regeo: function (lng, lat) {
      return Amap.ready().then(function () {
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
      }).catch(function () { return { address: '', city: '', district: '' }; });
    },

    geocode: function (text) {
      return Amap.ready().then(function () {
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
            } else { reject(new Error('没找到这个地方，换个说法试试（如「射阳县吾悦广场」）')); }
          });
        });
      });
    },

    // 多关键词 × 多页，串行拉取（高德 JS SDK 不宜高并发）
    poiSearch: function () {
      var kws = ['充电站', '充电桩', '电动汽车充电', '新能源充电'];
      var all = [], seen = {};
      return Amap.ready().then(function () {
        function oneKw(idx) {
          if (idx >= kws.length) return Promise.resolve();
          var kw = kws[idx];
          function onePage(page) {
            return new Promise(function (resolve) {
              var ps = new window.AMap.PlaceSearch({
                pageSize: 50, pageIndex: page, extensions: 'all',
                city: state.city || '全国', citylimit: false, autoFitView: false
              });
              ps.searchNearBy(kw, [state.center.lng, state.center.lat], state.radius,
                function (status, result) {
                  if (status === 'complete' && result.poiList && result.poiList.pois) {
                    result.poiList.pois.forEach(function (poi) {
                      if (!poi || !poi.id || seen[poi.id]) return;
                      seen[poi.id] = 1;
                      var ll = Amap.parseLoc(poi.location);
                      if (!ll) return;
                      all.push({
                        id: poi.id, name: poi.name || '', addr: poi.address || '',
                        lng: ll.lng, lat: ll.lat, tel: poi.tel || '', cat: poi.type || ''
                      });
                    });
                    resolve(result.poiList.pois.length);
                  } else { resolve(0); }
                });
            });
          }
          // 单关键词最多翻 2 页，不足一页说明后面没有了
          return onePage(1).then(function (n1) {
            if (n1 < 50) return;
            return onePage(2).then(function (n2) {
              if (n2 < 50) return;
            });
          }).then(function () { return oneKw(idx + 1); });
        }
        return oneKw(0).then(function () { return all; });
      });
    },

    // 高德 SDK 返回的 location 有时是 "lng,lat" 字符串，有时是 {lng,lat} 对象
    parseLoc: function (loc) {
      if (!loc) return null;
      if (typeof loc === 'string') {
        var p = loc.split(',');
        if (p.length !== 2) return null;
        var a = parseFloat(p[0]), b = parseFloat(p[1]);
        return (isFinite(a) && isFinite(b)) ? { lng: a, lat: b } : null;
      }
      if (isFinite(loc.lng) && isFinite(loc.lat)) return { lng: loc.lng, lat: loc.lat };
      if (typeof loc.getLng === 'function') {
        var c = loc.getLng(), d = loc.getLat();
        return (isFinite(c) && isFinite(d)) ? { lng: c, lat: d } : null;
      }
      return null;
    },

    navUri: function (s) {
      return 'https://uri.amap.com/navigation?to=' + s.lng + ',' + s.lat + ',' +
        encodeURIComponent(s.name) + '&mode=car&coordinate=gaode&callnative=1&src=longxiong';
    },
    poiUri: function (s) {
      // 优先用「精确坐标」落点：坐标来自高德检索结果，100% 准确，保证一点就钉在那个站的位置上
      // （poi?id= 深链在桌面端/部分情况下不会精准落到该站，故改为坐标 marker 为主）
      if (isFinite(s.lng) && isFinite(s.lat)) {
        return 'https://uri.amap.com/marker?position=' + s.lng + ',' + s.lat +
          '&name=' + encodeURIComponent(s.name) + '&coordinate=gaode&src=longxiong&callnative=1';
      }
      // 无坐标但 POI id 有效 → 走 POI 详情深链
      if (s.id && String(s.id).indexOf('fb') !== 0) {
        return 'https://uri.amap.com/poi?id=' + encodeURIComponent(s.id) + '&src=longxiong&callnative=1';
      }
      // 兜底：按站名 + 城市搜索（带城市限定更精准）
      return 'https://uri.amap.com/search?keyword=' + encodeURIComponent(s.name) +
        (state.city ? '&city=' + encodeURIComponent(state.city) : '') + '&src=longxiong';
    },

    drawMap: function (el, list) {
      return Amap.ready().then(function () {
        var A = window.AMap;
        if (!state.map) {
          state.map = new A.Map(el, {
            zoom: 14,
            center: [state.center.lng, state.center.lat],
            mapStyle: Amap.mapStyle()
          });
        } else {
          state.map.setCenter([state.center.lng, state.center.lat]);
          state.map.setMapStyle(Amap.mapStyle());
        }
        state.map.clearMap();
        state.markers = [];

        list.filter(function (s) { return isFinite(s.lng) && isFinite(s.lat); })
          .slice(0, 80)
          .forEach(function (s, i) {
            var mk = new A.Marker({
              position: [s.lng, s.lat],
              title: s.name,
              content: '<div class="ev-pin">' + (i + 1) + '</div>',
              offset: new A.Pixel(-13, -13)
            });
            mk.on('click', function () {
              new A.InfoWindow({
                content: stationInfoHTML(s),
                offset: new A.Pixel(0, -20)
              }).open(state.map, [s.lng, s.lat]);
            });
            state.map.add(mk);
            state.markers.push(mk);
          });
      });
    },

    // 卡片→地图联动：点卡片把地图移到那个站并弹出信息窗
    panTo: function (s) {
      if (!state.map || !isFinite(s.lng) || !isFinite(s.lat)) return;
      state.map.setZoomAndCenter(16, [s.lng, s.lat]);
      new window.AMap.InfoWindow({
        content: stationInfoHTML(s),
        offset: new window.AMap.Pixel(0, -20)
      }).open(state.map, [s.lng, s.lat]);
    },

    mapStyle: function () {
      var dark = document.documentElement.getAttribute('data-theme') !== 'light';
      return dark ? 'amap://styles/dark' : 'amap://styles/normal';
    },

    syncStyle: function () {
      if (state.map && window.AMap) {
        try { state.map.setMapStyle(Amap.mapStyle()); } catch (e) { /* 忽略 */ }
      }
    }
  };

  /* ============================================================
   * 适配器：腾讯位置服务
   * WebService 原生支持 JSONP，不依赖 SDK 即可检索；SDK 只在画地图时懒加载
   * ============================================================ */
  var jsonpSeq = 0;
  function jsonp(path, params) {
    return new Promise(function (resolve, reject) {
      var cb = '__evcb' + (++jsonpSeq);
      var script = document.createElement('script');
      var done = false;
      var timer = setTimeout(function () { finish(null, new Error('请求超时')); }, 12000);
      function finish(data, err) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        try { delete window[cb]; } catch (e) { window[cb] = undefined; }
        if (script.parentNode) script.parentNode.removeChild(script);
        err ? reject(err) : resolve(data || {});
      }
      window[cb] = function (data) { finish(data, null); };
      params = params || {};
      params.key = TENCENT_KEY;
      params.output = 'jsonp';
      params.callback = cb;
      var qs = Object.keys(params).map(function (k) {
        return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
      }).join('&');
      script.src = 'https://apis.map.qq.com' + path + '?' + qs;
      script.async = true;
      script.onerror = function () { finish(null, new Error('网络请求失败')); };
      document.head.appendChild(script);
    });
  }

  var NEARBY_CAP = 5000;   // 腾讯 nearby 检索半径上限 5000 米，超出部分由全市检索补

  var Tx = {
    label: '腾讯地图',

    // 腾讯的检索走 WebService JSONP，不需要 SDK；这里只给地图用
    ready: function () {
      return new Promise(function (resolve, reject) {
        if (window.qq && window.qq.maps && window.qq.maps.Map) { resolve(); return; }
        var s = document.createElement('script');
        s.src = 'https://map.qq.com/api/gljs?v=1.exp&key=' + encodeURIComponent(TENCENT_KEY);
        s.async = true;
        s.onload = function () {
          (window.qq && window.qq.maps && window.qq.maps.Map)
            ? resolve() : reject(new Error('地图组件未挂载'));
        };
        s.onerror = function () { reject(new Error('地图脚本加载失败')); };
        document.head.appendChild(s);
      });
    },

    locate: function () { return locateByBrowser(); },

    ipLocate: function () {
      return jsonp('/ws/location/v1/ip', {}).then(function (d) {
        if (d.status !== 0 || !d.result || !d.result.location) {
          throw new Error('IP 定位失败：' + (d.message || ''));
        }
        var ad = d.result.ad_info || {};
        var nat = ad.nation || '', prov = ad.province || '', city = ad.city || '', dist = ad.district || '';
        return {
          lng: d.result.location.lng, lat: d.result.location.lat,
          city: city, district: dist,
          address: (nat === '中国' ? '' : nat) + prov + city + dist,
          src: 'ip'
        };
      });
    },

    regeo: function (lng, lat) {
      return jsonp('/ws/geocoder/v1/', { location: lat + ',' + lng, get_poi: '0' })
        .then(function (d) {
          if (d.status !== 0 || !d.result) return { address: '', city: '', district: '' };
          var c = d.result.address_component || d.result.address_components || {};
          return {
            address: d.result.address || ((c.province || '') + (c.city || '') + (c.district || '')),
            city: c.city || '',
            district: c.district || ''
          };
        })
        .catch(function () { return { address: '', city: '', district: '' }; });
    },

    geocode: function (text) {
      return jsonp('/ws/geocoder/v1/', { address: text }).then(function (d) {
        if (d.status !== 0 || !d.result || !d.result.location) {
          throw new Error('没找到这个地方，换个说法试试（如「射阳县吾悦广场」）');
        }
        var c = d.result.address_components || d.result.address_component || {};
        return {
          lng: d.result.location.lng, lat: d.result.location.lat,
          address: d.result.address || text,
          city: c.city || '',
          district: c.district || ''
        };
      });
    },

    searchNearby: function (kw, page, radius) {
      return jsonp('/ws/place/v1/search', {
        keyword: kw,
        boundary: 'nearby(' + state.center.lat + ',' + state.center.lng + ',' + radius + ',1)',
        page_size: '20',
        page_index: String(page),
        orderby: '_distance'
      }).then(function (d) {
        return (d.status === 0 && Array.isArray(d.data)) ? d.data : [];
      }).catch(function () { return []; });
    },

    searchRegion: function (kw, page) {
      if (!state.city) return Promise.resolve([]);
      return jsonp('/ws/place/v1/search', {
        keyword: kw,
        boundary: 'region(' + state.city + ',1)',
        page_size: '20',
        page_index: String(page)
      }).then(function (d) {
        return (d.status === 0 && Array.isArray(d.data)) ? d.data : [];
      }).catch(function () { return []; });
    },

    poiSearch: function () {
      var kws = ['充电站', '充电桩'];
      var nearR = Math.min(state.radius, NEARBY_CAP);
      var jobs = [];
      kws.forEach(function (kw) {
        for (var p = 1; p <= 3; p++) jobs.push({ t: 'near', kw: kw, p: p });
        for (var q = 1; q <= 5; q++) jobs.push({ t: 'reg', kw: kw, p: q });
      });
      return mapLimit(jobs, 4, function (j) {
        return j.t === 'near' ? Tx.searchNearby(j.kw, j.p, nearR) : Tx.searchRegion(j.kw, j.p);
      }).then(function (chunks) {
        var seen = {}, all = [];
        chunks.forEach(function (list) {
          (list || []).forEach(function (poi) {
            if (!poi || !poi.id || seen[poi.id]) return;
            var loc = poi.location;
            if (!loc || !isFinite(loc.lng) || !isFinite(loc.lat)) return;
            seen[poi.id] = 1;
            all.push({
              id: poi.id, name: poi.title || '', addr: poi.address || '',
              lng: loc.lng, lat: loc.lat, tel: poi.tel || '', cat: poi.category || ''
            });
          });
        });
        return all;
      });
    },

    navUri: function (s) {
      if (!isFinite(s.lng) || !isFinite(s.lat)) return Tx.poiUri(s);
      return 'https://apis.map.qq.com/uri/v1/routeplan?type=drive&to=' + encodeURIComponent(s.name) +
        '&tocoord=' + s.lat + ',' + s.lng + '&coord_type=2&policy=1&referer=' + encodeURIComponent(TENCENT_REFERER);
    },
    poiUri: function (s) {
      if (!isFinite(s.lng) || !isFinite(s.lat)) {
        return 'https://apis.map.qq.com/uri/v1/search?keyword=' + encodeURIComponent(s.name) +
          '&referer=' + encodeURIComponent(TENCENT_REFERER);
      }
      return 'https://apis.map.qq.com/uri/v1/marker?marker=coord:' + s.lat + ',' + s.lng +
        ';title:' + encodeURIComponent(s.name) + ';addr:' + encodeURIComponent(s.addr || s.name) +
        '&coord_type=2&referer=' + encodeURIComponent(TENCENT_REFERER);
    },

    drawMap: function (el, list) {
      return Tx.ready().then(function () {
        var Q = window.qq.maps;
        var center = new Q.LatLng(state.center.lat, state.center.lng);
        if (!state.map) {
          state.map = new Q.Map(el, { center: center, zoom: 14, mapStyleId: Tx.mapStyle() });
        } else {
          state.map.setCenter(center);
          try { state.map.setMapStyleId(Tx.mapStyle()); } catch (e) { /* 老版本无此方法，忽略 */ }
        }

        state.markers.forEach(function (m) { try { m.setMap(null); } catch (e) { } });
        state.markers = [];
        if (state.infoW) { try { state.infoW.close(); } catch (e) { } }

        list.filter(function (s) { return isFinite(s.lng) && isFinite(s.lat); })
          .slice(0, 80)
          .forEach(function (s, i) {
            var pos = new Q.LatLng(s.lat, s.lng);
            var mk = new Q.Marker({
              map: state.map,
              position: pos,
              content: '<div class="ev-pin">' + (i + 1) + '</div>'
            });
            Q.event.addListener(mk, 'click', function () {
              if (!state.infoW) state.infoW = new Q.InfoWindow({ map: state.map });
              state.infoW.setContent(stationInfoHTML(s));
              state.infoW.setPosition(pos);
              state.infoW.open();
            });
            state.markers.push(mk);
          });
      });
    },

    // 卡片→地图联动：点卡片把地图移到那个站并弹出信息窗
    panTo: function (s) {
      if (!state.map || !isFinite(s.lat) || !isFinite(s.lng)) return;
      var pos = new window.qq.maps.LatLng(s.lat, s.lng);
      state.map.setCenter(pos);
      if (state.map.setZoom) { try { state.map.setZoom(16); } catch (e) { } }
      if (!state.infoW) state.infoW = new window.qq.maps.InfoWindow({ map: state.map });
      state.infoW.setContent(stationInfoHTML(s));
      state.infoW.setPosition(pos);
      state.infoW.open();
    },

    mapStyle: function () {
      var dark = document.documentElement.getAttribute('data-theme') !== 'light';
      return dark ? 'style2' : 'style1';
    },

    syncStyle: function () {
      if (state.map && window.qq && window.qq.maps) {
        try { state.map.setMapStyleId(Tx.mapStyle()); } catch (e) { /* 忽略 */ }
      }
    }
  };

  /* 当前生效的地图服务 */
  var P = PROVIDER === 'amap' ? Amap : Tx;

  /* ============================================================
   * 定位
   * ============================================================ */
  async function doLocate(manualText) {
    var t = $('evLocTitle'), s = $('evLocSub');
    t.innerHTML = '<span class="ev-spinner"></span>正在获取位置…';
    s.textContent = '';
    hide($('evWarn'));

    try {
      var pos;
      if (manualText) {
        if (!HAS_KEY) throw new Error('手动搜索需要配置地图服务 Key');
        pos = await P.geocode(manualText);
      } else {
        // ① 地图 SDK 定位 → ② 浏览器原生定位 → ③ IP 粗略定位
        try {
          pos = await P.locate();
        } catch (e1) {
          if (!HAS_KEY) throw e1;
          try {
            pos = await locateByBrowser();
          } catch (e2) {
            pos = await P.ipLocate();
          }
        }
        if (!pos.address && HAS_KEY) {
          var rg = await P.regeo(pos.lng, pos.lat);
          pos.address = rg.address;
          pos.city = rg.city || pos.city;
          pos.district = rg.district || pos.district;
        }
      }

      state.center = { lng: pos.lng, lat: pos.lat };
      state.address = pos.address || '';
      state.city = pos.city || '';
      state.district = pos.district || '';

      // IP 城市级定位：以市中心为参考点，距离只是「到市中心」的参考值，不代表身边。
      // 先把检索半径放大到覆盖全市，搜索完成后再弹出明确提示（search 内部会先 hide 掉提示横幅）。
      if (pos.src === 'ip') {
        state.radius = 20000;
        syncRadiusChip();
      }

      var where = state.district || state.city || (state.address || '已定位');
      t.textContent = '📍 ' + (state.address || (pos.lng.toFixed(5) + ', ' + pos.lat.toFixed(5)));
      s.textContent = '定位成功 · ' + where +
        (pos.src === 'ip' ? '（城市级定位 · 距离为到市中心参考值）' : '') +
        (HAS_KEY ? ' · 数据来自' + P.label : '（未配置地图服务 Key，当前显示内置射阳数据）');
      s.className = 'ev-locate-sub ok';

      await search();

      // IP 定位提示必须在 search() 之后弹出，否则会被其内部 hide($('evWarn')) 清掉
      if (pos.src === 'ip') {
        var warn = $('evWarn');
        warn.hidden = false;
        warn.innerHTML = '⚠️ <b>当前为城市级定位</b>（定位授权未开启或获取失败）：下面以' +
          esc(state.city || '市中心') + '为中心展示全市充电站，<b>距离仅为到市中心的参考值，不代表你身边的桩</b>。' +
          '在上方输入框输入你的具体地点（如「射阳县吾悦广场」）可精确到米。';
      }
    } catch (e) {
      t.textContent = '⚠️ ' + (e && e.message ? e.message : '定位失败');
      s.textContent = '可在下方输入框手动输入地点，或点「重新定位」再试一次';
      s.className = 'ev-locate-sub';
      // 定位失败也要给内容：直接上兜底数据
      renderFallback();
    }
  }

  /* ============================================================
   * 检索：适配器拉回原始 POI，这里统一做距离计算、半径过滤、品牌识别、价格匹配
   * ============================================================ */
  async function search() {
    if (!HAS_KEY) { renderFallback(); return; }
    if (!state.center) return;

    $('evList').innerHTML = '<div class="ev-skel"></div><div class="ev-skel"></div><div class="ev-skel"></div>';
    hide($('evSummary'));

    var raw = [];
    try {
      raw = await P.poiSearch();
    } catch (e) {
      $('evList').innerHTML = '<div class="ev-empty">检索失败：' + esc(e && e.message ? e.message : '未知原因') +
        '<br>可点「重新定位」再试一次。</div>';
      return;
    }

    var all = [];
    raw.forEach(function (poi) {
      var d = haversine({ lat: state.center.lat, lng: state.center.lng }, { lat: poi.lat, lng: poi.lng });
      if (d > state.radius * 1.05) return;   // 地图偶有超半径回传，滤掉
      var name = poi.name || '';
      // 关键词检索偶尔带回「XX新能源公司」这类擦边结果，轻过滤一下
      if (!/充电|加电|换电|超充/.test(name) && !/充电/.test(poi.cat || '')) return;

      var vp = matchVerified(name, poi.addr || '');
      // 明确标注暂停营业的站点不展示（找桩的人要的是能用的）
      if (vp && vp.status && /暂停|停用|在建/.test(vp.status)) { state.hiddenByStatus++; return; }

      all.push({
        id: poi.id, name: name, addr: poi.addr || '',
        lng: poi.lng, lat: poi.lat, dist: d,
        op: vp ? vp.op : guessOp(name + ' ' + (poi.cat || '')),
        tel: poi.tel || '',
        price: vp ? vp.price : null,
        priceNote: priceNoteOf(vp),
        priceSrc: vp ? vp.src : '',
        priceDate: vp ? vp.date : '',
        verified: !!vp,
        fast: false, slow: false   // 实时检索拿不到功率，一律未知，绝不编造快慢
      });
    });

    state.fallback = false;
    hide($('evWarn'));
    state.stations = all;
    buildOpBar();
    render();
  }

  /* 价格备注：桩数 + 停车费口径 */
  function priceNoteOf(vp) {
    if (!vp) return '';
    var parts = [];
    if (vp.dc || vp.ac) {
      var g = [];
      if (vp.dc) g.push(vp.dc + ' 直流');
      if (vp.ac) g.push(vp.ac + ' 交流');
      parts.push(g.join(' / '));
    }
    if (vp.park && PARK_TEXT[vp.park]) parts.push(PARK_TEXT[vp.park]);
    else if (vp.note) parts.push(vp.note);
    return parts.join(' · ');
  }

  /* 区县名是否出现在 POI 文本（站名+地址）里：用于消解「同名地标跨区县」歧义。
   * 高德站名常写「大丰」而非「大丰区」，故同时尝试去掉末尾 区/县/市 的短名。 */
  function regionInText(region, text) {
    if (!region || !text) return false;
    if (text.indexOf(region) !== -1) return true;
    var short = region.replace(/(区|县|市)$/, '');
    return short.length >= 2 && text.indexOf(short) !== -1;
  }

  /* ---------- 价格匹配：站名关键词 + 地区限定 + 品牌一致性，避免张冠李戴 ---------- */
  function matchVerified(name, addr) {
    if (!state.district && !state.city) return null;
    var here = state.district || '';
    var city = state.city || '';
    // 城市级（IP）定位时，here 为空、city 为「盐城市」；此时允许匹配该城市下任意区县的价格。
    // 注意：仅在「无精确区县（here 为空）」时才放开全市——若已精确到区县，必须只匹配该区县，
    // 否则会出现「亭湖的站套上射阳的价」这类跨区县误匹配。
    var districtsOfCity = (city && CITY_DISTRICTS[city]) || [];
    var cityWide = !here && districtsOfCity.length;
    var guessed = guessOp(name);   // 站名前缀通常就是运营商，如「星星充电汽车充电站(……)」
    var text = name + ' ' + (addr || '');
    var candidates = [];
    for (var i = 0; i < VERIFIED_PRICES.length; i++) {
      var v = VERIFIED_PRICES[i];
      // 地区门槛：本条价格只在对应地区生效
      //   · 精确区县定位（here=射阳县）→ 只看射阳县的价格
      //   · 城市级定位（city=盐城市，here 为空）→ 看盐城市下全部区县的价格
      var regionHit = (v.region === here) || (v.region === city) ||
        (here && v.region.indexOf(here) === 0) || (city && city.indexOf(v.region) === 0) ||
        (cityWide && districtsOfCity.indexOf(v.region) >= 0);
      if (!regionHit) continue;
      // 关键词命中：站名 OR 地址里包含全部关键词片段即可（高德有时把地标写在地址而非站名）
      var allHit = v.kw.every(function (k) {
        return name.indexOf(k) !== -1 || (addr && addr.indexOf(k) !== -1);
      });
      if (!allHit) continue;
      // 品牌冲突保护：站名里明明写着另一家运营商（如「星星充电…(晨光路充电站)」），
      // 说明它和价格库里那条国网晨光路站不是同一个站，价格不能套用。
      // 宁可显示「价格以现场为准」，也不能把别家的价安到这家头上。
      if (guessed !== '其他' && v.op && guessed !== v.op) continue;
      candidates.push(v);
    }
    if (!candidates.length) return null;
    // 城市级下「吾悦广场」这类同名地标可能跨区县都有价：优先选 POI 文本里出现了对应区县的，
    // 把"大丰吾悦"正确归到 大丰区 而非 射阳县。精确区县下 candidates 本就只有一个区县，无歧义。
    for (var c = 0; c < candidates.length; c++) {
      if (regionInText(candidates[c].region, text)) return candidates[c];
    }
    return candidates[0];
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
    if (state.onlyPrice) list = list.filter(function (s) { return s.price != null; });
    // 仅快充：只剔除「确定是纯慢充」的站点；功率未知的站点（实时检索）一律保留，绝不编造
    if (state.onlyFast) list = list.filter(function (s) { return !(s.slow && !s.fast); });
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

  /* 分时电价时段（一般规律，仅供参考：电价随尖峰/高峰/平段/低谷浮动） */
  var TOU_RULES = [
    { p: '低谷', test: function (h) { return h >= 23 || h < 7; } },
    { p: '平段', test: function (h) { return (h >= 7 && h < 10) || (h >= 15 && h < 18) || (h >= 21 && h < 23); } },
    { p: '高峰', test: function (h) { return (h >= 10 && h < 11) || (h >= 13 && h < 15) || (h >= 18 && h < 21); } },
    { p: '尖峰', test: function (h) { return h >= 11 && h < 13; } }
  ];
  function touPeriod(h) {
    for (var i = 0; i < TOU_RULES.length; i++) { if (TOU_RULES[i].test(h)) return TOU_RULES[i].p; }
    return '平段';
  }

  /* 运营商配色（国风黑金体系内的冷/暖区分，仅作视觉标识） */
  var OP_CLASS = {
    '国网': 'op-grid', '国家电网': 'op-grid',
    '特来电': 'op-teld',
    '星星充电': 'op-starcharge',
    '蔚来': 'op-nio', 'NIO': 'op-nio', 'NIO Power': 'op-nio',
    '特斯拉': 'op-tesla', 'Tesla': 'op-tesla'
  };
  function opClass(op) { return 'ev-op ' + (OP_CLASS[op] || 'op-default'); }

  function setText(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }

  function renderStats(list) {
    var total = list.length;
    var withPrice = 0, ops = {};
    list.forEach(function (s) {
      if (s.price != null) withPrice++;
      if (s.op) ops[s.op] = 1;
    });
    setText('evStatTotal', total);
    setText('evStatPrice', withPrice);
    setText('evStatOp', Object.keys(ops).length);
  }

  function renderTou() {
    var now = new Date();
    var p = touPeriod(now.getHours());
    var hh = String(now.getHours()).padStart(2, '0');
    var mm = String(now.getMinutes()).padStart(2, '0');
    setText('evTouNow', '现在约 ' + hh + ':' + mm + ' · 当前【' + p + '】');
    var segs = document.querySelectorAll('#evTou .ev-tou-seg');
    Array.prototype.forEach.call(segs, function (seg) {
      seg.classList.toggle('on', seg.getAttribute('data-p') === p);
    });
  }

  /* 地图信息窗 / 卡片联动共用的站点信息 HTML（保证两端一致） */
  function stationInfoHTML(s) {
    return '<div class="ev-info"><b>' + esc(s.name) + '</b><br>' +
      esc(s.op) + ' · ' + fmtDist(s.dist) + '<br>' +
      (s.price != null
        ? '<b class="ev-info-price">' + s.price.toFixed(2) + ' 元/度</b>'
        : '价格以现场为准') +
      '<br><a href="' + P.navUri(s) + '" target="_blank" rel="noopener">导航去这里</a> · ' +
      '<a href="' + P.poiUri(s) + '" target="_blank" rel="noopener">查实时价</a></div>';
  }

  function cardHtml(s, i) {
    var priceHtml = s.price != null
      ? '<span class="ev-price"><i>￥</i>' + s.price.toFixed(2) + '<i class="ev-unit">/度</i></span>' +
        '<span class="ev-seal">本站核实</span>'
      : '<span class="ev-price-none">价格以现场为准</span>';

    var srcHtml = (s.priceSrc || s.priceDate)
      ? '<div class="ev-src">来源：' + esc(s.priceSrc || '本站核实') +
        (s.priceDate ? ' · ' + esc(s.priceDate) + '采集' : '') + '</div>'
      : '';
    var noteHtml = s.priceNote
      ? '<div class="ev-note-line">📝 ' + esc(s.priceNote) + '</div>'
      : '';

    var tagHtml = (s.fast || s.slow)
      ? '<span class="ev-tag ' +
          (s.slow && !s.fast ? 'ev-tag-slow' : (s.fast && !s.slow ? 'ev-tag-fast' : 'ev-tag-both')) +
          '">' + (s.fast && !s.slow ? '快充' : (s.slow && !s.fast ? '慢充' : '快充·慢充')) + '</span>'
      : '';
    return '<article class="ev-card" data-i="' + i + '">' +
      '<div class="ev-card-head">' +
        '<div class="ev-rank">' + (i + 1) + '</div>' +
        '<div class="ev-head-main"><div class="ev-name">' + esc(s.name) + '</div>' +
        '<div class="ev-head-meta"><span class="' + opClass(s.op) + '">' + esc(s.op) + '</span>' + tagHtml + '</div></div>' +
        (isFinite(s.dist) ? '<div class="ev-dist">' + fmtDist(s.dist) + '</div>' : '') +
      '</div>' +
      '<div class="ev-card-body">' +
        '<div class="ev-price-row">' + priceHtml + '</div>' +
        (s.addr ? '<div class="ev-addr">📍 ' + esc(s.addr) + '</div>' : '') +
        (s.tel ? '<div class="ev-addr">☎ ' + esc(s.tel) + '</div>' : '') +
        noteHtml + srcHtml +
      '</div>' +
      '<div class="ev-card-foot">' +
        '<a class="ghost" href="' + P.navUri(s) + '" target="_blank" rel="noopener">🧭 导航去这里</a>' +
        '<a class="gold" href="' + P.poiUri(s) + '" target="_blank" rel="noopener">💰 查实时价</a>' +
      '</div></article>';
  }

  function render() {
    var list = sorted();
    state.lastList = list;
    renderStats(list);
    var box = $('evList');

    var withPrice = list.filter(function (s) { return s.price != null; }).length;
    var sum = $('evSummary');
    sum.hidden = false;
    sum.innerHTML = '找到 <b>' + list.length + '</b> 个充电站' +
      (state.fallback ? '' : '（半径 ' + (state.radius / 1000) + ' km）') +
      (state.op ? ' · 品牌筛选：' + esc(state.op) : '') +
      ' · 其中 <b>' + withPrice + '</b> 个有本站核实价，其余点「查实时价」看当前真实价格。' +
      (state.sort !== 'dist' && withPrice === 0 ? '<br>⚠️ 当前范围内没有已核实价格的站点，已按距离排列。' : '') +
      (state.hiddenByStatus ? '<br>（已过滤 ' + state.hiddenByStatus + ' 个标注暂停营业的站点）' : '');

    if (!list.length) {
      box.innerHTML = '<div class="ev-empty">这个范围内没找到充电站。<br>试试把半径调大，或换个地点搜。</div>';
    } else {
      box.innerHTML = list.map(cardHtml).join('');
    }
    if (HAS_KEY) renderMap(list);
  }

  /* ---------- 地图（按需：只在切到地图视图时才初始化） ---------- */
  function mapGuard() {
    if (!HAS_KEY) return Promise.reject(new Error('未配置地图服务 Key'));
    if (mapLoadErr) return Promise.reject(new Error(mapLoadErr));
    if (!mapPromise) {
      mapPromise = P.ready().catch(function (e) { mapLoadErr = e.message; throw e; });
    }
    return mapPromise;
  }

  /* ---------- 地图（常驻：有 Key 即与卡片栏联动显示） ---------- */
  function renderMap(list) {
    if (!HAS_KEY) return;   // 无 Key 时地图栏整体隐藏，不初始化
    var el = $('evMap');
    mapGuard().then(function () {
      if (el.querySelector('.ev-map-fail')) el.innerHTML = '';
      return P.drawMap(el, list);
    }).catch(function (e) {
      el.innerHTML = '<div class="ev-map-fail">地图组件暂不可用（' + esc(e && e.message ? e.message : '未知原因') +
        '）。<br>下面的卡片数据不受影响，点卡片上的「导航去这里」可在' + esc(P.label) + '里查看。</div>';
    });
  }

  /* ---------- 无 Key / 定位失败兜底 ---------- */
  function renderFallback() {
    state.fallback = true;
    var warn = $('evWarn');
    warn.hidden = false;
    warn.innerHTML = HAS_KEY
      ? '⚠️ 定位没成功，下面先显示<b>射阳县</b>的已知充电站（来源：县政府《"十四五"电动汽车充电设施布局规划》）。手动输入地点可查别处。'
      : '⚠️ 本页的实时定位检索需要地图服务授权，眼下未启用，下面先显示<b>射阳县</b>的已知充电站（来源：县政府《"十四五"电动汽车充电设施布局规划》表 2-3）。这些站点没有在线坐标，故按列表呈现、不做距离和地图。';

    if (!HAS_KEY) {
      $('evLocTitle').textContent = '📋 当前为内置数据模式';
      $('evLocSub').textContent = '实时定位检索需配置地图服务授权，启用后可查全国任意地点';
      $('evLocSub').className = 'ev-locate-sub';
    }

    // 兜底数据都是射阳的，价格匹配按射阳县限定，避免把别处同名站的价格安上来
    var region = '射阳县';
    state.hiddenByStatus = 0;

    state.stations = FALLBACK_STATIONS.map(function (s, i) {
      var vp = null;
      for (var j = 0; j < VERIFIED_PRICES.length; j++) {
        var v = VERIFIED_PRICES[j];
        if (v.region !== region) continue;
        if (v.kw.every(function (k) { return s.name.indexOf(k) !== -1; })) { vp = v; break; }
      }
      if (vp && vp.status && /暂停|停用|在建/.test(vp.status)) { state.hiddenByStatus++; return null; }
      return {
        id: 'fb' + i, name: s.name, addr: s.addr, lng: null, lat: null, dist: Infinity,
        op: s.op, tel: '',
        price: vp ? vp.price : null,
        priceNote: [s.n, (s.kw ? s.kw + ' kW' : ''), s.kind, priceNoteOf(vp)].filter(Boolean).join(' · '),
        priceSrc: vp ? vp.src : '', priceDate: vp ? vp.date : '', verified: !!vp,
        fast: /快/.test(s.n || ''), slow: /慢/.test(s.n || '')
      };
    }).filter(Boolean);

    buildOpBar();
    render();
  }

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
        if (state.center && HAS_KEY) search();
        return;
      }
      if (chip.hasAttribute('data-sort')) {
        state.sort = chip.getAttribute('data-sort');
        setOn(chip.parentNode, chip, 'data-sort');
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
      setTimeout(function () { P.syncStyle(); }, 60);
    });

    // 地图浮层筛选药丸（仅显示有价 / 仅快充）：切换即重渲染，地图与卡片同步过滤
    Array.prototype.forEach.call(document.querySelectorAll('.ev-pill'), function (p) {
      p.addEventListener('click', function () {
        var f = p.getAttribute('data-filter');
        if (f === 'price') { state.onlyPrice = !state.onlyPrice; p.classList.toggle('on', state.onlyPrice); }
        if (f === 'fast') { state.onlyFast = !state.onlyFast; p.classList.toggle('on', state.onlyFast); }
        render();
      });
    });

    // 卡片→地图联动：点卡片把地图移到对应站点（点卡片上的按钮/链接不触发）
    var listEl = $('evList');
    if (listEl) {
      listEl.addEventListener('click', function (e) {
        if (e.target.closest('a')) return;
        var card = e.target.closest('.ev-card');
        if (!card) return;
        var i = parseInt(card.getAttribute('data-i'), 10);
        if (!isNaN(i)) focusStation(i, card);
      });
    }
  }

  function setOn(scope, chip, attr) {
    Array.prototype.forEach.call(scope.querySelectorAll('.ev-chip'), function (c) {
      if (c.hasAttribute(attr)) c.classList.remove('on');
    });
    chip.classList.add('on');
  }

  // 让半径筛选条的高亮与 state.radius 保持一致（IP 定位自动放大半径后调用）
  function syncRadiusChip() {
    Array.prototype.forEach.call(document.querySelectorAll('.ev-chip[data-radius]'), function (c) {
      c.classList.toggle('on', parseInt(c.getAttribute('data-radius'), 10) === state.radius);
    });
  }

  /* 卡片→地图联动：高亮卡片并让地图聚焦到该站 */
  function focusStation(i, card) {
    var s = (state.lastList || [])[i];
    if (!s) return;
    Array.prototype.forEach.call(document.querySelectorAll('.ev-card'), function (c) { c.classList.remove('ev-card-focus'); });
    if (card) card.classList.add('ev-card-focus');
    if (!HAS_KEY || !isFinite(s.lng) || !isFinite(s.lat)) return;
    mapGuard().then(function () { P.panTo(s); }).catch(function () {});
  }

  /* ============================================================
   * 启动
   * ============================================================ */
  function init() {
    bind();
    renderTou();
    if (HAS_KEY) {
      document.body.classList.add('ev-has-map');
      doLocate();
    } else {
      renderFallback();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();
