/* =============================================================
 * 通用倒计时组件（与任意页面解耦，不依赖万年历 lunar 引擎）
 * 用法：在任意元素上加 data-countdown，并指定一种目标：
 *   data-target="2026-10-01"              绝对日期（单值）
 *   data-annual="10-01"                   每年重复的 MM-DD（取下一个未到来的）
 *   data-dates="2027-02-06,2028-01-26"     显式候选列表（按时间取首个未到来的；适合春节/端午/中秋等农历浮动节日）
 * 可选属性：
 *   data-label="距国庆"   前缀文案（缺省不显示）
 *   data-past="已结束"    目标已过期时的文案（缺省"已结束"）
 *   data-zero="今天"      目标为今天时的文案（缺省"今天"）
 *   data-format="num"     仅输出数字（适用于外层已自备标签/单位的场景）
 * 渲染：默认输出 <span class="cd-label">…</span><b class="cd-num">N</b><span class="cd-unit">天</span>
 * 更新：加载时计算一次，并每 60 秒校准（跨天自动刷新）。
 * ============================================================= */
(function () {
  'use strict';

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function startOfToday() {
    var n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }

  // 解析候选目标日期（绝对或列表），返回「今天及以后」中最接近的一个
  function resolveTarget(el) {
    var now = startOfToday();
    var dates = [];

    if (el.hasAttribute('data-dates')) {
      el.getAttribute('data-dates').split(',').forEach(function (s) {
        var p = s.trim(); if (!p) return;
        var t = parseISO(p); if (t) dates.push(t);
      });
    } else if (el.hasAttribute('data-annual')) {
      var md = el.getAttribute('data-annual').trim();
      var m = parseInt(md.slice(0, 2), 10), d = parseInt(md.slice(3, 5), 10);
      var y = now.getFullYear();
      var cand = new Date(y, m - 1, d);
      if (cand < now) cand = new Date(y + 1, m - 1, d);
      dates.push(cand);
    } else if (el.hasAttribute('data-target')) {
      var t = parseISO(el.getAttribute('data-target').trim());
      if (t) dates.push(t);
    }

    if (!dates.length) return null;
    dates.sort(function (a, b) { return a - b; });
    for (var i = 0; i < dates.length; i++) {
      if (dates[i] >= now) return dates[i];
    }
    return dates[dates.length - 1]; // 全部已过期 → 取最后一个
  }

  function parseISO(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (!m) return null;
    return new Date(+m[1], +m[2] - 1, +m[3]);
  }

  function daysBetween(target) {
    var ms = target.getTime() - startOfToday().getTime();
    return Math.round(ms / 86400000);
  }

  function render(el) {
    var target = resolveTarget(el);
    if (!target) {
      el.textContent = '—';
      return;
    }
    var diff = daysBetween(target);
    var label = el.getAttribute('data-label') || '';
    var past = el.getAttribute('data-past') || '已结束';
    var zero = el.getAttribute('data-zero') || '今天';
    var fmt = el.getAttribute('data-format') || '';

    if (diff < 0) {
      if (fmt === 'num') { el.textContent = past; }
      else { el.innerHTML = (label ? '<span class="cd-label">' + label + '</span>' : '') + '<span class="cd-end">' + past + '</span>'; }
      el.classList.add('cd-passed');
      el.classList.remove('is-soon');
      return;
    }
    if (diff === 0) {
      if (fmt === 'num') { el.textContent = zero; }
      else { el.innerHTML = (label ? '<span class="cd-label">' + label + '</span>' : '') + '<b class="cd-num">' + zero + '</b>'; }
      el.classList.remove('cd-passed', 'is-soon');
      return;
    }
    if (fmt === 'num') {
      el.textContent = String(diff);
    } else {
      el.innerHTML = (label ? '<span class="cd-label">' + label + '</span>' : '') +
        '<b class="cd-num">' + diff + '</b><span class="cd-unit">天</span>';
    }
    el.classList.remove('cd-passed');
    el.classList.toggle('is-soon', diff <= 30);
  }

  function init() {
    var els = document.querySelectorAll('[data-countdown]');
    for (var i = 0; i < els.length; i++) render(els[i]);
    // 跨天校准
    setInterval(function () {
      for (var j = 0; j < els.length; j++) render(els[j]);
    }, 60000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
