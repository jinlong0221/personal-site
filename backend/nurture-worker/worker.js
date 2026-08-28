// 灵圃·沉香养成 —— 免费小后端（Cloudflare Workers + KV）
// 提供：私有存档云端备份/跨设备恢复、香道榜、访客晒图。
//
// 鉴权模型：每位访客身份 = { id(公开), token(私密) }。
//   - 私有存档 key:  n:<id>  = { token, state, updatedAt, name }
//   - 写：若已存在需 token 匹配；不存在则以其为首设 token
//   - 读：必须 token 匹配
//   - 公开档案 key: p:<id>  （由存档派生，供榜单/晒图署名，世界可读）
//   - 晒图列表 key: s:<id>  = [ entry, ... ]（发布需 token，读取世界可读）
// 说明：这是面向个人小站的「无登录」后端，安全边界是 token 不泄露。
//   不防蓄意伪造/作弊（存档为客户端可信），但隐私与跨设备同步目标已达成。

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('Origin') || '';
    const cors = corsHeaders(origin);

    // 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors });
    }

    const path = url.pathname;

    try {
      if (path === '/api/nurture/leaderboard' || path === '/api/nurture/leaderboard/') {
        const limit = clampInt(url.searchParams.get('limit'), 50, 1, 200);
        const data = await getLeaderboard(env, limit);
        return json(data, cors);
      }
      if (path === '/api/nurture/showcase' || path === '/api/nurture/showcase/') {
        const limit = clampInt(url.searchParams.get('limit'), 30, 1, 100);
        const data = await getShowcase(env, limit);
        return json(data, cors);
      }
      if (path === '/api/nurture/showcase/post' || path === '/api/nurture/showcase/post/') {
        if (request.method !== 'POST') return json({ ok: false, reason: 'method' }, cors, 405);
        const body = await readJSON(request);
        if (!body || !body.id || !body.token || !body.piece) {
          return json({ ok: false, reason: 'bad_request' }, cors, 400);
        }
        const res = await postShowcase(env, String(body.id), String(body.token), body.piece, body.caption || '');
        return json(res, cors);
      }
      if (path === '/api/nurture' || path === '/api/nurture/') {
        if (request.method === 'GET') {
          const id = url.searchParams.get('id') || '';
          const token = url.searchParams.get('token') || '';
          const rec = await loadPrivate(env, id, token);
          if (!rec) return json({ ok: false, reason: 'not_found' }, cors, 404);
          return json({ ok: true, state: rec.state, updatedAt: rec.updatedAt }, cors);
        }
        if (request.method === 'POST') {
          const body = await readJSON(request);
          if (!body || !body.id || !body.token || typeof body.state !== 'object') {
            return json({ ok: false, reason: 'bad_request' }, cors, 400);
          }
          if (body.token.length < 8 || body.token.length > 128) {
            return json({ ok: false, reason: 'bad_token' }, cors, 400);
          }
          const str = JSON.stringify(body.state);
          if (str.length > 200000) {
            return json({ ok: false, reason: 'too_large' }, cors, 413);
          }
          const res = await savePrivate(env, String(body.id), String(body.token), body.name || '', body.state);
          return json(res, cors);
        }
        return json({ ok: false, reason: 'method' }, cors, 405);
      }
      // —— 游艺成绩榜（公开排名，匿名雅号）——
      if (path === '/api/arcade/submit' || path === '/api/arcade/submit/') {
        if (request.method !== 'POST') return json({ ok: false, reason: 'method' }, cors, 405);
        const body = await readJSON(request);
        if (!body || !body.id || !body.token || typeof body.xiuwei !== 'number') {
          return json({ ok: false, reason: 'bad_request' }, cors, 400);
        }
        if (body.token.length < 8 || body.token.length > 128) {
          return json({ ok: false, reason: 'bad_token' }, cors, 400);
        }
        const res = await saveArcade(env, String(body.id), String(body.token), String(body.name || ''), Math.max(0, Math.floor(body.xiuwei)), String(body.rank || ''), body.scores || null);
        return json(res, cors);
      }
      if (path === '/api/arcade/rank' || path === '/api/arcade/rank/') {
        const limit = clampInt(url.searchParams.get('limit'), 20, 1, 100);
        const data = await getArcadeRank(env, limit);
        return json(data, cors);
      }
      // 根路径：状态
      if (path === '/' || path === '') {
        return json({ ok: true, service: 'longxiong-nurture', ts: Date.now() }, cors);
      }
      return json({ ok: false, reason: 'not_found' }, cors, 404);
    } catch (e) {
      return json({ ok: false, reason: 'server_error', detail: String(e && e.message || e) }, cors, 500);
    }
  }
};

// ---------- CORS ----------
const ALLOWED_ORIGINS = [
  'https://longxiong.vip',
  'http://localhost:1313', 'http://127.0.0.1:1313',
  'http://localhost:5173', 'http://127.0.0.1:5173',
  'http://localhost:8080', 'http://127.0.0.1:8080',
  'http://localhost:5500', 'http://127.0.0.1:5500'
];

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : (origin && /\.workers\.dev$/.test(origin) ? origin : 'null');
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin'
  };
}

function json(data, cors, status) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: Object.assign({ 'content-type': 'application/json; charset=utf-8' }, cors)
  });
}

async function readJSON(request) {
  try {
    const t = await request.text();
    if (!t) return null;
    return JSON.parse(t);
  } catch (e) {
    return null;
  }
}

function clampInt(v, def, min, max) {
  let n = parseInt(v, 10);
  if (isNaN(n)) return def;
  return Math.max(min, Math.min(max, n));
}

