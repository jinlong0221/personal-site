#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 static/ev-sales.html —— 新能源车销量排行榜

数据来源（全部自动抓取 + 人工交叉核验，绝不手写编造）：
  1. 乘用车市场信息联席会（乘联会/CPCA）官方数据接口
     http://data.cpcadata.com/api/chartlist
     -> 乘用车厂商榜（批发/零售）、新能源渗透率、BEV/PHEV 结构、分国别份额、出口
  2. 新能源厂商榜：转载乘联会【终稿】的媒体报道（人工核对快照）
     见 fetch_ev_sales.py 顶部 NEV_MAKER_SNAPSHOT 的详细说明与校验记录

先跑数据抓取，再跑本脚本：
    python3 scripts/fetch_ev_sales.py
    python3 scripts/build_ev_sales.py
    python3 scripts/sync_v_param.py --write

设计约定：
  - 图表全部为内联 SVG 手绘，不引入 Chart.js 等外部库（避免 CSP 与额外请求）
  - 数据直接静态渲染进 HTML，JS 只负责 Tab 切换，利于 SEO 与首屏速度
  - 所有数字旁必须标注口径（批发/零售、含燃油车与否），杜绝误导
"""
import json
import os
import html as H
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'static', 'ev-sales.json')
OUT = os.path.join(ROOT, 'static', 'ev-sales.html')
DONOR = os.path.join(ROOT, 'static', 'ev-charge.html')

# 车型级销量（懂车帝接口全自动抓取，与上面的厂商级数据互相独立）。
# 这个文件拿不到时页面照常生成，只是不出车型榜 —— 绝不因此让整页失败。
MODEL_DATA = os.path.join(ROOT, 'static', 'ev-model-sales.json')

# 缓存破坏版本号：运行时按资源各自的 git 最后改动日计算，绝不写死。
# （写死的日期必然过期 → 同一资源两种 ?v → guard_v_param 判 ERROR → CI 红。）
# 详见 scripts/v_param.py 的说明。
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from v_param import css_version as _css_version, version_for as _version_for
except Exception:
    _css_version = None
    _version_for = None
V_CSS = _css_version() if _css_version else datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d')
V_JS = (_version_for('static/js/ev-sales.js')
        if _version_for else V_CSS)


def esc(s):
    return H.escape(str(s if s is not None else ''), quote=True)


def fmt(v, nd=2):
    """数字格式化：None 一律显示占位符，绝不编造。"""
    if v is None:
        return '—'
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '—'
    if abs(f) >= 10000:
        return '{:,.0f}'.format(f)
    s = ('{:,.%df}' % nd).format(f)
    return s.rstrip('0').rstrip('.') if '.' in s else s


def pct(v):
    return '—' if v is None else '%.1f%%' % float(v)


def yoy_cls(v):
    if v is None:
        return 'flat'
    return 'up' if float(v) > 0 else ('down' if float(v) < 0 else 'flat')


def yoy_txt(v):
    if v is None:
        return '—'
    f = float(v)
    return '%+.2f%%' % f


# ---------------------------------------------------------------- SVG 图表
def spark_line(values, labels, width=660, height=200, color='#C9A84C'):
    """渗透率折线图（带面积填充）。values 为百分比。"""
    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(pts) < 2:
        return '<p class="ev-note">数据不足，暂无法绘制走势。</p>'
    pad_l, pad_r, pad_t, pad_b = 44, 14, 16, 30
    lo = min(v for _, v in pts)
    hi = max(v for _, v in pts)
    if hi - lo < 6:
        lo = max(0, lo - 3)
        hi = hi + 3
    span = (hi - lo) or 1

    def X(i):
        return pad_l + (width - pad_l - pad_r) * (i / (len(values) - 1))

    def Y(v):
        return pad_t + (height - pad_t - pad_b) * (1 - (v - lo) / span)

    line = ' '.join('%.1f,%.1f' % (X(i), Y(v)) for i, v in pts)
    area = '%s %.1f,%.1f %.1f,%.1f' % (
        line, X(pts[-1][0]), height - pad_b, X(pts[0][0]), height - pad_b)

    grid = []
    for g in range(5):
        gv = lo + span * g / 4
        gy = Y(gv)
        grid.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" '
                    'stroke-opacity=".13" stroke-width="1"/>' % (pad_l, gy, width - pad_r, gy))
        grid.append('<text x="%d" y="%.1f" fill="currentColor" fill-opacity=".55" '
                    'font-size="10" text-anchor="end">%.0f%%</text>'
                    % (pad_l - 6, gy + 3.5, gv))

    dots = []
    xl = []
    for i, v in pts:
        dots.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="%s"/>' % (X(i), Y(v), color))
        if i == len(values) - 1:
            dots.append('<circle cx="%.1f" cy="%.1f" r="5.5" fill="%s" fill-opacity=".22"/>'
                        % (X(i), Y(v), color))
            dots.append('<text x="%.1f" y="%.1f" fill="%s" font-size="12" font-weight="700" '
                        'text-anchor="end">%.1f%%</text>' % (X(i) - 4, Y(v) - 10, color, v))
        if i % 2 == 0 or i == len(values) - 1:
            lb = labels[i] if i < len(labels) else ''
            xl.append('<text x="%.1f" y="%d" fill="currentColor" fill-opacity=".55" '
                      'font-size="10" text-anchor="middle">%s</text>'
                      % (X(i), height - 10, esc(lb.replace('2026-', '').replace('2025-', '25/'))))

    return (
        '<svg class="ev-chart" viewBox="0 0 %d %d" role="img" '
        'aria-label="新能源渗透率月度走势" preserveAspectRatio="xMidYMid meet">'
        '%s<polygon points="%s" fill="%s" fill-opacity=".13"/>'
        '<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4" '
        'stroke-linejoin="round" stroke-linecap="round"/>%s%s</svg>'
        % (width, height, ''.join(grid), area, color, line, color,
           ''.join(dots), ''.join(xl))
    )


def hbar(rows, width=660, row_h=30, max_label_w=96):
    """横向条形图。rows = [(名称, 数值, 显示文本)]"""
    if not rows:
        return '<p class="ev-note">暂无数据。</p>'
    hi = max((r[1] or 0) for r in rows) or 1
    bar_x = max_label_w + 8
    bar_w = width - bar_x - 62
    out = ['<svg class="ev-chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="xMidYMid meet">'
           % (width, len(rows) * row_h + 8)]
    for i, (name, val, txt) in enumerate(rows):
        y = i * row_h + 6
        w = max(0, bar_w * ((val or 0) / hi))
        out.append('<text x="%d" y="%d" fill="currentColor" fill-opacity=".85" font-size="12" '
                   'text-anchor="end">%s</text>' % (max_label_w, y + 14, esc(name)))
        out.append('<rect x="%d" y="%d" width="%d" height="15" rx="4" fill="currentColor" '
                   'fill-opacity=".08"/>' % (bar_x, y + 3, bar_w))
        out.append('<rect x="%d" y="%d" width="%.1f" height="15" rx="4" fill="%s" '
                   'fill-opacity=".82"/>' % (bar_x, y + 3, w, '#C9A84C'))
        out.append('<text x="%.1f" y="%d" fill="currentColor" fill-opacity=".9" font-size="12" '
                   'font-weight="600">%s</text>' % (bar_x + w + 8, y + 15, esc(txt)))
    out.append('</svg>')
    return ''.join(out)


# ---------------------------------------------------------------- 板块片段
def rank_table(rows, unit_label='辆', with_cum=False):
    """厂商排行榜表格。"""
    if not rows:
        return '<p class="ev-note">暂无数据。</p>'
    head = ['排名', '厂商', '当月销量']
    if with_cum:
        head.append('本年累计')
    head.append('同比')
    th = ''.join('<th scope="col">%s</th>' % esc(h) for h in head)
    trs = []
    for r in rows:
        tds = ['<td class="rk">%d</td>' % r['rank'],
               '<td class="nm">%s</td>' % esc(r['name']),
               '<td class="vl">%s</td>' % ('{:,}'.format(r['units']) if r.get('units') else '—')]
        if with_cum:
            tds.append('<td class="vl sub">%s</td>'
                       % ('{:,}'.format(r['cumulative']) if r.get('cumulative') else '—'))
        tds.append('<td class="%s">%s</td>' % (yoy_cls(r.get('yoy')), yoy_txt(r.get('yoy'))))
        trs.append('<tr>%s</tr>' % ''.join(tds))
    return ('<div class="ev-table-wrap"><table class="ev-rank"><thead><tr>%s</tr></thead>'
            '<tbody>%s</tbody></table></div>'
            '<p class="ev-unit">单位：%s</p>' % (th, ''.join(trs), esc(unit_label)))


def api_rank_table(rows, period_label):
    """接口口径的乘用车厂商榜（单位万辆）。"""
    if not rows:
        return '<p class="ev-note">暂无数据。</p>'
    th = ('<tr><th scope="col">排名</th><th scope="col">厂商</th>'
          '<th scope="col">销量（万辆）</th><th scope="col">去年同期</th>'
          '<th scope="col">同比</th></tr>')
    trs = []
    for r in rows:
        trs.append(
            '<tr><td class="rk">%d</td><td class="nm">%s</td>'
            '<td class="vl">%s</td><td class="vl sub">%s</td>'
            '<td class="%s">%s</td></tr>'
            % (r['rank'], esc(r['name']), fmt(r.get('value')), fmt(r.get('prev')),
               yoy_cls(r.get('yoy')), yoy_txt(r.get('yoy'))))
    return ('<div class="ev-table-wrap"><table class="ev-rank"><thead>%s</thead>'
            '<tbody>%s</tbody></table></div>' % (th, ''.join(trs)))


# ------------------------------------------------------- 车型级销量（懂车帝）
def load_model_data():
    """
    读车型级数据。这个文件是独立抓取的，拿不到/解析失败时返回 None，
    页面照常生成，只是不出车型榜 —— 绝不因为一个板块失败拖垮整页。
    """
    try:
        with open(MODEL_DATA, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:                              # noqa: BLE001
        _sys.stderr.write('[build_ev_sales] 未加载车型级数据（%s），跳过车型榜板块\n' % e)
        return None


def _rank_delta(cur, prev):
    """名次变化。cur 小 = 上升（好），显示绿色箭头。"""
    if prev is None or cur is None:
        return '<td class="vl sub">—</td>'
    try:
        c, p = int(cur), int(prev)
    except (TypeError, ValueError):
        return '<td class="vl sub">—</td>'
    if p <= 0:
        return '<td class="vl sub">新</td>'
    d = p - c                      # 正数 = 名次前进
    if d > 0:
        return '<td class="vl up">↑%d</td>' % d
    if d < 0:
        return '<td class="vl down">↓%d</td>' % (-d)
    return '<td class="vl sub">—</td>'


def model_rank_table(rows):
    """
    车型销量榜表格。

    两个刻意的设计：
    1. 同系合计：懂车帝按动力版本分列（如 宋Ultra EV / 宋Ultra DM），
       单看一条会让人低估该车系。同系的在车型名下补一行"合计 X"，
       分列数字保持原样不合并 —— 既不撒谎也不误导。
    2. 名次变化：用接口自带的 last_rank 算，不自己推算。
    """
    if not rows:
        return '<p class="ev-note">暂无数据。</p>'
    th = ('<tr><th scope="col">排名</th><th scope="col">车型</th>'
          '<th scope="col">品牌</th><th scope="col">销量</th>'
          '<th scope="col">名次变化</th><th scope="col">指导价</th></tr>')
    trs = []
    shown_groups = set()
    for r in rows:
        name = r.get('name') or ''
        grp = r.get('seriesGroup')
        grp_html = ''
        # 同系合计：每个车系只在首次出现的那行显示一次，避免重复刷屏
        if grp and grp not in shown_groups:
            shown_groups.add(grp)
            parts = r.get('seriesGroupParts') or []
            if len(parts) > 1 and r.get('seriesGroupTotal'):
                detail = ' ＋ '.join(
                    '%s %s' % (esc(p.get('name')), '{:,}'.format(p.get('units') or 0))
                    for p in parts)
                grp_html = ('<span class="ev-grp">%s 系合计 <b>%s</b> 辆'
                            '<span class="ev-grp-parts">（%s）</span></span>'
                            % (esc(grp), '{:,}'.format(r['seriesGroupTotal']), detail))
        # 车型名：有 seriesId 就链到该平台车型页，方便用户自己核原始页面。
        # 没有就不链 —— 绝不拼一个打不开的 URL 充数。
        sid = r.get('seriesId')
        if sid:
            name_html = ('<a href="https://www.dongchedi.com/auto/series/%s" '
                         'target="_blank" rel="noopener noreferrer" '
                         'title="在懂车帝查看该车型页">%s</a>' % (esc(str(sid)), esc(name)))
        else:
            name_html = esc(name)
        name_cell = '<td class="nm">%s%s</td>' % (name_html, grp_html)
        trs.append(
            '<tr><td class="rk">%d</td>%s<td class="bd">%s</td>'
            '<td class="vl">%s</td>%s<td class="vl sub">%s</td></tr>'
            % (r.get('rank') or 0, name_cell, esc(r.get('brand') or ''),
               '{:,}'.format(r['units']) if r.get('units') is not None else '—',
               _rank_delta(r.get('rank'), r.get('lastRank')),
               esc(r.get('priceRange') or '—')))
    return ('<div class="ev-table-wrap"><table class="ev-rank ev-model"><thead>%s</thead>'
            '<tbody>%s</tbody></table></div>' % (th, ''.join(trs)))


def model_source_badge(tier):
    """
    来源等级标识。这是本板块最要紧的一处诚实性设计：
    批发榜的数字能溯源到乘联会终稿，零售榜不能 —— 两者在页面上
    必须一眼可辨，不能让用户以为它们同样官方。
    """
    if tier == 'traceable':
        return ('<span class="ev-tier ev-tier-traceable" title="车型数字经与乘联会官方'
                '《全国乘用车市场分析》抽样比对，厂商级加总逐位一致">'
                '可溯源 · 与乘联会官方数字交叉验证</span>')
    return ('<span class="ev-tier ev-tier-platform" title="该平台未公开上游数据来源，'
            '本站按其自身口径如实引用，不与乘联会官方数据混用">'
            '平台口径 · 上游来源未公开</span>')


def build_body(d):
    period = d.get('period') or {}
    nev = d.get('nev') or {}
    maker = d.get('maker') or {}
    seg = d.get('segment') or []
    overall = d.get('overall') or []
    nm = d.get('nevMaker') or {}

    y = period.get('year') or 2026
    lm = period.get('latestMonth')
    cum_lb = period.get('cumulativeLabel') or ''
    mon_lb = period.get('monthlyLabel') or ''

    # ---- 核心指标（最新月份）
    ni = (nev.get('nevIce') or [])
    last_ni = ni[-1] if ni else {}
    nev_d = last_ni.get('NEV') or {}
    ice_d = last_ni.get('ICE') or {}
    bp = (nev.get('bevPhev') or [])
    last_bp = bp[-1] if bp else {}
    bev_d = last_bp.get('BEV') or {}
    phe_d = last_bp.get('PHEV') or {}
    last_seg = seg[-1] if seg else {}
    own = last_seg.get('自主') or {}
    last_ov = overall[-1] if overall else {}

    kpis = [
        ('新能源零售渗透率', pct(nev_d.get('rtShare')),
         '%s 国内零售，创阶段新高' % (last_ni.get('label', '').replace('2026-', '') or '本期')),
        ('新能源零售', '%s 万' % fmt(nev_d.get('retail')),
         '辆，%s 国内零售（上险量）' % (mon_lb or '本期')),
        ('新能源批发', '%s 万' % fmt(nev_d.get('wholesale')), '辆，含出口'),
        ('乘用车出口', '%s 万' % fmt(last_ov.get('出口')), '辆，%s' % (mon_lb or '本期')),
        ('自主品牌份额', pct(own.get('rtShare')), '国内零售口径'),
    ]
    kpi_html = ''.join(
        '<div class="ev-stat"><b>%s</b><span class="ev-stat-lb">%s</span>'
        '<span class="ev-stat-sub">%s</span></div>' % (esc(v), esc(k), esc(s))
        for k, v, s in kpis)

    # ---- 渗透率走势
    share_vals = [(x.get('NEV') or {}).get('rtShare') for x in ni]
    share_lbs = [x.get('label', '') for x in ni]
    chart_pen = spark_line(share_vals, share_lbs)

    # ---- BEV / PHEV 结构
    bev_rows = []
    if bev_d or phe_d:
        bev_rows = [
            ('BEV 纯电', bev_d.get('retail'), '%s 万' % fmt(bev_d.get('retail'))),
            ('PHEV 插混', phe_d.get('retail'), '%s 万' % fmt(phe_d.get('retail'))),
        ]
        gap = None
        if bev_d.get('retail') is not None and phe_d.get('retail') is not None \
                and nev_d.get('retail') is not None:
            gap = nev_d['retail'] - bev_d['retail'] - phe_d['retail']
        if gap is not None and gap > 0.05:
            bev_rows.append(('增程 EREV（推算）', gap, '%s 万' % fmt(gap)))
    chart_struct = hbar(bev_rows, width=660, row_h=34, max_label_w=104)

    # ---- 阵营份额
    camp_names = ['自主', '德系', '日系', '美系', '韩系', '法系']
    camp_rows = []
    for n in camp_names:
        v = last_seg.get(n) or {}
        if v.get('retail') is None:
            continue
        camp_rows.append((n, v.get('retail'), '%s 万（%s）' % (fmt(v.get('retail')), pct(v.get('rtShare')))))
    chart_camp = hbar(camp_rows, width=660, row_h=32, max_label_w=72)

    # ---- 新能源厂商榜（人工核对快照）
    ws = (nm.get('wholesale') or {})
    rt = (nm.get('retail') or {})
    ws_html = rank_table(ws.get('rows') or [], unit_label='辆', with_cum=True)
    rt_html = rank_table(rt.get('rows') or [], unit_label='辆', with_cum=False)

    notes_html = ''.join('<li>%s</li>' % esc(x) for x in (nm.get('notes') or []))

    # ---- 接口口径的乘用车总榜
    cum = maker.get('cumulative') or {}
    mon = maker.get('monthly') or {}
    api_ws = api_rank_table(mon.get('wholesale') or [], mon.get('label') or '')
    api_rt = api_rank_table(mon.get('retail') or [], mon.get('label') or '')

    cross = d.get('crossCheck') or []
    cross_html = ''
    if cross:
        cross_html = ('<details class="ev-fold"><summary>数据交叉校验记录（%d 条）</summary><ul class="ev-list">%s</ul></details>'
                      % (len(cross), ''.join('<li>%s</li>' % esc(x) for x in cross)))

    src = d.get('source') or {}

    # ---- 车型级销量（独立数据源，拿不到就整块不出现）
    md = load_model_data()
    model_sec = ''
    if md:
        md_period = ((md.get('period') or {}).get('label')) or ''
        md_rt = md.get('retail') or {}
        md_ws = md.get('wholesale') or {}
        md_rt_rows = md_rt.get('rows') or []
        md_ws_rows = md_ws.get('rows') or []

        # 默认展开哪个：优先零售（反映真实终端交付），零售没数据才退回批发
        default_tab = 'r' if md_rt_rows else ('w' if md_ws_rows else '')
        if default_tab:
            md_cal = md.get('caliber') or {}
            md_srcs = md.get('source') or []
            if isinstance(md_srcs, dict):
                md_srcs = [md_srcs]
            src_txt = '；'.join(
                '%s%s' % (esc(s.get('name') or ''),
                          ('（%s）' % esc(s.get('role'))) if s.get('role') else '')
                for s in md_srcs) or '懂车帝车型销量榜'

            md_notes = ''.join('<li>%s</li>' % esc(x) for x in (md.get('notes') or []))
            model_sec = """
  <section class="ev-sec" id="sec-nev-model">
    <div class="ev-sec-hd"><span class="ev-sec-no">贰</span><h2>新能源车型销量 TOP50</h2>
      <span class="ev-sec-tag">{md_period}</span></div>
    <p class="ev-lead">上面是<b>厂商</b>排行，这一节细到<b>具体车型</b>：哪一款车卖了多少辆、名次比上月涨了还是跌了。
       批发榜看出货（含出口），零售榜看国内真实上牌，<b>两者成员和排序都不同，不要混着比</b>。</p>

    <div class="ev-tabs" role="tablist">
      <button class="ev-tab{rt_on}" role="tab" data-evtab3="r" aria-selected="{rt_sel}">零售榜（国内上牌）</button>
      <button class="ev-tab{ws_on}" role="tab" data-evtab3="w" aria-selected="{ws_sel}">批发榜（含出口）</button>
    </div>

    <div class="ev-panel{rt_show}" id="evm-r"{rt_hide}>
      <p class="ev-tier-line">{rt_badge}</p>
      <p class="ev-panel-note">口径：{rt_cal}。单位：辆。</p>
      {rt_table}
      <p class="ev-src">来源：{src_txt} · 抓取时间 {md_time}</p>
    </div>

    <div class="ev-panel{ws_show}" id="evm-w"{ws_hide}>
      <p class="ev-tier-line">{ws_badge}</p>
      <p class="ev-panel-note">口径：{ws_cal}。单位：辆。</p>
      {ws_table}
      <p class="ev-src">来源：{src_txt} · 抓取时间 {md_time}</p>
    </div>

    <details class="ev-fold"><summary>关于这张车型榜，有几件事得先说清楚</summary>
      <ul class="ev-list">{md_notes}</ul>
    </details>
  </section>
