#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取乘联会（CPCA）官方数据，生成 static/ev-sales.json —— 新能源车销量排行榜板块的数据源。

数据源：乘用车市场信息联席会（乘联会 / CPCA）官方数据中心
    http://data.cpcadata.com/
    接口：http://data.cpcadata.com/api/chartlist?type=1&charttype=N   (N = 1..6)
    备用：http://data.cpcadata.com/api/chartlist_2?type=1&charttype=N

字段含义（已从前端渲染脚本 static/js/main.*.chunk.js 逆向确认，并用乘联会官方原文逐位校验）：

    charttype=1 整体市场月度：数值数组 = [产量, 批发, 零售, 出口]，单位万辆
        （下拉框选项顺序即为此；2025年1月零售 179.45 万、出口 37.79 万与公开数据吻合）
    charttype=2 厂商 TOP10  ：数值数组 = [批发, 零售]，单位万辆
        ⚠️ 注意：这是【全部乘用车】厂商榜，含燃油车，不是新能源榜。
           证据：零售榜成员含一汽大众/广汽丰田/一汽丰田/上汽大众等合资燃油大户，
           而官方新能源零售榜是鸿蒙智行/蔚来/小米/上汽乘用车 —— 成员完全不同。
           纯新能源车企（比亚迪/零跑/特斯拉）两榜数值相同，可作交叉验证锚点。
    charttype=3 分车型      ：MPV / SUV / 轿车 / 占比
    charttype=4 分国别      ：自主 / 德系 / 日系 / 美系 / 韩系 / 法系 / 其他欧系
    charttype=5 分级别      ：A0 / A / B / C × 车型
    charttype=6 新能源      ：组0 整体(产量/批发/零售/出口)；组1 BEV/PHEV；组2 ICE/NEV

    关于 charttype=4/5/6 的四列（重要，先前误判为「今年/去年」，已依官方原文修正）：
        [0] 批发销量  [1] 零售销量  [2] 批发占比%  [3] 零售占比%
        校验：2026年7月国别批发加总 225.1529 万、零售加总 146.0941 万，
              与官方「7月乘用车零售 146.1 万辆」吻合；NEV 零售占比 65.1%，
              与官方「新能源渗透率 65.1% 创历史新高」完全一致。

    ⚠️ BEV + PHEV ≠ NEV 总量（还差增程 EREV）。
       2026年7月：BEV 64.7 + PHEV 21.9 + EREV 8.5 = 95.1 万零售。
       因此页面展示新能源总量时必须用各组原始值，绝不自行把 BEV 和 PHEV 相加冒充总量。

重要口径说明（页面必须如实标注，不可混淆）：
    批发 = 厂商开给经销商及出口的出货量，含出口，不等于终端实际交付
    零售 = 经销商卖给最终用户的上险/上牌量，反映真实终端需求
    狭义乘用车 = 轿车 + SUV + MPV（不含微客）；广义乘用车 = 狭义 + 微客

安全策略（数据正确性红线）：
    任何一个数据集抓取/解析失败，都不会写入半成品；全部成功才落盘。
    拿不到的数据一律留空并标注，绝不编造、绝不用旧数据冒充当期。

用法：
    python3 scripts/fetch_ev_sales.py            # 抓取并写入 static/ev-sales.json
    python3 scripts/fetch_ev_sales.py --dry-run  # 只打印结果，不写文件
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'static', 'ev-sales.json')

API = 'http://data.cpcadata.com/api/chartlist'
API2 = 'http://data.cpcadata.com/api/chartlist_2'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# 单位口径：接口返回的数值单位是「万辆」
# charttype=1 的四列，顺序来自前端下拉框 [产量, 批发, 零售, 出口]
OVERALL_COLS = ['产量', '批发', '零售', '出口']
# charttype=2 的两列，顺序来自前端下拉框 [批发, 零售]
MAKER_COLS = ['批发', '零售']

