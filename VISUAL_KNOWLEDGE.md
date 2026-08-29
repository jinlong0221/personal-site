# 视觉美化知识库（托尼·视觉美化官专属）

> 本文件由【托尼·视觉美化官】在每周二 04:00 周巡检时持续学习、增量刷新。
> 仅作运营知识储备，**不进 public 部署**（Hugo 只构建 content/ 与 static/，根目录散落文件不会被发布）。

## 一、本站设计系统要点（国风黑金）

- **主调**：国风 + 黑金。深色为默认 `:root`，浅色 `[data-theme="light"]` 通过主题切换。
- **主题变量**（在 `static/css/style.css` / 根副本 `css/style.css`）：
  - `--accent-color: #C9A84C`（金，全站主强调色，所有强调/卡片顶条/印章/图标统一用它驱动）
  - `--gold`、`--cinnabar`（朱砂红，点缀用，不可大面积）
  - `--bg` / `--card` / `--border-color` / `--text-color`（明暗双主题各一套）
- **明暗双主题切换**：通过 `data-theme` 属性 + CSS 变量覆盖实现；切换逻辑在主题脚本。
- **`.lx-*` 卡片体系**：`.lx-card`（分类入口卡）、`.lx-epick`（本周精选卡）、`.lx-card-top`、`.lx-card-ico`、`.lx-card-seal`、`.artist-card`（紫砂艺术家卡）等，是全站统一组件，新增视觉须复用而非另起。
- **国风元素**：SVG 印章、毛笔字标题、纯色块分隔。使用须克制，避免与暗色金调冲突。

## 二、配色与对比度规范

- 全站强调色一律走 `--accent-color`（金），**严禁 inline 彩虹色残留**（此前首页分类卡曾硬编码蓝/金/朱砂/红，已统一修复）。
- **暖色刺眼红线**：黄/金/棕大面积高饱和背景或文字会刺眼，龙兄明确反感；金只作强调，不作大面积底色。
- 深色底（--bg）配金（--accent-color）需保证正文可读性；浅色主题下金色的对比度边界要复核。
- **暖色刺眼判定（P0 红线）**：须同时满足「大面积（整屏 hero / 通栏区块）+ 高饱和（纯红/橙/琥珀/亮金 `#ff6f00`·`#ffb300`·`#e65100` 级）+ 暖色相」才判刺眼；小尺寸语义色块（季节卡、板块色条、品牌徽标、警告框低透明度 tint）属合理分类编码，不在此列。判定顺序：**先量面积、再量饱和度**，勿见暖色即改。
- **国风黑金 hero 标准做法**：墨底渐变（`var(--bg-secondary)→var(--card)`）+ 金顶边（`border-top:3px solid var(--accent-color)`）+ 金标题（`color:var(--accent-color)`）；如需一点朱红，用 `radial-gradient(circle,var(--cinnabar-soft),transparent 70%)` 作低饱和印章微光，**绝不**堆高饱和暖色渐变（红→橙→琥珀是典型反面）。

## 三、响应式与移动端美学

- **safe-area 补偿**：navbar 实际高度含 `env(safe-area-inset-top)`；同级 fixed/sticky 元素 `top` 须加同名 `@supports` 补偿，否则刘海屏会把内容插进导航栏下半部。
- **全局触控区规则**：站点有 `button,.btn,…{min-width:44px;min-height:44px}` 全局规则；自定义小尺寸按钮（hero indicator、小图标按钮）必须显式 `min-width:0;min-height:0` 覆盖。
- **避免横向滚动**：移动端正文与表格须在视口宽度内完整可读，不出现横向滑动（更新日志/表格尤需当心）。
- **flex 中文防缩爆**：flex 行内嵌长副标题须 `flex-wrap:wrap` + 文本子项 `min-width:0` + `≤560px flex:1 1 100%`。
- **sticky 失效根因**：`body{overflow-x:hidden}` 会导致 sticky 永不吸附 → 改 `overflow-x:clip`。

## 四、视觉 glitch 修复范式

