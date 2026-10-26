# longxiong.vip 项目记忆（2026-10-25 建立）

## 站点结构与红线（沿用，详见全局用户记忆）
- 源码在 `~/陈金龙/代码与脚本/个人知识网站/hugo-site/`，git  remote = jinlong0221/personal-site（main 分支，push 触发 CI 部署 gh-pages）。
- 权威 CSS = `hugo-site/static/css/style.css`（单文件，minified+可读混合）；页面级样式在各 `static/*.html` 的内联 `<style>` 块。
- 全站改动必须：changelog 三副本同步（scripts/add_changelog_entry.py）、`?v=` 日期戳随文件改动日 bump（guard_v_param 会提醒）、pre-commit 守卫不得 --no-verify。
- 禁 AI 生成图；移动端禁页面级横向滚动（容器内横滑放行，见 AUDIT_REGRESSION C5）。

## 天气聚合页生成器架构（2026-10-25 拆分，commit 9ad9fe43）
- `scripts/build_weather_hub.py` 现**产出两页**（用 `build_page()` 共享函数）：
  - `static/weather.html` = **本地实时天气专注页**（进入即定位访客所在城市显示实时天气；页面内一个醒目入口卡 + 导航「生活」分组可直达「射阳气象」；**不含**四合一内容）。
  - `static/sheyang-weather.html` = **四合一「射阳气象」页**（射阳实时+新坍农田+台风+节气；**不含**本地天气横幅 `#localWeather`）。
- **龙兄需求（本轮）**：点顶部天气功能键 → 只看访客自己当地天气；射阳本地气象单独放「旁边」（独立页 + 天气页内入口卡 + 生活分组入口）。
- **关键**：生成器 `read()` 从 `scripts/weather_sources/` 读取**合并前完整源页**，不再读 `static/`——因为 Task 14 把射阳/新坍天气/台风/节气四页在线态转成了跳转壳（`static/` 下已是壳，无 critical-css、无 `<main>` 正文）。`scripts/weather_sources/` 是**构建输入专用目录**，Hugo 不服务 scripts/，不会上线成独立页。
- 重新跑生成器前，必须保证 `scripts/weather_sources/` 四页完整（sheyang.html / xintan-weather.html / typhoon.html / solar-terms.html）；删了会崩溃。
- 两页都须含 A9 骨架（breadcrumb + page-meta + BY-NC + h1），否则部署被 A9 硬门拦。
- 三个跳转壳（`static/xintan-weather.html`、`typhoon.html`、`solar-terms.html`）的 meta refresh 已由 `weather.html` 改指向 `sheyang-weather.html`。
- ⚠️ `static/sheyang.html`（旧「射阳天气」页，非生成器源 `scripts/weather_sources/sheyang.html`）也是跳转壳，原 meta refresh 指向 `weather.html`（本地天气页，错）；2026-10-25 审计后改指向 `sheyang-weather.html`（commit 5bee4d5f）。`static/weather_sources/sheyang.html` 是生成器输入源，跟这个壳是两码事，别混。

## 天气页「定位到访客所在城市」功能（2026-10-25，commit 912b0224）
- **龙兄需求**：点顶部天气胶囊进 weather.html 后，应显示**访客自己当前所在位置**的天气，不是射阳。
- **实现**：新增 `static/js/geo-weather.js`（仅 weather.html 引入），进入页面即 `navigator.geolocation.getCurrentPosition` → 反查城市（**BigDataCloud** `reverse-geocode-client`，免 Key、CORS `*`）+ 拉实时天气（**Open-Meteo**，免 Key）；渲染顶部横幅「您当前位置 · 城市 · 温度 · 天气描述」。
- **胶囊升级**：`static/js/app.js` 天气 IIFE 改为「若 localStorage `lx_local_wx` 新鲜（≤30min）则优先显示用户城市，跳过射阳默认」。geo-weather.js 拿到定位后写 `lx_local_wx`，故**授权一次后全站胶囊都显示访客城市**。
- **反查地名用 `city`→`principalSubdivision`**：BigDataCloud 的 `locality` 返回繁体（如「黃浦區」），与全站简体不一致，故弃用 locality，只用 city/省级（简体）。
- **CSP**：`scripts/weather_sources/*.html` 的 `connect-src` 增 `https://api.bigdatacloud.net`（生成器合并用 sheyang 那份）。
- **拒绝授权兜底**：横幅显示「授权并查看我的天气」按钮，点击再 `getCurrentPosition`（用户手势，Safari 更稳）。
- ⚠️ **CI 关键事实**：`build_weather_hub.py` 与 `sync_navbar.py` **都不在 deploy.yml 里跑** → 两页以**提交态**直接上线。改天气内容必须先 `python3 scripts/build_weather_hub.py` 重新生成两页，再 `python3 scripts/sync_navbar.py` 把真实导航（含 `#navWeather` 胶囊）注回（生成器写出的是占位导航，无胶囊），然后提交。否则线上会丢胶囊。
- ⚠️ **胶囊文案/链接写死在 `scripts/sync_navbar.py` 的 `build_nav()`（约第151行），不是 `layouts/partials/navbar.html`**：`sync_navbar` 只从 navbar.html 解析下拉/抽屉/顶栏**列表**，胶囊本身在脚本里硬编码重建。改胶囊的 `title`/`aria-label`/`href` 必须改 `sync_navbar.py`，光改 navbar.html 不会生效（本轮踩过：改了 navbar.html 的胶囊文案，sync 后 unchanged=187，直到改 sync_navbar.py 才落全站）。导航「列表项」（如下拉新增「射阳气象」）才改 navbar.html。
- ⚠️ 本地测 geolocation 用 Playwright：`context.grant_permissions(['geolocation'])` + `context.set_geolocation({lat,lon})`；`localhost` 是安全上下文，无需 https 即可定位。

