/**
 * 漫威正在热映票房加载器
 * 读取 marvel-boxoffice.json 并渲染最新上映漫威电影的实时票房卡。
 * 由每日自动化（automation-1783388608608）刷新 JSON，页面每日自动呈现最新数据。
 *
 * 渲染约定（避免「好乱」）：
 *  - 四宫格只显示每条票房的「头条数字」（干净数值），不再把多源长段落塞进卡片；
 *  - 当日口径用 movie.status 这一句已校对摘要（解析 **粗体**）；
 *  - 历史口径 / 里程碑（40+ 条研究笔记）收到可折叠 <details> 里，默认收起、最新在前；
 *  - 数据里偶发的 \n 换行按 <br> 处理，** 粗体按 <b> 处理，杜绝裸星号。
 */
(function () {
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // 把 **粗体** 转成 <b>：先转义再替换，杜绝 XSS
  function md(s) {
    return esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  }

  // 从一条票房字段里抽取「头条数字」：去掉【日期 更新】标签，取首个 **...**；
  // 没有 ** 就取到第一个（或 ；前，保证卡片只显示干净的头条值。
  function headline(s) {
    if (!s) return '—';
    var t = String(s).replace(/【[^】]*】/g, ' ').replace(/\s+/g, ' ').trim();
    var bm = t.match(/\*\*([\s\S]+?)\*\*/);
    if (bm) return bm[1].replace(/\s+/g, ' ').trim();
    var cut = t.split(/[（(。；;]/)[0].trim();
    return cut || t;
  }

  // 含 \n 的长文本拆成多行（\n → <br>），并解析粗体
  function multiline(s) {
    return String(s).split('\n').map(md).join('<br>');
  }

  function renderBo(data) {
    var wrap = document.getElementById('mvBoxoffice');
    if (!wrap) return;
    var m = data && data.movie;
    if (!m) {
      wrap.innerHTML = '<p class="mv-bo-loading">暂无票房数据</p>';
      return;
    }
    var bo = m.boxOffice || {};
    var cards = [
      { v: bo.worldwide || '—', l: '全球累计' },
      { v: bo.domestic || '—', l: '北美' },
      { v: bo.international || '—', l: '海外合计' },
      { v: bo.china || '—', l: '中国内地' }
    ];
    var grid = '<div class="mv-bo-grid">' + cards.map(function (c) {
      return '<div class="mv-bo-card"><div class="mv-bo-val">' + esc(headline(c.v)) +
        '</div><div class="mv-bo-label">' + esc(c.l) + '</div></div>';
    }).join('') + '</div>';

    // 当前追踪影片标题 + 上映日（扫码即知是哪部）
    var titleHtml = '<p class="mv-bo-title"><b>' + esc(m.title) + '</b>' +
      (m.titleEn ? ' <span class="mv-bo-en">' + esc(m.titleEn) + '</span>' : '') +
      (m.releaseDateCn ? ' <span class="mv-bo-date">内地 ' + esc(m.releaseDateCn) + '</span>' : '') +
      '</p>';

    // 当日口径：movie.status 已校对好的当日摘要（解析 ** 粗体）
    var status = m.status ? '<p class="mv-bo-status">' + md(m.status) + '</p>' : '';

    // 历史口径 / 里程碑：折叠，最新在前，避免一屏刷 40+ 条研究笔记
    var miles = (m.milestones || []).slice();
    var milesHtml = '';
    if (miles.length) {
      var items = miles.map(function (x) {
        return '<li class="mv-bo-mile">' + multiline(x) + '</li>';
      }).join('');
      milesHtml =
        '<details class="mv-bo-detail" id="boDetail">' +
        '<summary class="mv-bo-detail-sum">票房口径与里程碑记录（共 ' + miles.length +
        ' 条 · 点击展开）</summary>' +
        '<ul class="mv-bo-miles">' + items + '</ul>' +
        '</details>';
    }

    var note = m.note ? '<p class="mv-bo-note">' + md(m.note) + '</p>' : '';

    wrap.innerHTML = titleHtml + grid + status + milesHtml + note;

    var up = document.getElementById('boUpdated');
    if (up && data.updated) up.textContent = data.updated;
  }

  function loadBo() {
    fetch('marvel-boxoffice.json?v=' + Date.now())
      .then(function (r) {
        if (!r.ok) throw new Error('not found');
        return r.json();
      })
      .then(renderBo)
      .catch(function (e) {
        var w = document.getElementById('mvBoxoffice');
        if (w) w.innerHTML = '<p class="mv-bo-loading">票房数据加载失败，请稍后刷新</p>';
        console.log('[marvel_boxoffice] 加载失败:', e);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadBo);
  } else {
    loadBo();
  }
})();
