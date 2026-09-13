/*
 * auto-collapse.js — 通用「板块 > 阈值条数则默认折叠」组件
 *
 * 两种启用方式：
 *  1) 显式：在容器加 data-ac 及下列属性（手动控制，优先级最高）。
 *  2) 自动：脚本扫描全站「带标题的内容网格 / 列表 / section」，只­要直接子项 > 阈值（默认 2）即自动折叠。
 *           适用于所有页面，无需逐页加标记；新增页面亦自动生效。
 *
 * 显式属性：
 *   data-ac                    开启自动折叠
 *   data-ac-body=".sel"        折叠区选择器（默认：自身或首个匹配）
 *   data-ac-items=".sel"       计数与折叠判定的子项选择器（默认 :scope > *）
 *   data-ac-head=".sel"        点击折叠的头部选择器 / 标签
 *   data-ac-threshold="2"      超过该条数才折叠（默认 2）
 *   data-ac-default="auto|open|collapsed"  默认状态；auto=超过阈值才折叠（默认）
 *   data-ac-count="true|false" 是否显示条数徽标（默认 true）
 *
 * 自动探测规则（autoDetect）：
 *   - 候选：含 grid/deck/board/gallery/list 类名的容器，或直接包含 ≥(阈值+1) 张「卡片」的 div/section/ul/ol。
 *   - 头部：容器「前一个兄弟」中的标题（h2–h6 或 .section-title/.section-header/.sec-title 等），必须位于容器之外。
 *   - 排除：nav/header/footer/aside/工具栏/面包屑/hero/kpi，以及旅行加密相册页。
 *   - 找不到标题的板块静默跳过（不折叠），避免破坏布局。
 */
