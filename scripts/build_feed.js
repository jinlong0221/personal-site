#!/usr/bin/env node
'use strict';
/**
 * build_feed.js — 聚合多源内容更新为统一时间线 feed.json
 *
 * 数据源（任一缺失/异常都不影响其余，互不脱节）：
 *   - static/data/microblog.json   碎碎念（主人随手记）
 *   - static/typhoon.json         台风实时（仅在 active 时出一条）
 *   - content/original/*.md       原创发布（后台自助写入）
 * 输出：static/data/feed.json
 *
 * 设计边界（严谨约定，勿改）：
 *   - 更新日志（changelog.json）是「站点维护记录」，不属于首页内容动态，
 *     只在 changelog.html 独立呈现（经首页「目录 → 更新日志」可达）。
 *     严禁把 changelog 注入本 feed，否则维护记录会污染首页时间线。
 *   - 家庭旅行（travel）属隐私内容，仅在加密后的 travel.html 凭密码访问，
 *     不进入公开时间线 feed.json，避免隐私行程/照片泄露到首页。
 *
 * 由 CI（deploy.yml，hugo 之前）与本地提交前运行，保证首页时间线与碎碎念页始终最新。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.dirname(__dirname); // hugo-site（scripts 的上一级）
const STATIC = path.join(ROOT, 'static');
const DATA = path.join(STATIC, 'data');

const ACCENT = { '碎碎念': '#8B7FD6', '台风': '#2E8BC0' };

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

// 轻量 frontmatter 解析（项目无 YAML 依赖，仅覆盖后台写入的受控结构）
function stripVal(v) {
  return v.replace(/^["']|["']$/g, '');
}
function parseFrontmatter(raw) {
  var m = raw.match(/^---\s*\n([\s\S]*?)\n---\s*\n?/);
  if (!m) return null;
  var lines = m[1].split('\n');
  var out = {};
  var curKey = null;
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    if (!line.trim()) continue;
    if (/^\s*-\s+/.test(line) && curKey && Array.isArray(out[curKey])) {
      out[curKey].push(stripVal(line.trim().replace(/^\s*-\s+/, '')));
      continue;
    }
    var idx = line.indexOf(':');
    if (idx < 0) continue;
    var key = line.slice(0, idx).trim();
    var val = line.slice(idx + 1).trim();
    if (!key) continue;
    if (val === '') {
      out[key] = [];
      curKey = key;
    } else {
      out[key] = stripVal(val);
      curKey = null;
    }
  }
  return out;
}
function normTags(t) {
  if (Array.isArray(t)) return t.map(String).map(function (x) { return x.trim(); }).filter(Boolean);
  if (typeof t === 'string') {
    var s = t.trim();
    if (s.charAt(0) === '[' && s.charAt(s.length - 1) === ']') s = s.slice(1, -1);
    return s.split(',').map(function (x) { return x.trim().replace(/^["']|["']$/g, ''); }).filter(Boolean);
  }
  return [];
}
function bodyExcerpt(raw, n) {
  var body = raw.replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, '');
  var txt = body.replace(/^#+\s+.*$/gm, '').replace(/[*_`>#]/g, '').replace(/\s+/g, ' ').trim();
  return txt.length > n ? txt.slice(0, n) + '…' : txt;
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

// 2) 更新日志（changelog.json）刻意不纳入本 feed —— 它是站点维护记录，
//    只在 changelog.html 独立呈现。混入首页时间线会把「导航栏修复」这类
//    维护条目伪装成内容动态，干扰读者。请勿在此处重新引入。

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

// 0) 原创发布（后台自助写入 content/original/*.md，type=原创，带 board 字段）
var ORIGINAL_DIR = path.join(ROOT, 'content', 'original');
var BOARD_PAGE = {
  '中药材': 'herbs.html', '养生茶': 'health-tea.html', '文玩手串': 'bracelet.html',
  '特斯拉': 'tesla.html', '漫威宇宙': 'marvel.html', '紫砂艺术': 'zisha.html',
  '游戏主机': 'console.html', 'ChinaJoy': 'chinajoy.html', '光辉电力': 'guanghui.html',
  '踩坑记': 'pitfalls.html', '高考查分': 'gaokao.html', '农田气象': 'xintan-weather.html',
  '游戏库': 'games.html', '台风监测': 'typhoon.html'
};
var BOARD_ACCENT = {
  '中药材': '#3B9C6B', '养生茶': '#6FA85B', '文玩手串': '#B07A3C', '特斯拉': '#E0492F',
  '漫威宇宙': '#C0392B', '紫砂艺术': '#8B5A2B', '游戏主机': '#5B6BB0', 'ChinaJoy': '#D269A0',
  '光辉电力': '#E0A92F', '踩坑记': '#9B7BD4', '高考查分': '#2E8BC0', '农田气象': '#4FA3C7',
  '游戏库': '#7A8BD0', '台风监测': '#2E8BC0', '随笔杂记': '#8B7FD6'
};
if (fs.existsSync(ORIGINAL_DIR)) {
  fs.readdirSync(ORIGINAL_DIR).forEach(function (fn) {
    if (!/\.md$/.test(fn) || fn === '_index.md') return;
    var raw = fs.readFileSync(path.join(ORIGINAL_DIR, fn), 'utf8');
    var fm = parseFrontmatter(raw);
    if (!fm || !fm.title) return;
    var board = fm.board || '随笔杂记';
    var slug = fn.replace(/\.md$/, '');
    items.push({
      id: 'og-' + slug,
      type: '原创',
      date: String(fm.date || '').slice(0, 10),
      time: '',
      title: fm.title,
      text: fm.summary || bodyExcerpt(raw, 120),
      tags: normTags(fm.tags),
      link: 'original/' + slug + '/',
      linkText: '阅读全文 →',
      cover: fm.cover || '',
      accent: BOARD_ACCENT[board] || ACCENT['碎碎念'],
      board: board
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
