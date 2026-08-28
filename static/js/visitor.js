// 访客匿名身份卡：进网站自动领一张国风雅号+编号，成绩跟它绑定，存在浏览器里
// 扩展：新增私密 token（云端存档的钥匙），并支持导出/导入「身份密令」做跨设备恢复
(function () {
  var KEY = 'lx_visitor_v1';
  var BEST = 'lx_best_v1';

  var XING = ['墨', '青', '听', '拾', '归', '云', '竹', '松', '雪', '南', '北', '长', '半', '闲', '砚', '茶', '沉', '香', '兰', '鹤'];
  var MING = ['竹', '雨', '月', '光', '山', '川', '风', '林', '湖', '舟', '隐', '游', '尘', '溪', '松', '棠', '卿', '白'];
  var HOU  = ['客', '翁', '生', '主', '人', '子', '君', '士', '者', '郎', '隐', '仙'];

  function pick(a) { return a[Math.floor(Math.random() * a.length)]; }
  function randHex(n) {
    var s = '';
    var buf;
    try { buf = new Uint8Array(n / 2); crypto.getRandomValues(buf); for (var i = 0; i < buf.length; i++) s += ('0' + buf[i].toString(16)).slice(-2); }
    catch (e) { for (var j = 0; j < n; j++) s += Math.floor(Math.random() * 16).toString(16); }
    return s;
  }

  function load() {
    var v = null;
    try { v = JSON.parse(localStorage.getItem(KEY)); } catch (e) {}
    if (!v || !v.name) {
      v = {
        name: pick(XING) + pick(MING) + pick(HOU),
        id: Math.floor(1000 + Math.random() * 9000),
        joinedAt: Date.now()
      };
      try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {}
    }
    if (!v.token) { v.token = randHex(32); try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} }
    return v;
  }

  var v = load();
  var best = {};
  try { best = JSON.parse(localStorage.getItem(BEST)) || {}; } catch (e) {}

  function getBest(game) { return best[game] || null; }

  // 记录成绩：higherBetter=true 越大越好（默认）；false 越小越好
  function record(game, score, opts) {
    opts = opts || {};
    var hb = opts.higherBetter !== false;
    var cur = best[game];
    var isNew = false;
    if (cur == null || (hb ? score > cur.score : score < cur.score)) {
      best[game] = { score: score, at: Date.now(), extra: opts.extra || null };
      isNew = true;
      try { localStorage.setItem(BEST, JSON.stringify(best)); } catch (e) {}
    }
    return isNew;
  }

  function fmt(game, opts) {
    var b = getBest(game);
    if (!b) return '暂无记录';
    var hb = !opts || opts.higherBetter !== false;
    var unit = (opts && opts.unit) || '';
    return (hb ? '最佳 ' : '最少 ') + b.score + unit;
  }

  function dateStr(ts) {
    var d = new Date(ts);
    return d.getFullYear() + ' 年 ' + (d.getMonth() + 1) + ' 月 ' + d.getDate() + ' 日';
  }

  // 导出身份密令（base64 的 id+token+name），用于跨设备恢复云端存档
  function exportCard() {
    try {
      var payload = JSON.stringify({ id: v.id, token: v.token, name: v.name });
      return '灵圃' + b64encode(payload);
    } catch (e) { return ''; }
  }
  // 导入身份密令：成功返回 true 并写入本地，失败返回 false
  function importCard(code) {
    if (!code) return false;
    code = ('' + code).trim();
    if (code.indexOf('灵圃') === 0) code = code.slice(2);
    try {
      var json = b64decode(code);
      var o = JSON.parse(json);
      if (!o || !o.id || !o.token) return false;
      v.id = o.id; v.token = o.token;
      if (o.name) v.name = o.name;
      try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {}
      return true;
    } catch (e) { return false; }
  }
  function b64encode(s) {
    if (typeof btoa === 'function') return btoa(unescape(encodeURIComponent(s)));
    return Buffer.from(s, 'utf-8').toString('base64');
  }
  function b64decode(s) {
    if (typeof atob === 'function') return decodeURIComponent(escape(atob(s)));
    return Buffer.from(s, 'base64').toString('utf-8');
  }

  window.Visitor = {
    get: function () { return v; },
    getBest: getBest,
    record: record,
    fmt: fmt,
    dateStr: dateStr,
    exportCard: exportCard,
    importCard: importCard
  };
})();