(function () {
  'use strict';

  var THRESHOLD = 2;

  // 标题节点：仅 h2–h6 或带标题语义 class 的元素（不含 h1，避免折叠页面主标题下的首要内容）
  function isHeadingNode(n) {
    if (!n) return false;
    if (/^H[2-6]$/.test(n.tagName)) return true;
    var c = (n.className || '');
    if (typeof c !== 'string') return false;
    return /(sec-title|section-title|section-header|section-head|sec-header|heading|title|\bhead\b)/i.test(c);
  }

  // 是否为「内容块」而非裸标题：遇到内容块即停止向上寻找标题
  function looksLikeContentBlock(n) {
    if (!n) return false;
    if (/^H[1-6]$/.test(n.tagName)) return false;
    return !!(n.children && n.children.length >= 1 && !isHeadingNode(n));
  }

  // 在上下文中寻找首个标题元素（含 h2–h6 或带标题语义 class 的容器）
  function firstHeadingIn(ctx) {
    if (!ctx || !ctx.querySelector) return null;
    return ctx.querySelector('h2,h3,h4,h5,h6,.section-title,.section-header,.sec-title,.sec-header,.cat-header,[class*="sec-title"],[class*="heading"]');
  }

  // 返回元素所属「语义区块」：最近的 section/main/article 或带容器语义的类。
  // 用于把 findHead 的标题探测限定在本区块内，杜绝折叠键错挂到外层/无关 section 的标题
  // （万年历·拼假攻略误挂整年视图即用旧版跨区块攀爬所致）。
  function enclosingSection(el) {
    var a = el;
    while (a) {
      if (a.tagName === 'SECTION' || a.tagName === 'MAIN' || a.tagName === 'ARTICLE') return a;
      var c = (a.className || '');
      if (typeof c === 'string' && /(^|\s)(container|lx-section|cal-page|cat-section|board-section)(\s|$)/.test(c)) return a;
      a = a.parentElement;
    }
    return null;
  }

  // 仅返回位于容器之外的标题（保证折叠容器时标题仍可见）
  function findHead(board) {
    var sec = enclosingSection(board);
    // 1) 在 board 所属区块内，向上遍历前一个兄弟，直到标题
    var prev = board.previousElementSibling;
    while (prev && prev !== sec) {
      if (isHeadingNode(prev)) return prev;
      var inner = firstHeadingIn(prev); // 标题被包在 header 容器里（如 .cat-header > h2）
      if (inner) return inner;
      prev = prev.previousElementSibling;
    }
    // 2) 父级的前一个兄弟链，但**不超过本区块边界**（不向上爬到外层 section 的标题）
    var p = board.parentElement;
    while (p && p !== sec) {
      var pp = p.previousElementSibling;
      while (pp && pp !== sec) {
        if (isHeadingNode(pp)) return pp;
        var inner2 = firstHeadingIn(pp);
        if (inner2) return inner2;
        pp = pp.previousElementSibling;
      }
      p = p.parentElement;
    }
    return null;
  }

  var EXCLUDE_SEL = 'nav,header,footer,aside,.navbar,.sidebar,.breadcrumb,.pagination,.toolbar,.toc,.bm-bar,.quick-toc';
  var SKIP_CLASS = /(nav|menu|breadcrumb|toolbar|pagination|footer|sidebar|hero|kpi|crumb|social|share|bread|skip|toc|bookmark|fab|float|banner|ad-|advert|modal|popup|overlay)/i;

  function isExcluded(board) {
    if (board.closest && board.closest(EXCLUDE_SEL)) return true;
    var c = board.className || '';
    if (typeof c === 'string' && SKIP_CLASS.test(c)) return true;
    return false;
  }

  // 卡片判定：class 含 "card" 子串、且不是容器（grid/deck/board/gallery/list）的 token，
  // 才视为卡片。这样可精确命中 *-card / card-* 等卡片类，又不会把 .cj-era-grid 的内部 div
  // 或 .card-grid 容器误判为卡片。
  function isCard(ch) {
    if (!ch.classList) return false;
    var toks = ch.classList;
    for (var i = 0; i < toks.length; i++) {
      var t = toks[i].toLowerCase();
      if (t.indexOf('card') > -1 && !/(grid|deck|board|gallery|list)/.test(t)) return true;
    }
    return false;
  }

  function collectItems(board) {
    var out = [];
    var kids = board.children;
    var bcn = (typeof board.className === 'string') ? board.className : '';
    // 仅当列表容器带 grid/deck/board/gallery/list 类名时才计 li，避免折叠文章正文里的普通 markdown 项目符号列表
    var isCardList = /(^|[\s-])(grid|deck|board|gallery|list)([\s-]|$)/i.test(bcn);
    for (var i = 0; i < kids.length; i++) {
      var ch = kids[i];
      if (!ch.classList) continue;
      if (isCard(ch)) out.push(ch);
      else if (ch.tagName === 'LI' && isCardList) out.push(ch); // 仅列表型容器才计 li
      else if (ch.tagName === 'ARTICLE' && isCard(ch)) out.push(ch); // 仅卡片型 article
    }
    return out;
  }

  function makeBoard(board, opts) {
    var body = opts.body || board;
    var head = opts.head || null;
    var itemSel = opts.itemSel || ':scope > *';
    var threshold = (typeof opts.threshold === 'number') ? opts.threshold : THRESHOLD;
    var def = opts.def || 'auto';
    var showCount = (opts.count !== false);

    var items = (itemSel === ':scope > *')
      ? Array.prototype.slice.call(body.children)
      : body.querySelectorAll(itemSel);
    var count = items.length;

    var collapsed;
    if (def === 'open') collapsed = false;
    else if (def === 'collapsed') collapsed = true;
    else collapsed = count > threshold;

    // 自动模式且未超阈值：保持展开、不加折叠控件
    if (def === 'auto' && count <= threshold) {
      board.setAttribute('data-ac-state', 'open');
      return;
    }

    // 防错挂：找不到标题（如板块标题在本区块外）则不折叠，避免把 toggle 挂到卡片/容器上
    if (!head) {
      board.setAttribute('data-ac-state', 'open');
      return;
    }
    // 防与原生 <details>/<summary> 折叠控件重叠
    if (head.closest && head.closest('summary')) {
      board.setAttribute('data-ac-state', 'open');
      return;
    }
    // 防空板：body 无实质内容时不建折叠键（点了也看不见效果，属「没用」的一类）
    var bodyText = (body.innerText || '').trim();
    if (body.children.length === 0 && bodyText.length === 0) {
      board.setAttribute('data-ac-state', 'open');
      return;
    }

    board.classList.add('lx-ac');
    body.classList.add('lx-ac-body');
    head.classList.add('lx-ac-head', 'lx-ac-head-click');

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'lx-ac-toggle';
    toggle.setAttribute('aria-expanded', 'false');
    toggle.innerHTML =
      (showCount ? '<span class="lx-ac-count"></span>' : '') +
      '<span class="lx-ac-label"></span>' +
      '<span class="lx-ac-arrow" aria-hidden="true"></span>';

    var label = toggle.querySelector('.lx-ac-label');
    var arrow = toggle.querySelector('.lx-ac-arrow');
    var countBadge = toggle.querySelector('.lx-ac-count');

    function setState(state) {
      board.setAttribute('data-ac-state', state);
      var isOpen = state === 'open';
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      label.textContent = isOpen ? '收起' : '展开';
      arrow.textContent = isOpen ? '▴' : '▾';
      if (countBadge) countBadge.textContent = String(count);
    }

    head.appendChild(toggle);
    setState(collapsed ? 'collapsed' : 'open');

    function toggleState() {
      setState(board.getAttribute('data-ac-state') === 'open' ? 'collapsed' : 'open');
    }
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      toggleState();
    });
    head.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('.lx-ac-toggle')) return;
      toggleState();
    });
  }

  // 显式 data-ac 处理
  function initExplicit() {
    var boards = document.querySelectorAll('[data-ac]');
    Array.prototype.forEach.call(boards, function (board) {
      var bodySel = board.getAttribute('data-ac-body');
      var body = bodySel ? board.querySelector(bodySel) : null;
      if (bodySel && !body && board.matches(bodySel)) body = board; // body 即自身（无包裹模式）
      if (!body) body = board;

      var itemSel = board.getAttribute('data-ac-items') || ':scope > *';
      var headSel = board.getAttribute('data-ac-head');
      var head = null;
      if (headSel) {
        head = board.querySelector(headSel);
        if (!head && board.previousElementSibling && board.previousElementSibling.matches &&
            board.previousElementSibling.matches(headSel)) {
          head = board.previousElementSibling; // 头部为前一个兄弟节点（无包裹模式）
        }
      }
      if (!head) head = board.firstElementChild;
      if (!head) head = board;

      makeBoard(board, {
        body: body,
        head: head,
        itemSel: itemSel,
        threshold: parseInt(board.getAttribute('data-ac-threshold') || String(THRESHOLD), 10),
        def: board.getAttribute('data-ac-default') || 'auto',
        count: (board.getAttribute('data-ac-count') || 'true') !== 'false'
      });
    });
  }

  // 全站自动探测
  function autoDetect() {
    if (/travel/i.test(location.pathname)) return; // 旅行加密相册不自动处理

    var handled = new Set();
    // 显式板块及其所有后代不再自动处理
    document.querySelectorAll('[data-ac]').forEach(function (b) {
      handled.add(b);
      var d = b.querySelectorAll('*');
      Array.prototype.forEach.call(d, function (x) { handled.add(x); });
    });

  function fold(el) {
    // 跳过原生 <details> 折叠容器，避免与 <summary> 冲突
    if (el.closest && el.closest('details')) return;
    var items = collectItems(el);
    if (items.length <= THRESHOLD) return;
    var head = findHead(el);
    if (!head) return;
      // 防碰撞：同一标题已被另一折叠板占用（出现双 toggle），本容器不再挂键，
      // 避免一个标题下叠两个折叠键（如光辉电力·产品体系全覆盖内两兄弟卡片组共享同一 h2）
      if (head.querySelector('.lx-ac-toggle')) return;
      makeBoard(el, { body: el, head: head, itemSel: ':scope > *', threshold: THRESHOLD, def: 'auto', count: true });
      // 标记自身及祖先为已处理，避免外层容器重复折叠（仅折叠最内层板块）
      var a = el;
      while (a) { handled.add(a); a = a.parentElement; }
    }

    // 候选 1：带网格/列表语义类名的容器
    var named = document.querySelectorAll('[class*="grid"],[class*="deck"],[class*="board"],[class*="gallery"],[class*="list"]');
    Array.prototype.forEach.call(named, function (el) {
      if (handled.has(el) || isExcluded(el)) return;
      fold(el);
    });

    // 候选 2：直接包含多张卡片的 div/section/ul/ol（覆盖无 grid 类名的卡片列表）
    var broad = document.querySelectorAll('div,section,ul,ol');
    Array.prototype.forEach.call(broad, function (el) {
      if (handled.has(el) || isExcluded(el)) return;
      fold(el);
    });
  }

  function expandTarget(id) {
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    var board = el.hasAttribute('data-ac') ? el : (el.closest ? el.closest('[data-ac]') : null);
    if (board) board.setAttribute('data-ac-state', 'open');
  }

  function initAutoCollapse() {
    initExplicit();
    autoDetect();

    // 页内锚点 / # 直达：自动展开目标板块
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href^="#"]');
      if (!a) return;
      var href = a.getAttribute('href');
      if (href && href.length > 1) expandTarget(decodeURIComponent(href.slice(1)));
    });
    if (location.hash && location.hash.length > 1) {
      setTimeout(function () { expandTarget(decodeURIComponent(location.hash.slice(1))); }, 0);
    }
  }

  if (document.readyState !== 'loading') initAutoCollapse();
  else document.addEventListener('DOMContentLoaded', initAutoCollapse);
})();
