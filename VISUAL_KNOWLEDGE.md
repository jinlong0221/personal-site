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
