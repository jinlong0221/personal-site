/**
 * changelog.js — 更新日志页的渐进增强渲染
 *
 * ## 设计（2026-09-17 重写）
 *
 * 页面骨架里已经由 scripts/build_changelog_feed.py 注入了静态回退内容，
 * 所以本脚本的角色是「增强」而不是「从零渲染」：拿到全量 feed 后，
 * 把最近一批替换成完整的、按天分组、主线与自动化留痕分档的版本。
 *
 * 相比旧版修掉四件事：
 *
 *  1. **不再硬截断**。旧版把首句切到 60 字 + 省略号，切口常落在脚本名或
 *     半句话中间，观感是「话说到一半」。现在按标点回退断句，断在语义边界。
 *  2. **渲染行内 Markdown**。旧版只做 HTML 转义，正文里大量包脚本名的
 *     反引号原样显示。现在 `code` → <code>、**粗体** → <strong>。
 *  3. **按天分组**。旧版 652 条平铺成一条长线，看不出「哪天干了什么」。
 *  4. **自动化留痕不再淹没主线**。台风监测、新闻巡检这类记录按天折叠成
 *     一行计数，点开才看明细 —— 旧版把它们和真正的改动混在一起平铺。
 *
 * 渐进增强：feed 拿不到就什么都不动，静态回退内容原样留着；
 * 用户在无 JS / 弱网 / 拦截环境下看到的仍是完整可读的页面。
 */
