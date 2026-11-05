// 云函数：代理 huiniao 彩票接口，返回某彩种「最新一期」开奖。
// 部署目标：腾讯云开发 CloudBase 环境 home-d8gmilku1b5963fce
// 形态：云函数「HTTP 访问服务」，路径 /lottery/latest
// 入参：?type=ssq|dlt|fc3d|pls
// 出参：{ type, i, d, r, b, live:true, cached?:true } 或错误对象
//
// 设计要点：
//  - 服务端调用第三方，密钥/源站不暴露给浏览器；
//  - 返回 CORS 头，允许 longxiong.vip 跨域 fetch；
//  - 60s 内存缓存，避免每次页面加载都打第三方；
//  - 范围校验，上游脏数据直接丢弃，绝不伪造；
//  - 出错返回 502 结构化错误，由前端回退到内置数据。

'use strict';

const https = require('https');

const API = 'https://api.huiniao.top/interface/home/lotteryHistory';
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36';

const TYPES = {
  ssq:  { api: 'ssq',  groups: [
    { key: 'r', fields: ['one', 'two', 'three', 'four', 'five', 'six'], lo: 1, hi: 33 },
    { key: 'b', fields: ['seven'], lo: 1, hi: 16 },
  ] },
  dlt:  { api: 'dlt',  groups: [
    { key: 'r', fields: ['one', 'two', 'three', 'four', 'five'], lo: 1, hi: 35 },
    { key: 'b', fields: ['six', 'seven'], lo: 1, hi: 12 },
  ] },
  fc3d: { api: 'fcsd', groups: [ { key: 'r', fields: ['one', 'two', 'three'], lo: 0, hi: 9 } ] },
  pls:  { api: 'pls',  groups: [ { key: 'r', fields: ['one', 'two', 'three'], lo: 0, hi: 9 } ] },
};

const CACHE_TTL = 60 * 1000;
let cache = { at: 0, map: {} };

function corsHeaders(origin) {
  const allowed = [
    'https://longxiong.vip',
    'http://localhost:8765', 'http://127.0.0.1:8765',
    'http://localhost:8199', 'http://127.0.0.1:8199',
  ];
  const allow = allowed.indexOf(origin) >= 0 ? origin : 'https://longxiong.vip';
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  };
}

function getQuery(event) {
  if (!event) return {};
  const qs = event.queryStringParameters || event.queryString;
  if (qs && typeof qs === 'object') return qs;
  if (typeof qs === 'string' && qs) {
    try { return Object.fromEntries(new URLSearchParams(qs)); } catch (e) { return {}; }
  }
  return {};
}

function fetchJSON(url) {
  return new Promise(function (resolve, reject) {
    const req = https.get(url, { headers: { 'User-Agent': UA, Accept: 'application/json' } }, function (res) {
      if (res.statusCode !== 200) { res.resume(); return reject(new Error('upstream ' + res.statusCode)); }
      let buf = '';
      res.setEncoding('utf8');
      res.on('data', function (c) { buf += c; });
      res.on('end', function () {
        try { resolve(JSON.parse(buf)); } catch (e) { reject(new Error('bad json')); }
      });
    });
    req.on('error', reject);
    req.setTimeout(8000, function () { req.destroy(new Error('timeout')); });
  });
}

function toInt(v) { const n = parseInt(v, 10); return isNaN(n) ? 0 : n; }

function latestOf(type) {
  const cfg = TYPES[type];
  if (!cfg) return Promise.reject(new Error('unknown type'));
  const url = API + '?type=' + cfg.api + '&page=1&limit=20';
  return fetchJSON(url).then(function (resp) {
    const inner = (resp && resp.data && resp.data.data) || {};
    const list = inner.list || (resp && resp.data && resp.data.list) || [];
    if (!list.length) throw new Error('empty list');
    // 取日期最大、同日取期号最大的一条（接口顺序不一定最新在前，防御处理）
    let best = list[0];
    for (let i = 1; i < list.length; i++) {
      const row = list[i];
      if (!row.day) continue;
      if (row.day > best.day || (row.day === best.day && String(row.code) > String(best.code))) best = row;
    }
    const g = {};
    for (const grp of cfg.groups) g[grp.key] = grp.fields.map(function (f) { return toInt(best[f]); });
    if (!g.b) g.b = [];
    // 范围校验：脏数据直接丢弃，绝不伪造
    for (const grp of cfg.groups) {
      for (const n of g[grp.key]) if (n < grp.lo || n > grp.hi) throw new Error('out of range');
    }
    return { type: type, i: String(best.code), d: best.day, r: g.r, b: g.b };
  });
}

function respond(statusCode, headers, body) {
  return { statusCode: statusCode, headers: headers, body: body };
}

exports.main = async function (event, context) {
  const origin = (event && event.headers && (event.headers.origin || event.headers.Origin)) || '';

  // CORS 预检
  if (event && (event.httpMethod === 'OPTIONS' || event.method === 'OPTIONS')) {
    return respond(204, corsHeaders(origin), '');
  }

  const q = getQuery(event);
  const type = String(q.type || '').toLowerCase();
  if (!TYPES[type]) {
    return respond(400, corsHeaders(origin), JSON.stringify({ error: 'unknown type', hint: 'type=ssq|dlt|fc3d|pls' }));
  }

  const now = Date.now();
  if (cache.map[type] && now - cache.at < CACHE_TTL) {
    return respond(200, corsHeaders(origin), JSON.stringify(Object.assign({}, cache.map[type], { live: true, cached: true })));
  }

  try {
    const data = await latestOf(type);
    cache.at = now;
    cache.map[type] = data;
    return respond(200, corsHeaders(origin), JSON.stringify(Object.assign({}, data, { live: true })));
  } catch (e) {
    return respond(502, corsHeaders(origin), JSON.stringify({ error: 'upstream failed', detail: String((e && e.message) || e) }));
  }
};
