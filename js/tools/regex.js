/*!
 * tools/regex.js — 正则表达式工作台（工具箱·按需加载子模块）
 *
 * 正则这东西，写的时候自己觉得清楚，过两天再看就成天书了。这个小工具做四件事：
 *   1. 边打边把测试文本里所有匹配到的内容标成金色（即时高亮，不用点按钮）；
 *   2. 列一张明细表：第几处匹配、在什么位置、抓到了什么、每个圆括号分组分别抓到了什么；
 *   3. 把这条正则从左到右拆成一段一段，逐段说它到底要什么（"念成人话"）；
 *   4. 填上替换式，立刻看到替换后的文本（$1、$& 都照常支持）。
 *
 * 用的是浏览器自带的正则引擎——所以你在这里测出来的行为，跟它在程序里的行为
 * 一模一样，不会因为换了个引擎而变样。全部在本机算，一个字都不外发。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $$ = _.$$;
  var clearToast = _.clearToast, copyText = _.copyText,
      esc = _.esc, panelOf = _.panelOf, setStat = _.setStat, toast = _.toast,
      valOf = _.valOf;

  var MAX_MATCHES = 20000;   // 一次最多认这么多处，再多也没人看
  var SHOW_ROWS = 300;       // 明细表最多列这么多行
  var SHOW_PARTS = 80;       // 解释表最多列这么多段
  var MAX_HL = 200000;       // 测试文本超过这么长就不做整段高亮了（DOM 会太重）

  /* ======================================================================
     1. 逐段解释——把正则念成人话
     ====================================================================== */

  /** 反斜杠后面跟一个字符时的含义 */
  var ESC_DESC = {
    d: '一个数字（0 到 9）',
    D: '一个不是数字的字符',
    w: '一个"词字符"：字母、数字或下划线',
    W: '一个不是字母数字下划线的字符',
    s: '一个空白（空格 / 制表符 / 换行都算）',
    S: '一个不是空白的字符',
    b: '一个"词的边界"处（字母数字与其它字符的交界，本身不占字符）',
    B: '一个"不是词边界"的位置（本身不占字符）',
    n: '一个换行符',
    r: '一个回车符',
    t: '一个制表符',
    f: '一个换页符',
    v: '一个垂直制表符',
    '0': '一个空字符（NUL）'
  };

  /** 方括号里用 \d \w \s 这类简写时的含义 */
  var CLS_DESC = {
    d: '数字', D: '不是数字的字符',
    w: '字母数字下划线', W: '不是字母数字下划线的字符',
    s: '空白', S: '不是空白的字符'
  };

  function safeChar(code) {
    try { return String.fromCodePoint(code); } catch (e) { return '？'; }
  }

  /** 读一段 \uXXXX / \u{XXXXX} / \xXX，读不出来返回 null */
  function unicodeLiteral(s, i) {
    var rest = s.slice(i), m;
    m = /^\\u\{([0-9a-fA-F]+)\}/.exec(rest);
    if (m) return { ch: safeChar(parseInt(m[1], 16)), len: m[0].length };
    m = /^\\u([0-9a-fA-F]{4})/.exec(rest);
    if (m) return { ch: safeChar(parseInt(m[1], 16)), len: m[0].length };
    m = /^\\x([0-9a-fA-F]{2})/.exec(rest);
    if (m) return { ch: safeChar(parseInt(m[1], 16)), len: m[0].length };
    return null;
  }

  /** 读一个量词（* + ? {n} {n,} {n,m}，含懒惰写法），没有返回 null */
  function quantAt(src, i) {
    var c = src.charAt(i), raw = '', desc = '';
    if (c === '*') { raw = '*'; desc = '重复 0 次或任意多次'; }
    else if (c === '+') { raw = '+'; desc = '重复 1 次或更多次'; }
    else if (c === '?') { raw = '?'; desc = '可有可无，最多出现 1 次'; }
    else if (c === '{') {
      var m = /^\{(\d+)(,(\d*))?\}/.exec(src.slice(i));
      if (!m) return null;
      var a = parseInt(m[1], 10);
      if (m[2] === undefined) desc = '正好重复 ' + a + ' 次';
      else if (m[3] === '') desc = '至少重复 ' + a + ' 次';
      else {
        var b = parseInt(m[3], 10);
        if (b < a) return null;      // 写反了，交给浏览器报错，这里不装作看懂了
        desc = '重复 ' + a + ' 到 ' + b + ' 次';
      }
      raw = m[0];
    } else return null;

    var out = { raw: raw, desc: desc, len: raw.length };
    if (src.charAt(i + out.len) === '?') {
      out.raw += '?';
      out.len += 1;
      out.desc += '（但尽量少匹配）';
    }
    return out;
  }

  /** 方括号里的内容翻译成一串短语（拼在"一个字符："后面） */
  function classInside(body) {
    var phrases = [], singles = '', i = 0;
    function flushSingles() {
      if (!singles) return;
      var uniq = [];
      for (var k = 0; k < singles.length; k++) {
        if (uniq.indexOf(singles.charAt(k)) < 0) uniq.push(singles.charAt(k));
      }
      if (uniq.length <= 8) phrases.push('「' + uniq.join('') + '」里的任意一个');
      else phrases.push('这 ' + uniq.length + ' 个字符里的任意一个');
      singles = '';
    }
    while (i < body.length) {
      var c = body.charAt(i);
      if (c === '\\') {
        var e = body.charAt(i + 1);
        if (CLS_DESC[e]) { flushSingles(); phrases.push(CLS_DESC[e]); i += 2; continue; }
        var u = unicodeLiteral(body, i);
        if (u) { singles += u.ch; i += u.len; continue; }
        singles += (e || '\\'); i += 2; continue;
      }
      if (body.charAt(i + 1) === '-' && i + 2 < body.length) {
        flushSingles();
        phrases.push('「' + c + '」到「' + body.charAt(i + 2) + '」之间的');
        i += 3; continue;
      }
      singles += c; i++;
    }
    flushSingles();
    if (!phrases.length) return '空的方括号（什么都匹配不到）';
    return phrases.join('、');
  }

  /** 读一个 [...]，返回原文 / 含义 / 长度 */
  function classAt(src, i) {
    var j = i + 1, neg = false, body = '', closed = false;
    if (src.charAt(j) === '^') { neg = true; j++; }
    if (src.charAt(j) === ']') { body += ']'; j++; }   // 开头就写 ] 表示它本身
    while (j < src.length) {
      var c = src.charAt(j);
      if (c === '\\') { body += src.slice(j, j + 2); j += 2; continue; }
      if (c === ']') { closed = true; j++; break; }
      body += c; j++;
    }
    return {
      raw: src.slice(i, j),
      desc: '一个字符：' + (neg ? '不是 ' : '') + classInside(body),
      len: j - i,
      warn: closed ? '' : '有一个 `[` 没有对应的 `]` —— 方括号没配上对。'
    };
  }

  /** 读一个 \x 转义 */
  function escapeAt(src, i) {
    var c = src.charAt(i + 1);
    if (c === '') {
      return { raw: '\\', desc: '一个孤零零的反斜杠', len: 1,
        warn: '正则结尾多了一个 `\\`，后面没有东西可以转义。' };
    }
    if (ESC_DESC[c]) {
      return { raw: '\\' + c, desc: ESC_DESC[c], len: 2, anchor: c === 'b' || c === 'B' };
    }
    if (/[1-9]/.test(c)) {
      var back = /^\\([1-9]\d?)/.exec(src.slice(i))[0];
      var num = back.slice(1);
      return { raw: back, desc: '和第 ' + num + ' 个分组抓到的一模一样的内容（反向引用）', len: back.length,
        warn: '用了反向引用 `\\' + num + '`：正则里必须真的存在第 ' + num + ' 个分组，否则会报错。' };
    }
    if (c === 'k' && src.charAt(i + 2) === '<') {
      var km = /^\\k<([^>]*)>/.exec(src.slice(i));
      if (km) return { raw: km[0], desc: '和名为「' + km[1] + '」的那个分组抓到的一样（具名反向引用）', len: km[0].length };
    }
    if (c === 'p' || c === 'P') {
      var pm = /^\\[pP]\{[^}]*\}/.exec(src.slice(i));
      if (pm) {
        return { raw: pm[0], desc: '一个 Unicode 分类为「' + pm[0].slice(3, -1) + '」的字符' +
          (c === 'P' ? '（取反）' : ''), len: pm[0].length };
      }
    }
    var u = unicodeLiteral(src, i);
    if (u) return { raw: src.slice(i, i + u.len), desc: '一个特定的字符「' + u.ch + '」', len: u.len };
    return { raw: '\\' + c, desc: '一个普通的「' + c + '」字符（加了反斜杠，去掉了它的特殊含义）', len: 2 };
  }

  /**
   * 把一条正则拆成一段一段，逐段给一句人话。
   * @returns {{parts:Array<{raw:string,desc:string}>, warns:Array<string>, sentence:string, hasB:boolean}}
   */
  function explainRegex(src) {
    var parts = [], warns = [], i = 0;
    var n = src.length, capCount = 0, stack = [];

    function pushUnit(raw, desc) {
      var q = quantAt(src, i);
      if (q) { raw += q.raw; desc += '，' + q.desc; i += q.len; }
      parts.push({ raw: raw, desc: desc });
    }
    if (!n) return { parts: [], warns: ['还没有填正则。'], sentence: '', hasB: false };

    while (i < n) {
      var c = src.charAt(i);

      if (c === '|') { parts.push({ raw: '|', desc: '或者 —— 竖线左右两边任选一边' }); i++; continue; }
      if (c === '^') { parts.push({ raw: '^', desc: '要求这里是开头' }); i++; continue; }
      if (c === '$') { parts.push({ raw: '$', desc: '要求这里是结尾' }); i++; continue; }

      if (c === ')') {
        if (!stack.length) {
          parts.push({ raw: ')', desc: '多出来的一个右括号' });
          warns.push('有一个 `)` 没有对应的 `(`，括号数量对不上。');
        } else {
          var gno = stack.pop();
          var rawC = ')', descC = '到这儿，第 ' + gno + ' 个分组结束';
          var qc = quantAt(src, i + 1);
          if (qc) { rawC += qc.raw; descC += '，这一整组' + qc.desc; i += qc.len; }
          parts.push({ raw: rawC, desc: descC });
        }
        i++;
        continue;
      }

      if (c === '(') {
        var rest = src.slice(i), gm, rawG = '(', descG = '', no = 0, lenG = 1;
        gm = /^\(\?<([A-Za-z_$][A-Za-z0-9_$]*)>/.exec(rest);
        if (gm) {
          rawG = gm[0]; lenG = gm[0].length; no = ++capCount;
          descG = '开始一个"具名分组"：把里面匹配到的内容单独抓出来，起名叫「' + gm[1] +
            '」（它同时也是第 ' + no + ' 组）';
        } else if (/^\(\?:/.test(rest)) {
          rawG = '(?:'; lenG = 3;
          descG = '开始一个"只分组不抓取"的小括号：括号只是为了让后面的量词作用在一整块上，不会单独算一组';
        } else if (/^\(\?=/.test(rest)) {
          rawG = '(?='; lenG = 3;
          descG = '开始一个"预判"：要求紧接着的文本符合下面这段，但下面这段本身不算进匹配结果（只看位置，不吃字符）';
        } else if (/^\(\?!/.test(rest)) {
          rawG = '(?!'; lenG = 3;
          descG = '开始一个"否定预判"：要求紧接着的文本不符合下面这段（只看位置，不吃字符）';
        } else if (/^\(\?<=/.test(rest)) {
          rawG = '(?<='; lenG = 4;
          descG = '开始一个"回头看"：要求前面的文本符合下面这段，但下面这段不算进匹配结果（只看位置，不吃字符）';
        } else if (/^\(\?<!/.test(rest)) {
          rawG = '(?<!'; lenG = 4;
          descG = '开始一个"否定回头看"：要求前面的文本不符合下面这段（只看位置，不吃字符）';
        } else if (/^\(\?/.test(rest)) {
          warns.push('`(?` 后面的写法浏览器不认：只支持 `?:`、`?=`、`?!`、`?<=`、`?<!`、`?<名字>` 这几种。');
          descG = '开始一个分组（写法可能有问题）';
        } else {
          no = ++capCount;
          descG = '开始第 ' + no + ' 个分组：把里面匹配到的内容单独抓出来';
        }

        if (no) stack.push(no);
        pushUnit(rawG, descG);
        i += lenG;
        continue;
      }

      if (c === '[') {
        var cl = classAt(src, i);
        if (cl.warn) warns.push(cl.warn);
        i += cl.len;
        pushUnit(cl.raw, cl.desc);
        continue;
      }

      if (c === '\\') {
        var e = escapeAt(src, i);
        if (e.warn) warns.push(e.warn);
        i += e.len;
        if (e.anchor) parts.push({ raw: e.raw, desc: e.desc });   // 边界锚点后面不能跟量词
        else pushUnit(e.raw, e.desc);
        continue;
      }

      if (c === '*' || c === '+' || c === '?') {
        warns.push('重复符号（`*` `+` `?` `{n}`）前面必须紧跟着要重复的内容，这里前面没有，正则会报错。');
        parts.push({ raw: c, desc: '重复符号，可是前面没有东西可以重复' });
        i++; continue;
      }
      if (c === '{' && !/^\{\d+(,\d*)?\}/.test(src.slice(i))) {
        parts.push({ raw: '{', desc: '一个普通的「{」字符（要当量词用，得写成 {n}、{n,}、{n,m}）' });
        i++; continue;
      }

      if (c === '.') {
        var qd = quantAt(src, i + 1);
        if (qd && (qd.raw === '*' || qd.raw === '+')) {
          warns.push('`.' + qd.raw + '` 是"有多少要多少"，会一路吃到后面能对上的最后一段。想让它少匹配，写成 `.' +
            qd.raw + '?`。');
        }
        parts.push({ raw: '.', desc: '任意一个字符（默认不包括换行）' });
        i++;
        if (qd) {
          parts[parts.length - 1].raw += qd.raw;
          parts[parts.length - 1].desc += '，' + qd.desc;
          i += qd.len;
        }
        continue;
      }

      // 普通字面量
      parts.push({ raw: c, desc: '一个普通的「' + c + '」' });
      i++;
    }

    var sentence = parts.length <= 6
      ? '从左到右依次是：' + parts.map(function (p) { return p.desc; }).join('；')
      : '';
    return { parts: parts, warns: warns, sentence: sentence, hasB: /\\(b|B)/.test(src) };
  }

  /* ======================================================================
     2. 匹配
     ====================================================================== */
  /**
   * 找出所有匹配。空匹配（比如 `a*` 匹配到空）要手动把 lastIndex 往前挪一格，
   * 否则 exec 会原地打转 —— 这是 JS 正则的老坑。
   */
  function matchAll(re, text) {
    var out = [], m, guard = 0;
    re.lastIndex = 0;
    while ((m = re.exec(text)) !== null) {
      out.push({
        s: m.index,
        e: m.index + m[0].length,
        text: m[0],
        groups: Array.prototype.slice.call(m, 1),
        named: m.groups || null
      });
      if (m[0] === '') re.lastIndex++;
      if (out.length >= MAX_MATCHES) break;
      if (++guard > MAX_MATCHES + 10) break;
    }
    return out;
  }

  /** 把测试文本里所有匹配标成金色 */
  function highlight(text, list, cap) {
    var out = '', last = 0, i;
    for (i = 0; i < list.length; i++) {
      var m = list[i];
      if (m.s < last) continue;
      out += esc(text.slice(last, m.s));
      out += m.e > m.s
        ? '<mark class="tl-rm">' + esc(text.slice(m.s, m.e)) + '</mark>'
        : '<mark class="tl-rm tl-rm0" title="这一处匹配到的是空"></mark>';
      last = m.e;
      if (i + 1 >= cap) {
        out += esc(text.slice(last));
        return { html: out + '<span class="tl-rm-more">… 后面还有 ' + (list.length - cap) + ' 处未标出</span>' };
      }
    }
    out += esc(text.slice(last));
    return { html: out };
  }

  /** RegExp 报错的英文原文翻成大白话（浏览器一定给英文，中文兜底永远轮不到） */
  var RE_ERR = [
    [/unterminated group|missing \)/i, '括号没配上对：有一个 `(` 没有对应的 `)`'],
    [/unmatched \)/i, '括号没配上对：多了一个 `)`'],
    [/unterminated character class/i, '方括号没配上对：有一个 `[` 没有对应的 `]`'],
    [/nothing to repeat/i, '重复符号（`*` `+` `?` `{n}`）前面没有东西可以重复，量词必须紧跟在一段内容后面'],
    [/invalid character class range/i, '方括号里的范围写反了，比如 `[z-a]`'],
    [/lone quantifier brackets/i, '`{` 后面不是合法的重复次数，要写成 `{3}`、`{2,}`、`{2,5}`'],
    [/invalid group/i, '分组写法不认得：`(?` 后面只能跟 `:`、`=`、`!`、`<=`、`<!`、`<名字>`'],
    [/invalid capture group name|invalid group name/i, '分组的名字不合法，只能用字母、数字、下划线，而且不能以数字开头'],
    [/duplicate capture group name/i, '有两个分组起了同一个名字'],
    [/escape at end of pattern|\\ at end of pattern/i, '正则结尾多了一个 `\\`，后面没有可以转义的字符'],
    [/numbers out of order/i, '`{n,m}` 里的数字写反了：前面的数不能大于后面的数'],
    [/invalid escape/i, '`\\` 后面跟的这个字符不合法（严格 Unicode 模式下尤其挑剔）'],
    [/invalid flags/i, '标志位不合法'],
    [/regular expression too large|too large/i, '这条正则太长，浏览器装不下'],
    [/too much recursion|stack overflow|out of memory/i, '这条正则写得太绕，浏览器算不动了。把嵌套的重复改简单一些再试'],
    [/invalid unicode escape|invalid unicode/i, '`\\u` 后面不是合法的 Unicode 编码']
  ];

  function regexErrCN(e) {
    var raw = (e && e.message) || '';
    for (var i = 0; i < RE_ERR.length; i++) {
      if (RE_ERR[i][0].test(raw)) return RE_ERR[i][1];
    }
    // 兜底：把 "Invalid regular expression: /xxx/: 原因" 这层壳剥掉，只留原因
    var tail = raw.replace(/^Invalid regular expression:\s*\/[\s\S]*?\/[a-z]*:\s*/i, '');
    return '这条正则不合法（浏览器原话）：' + (tail || raw || '没有更多信息');
  }

  /* ======================================================================
     3. 常用写法模板（点一下就填进正则，并配一段带该内容的示例文本）
     f 是这个模板需要的额外标志位，点的时候会一起勾上。
     ====================================================================== */
  var TPL = [
    { n: '手机号', re: '1[3-9]\\d{9}',
      t: '联系人：龙兄 13812345678，备用号 15900001111。\n座机是 0515-88886666，位数不一样，别混在一起。' },
    { n: '邮箱', re: '[\\w.%+-]+@[\\w-]+(?:\\.[\\w-]+)+',
      t: '有疑问发 longxiong@example.com，\n或抄送 admin@test.co.uk 一份。' },
    { n: '身份证号', re: '[1-9]\\d{5}(?:19|20)\\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]',
      t: '样例（号码虚构）：320921199003071234，\n校验位写成小写 x 的（32092119900307123x）也得认。' },
    { n: '日期（带分组）', re: '(\\d{4})-(\\d{2})-(\\d{2})',
      t: '开工 2026-09-18，验收 2026-10-08，\n中间还有个节点 2026-09-30。' },
    { n: '时间（时:分:秒）', re: '([01]\\d|2[0-3]):([0-5]\\d)(?::([0-5]\\d))?',
      t: '08:30 出门，13:05:20 开完会，\n23:59 之前必须提交。' },
    { n: '网址', re: 'https?://[^\\s\u4e00-\u9fa5，。]+',
      t: '参考 https://longxiong.vip/tools.html 这个页面，\n还有 http://example.com/a?b=1 这种带参数的。' },
    { n: '中文词句', re: '[\\u4e00-\\u9fa5]+',
      t: 'Mixed 混排 text：前面的汉字要抓出来，English 部分就不要了。' },
    { n: '金额（带千分位）', re: '\\d{1,3}(?:,\\d{3})*(?:\\.\\d{1,2})?',
      t: '本月支出 1,234.50 元，收入 12,000 元，\n结余 10765.5 元。' },
    { n: '重复的词（反向引用）', re: '\\b(\\w+)\\s+\\1\\b',
      t: 'This is is a test.\nthe the quick brown fox\nWARN WARN 这种情况也常见。' },
    { n: '行首缩进（多行）', re: '^[ \\t]+', f: 'm',
      t: 'function a() {\n    return 1;\n}\n这一行顶格写' },
    { n: '空行（多行）', re: '^[ \\t]*$', f: 'm',
      t: '第一段\n\n第二段\n   \n第三段' },
    { n: '日志级别', re: '\\b(ERROR|WARN|INFO)\\b',
      t: '2026-09-18 10:01 INFO 启动完成\n2026-09-18 10:02 WARN 磁盘将满\n2026-09-18 10:03 ERROR 连接超时' },
    { n: '括号里的内容', re: '\\(([^()]*)\\)',
      t: '会议(周一下午两点)改到(周三上午)，\n地点仍是(三楼会议室)。' }
  ];

  /* ======================================================================
     4. 装配
     ====================================================================== */
  function setupRegex() {
    var P = panelOf('regex');
    if (!P) return;

    var hlBox = P.querySelector('[data-hl]');
    var listBox = P.querySelector('[data-mlist]');
    var expBox = P.querySelector('[data-explain]');
    var warnBox = P.querySelector('[data-warn]');
    var repBox = P.querySelector('[data-rep]');
    var tplBox = P.querySelector('[data-tpls]');
    var lastReport = '';
    var lastDemo = '';        // 上一次由模板填进去的示例文本

    function flags() {
      return 'g' + (valOf(P, 'i') ? 'i' : '') + (valOf(P, 'm') ? 'm' : '') +
        (valOf(P, 's') ? 's' : '') + (valOf(P, 'u') ? 'u' : '');
    }
    function flagText() {
      var names = [];
      if (valOf(P, 'i')) names.push('忽略大小写');
      if (valOf(P, 'm')) names.push('^ $ 按每一行算');
      if (valOf(P, 's')) names.push('. 也匹配换行');
      if (valOf(P, 'u')) names.push('严格 Unicode');
      return names.length ? names.join('、') : '默认（区分大小写，^ $ 只管整段的开头结尾）';
    }

    function clearResults() {
      if (hlBox) { hlBox.className = 'tl-rxhl is-ph'; hlBox.textContent = '上面填好正则和测试文本，匹配到的内容会在这里标出来。'; }
      if (listBox) listBox.innerHTML = '';
      if (expBox) expBox.innerHTML = '';
      if (warnBox) warnBox.innerHTML = '';
      if (repBox) { repBox.className = 'tl-rxhl is-ph'; repBox.textContent = '在「替换预览」里填上替换式，这里会显示替换后的文本。'; }
      setStat(P, null);
      lastReport = '';
    }

    function renderExplain(ex) {
      if (!expBox) return;
      var html = '';
      ex.parts.slice(0, SHOW_PARTS).forEach(function (p) {
        html += '<div class="tl-rxpr"><span class="tl-rxpc">' + esc(p.raw) + '</span>' +
          '<span class="tl-rxpd">' + esc(p.desc) + '</span></div>';
      });
      if (ex.parts.length > SHOW_PARTS) {
        html += '<div class="tl-rxpr"><span class="tl-rxpc">…</span><span class="tl-rxpd">' +
          '后面的 ' + (ex.parts.length - SHOW_PARTS) + ' 段没列出来（正则太长了）。</span></div>';
      }
      expBox.innerHTML = html;
      if (warnBox) {
        warnBox.innerHTML = ex.warns.slice(0, 6).map(function (s) {
          return '<div>' + esc(s) + '</div>';
        }).join('');
      }
    }

    /** 只有真的会遇到、且光看正则看不出来的情况才提醒 */
    function contextWarns(ex, text, pattern) {
      var extra = [], f = flags();
      if (ex.hasB && /[\u4e00-\u9fa5]/.test(text)) {
        extra.push('正则里有 `\\b`（词边界），但 `\\b` 只认英文字母数字，汉字旁边通常找不到边界。要在中文里卡位置，用 `(?<=…)` 或 `(?<!)` 更合适。');
      }
      if (pattern.indexOf('.') >= 0 && f.indexOf('s') < 0 && text.indexOf('\n') >= 0) {
        extra.push('测试文本里有换行，而 `.` 默认不匹配换行。要让 `.` 连换行一起吃，勾上「. 也匹配换行（s）」。');
      }
      if (/[\^$]/.test(pattern) && f.indexOf('m') < 0 && text.indexOf('\n') >= 0) {
        extra.push('正则里用了 `^` 或 `$`，现在只认整段文字的开头和结尾。想让它按每一行算，勾上「^ $ 按每一行算（m）」。');
      }
      return extra;
    }

    /** 把替换式里的 $1 / $& / $<名字> 展开（\n \t \r \\ 也顺手还原） */
    function expandReplacement(rep, args) {
      var mstr = args[0], groups = args.groups || {};
      return rep.replace(/\$(\$|&|\d{1,2}|<[^>]+>)/g, function (mm, g) {
        if (g === '$') return '$';
        if (g === '&') return mstr;
        if (/^\d+$/.test(g)) {
          var v = args[+g];
          return v === undefined ? '' : v;
        }
        var key = g.slice(1, -1);
        return groups[key] === undefined ? '' : groups[key];
      });
    }

    function buildReport(pattern, fl, text, list, ex, repCount, repText) {
      var L = [];
      L.push('正则：/' + pattern + '/' + fl.slice(1));
      L.push('测试文本：共 ' + text.length + ' 个字符');
      L.push('匹配到 ' + list.length + ' 处');
      L.push('');
      list.slice(0, SHOW_ROWS).forEach(function (m, i) {
        var line = '#' + (i + 1) + '  [' + m.s + '–' + m.e + ']  ' + JSON.stringify(m.text);
        if (m.groups.length) {
          line += '   分组：' + m.groups.map(function (g, gi) {
            return (gi + 1) + '=' + (g === undefined ? '(没抓到)' : JSON.stringify(g));
          }).join(' ');
        }
        L.push(line);
      });
      L.push('');
      L.push('—— 这条正则说的是什么 ——');
      ex.parts.forEach(function (p) { L.push(p.raw + '    ' + p.desc); });
      ex.warns.forEach(function (w) { L.push('提示：' + w.replace(/`/g, '')); });
      if (repCount) {
        L.push('');
        L.push('—— 替换后（' + repCount + ' 处）——');
        L.push(repText);
      }
      return L.join('\n');
    }

    function run() {
      var pattern = String(valOf(P, 're') == null ? '' : valOf(P, 're'));
      var text = String(valOf(P, 'tx') == null ? '' : valOf(P, 'tx'));
      var rep = String(valOf(P, 'rp') == null ? '' : valOf(P, 'rp'));

      if (!pattern) { clearToast(P); clearResults(); return; }

      if (!text) {
        clearToast(P);
        clearResults();
        renderExplain(explainRegex(pattern));
        toast(P, '正则记下了。再把要检查的文字贴到「测试文本」里，就能看到匹配结果。', 'ok');
        return;
      }

      var re;
      try {
        re = new RegExp(pattern, flags());
      } catch (e) {
        clearToast(P);
        clearResults();
        toast(P, regexErrCN(e), 'err');
        renderExplain(explainRegex(pattern));
        return;
      }
      clearToast(P);

      var t0 = (window.performance && performance.now) ? performance.now() : Date.now();
      var list;
      try {
        list = matchAll(re, text);
      } catch (e2) {
        toast(P, '这条正则在匹配的时候出错了：' + regexErrCN(e2), 'err');
        return;
      }
      var ms = ((window.performance && performance.now) ? performance.now() : Date.now()) - t0;

      /* ---- 高亮 ---- */
      if (hlBox) {
        if (!list.length) {
          hlBox.className = 'tl-rxhl is-ph';
          hlBox.textContent = '一处都没匹配上。检查一下正则，或者看看下面列出的提示。';
        } else if (text.length > MAX_HL) {
          hlBox.className = 'tl-rxhl is-ph';
          hlBox.textContent = '测试文本有 ' + text.length + ' 个字符，太长就不整段高亮了（明细表照常给出）。';
        } else {
          hlBox.className = 'tl-rxhl';
          hlBox.innerHTML = highlight(text, list, 500).html;
        }
      }

      /* ---- 明细表 ---- */
      if (listBox) {
        if (!list.length) listBox.innerHTML = '';
        else {
          var html = '';
          list.slice(0, SHOW_ROWS).forEach(function (m, i) {
            var chips = '';
            if (m.named) {
              Object.keys(m.named).forEach(function (k) {
                chips += '<span class="tl-rxg"><b>' + esc(k) + '</b> ' +
                  (m.named[k] === undefined ? '（没抓到）' : esc(m.named[k])) + '</span>';
              });
            }
            m.groups.forEach(function (g, gi) {
              chips += '<span class="tl-rxg"><b>' + (gi + 1) + '</b> ' +
                (g === undefined ? '没抓到' : '「' + esc(g) + '」') + '</span>';
            });
            if (!chips) chips = '<span class="tl-rxg tl-rxg0">没有分组</span>';
            html += '<div class="tl-rxrow"><span class="tl-rxi">#' + (i + 1) + '</span>' +
              '<span class="tl-rxm">' + (m.text === '' ? '<i>（这一处匹配到的是空）</i>' : esc(m.text)) + '</span>' +
              '<span class="tl-rxp">' + chips + '</span></div>';
          });
          if (list.length > SHOW_ROWS) {
            html += '<div class="tl-dmore">还有 ' + (list.length - SHOW_ROWS) + ' 处没列出来</div>';
          }
          listBox.innerHTML = html;
        }
      }

      /* ---- 逐段解释 ---- */
      var ex = explainRegex(pattern);
      ex.warns = ex.warns.concat(contextWarns(ex, text, pattern));
      renderExplain(ex);

      /* ---- 替换预览 ---- */
      var repCount = 0, repText = '';
      if (repBox) {
        if (!rep) {
          repBox.className = 'tl-rxhl is-ph';
          repBox.textContent = '在「替换预览」里填上替换式，这里会显示替换后的文本。';
        } else {
          var repExpanded = rep.replace(/\\\\/g, '\u0000').replace(/\\n/g, '\n')
            .replace(/\\t/g, '\t').replace(/\\r/g, '\r').replace(/\u0000/g, '\\');
          if (text.length > MAX_HL) {
            repBox.className = 'tl-rxhl is-ph';
            repBox.textContent = '测试文本太长，就不做替换预览了。';
          } else {
            repText = text.replace(re, function () {
              repCount++;
              return expandReplacement(repExpanded, arguments);
            });
            repBox.className = 'tl-rxhl' + (repCount ? '' : ' is-ph');
            repBox.textContent = repCount ? repText : '按这个替换式换下来，一处都没变。';
          }
        }
      }

      /* ---- 统计 ---- */
      var gcount = list.length ? list[0].groups.length : 0;
      var cells = [
        ['匹配到', list.length + ' 处'],
        ['分组', gcount ? gcount + ' 个' : '没有'],
        ['用时', ms < 1 ? '不到 1 ms' : ms.toFixed(0) + ' ms'],
        ['第一处位置', list.length ? (list[0].s + '–' + list[0].e) : '—']
      ];
      if (ex.parts.length) cells.push(['正则段数', ex.parts.length + ' 段']);
      var note = [];
      if (ex.sentence) note.push('<b>一句话：</b>' + esc(ex.sentence) + '。');
      note.push('标志：' + esc(flagText()) + '。');
      if (list.length >= MAX_MATCHES) note.push('匹配超过 ' + MAX_MATCHES + ' 处，只统计到这儿。');
      setStat(P, cells, note.join(' '));

      lastReport = buildReport(pattern, flags(), text, list, ex, repCount, repText);
    }

    var timer = 0;
    function schedule() {
      clearTimeout(timer);
      timer = setTimeout(run, 220);
    }

    ['re', 'tx', 'rp'].forEach(function (name) {
      var el = P.querySelector('[data-in="' + name + '"]');
      if (el) el.addEventListener('input', schedule);
    });
    ['i', 'm', 's', 'u'].forEach(function (name) {
      var el = P.querySelector('[data-in="' + name + '"]');
      if (el) el.addEventListener('change', run);
    });

    if (tplBox) {
      tplBox.innerHTML = TPL.map(function (t, i) {
        return '<button class="tl-chip" type="button" data-tpl="' + i + '">' + esc(t.n) + '</button>';
      }).join('');
      $$('[data-tpl]', tplBox).forEach(function (b) {
        b.addEventListener('click', function () {
          var t = TPL[+b.getAttribute('data-tpl')];
          if (!t) return;
          setVal('re', t.re);
          // 模板自己带的标志位（比如「行首缩进」必须开多行模式才有效）
          ['i', 'm', 's', 'u'].forEach(function (k) {
            var el = P.querySelector('[data-in="' + k + '"]');
            if (el) el.checked = t.f ? t.f.indexOf(k) >= 0 : false;
          });
          var cur = String(valOf(P, 'tx') || '');
          if (!cur || cur === lastDemo) {          // 别把人家辛苦贴进来的文本冲掉
            setVal('tx', t.t);
            lastDemo = t.t;
          }
          $$('[data-tpl]', tplBox).forEach(function (x) { x.classList.remove('on'); });
          b.classList.add('on');
          run();
        });
      });
    }

    function setVal(name, v) {
      var el = P.querySelector('[data-in="' + name + '"]');
      if (!el) return;
      if (el.type === 'checkbox') el.checked = !!v;
      else el.value = v == null ? '' : String(v);
    }

    var ACTS = {
      run: run,
      copy: function () {
        if (!lastReport) { toast(P, '先填正则和测试文本，有结果了才能复制。', 'err'); return; }
        copyText(lastReport).then(function () {
          toast(P, '匹配结果和逐段解释都复制到剪贴板了。', 'ok');
        }, function (e) {
          toast(P, (e && e.message) || '这个浏览器不允许自动复制，请手动选中。', 'err');
        });
      },
      clear: function () {
        ['re', 'tx', 'rp'].forEach(function (n) { setVal(n, ''); });
        ['i', 'm', 's', 'u'].forEach(function (n) { setVal(n, false); });
        lastDemo = '';
        clearToast(P);
        clearResults();
        if (tplBox) $$('[data-tpl]', tplBox).forEach(function (x) { x.classList.remove('on'); });
      }
    };

    $$('[data-act]', P).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var fn = ACTS[btn.getAttribute('data-act')];
        if (fn) fn();
      });
    });

    // 首次进来留个空面板的样子（不要一片空白，也不要乱报错）
    clearResults();
  }

  window.LXTools.define('regex', setupRegex);
})();