- **遮挡/空洞/溢出/错位/z-index 异常**：多用 `position:fixed/sticky` 的导航与悬浮组件易冲突，改前先查祖先链。
- **隐藏机制铁律**：「初始隐藏 + JS 触发显示」必须保证 JS 失效默认可见——`.js .reveal` 前缀 + head 注入 `<script>document.documentElement.classList.add('js')</script>`；**首屏绝不挂 reveal**。
- **本地验证坑**：head.html 写线上绝对 URL + CSP 会导致本地 CSS 静默不加载；验证需去 CSP、资源本地化到 `_verify.html`（puppeteer + python http.server）。

## 五、外部可借鉴规范（持续补充）

- Web 排版系统：模块化比例、留白尺度、栅格基线。
- 可访问性（a11y）美学：对比度 AA 阈值、焦点可见性、语义结构。
- 当代国风 / 暗色 UI 设计趋势：低饱和金、墨黑底、留白呼吸感。

## 六、本站踩过的视觉坑（复盘池）

- 首页分类卡/精选卡曾硬编码彩虹色破坏主调 → 已统一为 `--accent-color` 驱动（commit `b83c791` 前序审计）。
- `body{overflow-x:hidden}` 致 sticky 失效 → 改 `overflow-x:clip`。
- 刘海屏 safe-area 缺失导致内容插入导航栏下半部 → 同级 fixed/sticky 补 `@supports` 补偿。
- 全局 44px 触控规则入侵自定义小按钮 → 显式 `min-width:0;min-height:0` 覆盖。
- 高考页 `.gk-hero` 曾用 `linear-gradient(135deg,#e53935,#ff6f00,#ffb300)` 整屏红橙琥珀高饱和渐变 → 大面积暖色刺眼、违国风黑金；2026-08-25 巡检改为墨底+金顶边+金标题+朱红微光（见上「国风黑金 hero 标准做法」）。
- **子页内联 `:root` 被外部 `style.css` 覆盖（2026-08-26 发现）**：各 static 子页自带 `<style id="critical-css">` 内联 `:root{--bg:#0f0f0f…}`（偏冷灰），但因随后 `<link rel="stylesheet" href="css/style.css">` 加载更晚、同特异性，外部 `:root`（`--bg:#12100C` 国风墨黑）胜出 → 子页正确继承站点基色（实测 15 页均解析为 `bg=rgb(18,16,12)`）。⚠️ 例外：若子页在外部 link **之后**还有第二段 `<style>` 并重定义 `:root`（如 `sheyang.html` 第 115 行后、`games.html`），该第二段胜出 → 基色漂移（sheyang→`rgb(10,10,10)` 冷黑；games→`rgb(13,13,26)` 蓝黑）。二者均自巡检 `944bf85` 前已存在、属既定"板块主题色"被接受，**勿盲改**（无图难验、易引入回归），本巡检仅记录为已知项。

## 七、无头浏览器验证方法论（托尼自用）

模型无法读图，用 puppeteer-core + Chrome for Testing 做 DOM 实测替代"看见"：

- **本地构建必须改 baseURL**：`hugo --gc --baseURL "http://127.0.0.1:8199/" --destination /tmp/lx-pub`，否则线上绝对 URL 在本地 404。head.html 的 meta CSP `style-src 'self' 'unsafe-inline'` 在同源(localhost)下放行内联样式与同域 CSS，无需去 CSP、无需改资源本地化。
- **横向溢出双指标**（html `overflow-x:hidden` 会裁剪掩盖，单信 scrollWidth 会漏报）：
  1. 文档级 `document.documentElement.scrollWidth - window.innerWidth` 须 = 0；
  2. "伸出视口"元素扫描：遍历 `*`，取 `getBoundingClientRect()`，`rect.right > innerWidth+1.5` 且不在 `overflow-x:auto/scroll` 祖先内部者 = 视觉溢出。后者能抓被 html clip 掉的裁切内容，比前者更可靠。
