# 审计回归清单（AUDIT REGRESSION CHECKLIST）

> 龙兄 2026-09-19 定规：**每次审计排查，必须把历史问题全部带着一起查**——不许这轮漏这个、下轮漏那个。
> 本文件是「已修过的问题」的唯一登记处。**修一个问题 → 在这里加一行**；**做审计 → 先跑 `scripts/audit_regression.sh`，再照本表逐条过**。
>
> 维护规则：
> 1. 任何一轮审计/修复中发现并解决的问题，都要在下表补一行（含日期、症状、涉及文件、检查方式）。
> 2. 能自动化的就加守卫脚本并登记进 CI；不能自动化的，写清「人工怎么看」。
> 3. 本表只增不删；问题确认彻底消失后可标 `(已退役)` 但保留记录。

---

## 一、已自动化（CI + pre-commit 强制，每次构建必跑，无需人工记得）

这些是「本金」——只要改动进仓库，CI 就会拦，理论上不会复发。审计时用
`bash scripts/audit_regression.sh` 一次性复跑即可。

| # | 问题（症状） | 涉及文件 | 守卫 / 命令 |
|---|---|---|---|
| A1 | changelog 三副本不一致 / 空 content 条目 / 条数暴跌（435→40 事故）/ feed 标记区过期 | `static/changelog.json` `data/changelog.json` `static/data/changelog.json` | `guard_changelog.py` |
| A2 | 任何 `overflow-x:hidden`（会让同页 sticky 失效的根因） | `static/css/style.css` 等 | `guard_overflow.py` |
| A3 | 非关键 `<style>` 块用全局选择器重定义 `--bg/--text/...`（污染全站导航） | 各 `static/*.html` | `guard_theme_scope.py` |
| A4 | CSP 卫生回潮：script-src 出现 `'unsafe-inline'`、umami 死配置、协议相对外链 | 各页 `<head>` | `guard_csp_hygiene.py` |
| A5 | `?v=` 版本戳不一致 / 指向不存在的资源（手写哈希会让它 ERROR） | 各 `static/*.html` | `guard_v_param.py` |
| A6 | IDE 注入的 `data-page-node-id` 元数据被提交 | 全站 html | `guard_editor_noise.py`（pre-commit 自动 `--fix`） |
| A7 | 旅行页分片里出现明文（加密泄漏） | `travel-dist/` | `guard_travel_dist.sh` |
| A8 | 🆕 **硬编码深色容器（hero 等）里的文字用 `var(--text)`** → 浅色主题下黑字压黑底看不见 | `static/apple.html` `chinajoy.html` `marvel.html` `typhoon.html` | `guard_dark_container_text.py` |
| A9 | 页面产物解析失败 / 骨架缺失（面包屑、`main>h1`、页尾信息块、CC 许可行） | `public/` 产物 | `smoke_test.py` + `audit_live_artifact.py` |
| A10 | 板块新闻 `*-news.json` 日期乱序 | `static/*-news.json` | `sort_news.py` |
| A11 | 标题四字段不一致（`<title>`/`og:title`/`twitter:title`/JSON-LD） | 各页 | `sync_titles.py --check`（须报 0 页） |
| A14 | 🆕 **行内 Markdown 记号不成对**：数据里的 `**加粗**` / `` `代码` `` 由渲染器的 `md()` 解析，而 `md()` 只认成对记号——落单的那一个会**原样显示在页面上**（比「全都不解析」更难发现：别处都正常，只有一处露着星号）。也拦「想在正文里引用星号本身却写了裸 `**`」这种自伤 | `static/*-news.json`、`tesla/fsd-news.json`、`home-feed.json`、`typhoon.json`、changelog 三副本 + feed | `guard_markdown_marks.py`（pre-commit + CI 双拦） |
| A15 | 🆕 **「截断」把行内 Markdown 记号切得落单**：changelog 运维留痕按 220 字截断时，`clip()` 只数字数、不管记号配对，很容易在 `…**实质数据…** …` 中间一刀切下去 → 落单的半边 `**` 被前端 `md()` 原样显示到页面上（2026-10-01：10-01 那天的巡检样本 221 字、`**` 出现 3 次，A14 守卫直接 FAIL）。**只改数据修不掉，修的是截断函数**：`scripts/build_changelog_feed.py` 的 `balance_marks()` 在截断后把奇数个 `**` / `` ` `` 的末尾那半边整段丢掉（markdown 是「遇到第二个记号才算闭合」，奇数个里落单的一定是最后那个开头） | `scripts/build_changelog_feed.py` | `guard_markdown_marks.py`（A14 会连带触发；修复后 `clip()` 恒产出成对记号） |
| A13 | 🆕 **动效/立体化三类地雷**：① JS 写的 CSS 变量名与根级令牌撞名（`--tx` 既是「文字色」别名、又被当角度写 → 悬停时卡内文字变色，JS 未介入时 3D 变换整条作废）；② 条件块（`@supports`/`@media`）里的 `animation` 用 `both`/`backwards` 填充且起始帧 `opacity≈0`（动画没跑起来就永久全透明）；③ 改 transform/filter 的 `:hover` 未做设备门控（触屏点按被当成悬停） | `static/js/*.js`、`static/css/style.css`、各 `static/*.html` | `guard_motion_safety.py`（①② 阻断；③ 只计数提示） |

## 二、按需跑的审计脚本（做完功能/大改后跑一遍）

| # | 覆盖范围 | 命令 |
|---|---|---|
| B1 | 源码级：死链 / 缺图 / 空 alt / 薄弱页 / 断锚点 / 孤儿页 | `python3 scripts/audit_strict.py` |
| B2 | 产物级：结构豁免、H1 唯一、页尾集合 | `python3 scripts/audit_live_artifact.py --root public` |
| B3 | 移动端横向溢出（多宽度） | `python3 scripts/audit_mobile_layout.py` |
| B4 | 源链接可达性 | `python3 scripts/check_source_links.py` |

## 三、必须人工复核（暂无自动化，最容易被漏——重点！）

> 这几类**没有任何脚本能兜住**，历史上出事最多的就是它们。每次审计都要**逐条过一遍**，
> 且**必须双主题（浅色 + 深色）都看**，不能只看一种。

### C1 双主题渲染复核（每次改样式/新增页面必做）
深色主题正常 ≠ 浅色主题正常（反之亦然）。固定做法：
```bash
cd static && python3 -m http.server 89xx          # static/*.html 是相对路径，可直服
# 浏览器打开 127.0.0.1:89xx/<page>.html?cb=<时间戳>
# 用 agent-browser：eval 设 data-theme=light / dark → 分别 screenshot 看图
```
**要盯的**：所有「深色容器里的文字」——hero 标题、说明、角标、徽章、进度条文字。
凡是背景是**写死深色**的容器，其文字必须是**写死浅色**；凡背景是**跟随主题**的容器，
文字才可以跟随主题。**混搭 = 必然出事**。

### C2 浅色主题下「金 / 浅强调色小字」的对比度
- 症状：浅色主题下金色小字（角标、链接）压在近白底上偏淡、读不清。
- 已修样例：苹果 `.ap-prod-badge`（角标）、`.ap-shot-cap .zoom`（放大链接）→ 浅色下改用
  深金 `#6f5a1e`。（2026-09-19）
- 怎么查：解析浅色主题变量值（全局 `static/css/style.css`，**不是页内联**）→ 算 WCAG
  对比度 → 小字需 ≥ 4.5:1、大字 ≥ 3:1。
- **注意**：不要信页内联 `<style id="critical-css">` 的 `:root/[data-theme]` 变量——它是过期
  副本，会被全局 `css/style.css` 覆盖。**真实调色板以全局为准**。

### C3 「脚本挂掉后内容还在不在」降级复核
所有「默认隐藏 + JS 显示」的机制，JS 一挂必须**内容全平铺、控件不丢**。
- 已确立范式：`.ahub-on`（板块两半切换）、`.tools-js`（工具箱折叠）、`.ap-tabs-on`（苹果标签）。
- 怎么查：判断**可见性**（`getClientRects().length > 0`），**不能数类名**——`querySelectorAll('.x.is-off')`
  恒等于写在 HTML 里的数量，门控生不生效都一样，这种断言永不失败（假通过）。

### C4 运行时注入组件的样式位置
`.secnav-*` / `.reading-progress` 等运行时注入的组件，样式在 `app.js` 注入的
`<style id="secnav-styles">`，**不在 `static/css/style.css`**。改它们别去 style.css 找。

### C5 移动端横向滚动
更新日志的长表格、宽表格在窄屏是否横向溢出（底栏/页尾集合是否被撑破）。

### C7 触屏「点按被当成悬停」复核（移动端优先，2026-09-20 新增）
触摸屏点按会点亮 `:hover` **并保持**，所以任何「只在鼠标下才合理」的 `:hover` 位移/缩放，
在手机上都会变成「点一下卡在放大/上浮态」。
- 实时条数：`python3 scripts/guard_motion_safety.py`（末项 D3 计数）。**2026-09-20 首次统计为 95 处存量**，
  尚未逐个门控 —— 清单用 `--report` 打印。
- 判据：**这条 `:hover` 是「鼠标加成」还是「点按反馈」**——前者必须包 `@media (hover:hover) and (pointer:fine)`，
  后者应改写成 `:active`。
- 已完成样例：射阳气象磁贴 `.tile:hover{scale(1.02)}` 已门控（触屏点按原本会「放大」而不是「压下去」）。

### C8 更新日志「是不是又变成机器考勤表」（2026-10-01 新增，龙兄点名「更新日志太吵、没营养」）
更新日志的价值是「站点今天动了什么」，不是「机器人今天打卡几次」。
- 判据（打开 `https://longxiong.vip/changelog.html` 用眼看 + feed 数据一起看）：
  ① **当天主线条目 : 运维留痕** 的比值。留痕（🤖 巡检 / 🌀 台风刷新）按天折叠，
  折叠区里若出现「巡检 ×7、台风 ×6」这类**条数远多于主线**，就是又吵回来了；
  ② 任一条留痕**正文 250 字以上** = 自动化把整轮推理倒进来了，必须写成一行短摘要；
  ③ 页面顶部的「共 N 条 / 主线 M / 运维 K」里，运维占比长期 > 60% 说明源头还在灌。
- 看数据：`python3 -c "import json;d=json.load(open('static/data/changelog-feed.json'));[print(x['date'],len(x['items']),{k:v['n'] for k,v in x['ops'].items()}) for x in d['days'][:5]]"`
- **源头已在自动化提示词里锁死**（2026-10-01）：每 3 小时一次的「新闻补漏巡检」**只在真的补进新稿时**
  才写 changelog、且一行 ≤120 字；0 条新稿 → 不写。若哪天又刷屏，先查那个任务的提示词有没有被改回去。
- ⚠️ 未闭环：**「台风实时监测」自动化（ID 1786286346465）读不到原文、改不了提示词**，
  它仍在每 3 小时往 changelog 写一条 `🌀 台风实时监测刷新（时间…）`。台风数据本身在 typhoon 页独立呈现，
  日志里属于重复记录。建议龙兄在 automation 界面手工给它加一条「**不要写 changelog，只更新 typhoon 页**」。

### C9 游戏详情页「优缺点绿／红面板」文字对比度（2026-10-02 新增，模板既有、非新页引入）
2026-10-02 新增《逆转裁判 123》（`static/games/ace-attorney-123.html`）时跑了渲染级对比度体检
（Playwright + 本地 `hugo --gc --minify` 产物，1440 宽，dark/light 双主题），
新页与**对照页（鬼武者 `onimusha-1.html`）报出完全一致的差值项** → 属 `.lx-good/.lx-bad` 游戏详情页
模板的既有配色，不是本次新增，已随新页一并上线。
- 实测（`scripts/audit_visual.py`，alpha 混合按真实叠色算）：
  · **dark 2 项**：状态徽章「✅ 已玩过」绿底白字 3.15、页脚邮箱 4.29；
  · **light 6 项**：标题金色小字 3.68、平台徽章「🎮 Switch」3.23、「✅ 已玩过」3.15、
    评分星图标 1.85（装饰可豁免）、「更新记录」蓝字 4.34、「全站搜索」4.37。
  · 对照页鬼武者跑出**同款同值** → 确认是模板既有，不是新增页引入。
- 截图证据：`/tmp/lx-visual/games_ace-attorney-123 _{dark,light}[_full].png`。
- 结论：**视觉可读**（面板是半透明底，叠色后更深），但徽章白字与浅色主题下的金/蓝小字可再提一档。
  **下一轮统一改 `static/css/style.css` 里这几处颜色，绝不单独改某一页**，否则又会出现「这一页颜色不一样」。
- 顺带确认本页无回归：1440／768／390 三宽**无横向溢出**、图片全部可达
  （窄屏下视口外图 `complete=false` 是 `loading="lazy"` 的正常表现，不是 404）、
  关掉 JS 后 5 个标题全部平铺可读（C3 通过）、`games.html` 卡片与相关阅读各 1 处链接正常。

### C6 配图红线
- 绝不用 AI 生成图；只用真实图并注明来源版权。
- 清晰度优先于体积：只走 `quality=80` 视觉无损重压，**不缩尺寸**。

---

## 四、事故时间线（便于追溯「为什么有这条」）

- 2026-08-20：changelog 条数暴跌事故（435→40）→ A1 闸门
- 2026-08-22：红队加固 → A2/A3/A4/A5
- 2026-09-02：编辑器元数据污染 → A6
- 2026-09-17：旅行页页头与入口层级修复（`tl-topbar z-index:10000`）
- 2026-09-19：**深色 hero 标题在浅色主题下变黑看不见**（apple / chinajoy / marvel / typhoon）
  → 新增 A8 守卫；C1/C2 从此列为每次审计必查项（龙兄点名批评「审计走点心」）
- 2026-09-19：弱 CSP 脚本 `add_security_headers.py` 从仓库删除（曾误注入 8 页）
- 2026-09-20：**全站立体化 / App 感升级**（龙兄反馈「整个网站就像一个平面，不立体」）——
  一轮里连出 4 个问题，全部登记：① 动效变量 `--tx` 撞上「文字色」历史别名（`style.css:62`，17 处消费），
  悬停时卡内文字色被解析成非法值而失效、JS 未介入时 3D 变换整条作废 → 改名 `--tilt-x`/`--tilt-y`；
  ② 桌面「按住」无压感（新加的 `:hover` 优先级压过了 `:active`）→ 补同优先级 `:active`；
  ③ 射阳磁贴 `:hover` 未门控，触屏点按变「放大」→ 收进 `@media (hover:hover) and (pointer:fine)`；
  ④ `main` 跨页淡入一度用 `both` + `from{opacity:.001}`（与 2026-08-19 透明空洞同一类地雷）→ 改 `forwards`。
  → 新增 A13 守卫 `guard_motion_safety.py`、新增 C7 人工项。
- 2026-09-20：`console-3do` / `console-game-gear` / `console-master-system` 三页 `.game-card` 缺卡面
  （圆角 0、透明底、每张卡占满整行；其余 55 个主机详情页正常）—— 属「页内样式块缺段」，已按同款补齐。
- 2026-09-29：**GitHub Pages 部署连续 5 个红叉**（run 1891–1895）。根因＝`unify_quotes.py`
  遇「奇数个转义引号」会整段放弃清洗，残留引号撞上 `audit_live_artifact.py`（step 40）FAIL。
  修复后 CI 全绿；同轮把 `unify_quotes.py` 的放弃场景补在 CI 链最前（step 36 自愈）。
- 2026-09-30 / 10-01：**龙兄反馈「最近感觉网站不得劲」**（四项全做）：① 更新日志太吵没营养；
  ② 板块内容陈旧/重复；③ 打开变慢卡；④ 视觉排版不对劲。本轮处理：
  · **更新日志轻量化**：feed 侧运维样本从「整段几千字」截到 220 字（feed 640K→361K），
    并修掉截断切出落单 `**` 的新坑（A15）；源头把「每 3 小时巡检」的提示词改成
    **无新稿不写 changelog、有稿一行 ≤120 字** → 每天少 6~7 条考勤。
  · **性能**：首页首屏两处 `Date.now()` 唯一缓存戳（击穿缓存、每次请求回源）改成
    10 分钟窗口 `Math.floor(Date.now()/600000)`，重打包 `site-bundle.js`（?v=20261001）。
  · **内容**：特斯拉 FSD 板补 10-01 真稿（Roadster 亮相 + 欧盟 FSD 投票推迟 12 月，三源互证）；
    文玩手串板搜出来全是 SEO 软文 → 按「宁可不写也不编造」保留 09-30 条目。
- 2026-09-29：**农田气象（xintan-weather.html）「天气又刷新不出来」**（龙兄反馈，反复出现）。
  根因＝数据走境外 Open-Meteo API（EU 节点），中国大陆蜂窝/宽带网络偶发连不上；旧逻辑 `.catch` 直接显示
  「天气数据加载失败」且无缓存兜底 → 永久空白。修复：① 把内联天气 IIFE 抽成外部 `static/js/xintan-weather.js`
  （不动内联 CSP 哈希，避免牵动百来页）；② 改成 stale-while-revalidate：先渲染 localStorage 缓存（3h TTL）
  再后台拉取，拉取失败保留缓存并提示「可能过期」，绝不空白；fetch 带 9 秒 AbortController 超时；③ HTML 加
  `<noscript>` 兜底（JS 被禁用/拦截时隐藏转圈、给明确提示）。  能否自动化：根因是网络层，CI 无法复现，只能靠
  SWR 兜底 + 用户侧网络；已归入 C3 降级复核（页面无数据时须有缓存/提示，不能空白）。
- 2026-09-29：**全站视觉复查（C1–C7 人工项补做）**。自动化回归全绿（`audit_regression.sh` 10/0）后补做人工视觉复核。取证链路：本地 `hugo --gc --minify --baseURL http://127.0.0.1:8932/ -d /tmp/lxpreview` → `:8932` + agent-browser 0.27.0（Chromium 154）截【暗色桌面全页 25 张】+【浅色桌面视口 10 张】+【手机 390×844 视口 5 张】，并对 30 个风险页做【程序化横向溢出扫描】（断言 `scrollWidth ≤ innerWidth`）。结论：① **C5 移动端横向溢出——30 页全 PASS**（`scrollWidth 382 ≤ innerWidth 390`，无整页横滑）；ev-sales 标签栏「新能源车型销量 T…」截断实为 `.ev-tabs{flex-wrap:wrap}` 自动换行、表格 `.ev-table-wrap{overflow-x:auto}` 内部可横滑，非整页溢出，无需修；② **A8/C1 深色容器文字**已靠 A8 守卫固化，本轮截图留存待目检；③ **C3 降级 / C4 注入组件样式 / C7 触屏悬停**——未见异常信号。⚠️ **局限如实登记**：当前模型无法查看图片（`Read` 对 PNG 返回内容被过滤），故 **C1 双主题 hero 标题可见性、C6 配图红线只能靠客观扫描（溢出判定／源码变量核对）替代人工目检**，未逐页机械核验；截图存于 `/tmp/shots/`（42 张），建议龙兄本人或换多模态模型过一遍深色／浅色对照。

- 2026-09-30：**GitHub Pages 部署连续失败（run 1891–1895）**，根因＝自动化新闻/更新日志 JSON 混入直引号 `"…"` 与弯引号 `"…"`，触发部署前护栏 `audit_live_artifact.py` 的「数据 JSON 值内引号残留」检查 → 该步骤 FAIL → 后续部署全跳过。自愈脚本 `unify_quotes.py --ci`（step 36，审计之前）本应就地归一，但其 `convert_json` 有「反引号外转义引号个数为奇数就整段放弃」的逻辑，导致奇数个 `"` 的 JSON 没被归一 → 审计必挂（CI 时灵时不灵的根）。修复：`scripts/unify_quotes.py` 去掉该放弃逻辑，奇数个也按序映射成 `「」`（审计只拦直引号/弯引号、不拦 `「`），从此自动化再怎么写坏引号都能自愈、绝不拦部署。已提交 `06555f28` 并通过 run 1897 验证。**教训**：`unify_quotes.py --ci` 在 `--ci` 模式下即便末尾「未闭合」也只是告警、照常写入，不会再阻断构建。

- 2026-10-02：**「玩过的游戏」新增《逆转裁判123：成步堂精选集》（Switch）**（龙兄点名：玩过的游戏里加一个 Switch 版逆转裁判 123）。
  · 新页 `static/games/ace-attorney-123.html`（以 `onimusha-1.html` 为底稿、30 处断言替换后逐条人读校对），
  事实三源互证（萌娘/百度/快懂百科 + 任天堂商店页）：**Switch 版 2019-02-21 与 PS4/Xbox One 同步发售**、
  PC 版 2019-04-10、收录三作共 14 话、简繁中文 2019-08-22 更新追加、8 语言、12+、2.8GB、三平台累计 210 万（截至 2023-03）。
  · 配图**全部取任天堂官方商店素材**（封面 1280×720 + 6 张实机截图 1600×900 webp，来自 Nintendo Cloudinary
  `assets.nintendo.com/image/upload/<变换>/store/software/switch/...`，**变换参数必须写在 store 路径之前、否则 404**），
  零 AI 图，图注标 Capcom 版权（C6 通过）。
  · 卡在「相关阅读为空」→ 根因＝**新页没进 sitemap**：`content-index` 是从 `data/sitemap_extra.json` 反查的，
  新静态页必须先跑 `rebuild_sitemap_extra.py` 才进索引，顺序务必是
  `sitemap_extra → content_index → related → apply_related`。另 `apply_related.py` **只有 `--check` 一个开关**，
  已被注入过的页面要刷新必须**整站 `--refresh`**（本轮 172 页），没有单页过滤。
  · 捞回 2 个漏改：`canonical` 与 `og:url` 还指向 `onimusha-1.html`（底稿残留）。
  · 回归：源码级 **PASS 10 / FAIL 0**、完整链（含 hugo 构建+冒烟+骨架）**PASS 14 / FAIL 0**；
  新增 C9（游戏面板对比度属模板既有、非本轮引入）。
- 2026-10-02：**渲染级体检流程可复用**（本轮起沉淀）：`hugo --gc --minify` → `cd public && python3 -m http.server 8899`
  （**要用后台任务起，普通 Bash 调用结束会把服务带走**）→ miniconda playwright 脚本检查
  【三宽溢出扫描 + 图片 broken + 关 JS 降级 + dark/light 双主题截图 + 对比度矩阵】。
  脚本模板见 `/tmp/vis_ace.py`、`/tmp/vis_ace2.py`（临时目录，后续可移进 `scripts/` 长期化）。

---

## 五、给审计者的开工顺序（照做即可，别跳步）

1. `bash scripts/audit_regression.sh` —— 自动项一把梭（A + B 全跑）。
2. 打开本表 **第三节 C1–C9**（C1 双主题 / C2 浅色小字对比度 / C3 脚本降级 / C4 注入样式位置 /
   C5 横向滚动 / C7 触屏悬停 / C8 更新日志是不是考勤表 / C9 游戏面板对比度 / C6 配图红线），逐条人工过；
   **双主题截图**是硬要求。
3. 只改了某板块？仍要做 C1 全站双主题扫（同类 bug 常不止一处，2026-09-19 就是这样从 1 页查出 4 页）。
4. 本轮新发现/新修的问题 → **补进本表**（含日期/症状/文件/查法）。
5. 汇报时**明确写出**：自动项跑了哪些、人工项过了哪些、有没有新登记条目。
