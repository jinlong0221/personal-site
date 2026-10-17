/**
 * page-reveal.js — 手写静态页的「滚到哪、哪出场」
 *
 * 把首页那套滚动出场（.reveal / .reveal-group 的 CSS 早已在 style.css 里）
 * 铺到手写静态页。这些页面不走 Hugo 模板，拿不到 reveal.js / animations.js，
 * 所以此前 110 个页面一个都没有出场动效（2026-09-23 实测）。
 *
 * 改动前务必读这四条：
 *
 * 1. 门控是 <html class="js">，且**最后一步才加**。
 *    先算目标、绑好观察器，确认没抛异常，最后才给 html 打标记。
 *    中途任何异常 → 标记没加上 → 内容全部默认可见，绝不会留下透明空洞。
 *    （2026-08-19 首页 hero 曾因「先隐藏、脚本挂掉」整块空白，这是那次教训的通用化。）
 *
 * 2. Hugo 渲染的页面（首页/文章页）已由 head.html 加过 .js 并跑着 reveal.js。
 *    本脚本进来先看 .js 在不在，在就立刻退出，绝不和它抢同一批元素。
 *
 * 3. 尊重系统「减少动态」偏好：命中就直接不启用，内容照常显示。
 *
 * 4. 只动 transform / opacity，不改尺寸也不改占位 → 不产生布局抖动。
 *
 * 5. 🔴 悬浮 UI（搜索弹层 / 图片灯箱 / 返回顶部）绝不能标 .reveal。
 *    它们平时 display:none，观察器永远看不到 → 永远拿不到 .in → 点开时是透明的，
 *    功能直接坏掉。见下面 FLOATY / inFlow 的注释（2026-09-23 实测踩到）。
 */
