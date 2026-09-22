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

---

## 五、给审计者的开工顺序（照做即可，别跳步）

1. `bash scripts/audit_regression.sh` —— 自动项一把梭（A + B 全跑）。
2. 打开本表 **第三节 C1–C6**，逐条人工过；**双主题截图**是硬要求。
3. 只改了某板块？仍要做 C1 全站双主题扫（同类 bug 常不止一处，2026-09-19 就是这样从 1 页查出 4 页）。
4. 本轮新发现/新修的问题 → **补进本表**（含日期/症状/文件/查法）。
5. 汇报时**明确写出**：自动项跑了哪些、人工项过了哪些、有没有新登记条目。
