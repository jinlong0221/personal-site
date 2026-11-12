/**
 * 漫威正在热映票房加载器
 * 读取 marvel-boxoffice.json 并渲染最新上映漫威电影的实时票房卡。
 * 由每日自动化（automation-1783388608608）刷新 JSON，页面每日自动呈现最新数据。
 *
 * 渲染约定（避免「一大段文字」）：
 *  - 四宫格只显示每条票房的「头条数字」（干净数值）；
 *  - 当日口径用 movie.status 首条已校对摘要（解析 **粗体**）直接展示；
 *  - 历史复核记录 / 里程碑（机器人内部对账流水）不再渲染到公开页面，仅在 JSON 留底；
 *  - ** 粗体按 <b> 处理，杜绝裸星号。
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

  // 从一段票房文本里抽取「主金额」：优先匹配关键词 kw 之后的首个 $(美元) 或 ¥…亿(人民币)。
  // 修复无 ** 标记时 headline() 退化成「复搜」的问题，并为走势图提供干净数值。
  function money(text, kw) {
    if (!text) return null;
    var t = String(text).replace(/【[^】]*】/g, ' ');
    var pool = t;
    if (kw) {
      var i = t.indexOf(kw);
      if (i >= 0) pool = t.slice(i);
    }
    // 取「离关键词最近」的首个金额（美元或人民币），避免段落后文重提别的值被误抓
    var usdM = pool.match(/\$([\d,]+)(?:\.(\d+))?\s*([BM])?/);
    var cnyM = pool.match(/¥\s*([\d,]+)(?:\.(\d+))?\s*亿/);
    var usdPos = usdM ? usdM.index : Infinity;
    var cnyPos = cnyM ? cnyM.index : Infinity;
    if (cnyPos < usdPos && cnyM) {
      var c = parseFloat(cnyM[1].replace(/,/g, '') + (cnyM[2] ? '.' + cnyM[2] : ''));
      return { v: c, unit: 'CNY' };
    }
    if (usdM) {
      var n = parseFloat(usdM[1].replace(/,/g, '') + (usdM[2] ? '.' + usdM[2] : ''));
      if (usdM[3] === 'M') n = n / 1000;
      else if (usdM[3] !== 'B') n = n / 1e9;   // 无单位的大额美元按「美元原数」折算为 B
      return { v: n, unit: 'USD' };
    }
    if (cnyM) {
      var c2 = parseFloat(cnyM[1].replace(/,/g, '') + (cnyM[2] ? '.' + cnyM[2] : ''));
      return { v: c2, unit: 'CNY' };
    }
    return null;
  }

  // 美元统一以 B 为单位展示，保证四宫格单位一致
  function fmtUSD(b) {
    if (b == null) return '—';
    return '$' + b.toFixed(2) + 'B';
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
    var ww = money(bo.worldwide, '');
    var dom = money(bo.domestic, '北美');
    var intl = money(bo.international, '海外');
    var cn = money(bo.china, '中国内地');
    var cards = [
      { v: fmtUSD(ww && ww.unit === 'USD' ? ww.v : null), l: '全球累计' },
      { v: fmtUSD(dom && dom.unit === 'USD' ? dom.v : null), l: '北美' },
      { v: fmtUSD(intl && intl.unit === 'USD' ? intl.v : null), l: '海外合计' },
      { v: cn && cn.unit === 'CNY' ? '¥' + cn.v.toFixed(2) + '亿' : (cn && cn.unit === 'USD' ? fmtUSD(cn.v) : '—'), l: '中国内地' }
    ];
    var grid = '<div class="mv-bo-grid">' + cards.map(function (c) {
      return '<div class="mv-bo-card"><div class="mv-bo-val">' + esc(c.v) +
        '</div><div class="mv-bo-label">' + esc(c.l) + '</div></div>';
    }).join('') + '</div>';

    // 票房构成走势条：仅当三项美元数值齐全时显示，避免误导
    var chartHtml = '';
    if (ww && ww.unit === 'USD' && dom && dom.unit === 'USD' && intl && intl.unit === 'USD' && ww.v > 0) {
      var pct = function (x) { return Math.max(2, Math.round(x / ww.v * 100)); };
      chartHtml = '<div class="mv-bo-chart">' +
        '<div class="mv-bo-chart-h">票房构成（美元口径）</div>' +
        '<div class="mv-bo-bar"><span class="mv-bo-bar-l">全球累计</span><div class="mv-bo-bar-t"><i class="mv-bo-bar-f" style="width:100%"></i></div><span class="mv-bo-bar-v">' + fmtUSD(ww.v) + '</span></div>' +
        '<div class="mv-bo-bar"><span class="mv-bo-bar-l">北美</span><div class="mv-bo-bar-t"><i class="mv-bo-bar-f" style="width:' + pct(dom.v) + '%"></i></div><span class="mv-bo-bar-v">' + fmtUSD(dom.v) + '</span></div>' +
        '<div class="mv-bo-bar"><span class="mv-bo-bar-l">海外合计</span><div class="mv-bo-bar-t"><i class="mv-bo-bar-f" style="width:' + pct(intl.v) + '%"></i></div><span class="mv-bo-bar-v">' + fmtUSD(intl.v) + '</span></div>' +
        '<div class="mv-bo-chart-note">海外合计含中国内地约 ¥' + (cn && cn.unit === 'CNY' ? cn.v.toFixed(2) : '--') + '亿；柱状为占全球累计的比例。</div>' +
        '</div>';
    }

    // 当前追踪影片标题 + 上映日（扫码即知是哪部）
    var titleHtml = '<p class="mv-bo-title"><b>' + esc(m.title) + '</b>' +
      (m.titleEn ? ' <span class="mv-bo-en">' + esc(m.titleEn) + '</span>' : '') +
      (m.releaseDateCn ? ' <span class="mv-bo-date">内地 ' + esc(m.releaseDateCn) + '</span>' : '') +
      '</p>';

    // 当日口径：movie.status 可能包含多条复核（用 ｜ 分隔），
    // 只把最新一条展开显示，并按 ；拆成要点列表，避免一屏大段文字；
    // 历史复核折叠到 <details> 里，和里程碑保持一致。
    var statusHtml = '';
    if (m.status) {
      var entries = String(m.status).split('｜').map(function (s) { return s.trim(); }).filter(Boolean);
      var latest = entries[0] || '';

      if (latest) {
        var bullets = latest.split(/；|;/).map(function (s) { return s.trim(); }).filter(Boolean);
        if (bullets.length > 1) {
          statusHtml += '<ul class="mv-bo-status-list">' + bullets.map(function (b) {
            return '<li class="mv-bo-status-item">' + md(b) + '</li>';
          }).join('') + '</ul>';
        } else {
          statusHtml += '<p class="mv-bo-status">' + md(latest) + '</p>';
        }
      }
    }

    var note = m.note ? '<p class="mv-bo-note">' + md(m.note) + '</p>' : '';

    wrap.innerHTML = titleHtml + grid + chartHtml + statusHtml + note;

    var up = document.getElementById('boUpdated');
    if (up && data.updated) up.textContent = data.updated;
  }

  function loadBo() {
    fetch('marvel-boxoffice.json?t=' + Math.floor(Date.now() / 600000))
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
