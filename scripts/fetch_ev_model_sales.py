#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取懂车帝车型销量榜，生成 static/ev-model-sales.json —— 车型级新能源销量榜的数据源。

与 static/ev-sales.json 的区别（两个文件互相独立，不要混用）：
    ev-sales.json       厂商级（乘联会接口 + 人工核对快照），单位万辆
    ev-model-sales.json 车型级（懂车帝接口，全自动），单位辆

数据源：懂车帝销量榜（字节跳动旗下汽车信息与服务平台）
    接口：https://www.dongchedi.com/motor/pc/car/rank_data
    参数：month=<YYYYMM | 500近半年 | 1000近一年>&rank_data_type=<11零售 | 2批发>&offset=<0,10,20…>
    请求头：必须带 Accept: application/json + Referer: https://www.dongchedi.com/ + 桌面 UA

为什么用它：乘联分会官方接口（data.cpcadata.com）经全量穷举（2 端点 × charttype 1-6 ×
type 1/2/3 共 36 组合）确认**不存在车型维度**，官方也不以车型级形式发布销量榜。
懂车帝是目前唯一能稳定、结构化、零鉴权拿到中国车型级月度销量的公开源。

===============================================================================
口径与来源分级（红线：绝不把不同来源、不同口径的数字混用或相互推算）
===============================================================================
    零售 rank_data_type=11  sourceTier = "platform"
        该平台未公开其上游数据来源，本站按平台自身口径如实引用。
    批发 rank_data_type=2   sourceTier = "traceable"
        与转载乘联会终稿的盖世汽车月度车型榜逐位一致，可视为乘联会批发口径。

    ⚠️ 可溯源 ≠ 官方发布。本站不宣称本榜等同于乘联分会官方发布物。

    批发 = 厂商开给经销商及出口的出货量，含出口，不等于终端实际交付
    零售 = 终端销量（上牌/上险），反映真实需求
    BEV = 纯电；PHEV = 插电混动；EREV = 增程；HEV（普通混动）不算新能源

===============================================================================
两个必须知道的坑（已在本脚本内处理）
===============================================================================
1. month 参数会「静默回退」
   传一个未发布的月份（如 202608），接口不报错，直接返回上一个已发布月份的数据。
   解法：响应里的 data.sells_rank_month 是权威可选月份清单，
        先探测一次取其中最大的 6 位数作为真实期次，再以该月份正式抓取。
        绝不用当前日期自行拼接月份。

2. 接口返回的是「全车型榜」，含燃油车，且没有新能源筛选参数
   （试过 energy / energy_type / fuel_type / is_nev / nev / series_type，全部被忽略）
   解法：用接口自带的 brand_name 字段 + 车型名后缀做四层归类（见 NEV_* 常量）。
        凡归类为 UNK（无法判定）→ 拒绝写入，保留上一版，等人肉补名单。
        绝不猜判、绝不自动放行。

===============================================================================
数据正确性红线（与 scripts/fetch_ev_sales.py 保持一致）
===============================================================================
    * 抓取或解析失败 → 不写文件，保留上一版，stderr 报错，退出码 1
    * 出现 UNK 车型   → 同上，绝不把「说不清动力类型」的车型混进新能源榜
    * 绝不写占位数字、绝不用旧数据冒充当期、绝不合并或拆分车系

用法：
    python3 scripts/fetch_ev_model_sales.py            # 抓取并写入 static/ev-model-sales.json
    python3 scripts/fetch_ev_model_sales.py --dry-run  # 只打印结果，不写文件
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'static', 'ev-model-sales.json')

API = 'https://www.dongchedi.com/motor/pc/car/rank_data'
HOME = 'https://www.dongchedi.com/sales/rank'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# 榜单口径：11 = 零售（终端销量）；2 = 批发（厂商出货，含出口）
CALIBERS = [
    ('retail', 11, '零售', '终端销量（上牌/上险），反映真实需求'),
    ('wholesale', 2, '批发', '厂商开给经销商及出口的出货量，含出口，不等于终端实际交付'),
]

TOP_N = 50          # 新能源内部取前 50 名出榜
PAGE_SIZE = 10      # 接口每页固定 10 条
FETCH_DEPTH = 300   # 固定抓取深度（约 30 页 × 2 口径 = 60 次请求，实测无限流）
#
# 为什么固定抓 300 条而不是「够 50 辆新能源就停」：
#   brandTotals（按品牌加总）要拿去和乘联分会官方厂商数字做锚点核对，
#   加总必须覆盖该品牌的全部在售车型，抓浅了就会算出偏小的数，
#   核对结果反而是假的 —— 那比不核对更糟。
#   代价是 60 次请求（约 1 分钟），对每周一次的自动化完全可接受。
MAX_OFFSET = FETCH_DEPTH - PAGE_SIZE   # offset 起点从 0 算，最后一页是 290
TIMEOUT = 25
RETRY = 3
SLEEP = 0.3         # 礼貌间隔，实测无限流但别打太猛

