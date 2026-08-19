#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 static/travel.html —— 「足迹 · 家庭旅行」板块页

数据驱动、可持续更新方式：
  1. 编辑 static/data/travel.json（在 trips 列表里增删出行；每个 trip 内含 cities 列表）
  2. 旅行照片放到  static/img/travel/<行程id>/<城市或 cover>.webp
     （脚本检测到文件才显示，绝不生成 AI 图；无照片则显示优雅的占位卡）
  3. 运行：python3 scripts/build_travel.py
  4. hugo --gc 构建后提交即可

页面结构与站内其它板块页（herbs/console/marvel/chinajoy）完全一致：
  critical CSS -> navbar(内联) -> 面包屑 -> hero -> 统计条 -> 出行档案 -> footer -> 脚本
"""
import os
import re
import json
from collections import OrderedDict
import html as htmllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'static', 'travel.html')
DONOR = os.path.join(ROOT, 'static', 'herbs.html')
DATA = os.path.join(ROOT, 'static', 'data', 'travel.json')
PHOTO_DIR = os.path.join(ROOT, 'static', 'img', 'travel')

SEASON_COLOR = {'春': '#3f7d4f', '夏': '#c2623f', '秋': '#b8822e', '冬': '#3f6b9e'}


def esc(s):
    return htmllib.escape(str(s), quote=True)


def extract(donor_html, start_mark, end_mark, inclusive=True):
    i = donor_html.index(start_mark)
    j = donor_html.index(end_mark, i)
    return donor_html[i:j + len(end_mark)] if inclusive else donor_html[i + len(start_mark):j]


def resolve_photo(rel_path):
    """仅返回真实存在的照片路径；无照片返回 None（不渲染任何占位图/AI 图）"""
    if not rel_path:
        return None
    base = os.path.join(PHOTO_DIR, rel_path)
    for ext in ('webp', 'jpg', 'jpeg', 'png', 'gif'):
        p = base + '.' + ext if not rel_path.lower().endswith(ext) else base
        if os.path.exists(p):
            return 'img/travel/' + (rel_path + '.' + ext if not rel_path.lower().endswith(ext) else rel_path)
    return None


def _pure_img_size(path):
    """纯 Python 读取图片真实宽高（PNG/JPEG/WEBP），无需第三方库。"""
    try:
        with open(path, 'rb') as f:
            sig = f.read(64)
        if sig[:8] == b'\x89PNG\r\n\x1a\n':
            import struct
            return struct.unpack('>II', sig[16:24])
        if sig[:2] == b'\xff\xd8':
            with open(path, 'rb') as f:
                f.read(2)
                while True:
                    b = f.read(1)
                    if not b:
                        return None
                    if b != b'\xff':
                        f.read(1)
                        continue
                    mk = f.read(1)
                    if mk in (b'\xc0', b'\xc1', b'\xc2', b'\xc3', b'\xc5', b'\xc6', b'\xc7',
                              b'\xc9', b'\xca', b'\xcb', b'\xcd', b'\xce', b'\xcf'):
                        f.read(3)
                        import struct
                        h, w = struct.unpack('>HH', f.read(4))
                        return w, h
                    else:
                        import struct
                        ln = struct.unpack('>H', f.read(2))[0]
                        f.read(ln - 2)
        if sig[:4] == b'RIFF' and sig[8:12] == b'WEBP':
            fmt = sig[12:16]
            if fmt == b'VP8X':
                return int.from_bytes(sig[24:27], 'little') + 1, int.from_bytes(sig[27:30], 'little') + 1
            if fmt == b'VP8L':
                b = sig[21:26]
                return ((b[1] & 0x3F) << 8 | b[0]) + 1, ((b[2] << 4) | (b[1] >> 6)) + 1
            if fmt == b'VP8 ':
                import struct
                return struct.unpack('<H', sig[26:28])[0] & 0x3fff, struct.unpack('<H', sig[28:30])[0] & 0x3fff
    except Exception:
        return None
    return None


def img_dims(rel_path):
    """返回 (w, h)；纯 Python 读取，无第三方依赖，始终可用。"""
    if not rel_path:
        return (None, None)
    base = os.path.join(PHOTO_DIR, rel_path)
    p = base if rel_path.lower().endswith(('webp', 'jpg', 'jpeg', 'png', 'gif')) else base + '.webp'
    return _pure_img_size(p) or (None, None)


def stars_html(rating):
    try:
        r = int(rating)
    except (TypeError, ValueError):
        return ''
    if r <= 0:
        return ''
    full = max(0, min(5, r))
    star = ('<svg class="tl-star on" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
            '<path d="M12 2l2.9 6.1 6.6.9-4.8 4.6 1.2 6.5L12 17.8 6.1 20.6 7.3 14 2.5 9.4l6.6-.9z"/></svg>')
    empty = ('<svg class="tl-star" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.6" aria-hidden="true">'
             '<path d="M12 2l2.9 6.1 6.6.9-4.8 4.6 1.2 6.5L12 17.8 6.1 20.6 7.3 14 2.5 9.4l6.6-.9z"/></svg>')
    return '<span class="tl-rating" title="推荐指数 %d/5" aria-label="推荐指数 %d 星">%s%s</span>' % (
        full, full, star * full, empty * (5 - full))


def build_city_card(c, trip_id):
    name = c.get('name', '城市')
    region = c.get('region', '')
    country = c.get('country', '中国')
    days = c.get('days')
    memory = c.get('memory', '')
    kids = c.get('kids', '')
    rating = c.get('rating')
    highlights = c.get('highlights', [])

    region_line = ' · '.join([x for x in (region, country) if x])
    meta_bits = []
    if region_line:
        meta_bits.append(region_line)
    if days:
        meta_bits.append('%d 天' % days)
    meta = ' · '.join(meta_bits)

    # 照片：仅真实存在才显示；否则优雅占位（绝不用 AI 图）
    photo = resolve_photo(c.get('photo', ''))
    if photo:
        cw, ch = img_dims(c.get('photo', ''))
        dim = ' width="%d" height="%d"' % (cw, ch) if (cw and ch) else ' width="320" height="200"'
        img = ('<img class="tl-city-img" src="%s" alt="%s 旅行照" loading="lazy"%s decoding="async">' % (esc(photo), esc(name), dim))
        img_wrap = '<div class="tl-city-img-wrap has-photo">%s</div>' % img
    else:
        img_wrap = ('<div class="tl-city-img-wrap tl-photo-empty">'
                    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
                    '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8" cy="10" r="1.6"/>'
                    '<path d="M3 17l5-5 4 4 3-3 6 6"/></svg>'
                    '<span>照片随后补充</span></div>')

    memory_html = '<p class="tl-city-memory">%s</p>' % esc(memory) if memory else ''
    kids_html = '<p class="tl-city-kids">%s</p>' % esc(kids) if kids else ''
    rating_html = stars_html(rating)

    detail = ''
    if highlights:
        lis = ''.join('<li>%s</li>' % esc(h) for h in highlights)
        detail = ('<button type="button" class="tl-city-toggle" aria-expanded="false">'
                  '<span class="tl-toggle-txt">展开亮点</span> <span class="tl-caret">▾</span></button>'
                  '<div class="tl-city-detail"><ul class="tl-highlights">%s</ul></div>' % lis)

    q = ' '.join([name, region, country, memory, kids] + highlights).lower()

    return (
        '<article class="tl-city" data-q="%s">'
        '%s'
        '<div class="tl-city-body">'
        '  <div class="tl-city-name">%s<span class="tl-city-meta">%s</span></div>'
        '  %s%s%s'
        '  %s'
        '</div>'
        '</article>'
    ) % (esc(q), img_wrap, esc(name), esc(meta), memory_html, kids_html, rating_html, detail)


def region_of(t):
    """返回 (城市级分组键, 完整 region 串)，用于把同一地区的多次出行聚合到一张卡内。"""
    cities = t.get('cities', [])
    if not cities:
        return (t.get('title', t.get('id', '')), t.get('title', t.get('id', '')))
    region = cities[0].get('region', '')
    parts = [p.strip() for p in region.split('·') if p.strip()]
    return (parts[-1] if parts else cities[0].get('name', ''), region)


def build_visit_section(t, latest_id):
    """渲染某地区卡内部的一段「年份出行」：季节/日期 + 城市解说 + 沿途相册。"""
    tid = t.get('id', '')
    year = t.get('year', '')
    season = t.get('season', '')
    title = t.get('title', '')
    date = t.get('date', '')
    days = t.get('days')
    note = t.get('note', '')
    cities = t.get('cities', [])

    season_html = ''
    if season:
        color = SEASON_COLOR.get(season, '#777')
        season_html = '<span class="tl-season" data-season="%s" style="background:%s">%s</span>' % (
            esc(season), color, esc(season))

    latest_badge = '<span class="tl-latest">最新足迹</span>' if tid == latest_id else ''

    meta_bits = []
    if date:
        meta_bits.append(date)
    if days:
        meta_bits.append('%d 天' % days)
    if cities:
        meta_bits.append('%d 城' % len(cities))
    meta = ' · '.join(meta_bits)

    note_html = '<p class="tl-trip-note">%s</p>' % esc(note) if note else ''

    city_cards = '\n'.join(build_city_card(c, tid) for c in cities)

    # 沿途相册：本段真实照片全收录，每张配一句解说（文字对应图片）
    gallery_imgs = []
    for p in t.get('photos', []):
        if isinstance(p, dict):
            src = p.get('src', '')
            caption = p.get('caption', '')
        else:
            src, caption = p, ''
        s = resolve_photo(src)
        if s:
            cap = ('<figcaption class="tl-photo-cap">%s</figcaption>' % esc(caption)) if caption else ''
            w, h = img_dims(src)
            dim_attr = ' width="%d" height="%d"' % (w, h) if (w and h) else ''
            gallery_imgs.append('<figure class="tl-photo">'
                                '<a href="%s" target="_blank" rel="noopener">'
                                '<img src="%s" alt="%s" loading="lazy" decoding="async"%s></a>%s</figure>'
                                % (esc(s), esc(s), esc(caption or title), dim_attr, cap))
    if gallery_imgs:
        gallery_html = ('<div class="tl-gallery-block">'
                        '<div class="tl-gallery-title">沿途 · %d 张（点开看大图）</div>'
                        '<div class="tl-gallery tl-gallery-captioned">%s</div></div>'
                        % (len(gallery_imgs), ''.join(gallery_imgs)))
    else:
        gallery_html = ''

    n_cities = len(cities)
    city_limit = 4
    cities_cls = 'tl-cities'
    city_more = ''
    if n_cities > city_limit:
        cities_cls += ' tl-collapsible'
        city_more = ('<button type="button" class="tl-cities-more" data-limit="%d" data-total="%d" '
                     'aria-expanded="false">展开全部 %d 城 <span class="tl-caret">▾</span></button>'
                     % (city_limit, n_cities, n_cities))

    return (
        '<section class="tl-visit">'
        '  <button type="button" class="tl-visit-head" aria-expanded="false">'
        '    %s'
        '    <span class="tl-visit-date">%s</span>'
        '    <span class="tl-visit-meta">%s</span>'
        '    %s'
        '    <span class="tl-visit-caret" aria-hidden="true">▾</span>'
        '  </button>'
        '  <div class="tl-visit-body">'
        '    %s'
        '    <div class="%s">%s</div>'
        '    %s'
        '    %s'
        '  </div>'
        '</section>'
    ) % (season_html, esc(date), meta, latest_badge, note_html, cities_cls, city_cards, city_more, gallery_html)


def build_region_card(key, region_full, visits, latest_id, open_default=False):
    """把同一地区的多次出行聚合为一张可展开的大卡；卡内按年份分小段。"""
    # 卡封面用该地区最近一次出行的封面（visits 已按年份倒序，[0] 为最新）
    cover_raw = visits[0].get('cover', '')
    cover = resolve_photo(cover_raw)
    cw, ch = img_dims(cover_raw)
    cover_dim = ' width="%d" height="%d"' % (cw, ch) if (cw and ch) else ''
    bg = '<img class="tl-trip-bg" src="%s" alt="%s 出行封面" loading="lazy"%s>' % (esc(cover), esc(key), cover_dim) if cover else ''

    years = ' '.join(str(v.get('year', '')) for v in visits)
    year_disp = ' / '.join(str(v.get('year', '')) for v in visits)
    n_visits = len(visits)

    meta = '去过 %d 次 · %s' % (n_visits, year_disp)

    q_parts = [key, region_full]
    for v in visits:
        q_parts += [v.get('title', ''), v.get('season', ''), v.get('date', ''), v.get('note', '')]
        q_parts += [c.get('name', '') for c in v.get('cities', [])]
        for p in v.get('photos', []):
            if isinstance(p, dict):
                q_parts.append(p.get('caption', ''))
    q = ' '.join(q_parts).lower()

    visit_html = '\n'.join(build_visit_section(v, latest_id) for v in visits)

    open_cls = ' open' if open_default else ''
    aria = 'true' if open_default else 'false'
    hint = '点击展开 · 再点年份查看每次出行的城市解说与照片' if n_visits > 1 else '点击展开 · 点年份查看城市解说与照片'

    return (
        '<article class="tl-trip tl-reveal%s" data-year="%s" data-n="%d" data-q="%s">'
        '  <button type="button" class="tl-trip-head" aria-expanded="%s">'
        '    %s'
        '    <span class="tl-trip-head-inner">'
        '      <span class="tl-trip-titles">'
        '        <span class="tl-trip-title">%s <span class="tl-trip-region">%s</span></span>'
        '        <span class="tl-trip-meta">%s</span>'
        '        <span class="tl-trip-hint">%s</span>'
        '      </span>'
        '      <span class="tl-trip-caret" aria-hidden="true">▾</span>'
        '    </span>'
        '  </button>'
        '  <div class="tl-trip-body">'
        '    %s'
        '  </div>'
        '</article>'
    ) % (open_cls, esc(years), n_visits, esc(q), aria, bg, esc(key), esc(region_full), esc(meta), esc(hint), visit_html)


def main():
    with open(DATA, encoding='utf-8') as f:
        data = json.load(f)
    site = data.get('site', {})
    trips = data.get('trips', [])

    # 计算统计
    # 走过城市：按「城市」去重（棒棰岛/东港均属大连、天河/珠江新城均属广州，只算 大连/广州/南京）
    city_set = set()
    for t in trips:
        for c in t.get('cities', []):
            region = c.get('region', '')
            parts = [p.strip() for p in region.replace('·', '·').split('·') if p.strip()]
            city = parts[-1] if parts else c.get('name', '')
            if city:
                city_set.add(city)
    total_cities = len(city_set)
    total_trips = len(trips)
    countries = set()
    for t in trips:
        for c in t.get('cities', []):
            countries.add(c.get('country', '中国'))
    start_year = site.get('startYear') or (min(t.get('year', 9999) for t in trips) if trips else '')
    start_year_disp = str(start_year) if trips else '—'
    years = sorted(set(t.get('year') for t in trips), reverse=True)
    # 最新一次出行（按 年+日期 倒序）
    def sort_key(t):
        return (t.get('year', 0), t.get('date', ''))
    latest_id = max(trips, key=sort_key).get('id') if trips else ''

    # 封面：取最新一次出行的 cover（存在才用）
    latest_trip = max(trips, key=sort_key) if trips else {}
    cover = resolve_photo(latest_trip.get('cover', ''))
    if cover:
        hw, hh = img_dims(latest_trip.get('cover', ''))
        hero_dim = ' width="%d" height="%d"' % (hw, hh) if (hw and hh) else ' width="1200" height="480"'
        hero_img = ('<img class="tl-hero-img" src="%s" alt="家庭旅行封面" fetchpriority="high"%s decoding="async">' % (esc(cover), hero_dim))
    else:
        hero_img = ('<div class="tl-hero-img tl-photo-empty">'
                    '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">'
                    '<path d="M2 16l5-5 4 4 3-3 6 6"/><rect x="2" y="6" width="20" height="13" rx="2"/>'
                    '<circle cx="8" cy="10" r="1.6"/></svg>'
                    '<span>封面照片随后补充</span></div>')

    title = site.get('title', '足迹')
    subtitle = site.get('subtitle', '')
    intro = site.get('intro', '')

    # 年份筛选 chips
    year_chips = ['<button class="tl-chip active" data-year="all">全部 <b>%d</b></button>' % total_trips]
    for y in years:
        n = len([t for t in trips if t.get('year') == y])
        year_chips.append('<button class="tl-chip" data-year="%s">%s <b>%d</b></button>' % (y, y, n))
    year_chips_html = '\n        '.join(year_chips)

    if trips:
        # 按地区聚合：同一城市的多段出行合并成一张卡，卡内按年份分小段（用户要求：同地区放一起、里面分年份）
        groups = OrderedDict()
        for t in trips:
            key, region_full = region_of(t)
            if key not in groups:
                groups[key] = {'region_full': region_full, 'visits': []}
            groups[key]['visits'].append(t)
        # 地区卡按「最近一次出行」倒序；卡内年份段也倒序
        group_items = sorted(groups.items(),
                             key=lambda kv: max(sort_key(v) for v in kv[1]['visits']),
                             reverse=True)
        for _, g in group_items:
            g['visits'].sort(key=sort_key, reverse=True)
        latest_region = region_of(max(trips, key=sort_key))[0] if trips else ''
        cards = '\n\n'.join(
            build_region_card(key, g['region_full'], g['visits'], latest_id, key == latest_region)
            for key, g in group_items)
    else:
        cards = ('<div class="tl-empty-state">'
                 '<svg width="40" height="40" viewBox="0 0 64 64" fill="none" stroke="currentColor" '
                 'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                 '<path d="M32 10c-8 0-14 6-14 14 0 10 14 30 14 30s14-20 14-30c0-8-6-14-14-14z"/>'
                 '<circle cx="32" cy="24" r="5"/></svg>'
                 '<p class="tl-empty-title">足迹，正在路上</p>'
                 '<p class="tl-empty-sub">还没有出行记录。把旅行照片发给我，告诉我对应哪座城，'
                 '我就帮你一张张填进来——这里会慢慢长出你们一家人的脚印。</p>'
                 '</div>')

    page_css = """