# ---------------------------------------------------------------------------
# 新能源厂商榜 —— 人工核对快照（不是自动抓取，务必如实理解）
#
# 为什么不能自动抓：
#   1. 乘联会官网《新能源乘用车厂商批发销量快讯》里的榜单是【图片】，
#      无法程序化解析（已实测：页面无任何 <table> 节点）。
#   2. 该快讯发布于月初、属【初步数据】，官网原文明确警告：
#      「由于乘联快报数据可能与厂商终稿数据有差异，因此对此版的具体厂商数据
#        不要与历史终稿数据直接对比，以防误导。」
#   3. 乘联会数据接口 charttype=2 是【全部乘用车】厂商榜（含燃油车），
#      并非新能源榜，不能拿它冒充新能源排行。
#
# 因此：本段数字取自转载乘联会【终稿】的媒体报道，并经多源交叉验证后才写入。
# 每次更新必须人工核对，同步修改 period / verifiedOn / 数字 / 来源。
#
# 交叉验证记录（2026-09-02 核对）：
#   比亚迪 7月批发 410,612 辆 = 41.0612 万辆
#       -> 与接口 charttype=2 组1 比亚迪 [0] 完全一致 ✓
#   比亚迪 7月零售 223,461 辆 = 22.3461 万辆
#       -> 与接口组1 比亚迪 [1] 完全一致 ✓
#   零跑 101,267 辆 = 10.1267 万辆 -> 与接口零跑 [0] 一致 ✓
#   特斯拉 93,579 辆 = 9.3579 万辆 -> 与接口特斯拉 [0] 一致 ✓
#   （比亚迪/零跑/特斯拉为纯新能源车企，故批发口径下两榜必然相等，可作锚点）
#   零售榜十家数字经网通社、新浪两家独立报道逐位比对，全部一致 ✓
# ---------------------------------------------------------------------------
NEV_MAKER_SNAPSHOT = {
    'period': '2026年7月',
    'verifiedOn': '2026-09-02',
    'unit': '辆',
    'autoFetched': False,
    'wholesale': {
        'title': '新能源乘用车厂商批发销量 TOP10',
        'caliber': '狭义乘用车批发销量（含出口，非终端交付）',
        'sourceName': '盖世汽车（转载乘联会终稿数据）',
        'sourceUrl': 'https://m.gasgoo.com/qcxl/article/81426.html',
        'rows': [
            {'rank': 1, 'name': '比亚迪汽车', 'units': 410612, 'cumulative': 2187987, 'yoy': 20.40, 'mom': 3.35},
            {'rank': 2, 'name': '吉利汽车', 'units': 163678, 'cumulative': 1713591, 'yoy': -32.85, 'mom': -33.99},
            {'rank': 3, 'name': '奇瑞汽车', 'units': 108014, 'cumulative': 1427119, 'yoy': -48.58, 'mom': -48.24},
            {'rank': 4, 'name': '零跑汽车', 'units': 101267, 'cumulative': 457754, 'yoy': 102.01, 'mom': 8.45},
            {'rank': 5, 'name': '特斯拉汽车', 'units': 93579, 'cumulative': 561528, 'yoy': 37.85, 'mom': 5.04},
            {'rank': 6, 'name': '上汽通用五菱', 'units': 61539, 'cumulative': 494434, 'yoy': -20.30, 'mom': -30.01},
            {'rank': 7, 'name': '长安汽车', 'units': 60977, 'cumulative': 722387, 'yoy': -55.32, 'mom': -45.31},
            {'rank': 8, 'name': '上汽乘用车', 'units': 59406, 'cumulative': 701568, 'yoy': -17.26, 'mom': -51.74},
            {'rank': 9, 'name': '长城汽车', 'units': 40140, 'cumulative': 582891, 'yoy': -55.69, 'mom': -57.30},
            {'rank': 10, 'name': '小鹏汽车', 'units': 38027, 'cumulative': 204004, 'yoy': 3.57, 'mom': -5.23},
        ],
    },
    'retail': {
        'title': '新能源乘用车厂商零售销量 TOP10',
        'caliber': '国内零售口径（上牌/开票，不含出口）',
        'sourceName': '网通社汽车（转载乘联会）、新浪汽车',
        'sourceUrl': 'https://auto.news18a.com/news/storys_285699.html',
        'extraSourceUrl': 'https://www.sina.cn/gc/article/ninhait2961667.html',
        'rows': [
            {'rank': 1, 'name': '比亚迪汽车', 'units': 223461, 'cumulative': None, 'yoy': -0.45, 'mom': None},
            {'rank': 2, 'name': '吉利汽车', 'units': 105526, 'cumulative': None, 'yoy': -2.3, 'mom': None},
            {'rank': 3, 'name': '零跑汽车', 'units': 83698, 'cumulative': None, 'yoy': 15.6, 'mom': None},
            {'rank': 4, 'name': '长安汽车', 'units': 59907, 'cumulative': None, 'yoy': None, 'mom': None},
            {'rank': 5, 'name': '上汽通用五菱', 'units': 48967, 'cumulative': None, 'yoy': None, 'mom': None},
            {'rank': 6, 'name': '鸿蒙智行', 'units': 45422, 'cumulative': None, 'yoy': None, 'mom': None},
            {'rank': 7, 'name': '奇瑞汽车', 'units': 39079, 'cumulative': None, 'yoy': None, 'mom': None},
            {'rank': 8, 'name': '蔚来汽车', 'units': 35842, 'cumulative': None, 'yoy': None, 'mom': None},
            {'rank': 9, 'name': '上汽乘用车', 'units': 31471, 'cumulative': None, 'yoy': None, 'mom': None},
            {'rank': 10, 'name': '小米汽车', 'units': 31267, 'cumulative': None, 'yoy': None, 'mom': None},
        ],
    },
    'notes': [
        '批发榜与零售榜成员差异很大，这是正常的：批发含出口，零售只算国内上牌。',
        '小鹏 7月全球交付 38,027 辆，但其中近 1 万辆来自出口，国内零售仅 28,327 辆，故未进零售榜前十。',
        '蔚来、小米只出现在零售榜而未进批发榜前十，是两家媒体各自榜单口径与名单长度不同所致，非数据矛盾。',
    ],
}