## iPhone Duo 折叠屏适配基线（2026-10-25）
- Duo 三视口：折叠外屏 466×678 / 展开内屏 626×890 / 横屏 890×626；折叠/展开由 CSS 媒体查询天然响应。
- 600–767px 是「展开态双列层」：`.lx-deck`/`.live-grid`/`.gl-people`（全局）+ `.works-grid`(zisha)/`.ahub-cards`(apple)/`.gh-partner-cards`(guanghui)（页面级）为双列；`.bracelet-grid.is-single` 是故意单列勿动。
- 回归工具：`~/.workbuddy/binaries/python/envs/playwright/bin/python3 scripts/audit_duo_viewports.py`（默认固定端口 8973，自建 /tmp/duo-public + 同端口 baseURL）。

## 本地预览/测试固定流程（避坑）
1. `hugo --minify --baseURL http://127.0.0.1:8973/ --destination /tmp/duo-public`（CSP `default-src 'self'` 会拦掉指向 longxiong.vip 的外链样式表，不用本地 baseURL 就会拿到「只剩 critical-css」的假渲染）。
2. 起服务跑 Playwright（用 `envs/playwright` 环境；`domcontentloaded` + `wait_for_timeout`，不用 networkidle）。
3. 后台自动化（二米等）会用生产 baseURL 重建 `public/`——测试构建放 /tmp，别放 public/；端口引用要同构建一致。

## CI-only 失败的复现方法（2026-10-25 踩坑，务必记住）
- **本地工作区 ≠ 干净检出**：本地工作区里**留着被 .gitignore 排除的文件**（如 `static/travel.html`、`static/img/travel/`、`static/data/travel.json`），CI 的干净检出里**没有**。所以「本地跑守卫全绿、CI 同一守卫 FAIL」是常态，别怀疑玄学。
- **复现姿势**：`git clone <本仓路径> /tmp/xxx && cd /tmp/xxx && git checkout <commit>`，再按 CI 顺序跑一遍那些会改 static 页的脚本，最后跑守卫。本轮两次 CI-only 失败都是这样定位的（一次是 travel.html 存在性误报，一次是 `build_ev_sales.py` 改坏导航）。
- **推论**：新增任何「会读 static/ 源文件」的守卫，必须在**干净 clone** 里验一遍才算数。

## 后台自动化并发现实
- 「二米·新闻补漏巡检·每3小时」等自动化会在本仓库并发跑（改 JSON、重建 public/、改文案），提交前先看 git status 里哪些不是自己的改动；其改动若自洽可同批提交并在 commit message 里注明。
- **pre-commit hook 会把工作区改动卷进自动化的提交**（hook 里 `git add changelog 三副本`）→ 会出现「我的 changelog 已进库、页面改动还没进库」。提交前先 `git log --oneline -1` 看 HEAD 是否被后台推进。
- **zsh 不做默认分词**：`for c in "cmd --flag"; do $c; done` 会把整串当一个命令名 → 静默全 FAIL。复刻 CI 步骤必须 `eval "$c"`。