""".format(
                md_period=esc(md_period),
                rt_on=' active' if default_tab == 'r' else '',
                ws_on=' active' if default_tab == 'w' else '',
                rt_sel='true' if default_tab == 'r' else 'false',
                ws_sel='true' if default_tab == 'w' else 'false',
                rt_show=' active' if default_tab == 'r' else '',
                ws_show=' active' if default_tab == 'w' else '',
                rt_hide='' if default_tab == 'r' else ' hidden',
                ws_hide='' if default_tab == 'w' else ' hidden',
                rt_badge=model_source_badge(md_rt.get('sourceTier')),
                ws_badge=model_source_badge(md_ws.get('sourceTier')),
                rt_cal=esc(md_cal.get('零售') or '终端交付/上险口径，不含出口'),
                ws_cal=esc(md_cal.get('批发') or '厂商出货口径，含出口，不等于终端交付'),
                rt_table=model_rank_table(md_rt_rows),
                ws_table=model_rank_table(md_ws_rows),
                src_txt=src_txt,
                md_time=esc(md.get('updatedAt') or md.get('updated') or ''),
                md_notes=md_notes,
            )

    return """
<main id="main-content" role="main"><div class="page-wrap">

  <header class="ev-hero">
    <div class="ev-hero-left">
      <div class="ev-hero-badge" aria-hidden="true">📊</div>
      <div class="ev-hero-txt">
        <h1 class="ev-title">新能源车销量排行榜</h1>
        <p class="ev-sub">乘联会官方数据 · 批发与零售双口径 · 数据截至 {period_txt}</p>
      </div>
    </div>
    <div class="ev-stats">{kpis}</div>
  </header>

  <section class="ev-sec" id="sec-nev-maker">
    <div class="ev-sec-hd"><span class="ev-sec-no">壹</span><h2>新能源厂商销量 TOP10</h2>
      <span class="ev-sec-tag">{nm_period}</span></div>
    <p class="ev-lead">这是本页的核心榜单：<b>新能源乘用车</b>厂商排行。批发榜看出货（含出口），
      零售榜看国内真实上牌，两者成员差异很大，合起来看才完整。</p>

    <div class="ev-tabs" role="tablist">
      <button class="ev-tab active" role="tab" data-evtab="w" aria-selected="true">批发榜（含出口）</button>
      <button class="ev-tab" role="tab" data-evtab="r" aria-selected="false">零售榜（国内上牌）</button>
    </div>

    <div class="ev-panel active" id="evp-w">
      <p class="ev-panel-note">口径：{ws_cal}</p>
      {ws_html}
      <p class="ev-src">来源：<a href="{ws_url}" target="_blank" rel="noopener noreferrer">{ws_src}</a>
        （转载乘联会终稿数据）· 人工核对日期 {verified}</p>
    </div>

    <div class="ev-panel" id="evp-r" hidden>
      <p class="ev-panel-note">口径：{rt_cal}</p>
      {rt_html}
      <p class="ev-src">来源：<a href="{rt_url}" target="_blank" rel="noopener noreferrer">{rt_src}</a>
        、<a href="{rt_url2}" target="_blank" rel="noopener noreferrer">新浪汽车</a>
        （均转载乘联会数据，两家报道逐位比对一致）· 人工核对日期 {verified}</p>
    </div>

    {cross_html}

    <details class="ev-fold"><summary>关于这两张榜的几点说明</summary>
      <ul class="ev-list">{notes_html}</ul>
    </details>
  </section>
{model_sec}
  <section class="ev-sec" id="sec-penetration">
    <div class="ev-sec-hd"><span class="ev-sec-no">叁</span><h2>新能源渗透率走势</h2>
      <span class="ev-sec-tag">近 12 个月</span></div>
    <p class="ev-lead">新能源车在国内零售中的占比。{pen_txt}</p>
    <div class="ev-chart-box">{chart_pen}</div>
    <p class="ev-note">口径：NEV 指纯电 + 插混 + 增程，占狭义乘用车国内零售的比例；数据来自乘联会官方接口。</p>
  </section>

  <section class="ev-sec" id="sec-structure">
    <div class="ev-sec-hd"><span class="ev-sec-no">肆</span><h2>纯电 / 插混结构</h2>
      <span class="ev-sec-tag">{struct_lb}</span></div>
    <p class="ev-lead">新能源内部的技术路线分布（零售口径）。</p>
    <div class="ev-chart-box">{chart_struct}</div>
    <p class="ev-note"><b>注意：</b>纯电 + 插混 <b>不等于</b>新能源总量，差额主要是增程式（EREV）。
      上表中的增程为总量倒推值，仅供参考；总量请以乘联会公布口径为准。</p>
  </section>

  <section class="ev-sec" id="sec-camp">
    <div class="ev-sec-hd"><span class="ev-sec-no">伍</span><h2>品牌阵营份额</h2>
      <span class="ev-sec-tag">{camp_lb}</span></div>
    <p class="ev-lead">按国别划分的乘用车零售销量与份额。自主品牌份额 {own_share}，
      合资阵营持续承压。</p>
    <div class="ev-chart-box">{chart_camp}</div>
    <p class="ev-note">口径：狭义乘用车国内零售。德系、日系等按品牌归属国别划分。</p>
  </section>

  <section class="ev-sec" id="sec-total">
    <div class="ev-sec-hd"><span class="ev-sec-no">陆</span><h2>乘用车厂商总销量榜</h2>
      <span class="ev-sec-tag">{mon_label}</span></div>
    <p class="ev-warn"><b>这不是新能源榜。</b>下面这张是<b>全部乘用车</b>（含燃油车）的厂商排名，
      用来对照看各家的基本盘。要看新能源排行请回到页首第壹节。</p>

    <div class="ev-tabs" role="tablist">
      <button class="ev-tab active" role="tab" data-evtab2="w" aria-selected="true">批发</button>
      <button class="ev-tab" role="tab" data-evtab2="r" aria-selected="false">零售</button>
    </div>
    <div class="ev-panel active" id="evt-w">{api_ws}</div>
    <div class="ev-panel" id="evt-r" hidden>{api_rt}</div>
    <p class="ev-src">来源：乘联会官方数据接口 · 狭义乘用车口径 · 单位万辆</p>
  </section>

  <section class="ev-sec" id="sec-caliber">
    <div class="ev-sec-hd"><span class="ev-sec-no">柒</span><h2>口径说明与数据来源</h2></div>
    <div class="ev-cal">
      <dl>
        <dt>批发</dt><dd>厂商开给经销商及出口的出货量，<b>含出口</b>，不等于终端实际交付。</dd>
        <dt>零售</dt><dd>经销商卖给最终用户的上险/上牌量，反映真实终端需求。</dd>
        <dt>狭义乘用车</dt><dd>轿车 + SUV + MPV，不含微客。</dd>
        <dt>新能源</dt><dd>BEV（纯电）+ PHEV（插混）+ EREV（增程），不含普通混动 HEV。</dd>
      </dl>
    </div>
    <p class="ev-note">
      主数据来自<b>乘用车市场信息联席会（乘联会 / CPCA）</b>官方数据中心
      <a href="{src_home}" target="_blank" rel="noopener noreferrer">{src_home}</a>，
      每月中旬更新上月数据，本站通过官方接口自动同步（当前数据期：{period_txt}）。<br>
      新能源厂商榜因官方原文以图片发布、且月初「快讯」为初步数据（官方明确提示不可与终稿直接对比），
      故采用转载终稿的媒体报道并<b>人工核对</b>后录入，核对日期 {verified}。<br>
      <b>本站不生产数据</b>，所有数字均标注出处；口径不同会导致排名差异，请以官方原文为准。
      数据版权归乘联会所有。
    </p>
  </section>