:root{--tl:#c9a84c;--tl-2:#d98a4e;--tl-soft:rgba(201,168,76,.12)}
[data-theme="light"]{--tl:#a68a3c;--tl-2:#c2763a;--tl-soft:rgba(166,138,60,.10)}
.tl-hero{position:relative;overflow:hidden;border-radius:16px;margin:16px 0 8px;
  height:clamp(340px,34vw,440px);
  display:flex;align-items:flex-end;background:linear-gradient(135deg,#231c0e 0%,#2e2512 50%,#3a2a14 100%)}
.tl-hero-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.tl-hero::after{content:'';position:absolute;inset:0;z-index:1;
  background:linear-gradient(to top,rgba(0,0,0,.88) 0%,rgba(0,0,0,.55) 38%,rgba(0,0,0,.1) 72%);pointer-events:none}
.tl-hero-inner{position:relative;z-index:2;padding:24px 28px 26px;max-width:780px;
  background:linear-gradient(to top,rgba(0,0,0,.72) 0%,rgba(0,0,0,.38) 55%,rgba(0,0,0,0) 100%);border-radius:12px}
.tl-kicker{display:inline-block;font-size:.72rem;font-weight:700;letter-spacing:3px;color:#f1deaa;
  border:1px solid rgba(241,222,170,.55);border-radius:999px;padding:4px 16px;margin-bottom:14px;
  text-shadow:0 1px 6px rgba(0,0,0,.55)}
.tl-hero h1{font-size:2.35rem;color:#fff;margin:0 0 10px;line-height:1.2;
  text-shadow:0 2px 20px rgba(0,0,0,.65),0 1px 3px rgba(0,0,0,.55)}
.tl-hero p.tl-sub{color:rgba(255,255,255,.94);font-size:1.05rem;margin:0 0 12px;font-weight:600;
  text-shadow:0 1px 10px rgba(0,0,0,.6)}
.tl-hero p.tl-intro{color:rgba(255,255,255,.85);font-size:.93rem;line-height:1.85;margin:0;max-width:640px;
  text-shadow:0 1px 8px rgba(0,0,0,.55)}
.tl-gallery-block{margin-top:20px;padding-top:16px;border-top:1px dashed var(--border)}
.tl-gallery-title{font-size:.78rem;font-weight:700;letter-spacing:2px;color:var(--text-secondary);margin:0 0 12px;
  display:flex;align-items:center;gap:8px}
.tl-gallery-title::before{content:'';display:inline-block;width:14px;height:2px;background:var(--tl);border-radius:1px}
.tl-gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.tl-gallery a{display:block;line-height:0}
.tl-gallery img{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:10px;border:1px solid var(--border);
  display:block;background:#222;transition:transform .35s ease,border-color .35s ease,box-shadow .35s ease}
.tl-gallery img:hover{transform:scale(1.04);border-color:var(--tl);box-shadow:0 8px 22px rgba(0,0,0,.5)}
.tl-gallery-captioned{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.tl-photo{margin:0;background:var(--bg);border:1px solid var(--border);border-radius:12px;overflow:hidden;
  display:flex;flex-direction:column;transition:box-shadow .25s,transform .25s,border-color .25s}
.tl-photo:hover{box-shadow:var(--shadow-md);transform:translateY(-2px);border-color:var(--tl)}
.tl-photo a{display:block;line-height:0}
.tl-gallery-captioned .tl-photo img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;background:#222;
  border:none;border-radius:0}
.tl-gallery-captioned .tl-photo img:hover{transform:none}
.tl-photo-cap{font-size:.82rem;color:var(--text-secondary);line-height:1.6;padding:10px 12px 12px}
.tl-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0 10px}
.tl-stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 12px;text-align:center}
.tl-stat-num{display:block;font-size:1.65rem;font-weight:800;color:var(--tl);line-height:1.2}
.tl-stat-label{display:block;font-size:.76rem;color:var(--text-secondary);margin-top:4px}
.tl-sec{margin:42px 0 0}
.tl-sec-title{display:flex;align-items:center;gap:10px;font-size:1.28rem;font-weight:800;margin:0 0 6px;padding-left:12px;border-left:4px solid var(--tl)}
.tl-sec-sub{font-size:.86rem;color:var(--text-muted);margin:0 0 18px 16px}
.tl-filter{margin:0 0 20px;padding:12px 14px;background:color-mix(in srgb,var(--bg) 86%,transparent);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:12px}
.tl-search-wrap{position:relative;margin-bottom:10px}
.tl-search{width:100%;padding:9px 34px 9px 34px;font-size:.9rem;color:var(--text);background:var(--card);
  border:1px solid var(--border);border-radius:9px;font-family:inherit}
.tl-search:focus{outline:none;border-color:var(--tl);box-shadow:0 0 0 3px var(--tl-soft)}
.tl-search-ico{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--text-muted);font-size:.9rem;pointer-events:none}
.tl-search-clear{position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;
  color:var(--text-muted);cursor:pointer;font-size:1rem;padding:2px 6px;display:none}
.tl-chips{display:flex;flex-wrap:wrap;gap:7px}
.tl-chip{font-size:.8rem;padding:5px 13px;border-radius:999px;border:1px solid var(--border);background:var(--card);
  color:var(--text-secondary);cursor:pointer;font-family:inherit;transition:all .18s}
.tl-chip b{font-weight:700;opacity:.6;margin-left:2px;font-size:.74rem}
.tl-chip:hover{border-color:var(--tl);color:var(--tl)}
.tl-chip.active{background:var(--tl);border-color:var(--tl);color:#1a1408}
.tl-chip.active b{opacity:.85}
.tl-count-bar{display:flex;justify-content:space-between;align-items:center;font-size:.8rem;color:var(--text-muted);margin-bottom:14px}
.tl-reset{background:none;border:none;color:var(--tl);cursor:pointer;font-size:.8rem;font-family:inherit;text-decoration:underline}
.tl-list{display:flex;flex-direction:column;gap:20px}
.tl-trip{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;
  transition:box-shadow .25s ease,border-color .25s ease}
.tl-trip.open{border-color:var(--tl);box-shadow:0 10px 30px rgba(0,0,0,.35)}
.tl-trip-head{position:relative;display:flex;width:100%;text-align:left;cursor:pointer;border:none;
  -webkit-appearance:none;appearance:none;background:linear-gradient(135deg,#231c0e 0%,#2e2512 50%,#3a2a14 100%);
  color:#fff;padding:0;font-family:inherit;-webkit-tap-highlight-color:transparent;outline:none}
.tl-trip-head:focus-visible{box-shadow:0 0 0 3px var(--tl-soft)}
.tl-trip-bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.5;z-index:0}
.tl-trip-head::before{content:'';position:absolute;inset:0;z-index:1;
  background:linear-gradient(to top,rgba(0,0,0,.85) 0%,rgba(0,0,0,.5) 55%,rgba(0,0,0,.22) 100%)}
.tl-trip-head-inner{position:relative;z-index:2;flex:1;display:flex;justify-content:space-between;align-items:center;
  gap:16px;padding:20px 22px;min-height:120px}
.tl-trip-titles{display:flex;flex-direction:column;gap:3px}
.tl-trip-head .tl-trip-title{font-size:1.24rem;font-weight:800;color:#fff;line-height:1.3;margin:0;
  display:flex;align-items:center;gap:10px;flex-wrap:wrap;text-shadow:0 2px 14px rgba(0,0,0,.6)}
.tl-trip-head .tl-trip-meta{font-size:.82rem;color:rgba(255,255,255,.86);margin-top:2px;text-shadow:0 1px 8px rgba(0,0,0,.6)}
.tl-trip-hint{font-size:.76rem;color:rgba(255,255,255,.7);margin-top:3px;letter-spacing:.3px}
.tl-trip-caret{flex:0 0 auto;font-size:1.1rem;color:rgba(255,255,255,.9);transition:transform .25s ease;line-height:1}
.tl-trip.open .tl-trip-caret{transform:rotate(180deg)}
.tl-trip-body{display:none;padding:18px 22px 22px}
.tl-trip.open .tl-trip-body{display:block;animation:tlSlide .3s ease}
@keyframes tlSlide{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}
.tl-visit{padding-top:14px;margin-top:14px;border-top:1px dashed var(--border)}
.tl-visit:first-of-type{padding-top:2px;margin-top:0;border-top:none}
.tl-visit-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;width:100%;text-align:left;
  cursor:pointer;margin:0 0 10px;padding:10px 14px;border:1px solid var(--border);border-radius:10px;
  background:var(--bg);color:var(--text);font-family:inherit;-webkit-appearance:none;appearance:none;
  -webkit-tap-highlight-color:transparent;transition:border-color .18s,background .18s}
.tl-visit-head:hover{border-color:var(--tl)}
.tl-visit.open .tl-visit-head{border-color:var(--tl);background:var(--tl-soft)}
.tl-visit-date{font-size:1.06rem;font-weight:800;color:var(--text);line-height:1.3;display:flex;align-items:center;gap:8px}
.tl-visit-meta{font-size:.8rem;color:var(--text-muted)}
.tl-visit-caret{margin-left:auto;font-size:1rem;color:var(--text-muted);transition:transform .2s ease;line-height:1}
.tl-visit.open .tl-visit-caret{transform:rotate(180deg);color:var(--tl)}
.tl-visit-body{display:none;padding:2px 2px 4px}
.tl-visit.open .tl-visit-body{display:block;animation:tlFade .2s ease}
.tl-trip-region{font-size:.8rem;font-weight:500;color:rgba(255,255,255,.6);margin-left:4px}
.tl-season{flex:0 0 auto;width:40px;height:40px;border-radius:11px;display:flex;align-items:center;justify-content:center;
  color:#fff;font-size:1.05rem;font-weight:800}
.tl-trip-titles{display:flex;flex-direction:column}
.tl-trip-title{font-size:1.22rem;font-weight:800;color:var(--text);line-height:1.3;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.tl-latest{flex:0 0 auto;font-size:.7rem;font-weight:700;color:#fff;background:linear-gradient(135deg,var(--tl),var(--tl-2));
  padding:2px 10px;border-radius:999px;letter-spacing:.5px}
.tl-trip-meta{font-size:.82rem;color:var(--text-secondary);margin-top:2px}
.tl-trip-note{font-size:.92rem;color:var(--text-secondary);line-height:1.8;margin:0 0 14px;padding:10px 14px;
  background:var(--tl-soft);border-left:3px solid var(--tl);border-radius:0 9px 9px 0;font-style:italic}
.tl-cities{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.tl-city{background:var(--bg);border:1px solid var(--border);border-radius:12px;overflow:hidden;
  transition:box-shadow .2s,transform .2s}
.tl-city:hover{box-shadow:var(--shadow-md);transform:translateY(-2px)}
.tl-city-img-wrap{position:relative;aspect-ratio:320/200;background:var(--card);overflow:hidden}
.tl-city-img{display:block;width:100%;height:100%;object-fit:cover}
.tl-photo-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;
  color:var(--text-muted);background:
    repeating-linear-gradient(45deg,rgba(201,168,76,.05) 0 12px,transparent 12px 24px),var(--card);
  font-size:.78rem}
.tl-photo-empty svg{opacity:.5}
.tl-city-body{padding:12px 14px 14px}
.tl-city-name{font-size:1.05rem;font-weight:800;color:var(--text);display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.tl-city-meta{font-size:.76rem;font-weight:400;color:var(--text-muted)}
.tl-city-memory{font-size:.88rem;color:var(--text-secondary);line-height:1.7;margin:6px 0 2px}
.tl-city-kids{font-size:.78rem;color:var(--tl);margin:4px 0 6px;font-weight:600}
.tl-rating{display:inline-flex;gap:1px;color:var(--tl);vertical-align:middle;margin-bottom:4px}
.tl-rating .tl-star{color:var(--text-muted)}
.tl-rating .tl-star.on{color:var(--tl)}
.tl-city-toggle{display:inline-flex;align-items:center;gap:4px;margin-top:4px;padding:4px 12px;font-size:.76rem;
  font-family:inherit;color:var(--tl);background:var(--tl-soft);border:1px solid transparent;border-radius:999px;cursor:pointer;transition:border-color .15s}
.tl-city-toggle:hover{border-color:var(--tl)}
.tl-caret{display:inline-block;transition:transform .2s;font-size:.7rem;line-height:1}
.tl-city.open .tl-caret{transform:rotate(180deg)}
.tl-city-detail{display:none;margin-top:8px;animation:tlFade .2s ease}
.tl-city.open .tl-city-detail{display:block}
.tl-highlights{margin:0;padding-left:18px}
.tl-highlights li{font-size:.84rem;color:var(--text-secondary);line-height:1.8}
.tl-empty{display:none;text-align:center;padding:46px 20px;color:var(--text-muted);font-size:.9rem}
@keyframes tlFade{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.tl-reveal{opacity:0;transform:translateY(14px);transition:opacity .55s ease,transform .55s ease}
.tl-reveal.in{opacity:1;transform:none}
.tl-note{margin:36px 0 8px;padding:16px 18px;background:var(--bg);border:1px solid var(--border);border-radius:12px;
  font-size:.82rem;color:var(--text-secondary);line-height:1.85}
.tl-note h3{font-size:.9rem;margin:0 0 8px;color:var(--text)}
.tl-note code{background:var(--card);padding:1px 6px;border-radius:5px;font-size:.78rem;color:var(--tl)}
.tl-empty-state{text-align:center;padding:54px 20px;color:var(--text-muted)}
.tl-empty-state svg{color:var(--tl);opacity:.7;margin-bottom:14px}
.tl-empty-title{font-size:1.15rem;font-weight:800;color:var(--text);margin:0 0 8px}
.tl-empty-sub{font-size:.9rem;line-height:1.85;max-width:440px;margin:0 auto;color:var(--text-secondary)}
.tl-more-wrap{display:none;text-align:center;margin:22px 0 4px}
.tl-more-btn{display:inline-flex;align-items:center;gap:6px;padding:10px 28px;font-size:.92rem;font-family:inherit;
  color:var(--tl);background:var(--tl-soft);border:1px solid var(--tl);border-radius:999px;cursor:pointer;transition:all .18s}
.tl-more-btn:hover{background:var(--tl);color:#1a1408}
.tl-cities-more{display:inline-flex;align-items:center;gap:4px;margin:12px 0 2px;padding:4px 14px;font-size:.78rem;
  font-family:inherit;color:var(--tl);background:var(--tl-soft);border:1px solid transparent;border-radius:999px;cursor:pointer}
.tl-cities-more:hover{border-color:var(--tl)}
.tl-cities.tl-collapsible{position:relative}
@media(max-width:992px){.tl-stats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:576px){.tl-hero{min-height:200px}.tl-hero-inner{padding:22px 16px 20px}.tl-hero h1{font-size:1.5rem}
  .tl-trip{padding:16px 15px}.tl-cities{grid-template-columns:1fr}.tl-stat-num{font-size:1.35rem}}
"""

    page_js = """
(function(){
  var list=document.getElementById('tlList');
  if(!list)return;
  var trips=[].slice.call(list.querySelectorAll('.tl-trip'));
  var chips=[].slice.call(document.querySelectorAll('.tl-chip'));
  var input=document.getElementById('tlSearch');
  var clear=document.getElementById('tlClear');
  var shown=document.getElementById('tlShown');
  var empty=document.getElementById('tlEmpty');
  var reset=document.getElementById('tlReset');
  var moreWrap=document.getElementById('tlMoreWrap');
  var moreBtn=document.getElementById('tlMore');
  var PER=6;
  var ALIAS={'旅游':'travel 旅行','家庭':'family 家庭','孩子':'孩子 女儿 儿子','亲子':'亲子 家庭'};
  var state={year:'all',q:'',page:1};
  trips.forEach(function(t){ t._q=(t.getAttribute('data-q')||''); });
  function match(t){
    var y=t.getAttribute('data-year')||'';
    var okY=(state.year==='all')||y.indexOf(state.year)>-1;
    var okQ=!state.q||t._q.indexOf(state.q)>-1;
    return okY&&okQ;
  }
  function render(){
    var total=0,shownCount=0,visitCount=0;
    trips.forEach(function(t){
      if(!match(t)){ t.style.display='none'; return; }
      total++;
      visitCount += parseInt(t.getAttribute('data-n')||'0',10);
      if(shownCount < state.page*PER){
        var wasHidden=t.style.display==='none';
        t.style.display='';
        if(wasHidden) t.classList.add('in');
        shownCount++;
      } else {
        t.style.display='none';
      }
    });
    shown.textContent=visitCount;
    empty.style.display=total?'none':'block';
    clear.style.display=state.q?'block':'none';
    moreWrap.style.display=(total>state.page*PER)?'block':'none';
  }
  chips.forEach(function(ch){
    ch.addEventListener('click',function(){
      chips.forEach(function(x){x.classList.remove('active');});
      ch.classList.add('active');
      state.year=ch.getAttribute('data-year'); state.page=1; render();
    });
  });
  input.addEventListener('input',function(){
    var v=input.value.trim().toLowerCase();
    if(ALIAS[v])v=ALIAS[v];
    state.q=v; state.page=1; render();
  });
  clear.addEventListener('click',function(){ input.value=''; state.q=''; state.page=1; render(); input.focus(); });
  reset.addEventListener('click',function(){
    input.value=''; state.q=''; state.year='all'; state.page=1;
    chips.forEach(function(x){x.classList.toggle('active',x.getAttribute('data-year')==='all');});
    render();
  });
  if(moreBtn){ moreBtn.addEventListener('click',function(){ state.page++; render(); }); }
  // 城市卡片折叠（一趟出行城市很多时，默认仅显示前 4 座）
  var collapsibles=[].slice.call(list.querySelectorAll('.tl-cities.tl-collapsible'));
  collapsibles.forEach(function(grid){
    var limit=parseInt(grid.getAttribute('data-limit')||'4',10);
    var totalN=grid.getAttribute('data-total')||'';
    var kids=[].slice.call(grid.children);
    kids.forEach(function(k,i){ if(i>=limit) k.style.display='none'; });
    var btn=grid.parentNode.querySelector('.tl-cities-more');
    if(btn){
      btn.addEventListener('click',function(){
        var open=grid.classList.toggle('open');
        btn.setAttribute('aria-expanded',open?'true':'false');
        kids.forEach(function(k,i){ k.style.display=(open||i<limit)?'':'none'; });
        btn.firstChild.nodeValue=open?('收起城市 '):('展开全部 '+totalN+' 城 ');
        var caret=btn.querySelector('.tl-caret'); if(caret)caret.textContent=open?'▴':'▾';
      });
    }
  });
  var toggles=[].slice.call(list.querySelectorAll('.tl-city-toggle'));
  toggles.forEach(function(btn){
    btn.addEventListener('click',function(){
      var card=btn.closest('.tl-city');
      var open=card.classList.toggle('open');
      btn.setAttribute('aria-expanded',open?'true':'false');
      var t=btn.querySelector('.tl-toggle-txt'); if(t)t.textContent=open?'收起亮点':'展开亮点';
    });
  });
  // 出行卡片手风琴：点击背景卡头部展开/收起该地区的城市解说与照片
  var heads=[].slice.call(list.querySelectorAll('.tl-trip-head'));
  heads.forEach(function(btn){
    btn.addEventListener('click',function(){
      var card=btn.closest('.tl-trip');
      var open=card.classList.toggle('open');
      btn.setAttribute('aria-expanded',open?'true':'false');
    });
  });
  // 年份小段手风琴：地区卡展开后，每段年份默认折叠，点年份条才展开该年的城市解说与相册
  var vheads=[].slice.call(list.querySelectorAll('.tl-visit-head'));
  vheads.forEach(function(btn){
    btn.addEventListener('click',function(){
      var sec=btn.closest('.tl-visit');
      var open=sec.classList.toggle('open');
      btn.setAttribute('aria-expanded',open?'true':'false');
    });
  });
  // 滚动淡入
  var reveals=[].slice.call(document.querySelectorAll('.tl-reveal'));
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){
      es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
    },{threshold:0.08});
    reveals.forEach(function(r){io.observe(r);});
  } else { reveals.forEach(function(r){r.classList.add('in');}); }
  render();
})();
"""

    with open(DONOR, encoding='utf-8') as f:
        donor = f.read()

    critical = extract(donor, '<style id="critical-css">', '</style>')
    navbar = extract(donor, '<nav class="navbar"', '</nav>')
    footer = extract(donor, '<footer role="contentinfo">', '</footer>')

    # 导航高亮切换到 家庭旅行（herbs 供体上是中药材高亮）
    navbar = re.sub(r' class="active"', '', navbar)  # 先清掉所有 active
    navbar = navbar.replace('<a href="travel.html">家庭旅行</a>',
                            '<a href="travel.html" class="active">家庭旅行</a>')
    if 'travel.html' not in navbar:
        raise SystemExit('供体导航缺少 家庭旅行 链接，请先运行导航注入脚本（sync_navbar.py 已加入该链接）')

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script>(function(){try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t)}else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark')}}catch(e){}})();</script>
<link rel="preload" href="js/app.js" as="script">
<link rel="preconnect" href="//hm.baidu.com">
<link rel="dns-prefetch" href="//hm.baidu.com">
<link rel="dns-prefetch" href="//busuanzi.ibruce.info">
__CRITICAL__
<link rel="preload" href="css/style.css?v=20260822" as="style" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="css/style.css?v=20260822"></noscript>
<title>足迹 · 家庭旅行 - 龙兄知识库</title><meta name="description" content="带着老婆和两个儿子走过的每一座城：一份有温度的家庭旅行档案，按年份记录每一次出行的城市、瞬间与孩子的笑容。">
<meta name="keywords" content="家庭旅行,亲子游,足迹,带着孩子去旅行,龙兄知识库">
<style>__PAGECSS__</style>
<script>
var _hmt = _hmt || [];
(function() {
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?04913e92799dc86649938ea8f5eb4b78";
  var s = document.getElementsByTagName("script")[0];
  s.parentNode.insertBefore(hm, s);
})();
</script>
<script async src="//busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
<meta property="og:site_name" content="龙兄知识库">
<link rel="canonical" href="https://longxiong.vip/travel.html">
<link rel="icon" type="image/svg+xml" href="https://longxiong.vip/favicon.svg">
<meta property="og:title" content="足迹 · 家庭旅行 - 龙兄知识库">
<meta property="og:description" content="带着老婆和两个儿子走过的每一座城：一份有温度的家庭旅行档案。">
<meta property="og:type" content="article">
<meta property="og:url" content="https://longxiong.vip/travel.html">
<meta property="og:image" content="https://longxiong.vip/img/og-image.png">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="足迹 · 家庭旅行 - 龙兄知识库">
<meta name="twitter:description" content="带着老婆和两个儿子走过的每一座城：一份有温度的家庭旅行档案。">
<meta name="twitter:image" content="https://longxiong.vip/img/og-image.png">
</head>
<body>

__NAVBAR__

<div id="tlWrap" data-tl-wrap>
  <main id="main-content" role="main"><div class="container">
  <div class="breadcrumb" id="breadcrumb">
    <a href="index.html">首页</a>
    <span class="sep">›</span>
    <span class="current">家庭旅行 · 足迹</span>
  </div>

  <!-- ===== Hero ===== -->
  <div class="tl-hero">
    __HEROIMG__
    <div class="tl-hero-inner">
      <span class="tl-kicker">FAMILY TRAVEL · 家庭旅行</span>
      <h1>__TITLE__</h1>
      <p class="tl-sub">__SUBTITLE__</p>
      <p class="tl-intro">__INTRO__</p>
    </div>
  </div>

  <div class="tl-stats">
    <div class="tl-stat"><span class="tl-stat-num">__N_CITIES__</span><span class="tl-stat-label">走过城市</span></div>
    <div class="tl-stat"><span class="tl-stat-num">__N_TRIPS__</span><span class="tl-stat-label">出行次数</span></div>
    <div class="tl-stat"><span class="tl-stat-num">__N_COUNTRIES__</span><span class="tl-stat-label">到过国家/地区</span></div>
    <div class="tl-stat"><span class="tl-stat-num">__START_YEAR__</span><span class="tl-stat-label">始于</span></div>
  </div>

  <!-- ===== 出行档案 ===== -->
  <section class="tl-sec">
    <h2 class="tl-sec-title">我们的出行档案</h2>
    <p class="tl-sec-sub">点开任意地区卡片，即可看到该地区每一次出行的城市解说与沿途照片；可按年份筛选或搜索关键词（城市、地区、记忆、年份都能搜），点「显示更多地区」看更早的足迹。</p>

    <div class="tl-filter">
      <div class="tl-search-wrap">
        <span class="tl-search-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
        <input type="search" class="tl-search" id="tlSearch" placeholder="搜城市、地区或记忆" aria-label="搜索家庭旅行">
        <button class="tl-search-clear" id="tlClear" aria-label="清空搜索"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg></button>
      </div>
      <div class="tl-chips">
        __YEARCHIPS__
      </div>
    </div>

    <div class="tl-count-bar">
      <span>共 <strong id="tlShown">__N_TRIPS__</strong> 次出行</span>
      <button class="tl-reset" id="tlReset">重置筛选</button>
    </div>

    <div class="tl-list" id="tlList">
__CARDS__
    </div>
    <div class="tl-more-wrap" id="tlMoreWrap">
      <button class="tl-more-btn" id="tlMore" type="button">显示更多地区 <span class="tl-caret">▾</span></button>
    </div>
    <div class="tl-empty" id="tlEmpty">没有匹配的出行，换个关键词试试～</div>
  </section>

  <div class="tl-note">
    <h3>关于本页</h3>
    <p>这里记的是我们一家人的真实足迹，不是攻略——每一座城背后，都是一段想被记住的时光。所有照片均为真实拍摄，绝不使用 AI 生成图。</p>
    <p style="font-size:.8rem;line-height:1.75;color:var(--text-muted);margin-top:10px;">
      内容来源：本页全部为自有一手记录——行程、日期与城市信息来自我们家庭的真实出行安排，
      照片由本人实地拍摄并加注水印，未采用任何网络图片或 AI 生成图；
      文中不含景点门票、交通时刻等易变信息，如需出行规划请以官方渠道最新公告为准。
    </p>
  </div>

</div>
</main>__FOOTER__

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "name": "龙兄知识库",
      "url": "https://longxiong.vip",
      "description": "AI · 文玩 · 游戏 · 养生 · 新能源 — 做一个有温度的知识站点"
    },
    {
      "@type": "Article",
      "author": { "@type": "Person", "name": "龙兄" },
      "headline": "足迹 · 家庭旅行 - 龙兄知识库",
      "url": "https://longxiong.vip/travel.html",
      "description": "带着老婆和两个儿子走过的每一座城：一份有温度的家庭旅行档案。"
    }
  ]
}
</script>

<script>__PAGEJS__</script>
</div>

<script src="js/search.js"></script>
<script defer src="js/app.js"></script>
<script src="js/share.js"></script>
</body>
</html>
"""

    html = (html
            .replace('__CRITICAL__', critical)
            .replace('__NAVBAR__', navbar)
            .replace('__FOOTER__', footer)
            .replace('__PAGECSS__', page_css.strip())
            .replace('__PAGEJS__', page_js.strip())
            .replace('__HEROIMG__', hero_img)
            .replace('__TITLE__', esc(title))
            .replace('__SUBTITLE__', esc(subtitle))
            .replace('__INTRO__', esc(intro))
            .replace('__YEARCHIPS__', year_chips_html)
            .replace('__CARDS__', cards)
            .replace('__N_CITIES__', str(total_cities))
            .replace('__N_TRIPS__', str(total_trips))
            .replace('__N_COUNTRIES__', str(len(countries)))
            .replace('__START_YEAR__', start_year_disp))

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)

    print('生成完成: %s' % OUT)
    print('  出行 %d 次 / 城市 %d 座 / 国家地区 %d / 始于 %s' % (total_trips, total_cities, len(countries), start_year))
    print('  文件大小 %.1f KB' % (len(html.encode('utf-8')) / 1024))


if __name__ == '__main__':
    main()
