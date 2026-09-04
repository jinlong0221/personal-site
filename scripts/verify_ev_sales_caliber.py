#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乘联会（CPCA）数据接口 —— 口径校验闸
==================================

为什么需要这道闸
----------------
接口 charttype=3/4/5/6 的四列数组，曾经被误读成
「[当年销量, 去年同期, 当年份额%, 去年份额%]」。正确口径是：

    [0] 批发销量（万辆）  [1] 零售销量（万辆）
    [2] 批发占比 %        [3] 零售占比 %

这个错之所以危险：四种读法下接口都照样返回四个数字，量级也都"像那么回事"，
页面不会报错，[2]/[3] 会被当成份额直接画进图表 —— 是那种看不出错的错。
所以不能靠"看起来对"来守，得用数据内部的自洽关系把口径钉死。

三项检查
--------
  1. 份额加总闸：每月 [2] 加总、[3] 加总都应 ≈ 100
     各阵营份额四舍五入到 1 位小数，累加必然有 ±0.5 以内的误差，故取 [99.5, 100.5]。
  2. 份额复算闸：每行 [2] ≈ [0]/该月批发总量×100，[3] ≈ [1]/该月零售总量×100，
     误差 < 0.15 个百分点。
     —— 这条是决定性的：[2] 若是"去年同期销量"，绝无可能等于 [0]/总量×100。
  3. 同一套检查原样施加于 charttype=3 的「占比」组。

检查范围是接口返回的【全部】月份，不只最新月：历史月若错位同样报警，
因为页面上的趋势图会一起画出来。

退出码
------
  0  全部通过
  1  校验不通过（口径自洽性被打破）→ 应拒绝写入，保留上一版数据
  2  抓取失败，或接口结构变化（份额组/字段找不到）→ 闸本身失效，需人工介入

用法
----
  python3 scripts/verify_ev_sales_caliber.py
  python3 scripts/verify_ev_sales_caliber.py --inject share
  python3 scripts/verify_ev_sales_caliber.py --inject volume

为什么自带 --inject
-------------------
一道永远通过的闸等于没有闸。--inject 在【内存里】把一个值改错，
用真实响应证明闸确实拦得住。不落盘、不动任何业务文件、可随时复现。
    volume = 篡改某阵营的 [0] 批发量 → 只触发复算闸
    share  = 篡改某阵营的 [2] 占比  → 加总闸与复算闸同时触发