</div></main>
""".format(
        period_txt='%d年%s' % (y, cum_lb or mon_lb or ''),
        kpis=kpi_html,
        model_sec=model_sec,
        nm_period=esc(nm.get('period') or ''),
        ws_cal=esc(ws.get('caliber') or ''),
        ws_html=ws_html,
        ws_url=esc(ws.get('sourceUrl') or '#'),
        ws_src=esc(ws.get('sourceName') or ''),
        rt_cal=esc(rt.get('caliber') or ''),
        rt_html=rt_html,
        rt_url=esc(rt.get('sourceUrl') or '#'),
        rt_url2=esc(rt.get('extraSourceUrl') or '#'),
        rt_src=esc(rt.get('sourceName') or ''),
        verified=esc(nm.get('verifiedOn') or ''),
        notes_html=notes_html,
        cross_html=cross_html,
        pen_txt='最新月份为 %s，渗透率 %s。' % (
            esc((last_ni.get('label') or '').replace('2026-', '').replace('2025-', '2025年/')),
            pct(nev_d.get('rtShare'))),
        chart_pen=chart_pen,
        struct_lb=esc((last_bp.get('label') or '').replace('2026-', '').replace('2025-', '2025年/')),
        chart_struct=chart_struct,
        camp_lb=esc((last_seg.get('label') or '').replace('2026-', '').replace('2025-', '2025年/')),
        own_share=pct(own.get('rtShare')),
        chart_camp=chart_camp,
        mon_label=esc(mon.get('label') or ''),
        api_ws=api_ws,
        api_rt=api_rt,
        src_home=esc(src.get('home') or 'http://data.cpcadata.com/'),
    )


# ---------------------------------------------------------------- 专属样式
CSS = """
<style>
/* ===== 新能源销量榜专属样式（国风黑金） ===== */
.ev-hero{display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;
  padding:24px 22px;margin:18px 0 14px;background:var(--card);border:1px solid var(--border);
  border-radius:16px;position:relative;overflow:hidden}
