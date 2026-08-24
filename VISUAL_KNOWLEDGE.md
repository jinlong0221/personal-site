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

## 七、无头浏览器验证方法论（托尼自用）

模型无法读图，用 puppeteer-core + Chrome for Testing 做 DOM 实测替代"看见"：

- **本地构建必须改 baseURL**：`hugo --gc --baseURL "http://127.0.0.1:8199/" --destination /tmp/lx-pub`，否则线上绝对 URL 在本地 404。head.html 的 meta CSP `style-src 'self' 'unsafe-inline'` 在同源(localhost)下放行内联样式与同域 CSS，无需去 CSP、无需改资源本地化。
- **横向溢出双指标**（html `overflow-x:hidden` 会裁剪掩盖，单信 scrollWidth 会漏报）：
  1. 文档级 `document.documentElement.scrollWidth - window.innerWidth` 须 = 0；
  2. "伸出视口"元素扫描：遍历 `*`，取 `getBoundingClientRect()`，`rect.right > innerWidth+1.5` 且不在 `overflow-x:auto/scroll` 祖先内部者 = 视觉溢出。后者能抓被 html clip 掉的裁切内容，比前者更可靠。
- **遍历规模**：194 页 × 5 视口(390/375/360/1440/1920) × 2 主题 ≈ 1940 次加载，单进程约 12–20 分钟；务必后台跑、勿前台阻塞。
- **undefined CSS 变量扫描坑**：只扫 `style.css` 会大量误报（页面内联 `<style>` 与 pagefind 自带 CSS 也定义了 `--xxx`）。正确做法：从「全部 .css + 全部 html 内联 `<style>` + JS `setProperty`」收集定义，再比对 `var()` 用法，并过滤带 fallback 的 `var(--x, 默认值)`。
- **safe-area / sticky 用代码审查而非截图**：grep `position:sticky` 找所有 `top:var(--nav-height)` 元素，确认每个都在 `@supports(padding:env(safe-area-inset-top))` 内补 `top:calc(var(--nav-height)+env(safe-area-inset-top))`；并确认 body 是 `overflow-x:clip`（非 hidden），sticky 才能以视口为滚动祖先。
