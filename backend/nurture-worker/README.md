# 灵圃·沉香养成 · 免费小后端

Cloudflare Workers + KV 实现的零成本云端后端，给 `nurture.html`（灵圃·沉香养成）提供：

- **云端备份 / 跨设备恢复**：把你的沉香树存档存到云端，换手机/换浏览器不丢。
- **香道榜**：所有访客的香道等级、收藏数公开排行。
- **访客晒图**：把收藏阁里的某块沉香「晒」出来，带一句寄语，世界可读。

免费额度对这类小站绰绰有余（Workers 每日 10 万次请求、KV 免费档够用）。

## 部署（一次性）

需要：一个 Cloudflare 账号（邮箱注册即可，**无需信用卡**）。

```bash
# 1. 装 wrangler（本机已装 Node 即可）
npm i -g wrangler

# 2. 登录（浏览器授权）
wrangler login

# 3. 创建 KV 命名空间，把返回的 id 填进 wrangler.toml 的 REPLACE_WITH_KV_ID
wrangler kv namespace create NURTURE

# 4. 部署
wrangler deploy
```

部署成功后你会得到一个地址，形如：
`https://longxiong-nurture.<你的子域>.workers.dev`

## 把地址告诉前端

打开 `static/js/nurture/sync.js`，把顶部的：

```js
var API = 'https://longxiong-nurture.YOURSUB.workers.dev';
```

改成你真实的 Worker 地址，然后正常走站点构建三连即可
（`hugo --gc` → `compute_csp_hashes.py --inject` → `hugo --gc` → 推送）。

> 注意：`nurture.html` 的 CSP 已放行 `https://*.workers.dev` 的 `connect-src`，
> 所以跨域 `fetch` 不会被安全策略拦截。如需更严格，可改为只放行你的具体子域。

## 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/nurture/leaderboard?limit=50` | 香道榜（公开） |
| GET | `/api/nurture/showcase?limit=30` | 晒图列表（公开） |
| GET | `/api/nurture?id=ID&token=TOKEN` | 取回私有存档（需 token） |
| POST | `/api/nurture` | 保存私有存档 + 更新公开档案 |
| POST | `/api/nurture/showcase/post` | 发布一条晒图（需 token） |

## 鉴权与安全说明

- 每位访客身份 = `{ id(公开), token(私密) }`，token 在浏览器本地生成、从不上网明文展示。
- 私有存档读写都校验 token；token 不匹配一律拒。
- 存档为「客户端可信」：本站不防蓄意伪造/作弊（例如手改成长值刷榜），定位是个人备份与轻社交，非竞技反作弊。隐私与跨设备同步目标已达成。
- 跨设备恢复：在 A 设备用「导出身份卡」拿到密令，在 B 设备「导入身份卡」即可读回同一份云端存档。