.ev-hero::after{content:'';position:absolute;right:-46px;top:-46px;width:170px;height:170px;border-radius:50%;
  background:radial-gradient(circle,rgba(201,168,76,.13),transparent 70%);pointer-events:none}
.ev-hero-left{display:flex;align-items:center;gap:14px;min-width:0}
.ev-hero-badge{flex:0 0 48px;width:48px;height:48px;border-radius:14px;display:flex;align-items:center;
  justify-content:center;font-size:1.5rem;background:rgba(201,168,76,.12);border:1px solid rgba(201,168,76,.28)}
.ev-title{font-size:1.7rem;color:var(--gold);letter-spacing:1px;line-height:1.2;margin:0}
.ev-sub{color:var(--text-secondary);font-size:.86rem;margin-top:4px}
.ev-stats{display:flex;gap:10px;flex-wrap:wrap}
.ev-stat{flex:1 1 96px;min-width:96px;text-align:center;padding:10px 8px;background:var(--bg-secondary);
  border:1px solid var(--border);border-radius:10px}
.ev-stat b{display:block;font-size:1.28rem;color:var(--gold);font-weight:800;line-height:1.15;
  word-break:break-all}
.ev-stat-lb{display:block;font-size:.74rem;color:var(--text-secondary);margin-top:3px}
.ev-stat-sub{display:block;font-size:.66rem;color:var(--text-muted);margin-top:2px;line-height:1.35}

