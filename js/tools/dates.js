/*!
 * tools/dates.js — 日期天数计算（工具箱·按需加载子模块）
 *
 * 三件小事：两个日期相隔多久（含工作日）、某天往前/往后推 N 天是哪天、几岁。
 * 全部按用户设备上的日历与时区算，不联网校时、不读任何外部数据。
 *
 * 「虚岁 / 生肖 / 农历生日」用内置的农历对照表（1900-2098 年，1.6 KB）。
 * 一开始想省掉这张表——现代浏览器自带中国农历（Intl 的 chinese calendar）——
 * 实测发现它跟权威历书对不上：1987 年把「闰六月」算成了「闰七月」，2027 与 2030 年
 * 的春节各差一天（1476 个抽样日期里错了 28 个）。既然它会给错答案，就宁可自己带表。
 * 表是生成的、逐日校验过的（顺手还查出几个常用农历库各自的错处，一并记在第 3 节里，
 * 省得下次再踩）。来源与校验办法写在下面第 3 节。
 *
 * 有意不做的事：不查法定节假日。每年的放假安排由国务院办公厅另行公告，
 * 还会调休，任何写死在代码里的表都迟早会过期。这里改成让用户自己把
 * 休息日填进来，永远不会有「去年还能用、今年算错」的问题。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $$ = _.$$;
  var bindSeg = _.bindSeg, clearToast = _.clearToast, field = _.field,
      numOf = _.numOf, panelOf = _.panelOf, setStat = _.setStat, toast = _.toast,
      valOf = _.valOf;

  /* ======================================================================
     1. 日期基础
     ====================================================================== */
  var DAY = 86400000;
  var WD = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function iso(dt) { return dt.getFullYear() + '-' + pad2(dt.getMonth() + 1) + '-' + pad2(dt.getDate()); }
  function thousands(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

  /** 解析 <input type=date> 的 YYYY-MM-DD；非法（含 2 月 30 日这类）返回 null */
  function parseISO(s) {
    var m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(String(s == null ? '' : s).trim());
    if (!m) return null;
    var y = +m[1], mo = +m[2], d = +m[3];
    var dt = new Date(y, mo - 1, d);
    if (dt.getFullYear() !== y || dt.getMonth() !== mo - 1 || dt.getDate() !== d) return null;
    return dt;
  }

  /** 今天的 0 点（本地时区），后面所有比较都落在自然日上 */
  function today() {
    var n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }
  function todayISO() { return iso(today()); }

  /** 转成"第几天"整数：走 UTC 是为了避开夏令时——某些地区的一天不是 24 小时，
      直接拿毫秒相减会算出 0.9583 天这种数，取整后差一天 */
  function dayNum(dt) { return Math.round(Date.UTC(dt.getFullYear(), dt.getMonth(), dt.getDate()) / DAY); }
  function diffDays(a, b) { return dayNum(b) - dayNum(a); }
  function addDays(dt, n) { return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate() + n); }

  /** 某年某月（m 为 0-11）有几天。m 传 -1 / 12 时自动落到上一年 12 月 / 下一年 1 月 */
  function dim(y, m) { return new Date(y, m + 1, 0).getDate(); }

  function addMonths(dt, n) {
    var y = dt.getFullYear(), m = dt.getMonth() + n, d = dt.getDate();
    var ny = y + Math.floor(m / 12), nm = ((m % 12) + 12) % 12;
    // 1 月 31 日 + 1 个月 → 2 月只有 28/29 天，夹到月末（各家日历软件都这么做）
    return new Date(ny, nm, Math.min(d, dim(ny, nm)));
  }
  function addYears(dt, n) { return addMonths(dt, n * 12); }

  /**
   * 相差几年几月几天。
   *
   * 不用"年、月、日逐位相减再借位"那种写法——那种写法碰上 1 月 31 日、2 月 29 日这类
   * 边界会出现借位借过头、算出负数或差两三天的情况。这里改成先数满几个月：
   * 取最大的 M 使得「起始日 + M 个月」不超过结束日，剩下的用天数补齐。
   * 这样恒等式 a + M 个月 + d 天 = b 永远成立（M 个月按 addMonths 的规则夹到月末）。
   */
  function ymdBetween(a, b) {
    var months = (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth());
    var M = months;
    var cand = addMonths(a, M);
    if (dayNum(cand) > dayNum(b)) { M -= 1; cand = addMonths(a, M); }
    if (M < 0) { M = 0; cand = a; }
    return { y: Math.floor(M / 12), m: M % 12, d: diffDays(cand, b) };
  }
  function ymdText(o) {
    var s = [];
    if (o.y) s.push(o.y + ' 年');
    if (o.m) s.push(o.m + ' 个月');
    if (o.d || !s.length) s.push(o.d + ' 天');
    return s.join(' ');
  }

  /* ======================================================================
     2. 休息日：周六周日 + 用户自己填的
     ====================================================================== */
  /**
   * 解析自定义休息日。每行一个，支持 2026-10-01 与 2026-10-01~2026-10-07，
   * 同一行里用空格/逗号/顿号分隔多个也算。
   * @returns {{set:Object, bad:Array<string>, count:number}}
   */
  function parseHolidays(text) {
    var set = {}, bad = [], count = 0;

    function put(dt) { var k = iso(dt); if (!set[k]) { set[k] = 1; count++; } }

    String(text || '').split(/\r?\n/).forEach(function (raw) {
      var line = raw.replace(/[，、,;；]/g, ' ').trim();
      if (!line) return;
      line.split(/\s+/).forEach(function (item) {
        if (!item) return;
        var m = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s*(?:~|～|-{1,2}|至|到)\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2}))?$/.exec(item);
        if (!m) { bad.push(item); return; }
        var s = new Date(+m[1], +m[2] - 1, +m[3]);
        if (isNaN(s.getTime())) { bad.push(item); return; }
        if (!m[4]) { put(s); return; }
        var e = new Date(+m[4], +m[5] - 1, +m[6]);
        if (isNaN(e.getTime()) || dayNum(e) < dayNum(s)) { bad.push(item); return; }
        if (diffDays(s, e) > 400) { bad.push(item + '（区间最长 400 天）'); return; }
        for (var i = 0; i <= diffDays(s, e); i++) put(addDays(s, i));
      });
    });
    return { set: set, bad: bad, count: count };
  }

  /** 'hol' / 'week' / '' */
  function restOf(dt, holidays) {
    if (holidays && holidays[iso(dt)]) return 'hol';
    var w = dt.getDay();
    return (w === 0 || w === 6) ? 'week' : '';
  }

  /** 往后（n>0）或往前（n<0）数 n 个工作日，跳过周六周日与自定义休息日 */
  function addWorkdays(dt, n, holidays) {
    if (!n) return dt;
    var step = n > 0 ? 1 : -1, left = Math.abs(n), d = dt;
    var guard = left * 3 + 400;   // 连续休息日再多也不会卡死
    while (left > 0 && guard-- > 0) {
      d = addDays(d, step);
      if (!restOf(d, holidays)) left--;
    }
    return d;
  }

  /** 落在休息日就顺延到下一个工作日 */
  function nextWorkday(dt, holidays) {
    var d = dt, guard = 400;
    while (restOf(d, holidays) && guard-- > 0) d = addDays(d, 1);
    return d;
  }

  /* ======================================================================
     3. 农历（虚岁 / 生肖 / 农历生日）—— 内置对照表，不联网、不看浏览器脸色

     为什么不用 Intl 自带的农历：实测它跟权威历书对不上（1987 年把闰六月算成闰七月，
     2027 与 2030 年的春节各差一天；1476 个抽样日期里错了 28 个），而且它是按天文算法
     现算的，不同浏览器 / 系统版本还可能给出不同结果。既然会给错答案，就自己带表。

     表 = 两个字符串（合计 1.6 KB），覆盖农历 1900-2098 年：
       LX_STARTS  每 3 位一组，累积起来就是该年正月初一距 1900 年正月初一的天数
       LX_INFOS   每 5 位一组十六进制（最多 17 位有效）：
                    bit 0-3   闰月月份（0 = 本年无闰月）
                    bit 4-15  正月到腊月各月长度，1 = 30 天、0 = 29 天（bit 4 是正月）
                    bit 16    闰月长度，1 = 30 天、0 = 29 天
     换表 / 扩年份：改这两串就行，别的都不用动。

     这份表怎么来的、怎么验的（要换表就照这个流程重来一遍）：
       来源：由 lunardate 0.3.0 的农历数据生成，再把 1933 / 1954 / 1978 三年各一个月
             的大月小月判反改正过来（见下）。三处改的都是「这 30 天该算在前一个月还是
             后一个月」，该年总天数没有变，所以每年正月初一的位置一个字都没动。
       逐日核验：装回 JS 后逐日跑 1900-01-31 ~ 2099-01-20 共 72,674 天，与 zhdate
             （纯 Python 的独立实现）逐日比对，全部一致。
       官方裁决：1933 / 1954 / 1978 / 2057 四年各有一段，几个库给出的答案互不相同。
             拿香港天文台官网公布的《公曆與農曆日期對照表》逐点核对，结论是：
               1933-07-22 = 闰五月三十（原表错写成六月初一）→ 已按官方订正
               1954-11-25 = 冬月初一（原表错写成十月三十）  → 已按官方订正
               1978-09-02 = 七月三十（原表错写成八月初一）  → 已按官方订正
               2057-09-28 = 九月初一 → 本表本来就是对的，是 lunar-javascript 错了一天
             四段共 15 个边界点（每月初一、廿九、三十）现已全部与香港天文台一致。
       已知分歧：lunar-javascript 跟本表只差 2057-09-28 ~ 2057-10-27 这一段，
             而这一段香港天文台支持本表。
       区间尾部：农历 2099 年的腊月长度需要 2100 年的正月初一才能定，取不到，所以
             表只收到 2098 年——超出范围时 lunarOf() 返回 null，界面照实说明，不猜。
     ====================================================================== */
  var BRANCH = '子丑寅卯辰巳午未申酉戌亥';
  var ANIMAL = { 子: '鼠', 丑: '牛', 寅: '虎', 卯: '兔', 辰: '龙', 巳: '蛇',
                 午: '马', 未: '羊', 申: '猴', 酉: '鸡', 戌: '狗', 亥: '猪' };
  var MONTH_CN = ['正月', '二月', '三月', '四月', '五月', '六月',
                  '七月', '八月', '九月', '十月', '冬月', '腊月'];
  var DAY_CN = ['初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
                '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
                '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'];

  var LX_EPOCH = '1900-01-31';
  var LX_Y0 = 1900;
  var LX_STARTS = '000384354355383354355384354355384354384354354384354355384355384354354384354354385354355384' +
    '354383354355384355354384354384354354384355354385354354384354384354355384354355384354383355' +
    '354384355354384355353384355384354355384354354384354384354355384355354384354384354354384355' +
    '355384354354383355384354355384354354384354355384354385354354384354354384355384354355384354' +
    '354384354355384354384354354384355354384355384354354384354354384355355384354384354354384354' +
    '355384355384354354383355354384355354384354384354355384354355384354384354354384355354384355' +
    '354384354384354355384354355383354384354355384355354384354';
  var LX_INFOS = '0bd28075200ea500b2a5064b00a9b01aa64056a00b5900baa2075200da560b2500a4b01a4b502ad0056b005b52' +
    '0da901e9270e9200d2500d2d50a56002b601ad5406d400ea900f4a20e92006a66052b00a570195650b5a006d40' +
    '17613074901b1370a930052b0151b60aad0056a01da540ba400b4900d4b20a9500aad7053600aad01aca505b20' +
    '0da501ea230d4a0059580a97005560057560ad5006d20075540ea50064a0064f30a9b00ada7056a00b6900bb25' +
    '0b5200b2500b2b40a4b00aab802ad0056d015a960da900d9200e9540d2500e4da0a56002b6002f5606d500ea90' +
    '0f5250e9200d260052e30a5700ad68035a006d500b69507490069300a9b4052b00a5b00aae2056a00dd570ba40' +
    '0b4900d5350a950052d0055d40ab500baa905d200da501e8a60d4a00c9500a9e4055600ab500ada206d2007656' +
    '07250064b0065750cab0055a0056e30b6900f52b0b5200b2501d0b60a4b004ab002bb505ad00b6a00daa20d920' +
    '0ea570d2500a5501a4d504b6005b5016d230ec900f9280e9200d260151660a57005560136540755007490074b3' +
    '069300aab7052b00a5b00aba5056a00b6500baa40b4a00d9580a950052d0056d60ab5005aa005d540da500d4a0' +
    '0e4d30c9600cce7055600ab501ad2506d200ea50072a4068b00697804ab0055b0155660b6a0075200b9540b450' +
    '0a8b0';
  var LX = (function () {
    var starts = [], i, acc = 0;
    for (i = 0; i < LX_STARTS.length; i += 3) starts.push(parseInt(LX_STARTS.substr(i, 3), 10));
    for (i = 0; i < starts.length; i++) { acc += starts[i]; starts[i] = acc; }
    var infos = [];
    for (i = 0; i < LX_INFOS.length; i += 5) infos.push(parseInt(LX_INFOS.substr(i, 5), 16));
    return {
      starts: starts, infos: infos,
      base: dayNum(parseISO(LX_EPOCH)),
      // 表尾：最后一年各月长度加起来，就是表格覆盖到的最后一天
      last: starts[starts.length - 1] + (function () {
        var ms = lxMonths(infos[infos.length - 1]), n = 0, k;
        for (k = 0; k < ms.length; k++) n += ms[k].days;
        return n - 1;
      })()
    };
  })();

  /** 把 info 展开成本年的月份序列：{month, leap, days} */
  function lxMonths(info) {
    var leapM = info & 0xF, out = [], lens = [], m;
    for (m = 1; m <= 12; m++) lens.push(((info >> (3 + m)) & 1) ? 30 : 29);
    var extra = ((info >> 16) & 1) ? 30 : 29;
    for (m = 1; m <= 12; m++) {
      out.push({ month: m, leap: false, days: lens[m - 1] });
      if (leapM && m === leapM) out.push({ month: m, leap: true, days: extra });
    }
    return out;
  }

  /**
   * 公历 → 农历。y 是农历年号（例：2026-02-16 还在乙巳年，y 为 2025），
   * 这样 (y-4)%12 直接是生肖序号，不必去解析干支字符串。
   * 超出表格范围（1900-01-31 之前 / 2099-01-20 之后）返回 null，由界面照实说明。
   */
  function lunarOf(dt) {
    var n = dayNum(dt) - LX.base;
    if (n < 0 || n > LX.last) return null;
    var s = LX.starts, lo = 0, hi = s.length - 1, mid;
    while (lo < hi) {
      mid = (lo + hi + 1) >> 1;
      if (s[mid] <= n) lo = mid; else hi = mid - 1;
    }
    var months = lxMonths(LX.infos[lo]), off = n - s[lo], i, mo;
    for (i = 0; i < months.length; i++) {
      mo = months[i];
      if (off < mo.days) {
        return {
          year: LX_Y0 + lo, month: mo.month, day: off + 1, leap: mo.leap,
          text: (mo.leap ? '闰' : '') + MONTH_CN[mo.month - 1] + DAY_CN[off]
        };
      }
      off -= mo.days;
    }
    return null;
  }

  function animalOf(lunarYear) { return ANIMAL[BRANCH[(((lunarYear - 4) % 12) + 12) % 12]] || '—'; }

  /* ======================================================================
     4. 星座（纯公历，规则固定）
     ====================================================================== */
  var STARS = [[1, 20, '摩羯座'], [2, 19, '水瓶座'], [3, 21, '双鱼座'], [4, 20, '白羊座'],
    [5, 21, '金牛座'], [6, 22, '双子座'], [7, 23, '巨蟹座'], [8, 23, '狮子座'],
    [9, 23, '处女座'], [10, 24, '天秤座'], [11, 23, '天蝎座'], [12, 22, '射手座'],
    [12, 32, '摩羯座']];
  function starOf(dt) {
    var m = dt.getMonth() + 1, d = dt.getDate();
    for (var i = 0; i < STARS.length; i++) {
      if (m < STARS[i][0] || (m === STARS[i][0] && d < STARS[i][1])) return STARS[i][2];
    }
    return '摩羯座';
  }

  /* ======================================================================
     5. 三个小功能
     ====================================================================== */
  function setupDates() {
    var P = panelOf('dates');
    if (!P) return;

    bindSeg(P);

    function setDate(name, value) {
      var el = field(P, name);
      if (el) el.value = value;
    }

    // 默认值：开始=今天，结束=今天 +30 天，基准=今天，算到=今天。出生日留空让用户自己填。
    var t = today();
    setDate('a', iso(t));
    setDate('b', iso(addDays(t, 30)));
    setDate('base', iso(t));
    setDate('ref', iso(t));

    /* ---- ① 相隔多久 ---- */
    function runGap(sub) {
      clearToast(sub);
      var A = parseISO(valOf(P, 'a')), B = parseISO(valOf(P, 'b'));
      if (!A || !B) { toast(sub, '开始日期和结束日期都填上才能算。', 'err'); return; }

      var hol = parseHolidays(valOf(P, 'hd'));
      if (hol.bad.length) {
        toast(sub, '有 ' + hol.bad.length + ' 条自定义日期没看懂：' +
          hol.bad.slice(0, 3).join('、') + (hol.bad.length > 3 ? ' 等' : '') +
          '。请照着 2026-10-01 或者 2026-10-01~2026-10-07 这样写。', 'err');
        return;
      }

      var swapped = false, a = A, b = B;
      if (dayNum(b) < dayNum(a)) { swapped = true; a = B; b = A; }

      var total = diffDays(a, b);
      if (total > 400000) { toast(sub, '这两个日期隔得太远了，换近一点的再算。', 'err'); return; }

      var work = 0, week = 0, holi = 0, i, d, r;
      for (i = 0; i < total; i++) {
        r = restOf(addDays(a, i), hol.set);
        if (r === 'hol') holi++;
        else if (r === 'week') week++;
        else work++;
      }

      var ymd = ymdBetween(a, b);
      var cells = [
        ['总天数', thousands(total) + ' 天'],
        ['折合', ymdText(ymd)],
        ['工作日', thousands(work) + ' 天'],
        ['周六周日', thousands(week) + ' 天']
      ];
      if (holi) cells.push(['你填的休息日', thousands(holi) + ' 天']);

      var rel = diffDays(today(), b);
      if (rel > 0) cells.push(['倒计时', '还有 ' + thousands(rel) + ' 天']);
      else if (rel === 0) cells.push(['倒计时', '就是今天']);
      else cells.push(['已经过去', thousands(-rel) + ' 天']);

      var note = '「总天数」按日历直接相减：9 月 1 日到 10 月 1 日是 30 天，也就是整 1 个月——' +
        '同一段区间，「总天数」和「折合」只是两种数法（相差几天、差几月几天）。' +
        '<br>工作日 = 这段区间里的周一至周五，再剔除你填的休息日。' +
        '口径是<b>含开始日、不含结束日</b>，所以工作日 + 周六周日 + 你填的休息日 = 总天数。';
      if (swapped) note += '<br>你填的开始日比结束日还晚，已经对调过来按正序算了。';
      if (hol.count && !holi) note += '<br>你填的 ' + hol.count + ' 个休息日都不在这段区间里。';
      setStat(sub, cells, note);
    }

    /* ---- ② 往前 / 往后推 ---- */
    function runShift(sub) {
      clearToast(sub);
      var base = parseISO(valOf(P, 'base'));
      if (!base) { toast(sub, '先填一个起始日期。', 'err'); return; }

      var dir = valOf(P, 'dir') === '-1' ? -1 : 1;
      var unit = valOf(P, 'unit') || 'd';
      var onlyWork = !!valOf(P, 'onlyWork');
      var n = Math.abs(numOf(P, 'num', 0));
      if (!(n > 0)) { toast(sub, '数量填个大于 0 的整数。', 'err'); return; }
      if (unit === 'd' || unit === 'w') {
        if (n > 1000000) { toast(sub, '数量太大了，最多 1000000。', 'err'); return; }
      } else if (n > 100000) { toast(sub, '数量太大了，最多 100000。', 'err'); return; }

      var hol = parseHolidays(valOf(P, 'hd'));
      if (hol.bad.length) {
        toast(sub, '「相隔多久」里那 ' + hol.bad.length + ' 条自定义日期没看懂，先改一下再来按工作日推算。', 'err');
        return;
      }

      var res, how = '', workMode = '';
      if (unit === 'd') {
        if (onlyWork) {
          if (n > 2000) { toast(sub, '按工作日推算时最多算 2000 天，再多请分几次。', 'err'); return; }
          res = addWorkdays(base, dir * n, hol.set);
          workMode = '只数工作日：跳过周六周日' + (hol.count ? '和你填的 ' + hol.count + ' 个休息日' : '');
        } else res = addDays(base, dir * n);
      } else if (unit === 'w') {
        if (onlyWork) {
          if (n * 5 > 2000) { toast(sub, '按工作日推算时最多算 2000 天，再多请分几次。', 'err'); return; }
          res = addWorkdays(base, dir * n * 5, hol.set);
          workMode = '你选了「只数工作日」，' + n + ' 周按 ' + (n * 5) + ' 个工作日算';
        } else res = addDays(base, dir * n * 7);
      } else if (unit === 'm') {
        res = addMonths(base, dir * n);
        if (onlyWork) {
          var r1 = nextWorkday(res, hol.set);
          if (dayNum(r1) !== dayNum(res)) how = '落在休息日，顺延到了 ' + iso(r1);
          res = r1;
          workMode = '按月推的是日历日期；碰到休息日会顺延到下一个工作日';
        }
      } else {
        res = addYears(base, dir * n);
        if (onlyWork) {
          var r2 = nextWorkday(res, hol.set);
          if (dayNum(r2) !== dayNum(res)) how = '落在休息日，顺延到了 ' + iso(r2);
          res = r2;
          workMode = '按年推的是日历日期；碰到休息日会顺延到下一个工作日';
        }
      }

      var cal = diffDays(base, res);
      var cells = [
        ['结果日期', iso(res)],
        ['星期', WD[res.getDay()]],
        ['相隔', (cal < 0 ? '往前 ' : '') + thousands(Math.abs(cal)) + ' 天']
      ];
      var rest = restOf(res, hol.set);
      cells.push(['这一天是', rest === 'hol' ? '你填的休息日' : (rest === 'week' ? '周六周日' : '工作日')]);

      var toNow = diffDays(today(), res);
      if (toNow > 0) cells.push(['距今天', '还有 ' + thousands(toNow) + ' 天']);
      else if (toNow === 0) cells.push(['距今天', '就是今天']);
      else if (dayNum(base) <= dayNum(today())) cells.push(['距今天', '已经过去 ' + thousands(-toNow) + ' 天']);

      var uTxt = { d: '天', w: '周', m: '个月', y: '年' }[unit];
      var note = '从 ' + iso(base) + '（' + WD[base.getDay()] + '）' +
        (dir > 0 ? '往后' : '往前') + ' ' + n + ' ' + uTxt + '，得到 ' + iso(res) + '。' +
        '日历上一共跨了 ' + thousands(Math.abs(cal)) + ' 天。';
      if (workMode) note += '<br>' + workMode + '。';
      if (how) note += '<br>' + how + '。';
      if (unit === 'm' || unit === 'y') {
        note += '<br>按月、按年推的时候，如果起始日是 31 号而目标月份没有 31 号，会自动夹到那个月的最后一天。';
      }
      setStat(sub, cells, note);
    }

    /* ---- ③ 算年龄 ---- */
    function runAge(sub) {
      clearToast(sub);
      var birth = parseISO(valOf(P, 'birth'));
      var ref = parseISO(valOf(P, 'ref')) || today();
      if (!birth) { toast(sub, '先填出生日期。', 'err'); return; }
      if (dayNum(ref) < dayNum(birth)) { toast(sub, '「算到哪一天」比出生日期还早，换一个。', 'err'); return; }

      var ymd = ymdBetween(birth, ref);
      var full = diffDays(birth, ref);
      var lb = lunarOf(birth), lr = lunarOf(ref);

      var cells = [['实足年龄', ymdText(ymd)]];
      if (lb && lr) cells.push(['虚岁', (lr.year - lb.year + 1) + ' 岁']);
      if (lb) cells.push(['生肖', animalOf(lb.year)]);
      cells.push(['出生至今', thousands(full) + ' 天']);

      // 下一个公历生日
      var nb = null, feb29 = false;
      if (birth.getMonth() === 1 && birth.getDate() === 29 && dim(ref.getFullYear(), 1) === 28) {
        feb29 = true;
        nb = new Date(ref.getFullYear(), 1, 28);
      } else {
        nb = new Date(ref.getFullYear(), birth.getMonth(), Math.min(birth.getDate(), dim(ref.getFullYear(), birth.getMonth())));
      }
      if (dayNum(nb) < dayNum(ref)) {
        var ny = ref.getFullYear() + 1;
        nb = (birth.getMonth() === 1 && birth.getDate() === 29 && dim(ny, 1) === 28)
          ? new Date(ny, 1, 28) : new Date(ny, birth.getMonth(), birth.getDate());
      }
      var toB = diffDays(ref, nb);

      if (lb) cells.push(['农历生日', lb.text]);
      cells.push(['星座', starOf(birth)]);
      cells.push(['出生那天', WD[birth.getDay()]]);
      cells.push(['下个生日', iso(nb) + '（' + WD[nb.getDay()] + '）']);
      cells.push(['距离生日', toB === 0 ? '就是今天' : '还有 ' + thousands(toB) + ' 天']);

      var note = '实足年龄按公历逐位借位算，就是「满 X 年 Y 个月 Z 天」。' +
        (lb && lr ? '虚岁按农历年算：出生当天算 1 岁，每过一个春节长 1 岁，所以虚岁通常比周岁大 1 到 2 岁。' : '');
      note += '<br>农历与生肖按本站内置的农历表算（覆盖 1900 至 2098 年），不联网，' +
        '也不会因为浏览器不同而结果不一样。';
      if (feb29) note += '<br>生日是 2 月 29 日，遇到没有 2 月 29 日的年份，下个生日按 2 月 28 日算。';
      if (!lb) note += '<br>这个日期超出了内置农历表的范围（1900 年 1 月 31 日至 2099 年 1 月 20 日），' +
        '所以虚岁和生肖这次没算，公历部分不受影响。';
      else if (lb.leap) note += '<br>出生那年有闰月，你的农历生日落在闰月里。';
      setStat(sub, cells, note);
    }

    /* ---- 绑定 ---- */
    var run = { gap: runGap, shift: runShift, age: runAge };
    $$('[data-act]', P).forEach(function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act');
        var sub = (b.closest ? b.closest('[data-sub]') : null) || P;

        if (act === 'gapToday') { setDate('b', todayISO()); return runGap(sub); }
        if (act === 'gap30') { setDate('b', iso(addDays(today(), 30))); return runGap(sub); }
        if (act === 'gapY') { setDate('b', iso(addYears(today(), 1))); return runGap(sub); }
        if (act === 'gapFirst') { setDate('a', todayISO()); return runGap(sub); }
        if (act === 'swap') {
          var va = valOf(P, 'a'), vb = valOf(P, 'b');
          if (va && vb) { setDate('a', vb); setDate('b', va); }
          return runGap(sub);
        }
        if (act === 'shiftToday') { setDate('base', todayISO()); return runShift(sub); }
        if (act === 'ageToday') { setDate('ref', todayISO()); return runAge(sub); }
        if (run[act]) run[act](sub);
      });
    });

    // 日期框改动后立刻重算（键盘上下键调日期也能实时跟着变）
    var SUBS = {};
    ['gap', 'shift', 'age'].forEach(function (k) {
      SUBS[k] = P.querySelector('[data-sub="' + k + '"]') || P;
    });

    [['a', 'gap'], ['b', 'gap'], ['hd', 'gap'], ['base', 'shift'],
      ['num', 'shift'], ['birth', 'age'], ['ref', 'age']].forEach(function (pair) {
      var el = field(P, pair[0]);
      if (!el) return;
      el.addEventListener('change', function () {
        // 出生日还空着就别在「算年龄」那格弹报错——用户只是先点了参考日期
        if (pair[1] === 'age' && !valOf(P, 'birth')) return;
        run[pair[1]](SUBS[pair[1]]);
      });
    });

    runGap(SUBS.gap);
    runShift(SUBS.shift);
  }

  window.LXTools.define('dates', setupDates);
})();