# =============================================================================
# 新能源归类映射表
#
# 这是【本站整理】的分类，不是数据源官方口径，页面必须如实标注。
# 判定顺序：MIXED -> 品牌白名单 -> 车型白名单 -> 名称后缀 -> 燃油名单 -> UNK
#
# 覆盖度实测（2026年7月，全车型 TOP100）：UNK 为 0。
# TOP101-300 仍有部分 UNK，故本脚本采取「遇到 UNK 就拒绝写入」的保守策略。
#
# 维护方式：只在混合品牌（MG / 丰田 / 别克 / 哈弗 / 奇瑞 / 五菱…）推出新新能源车型
#           时才需要补 nev_models。纯新能源品牌下的新车型自动命中，零维护。
#           每次新增条目都应留下可核查的依据，不要凭印象添加。
# =============================================================================

# 规则1 —— 纯新能源品牌白名单
# 依据：这些品牌在中国市场在售车型全系为纯电 / 插混 / 增程，本身不产销燃油车。
# 品牌名必须与接口返回的 brand_name 字段逐字一致。
NEV_BRANDS = {
    # 造车新势力 / 纯电新品牌
    '特斯拉', '零跑汽车', '小米汽车', '理想汽车', '蔚来', '小鹏汽车',
    'firefly萤火虫', '乐道', '智己汽车', 'iCAR', '阿维塔',
    # 华为鸿蒙智行系列
    'AITO问界', '智界', '尚界', '享界',
    # 传统车企旗下的独立新能源品牌
    '比亚迪',            # 2022年3月起停产燃油车
    '长安启源', '深蓝汽车', '阿维塔',
    '吉利银河', '极氪', '极狐', 'ARCFOX极狐', '欧拉', '魏牌', '岚图',
    '埃安', '方程豹', '奇瑞QQ', '奇瑞风云', '东风奕派',
    '华境',              # 上汽通用五菱 × 华为乾崑，插混
    'Polestar极星', 'smart', 'ROX极石', '瑞驰', '蓝电',
}

# 规则2 —— 混合品牌（同时产销燃油与新能源）旗下的新能源车型
#
# ⚠️ 这条名单是【人工逐款核实】的，每条都必须留下可核查的依据。
#    没有依据的一律不写进来 —— 它会在出榜名次之前变成 UNK 让脚本拒绝写入，
#    由人肉查证后再补。宁可榜单不更新，也不凭印象判定动力类型。
NEV_MODELS = {
    'MG4',             # 盖世汽车 2026年7月新能源轿车榜写作「MG4 EV」，批发 19,176
    '铂智3X',          # 广汽丰田铂智3X，纯电（盖世榜列为新能源车型）
    '五菱宏光MINIEV',  # 车名自带 EV，微型纯电
    '缤果Pro',         # 盖世 2026年7月新能源轿车榜作「五菱缤果Pro」，批发 19,396
    '星光730',         # 盖世 2026年7月新能源 MPV 榜作「星光730 EV」，批发 3,323
}
#
# 以下车型未收录（无可靠依据，退回 UNK 由人工确认后再补）：
#   别克至境E7、缤果S、星光L、星光560、悦也Plus、荣威D6、奥迪E7X、
#   与众06、奔腾小马、悦意03、悦意08
#   它们目前都排在出榜名次之后，不影响 TOP50，只影响 brandTotals 与 UNK 计数。

# 规则3 —— 车型名自带动力后缀（顺带可推出动力类型）
NEV_SUFFIX = re.compile(
    r'(PHEV|REEV|EREV|BEV|EV|C-DM|DM|EM-i|EREV|Hi4-T|Hi4-Z|增程|纯电)',
    re.I)