// ---------- 私有存档 ----------
async function loadPrivate(env, id, token) {
  if (!id || !token) return null;
  const raw = await env.NURTURE.get('n:' + id);
  if (!raw) return null;
  let rec;
  try { rec = JSON.parse(raw); } catch (e) { return null; }
  if (rec.token !== token) return null;
  return rec;
}

async function savePrivate(env, id, token, name, state) {
  const key = 'n:' + id;
  const existing = await env.NURTURE.get(key);
  let rec = null;
  if (existing) {
    try { rec = JSON.parse(existing); } catch (e) {}
    if (rec && rec.token && rec.token !== token) {
      return { ok: false, reason: 'auth' };
    }
  }
  const now = Date.now();
  rec = {
    token: token,
    name: (name || (rec && rec.name) || '').toString().slice(0, 40),
    state: state,
    updatedAt: now
  };
  await env.NURTURE.put(key, JSON.stringify(rec));

  // 派生公开档案
  const pub = derivePublic(id, rec.name, state, now);
  await env.NURTURE.put('p:' + id, JSON.stringify(pub));
  return { ok: true, updatedAt: now };
}

function derivePublic(id, name, state, now) {
  const total = state.totalHarvest || 0;
  const coll = Array.isArray(state.collection) ? state.collection.length : 0;
  const achv = state.achv ? Object.keys(state.achv).length : 0;
  return {
    id: String(id),
    name: (name || ('访客' + id)).toString().slice(0, 40),
    rank: rankOf(total),
    total: total,
    coll: coll,
    achv: achv,
    updatedAt: now
  };
}

function rankOf(total) {
  const R = [[0, '初学弟子'], [8, '香童'], [24, '香人'], [56, '香师'], [100, '香宗'], [200, '香圣']];
  let r = '初学弟子';
  for (const m of R) if (total >= m[0]) r = m[1];
  return r;
}

// ---------- 香道榜 ----------
async function getLeaderboard(env, limit) {
  const out = [];
  const list = await env.NURTURE.list({ prefix: 'p:' });
  for (const k of list.keys) {
    const raw = await env.NURTURE.get(k.name);
    if (!raw) continue;
    try { out.push(JSON.parse(raw)); } catch (e) {}
  }
  out.sort(function (a, b) {
    if (b.total !== a.total) return b.total - a.total;
    if (b.coll !== a.coll) return b.coll - a.coll;
    return b.achv - a.achv;
  });
  return { ok: true, list: out.slice(0, limit) };
}

// ---------- 晒图 ----------
async function postShowcase(env, id, token, piece, caption) {
  const rec = await loadPrivate(env, id, token);
  if (!rec) return { ok: false, reason: 'auth' };
  const key = 's:' + id;
  let arr = [];
  const raw = await env.NURTURE.get(key);
  if (raw) { try { arr = JSON.parse(raw); } catch (e) {} }
  const entry = {
    id: String(id),
    name: (rec.name || ('访客' + id)).toString().slice(0, 40),
    piece: sanitizePiece(piece),
    caption: String(caption || '').slice(0, 120),
    ts: Date.now()
  };
  arr.unshift(entry);
  if (arr.length > 20) arr = arr.slice(0, 20);
  await env.NURTURE.put(key, JSON.stringify(arr));
  return { ok: true };
}

function sanitizePiece(p) {
  if (!p || typeof p !== 'object') return null;
  return {
    type: String(p.type || '').slice(0, 12),
    grade: String(p.grade || '').slice(0, 12),
    weight: Math.max(0, Math.min(9999, Number(p.weight) || 0)),
    ageDays: Math.max(0, Math.min(99999, Number(p.ageDays) || 0))
  };
}

async function getShowcase(env, limit) {
  const out = [];
  const list = await env.NURTURE.list({ prefix: 's:' });
  for (const k of list.keys) {
    const raw = await env.NURTURE.get(k.name);
    if (!raw) continue;
    let arr;
    try { arr = JSON.parse(raw); } catch (e) { continue; }
    if (Array.isArray(arr)) for (const e of arr) out.push(e);
  }
  out.sort(function (a, b) { return (b.ts || 0) - (a.ts || 0); });
  return { ok: true, list: out.slice(0, limit) };
}

// ---------- 游艺成绩榜 ----------
async function saveArcade(env, id, token, name, xiuwei, rank, scores) {
  const key = 'a:' + id;
  const existing = await env.NURTURE.get(key);
  let rec = null;
  if (existing) {
    try { rec = JSON.parse(existing); } catch (e) {}
    if (rec && rec.token && rec.token !== token) {
      return { ok: false, reason: 'auth' };
    }
  }
  rec = {
    id: id,
    name: name.slice(0, 40),
    token: token,
    xiuwei: xiuwei,
    rank: rank,
    scores: scores,
    updatedAt: Date.now()
  };
  await env.NURTURE.put(key, JSON.stringify(rec));
  return { ok: true, updatedAt: rec.updatedAt };
}

async function getArcadeRank(env, limit) {
  const out = [];
  const list = await env.NURTURE.list({ prefix: 'a:' });
  for (const k of list.keys) {
    const raw = await env.NURTURE.get(k.name);
    if (!raw) continue;
    try {
      const r = JSON.parse(raw);
      out.push({ id: r.id, name: r.name, xiuwei: r.xiuwei || 0, rank: r.rank || '', updatedAt: r.updatedAt || 0 });
    } catch (e) {}
  }
  out.sort(function (a, b) { return (b.xiuwei || 0) - (a.xiuwei || 0); });
  return { ok: true, list: out.slice(0, limit) };
}