- **遍历规模**：197 页 × 5 视口(390/375/360/1440/1920) × 2 主题 ≈ 1970 次加载，单进程约 12–20 分钟；务必后台跑、勿前台阻塞。
- **undefined CSS 变量扫描坑**：只扫 `style.css` 会大量误报（页面内联 `<style>` 与 pagefind 自带 CSS 也定义了 `--xxx`）。正确做法：从「全部 .css + 全部 html 内联 `<style>` + JS `setProperty`」收集定义，再比对 `var()` 用法，并过滤带 fallback 的 `var(--x, 默认值)`。
- **⚠️ 2026-08-29 扫描 refinement（必看，否则误报）**：定义收集源**还须包含内联 `style="--x:值"` 属性里的自定义属性**。chinajoy.html 的 `.cj-hall-card` 用 `style="--hall:#4f46e5"` 逐卡片定义、在 `.cj-tag-hall`/`.cj-hall-card` 内 `var(--hall)` 引用——若只扫 `:root`/`<style>`/`setProperty` 会误报 10 处「未定义」。完整定义源 = `.css` + html 内联 `<style>` + **html 内联 `style="--x:.."` 属性** + JS `setProperty`。本周全站 34951 处 `var()` / 161 定义，真实未定义 = 0。
- **2026-08-30 复盘：`--cf-top` 是「JS 运行时 setProperty」典型安全范式**：`console.html` 用 `document.documentElement.style.setProperty('--cf-top', h+'px')` 在运行时写入、引用处 `var(--cf-top, 56px)` 带 56px fallback。扫描器在静态源码里看不到定义会误报「未定义」，但它运行时必被赋值、且 fallback 兜底 → **非缺陷**。结论：凡 `var(--x, <默认值>)` 带 fallback 且由 `setProperty` 运行时填充的，一律按「安全、不计入未定义」。
- **2026-08-30 补漏：元素伸出视口的「祖先裁剪」误报陷阱（P0 判定关键）**：仅测 `rect.right > innerWidth` 会把**预期内的横向滚动容器后代**也标成溢出——本站实测 43 页出现 `over` 标记，但全部是：① 主机页 `.timeline-dot`/`.tl-year`（时间轴装饰点，父级 `.timeline` 已 overflow 裁切）；② 特斯拉页 `.version-tag`（表格内小标签，父级 `.table-wrapper` overflow-x:auto）；③ `xintan-weather.html` 的 `.xw-h-*`（逐时天气横滑行，本就 intended 横滑）；④ 首页 `.lx-vchip`（活体首页横滑胶囊，intended）。**正确 P0 判定 = 文档级 `docOverflow==0` 为硬闸门，元素扫描须向上遍历祖先，凡祖先含 `overflow-x:auto/scroll/hidden/clip` 即视为「已收纳」，不计入真实溢出**。本周用祖先感知重扫 43 页 → 真实元素溢出 = 0。
- **safe-area / sticky 用代码审查而非截图**：grep `position:sticky` 找所有 `top:var(--nav-height)` 元素，确认每个都在 `@supports(padding:env(safe-area-inset-top))` 内补 `top:calc(var(--nav-height)+env(safe-area-inset-top))`；并确认 body 是 `overflow-x:clip`（非 hidden），sticky 才能以视口为滚动祖先。

## 八、CSP × 视觉渲染关系（2026-08-26 复盘）

本站 CSP（head.html meta，经安全加固）：
`default-src 'self'; script-src 'self' + 约 47 个 sha256 白名单; style-src 'self' 'unsafe-inline' + gitalk CDN; img-src 'self' data: + 二维码/头像源; …`。

- **关键结论**：`style-src` 含 `'unsafe-inline'` → **内联 `<style>` 与 `style="…"` 属性全部放行**。全站 181 页 / 2704 处 inline style 正常渲染，不受 `default-src 'self'` 影响。⚠️ 勿误判"default-src 'self' 会封杀内联样式"——必须先 `grep -oE "(style-src|style-src-attr)[^;]*"` 确认有无 `style-src` 指令再下结论。
- **script-src 已去 'unsafe-inline'**，改用 sha256 白名单（约 47 个哈希）。`scripts/verify_csp_headless.cjs` 全量 194 页扫描 → **0 处 script-src 拒绝**，说明主题切换脚本、`document.documentElement.classList.add('js')` 等内联脚本均被正确哈希放行。
- **对托尼巡检的影响**：
  1. 内联样式正常 → 视觉继承/卡片/暖色判定与加固前一致，无系统性回归。
  2. 主题脚本被放行 → `data-theme` 正常设置，明暗双主题均按设计渲染；`.js` 类正常注入 → `.js .reveal{opacity:0}` 生效（首屏无 reveal，安全）。
  3. 无头实测时用 `page.evaluateOnNewDocument(()=>localStorage.setItem('theme',T))` 强制主题，绕过渲染时序差异，数据更稳。