# 规则4 —— 明确燃油（用于拦截，防止混合品牌下的燃油车被后缀误伤后漏判）
ICE_MODELS = {
    '卡罗拉锐放', 'RAV4荣放', '博越L', '朗逸', '星越L', '凯美瑞', '速腾', '探岳', '途观L',
    '宝马3系', '迈腾', '锋兰达', '帕萨特', '缤越', '奔驰E级', '威兰达', '瑞虎8', '亚洲龙',
    '本田CR-V', '轩逸', '长安CS75 PLUS', '星瑞', '帝豪', '奥迪A6L', '宝马X3', '赛那', '雅阁',
    '奔驰GLC', '逸动', '宝马5系', '奥迪Q5L', '哈弗大狗', '昂科威', '艾瑞泽8', '卡罗拉',
    '途岳', '奥迪A3', '瑞虎7', '瑞虎5x', '捷途旅行者', '长安X5 PLUS', '欧萌达', '捷途X70',
    '哈弗H6', '焕驰', 'MG5', '捷途自由者', '领睿', '红旗H5', '睿蓝X3 PRO',
    '汉兰达', '皓影', '奔驰C级', '传祺M8', '瑞虎9', '伊兰特', '宝马X5', '宝马X1', '马自达CX-5',
    '君越', '五菱宏光V', '五菱宏光', '五菱荣光', '五菱星驰', '宝来', '逍客', '捷达VS5', '捷达VA3',
    '捷达VS8', '红旗HS5', '凯迪拉克XT5', '皇冠陆放', '奥迪A5L', '别克GL8', '格瑞维亚', '天籁',
    '赛图斯', '奥迪Q3', '传祺GS3', '揽巡', '奇骏', '英仕派', '蒙迪欧', '起亚K3', '锐界',
    '本田HR-V', '传祺M6', '君威', '北京越野BJ30', '北京越野BJ40', '探歌', '途胜', '长安UNI-V',
    '思域', '凌渡', '普拉多', '传祺GS8', '高尔夫', '艾瑞泽5', '索纳塔', '现代ix35', '狮铂拓界',
    '传祺GS4', '荣威RX9', '荣威i6', '荣威RX5', '哈弗H9', '航海家', '江淮X8 PLUS', '江淮A5 PLUS',
    '瑞虎3x', '领地', '212 T01', '坦克500', '星途凌云', '影豹', '豪越L', '长安CS55 PLUS',
    '哈弗猛龙燃油版', '坦克300', '起亚K3',
}

# 规则0 —— 车系合并统计，同时含燃油与新能源版本且接口不拆分，占比不可考
# → 明确排除出新能源榜。宁可少列，也不靠猜。
MIXED_MODELS = {
    '北京越野BJ30',   # 同时有 1.5T 燃油版与魔核电驱版
}

# 动力类型推断（顺序敏感：EREV 先于 PHEV 先于 BEV，因为 REEV/PHEV 里都含 "EV"）
ENERGY_RULES = [
    ('EREV', re.compile(r'(REEV|EREV|增程)', re.I)),
    ('PHEV', re.compile(r'(PHEV|C-DM|DM|EM-i|Hi4-T|Hi4-Z)', re.I)),
    ('BEV', re.compile(r'(BEV|EV|纯电)', re.I)),
]

# =============================================================================
# 人工核对锚点（用于 crossCheck，不是自动抓取的）
#
# 方法：找「在售车型全部进入懂车帝榜单」的纯新能源品牌，把它的车型销量加总，
#       与乘联分会官方发布的【厂商级】数字逐位比对。这比「榜首数字对得上」强得多。
#
# 2026-09-03 核对结果：
#   特斯拉 零售 25,158 + 2,091 = 27,249  == 官方 27,249  ✓
#   特斯拉 批发 59,836 + 33,743 = 93,579 == 官方 93,579  ✓
#   零跑   零售 10 款加总 = 83,698       == 官方 83,698  ✓
#   零跑   批发 96,408 + 4,859 = 101,267 == 官方 101,267 ✓
#       其中 4,859 = 零跑B10 REEV，排在懂车帝批发榜第 300 名之后，
#       不在本脚本抓取深度内，故 autoSum 会显示 96,408，expectedDelta 记下这个缺口。
#
# ⚠️ 期次一旦变化，这些锚点即失效，crossCheck.status 会变成 stale 并提示重核。
# =============================================================================
ANCHORS = [
    {'brand': '特斯拉', 'caliber': 'retail', 'official': 27249,
     'complete': True, 'note': 'Model Y 25,158 + Model 3 2,091，2 款全部在榜'},
    {'brand': '特斯拉', 'caliber': 'wholesale', 'official': 93579,
     'complete': True, 'note': 'Model Y 59,836 + Model 3 33,743，2 款全部在榜'},
    {'brand': '零跑汽车', 'caliber': 'retail', 'official': 83698,
     'complete': True, 'note': '10 款全部在榜'},
    {'brand': '零跑汽车', 'caliber': 'wholesale', 'official': 101267,
     'complete': False, 'expectedDelta': 4859,
     'note': '第 300 名后的「零跑B10 REEV」4,859 辆不在抓取深度内，故本站加总为 96,408'},
]
ANCHOR_PERIOD = '2026年7月'
ANCHOR_VERIFIED_ON = '2026-09-03'


