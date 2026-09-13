/**
 * 漫威正在热映票房加载器
 * 读取 marvel-boxoffice.json 并渲染最新上映漫威电影的实时票房卡。
 * 由每日自动化（automation-1783388608608）刷新 JSON，页面每日自动呈现最新数据。
 */
(function () {
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
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
      return '<div class="mv-bo-card"><div class="mv-bo-val">' + esc(c.v) +
        '</div><div class="mv-bo-label">' + esc(c.l) + '</div></div>';
    }).join('') + '</div>';

    var dateBits = [];
    if (m.releaseDateCn) dateBits.push('内地 ' + m.releaseDateCn);
    if (m.releaseDate && m.releaseDate !== m.releaseDateCn) dateBits.push('北美 ' + m.releaseDate);
    var meta = '<p class="mv-bo-meta"><b>' + esc(m.title) + '</b>' +
      (m.titleEn ? ' · ' + esc(m.titleEn) : '') +
      (dateBits.length ? ' · 上映 ' + esc(dateBits.join(' / ')) : '') +
      (m.status ? ' · ' + esc(m.status) : '') + '</p>';

    var miles = (m.milestones || []).map(function (x) {
      return '<li>' + esc(x) + '</li>';
    }).join('');
    var milesHtml = miles ? '<ul class="mv-bo-miles">' + miles + '</ul>' : '';

    var note = m.note ? '<p class="mv-bo-note">' + esc(m.note) + '</p>' : '';

    wrap.innerHTML = grid + meta + milesHtml + note;

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