(function () {
  'use strict';

  var FEED_PATH = 'data/changelog-feed.json';
  var LEGACY_PATHS = ['data/changelog.json', 'changelog.json'];
  var PAGE_DAYS = 15;   // 每次「加载更早」追加的天数
  var LEAD_LIMIT = 110; // 首句超过多少字开始找标点断句

  /* ── 小工具 ────────────────────────────────────────────── */

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /** 行内 Markdown：先转义再替换，不引入 XSS 面 */
  function md(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  }

  /** 拆首屏可见 / 收进详情两段。规则同 scripts/build_changelog_feed.py 的 split_lead：
   *  短条目（≤180 字）整条显示；长条目取首句，首句过长时回退到标点断开。 */
  function splitLead(text) {
    text = String(text || '').trim();
    if (text.length <= 180) return [text, ''];
    var m = text.split(/(?<=[。！？\n])/);
    var lead = (m[0] || '').trim();
    var rest = m.slice(1).join('').trim();
    if (lead.length <= LEAD_LIMIT) return [lead, rest];
    var cut = -1, marks = '，、；：,;:';
    for (var i = 0; i < marks.length; i++) {
      var idx = lead.lastIndexOf(marks[i], LEAD_LIMIT);
      if (idx > cut) cut = idx;
    }
    if (cut >= LEAD_LIMIT / 2) {
      return [lead.slice(0, cut + 1), (lead.slice(cut + 1) + ' ' + rest).trim()];
    }
    return [lead, rest];
  }

  var WD = ['一', '二', '三', '四', '五', '六', '日'];
  function fmtDay(d) {
    var y = d.slice(0, 4), mo = parseInt(d.slice(5, 7), 10), da = parseInt(d.slice(8, 10), 10);
    var w = WD[new Date(d + 'T00:00:00').getDay() === 0 ? 6 : new Date(d + 'T00:00:00').getDay() - 1];
    return y + ' 年 ' + mo + ' 月 ' + da + ' 日 · 周' + w;
  }
  function hhmm(d) { return d.length >= 16 ? d.slice(11, 16) : ''; }

  function baseOf() {
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var m = scripts[i].src.match(/(.*\/)js\/.+/);
      if (m) return m[1];
    }
    return '';
  }

  function getJSON(url) {
    return new Promise(function (resolve) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', url, true);
      xhr.responseType = 'json';
      xhr.onload = function () {
        resolve((xhr.status === 200 || xhr.status === 0) && xhr.response ? xhr.response : null);
      };
      xhr.onerror = function () { resolve(null); };
      try { xhr.send(); } catch (e) { resolve(null); }
    });
  }

  /* ── 渲染片段 ──────────────────────────────────────────── */

  function itemHTML(it) {
    var lead = splitLead(it.t);
    var t = hhmm(it.date);
    var h = '<div class="cl-item">';
    if (t) h += '<span class="cl-time">' + esc(t) + '</span>';
    h += '<div class="cl-main"><p class="cl-head">' + md(lead[0]) + '</p>';
    if (lead[1]) {
      h += '<details class="cl-detail"><summary>展开全文</summary>'
         + '<div class="cl-body">' + md(lead[1]) + '</div></details>';
    }
    return h + '</div></div>';
  }

  function opsHTML(ops) {
    var names = Object.keys(ops || {});
    if (!names.length) return '';
    var chips = '', bodies = '';
    names.forEach(function (name) {
      var slot = ops[name] || { n: 0, s: [] };
      chips += '<span class="cl-chip">' + esc(name) + ' ×' + slot.n + '</span>';
      var rows = (slot.s || []).map(function (s) {
        return '<p class="cl-ops-row">' + md(s) + '</p>';
      }).join('');
      var more = slot.n > (slot.s || []).length
        ? '<p class="cl-ops-more">另有 ' + (slot.n - slot.s.length) +
          ' 条同类记录，完整明细见站点数据文件 data/changelog.json。</p>' : '';
      bodies += '<div class="cl-ops-grp"><div class="cl-ops-name">' + esc(name) +
                '</div>' + rows + more + '</div>';
    });
    return '<details class="cl-ops"><summary><span class="cl-ops-t">自动化运维</span>'
         + chips + '<span class="cl-ops-hint">展开明细</span></summary>'
         + '<div class="cl-ops-body">' + bodies + '</div></details>';
  }

  function dayHTML(day) {
    var items = (day.items || []);
    var rows = items.map(itemHTML).join('');
    if (!rows && !day.ops) return '';
    var n = items.length
      ? '<span class="cl-day-n">' + items.length + ' 项改动</span>' : '';
    // h4 不是笔误：app.js 的区域J 自动章节导航扫全页 h2/h3 建目录，
    // 日分组若用 h3，七十天的小标题会把底部目录撑成七十项。详见
    // scripts/build_changelog_feed.py 同名注释。
    return '<section class="cl-day"><h4 class="cl-day-hd"><time datetime="' + esc(day.date) +
           '">' + fmtDay(day.date) + '</time>' + n + '</h4>' + rows + opsHTML(day.ops) + '</section>';
  }

  function summaryHTML(st) {
    if (!st) return '';
    var gap = '';
    if (st.gaps && st.gaps.length) {
      gap = '<p class="cl-sum-gap">记录断档：' +
            st.gaps.map(function (g) { return esc(g.replace('~', ' ~ ')); }).join('、') +
            '（那几天本站未维护更新日志，此处不补造内容）</p>';
    }
    return '<p class="cl-sum-lead">从 ' + esc(st.first) + ' 建站第一天起，共 <strong>' + st.total +
           '</strong> 条记录、覆盖 <strong>' + st.days + '</strong> 天，累计 <strong>' +
           st.chars.toLocaleString('en-US') + '</strong> 字。</p>' +
           '<p class="cl-sum-sub">其中 <strong>' + st.main + '</strong> 条是站点本身的改动' +
           '（新板块、修复、重构、文案），另有 <strong>' + st.ops + '</strong> 条是台风监测、' +
           '新闻巡检这类自动化留痕 —— 后者按天折叠，不占版面。</p>' + gap;
  }

  /* ── 主流程 ────────────────────────────────────────────── */

  function renderFeed(feed, container) {
    var sum = document.getElementById('clSummary');
    if (sum && feed.stats) sum.innerHTML = summaryHTML(feed.stats);

    var days = feed.days || [];
    if (!days.length || !container) return;

    var shown = 0;
    container.innerHTML = '';

    function appendChunk() {
      var buf = '', added = 0;
      while (shown < days.length && added < PAGE_DAYS) {
        var html = dayHTML(days[shown]);
        shown++; added++;
        if (html) buf += html;
      }
      container.insertAdjacentHTML('beforeend', buf);
      var old = container.parentNode.querySelector('.cl-more');
      if (old) old.remove();
      if (shown < days.length) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'cl-more';
        btn.textContent = '加载更早的记录（还剩 ' + (days.length - shown) + ' 天）';
        btn.addEventListener('click', appendChunk);
        container.parentNode.insertBefore(btn, container.nextSibling);
      }
      // 让新插入的节点也吃到滚动入场动画（若页面启用了该效果）
      if (window.initScrollAnimations) { try { window.initScrollAnimations(); } catch (e) {} }
    }
    appendChunk();

    // 页脚数据同步（静态回退里写的是生成时的值，这里按真实 feed 刷新）
    var upd = document.getElementById('changelogUpdated');
    if (upd && feed.stats && feed.stats.last) upd.textContent = feed.stats.last.slice(0, 10);
    var stamp = document.getElementById('clLastStamp');
    if (stamp && feed.stats && feed.stats.last.length >= 16) {
      stamp.textContent = ' ' + feed.stats.last.slice(11, 16);
    }
    var cnt = document.getElementById('update-count');
    if (cnt && feed.stats) cnt.textContent = feed.stats.total;
  }

  /** feed 拿不到时退回旧的两份数据源合并（不分组、不折叠，仅保证有内容） */
  function renderLegacy(base, container) {
    var done = 0, results = [];
    LEGACY_PATHS.forEach(function (p) {
      getJSON(base + p).then(function (r) { results.push(r); finish(); }, function () { results.push(null); finish(); });
    });
    function finish() {
      if (++done < LEGACY_PATHS.length) return;
      var seen = {}, merged = [];
      results.forEach(function (arr) {
        if (!Array.isArray(arr)) return;
        arr.forEach(function (x) {
          if (!x || !x.date) return;
          var c = x.content || x.desc || x.title || '';
          var k = x.date + ' ' + c;
          if (seen[k]) return;
          seen[k] = 1;
          merged.push({ date: x.date, content: c });
        });
      });
      if (!merged.length) return;
      merged.sort(function (a, b) { return a.date < b.date ? 1 : (a.date > b.date ? -1 : 0); });
      container.innerHTML = merged.slice(0, 60).map(function (x) {
        return '<section class="cl-day"><h4 class="cl-day-hd"><time datetime="' + esc(x.date.slice(0, 10)) +
               '">' + esc(x.date) + '</time></h4>' + itemHTML({ date: x.date, t: x.content }) + '</section>';
      }).join('');
    }
  }

  function boot() {
    var container = document.getElementById('weeklyChangelog');
    if (!container) return; // 非本页，零开销
    var base = baseOf();
    getJSON(base + FEED_PATH).then(function (feed) {
      if (feed && feed.days && feed.days.length) renderFeed(feed, container);
      else renderLegacy(base, container);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