本脚本只做校验，不抓取、不写业务数据，与 fetch_ev_sales.py 完全解耦。
仅用标准库。
"""
import json
import sys
import time
import urllib.request

API = 'http://data.cpcadata.com/api/chartlist'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

TIMEOUT = 30
RETRY = 3

# 份额加总的允许区间。接口把占比四舍五入到 1 位小数，
# N 个阵营累加的误差上界约为 N/2 × 0.1 = 0.35（N=7），故 ±0.5 足够宽松也不会漏。
SUM_LO, SUM_HI = 99.5, 100.5
# 单行份额与复算值之间的允许偏差（百分点）。
# 误差来源只有接口那 1 位小数的四舍五入（≤0.05），0.15 已留出三倍冗余。
SHARE_TOL = 0.15

# 份额表的期次键名。charttype=3 的非占比组用的是 'month' + 年份键，
# 占比组和 charttype=4 用 '月份' + 阵营/车身形式键，据此区分。
PERIOD_KEY = '月份'


def fetch(charttype):
    """抓取 charttype=N 的完整响应。失败抛异常，绝不返回半成品。"""
    full = '%s?type=1&charttype=%d' % (API, charttype)
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


def share_groups(data, charttype):
    """
    挑出「份额表」形态的组：行以 `月份` 为键，其余键是四元素数组。
    charttype=3 的占比组、charttype=4 的分国别组都是这个形态。
    """
    out = []
    for gi, group in enumerate(data):
        rows = group.get('dataList') or []
        if rows and PERIOD_KEY in rows[0]:
            out.append((gi, rows))
    return out


def check_group(where, rows, errors, stats):
    """对一组份额表施加检查 1 与检查 2，错误追加进 errors。"""
    for row in rows:
        period = row.get(PERIOD_KEY)
        series, bad = [], []
        for k, v in row.items():
            if k == PERIOD_KEY:
                continue
            if isinstance(v, (list, tuple)):
                if len(v) != 4:
                    bad.append('%s=%r(长度%d)' % (k, v, len(v)))
                else:
                    try:
                        series.append((k, [float(x) for x in v]))
                    except (TypeError, ValueError):
                        bad.append('%s=%r(非数值)' % (k, v))
        if bad:
            errors.append('%s %s：字段结构异常，应为 4 元素数值数组 -> %s'
                          % (where, period, '; '.join(bad)))
            continue
        if len(series) < 2:
            errors.append('%s %s：只有 %d 个系列，加总校验无意义'
                          % (where, period, len(series)))
            continue

        tot_ws = sum(v[0] for _, v in series)
        tot_rt = sum(v[1] for _, v in series)
        sum_ws_share = sum(v[2] for _, v in series)
        sum_rt_share = sum(v[3] for _, v in series)

        stats['rows'] += 1
        stats['pairs'] += len(series) * 2

        # ---------- 检查 1：份额加总 ----------
        for idx, total, name in ((2, sum_ws_share, '批发占比'),
                                 (3, sum_rt_share, '零售占比')):
            stats['sums'] += 1
            if not (SUM_LO <= total <= SUM_HI):
                errors.append(
                    '%s %s：[%d]%s 加总 = %.4f，超出允许区间 [%g, %g]｜明细 %s'
                    % (where, period, idx, name, total, SUM_LO, SUM_HI,
                       ' '.join('%s=%.1f' % (k, v[idx]) for k, v in series)))

        # ---------- 检查 2：份额复算 ----------
        if tot_ws <= 0 or tot_rt <= 0:
            errors.append('%s %s：总量非正（批发 %.4f / 零售 %.4f），无法复算份额'
                          % (where, period, tot_ws, tot_rt))
            continue
        for k, v in series:
            for idx, total, name, src in ((2, tot_ws, '批发', v[0]),
                                          (3, tot_rt, '零售', v[1])):
                expected = src / total * 100.0
                diff = abs(v[idx] - expected)
                if diff > stats['maxErr']:
                    stats['maxErr'] = diff
                    stats['maxWhere'] = '%s %s %s %s占比' % (where, period, k, name)
                if diff > SHARE_TOL:
                    errors.append(
                        '%s %s「%s」%s占比：接口值 %.4f，按 [0]/总量 复算 %.4f，'
                        '差 %.4f pp（阈值 %.2f）｜总量 批发 %.4f 零售 %.4f'
                        % (where, period, k, name, v[idx], expected, diff,
                           SHARE_TOL, tot_ws, tot_rt))


def inject_error(groups, mode):
    """在【内存里】改错一个值，用于对照实验。返回改动说明。"""
    where, rows = groups[0]
    row = rows[-1]                                  # 最新一个月
    period = row.get(PERIOD_KEY)
    key = max((k for k, v in row.items()
               if k != PERIOD_KEY and isinstance(v, list) and len(v) == 4),
              key=lambda k: row[k][0])
    row[key] = list(row[key])
    if mode == 'volume':
        old = row[key][0]
        row[key][0] = round(old * 1.5, 4)
        return ('%s %s「%s」[0] 批发量 %.4f -> %.4f（篡改量值）'
                % (where, period, key, old, row[key][0]))
    old = row[key][2]
    row[key][2] = 50.0
    return ('%s %s「%s」[2] 批发占比 %.4f -> 50.0（篡改份额）'
            % (where, period, key, old))


def main():
    modes = []
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ('-h', '--help'):
            sys.stdout.write(__doc__)
            return 0
        if arg == '--inject':                        # --inject share（空格式）
            if i + 1 < len(argv):
                i += 1
                modes = [x.strip() for x in argv[i].split(',') if x.strip()]
            else:
                modes = ['share']
        elif arg.startswith('--inject='):            # --inject=share（等号式）
            modes = [x.strip() for x in arg.split('=', 1)[1].split(',') if x.strip()]
        else:
            sys.stderr.write('未知参数：%s（用 --help 看用法）\n' % arg)
            return 2
        i += 1
    for m in modes:
        if m not in ('volume', 'share'):
            sys.stderr.write('--inject 只接受 volume / share，收到：%r\n' % m)
            return 2

    # ---------- 抓取 ----------
    try:
        data3 = fetch(3)
        data4 = fetch(4)
    except Exception as e:                          # noqa: BLE001
        sys.stderr.write('[口径闸] 抓取失败，闸本身无法执行：%s\n' % e)
        return 2

    targets = []
    for charttype, data, alias in ((4, data4, 'charttype=4 分国别'),
                                   (3, data3, 'charttype=3 占比组')):
        groups = share_groups(data, charttype)
        if not groups:
            sys.stderr.write(
                '[口径闸] %s：找不到以「%s」为键的份额组，接口结构可能已变化。\n'
                '         现有组：%s\n'
                % (alias, PERIOD_KEY,
                   '; '.join('组%d 首行keys=%s' % (gi, list((g.get('dataList') or [{}])[0].keys()))
                             for gi, g in enumerate(data))))
            return 2
        for gi, rows in groups:
            targets.append(('%s 组%d' % (alias, gi), rows))

    # ---------- 对照实验（仅 --inject 时）----------
    if modes:
        notes = [inject_error(targets, m) for m in modes]
        sys.stdout.write('[口径闸] 对照实验 —— 已注入错误：\n')
        for n in notes:
            sys.stdout.write('          %s\n' % n)

    # ---------- 校验 ----------
    errors = []
    stats = {'rows': 0, 'pairs': 0, 'sums': 0, 'maxErr': 0.0, 'maxWhere': ''}
    for where, rows in targets:
        before_rows, before_pairs = stats['rows'], stats['pairs']
        check_group(where, rows, errors, stats)
        sys.stdout.write('[口径闸] %s：%d 个月，%d 个（系列×口径）对\n'
                         % (where,
                            stats['rows'] - before_rows,
                            stats['pairs'] - before_pairs))

    sys.stdout.write('[口径闸] 份额加总闸：%d 组，允许区间 [%g, %g]\n'
                     % (stats['sums'], SUM_LO, SUM_HI))
    sys.stdout.write('[口径闸] 份额复算闸：%d 对，最大偏差 %.4f pp（阈值 %.2f）@ %s\n'
                     % (stats['pairs'], stats['maxErr'], SHARE_TOL,
                        stats['maxWhere'] or '无'))

    if errors:
        sys.stderr.write('\n[口径闸] 校验不通过，共 %d 项：\n' % len(errors))
        for e in errors:
            sys.stderr.write('  - %s\n' % e)
        sys.stderr.write(
            '\n[口径闸] 含义：数据内部自洽性被打破，[0]=批发 [1]=零售 '
            '[2]=批发占比% [3]=零售占比% 这个口径解释已不成立。\n'
            '         不要写入，保留上一版数据；若接口已改版，需重新确认字段顺序。\n')
        return 1

    sys.stdout.write('[口径闸] 通过：口径自洽 —— '
                     '[0]=批发 [1]=零售 [2]=批发占比% [3]=零售占比%\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
