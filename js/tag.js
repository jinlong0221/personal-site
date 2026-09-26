/**
 * tag.js — 标签聚合页逻辑（零依赖，读 /data/content-index.json）
 *  - /tag.html?tag=标签名   → 列出打上该标签的全部文章
 *  - /tags.html             → 标签云（全部标签 + 计数，点击跳转到 tag.html）
 */
(function () {
  var INDEX = "/data/content-index.json";
  var data = [];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function load(cb) {
    fetch(INDEX)
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (d) { data = d || []; cb(); })
      .catch(function () { data = []; cb(); });
  }

  function cardHTML(x) {
    var tags = (x.tags || []).map(function (t) { return '<span class="fs-tag">' + esc(t) + "</span>"; }).join("");
    return '<a class="filter-card" href="' + esc(x.url) + '">' +
      '<div class="fc-top"><span class="fc-cat">' + esc(x.category) + "</span>" +
      (x.updated ? '<span class="fc-date">🕓 ' + esc(x.updated) + "</span>" : "") + "</div>" +
      '<div class="fc-title">' + esc(x.title) + "</div>" +
      (x.desc ? '<div class="fc-desc">' + esc(x.desc) + "</div>" : "") +
      (tags ? '<div class="fc-tags">' + tags + "</div>" : "") +
      "</a>";
  }

  // 返回 true 表示本页是 tag.html（已处理）；false 表示交给标签云处理
  function renderTagPage() {
    var el = document.getElementById("tagResults");
    if (!el) return false;
    var m = location.search.match(/[?&]tag=([^&]*)/);
    var tag = m ? decodeURIComponent(m[1]) : "";
    var titleEl = document.getElementById("tagTitle");
    if (!tag) {
      el.innerHTML = '<div class="fs-empty">请在网址后加 <code>?tag=标签名</code>，或从 <a href="/tags.html">标签聚合页</a> 选择一个标签。</div>';
      return true;
    }
    if (titleEl) titleEl.textContent = "标签：" + tag;
    document.title = "标签：" + tag + "｜龙兄知识库";
    var list = data
      .filter(function (x) { return (x.tags || []).indexOf(tag) > -1; })
      .sort(function (a, b) { return (b.updated || "").localeCompare(a.updated || ""); });
    if (!list.length) {
      el.innerHTML = '<div class="fs-empty">暂无打上「' + esc(tag) + '」标签的文章。</div>';
      return true;
    }
    el.innerHTML = '<div class="fs-count">共 ' + list.length + " 篇</div>" + list.map(cardHTML).join("");
    return true;
  }

  function renderCloud() {
    var el = document.getElementById("tagCloud");
    if (!el) return;
    var map = {};
    data.forEach(function (x) { (x.tags || []).forEach(function (t) { map[t] = (map[t] || 0) + 1; }); });
    var tags = Object.keys(map).sort(function (a, b) { return map[b] - map[a]; });
    if (!tags.length) {
      el.innerHTML = '<div class="fs-empty">还没有文章打标签，去文章里加 <code>&lt;meta name="article-tags"&gt;</code> 即可。</div>';
      return;
    }
    el.innerHTML = tags.map(function (t) {
      return '<a class="tag-cloud-item" href="/tag.html?tag=' + encodeURIComponent(t) + '">' +
        esc(t) + '<span class="tci-count">' + map[t] + "</span></a>";
    }).join("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    load(function () {
      if (renderTagPage()) return;
      renderCloud();
    });
  });
})();