## 九、协调探针：子页基色继承客观验证（2026-08-26 新增）

不依赖读图，用 puppeteer 对样本子页读取 computed token，客观判定"子页是否像另一个站"：

- **读取值**：`getComputedStyle(document.body).backgroundColor` + `getComputedStyle(document.documentElement).getPropertyValue('--accent-color' / '--card' / '--nav-height')`。
- **2026-08-26 抽样 15 页**（台风/主机/中药材/紫砂/漫威/旅行/游戏/射阳/健康茶/ChinaJoy/特斯拉/手办/关于/万年历/bracelet）→ 全部解析为 `bg=rgb(18, 16, 12)`（国风墨黑）、`accent=#C9A84C`（金）、`card=#1C1711` → **子页继承国风黑金设计语言、金主调一致**。
- **唯一漂移**：`sheyang.html`(`rgb(10,10,10)` 冷黑)、`games.html`(`rgb(13,13,26)` 蓝黑) — 见第六节，属既定板块主题色、已知接受。
- **此法价值**：把"协调性"从主观读图转为可量化指标（基色 token 一致性），适合无图环境每周复验。
- **2026-08-28 复验规模**：站点已 197 页（较 08-25 的 194 页 +3），新增 3 页均为「脚趾抠地」App 独立品牌页（见第六节），基色协调探针抽样仍全绿、金主调一致。
- **2026-08-29 复验规模**：站点已 199 页（较 08-28 的 197 页 +2）。新增：① commit `39901d8e` 首页「今时·节气 / 每日一物 / 站长手记」活起来带（gold 驱动、复用 .lx-mod 卡片体系、无 reveal 隐藏、JS 失效有静态兜底文案）；② 小米 新增 `offline.html`（PWA 离线兜底页，系统页）。基色协调探针仍全绿、金主调一致。
- **2026-08-30 复验**：站点仍为 199 页；本轮以 docOverflow/祖先感知元素溢出硬指标为主，协调探针结论延续（国风墨黑基色 + 金主调一致、sheyang/games 蓝黑为既定板块主题色已知接受）。

## 十、SRI 安全加固与全局样式表风险（2026-08-28 复盘）

安全加固 commit `c9e0fb7`（逐资源验签）给站内资源加了 SRI `integrity`，但**主 `style.css` 的 `<link>`（head.html:267）未加 `integrity`/`crossorigin`**——仅 `css/style.css?v=20260828` 普通引用。结论：

- **当前无风险**：主样式表不受哈希失配影响，全站正常加载（headless 实测 `document.styleSheets` 含该 href）。
- **⚠️ 未来红线**：若某次加固给 `style.css` 也加 SRI，则每次 bump `?v=` 或改 CSS 后**必须同步重算 integrity 哈希**；哈希与文件不符时浏览器会静默拒绝加载 → 全站去样式（headless 只表现为"未样式"而非普通 glitch，极易误判为其他 bug）。给主 CSS 加 SRI 前务必配套"改完即重算哈希"的脚本。
- 影响范围仅限主样式表；页面内联 `<style>`/`<style id="critical-css">` 与小脚本不受 SRI 约束（见第八节 CSP 关系）。

## 十一、协调性例外：App 独立品牌页（2026-08-28 明确）

「脚趾抠地」App 分享/隐私落地页 `static/shesi-landing.html`、`static/shesi-privacy.html`、`static/privacy.html`（commit `3044835` 等引入）为**刻意独立于 longxiong.vip 国风黑金家族**的 App 品牌页：浅色纸感底（`--paper:#f4efe6`）+ coral(`#ff5a5f`)/purple(`#7b5cff`) 撞色 + brutalist 描边卡片（`box-shadow:5px 5px 0`）。

