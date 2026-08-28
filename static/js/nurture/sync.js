// 灵圃·沉香养成 —— 云端同步客户端
// 依赖：window.Visitor（身份卡，含 token / exportCard / importCard）、window.Nurture（core.js）
// 后端：Cloudflare Workers + KV（见 backend/nurture-worker/worker.js）
//
// 功能：
//   1) 自动/手动云端备份（离开页面用 sendBeacon 兜底，防丢）
//   2) 进入页面检测远程是否有更新的存档，可一键恢复（跨设备）
//   3) 香道榜、访客晒图 的拉取与发布
//
// 部署后请把下面的 API 改成你的 Worker 地址。

(function () {
  'use strict';

  // ====== 部署后改成你的 Worker 地址 ======
  var API = 'https://longxiong-nurture.YOURSUB.workers.dev';
  // =========================================

  var EP = API + '/api/nurture';
  var V = null;          // Visitor
  var dirty = false;
  var flushTimer = null;

  function $(s) { return document.querySelector(s); }

  function creds() {
    var v = V && V.get();
    if (!v || !v.token) return null;
    return v;
  }

  // ---------- 小工具 ----------
  function nowStr() {
    var d = new Date();
    return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }
  function toast(title, text, kind) {
    var wrap = $('#toast');
    if (!wrap) return;
    var t = document.createElement('div');
    t.className = 'toast toast-' + (kind || 'info');
    t.innerHTML = '<div class="toast-t">' + title + '</div><div class="toast-x">' + text + '</div>';
    wrap.appendChild(t);
    requestAnimationFrame(function () { t.classList.add('show'); });
    setTimeout(function () { t.classList.remove('show'); setTimeout(function () { t.remove(); }, 400); }, 3200);
  }
  function setStatus(text, kind) {
    var el = $('#cloudStatus');
    if (!el) return;
    el.textContent = text;
    el.className = 'cloud-status' + (kind ? ' ' + kind : '');
  }

  // ---------- 网络 ----------
  function readJSON(req) {
    return req.then(function (r) { return r.json().catch(function () { return { ok: false }; }); });
  }
  function apiPost(path, obj) {
    return readJSON(fetch(EP + path, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(obj)
    }));
  }
  // 离开页面用 beacon（text/plain，绕过预检，服务器照常解析 JSON）
  function beaconSave(state) {
    var v = creds();
    if (!v) return false;
    try {
      var blob = new Blob([JSON.stringify({ id: v.id, token: v.token, name: v.name, state: state })], { type: 'text/plain' });
      return navigator.sendBeacon(EP, blob);
    } catch (e) { return false; }
  }

  // ---------- 备份 ----------
  function flush() {
    if (!dirty) return;
    dirty = false;
    var v = creds();
    if (!v || !window.Nurture) return;
    var state = window.Nurture.get();
    if (!state) return;
    apiPost('', { id: v.id, token: v.token, name: v.name, state: state }).then(function (r) {
      if (r && r.ok) setStatus('已备份云端 · ' + nowStr(), 'ok');
      else if (r && r.reason === 'auth') setStatus('身份不符，请重新导入身份卡', 'bad');
      else setStatus('备份失败，稍后重试', 'warn');
    }).catch(function () { setStatus('备份失败（网络）', 'warn'); });
  }
  function scheduleFlush() {
    if (flushTimer) return;
    flushTimer = setTimeout(function () { flushTimer = null; flush(); }, 15000);
  }
  function backupNow() {
    var v = creds();
    if (!v) { setStatus('请先导出并导入身份卡以启用云端', 'warn'); return; }
    setStatus('备份中…');
    var state = window.Nurture.get();
    apiPost('', { id: v.id, token: v.token, name: v.name, state: state }).then(function (r) {
      if (r && r.ok) { setStatus('已备份云端 · ' + nowStr(), 'ok'); loadLeaderboard(); }
      else if (r && r.reason === 'auth') setStatus('身份不符，请重新导入身份卡', 'bad');
      else setStatus('备份失败，稍后重试', 'warn');
    }).catch(function () { setStatus('备份失败（网络）', 'warn'); });
  }

  // ---------- 恢复 ----------
  function checkRemote() {
    var v = creds();
    if (!v) { setStatus('未启用云端（导出身份卡可启用）', ''); return; }
    setStatus('连接云端中…');
    fetch(EP + '?id=' + encodeURIComponent(v.id) + '&token=' + encodeURIComponent(v.token))
      .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
      .then(function (r) {
        if (!r || !r.ok || !r.state) { setStatus('云端暂无存档，操作后会自动备份', ''); return; }
        var local = window.Nurture.get();
        var remoteAt = r.updatedAt || 0;
        var localAt = (local && local.lastSeen) || 0;
        if (remoteAt > localAt + 1000) {
          setStatus('云端有更新的存档', 'ok');
          showRestore(r.state, remoteAt);
        } else {
          setStatus('已与云端同步 · ' + nowStr(), 'ok');
          loadLeaderboard();
        }
      })
      .catch(function () { setStatus('云端连接失败', 'warn'); });
  }
  function showRestore(state, at) {
    var box = $('#cloudCode');
    if (!box) return;
    box.style.display = 'block';
    box.innerHTML =
      '<div class="restore-banner">检测到云端有一份更新的存档（' + new Date(at).toLocaleString('zh-CN') + '），是否恢复？' +
      '<div class="restore-actions">' +
      '<button class="cf-btn cf-restore" id="doRestore">恢复云端</button>' +
      '<button class="cf-btn" id="skipRestore">暂不</button>' +
      '</div></div>';
    $('#doRestore').addEventListener('click', function () {
      try { localStorage.setItem('lx_nurture_v1', JSON.stringify(state)); } catch (e) {}
      location.reload();
    });
    $('#skipRestore').addEventListener('click', function () {
      try { localStorage.setItem('lx_nurture_ignore_' + at, '1'); } catch (e) {}
      box.style.display = 'none';
    });
  }

  // ---------- 导出 / 导入身份卡 ----------
  function exportCard() {
    var v = V && V.get();
    if (!v) return;
    var code = V.exportCard();
    var box = $('#cloudCode');
    if (!box) return;
    box.style.display = 'block';
    box.innerHTML = '<div class="code-label">身份密令（复制保存，换设备导入即读回云端存档）：</div>' +
      '<textarea class="code-area" id="codeArea" readonly>' + code + '</textarea>' +
      '<div class="restore-actions"><button class="cf-btn" id="copyCode">复制</button></div>';
    $('#copyCode').addEventListener('click', function () {
      var ta = $('#codeArea'); ta.select();
      try { document.execCommand('copy'); toast('已复制', '身份密令已复制到剪贴板', 'ok'); }
      catch (e) { toast('请手动复制', '选中文本后复制', 'warn'); }
    });
  }
  function importCard() {
    var code = window.prompt('粘贴你的身份密令：');
    if (!code) return;
    var ok = V.importCard(code);
    if (ok) {
      toast('导入成功', '正在连接云端存档…', 'ok');
      setStatus('已导入，连接云端中…');
      // 重新渲染身份卡（visitor 已更新）
      if (window.renderVisitorCard) window.renderVisitorCard();
      checkRemote();
      loadLeaderboard();
    } else {
      toast('导入失败', '密令格式不正确', 'bad');
    }
  }

  // ---------- 香道榜 ----------
  function loadLeaderboard() {
    var box = $('#rankList');
    if (!box) return;
    fetch(EP + '/leaderboard?limit=50').then(function (r) { return r.json().catch(function () { return { ok: false, list: [] }; }); })
      .then(function (r) {
        var list = (r && r.list) || [];
        var cnt = $('#rankCount');
        if (cnt) cnt.textContent = list.length ? (list.length + ' 位香友') : '';
        if (!list.length) { box.innerHTML = '<div class="empty-hint">还没有人登上香道榜。养护你的沉香树，自动上榜。</div>'; return; }
        box.innerHTML = '';
        list.forEach(function (p, i) {
          var row = document.createElement('div');
          row.className = 'rank-row';
          row.innerHTML =
            '<div class="rank-no">' + (i + 1) + '</div>' +
            '<div class="rank-name">' + escapeHtml(p.name) + '</div>' +
            '<div class="rank-rank">' + escapeHtml(p.rank) + '</div>' +
            '<div class="rank-stat">藏 ' + p.coll + ' · 采 ' + p.total + '</div>';
          box.appendChild(row);
        });
      }).catch(function () { box.innerHTML = '<div class="empty-hint">榜单加载失败。</div>'; });
  }

  // ---------- 访客晒图 ----------
  function loadShowcase() {
    var box = $('#showList');
    if (!box) return;
    fetch(EP + '/showcase?limit=30').then(function (r) { return r.json().catch(function () { return { ok: false, list: [] }; }); })
      .then(function (r) {
        var list = (r && r.list) || [];
        if (!list.length) { box.innerHTML = '<div class="empty-hint">还没有人晒香。去收藏阁挑一块沉香晒出来吧。</div>'; return; }
        box.innerHTML = '';
        list.forEach(function (e) {
          var card = document.createElement('div');
          card.className = 'show-card';
          var piece = e.piece || {};
          card.innerHTML =
            '<div class="show-head"><span class="show-name">' + escapeHtml(e.name) + '</span>' +
            '<span class="show-time">' + timeAgo(e.ts) + '</span></div>' +
            '<div class="show-piece">' + (piece.grade === '奇楠' ? '💎' : '🪵') + ' ' + escapeHtml(piece.type || '') + '·' + escapeHtml(piece.grade || '') + ' ' + (piece.weight || 0) + 'g</div>' +
            (e.caption ? '<div class="show-cap">“' + escapeHtml(e.caption) + '”</div>' : '');
          box.appendChild(card);
        });
      }).catch(function () { box.innerHTML = '<div class="empty-hint">晒图加载失败。</div>'; });
  }
  function showcasePost(piece) {
    var v = creds();
    if (!v) { toast('需先启用云端', '导出并导入身份卡后即可晒图', 'warn'); return; }
    var caption = window.prompt('为这块沉香写句寄语（可选）：', '');
    if (caption === null) return; // 取消
    apiPost('/showcase/post', { id: v.id, token: v.token, piece: piece, caption: caption }).then(function (r) {
      if (r && r.ok) { toast('已晒出', '你的沉香已展示在访客晒图', 'ok'); loadShowcase(); }
      else if (r && r.reason === 'auth') toast('身份不符', '请重新导入身份卡', 'bad');
      else toast('晒图失败', '请稍后重试', 'warn');
    }).catch(function () { toast('晒图失败', '网络异常', 'warn'); });
  }

  function timeAgo(ts) {
    var d = Date.now() - (ts || 0);
    if (d < 60000) return '刚刚';
    if (d < 3600000) return Math.floor(d / 60000) + ' 分钟前';
    if (d < 86400000) return Math.floor(d / 3600000) + ' 小时前';
    return Math.floor(d / 86400000) + ' 天前';
  }
  function escapeHtml(s) {
    return ('' + (s == null ? '' : s)).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // ---------- 启动 ----------
  document.addEventListener('DOMContentLoaded', function () {
    if (!window.Visitor || !window.Nurture) { console.error('Visitor/Nurture 未加载'); return; }
    V = window.Visitor;

    // 本地存档改动 → 标记脏，定时/离开时备份
    window.addEventListener('nurture:save', function () { dirty = true; scheduleFlush(); });
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden' && dirty) {
        var s = window.Nurture.get(); if (s) beaconSave(s);
        dirty = false;
      }
    });
    window.addEventListener('pagehide', function () {
      if (dirty) { var s = window.Nurture.get(); if (s) beaconSave(s); dirty = false; }
    });

    // 按钮
    var b = $('#btnBackup'); if (b) b.addEventListener('click', backupNow);
    var im = $('#btnImport'); if (im) im.addEventListener('click', importCard);
    var ex = $('#btnExport'); if (ex) ex.addEventListener('click', exportCard);
    var rs = $('#btnRestore'); if (rs) rs.addEventListener('click', checkRemote);

    // 收藏卡「晒」按钮（事件委托）
    var coll = $('#collection');
    if (coll) coll.addEventListener('click', function (ev) {
      var btn = ev.target.closest && ev.target.closest('.coll-share');
      if (!btn) return;
      var pid = btn.getAttribute('data-pid');
      var piece = findPiece(pid);
      if (piece) showcasePost(piece);
    });

    checkRemote();
    loadLeaderboard();
    loadShowcase();
  });

  function findPiece(pid) {
    var S = window.Nurture && window.Nurture.get();
    if (!S || !S.collection) return null;
    for (var i = 0; i < S.collection.length; i++) if (S.collection[i].id === pid) return S.collection[i];
    return null;
  }

  // 暴露给 ui.js 调用（渲染完身份卡后刷新显示）
  window.NurtureSync = { backupNow: backupNow, checkRemote: checkRemote };
})();
