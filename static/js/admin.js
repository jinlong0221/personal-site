/**
 * admin.js — 龙兄知识库内容管理后台（纯静态，直连 GitHub Contents API）
 *
 * 设计要点：
 *  - 令牌（细粒度 PAT，仅本仓库 contents:write）存浏览器 localStorage，仅发往 api.github.com。
 *  - 所有写操作 = 往 content/original/*.md 提交，触发现有 GitHub Actions 重建部署（约 1–2 分钟上线）。
 *  - 图片上传到 static/img/uploads/，正文中用 /img/uploads/xxx.jpg 引用。
 *  - 失败有清晰提示；401 自动要求重新登录；绝不白屏。
 */
(function () {
  'use strict';

  var API = 'https://api.github.com/repos/jinlong0221/personal-site/contents/';
  var BRANCH = 'main';
  var TOKEN_KEY = 'lx_admin_token';
  var SITE = 'https://longxiong.vip';

  // 板块列表（须与 scripts/build_feed.js 的 BOARD_PAGE、inject_board_originals.py 的 MAP 一致）
  var BOARDS = [
    { value: '中药材', page: 'herbs.html' },
    { value: '养生茶', page: 'health-tea.html' },
    { value: '文玩手串', page: 'bracelet.html' },
    { value: '特斯拉', page: 'tesla.html' },
    { value: '漫威宇宙', page: 'marvel.html' },
    { value: '紫砂艺术', page: 'zisha.html' },
    { value: '游戏主机', page: 'console.html' },
    { value: 'ChinaJoy', page: 'chinajoy.html' },
    { value: '光辉电力', page: 'guanghui.html' },
    { value: '踩坑记', page: 'pitfalls.html' },
    { value: '高考查分', page: 'gaokao.html' },
    { value: '农田气象', page: 'xintan-weather.html' },
    { value: '游戏库', page: 'games.html' },
    { value: '台风监测', page: 'typhoon.html' },
    { value: '随笔杂记', page: '' }
  ];

  var loginEl = document.getElementById('login');
  var panelEl = document.getElementById('panel');
  var toastEl = document.getElementById('toast');
  var token = localStorage.getItem(TOKEN_KEY) || '';

  // ---------- 工具 ----------
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function stripVal(v) { return v.replace(/^["']|["']$/g, ''); }
  function yamlStr(s) {
    s = String(s == null ? '' : s);
    return '"' + s.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
  }
  function b64encode(s) { return btoa(unescape(encodeURIComponent(s))); }
  function b64decode(b) { return decodeURIComponent(escape(atob(b))); }
  function todayStr() { return new Date().toISOString().slice(0, 10); }
  function slugify(s) {
    return String(s || '').trim().toLowerCase()
      .replace(/[^\w\u4e00-\u9fa5]+/g, '-')
      .replace(/^-+|-+$/g, '').slice(0, 40) || 'post';
  }
  function safeName(s) {
    return String(s || '').replace(/[^A-Za-z0-9._-]/g, '_').slice(0, 60) || 'file';
  }
  function toast(msg, kind) {
    toastEl.textContent = msg;
    toastEl.className = 'toast show' + (kind ? ' ' + kind : '');
    setTimeout(function () { toastEl.className = 'toast'; }, 3200);
  }
  function parseFm(text) {
    var m = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?/);
    if (!m) return {};
    var out = {}, cur = null;
    m[1].split('\n').forEach(function (line) {
      if (!line.trim()) return;
      if (/^\s*-\s+/.test(line) && cur && Array.isArray(out[cur])) {
        out[cur].push(stripVal(line.trim().replace(/^\s*-\s+/, ''))); return;
      }
      var idx = line.indexOf(':'); if (idx < 0) return;
      var k = line.slice(0, idx).trim(), v = line.slice(idx + 1).trim();
      if (!k) return;
      if (v === '') { out[k] = []; cur = k; }
      else { out[k] = stripVal(v); cur = null; }
    });
    return out;
  }

  // ---------- GitHub API ----------
  function api(path, opts) {
    opts = opts || {};
    var url = API + path + (path.indexOf('?') >= 0 ? '&' : '?') + 'ref=' + BRANCH;
    var init = {
      method: opts.method || 'GET',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      }
    };
    if (opts.body) init.body = opts.body;
    return fetch(url, init).then(function (res) {
      var p = res.json ? res.json().catch(function () { return {}; }) : Promise.resolve({});
      return p.then(function (data) {
        if (!res.ok) {
          var err = new Error((data && (data.message || data.error)) || ('HTTP ' + res.status));
          err.status = res.status; err.data = data;
          throw err;
        }
        return data;
      });
    });
  }
  function getFile(path) {
    return api(path).then(function (d) {
      return { content: b64decode(d.content), sha: d.sha, path: d.path, name: d.name };
    });
  }
  function putFile(path, content, message, sha) {
    var body = { message: message, content: b64encode(content), branch: BRANCH, committer: { name: '龙兄', email: 'longxiong@users.noreply.github.com' } };
    if (sha) body.sha = sha;
    return api(path, { method: 'PUT', body: JSON.stringify(body) });
  }
  function deleteFile(path, sha, message) {
    return api(path, { method: 'DELETE', body: JSON.stringify({ message: message, sha: sha, branch: BRANCH }) });
  }

  function buildMarkdown(d) {
    var tags = (d.tags || []).map(function (t) { return String(t).trim(); }).filter(Boolean);
    var fm = '---\n';
    fm += 'title: ' + yamlStr(d.title) + '\n';
    fm += 'date: ' + (d.date || todayStr()) + '\n';
    fm += 'board: ' + yamlStr(d.board) + '\n';
    fm += 'tags: [' + tags.map(yamlStr).join(', ') + ']\n';
    if (d.cover) fm += 'cover: ' + yamlStr(d.cover) + '\n';
    if (d.summary) fm += 'summary: ' + yamlStr(d.summary) + '\n';
    fm += '---\n\n';
    return fm + (d.body || '');
  }

  // ---------- 渲染：登录 ----------
  function renderLogin(reason) {
    panelEl.classList.add('hidden');
    loginEl.classList.remove('hidden');
    loginEl.innerHTML =
      '<p class="login-tip">本后台直连你的 GitHub 仓库。请粘贴一把 <b>细粒度个人访问令牌（PAT）</b>，' +
      '权限只需本仓库的 <b>Contents: 读写</b>。令牌仅保存在你当前浏览器，只发往 api.github.com，' +
      '可随时在 GitHub 撤销。' +
      '<br>生成入口：GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate。</p>' +
      (reason ? '<div class="err-box">' + esc(reason) + '</div>' : '') +
      '<label for="tk">GitHub 细粒度令牌</label>' +
      '<input id="tk" type="password" placeholder="github_pat_xxx" autocomplete="off">' +
      '<div class="row" style="margin-top:14px">' +
      '<button class="btn btn-primary" id="saveToken">保存并进入</button>' +
      '<a class="link" href="' + SITE + '/original/" target="_blank" rel="noopener">查看已发布内容 →</a>' +
      '</div>';
    document.getElementById('saveToken').addEventListener('click', function () {
      var v = document.getElementById('tk').value.trim();
      if (!v) { toast('请先粘贴令牌', 'err'); return; }
      token = v; localStorage.setItem(TOKEN_KEY, token);
      renderPanel();
    });
  }

  // ---------- 渲染：面板 + 列表 ----------
  function renderPanel() {
    loginEl.classList.add('hidden');
    panelEl.classList.remove('hidden');
    panelEl.innerHTML =
      '<div class="topbar">' +
      '<div class="row">' +
      '<button class="btn btn-primary" id="newBtn">+ 新建原创</button>' +
      '<select id="boardFilter" class="grow" style="max-width:220px"></select>' +
      '</div>' +
      '<div class="row">' +
      '<a class="btn btn-ghost btn-sm" href="' + SITE + '/original/" target="_blank" rel="noopener">查看站点</a>' +
      '<button class="btn btn-ghost btn-sm" id="logoutBtn">退出/清除令牌</button>' +
      '</div>' +
      '</div>' +
      '<div id="listWrap"><div class="empty">加载中…</div></div>';

    var sel = document.getElementById('boardFilter');
    sel.innerHTML = '<option value="">全部板块</option>' +
      BOARDS.map(function (b) { return '<option value="' + esc(b.value) + '">' + esc(b.value) + '</option>'; }).join('');
    sel.addEventListener('change', function () { loadList(sel.value); });

    document.getElementById('newBtn').addEventListener('click', function () { openEditor(null, sel.value); });
    document.getElementById('logoutBtn').addEventListener('click', function () {
      localStorage.removeItem(TOKEN_KEY); token = '';
      renderLogin('已清除本地令牌。');
    });

    loadList('');
  }

  function loadList(boardFilter) {
    var wrap = document.getElementById('listWrap');
    wrap.innerHTML = '<div class="empty">加载中…</div>';
    api('content/original').then(function (entries) {
      var files = entries.filter(function (e) {
        return e.type === 'file' && /\.md$/.test(e.name) && e.name !== '_index.md';
      });
      if (!files.length) {
        wrap.innerHTML = '<div class="empty">还没有原创内容。点「新建原创」发第一篇吧。</div>';
        return;
      }
      Promise.all(files.map(function (f) {
        return getFile('content/original/' + f.name).then(function (file) {
          var fm = parseFm(file.content);
          return {
            name: f.name, sha: file.sha, path: file.path,
            title: fm.title || f.name, board: fm.board || '随笔杂记',
            date: String(fm.date || '').slice(0, 10),
            content: file.content
          };
        }).catch(function () { return null; });
      })).then(function (items) {
        items = items.filter(Boolean).sort(function (a, b) {
          return String(b.date).localeCompare(String(a.date));
        });
        renderList(items, boardFilter);
      });
    }).catch(function (err) {
      if (err.status === 401) { localStorage.removeItem(TOKEN_KEY); token = ''; renderLogin('令牌无效或权限不足（需本仓库 Contents 读写）。请重新生成并粘贴。'); }
      else wrap.innerHTML = '<div class="err-box">加载失败：' + esc(err.message) + '</div>';
    });
  }

  function renderList(items, boardFilter) {
    var wrap = document.getElementById('listWrap');
    var shown = boardFilter ? items.filter(function (i) { return i.board === boardFilter; }) : items;
    if (!shown.length) {
      wrap.innerHTML = '<div class="empty">该板块下还没有内容。</div>';
      return;
    }
    var groups = {};
    shown.forEach(function (i) {
      (groups[i.board] = groups[i.board] || []).push(i);
    });
    var html = '';
    Object.keys(groups).forEach(function (board) {
      html += '<div class="group"><h3 class="group-h">' + esc(board) +
        '<span class="group-n">' + groups[board].length + ' 篇</span></h3>';
      groups[board].forEach(function (i) {
        html += '<div class="item">' +
          '<div><div class="item-title">' + esc(i.title) + '</div>' +
          '<div class="item-meta">' + esc(i.date) + ' · ' + esc(i.name) + '</div></div>' +
          '<div class="item-actions">' +
          '<button class="btn btn-ghost btn-sm" data-edit="' + esc(i.name) + '">编辑</button>' +
          '<button class="btn btn-danger btn-sm" data-del="' + esc(i.name) + '" data-sha="' + esc(i.sha) + '">删除</button>' +
          '</div></div>';
      });
      html += '</div>';
    });
    wrap.innerHTML = html;

    wrap.querySelectorAll('[data-edit]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var it = shown.filter(function (x) { return x.name === btn.getAttribute('data-edit'); })[0];
        if (it) openEditor(it, it.board);
      });
    });
    wrap.querySelectorAll('[data-del]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var name = btn.getAttribute('data-del'), sha = btn.getAttribute('data-sha');
        if (!confirm('确定删除《' + name + '》？此操作会提交到 GitHub，删除后不可在本后台恢复（可用 git 历史找回）。')) return;
        deleteFile('content/original/' + name, sha, '删除原创：' + name).then(function () {
          toast('已删除，正在重新构建…', 'ok');
          loadList(document.getElementById('boardFilter').value);
        }).catch(function (err) { toast('删除失败：' + err.message, 'err'); });
      });
    });
  }

  // ---------- 编辑器 ----------
  function openEditor(item, presetBoard) {
    var fm = item ? parseFm(item.content) : {};
    var body = item ? item.content.replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, '') : '';
    var data = {
      title: fm.title || '', date: String(fm.date || '').slice(0, 10) || todayStr(),
      board: fm.board || presetBoard || BOARDS[0].value,
      tags: Array.isArray(fm.tags) ? fm.tags : (typeof fm.tags === 'string' ? fm.tags.replace(/^\[|\]$/g, '').split(',').map(function (s) { return s.trim(); }) : []),
      cover: fm.cover || '', summary: fm.summary || '', body: body
    };

    var mask = document.createElement('div');
    mask.className = 'modal-mask';
    mask.innerHTML =
      '<div class="modal">' +
      '<h2>' + (item ? '编辑：' + esc(item.name) : '新建原创') + '</h2>' +
      '<label>标题</label><input id="f-title" value="' + esc(data.title) + '">' +
      '<div class="row" style="margin-top:14px">' +
      '<div class="grow"><label>发布日期</label><input id="f-date" type="date" value="' + esc(data.date) + '"></div>' +
      '<div class="grow"><label>所属板块</label><select id="f-board">' +
      BOARDS.map(function (b) { return '<option value="' + esc(b.value) + '"' + (b.value === data.board ? ' selected' : '') + '>' + esc(b.value) + '</option>'; }).join('') +
      '</select></div>' +
      '</div>' +
      '<label>标签（逗号分隔）</label><input id="f-tags" value="' + esc(data.tags.join(', ')) + '">' +
      '<label>封面图（可选）</label>' +
      '<div class="row">' +
      '<input id="f-cover" value="' + esc(data.cover) + '" placeholder="/img/uploads/xxx.jpg">' +
      '<button class="btn btn-ghost btn-sm" id="f-up">上传图片</button>' +
      '<input type="file" id="f-file" accept="image/*" class="hidden">' +
      '</div>' +
      '<label>摘要（一句话，可选）</label><input id="f-summary" value="' + esc(data.summary) + '">' +
      '<label>正文（Markdown）</label>' +
      '<div class="row" style="align-items:stretch">' +
      '<textarea id="f-body" style="flex:1">' + esc(data.body) + '</textarea>' +
      '<div class="preview grow" id="f-prev"></div>' +
      '</div>' +
      '<div class="hint">支持 # 标题、**加粗**、*斜体*、列表、- 链接等 Markdown 语法。</div>' +
      '<div class="err-box" id="f-err"></div>' +
      '<div class="row" style="margin-top:16px;justify-content:flex-end">' +
      '<button class="btn btn-ghost" id="f-cancel">取消</button>' +
      '<button class="btn btn-primary" id="f-save">保存并发布</button>' +
      '</div>' +
      '</div>';
    document.body.appendChild(mask);

    var bodyEl = mask.querySelector('#f-body');
    var prevEl = mask.querySelector('#f-prev');
    function renderPrev() {
      if (window.marked) {
        try { prevEl.innerHTML = window.marked.parse(bodyEl.value); return; } catch (e) {}
      }
      prevEl.textContent = bodyEl.value;
    }
    bodyEl.addEventListener('input', renderPrev);
    renderPrev();
    if (!window.marked) {
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/marked@12/marked.min.js';
      s.onload = renderPrev;
      document.head.appendChild(s);
    }

    function close() { mask.remove(); }

    mask.querySelector('#f-cancel').addEventListener('click', close);
    mask.addEventListener('click', function (e) { if (e.target === mask) close(); });

    var fileInput = mask.querySelector('#f-file');
    mask.querySelector('#f-up').addEventListener('click', function () { fileInput.click(); });
    fileInput.addEventListener('change', function () {
      var f = fileInput.files && fileInput.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        var b64 = (reader.result || '').split(',')[1];
        var name = Date.now() + '-' + safeName(f.name);
        putFile('static/img/uploads/' + name, b64, '上传图片：' + name).then(function () {
          mask.querySelector('#f-cover').value = '/img/uploads/' + name;
          toast('图片已上传', 'ok');
        }).catch(function (err) { toast('上传失败：' + err.message, 'err'); });
      };
      reader.readAsDataURL(f);
    });

    mask.querySelector('#f-save').addEventListener('click', function () {
      var d = {
        title: mask.querySelector('#f-title').value.trim(),
        date: mask.querySelector('#f-date').value,
        board: mask.querySelector('#f-board').value,
        tags: mask.querySelector('#f-tags').value.split(',').map(function (t) { return t.trim(); }).filter(Boolean),
        cover: mask.querySelector('#f-cover').value.trim(),
        summary: mask.querySelector('#f-summary').value.trim(),
        body: bodyEl.value
      };
      var errEl = mask.querySelector('#f-err');
      if (!d.title) { errEl.textContent = '标题不能为空'; return; }
      if (!d.body.trim()) { errEl.textContent = '正文不能为空'; return; }
      var md = buildMarkdown(d);
      var name = item ? item.name : (d.date + '-' + slugify(d.title) + '.md');
      var msg = (item ? '更新原创：' : '原创：') + d.title;
      var sha = item ? item.sha : undefined;
      errEl.textContent = '保存中…';
      putFile('content/original/' + name, md, msg, sha).then(function () {
        close();
        toast('已保存，GitHub Actions 正在重新构建，约 1–2 分钟上线', 'ok');
        loadList(document.getElementById('boardFilter').value);
      }).catch(function (err) {
        if (err.status === 409) errEl.textContent = '保存冲突（内容已被改动），请取消后刷新列表重试。';
        else errEl.textContent = '保存失败：' + err.message;
      });
    });
  }

  // ---------- 启动 ----------
  if (token) renderPanel();
  else renderLogin('');
})();
