#!/usr/bin/env node
'use strict';
/**
 * build_feed.js — 聚合多源更新为统一时间线 feed.json
 *
 * 数据源（任一缺失/异常都不影响其余，互不脱节）：
 *   - static/data/microblog.json   碎碎念（主人随手记）
 *   - static/data/changelog.json  手工更新日志（站点里程碑）
 *   - static/typhoon.json         台风实时（仅在 active 时出一条）
 *   - static/data/travel.json     家庭旅行（取最近 2 次出行）
 * 输出：static/data/feed.json
 *
 * 由 CI（deploy.yml，hugo 之前）与本地提交前运行，保证首页时间线与碎碎念页始终最新。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.dirname(__dirname); // hugo-site（scripts 的上一级）
const STATIC = path.join(ROOT, 'static');
const DATA = path.join(STATIC, 'data');

const ACCENT = { '碎碎念': '#8B7FD6', '动态': '#3B93DD', '台风': '#2E8BC0', '旅行': '#D98A5C' };

function readJSON(p) {
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch (e) {
    return null;
  }
}

function tsOf(date, time) {
  const d = (date || '').trim();
  const t = (time || '').trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(d)) {
    const dt = new Date(d + 'T' + (t || '00:00:00'));
    if (!isNaN(dt.getTime())) return dt.getTime();
  }
  // 旅行等非 ISO 日期，从字符串里取年份兜底
  const y = (d + ' ' + t).match(/\d{4}/);
  if (y) {
    const dt = new Date(y[0] + '-06-01T00:00:00');
    if (!isNaN(dt.getTime())) return dt.getTime();
  }
  return 0;
}

function trunc(s, n) {
  s = String(s || '');
  return s.length > n ? s.slice(0, n) + '…' : s;
}

const items = [];

// 1) 碎碎念
const mb = readJSON(path.join(DATA, 'microblog.json'));
if (Array.isArray(mb)) {
  mb.forEach(function (it, i) {
    if (!it || !it.date) return;
    items.push({
      id: 'mb-' + it.date + '-' + (it.time || i),
      type: '碎碎念',
      date: it.date,
      time: it.time || '',
      title: '',
      text: it.text || '',
      tags: Array.isArray(it.tags) ? it.tags : [],
      link: '',
      linkText: '',
      cover: '',
      accent: ACCENT['碎碎念']
    });
  });
}

// 2) 手工更新日志（仅取最近 12 条，避免历史里程碑淹没时间线；完整归档见 changelog.html）
const cl = readJSON(path.join(DATA, 'changelog.json'));
if (Array.isArray(cl)) {
  cl.slice(0, 12).forEach(function (it, i) {
    if (!it || !it.date) return;
    const content = it.content || it.desc || it.title || '';
    if (!content) return;
    const head = trunc((content.split(/[。！\n]/)[0] || content), 80);
    items.push({
      id: 'cl-' + it.date + '-' + i,
      type: '动态',
      date: it.date,
      time: it.time || '',
      title: '',
      text: head,
      tags: [],
      link: 'changelog.html',
      linkText: '查看更新日志',
      cover: '',
      accent: ACCENT['动态']
    });
  });
}

// 3) 台风实时（仅在 active：warn/danger/info）
const ty = readJSON(path.join(STATIC, 'typhoon.json'));
if (ty && ty.statusLevel && ['warn', 'danger', 'info'].indexOf(ty.statusLevel) >= 0) {
  const datePart = (ty.updated || '').slice(0, 10);
  const timePart = (ty.updated || '').slice(11, 16);
  const levelName = ty.statusLevel === 'warn' ? '在效监测' : ty.statusLevel === 'danger' ? '高风险预警' : '收尾/解除';
  const short = ty.statusShort || levelName;
  items.push({
    id: 'ty-' + (datePart || 'x'),
    type: '台风',
    date: datePart || '',
    time: timePart || '',
    title: (ty.name || '台风') + ' · ' + short,
    text: trunc(ty.status || '', 120),
    tags: ['台风'],
    link: 'typhoon.html',
    linkText: '查看实时路径',
    cover: '',
    accent: ACCENT['台风']
  });
}

// 4) 旅行（最近 2 次出行）
const tv = readJSON(path.join(DATA, 'travel.json'));
if (tv && Array.isArray(tv.trips)) {
  const trips = tv.trips.slice().sort(function (a, b) {
    return tsOf(b.id || b.date || '', '') - tsOf(a.id || a.date || '', '');
  }).slice(0, 2);
  trips.forEach(function (tr) {
    if (!tr || !tr.id) return;
    const cover = tr.cover ? ('img/travel/' + tr.cover + '.webp') : '';
    items.push({
      id: 'tr-' + tr.id,
      type: '旅行',
      date: '',
      time: tr.date || '',
      title: tr.title || '旅行',
      text: tr.note || '',
      tags: ['旅行'],
      link: 'travel.html',
      linkText: '看旅行记录',
      cover: cover,
      accent: ACCENT['旅行']
    });
  });
}

// 排序：新 → 旧
items.sort(function (a, b) {
  return tsOf(b.date, b.time) - tsOf(a.date, a.time);
});

// 安全上限：时间线最多 50 条，超出截断（防极端情况下页面过长）
if (items.length > 50) items.length = 50;

const out = { generatedAt: new Date().toISOString(), items: items };
fs.writeFileSync(path.join(DATA, 'feed.json'), JSON.stringify(out, null, 2) + '\n', 'utf8');
console.log('[build_feed] wrote ' + items.length + ' items -> static/data/feed.json');