TIMEOUT = 30
RETRY = 3


def fetch_json(url, params):
    """带重试地抓取 JSON。失败抛异常，绝不返回半成品。"""
    qs = '&'.join('%s=%s' % (k, v) for k, v in params.items())
    full = '%s?%s' % (url, qs)
    last = None
    for attempt in range(1, RETRY + 1):
        try:
            req = urllib.request.Request(full, headers={
                'User-Agent': UA,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'http://data.cpcadata.com/',
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read().decode('utf-8', errors='replace')
            return json.loads(raw)
        except Exception as e:                      # noqa: BLE001
            last = e
            if attempt < RETRY:
                time.sleep(1.5 * attempt)
    raise RuntimeError('抓取失败 %s -> %s' % (full, last))


def num(v):
    """把接口数值统一成 float。None/空一律返回 None，不猜。"""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, 4)


def parse_period_label(keys, row0):
    """
    从厂商榜的 key 里解析出统计区间。
    形如 '2026年 1-7月'（累计）或 '2026年7月'（单月）
    返回 (year, cum_months, latest_month, cum_label, month_label)
    """
    for k in keys:
        if k == '厂商' or '同比' in k:
            continue
        m = re.search(r'(\d{4})年\s*(\d+)\s*-\s*(\d+)月', k)
        if m:
            y, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return y, b, b, '%d-%d月' % (a, b), None
        m = re.search(r'(\d{4})年\s*(\d+)月', k)
        if m:
            y, mo = int(m.group(1)), int(m.group(2))
            return y, mo, mo, '1-%d月' % mo, '%d月' % mo
    return None, None, None, None, None


def build_maker_rank(data_ws, data_rt, group_index, value_index, col_name):
    """
    厂商榜：名单按各自口径排序（批发榜取 /chartlist，零售榜取 /chartlist_2），
    数值统一从该行数组取第 value_index 位。

    之所以名单和数值分开取：两个接口的 TOP10 成员不同
    （批发榜含长城/特斯拉等出口大户，零售榜含广汽丰田/一汽丰田等合资内销大户），
    但交集厂商的数值完全一致 —— 说明接口返回的是同一份两列数据，只是榜单排序口径不同。
    """
    src = data_ws if col_name == '批发' else data_rt
    grp = src[group_index]
    rows = grp.get('dataList') or []
    if not rows:
        raise RuntimeError('厂商榜组%d 数据为空' % group_index)

    keys = [k for k in rows[0].keys() if k not in ('厂商', '同比')]
    if len(keys) < 2:
        raise RuntimeError('厂商榜缺少年份字段: %s' % list(rows[0].keys()))
    # 当年 key 与去年 key：取含最大年份的那个
    year_keys = sorted(keys, key=lambda k: int(re.search(r'(\d{4})', k).group(1)) if re.search(r'(\d{4})', k) else 0)
    cur_key, prev_key = year_keys[-1], year_keys[0]

    out = []
    for i, row in enumerate(rows, 1):
        name = row.get('厂商')
        if not name:
            continue
        cur = row.get(cur_key) or []
        prev = row.get(prev_key) or []
        yoy = row.get('同比') or []
        out.append({
            'rank': i,
            'name': name,
            'value': num(cur[value_index]) if len(cur) > value_index else None,
            'prev': num(prev[value_index]) if len(prev) > value_index else None,
            'yoy': round(float(yoy[value_index]), 2) if len(yoy) > value_index and yoy[value_index] is not None else None,
        })
    return out, cur_key, prev_key


def build_overall(data):
    """整体市场月度走势：狭义乘用车（组0）。"""
    grp = data[0]
    rows = grp.get('dataList') or []
    series = []
    for row in rows:
        y26 = row.get('2026年')
        # 只保留真正有数的月份（接口会回填 12 条，未发生的月份为空）
        if not y26 or not any(v is not None for v in y26):
            continue
        m = re.match(r'(\d+)月', str(row.get('month') or ''))
        if not m:
            continue
        series.append({
            'month': int(m.group(1)),
            '产量': num(y26[0]),
            '批发': num(y26[1]),
            '零售': num(y26[2]),
            '出口': num(y26[3]),
        })
    return series


def build_nev(data):
    """
    新能源数据。
    组0 = 新能源整体市场月度（[产量, 批发, 零售, 出口]）
    组1 = BEV / PHEV 拆分（[批发, 零售, 批发占比%, 零售占比%]）
    组2 = ICE / NEV 对比 （[批发, 零售, 批发占比%, 零售占比%]）

    ⚠️ 不可把 BEV 与 PHEV 相加当作新能源总量（还差增程 EREV）。
    """
    def pick(idx):
        grp = data[idx] if idx < len(data) else None
        return (grp or {}).get('dataList') or []

    # 组0：新能源整体月度走势
    overall = []
    for row in pick(0):
        m = re.match(r'(\d+)月', str(row.get('month') or ''))
        if not m:
            continue
        v = row.get('2026年') or []
        if not v or not any(x is not None for x in v):
            continue
        overall.append({
            'month': int(m.group(1)),
            '产量': num(v[0]) if len(v) > 0 else None,
            '批发': num(v[1]) if len(v) > 1 else None,
            '零售': num(v[2]) if len(v) > 2 else None,
            '出口': num(v[3]) if len(v) > 3 else None,
        })

    def pair(rows, a_key, b_key):
        out = []
        for row in rows:
            label = str(row.get('月份') or '')
            if not label:
                continue
            a = row.get(a_key) or []
            b = row.get(b_key) or []
            if not a and not b:
                continue
            out.append({
                'label': label,
                a_key: {'wholesale': num(a[0]) if len(a) > 0 else None,
                        'retail': num(a[1]) if len(a) > 1 else None,
                        'wsShare': num(a[2]) if len(a) > 2 else None,
                        'rtShare': num(a[3]) if len(a) > 3 else None},
                b_key: {'wholesale': num(b[0]) if len(b) > 0 else None,
                        'retail': num(b[1]) if len(b) > 1 else None,
                        'wsShare': num(b[2]) if len(b) > 2 else None,
                        'rtShare': num(b[3]) if len(b) > 3 else None},
            })
        return out

    return {
        'overall': overall,
        'bevPhev': pair(pick(1), 'BEV', 'PHEV'),
        'nevIce': pair(pick(2), 'NEV', 'ICE'),
    }


def build_segment(data):
    """分国别市场份额：[批发, 零售, 批发占比%, 零售占比%]"""
    rows = (data[0] if data else {}).get('dataList') or []
    labels = ['自主', '德系', '日系', '美系', '韩系', '法系', '其他欧系']
    out = []
    for row in rows:
        label = str(row.get('月份') or '')
        if not label:
            continue
        rec = {'label': label}
        has = False
        for lb in labels:
            v = row.get(lb)
            if not v:
                continue
            rec[lb] = {
                'wholesale': num(v[0]) if len(v) > 0 else None,
                'retail': num(v[1]) if len(v) > 1 else None,
                'wsShare': num(v[2]) if len(v) > 2 else None,
                'rtShare': num(v[3]) if len(v) > 3 else None,
            }
            has = True
        if has:
            out.append(rec)
    return out


def main():
    dry = '--dry-run' in sys.argv
    now = datetime.now(timezone(timedelta(hours=8)))

    errors = []
    result = {
        'updated': now.strftime('%Y-%m-%d'),
        'updatedAt': now.strftime('%Y-%m-%d %H:%M'),
        'source': {
            'name': '乘用车市场信息联合会（乘联会 / CPCA）官方数据中心',
            'home': 'http://data.cpcadata.com/',
            'org': 'http://www.cpcaauto.com/',
            'api': API,
            'licence': '数据版权归乘联会所有，本站仅作引用并注明出处',
        },
        'units': '万辆',
        'caliber': {
            '批发': '厂商开给经销商及出口的出货量，含出口，不等于终端实际交付量',
            '零售': '经销商卖给最终用户的上险/上牌量，反映真实终端需求',
            '狭义乘用车': '轿车 + SUV + MPV，不含微客',
            '新能源': 'BEV（纯电）+ PHEV（插电混动），不含普通混动（HEV）',
            '单位说明': '接口数值单位为万辆',
        },
    }

    # ---------- 厂商榜（charttype=2）----------
    try:
        ws = fetch_json(API, {'type': 1, 'charttype': 2})
        rt = fetch_json(API2, {'type': 1, 'charttype': 2})
        if len(ws) < 4 or len(rt) < 4:
            raise RuntimeError('厂商榜组数异常: ws=%d rt=%d' % (len(ws), len(rt)))

        # 组0=狭义累计，组1=狭义单月，组2=广义累计，组3=广义单月
        cum_ws, ck, pk = build_maker_rank(ws, rt, 0, 0, '批发')
        cum_rt, _, _ = build_maker_rank(ws, rt, 0, 1, '零售')
        mon_ws, ckm, pkm = build_maker_rank(ws, rt, 1, 0, '批发')
        mon_rt, _, _ = build_maker_rank(ws, rt, 1, 1, '零售')

        year, latest, _, cum_label, mon_label = parse_period_label(
            [ck, pk], ws[0]['dataList'][0])
        _, latest2, _, _, mon_label2 = parse_period_label(
            [ckm, pkm], ws[1]['dataList'][0])
        if mon_label2 and latest2:
            mon_label = mon_label2
            latest = latest2

        result['period'] = {
            'year': year,
            'latestMonth': latest,
            'cumulativeLabel': cum_label,
            'monthlyLabel': mon_label,
        }
        result['maker'] = {
            'cumulative': {'label': ck, 'wholesale': cum_ws, 'retail': cum_rt},
            'monthly': {'label': ckm, 'wholesale': mon_ws, 'retail': mon_rt},
        }
    except Exception as e:                          # noqa: BLE001
        errors.append('厂商榜: %s' % e)

    # ---------- 整体市场（charttype=1）----------
    try:
        d1 = fetch_json(API, {'type': 1, 'charttype': 1})
        result['overall'] = build_overall(d1)
    except Exception as e:                          # noqa: BLE001
        errors.append('整体市场: %s' % e)

    # ---------- 新能源（charttype=6）----------
    try:
        d6 = fetch_json(API, {'type': 1, 'charttype': 6})
        result['nev'] = build_nev(d6)
    except Exception as e:                          # noqa: BLE001
        errors.append('新能源: %s' % e)

    # ---------- 分国别（charttype=4）----------
    try:
        d4 = fetch_json(API, {'type': 1, 'charttype': 4})
        result['segment'] = build_segment(d4)
    except Exception as e:                          # noqa: BLE001
        errors.append('分国别: %s' % e)

    if errors:
        # 数据正确性红线：任何一块失败，都不写文件，保留上一版数据
        sys.stderr.write('[fetch_ev_sales] 抓取失败，未写入任何文件：\n')
        for e in errors:
            sys.stderr.write('  - %s\n' % e)
        return 1

    result['errors'] = []

    # 新能源厂商榜：人工核对快照（不随接口自动变化，见文件顶部说明）
    result['nevMaker'] = dict(NEV_MAKER_SNAPSHOT)

    # 自动交叉校验：把快照里能与接口对上的数字核一遍，对不上就报警但不写死
    # 名称别名：接口用「特斯拉中国」，媒体报道用「特斯拉汽车」，需对齐否则会漏校验
    NAME_ALIAS = {'特斯拉汽车': ['特斯拉中国', '特斯拉汽车']}
    warns = []
    try:
        ws_month = {r['name']: r for r in result['maker']['monthly']['wholesale']}
        for row in NEV_MAKER_SNAPSHOT['wholesale']['rows']:
            ref = None
            for alias in NAME_ALIAS.get(row['name'], [row['name']]):
                if alias in ws_month:
                    ref = ws_month[alias]
                    break
            if not ref or ref.get('value') is None:
                continue
            # 纯新能源车企：批发口径下两榜应相等，容差 0.5%
            if row['name'] in ('比亚迪汽车', '零跑汽车', '特斯拉汽车'):
                api_units = round(ref['value'] * 10000)
                delta = abs(api_units - row['units']) / max(row['units'], 1)
                if delta > 0.005:
                    warns.append('交叉校验不符 %s：接口 %d 辆 vs 快照 %d 辆（差 %.2f%%）'
                                 % (row['name'], api_units, row['units'], delta * 100))
                else:
                    warns.append('交叉校验通过 %s：接口 %d 辆 ≈ 快照 %d 辆'
                                 % (row['name'], api_units, row['units']))
    except Exception as e:                          # noqa: BLE001
        warns.append('交叉校验跳过：%s' % e)
    result['crossCheck'] = warns

    if dry:
        print(json.dumps(result, ensure_ascii=False, indent=2)[:4000])
        print('\n[dry-run] 未写入文件')
        return 0

    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, OUT)
    sys.stderr.write('[fetch_ev_sales] 已写入 %s\n' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