(function () {
  'use strict';

  // 已有别的机制在管这批元素（Hugo 页）→ 让位，不重复绑定
  var html = document.documentElement;
  if (html.classList.contains('js')) return;

  // 用户要求减少动态 → 整个不启用（不做任何标记，内容默认可见）
  try {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  } catch (e) { /* 老浏览器不认这个查询，按启用处理 */ }

  // 顶部面包屑与页尾信息块不参与出场（面包屑是首屏锚点，动了像页面在抖）
  var SKIP = /(^|\s)(breadcrumb|page-meta)(\s|$)/;
  // 首屏 hero 必须无条件可见，永远不参与滚动出场
  var HERO = /hero/i;

  function cls(el) {
    return typeof el.className === 'string' ? el.className : '';
  }

  // 网格容器的判定：先看类名（快），类名里没有 grid 字样的再用计算样式确认（准）。
  // 🔴 只看类名会漏掉 .bl-shots —— 它在 CSS 里是 display:grid，类名却叫 shots，
  // 而那正好是文玩板块首页那 4 张实拍，漏掉就少了最该错开的一组。
  // 刻意**不**把含 list 的容器也算进来：短列表本身就不该逐个蹦，收了会显得吵。
  var GRID_HINT = /grid|shots|deck/;
  function isGridBox(el) {
    if (!el || el.children.length < 2) return false;
    if (GRID_HINT.test(cls(el))) return true;
    try {
      return String(getComputedStyle(el).display).indexOf('grid') === 0;
    } catch (e) { return false; }
  }

  // 🔴 全站有两套正文骨架（2026-09-23 补第二套）：
  //
  //   A 型（main 骨架，117 页）：nav → main.container → footer
  //     main 的直接子元素就是各页「区块」（detail-section / bl-lead / cat-header /
  //     lx-related … 都在这一层）。这条路径已被 117 页实测，**不要动**。
  //
  //   B 型（无 main，59 页）：nav → .breadcrumb → .detail-hero → .detail-section
  //     → .lx-insight → .lx-related → .page-meta → footer，区块直接挂在 body 下。
  //     紫砂 40 个详情页还多包一层 .page-wrap，要穿透后再取区块。
  //     只认 main 会让这 59 页一个动效都没有 —— 从 games.html（有出场）点进
  //     gta6.html（死板）比两边都没动效更刺眼。
  var WRAP = /(^|\s)(page-wrap|page-main|content-wrap|detail-body)(\s|$)/;   // 需要穿透的外壳
  var NOT_BLOCK = /(^|\s)(navbar|mobile-nav|breadcrumb|page-meta|footer)(\s|$)/;

  // 🔴 悬浮 UI 绝不能参与出场（2026-09-23 实测踩到）：
  //    搜索弹层 .search-modal、图片灯箱 .site-lightbox、返回顶部 .back-to-top
  //    都是 body 的直接子元素，会被当成「内容块」标上 .reveal → 带 opacity:0。
  //    灯箱平时 display:none，观察器永远看不到它 → 永远拿不到 .in →
  //    **用户点开照片时灯箱是透明的，功能直接坏掉**。
  //    两条判据一起用：类名黑名单（意图明确） + 是否脱离文档流（兜住没列举到的）。
  var FLOATY = /(modal|lightbox|overlay|drawer|toast|popup|fab|back-to-top|quicktoc|toolbar)/i;

  function inFlow(el) {
    try {
      var pos = getComputedStyle(el).position;
      return pos === 'static' || pos === 'relative';
    } catch (e) { return true; }
  }

  // B 型专用：排除骨架件、悬浮 UI 与「空壳小碎块」（后者会让页面出现一闪而过的小方块）
  function usableOnBody(el) {
    var tag = el.tagName;
    if (tag === 'NAV' || tag === 'FOOTER' || tag === 'SCRIPT' ||
        tag === 'STYLE' || tag === 'LINK' || tag === 'NOSCRIPT') return false;
    var c = cls(el);
    if (FLOATY.test(c) || FLOATY.test(el.id || '')) return false;
    if (!inFlow(el)) return false;
    if (NOT_BLOCK.test(c) || SKIP.test(c) || HERO.test(c)) return false;
    // 既没有实质结构、文字又很短（如孤零零一个「返回」链接）→ 不值得出场一次
    if (!el.querySelector('img, svg, h1, h2, h3, table, ul, ol') &&
        (el.textContent || '').replace(/\s+/g, '').length < 12) return false;
    return true;
  }

  function blocks() {
    var main = document.querySelector('main');
    var out = [];
    var i, j;
    if (main) {
      var kids = main.children;
      for (i = 0; i < kids.length; i++) {
        var c = kids[i];
        if (SKIP.test(cls(c)) || HERO.test(cls(c))) continue;
        out.push(c);
      }
      return out;
    }
    // B 型：从 body 取，遇到外壳先穿一层
    var bk = document.body.children;
    for (i = 0; i < bk.length; i++) {
      if (!usableOnBody(bk[i])) continue;
      if (WRAP.test(cls(bk[i]))) {
        var inner = bk[i].children;
        for (j = 0; j < inner.length; j++) {
          if (usableOnBody(inner[j])) out.push(inner[j]);
        }
        continue;
      }
      out.push(bk[i]);
    }
    return out;
  }

  // 给一个容器挂「错开出场」：容器认领 .reveal-group，子元素各自认领 .reveal，
  // 档位由 style.css 里既有的 .reveal-group .reveal:nth-child(n) 提供（0/60/…/420ms）。
  function group(grid, marked) {
    if (grid.classList.contains('reveal-group')) return;
    if (grid.children.length < 2) return;
    grid.classList.add('reveal-group');
    for (var i = 0; i < grid.children.length; i++) {
      grid.children[i].classList.add('reveal');
      marked.push(grid.children[i]);
    }
  }

  function mark(nodes) {
    var marked = [];

    // 一层：区块本身。是网格容器就错开子卡片，否则整块出场。
    nodes.forEach(function (el) {
      if (isGridBox(el)) { group(el, marked); return; }
      el.classList.add('reveal');
      marked.push(el);
    });

    // 二层：区块内部嵌套的网格（如主机详情页 .detail-section > .spec-grid、
    // 文玩页 .bl-shots-wrap > .bl-shots）—— 让里面的条目错开，比整块一起淡入更细。
    nodes.forEach(function (el) {
      var grids = el.querySelectorAll('[class*="grid"], [class*="shots"], [class*="deck"]');
      for (var i = 0; i < grids.length; i++) {
        if (isGridBox(grids[i])) group(grids[i], marked);
      }
    });

    // 三层：去嵌套重复。一个元素被标记，它的祖先就不能再带 .reveal，
    // 否则内外各淡一次、各移动 24px，叠成 48px 的双重位移。
    marked.forEach(function (el) {
      var p = el.parentElement;
      while (p && p !== document.body) {
        if (p.classList.contains('reveal')) p.classList.remove('reveal');
        p = p.parentElement;
      }
    });

    return marked;
  }

  function watch(nodes) {
    function allIn() {
      for (var i = 0; i < nodes.length; i++) nodes[i].classList.add('in');
    }
    // 浏览器不支持就全部直接显示，不留隐藏态
    if (!('IntersectionObserver' in window)) { allIn(); return; }

    var obs = new IntersectionObserver(function (entries) {
      var hit = false;
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          obs.unobserve(e.target);
          hit = true;
        }
      });
      // 有人刚进视口 → 顺手补一次兜底。
      // 为什么放在回调里：这样不用挂 scroll 监听（省一个每帧回调），
      // 而覆盖时机刚好 —— 只要用户滚动到任何新元素，之前被「跳过去」的元素都会被补上。
      if (hit) sweep();
    }, { rootMargin: '0px 0px -50px 0px', threshold: 0.1 });

    nodes.forEach(function (el) { obs.observe(el); });

    // 兜底：把「已经到达或越过视口」却还没显形的强制显示。
    // 🔴 判据是「顶边到达过视口下沿」而不是「此刻在视口里」（2026-09-23 修）：
    //    后者对**已经滚过去**的元素（rect.top 为负）永远为假 ——
    //    一次性跳转（锚点 #tab-hist、按 End 键、触控板一甩）会让元素整段跳过视口，
    //    它们就一直 opacity:0，用户往回滚时才一个接一个凭空淡入，
    //    看着像页面在重载。改成单向判据后，滚过去的就算「已出场」。
    // 零尺寸元素（display:none 的折叠区、自定义弹层）跳过不计：
    // 它们本就不该被判为「已到达」，等真正显示时由观察器接管（已实测有效）。
    function sweep() {
      for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        if (el.classList.contains('in')) continue;
        var r = el.getBoundingClientRect();
        if (r.height === 0 && r.width === 0) continue;
        if (r.top < window.innerHeight - 50) el.classList.add('in');
      }
    }
    function schedule() {
      setTimeout(sweep, 1000);
      setTimeout(sweep, 2500);
    }
    if (document.readyState === 'complete') schedule();
    else window.addEventListener('load', schedule);
  }

  function init() {
    var marked = mark(blocks());
    if (!marked.length) return;   // 没有可做的页面（跳转壳 / 法务页）→ 保持原样
    watch(marked);
    html.classList.add('js');     // 🔴 一切就绪，最后才开门控
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
