// =====================================================================
// Gitalk CORS 反向代理（Cloudflare Worker）
// ---------------------------------------------------------------------
// 作用: 浏览器不能直接跨域 POST https://github.com/login/oauth/access_token,
//        Gitalk 1.7.2 默认 proxy (cors-anywhere.azm.workers.dev) 已下线,
//        这里用 Cloudflare Worker 做 server-side 转发,顺便统一加 CORS 头。
//
// 协议 (与 Gitalk 1.7.2 src/gitalk.jsx 中 axiosJSON.post 协议保持一致):
//   入站 POST  application/json  body = { code, client_id, client_secret }
//   出站 POST  https://github.com/login/oauth/access_token
//        body = 原样转发
//        Accept: application/json
//   出站响应  application/json  透传 GitHub 的返回
//
// 安全:
//   - 仅允许 POST 跨域,GET/OPTIONS 仅做 CORS 预检
//   - Access-Control-Allow-Origin: *  (Gitalk 客户端不需要携带凭据)
//   - 不记录请求体/响应体(关闭 observability 即彻底无日志,见 wrangler.toml)
//
// 部署:
//   cd infra/gitalk-proxy && npx wrangler deploy
// =====================================================================

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400'
};

function jsonResponse (body, status) {
  return new Response(typeof body === 'string' ? body : JSON.stringify(body), {
    status: status || 200,
    headers: Object.assign(
      { 'Content-Type': 'application/json; charset=utf-8' },
      CORS_HEADERS
    )
  });
}

export default {
  async fetch (request) {
    // CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }
    if (request.method !== 'POST') {
      return jsonResponse({ error: 'method_not_allowed' }, 405);
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return jsonResponse({ error: 'invalid_json', detail: e.message }, 400);
    }
    if (!body || !body.code) {
      return jsonResponse({ error: 'missing_code' }, 400);
    }

    // server-to-server 调 GitHub,Accept: application/json 让 GitHub 返回 JSON
    let upstream;
    try {
      upstream = await fetch('https://github.com/login/oauth/access_token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'User-Agent': 'gitalk-proxy-longxiong (Cloudflare Worker)'
        },
        body: JSON.stringify({
          client_id: body.client_id,
          client_secret: body.client_secret,
          code: body.code
        })
      });
    } catch (e) {
      return jsonResponse({ error: 'upstream_fetch_failed', detail: e.message }, 502);
    }

    const text = await upstream.text();
    // GitHub 即使在 4xx/5xx 也可能返回 JSON 体的 error,这里透传
    return new Response(text, {
      status: upstream.status,
      headers: Object.assign(
        { 'Content-Type': 'application/json; charset=utf-8' },
        CORS_HEADERS
      )
    });
  }
};