def fetch_page(month, rank_type, offset):
    """抓取单页。失败抛异常，绝不返回半成品。"""
    url = '%s?month=%s&rank_data_type=%s&offset=%d' % (API, month, rank_type, offset)
    last = None
    for attempt in range(1, RETRY + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': UA,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://www.dongchedi.com/',
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read().decode('utf-8', errors='replace')
            d = json.loads(raw)
            if d.get('status') != 0:
                raise RuntimeError('接口返回 status=%s message=%s'
                                   % (d.get('status'), d.get('message')))
            return d
        except Exception as e:                          # noqa: BLE001
            last = e
            if attempt < RETRY:
                time.sleep(1.5 * attempt)
    raise RuntimeError('抓取失败 %s -> %s' % (url, last))


def guess_request_month(now):
    """猜一个请求月份（上月）。只是探测用的起点，真实期次以接口返回为准。"""
    y, m = now.year, now.month - 1
    if m == 0:
        y, m = y - 1, 12
    return y * 100 + m


def parse_months(d):
    """从 data.sells_rank_month 里取出所有合法月份（6 位 YYYYMM）。"""
    out = []
    for it in (d.get('data') or {}).get('sells_rank_month') or []:
        m = it.get('month')
        if isinstance(m, int) and 100000 <= m <= 999999:
            out.append(m)
    return sorted(set(out))


def detect_month(rank_type, requested):
    """
    探测真实最新期次。

    接口的 month 参数会静默回退：传一个未发布的月份，它不报错，
    直接返回上一个已发布月份的数据。因此绝不能信自己拼的月份，
    必须读接口给的 sells_rank_month 清单。
    """
    d = fetch_page(requested, rank_type, 0)
    months = parse_months(d)
    if not months:
        raise RuntimeError('接口未返回任何可选月份（sells_rank_month 为空）')
    real = months[-1]           # 降序清单里的最大月份即最新期次
    return real, (real == requested), months


def classify(name, brand):
    """四层归类。返回 (类别, 命中规则)。类别 ∈ NEV / ICE / MIXED / UNK。"""
    if name in MIXED_MODELS:
        return 'MIXED', 'mixed-excluded'
    if brand in NEV_BRANDS:
        return 'NEV', 'brand'
    if name in NEV_MODELS:
        return 'NEV', 'model'
    if NEV_SUFFIX.search(name):
        return 'NEV', 'suffix'
    if name in ICE_MODELS:
        return 'ICE', 'ice-list'
    return 'UNK', 'unknown'


def guess_energy(name):
    """从车型名后缀推动力类型。推不出来返回 None，绝不猜。"""
    for label, pat in ENERGY_RULES:
        if pat.search(name):
            return label
    return None


def collect(month, rank_type):
    """
    按 offset 翻页抓取到 FETCH_DEPTH 深度为止。
    返回 (all_rows, nev_rows, unk_rows, pages)

    不提前停：brandTotals 需要覆盖品牌的全部在售车型才能做锚点核对（见 FETCH_DEPTH 注释）。
    """
    all_rows, nev_rows, unk_rows = [], [], []
    seen = set()
    pages = 0
    offset = 0
    while offset <= MAX_OFFSET:
        d = fetch_page(month, rank_type, offset)
        pages += 1
        lst = (d.get('data') or {}).get('list') or []
        if not lst:
            break
        for it in lst:
            sid = it.get('series_id')
            if sid in seen:                 # 跨页可能重复返回，按 series_id 去重
                continue
            seen.add(sid)
            name = it.get('series_name') or ''
            brand = it.get('brand_name') or ''
            row = {
                'globalRank': it.get('rank'),
                'name': name,
                'brand': brand,
                'seriesId': sid,
                'units': it.get('count'),
                'lastRank': it.get('last_rank'),
                'priceRange': it.get('price'),
                'energy': guess_energy(name),
            }
            all_rows.append(row)
            cls, rule = classify(name, brand)
            row['_cls'], row['_rule'] = cls, rule
            if cls == 'NEV':
                nev_rows.append(row)
            elif cls == 'UNK':
                unk_rows.append(row)
        if not (d.get('data') or {}).get('paging', {}).get('has_more'):
            break
        offset += PAGE_SIZE
        time.sleep(SLEEP)
    return all_rows, nev_rows, unk_rows, pages


# ---------------------------------------------------------------------------
# 对外措辞（由 team-lead 给定原文，逐字使用，不得自行改写）
#
# 2026-09-03 订正：批发口径原写「与转载乘联会终稿的盖世汽车车型榜逐位一致」，
# 该说法已被证伪并收回 —— 用乘联会官方《2026年7月全国乘用车市场分析》里
# 官方唯一以车型粒度发布的内容（批发超两万辆车型 18 款）逐条验证，
# 结果只有 12/18 闭合。厂商粒度成立的逐位一致不能搬到车型粒度，
# 证据强度不可跨粒度搬运。
# ---------------------------------------------------------------------------
SOURCE_NOTE = (
    '本站车型销量数字取自懂车帝销量榜（商业平台，非行业统计机构）。'
    '该平台未公开其上游数据来源。零售口径按其自身口径如实引用；'
    '批发口径经抽样比对，与乘联会官方《全国乘用车市场分析》发布的车型级数字 '
    '18 款中 12 款闭合。'
    '两个口径下的车型级数字均不等同于乘联会官方发布物，'
    '不与官方数据混用或相互推算，引用请以官方原文为准。'
)

DISCLAIMERS = {
    'retail': (
        '零售口径：懂车帝未公开其上游数据来源，本站按其自身口径如实引用。'
        '厂商级数字已与乘联会官方零售数据交叉验证'
        '（特斯拉、零跑等纯新能源品牌的在售车型加总与官方厂商级数字逐位一致），'
        '但车型级数字未经官方逐条确认。'
        '本榜不等同于乘联会官方发布物，仅供横向比较参考。'
    ),
    'wholesale': (
        '批发口径：厂商级加总与乘联会官方批发数字逐位一致'
        '（特斯拉 93,579、零跑 101,267 等已逐位验证）。'
        '车型级以官方《2026年7月全国乘用车市场分析》中"批发超两万辆车型"'
        '18 款为样本抽样比对，12 款闭合（9 款逐位相等、3 款合并动力版本后相等），'
        '另 6 款存在差异，其中 4 款可归因于系列拆分与出口车型'
        '（JAECOO J5、MG ZS 为纯出口）、2 款（元UP、海豚）原因不明。'
        '因此本榜车型级数字仅供横向比较参考，不等同于乘联会官方发布物。'
    ),
}


# ---------------------------------------------------------------------------
# 车系归并：把被动力后缀拆开的同一车系并回来
#
# 懂车帝按动力版本拆行，例如批发榜里「钛7 PHEV」17,820 与「钛7 EV」9,500
# 是两个 series_id，但对外是同一个车系（合计 27,320）。
# 只看单行会让人低估该车系一大截，属于实质性误导，故补算车系合计。
#
# 注意：seriesGroupTotal 是本站对同源同期数字做的加总，不是数据源发布的数字，
#       也不是估算 —— 各成员行本身仍原样保留，不做合并、不做拆分。
# ---------------------------------------------------------------------------
# 按最长匹配，顺序不可调换（C-DM/EM-i/DM-i 必须排在 DM 之前，EREV/BEV 在 EV 之前）
GROUP_SUFFIX = ['PHEV', 'REEV', 'EREV', 'BEV', 'C-DM', 'EM-i', 'DM-i', 'DM',
                'EV', '增程', '纯电']


def series_base(name):
    """去掉尾部动力后缀，取车系基名。'钛7 PHEV' -> '钛7'，'海狮06EV' -> '海狮06'。"""
    s = (name or '').strip()
    up = s.upper()
    for suf in GROUP_SUFFIX:
        if up.endswith(suf.upper()):
            s = s[:len(s) - len(suf)]
            break
    return s.rstrip(' \t-')


def apply_series_groups(out_rows):
    """
    给每个多成员车系组的「组内名次最靠前的那一行」补 seriesGroup* 四字段。
    单行组不写。返回归并结果清单，供人工复核是否误并。
    """
    groups = {}
    for idx, r in enumerate(out_rows):
        groups.setdefault(series_base(r['name']), []).append(idx)

    report = []
    for base, idxs in groups.items():
        members = [out_rows[i] for i in idxs]
        if len(members) < 2:
            continue
        total = sum(m['units'] or 0 for m in members)
        head = out_rows[idxs[0]]          # idxs 升序，首元素即组内名次最靠前
        head['seriesGroup'] = base
        head['seriesGroupTotal'] = total
        head['seriesGroupMembers'] = len(members)
        head['seriesGroupParts'] = [
            {'name': m['name'], 'units': m['units'], 'rank': m['rank']}
            for m in sorted(members, key=lambda x: -(x['units'] or 0))
        ]
        report.append((base, len(members), total, [m['name'] for m in members]))
    return sorted(report, key=lambda x: -x[2])


def build_caliber(key, rank_type, label, caliber_text, month, months_available,
                  rows, nev_rows, all_rows):
    """组装单个口径的输出块。"""
    tier = 'traceable' if key == 'wholesale' else 'platform'
    disclaimer = DISCLAIMERS[key]

    # 新能源内部连续编号；原全车型榜名次保留到 globalRank
    top = nev_rows[:TOP_N]
    out_rows = []
    for i, r in enumerate(top, 1):
        out_rows.append({
            'rank': i,                 # 新能源榜内部连续名次
            'globalRank': r['globalRank'],   # 全车型榜名次（副信息，会跳号）
            'name': r['name'],
            'brand': r['brand'],
            'seriesId': r['seriesId'],
            'units': r['units'],
            'lastRank': r['lastRank'],
            'priceRange': r['priceRange'],
            'energy': r['energy'],
            'matchRule': r['_rule'],
        })
    group_report = apply_series_groups(out_rows)
    for base, n, total, names in group_report:
        sys.stderr.write('[fetch_ev_model_sales] %s 归并：%s 合计 %d（%d 款：%s）\n'
                         % (label, base, total, n, ' + '.join(names)))

    # 品牌加总（仅统计本次抓取深度内的车型，用于人工核对，非官方口径）
    agg = {}
    for r in all_rows:
        if r['_cls'] != 'NEV':
            continue
        b = r['brand'] or '（未标注品牌）'
        agg[b] = agg.get(b, 0) + (r['units'] or 0)
    brand_totals = [{'brand': b, 'units': v}
                    for b, v in sorted(agg.items(), key=lambda x: -x[1])[:15]]

    return {
        'title': '中国新能源乘用车车型%s销量 TOP%d' % (label, len(out_rows)),
        'caliber': caliber_text,
        'sourceTier': tier,
        'disclaimer': disclaimer,
        'rankDataType': rank_type,
        'fetchedRows': len(rows),
        'nevRowsFound': len(nev_rows),
        'rows': out_rows,
        'brandTotals': brand_totals,
        'brandTotalsNote': (
            '按本榜新能源车型加总，仅含排在抓取深度内的车型；'
            '在售车型数量多、有车型跌出深度的品牌会偏小，不代表该品牌官方总量。'
        ),
    }


def build_crosscheck(period_label, calibers):
    """把人工核对锚点与本次抓取的加总比对。期次变了就标 stale。"""
    status = 'current' if period_label == ANCHOR_PERIOD else 'stale'
    items = []
    for a in ANCHORS:
        block = calibers.get(a['caliber']) or {}
        tot = None
        for bt in block.get('brandTotals') or []:
            if bt['brand'] == a['brand']:
                tot = bt['units']
                break
        item = {
            'brand': a['brand'],
            'caliber': a['caliber'],
            'official': a['official'],
            'autoSum': tot,
            'note': a['note'],
        }
        if tot is None:
            item['result'] = 'skipped'
        elif a['complete']:
            item['result'] = 'match' if tot == a['official'] else 'mismatch'
            item['diff'] = tot - a['official']
        else:
            expect = a['official'] - a.get('expectedDelta', 0)
            item['result'] = 'match' if tot == expect else 'mismatch'
            item['diff'] = tot - expect
            item['expectedDelta'] = a.get('expectedDelta')
        items.append(item)
    return {
        'status': status,
        'verifiedPeriod': ANCHOR_PERIOD,
        'verifiedOn': ANCHOR_VERIFIED_ON,
        'method': (
            '取「在售车型全部进入榜单」的纯新能源品牌，把其车型销量加总，'
            '与乘联分会官方发布的厂商级新能源数字逐位比对。'
        ),
        'officialSource': '中国汽车流通协会乘用车市场信息联席分会（乘联分会）官方发布的厂商新能源销量',
        'items': items,
        'staleHint': (
            None if status == 'current' else
            '当前期次（%s）与锚点核对期次（%s）不一致，上述比对结果已失效，'
            '请用新期次的乘联分会官方厂商数字重新核对后再更新 ANCHORS。'
            % (period_label, ANCHOR_PERIOD)
        ),
    }


def main():
    dry = '--dry-run' in sys.argv
    now = datetime.now(timezone(timedelta(hours=8)))
    errors = []

    # ---------- 期次探测：真实月份以接口为准，不信自己拼的月份 ----------
    requested = guess_request_month(now)
    try:
        real_month, matched, months_available = detect_month(11, requested)
    except Exception as e:                              # noqa: BLE001
        sys.stderr.write('[fetch_ev_model_sales] 期次探测失败，未写入任何文件：%s\n' % e)
        return 1

    year, mon = real_month // 100, real_month % 100
    period_label = '%d年%d月' % (year, mon)
    sys.stderr.write('[fetch_ev_model_sales] 请求期次 %s，接口最新期次 %s%s\n'
                     % (requested, real_month, '' if matched else '（已按期次回退）'))

    # ---------- 两个口径分别抓取 ----------
    calibers = {}
    unk_below_cutoff = {}
    for key, rank_type, label, caliber_text in CALIBERS:
        try:
            rows, nev_rows, unk_rows, pages = collect(real_month, rank_type)
            if not rows:
                raise RuntimeError('未抓到任何车型数据')
            if len(nev_rows) < TOP_N:
                raise RuntimeError(
                    '抓取深度内只找到 %d 款新能源车型，不足 TOP%d（已翻到第 %d 名）'
                    % (len(nev_rows), TOP_N, rows[-1]['globalRank']))

            # UNK 判定：只有「排在出榜名次之前」的 UNK 才会影响榜单正确性。
            # 设第 TOP_N 个新能源车型的全车型榜名次为 cutoff，
            # 那么名次 < cutoff 的每一款车都必须给出明确归类 ——
            # 它是新能源就该进榜、是燃油就不该进榜，说不清就会让 TOP50 站不住脚。
            # 名次 > cutoff 的 UNK 进不了前 50，判定与否都不改变出榜结果，
            # 只记个数、不阻断（否则每月都要为第 200 名的冷门车补名单，不现实）。
            cutoff = nev_rows[TOP_N - 1]['globalRank']
            critical = [r for r in unk_rows
                        if (r['globalRank'] or 0) < (cutoff or 0)]
            if critical:
                names = ['#%s %s（%s）' % (r['globalRank'], r['name'], r['brand'])
                         for r in critical[:10]]
                raise RuntimeError(
                    '有 %d 款车型排在出榜名次（第 %d 名）之前却无法判定是否新能源，拒绝写入。'
                    '请在脚本的 NEV_BRANDS / NEV_MODELS / ICE_MODELS 中补上再跑：%s'
                    % (len(critical), cutoff, '；'.join(names)))
            unk_below_cutoff[key] = len(unk_rows)

            calibers[key] = build_caliber(
                key, rank_type, label, caliber_text, real_month,
                months_available, rows, nev_rows, rows)
            sys.stderr.write(
                '[fetch_ev_model_sales] %s：抓 %d 款 / %d 页，筛出新能源 %d 款，'
                '出榜名次截至第 %d 名，榜外 UNK %d 款\n'
                % (label, len(rows), pages, len(nev_rows), cutoff, len(unk_rows)))
        except Exception as e:                          # noqa: BLE001
            errors.append('%s榜: %s' % (label, e))

    if errors or len(calibers) != len(CALIBERS):
        # 数据正确性红线：任何一块失败都不写文件，保留上一版
        sys.stderr.write('[fetch_ev_model_sales] 抓取失败，未写入任何文件：\n')
        for e in errors:
            sys.stderr.write('  - %s\n' % e)
        return 1

    result = {
        'updated': now.strftime('%Y-%m-%d'),
        'updatedAt': now.strftime('%Y-%m-%d %H:%M'),
        'autoFetched': True,
        'source': {
            'name': '懂车帝销量榜',
            'platform': '懂车帝（字节跳动旗下汽车信息与服务平台）',
            'home': HOME,
            'api': API,
            'licence': '数据版权归懂车帝所有，本站仅作引用并注明出处',
        },
        'units': '辆',
        'caliber': {
            '批发': '厂商开给经销商及出口的出货量，含出口，不等于终端实际交付量',
            '零售': '终端销量（上牌/上险），反映真实需求',
            '新能源': 'BEV（纯电）+ PHEV（插电混动）+ EREV（增程），不含普通混动（HEV）',
            'sourceNote': SOURCE_NOTE,
        },
        'period': {
            'year': year,
            'month': mon,
            'label': period_label,
            'requestedMonth': requested,
            'periodMatched': matched,
            'availableMonths': months_available,
            'note': (
                '期次取自接口返回的 sells_rank_month 清单，非本地日期推算。'
                '若 periodMatched 为 false，说明请求月份尚未发布，接口已静默回退，'
                '本文件记录的是它实际返回的期次。'
            ),
        },
        'classify': {
            'note': (
                '接口返回的是全车型榜（含燃油车）且无新能源筛选参数，'
                '故新能源归类由本站按下列规则整理，不是数据源官方口径。'
            ),
            'order': ['MIXED 排除', '品牌白名单', '车型白名单', '名称后缀', '燃油名单', 'UNK 拒绝写入'],
            'nevBrands': sorted(NEV_BRANDS),
            'nevModels': sorted(NEV_MODELS),
            'nevSuffix': NEV_SUFFIX.pattern,
            'mixedModels': sorted(MIXED_MODELS),
            'iceModels': sorted(ICE_MODELS),
            'maintenance': (
                '纯新能源品牌下的新车型自动命中，零维护；'
                '只有混合品牌（MG/丰田/别克/哈弗/奇瑞/五菱等）推出新新能源车型时才需补 nevModels。'
                '排在出榜名次之前的车型若落入 UNK，脚本会拒绝写入并保留上一版，不会自动猜判。'
            ),
            'unkBelowCutoff': unk_below_cutoff,
            'unkBelowCutoffNote': (
                '名次在出榜名次之后的 UNK 数量（多为冷门燃油车或本站尚未收录的新能源车）。'
                '它们进不了 TOP%d，故不阻断抓取；等榜单变长或排名变化时再补名单。' % TOP_N
            ),
        },
        'retail': calibers['retail'],
        'wholesale': calibers['wholesale'],
        'crossCheck': build_crosscheck(period_label, calibers),
        'notes': [
            '榜单每行按懂车帝的「车系（series_id）」粒度原样呈现，各行数字不做合并、不做拆分、不做推算。'
            '其他平台按动力版本拆分统计时，同一车系的数字可能对不上，这是统计粒度不同，不是错误。',
            '本站已用乘联会官方发布的车型级数字做过抽样比对：18 款中 12 款闭合，'
            '6 款对不上（其中 2 款原因不明）。'
            '因此本榜车型数字只能用于横向比较，不能当作乘联会官方数字引用。',
            '动力类型字段仅有 26% 覆盖率'
            '（该平台接口未提供动力类型字段，仅能从车名后缀识别，车名不含动力标识的一律留空），'
            '故本榜不提供纯电/插混/增程分类。',
            '同一车系若被按动力版本拆成多行（如钛7 拆为 PHEV 与 EV），'
            '本站会在该组名次最靠前的一行额外给出 seriesGroupTotal，'
            '即同源同期各成员行数字之和，用于避免只看单行低估该车系。'
            '这是本站对同源数字的加总，不是数据源发布的数字；'
            '成员行本身仍各自原样保留，不合并、不拆分。',
            '元UP：懂车帝记为一条（2026年7月零售 20,275 / 批发 37,658）；'
            '盖世汽车批发榜拆为「比亚迪元UP 37,658」+「元UP DM-i 25,600」。'
            '两边粒度不同，本站不合并、不拆分，原样呈现懂车帝口径。',
            '宋PLUS DM：盖世汽车批发榜有此车（16,242），懂车帝榜单内无对应条目，'
            '属「别家有、本站数据源没有」，不硬凑、不从别处补数。',
            '海豚：懂车帝为车系合并口径（零售 13,910 / 批发 34,910）；'
            '盖世汽车拆为「海豚 22,910」+「海豚G PHEV 12,000」（批发）。本站取懂车帝原口径。',
            '长安Lumin 在批发口径下未进入抓取深度（全车型 300 名之后），故只出现在零售榜。',
            '站长提到的「秦PLUS DM-i」在懂车帝里叫「秦PLUS DM」，检索时请用榜单上的名字。',
            'energy 字段由车型名后缀推断（PHEV/REEV/BEV/EV/DM/C-DM/EM-i/EREV/增程/纯电）；'
            '车名不含动力标识的一律为 null，不做推断。',
        ],
        'errors': [],
    }

    if dry:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print('\n[dry-run] 未写入文件', file=sys.stderr)
        return 0

    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, OUT)
    sys.stderr.write('[fetch_ev_model_sales] 已写入 %s（期次 %s）\n' % (OUT, period_label))
    return 0


if __name__ == '__main__':
    sys.exit(main())
