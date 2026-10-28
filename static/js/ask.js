/* ask.js — 「问龙兄」纯前端问答（无后端、不联网、不花钱）
 * 浏览器端关键词匹配 static/ask-kb.json，GitHub Pages 静态托管。
 * 所有匹配均在本地完成，不向任何服务器发送输入内容。
 */
(function () {
  "use strict";

  var KB_URL = "ask-kb.json";
  var MAX_RESULTS = 6;

  var inputEl, btnEl, chipsEl, resultEl;
  var KB = null;          // 整个知识库
  var entries = [];       // 条目数组
  var categories = [];    // 分类列表
  var activeCat = null;   // 当前选中的分类筛选

  function $(id) { return document.getElementById(id); }

  function normalize(s) {
    return (s || "").toString().toLowerCase().replace(/\s+/g, " ").trim();
  }

  // 给一条目算分：问法/触发词命中权重最高，分类次之，正文最弱
  function scoreEntry(entry, q) {
    if (!q) return 0;
    var score = 0;
    var keys = [];
    if (entry.q) keys.push(entry.q);
    if (Array.isArray(entry.aka)) keys = keys.concat(entry.aka);

    for (var i = 0; i < keys.length; i++) {
      var k = normalize(keys[i]);
      if (!k) continue;
      if (q === k) score += 100;
      else if (k.indexOf(q) !== -1) score += 12 + k.length;          // 用户输入是触发词的子集
      else if (q.indexOf(k) !== -1) score += 20 + k.length;          // 触发词出现在用户输入里
    }
    // 分类名命中（弱）
    if (entry.category && normalize(entry.category).indexOf(q) !== -1) score += 6;
    // 正文弱匹配（仅当查询 >= 3 字，避免噪声）
    if (q.length >= 3 && entry.a && normalize(entry.a).indexOf(q) !== -1) score += 3;
    return score;
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function entryCardHTML(e) {
    var links = "";
    if (Array.isArray(e.links) && e.links.length) {
      links = '<div class="ask-links">' + e.links.map(function (l) {
        return '<a class="ask-link" href="' + escapeHtml(l.url) + '">' + escapeHtml(l.title) + " ›</a>";
      }).join("") + "</div>";
    }
    return (
      '<article class="ask-card">' +
        '<h3 class="ask-q">' + escapeHtml(e.q) +
          '<span class="ask-cat">' + escapeHtml(e.category || "问答") + "</span></h3>" +
        '<p class="ask-a">' + escapeHtml(e.a) + "</p>" +
        links +
      "</article>"
    );
  }

  function renderResults(list) {
    if (!list.length) {
      resultEl.innerHTML =
        '<div class="ask-empty">没太对上🤔 换个说法试试？比如「<b>紫砂</b>」「<b>你站里卖东西吗</b>」「<b>贾维斯</b>」。<br>' +
        "或者直接翻翻下面的热门问题。需要真办事，在对话里跟我说「状态：…」这类暗号即可。</div>";
      return;
    }
    resultEl.innerHTML = list.map(entryCardHTML).join("");
  }

  function search(raw) {
    var q = normalize(raw);
    var pool = activeCat ? entries.filter(function (e) { return e.category === activeCat; }) : entries;
    if (!q) {
      // 空查询：展示当前分类下的全部（或默认热门）
      renderResults(pool.slice(0, MAX_RESULTS));
      return;
    }
    var scored = [];
    for (var i = 0; i < pool.length; i++) {
      var s = scoreEntry(pool[i], q);
      if (s > 0) scored.push({ e: pool[i], s: s });
    }
    scored.sort(function (a, b) { return b.s - a.s; });
    renderResults(scored.slice(0, MAX_RESULTS).map(function (x) { return x.e; }));
  }

  function renderChips() {
    var html = '<button class="ask-chip' + (activeCat === null ? " on" : "") + '" data-cat="">全部</button>';
    html += categories.map(function (c) {
      return '<button class="ask-chip' + (activeCat === c ? " on" : "") + '" data-cat="' + escapeHtml(c) + '">' + escapeHtml(c) + "</button>";
    }).join("");
    chipsEl.innerHTML = html;
    Array.prototype.forEach.call(chipsEl.querySelectorAll(".ask-chip"), function (chip) {
      chip.addEventListener("click", function () {
        var c = chip.getAttribute("data-cat");
        activeCat = c === "" ? null : c;
        renderChips();
        search(inputEl.value);
      });
    });
  }

  function renderHot() {
    // 无分类筛选、无输入时的默认热门（挑几个有代表性的）
    var hotIds = ["who", "site-what", "zisha", "no-commerce", "ask-what", "javis"];
    var hot = hotIds.map(function (id) {
      for (var i = 0; i < entries.length; i++) if (entries[i].id === id) return entries[i];
      return null;
    }).filter(Boolean);
    if (hot.length) renderResults(hot);
    else renderResults(entries.slice(0, MAX_RESULTS));
  }

  function bindUI() {
    inputEl = $("askInput");
    btnEl = $("askBtn");
    chipsEl = $("askChips");
    resultEl = $("askResult");
    if (!inputEl || !btnEl || !chipsEl || !resultEl) return;

    btnEl.addEventListener("click", function () { search(inputEl.value); });
    inputEl.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.keyCode === 13) { ev.preventDefault(); search(inputEl.value); }
    });
    // 输入即搜（轻量防抖）
    var t = null;
    inputEl.addEventListener("input", function () {
      if (t) clearTimeout(t);
      t = setTimeout(function () { search(inputEl.value); }, 120);
    });
  }

  function init() {
    bindUI();
    fetch(KB_URL, { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        KB = data;
        entries = (data && data.entries) || [];
        var seen = {};
        categories = [];
        entries.forEach(function (e) {
          if (e.category && !seen[e.category]) { seen[e.category] = 1; categories.push(e.category); }
        });
        renderChips();
        renderHot();
      })
      .catch(function (err) {
        if (resultEl) {
          resultEl.innerHTML =
            '<div class="ask-empty">知识库加载失败（' + escapeHtml(String(err && err.message || err)) +
            "）。请刷新重试；若仍不行，可到「关于本站 / 站长手记」直接看原文。</div>";
        }
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