## 文案「取其精华」规范与 A23 守卫（2026-10-25，龙兄定调）
- **定调原文**：「网站是做技术交流的，不是做文字表述的，所有各个板块要放取其精华的文字，让懂的人一看就懂，不喜欢各个板块的文字太多太浮肿。」
- **判据（scripts/guard_concise_copy.py = A23，已接 CI + audit_regression.sh）**：A 跨页重复正文段（≥40 中文字出现在 ≥5 页）/ B 口水话黑名单 / C 元叙述黑名单 / D 单段 >260 中文字。豁免：`.page-meta` 与「📌 资料说明」固定块、**跳转壳页**（meta refresh 或带「恢复方法：」注释）、**`static/changelog.html`**（台账天然要引用旧措辞，引用旧话不算浮肿）。
- **改写脚本**：`scripts/apply_concise_copy.py`（幂等，可复跑，改完自动清空 `<p>`）、`scripts/audit_text_bloat.py`（体检：各页正文体量 + 跨页重复段）。
- **原则**：只改「表达」不动「事实」——参数、发售日期、销量、价格、来源链接、免责声明的存在性一律保留；禁忌/口径类限定条件压缩保留，不删。
- 人工项见 `scripts/AUDIT_REGRESSION.md` **C12**（结论先行 / 取其精华抽查，脚本抓不了「这段值不值得留」）。
- ⚠️ **`scripts/build_game_pages.py` 已是陈旧生成器**：它的 `out.replace()` 目标串与现模板对不上（JSON-LD headline 早已被改成「…| 玩过的游戏2026实测避坑｜龙兄知识库」），实跑会**丢掉 `<!-- game:begin -->` marker / 「值不值得玩」块 / 全部截图**并留下 GTA6 的元数据。**别跑它**；要改游戏页直接改 `static/games/*.html`。跑任何 `build_*.py` 前先确认 replace 目标串还能命中。
- ⚠️ **`scripts/build_ev_sales.py` 会重写 `static/ev-sales.html`**（DONOR=ev-charge.html）：它只做「把 active 交给本页」，**不要**再往导航里插入口（DONOR 里已有「新能源销量榜」）。它改的是导航 active，故 `guard_nav_sync.py` 必须排在它**之后**跑。
- ⚠️ **`guard_nav_sync.py`（A22）2026-10-25 之前从未进过 CI**；现已补 `Guard nav consistency (after generators)` 步骤（deploy.yml，排在所有生成器之后）。**教训：凡「生成器会重写页面」的守卫，必须排在生成器之后**，否则抓不到生成器改坏的东西。

## 移动端提速基线（2026-10-25，commit 73f3802e）
- 全站 `<img>` 已包成 `<picture>`：≤600px 用 `@480w`、≤1000px 用 `@768w`、否则原图。缩略图已入库（`static/img/**/*@480w.webp` / `@768w.webp`，976 张）。
- 生成/注入脚本：`scripts/gen_responsive_images.py`（Pillow 生成，幂等）、`scripts/inject_responsive_img.py`（幂等包壳，无 Pillow 依赖）。**CI 必须在 `Build Hugo` 前跑 inject**（deploy.yml 已有该步骤），否则 build_marvel/chinajoy/travel 重写 static 页会把 `<picture>` 冲掉。
- 底部 `obfuscate-email.js` 全站改 `defer`（原为同步卡解析）。

## 「iOS 上点击没反应」根因模式与修复范式（2026-10-25）
- **根因**：iOS Safari 在 tap 伴随微小位移/页面滚动时会取消「合成的 click」→ document 上的 click 委托静默失效。桌面 Chromium（含移动视口模拟 + touch tap）复现不出来；本地 WebKit 不可用（http 被强制升 https）；safaridriver 需 GUI 授权。
- **修复范式**（static/js/app.js 区域K，已上线 bda43df7）：`data-act` 委托加 **touchend 兜底通道**（touch 序列 target 固定、100% 派发）+ **700ms 去重**（防 touch 与合成 click 各执行一次互相抵消）+ **touchmove 滚动豁免** + Enter/空格键盘触发 + init 自动补 `role=button/tabindex=0/aria-expanded`。以后遇到「仅 iOS 复现的点击问题」直接按此模式修，别在本地复现上耗时。
- 折叠卡片 CSS：`.home-collapsible-header` 已有 `touch-action:manipulation` + `:active` 反馈。
- 测试坑：`touchscreen.tap` 的坐标若在视口外会静默无效——tap 前必须 `scrollIntoView` 再取 rect。
- 全站 JS 事实：`static/js/site-bundle.js` 是 0 引用死文件（含旧版 toggleHomeSection，已同步修复防分叉）；`js/` 参考源目录已不存在，权威源就是 `static/js/`。

