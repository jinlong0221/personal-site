# gitalk-proxy

替换已下线的 Gitalk 默认 CORS proxy (`cors-anywhere.azm.workers.dev`)。

## 工作原理

```
浏览器 (longxiong.vip)
  │  POST application/json  {code, client_id, client_secret}
  ▼
Cloudflare Worker (本仓库 src/index.js)
  │  server-to-server POST  https://github.com/login/oauth/access_token
  ▼
GitHub OAuth Token Endpoint
  │  application/json
  ▼
Cloudflare Worker (加 CORS 头)
  │  application/json
  ▼
浏览器 (Gitalk 拿到 access_token)
```

## 部署(首次)

需要一次 Cloudflare 账户授权:

```bash
cd infra/gitalk-proxy
npx wrangler login          # 浏览器跳 CF 授权页,选账号
npx wrangler deploy          # 部署,输出形如 https://gitalk-proxy.<subdomain>.workers.dev
```

部署后把输出的 URL 填到 `static/js/gitalk-init.js` 的 `GITALK_CONFIG.proxy`,并把 OAuth App 的
Authorization callback URL 改为 `https://longxiong.vip/oauth-callback.html`。

## 后续更新

```bash
cd infra/gitalk-proxy
npx wrangler deploy
```

## 配 OAuth App

GitHub → Settings → Developer settings → OAuth Apps → 选 longxiong →
Authorization callback URL 改为 `https://longxiong.vip/oauth-callback.html`。