- **设计意图**：分享卡要在社媒/微信里独立传播，需与 App 自身视觉一致、与知识站区分；无站点导航、无国风元素，属预期。
- **巡检处理**：排除在「首页↔子页协调 / 子页像另一个站」红线之外，**勿强行改回国风黑金**；仅验证其自身无 glitch（无横向滚动、无遮挡、无溢出）即可。
- **资产边界**：依用户硬性规则，App 内容不应挂在 longxiong.vip 下承载——此 3 页属既有历史放置，托尼巡检只管视觉无破损、不迁移域名（迁移归 legal/架构）。

## 十二、本周（2026-08-28）巡检结论速记

- 横向溢出：197 页 × 5 视口 × 2 主题 = 1970 组合，文档级 `scrollWidth-innerWidth` 全 0（headless 实测）。
- undefined CSS 变量：19009 处 `var()` 用法 / 213 定义，0 处未定义（带 fallback 已过滤）。
- 暖色刺眼：仅余既定小尺寸语义色（year-badge 红/橙胶囊、季节卡、`#42b883` 联系邮箱绿、`#e57373` 警示红、status-bubble 红徽标），均非大面积高饱和，按第六节"保持不动"准则维持。
- safe-area / sticky：navbar、mobile-nav、body、`.lx-search-wrap` 的 `top/height` 均在 `@supports(padding:env(safe-area-inset-top))` 内补 `calc(var(--nav-height)+env(...))`；body 用 `overflow-x:clip`（非 hidden），sticky 以视口为祖先，无失效。
- 交付门槛：视觉层面 **P0=P1=0** ✅。

## 十三、本周（2026-08-30）巡检结论速记

- 横向溢出（硬闸门）：199 页 × 5 视口(390/375/360/1440/1920) × 2 主题 = **1990 组合**，文档级 `documentElement.scrollWidth - innerWidth` 全 = 0，0 errors。
- 元素伸出视口（祖先感知重扫）：首轮标记 43 页含 `over`，经「向上遍历祖先查 overflow 裁剪」过滤后，**真实元素溢出 = 0**（全部为时间轴装饰点 / 表格内 version-tag / 逐时天气横滑行 / 首页横滑胶囊等预期内滚动容器后代）。
- undefined CSS 变量（refined，含 inline `style="--x"` + JS `setProperty` + fallback 过滤）：仅 `--cf-top`（console.html 运行时 setProperty + 56px fallback，安全），**真实未定义 = 0**。
- 暖色刺眼：全站无大面积高饱和暖色渐变；唯一暖色为 `.long-avatar`（48px 圆形头像，`linear-gradient(var(--orange),#FF8C42)`）属小尺寸语义头像、与 year-badge/季节卡同列「保持不动」；其余既定小尺寸语义色（year-badge 红橙胶囊、季节卡、`#42b883` 联系邮箱绿、`#e57373` 警示红、status-bubble 红徽标、footer 邮箱绿）维持。
- inline 颜色：static/*.html 零彩虹/暖色 inline 颜色；layouts/footer.html 仅一处 `color:#42b883`（联系邮箱绿，已知小语义色）。
- safe-area / sticky：`@supports(padding:env(safe-area-inset-top))` 完整覆盖 navbar(`height+padding-top`)、mobile-nav(`top+max-height`)、body(`padding-top`)、`.lx-search-wrap`(`top`)、theme-toggle/back-to-top/search-modal(`bottom/right` + safe-area 补偿)；body/html 均 `overflow-x:clip`（非 hidden），sticky 以视口为滚动祖先、无失效。
- 卡片系统：`.lx-card`/`.lx-epick`/`.artist-card` 跨页一致、无内联重定义漂移；新增组件复用 `.lx-*` 体系。
- 知识储备：本节 + 第七节新增 `--cf-top` 安全范式与「祖先裁剪误报」补漏（见上）。
- 交付门槛：视觉层面 **P0=P1=0** ✅（连续 3 周达标：08-25 / 08-28 / 08-30）。