## 「脚趾抠地」App 状态（2026-10-25 龙兄宣布无限期搁置）
- 不再推进上架；本机工程 `/Users/chenjinlong/WorkBuddy/2026-08-21-18-02-13/SheSiArchive/` 原样保留。
- 网站侧已处置（commit 2a9c123b，已部署验证）：`static/shesi-landing.html`、`static/shesi-privacy.html`、`static/privacy.html` 三页已下线（原本是全站无入口孤岛、两份隐私政策重复、违反「App 资产不挂 longxiong.vip」约定）；线上三 URL 已 404，更新日志已记账。
- App 工程遗留引用（未动）：`ShareCardContentView.swift` 的 `landingBase` 硬编码 `https://longxiong.vip/shesi-landing.html`；APPSTORE_LAUNCH_CHECKLIST 等多份文档记着隐私页 URL——App 若重启，须独立托管并改这些引用。

## 「游戏发售日历」板块下线（2026-10-25 龙兄宣布未达预期、暂搁置）
- **现状态**：入口全撤，原 `static/game-calendar.html` 改为**跳转壳**（meta refresh→`games.html`、`noindex`、复用 weather.html 合规 CSP、无 `<nav>`）。内容留 git 历史，随时可恢复。
- **移除入口处**：`navbar.html`(2处)、`layouts/index.html`(首页卡片)、`content/categories/_index.md`、`build_content_index.py`(EXCLUDE+FILE_CAT)、`build_related.py`(EXCLUDE+FILE_BOARD+TOPIC_GROUPS)、`rebuild_sitemap_extra.py`(EXCLUDE+PRIORITY_RULES)、`build_weather_hub.py`+4 个 `weather_sources/*.html`(天气 hub 内链，否则重建回潮)、RSS(源 content-index 已剔)。
- **保留未动**（便于重启）：`scripts/fetch_game_covers.py`、`scripts/build_game_calendar_covers.py`、`static/img/games/` 真封面（CI 不调用这两脚本）。
- **恢复方法**：`git show 40bdf4f5^:static/game-calendar.html` 取回原页 → 反向上述入口改动 → 重跑生成链 → 加 changelog 条目。

## ⚠️ head.html 内联延迟加载器 CSP 哈希陷阱（2026-10-26 踩坑，必守）
- **现象**：往 head.html 那段内联延迟加载器脚本（含 `['js/lightbox.js','js/search.js',...].forEach(...)`、`requestIdleCallback(loadDeferred...)`）的数组里加新文件名 → 整段内联脚本被 strict CSP（`script-src` 无 `'unsafe-inline'`，白名单是 `sha256-...`）拦截 → `search.js`/`share.js`/`lightbox.js`/`changelog.js` **全不加载**，且任何想借它加载的新文件也失效。
- **根因**：CSP 内联白名单的 `sha256` 是对**渲染后**脚本内容算的，而该内联脚本含 `{{ .Site.BaseURL }}`（生产=https://longxiong.vip/），所以哈希绑定生产域名；内容一变（加文件名）哈希即失配。
- **铁律**：新增「延迟/空闲加载」的脚本**一律用外部 `<script defer src="...js/xxx.js?v=YYYYMMDD">` 标签**追加在 head.html（CSP `'self'` 放行外部同站脚本，无需哈希）。**绝不改那段内联延迟加载器。**
- **本地测试**：用 `--baseURL http://127.0.0.1:8973/` 构建，资源才与页面同源被 `'self'` 放行；延迟加载器内联脚本因哈希绑定生产域名，localhost 下恒被拦（search.js 等本地测不了，仅生产生效），属预期非 bug。

## ⚠️ 全局脚本必须带 ?v= 缓存戳（2026-10-26 铁律，源自顶部时钟/天气空白 bug）
- **根因级教训**：bump_v_hash.py 只处理源码里写成 `?v=YYYYMMDD` 的引用，裸 `js/app.js` 等会被它忽略 → 移动端按同 URL 缓存旧版、部署更新后也不刷新（2026-10-26 顶部时钟/天气胶囊在 iOS/Android 空白即此因）。
- **铁律**：任何全局 JS（app.js / interactions / search / share / bookmark / obfuscate-email / board-nav / 新增同类）在 static 页与 layouts 模板里的 `<script src>` 引用**必须带 `?v=YYYYMMDD`**（日期=该文件 git 最后改动日；bump_v_hash 部署时转内容哈希）。漏带戳＝埋移动端「改了跟没改一样」的地雷。
- 与「head.html 内联延迟加载器」铁律互不冲突：新脚本走外部 `<script defer src="...js/xxx.js?v=YYYYMMDD">`，内联延迟加载器数组仍不动。
- **审计带查项**：每次新增/改动全局脚本后，grep 全站确认其 `<script src>` 引用均已带 `?v=`；guard_v_param(致命) 只查「同资源 ?v 一致性+文件存在」，漏戳不会被 CI 拦（仅 WARNING），必须人工带查。