.ev-sec{margin:26px 0;padding:20px 18px;background:var(--card);border:1px solid var(--border);border-radius:14px}
.ev-sec-hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;
  padding-bottom:9px;border-bottom:1px solid var(--border)}
.ev-sec-no{flex:0 0 auto;width:26px;height:26px;border-radius:7px;display:flex;align-items:center;
  justify-content:center;font-size:.82rem;color:#111;background:var(--gold);font-weight:700}
.ev-sec-hd h2{font-size:1.12rem;color:var(--text);margin:0;flex:1 1 auto}
.ev-sec-tag{font-size:.72rem;color:var(--text-muted);border:1px solid var(--border);
  border-radius:20px;padding:2px 10px}
.ev-lead{color:var(--text-secondary);font-size:.88rem;line-height:1.75;margin:0 0 12px}
.ev-lead b{color:var(--gold)}
.ev-note{color:var(--text-muted);font-size:.79rem;line-height:1.7;margin:9px 0 0}
.ev-note b{color:var(--text-secondary)}
.ev-warn{background:rgba(193,64,64,.09);border:1px solid rgba(193,64,64,.3);border-radius:9px;
  padding:10px 13px;color:var(--text-secondary);font-size:.83rem;line-height:1.7;margin:0 0 13px}
.ev-warn b{color:var(--cinnabar)}
.ev-src{color:var(--text-muted);font-size:.76rem;margin-top:10px;line-height:1.7}
.ev-src a{color:var(--blue-light)}
.ev-unit{color:var(--text-muted);font-size:.73rem;margin-top:5px;text-align:right}

.ev-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}
.ev-tab{background:var(--bg-secondary);color:var(--text-secondary);border:1px solid var(--border);
  border-radius:9px;padding:8px 15px;font-size:.84rem;cursor:pointer;min-height:38px;
  transition:all .18s ease}
