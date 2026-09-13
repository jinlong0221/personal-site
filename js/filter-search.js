/**
 * filter-search.js — 升级后的全站搜索（关键词 + 分类/标签/更新时间筛选）
 * 零依赖：读取 /data/content-index.json（由 scripts/build_content_index.py 生成），
 *        纯前端过滤。原 Pagefind 弹窗搜索（search.js）保持不变，此处为搜索页专用。
 */
(function () {
  var INDEX = "/data/content-index.json";
  var state = { q: "", cat: "", tags: [], time: "" };
  var data = [];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function uniq(a) { return a.filter(function (v, i) { return a.indexOf(v) === i; }); }
  function daysAgo(dateStr) {
    if (!dateStr) return null;
    var d = new Date(dateStr);
    if (isNaN(d.getTime())) return null;
    return (Date.now() - d.getTime()) / 86400000;
  }

  function load(cb) {
    fetch(INDEX)
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (d) { data = d || []; cb(); })
      .catch(function () { data = []; cb(); });
  }

  function categories() {
    return uniq(data.map(function (x) { return x.category; }).filter(Boolean)).sort();
  }
  function allTags() {
    var t = [];
    data.forEach(function (x) { (x.tags || []).forEach(function (tg) { t.push(tg); }); });
    return uniq(t).sort();
  }

  function matches(x) {
    if (state.cat && x.category !== state.cat) return false;
    if (state.time) {
      var age = daysAgo(x.updated);
      if (age === null || age > state.time) return false;
    }
    if (state.tags.length) {
      var xt = x.tags || [];
      if (!state.tags.every(function (t) { return xt.indexOf(t) > -1; })) return false;
    }
    if (state.q) {
      var q = state.q.toLowerCase();
      var hay = (x.title + " " + (x.desc || "") + " " + (x.tags || []).join(" ") + " " + x.category).toLowerCase();
      if (hay.indexOf(q) === -1) return false;
    }
    return true;
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

  function render() {
    var list = data.filter(matches);
    var countEl = document.getElementById("fsCount");
    var resEl = document.getElementById("fsResults");
    if (countEl) countEl.textContent = "共 " + list.length + " 条结果" + (data.length ? "（全站 " + data.length + " 篇）" : "");
    if (!list.length) {
      resEl.innerHTML = '<div class="fs-empty">没有符合条件的文章，试试放宽筛选条件。</div>';
      return;
    }
    resEl.innerHTML = list.map(cardHTML).join("");
  }

  function buildFilters() {
    var c = document.getElementById("fsCat");
    categories().forEach(function (cat) {
      var o = document.createElement("option"); o.value = cat; o.textContent = cat; c.appendChild(o);
    });
    var box = document.getElementById("fsTags");
    box.innerHTML = "";
    if (!allTags().length) { box.innerHTML = '<span class="tag-chips-hint">暂无标签</span>'; return; }
    allTags().forEach(function (t) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "tag-chip"; b.textContent = t; b.dataset.tag = t;
      b.addEventListener("click", function () {
        var i = state.tags.indexOf(t);
        if (i > -1) { state.tags.splice(i, 1); b.classList.remove("active"); }
        else { state.tags.push(t); b.classList.add("active"); }
        render();
      });
      box.appendChild(b);
    });
  }

  function bind() {
    document.getElementById("fsKeyword").addEventListener("input", function (e) {
      state.q = e.target.value.trim(); render();
    });
    document.getElementById("fsCat").addEventListener("change", function (e) {
      state.cat = e.target.value; render();
    });
    document.getElementById("fsTime").addEventListener("change", function (e) {
      state.time = parseInt(e.target.value, 10) || ""; render();
    });
    document.getElementById("fsReset").addEventListener("click", function () {
      state = { q: "", cat: "", tags: [], time: "" };
      document.getElementById("fsKeyword").value = "";
      document.getElementById("fsCat").value = "";
      document.getElementById("fsTime").value = "";
      document.querySelectorAll("#fsTags .tag-chip.active").forEach(function (b) { b.classList.remove("active"); });
      render();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!document.getElementById("fsResults")) return;
    bind();
    load(function () { buildFilters(); render(); });
  });
})();
