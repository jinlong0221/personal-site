# 隐藏板块恢复预案（Runbook）

> 用途：当用户（龙兄）说"恢复隐藏板块"时，按本清单机械执行，避免漏改。
> 状态：8 个板块当前为**隐藏态**（不进搜索、任何页面不给入口，但 URL 仍可直接打开）。
> 隐藏板块：`guanghui`(光辉电力) `herbs`(中药材) `health-tea`(养生茶) `sheyang`(射阳)
>        `solar-terms`(节气) `typhoon`(台风) `xintan-weather`(新坍天气) `gaokao`(高考)

---

## 一、当前隐藏是怎么实现的（已核实 2026-10-12）

隐藏只靠**两道闸**，没有第三处：

| # | 机制 | 落点 | 验证方式 |
|---|------|------|----------|
| ① | 页面 `<body data-pagefind-ignore>` | 18 个静态页（8 个板块落地页 + herbs 9 个子页 + sheyang-guide.html） | `grep -rl "data-pagefind-ignore" static/` |
| ② | JSON 数据源不含隐藏板块条目 | `home-feed.json` / `hot-picks.json` / `feed.json` 等 | `grep -o "guanghui\|herbs\|..." static/home-feed.json` 返回空 |

**已确认无需处理**：
- 导航栏 `layouts/partials/navbar.html` 与 `static/categories.html` **不链**隐藏板块（无泄漏）。
- `scripts/` 构建脚本里**无**硬编码跳过隐藏板块的清单（恢复后可放心重跑构建器）。

> 注：早期曾在 `home-feed.js` 加过渲染层黑名单（HIDDEN_URL_HINTS 等），现已移除，
> 隐藏完全由 ①② 两道数据闸承担，反而更干净、更好恢复。

---

## 二、恢复步骤（按顺序）

### 步骤 1 — 解除搜索忽略（机制①，脚本自动）
```bash
cd hugo-site
python3 scripts/restore_hidden_boards.py          # 先 dry-run 预览 18 个文件
python3 scripts/restore_hidden_boards.py --apply  # 确认无误后真实移除 data-pagefind-ignore
```
脚本只动 `<body>` 标签里的 `data-pagefind-ignore`，不会误伤正文。

### 步骤 2 — 恢复 JSON 数据源条目（机制②，人工/半自动）
首页"今日更新 / 热门精选"要从 JSON 取数。需把隐藏板块条目写回：
- `static/home-feed.json`：补回各隐藏板块的"今日更新"条目（或直接重跑对应构建器，
  因 `scripts/` 无跳过清单，重跑会自动带出这些板块——前提是它们的 `-news.json` 源数据还在）。
- `static/hot-picks.json`：补回"光辉电力"等代表卡片（如曾删除）。
- `static/feed.json` / `data/feed.json`：补回台风等 link 条目（如曾删除）。
- 如首页渲染层（`scripts/js-src/home-feed.js` → `static/js/site-bundle.js`）有过滤逻辑，确认已无残留黑名单。

> 此步属**内容决策**：恢复哪些板块、放什么条目，由人定。脚本不替你改 JSON，避免恢复出半吊子状态。

### 步骤 3 — 重建索引 + 部署
```bash
hugo --gc --minify
npx pagefind --site public        # 重建搜索索引（pagefind 现在会收录这 18 页）
git add -A && git commit -m "restore: 恢复隐藏板块 X/Y/Z" && git push origin main
```
CI 跑通即上线。

### 步骤 4 — 验证（必须做，防漏）
1. `curl -s https://longxiong.vip/<板块>.html` 能正常打开。
2. 站内搜索（search.html）能搜到隐藏板块的内容。
3. 首页"今日更新 / 热门精选"出现对应板块条目。
4. 全站审计 `python3 scripts/audit_live_artifact.py --root public` 全绿。
5. `grep -rn "guanghui\|herbs\|..." static/ | grep -v "data-pagefind-ignore"` 确认入口已恢复、无遗漏。

---

## 三、再次隐藏（如需回滚）
反向执行：给 18 个页面 `<body>` 加回 `data-pagefind-ignore`，并从 JSON 移除条目，重建索引。