.ev-tab:hover{border-color:var(--gold);color:var(--gold)}
.ev-tab.active{background:var(--gold);color:#111;border-color:var(--gold);font-weight:600}
.ev-panel{display:none}
.ev-panel.active{display:block}
.ev-panel-note{color:var(--text-muted);font-size:.78rem;margin:0 0 8px;padding-left:9px;
  border-left:3px solid var(--gold)}

.ev-table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -2px}
table.ev-rank{width:100%;border-collapse:collapse;font-size:.85rem;min-width:320px}
table.ev-rank th{background:var(--bg-secondary);color:var(--text-secondary);font-weight:600;
  font-size:.76rem;text-align:right;padding:9px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
table.ev-rank th:first-child,table.ev-rank th:nth-child(2){text-align:left}
table.ev-rank td{padding:9px 10px;border-bottom:1px solid var(--border);text-align:right;
  color:var(--text);vertical-align:middle}
table.ev-rank td.nm{text-align:left;font-weight:600;white-space:nowrap}
table.ev-rank td.rk{text-align:center;color:var(--text-muted);font-size:.78rem;width:38px}
table.ev-rank td.rk::before{content:none}
table.ev-rank tbody tr:nth-child(1) td.rk{color:var(--gold);font-weight:800}
table.ev-rank tbody tr:nth-child(2) td.rk,table.ev-rank tbody tr:nth-child(3) td.rk{color:var(--gold);font-weight:700}
table.ev-rank td.vl{font-variant-numeric:tabular-nums;font-weight:600}
table.ev-rank td.vl.sub{color:var(--text-muted);font-weight:400;font-size:.8rem}
table.ev-rank td.up{color:#e04b4b;font-weight:600;font-variant-numeric:tabular-nums}
table.ev-rank td.down{color:#3aa76d;font-weight:600;font-variant-numeric:tabular-nums}
table.ev-rank td.flat{color:var(--text-muted);font-variant-numeric:tabular-nums}

.ev-chart-box{margin:6px 0 0;color:var(--text)}
svg.ev-chart{display:block;width:100%;height:auto;max-width:100%;overflow:visible}
.ev-chart text{font-family:inherit}

.ev-cal{margin:4px 0 12px}
.ev-cal dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:8px 14px}
.ev-cal dt{color:var(--gold);font-size:.83rem;font-weight:600;white-space:nowrap}
.ev-cal dd{margin:0;color:var(--text-secondary);font-size:.83rem;line-height:1.7}
.ev-cal dd b{color:var(--text)}

.ev-fold{margin:14px 0 0;border:1px solid var(--border);border-radius:9px;background:var(--bg-secondary)}
.ev-fold summary{cursor:pointer;padding:10px 14px;font-size:.84rem;color:var(--text-secondary);
  list-style:none;display:flex;align-items:center;gap:7px;min-height:40px}
.ev-fold summary::-webkit-details-marker{display:none}
.ev-fold summary::before{content:'▸';color:var(--gold);font-size:.8rem;transition:transform .18s}
.ev-fold[open] summary::before{transform:rotate(90deg)}
.ev-list{margin:0;padding:2px 16px 14px 30px;color:var(--text-secondary);font-size:.83rem;line-height:1.85}
.ev-list li{margin:5px 0}

/* ===== 车型销量榜（第贰节） ===== */
/* 车型表 6 列，比厂商表密：给车型名列留白、允许换行，窄屏才不至于横向拖 */
table.ev-model{min-width:300px}
table.ev-model td.nm{white-space:normal;font-weight:600;line-height:1.45;min-width:104px}
table.ev-model td.bd{text-align:left;color:var(--text-secondary);font-size:.8rem;white-space:nowrap}
table.ev-model td.vl{white-space:nowrap}

/* 同系合计：懂车帝按动力版本分列，单看一条会低估整个车系，
   故在车系首次出现的那行补一行合计，分列数字保持原样不合并 */
.ev-grp{display:block;margin-top:3px;font-size:.72rem;color:var(--text-muted);
  line-height:1.5;font-weight:400}
.ev-grp b{color:var(--gold);font-weight:700;font-variant-numeric:tabular-nums}
.ev-grp-parts{display:block;color:var(--text-muted);opacity:.85;font-size:.68rem}

/* 来源等级标识：批发能溯源到乘联会终稿、零售不能，两者必须一眼可辨，
   不能让用户以为这两张榜同样官方 */
.ev-tier-line{margin:0 0 7px}
.ev-tier{display:inline-block;font-size:.73rem;line-height:1.5;padding:3px 10px;border-radius:20px;
  border:1px solid var(--border);cursor:help}
.ev-tier-traceable{color:#3aa76d;background:rgba(58,167,109,.10);border-color:rgba(58,167,109,.38)}
.ev-tier-platform{color:var(--text-secondary);background:var(--bg-secondary);
  border-color:var(--border);border-style:dashed}

/* 车型名外链（懂车帝车型页），仅在有 seriesId 时出现 */
table.ev-model td.nm a{color:var(--text);text-decoration:none;border-bottom:1px dotted var(--border)}
table.ev-model td.nm a:hover{color:var(--gold);border-bottom-color:var(--gold)}

@media(max-width:600px){
  .ev-title{font-size:1.35rem}
  .ev-hero{padding:18px 15px;gap:14px}
  .ev-stat{flex:1 1 76px;min-width:76px;padding:9px 5px}
  .ev-stat b{font-size:1.05rem}
  .ev-sec{padding:16px 13px;border-radius:12px}
  .ev-sec-hd h2{font-size:1rem}
  table.ev-rank{font-size:.8rem}
  table.ev-rank th,table.ev-rank td{padding:8px 6px}
  .ev-cal dl{grid-template-columns:1fr;gap:3px}
  .ev-cal dd{padding-bottom:8px}
  /* 车型表在窄屏彻底放弃横向滚动：缩字号 + 让车型名换行 */
  table.ev-model{min-width:0;font-size:.78rem}
  table.ev-model th,table.ev-model td{padding:7px 4px}
  table.ev-model td.nm{min-width:0;font-size:.78rem}
  table.ev-model td.bd{font-size:.72rem;white-space:normal}
  .ev-grp{font-size:.68rem}
  .ev-grp-parts{font-size:.64rem}
  .ev-tier{font-size:.7rem;padding:3px 8px}
}
</style>
"""


def main():
    with open(DATA, encoding='utf-8') as f:
        d = json.load(f)
    with open(DONOR, encoding='utf-8') as f:
        donor = f.read()

    src = d.get('source') or {}
    period = d.get('period') or {}
    period_txt = '%d年%s' % (period.get('year') or 2026,
                             period.get('cumulativeLabel') or period.get('monthlyLabel') or '')

    # ---- head：复用 donor 的 head（含 critical CSS 与 CSP），只替换 TDK
    head_end = donor.index('<link rel="stylesheet"')
    head = donor[:head_end]
    head = head.replace(
        '<title>充电桩查询｜全国新能源充电站实时地图 · 按价格排序｜龙兄知识库</title>',
        '<title>新能源车销量排行榜｜厂商 TOP10 · 渗透率走势｜龙兄知识库</title>')
    head = head.replace(
        '<meta name="keywords" content="充电桩查询,充电站地图,全国充电桩,新能源充电,电费价格,附近充电桩,充电站比价,盐城充电桩,射阳充电桩,龙兄知识库">',
        '<meta name="keywords" content="新能源汽车销量排行,新能源厂商销量TOP10,电动车销量榜,新能源渗透率,乘联会,比亚迪销量,特斯拉销量,理想蔚来小鹏销量,龙兄知识库">')
    head = head.replace(
        '<meta name="description" content="打开即定位，自动显示你所在地区的全部新能源充电站：国家电网、特来电、星星充电、蔚来、特斯拉等各品牌一站聚合，支持按距离或价格排序、一键导航、一键查实时电价。">',
        '<meta name="description" content="新能源乘用车厂商销量排行榜：批发与零售双口径 TOP10、新能源渗透率走势、纯电插混结构、品牌阵营份额。数据取自乘联会官方接口并交叉核验，口径标注清晰，不混淆批发与零售。">')
    head = head.replace('<meta name="article-category" content="实用工具">',
                        '<meta name="article-category" content="数据榜单">')
    head = head.replace('<meta name="article-tags" content="充电桩,新能源,定位,便民工具">',
                        '<meta name="article-tags" content="新能源汽车,销量排行,乘联会,渗透率,数据榜单">')
    head = head.replace('<meta name="article-updated" content="2026-08-30">',
                        '<meta name="article-updated" content="%s">' % d.get('updated', ''))

    # ---- body 起始到 <main> 之前（navbar 原样复用）
    body_start = donor.index('<body>')
    main_start = donor.index('<main id="main-content"')
    body_head = donor[body_start:main_start]
    # 导航栏补上本页入口
    body_head = body_head.replace(
        '<li><a href="console.html">游戏主机</a></li>',
        '<li><a href="console.html">游戏主机</a></li>\n      <li><a href="ev-sales.html" class="active">销量排行</a></li>')
    body_head = body_head.replace(
        '<a href="ev-charge.html">充电桩查询</a>',
        '<a href="ev-charge.html">充电桩查询</a>\n          <a href="ev-sales.html">销量排行</a>')
    body_head = body_head.replace(
        '<a href="index.html">首页</a>',
        '<a href="index.html">首页</a>\n    <a href="ev-sales.html">销量排行</a>')

    body = build_body(d)

    # ---- footer
    foot_start = donor.index('<footer role="contentinfo">')
    foot_end = donor.index('</footer>') + len('</footer>')
    footer = donor[foot_start:foot_end].replace(
        '充电桩位置数据由高德地图提供，价格信息以各运营商现场公示为准，本页不承担因数据变动导致的任何责任。<br>',
        '销量数据版权归乘用车市场信息联席会（乘联会）所有，本站仅作引用并注明出处；'
        '批发与零售口径不同，排名会有差异，请以官方原文为准。<br>')

    # ---- 脚本区
    scripts = """
<script async src="/js/busuanzi.pure.mini.js" integrity="sha384-oaKlriFiEaHzTKw66TKlzwgjYHPT5tvx+uf4JRnAGvP7HCHj5NPqEoAkyyOAPxZN" crossorigin="anonymous"></script>
<script defer src="/js/board-nav.js"></script>
<script defer src="js/search.js"></script>
<script defer src="js/app.js"></script>
<script defer src="js/ev-sales.js?v=__VJS__"></script>
<script defer src="js/share.js"></script>
<!-- 悬浮栏目目录 quick-toc.js 与本地收藏 bookmark.js 由
     scripts/apply_site_widgets.py 统一注入（含 #quickToc 容器）。
     这里不要再写一遍，否则组件脚本会被重复加载两次。 -->
</body>
</html>
""".replace("__VJS__", V_JS)

    out = head + CSS + '\n<link rel="stylesheet" href="css/style.css?v=%s">\n</head>\n\n' % V_CSS \
        + body_head + body + '\n' + footer + '\n' + scripts

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(out)
    print('已生成 %s（%d 字符）' % (OUT, len(out)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
