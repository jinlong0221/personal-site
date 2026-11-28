/*!
 * tools/json.js — JSON 智能修复台（工具箱·按需加载子模块）
 *
 * 谁都有过这种时候：从日志里、从配置文件里、从聊天记录里抠出来一段 JSON，
 * 粘进程序就报错，可它到底哪错了，报错信息只给你一个看不懂的 position。
 *
 * 这个小工具的做法是：不猜、不装作看懂了，而是**逐条列出它改了什么**——
 *   · 多余/缺失的逗号、单引号、字段名没加引号、夹着注释、True/None 这种别的语言写法、
 *     全角标点、.5 这种数字写法、括号少了一个、好几段 JSON 拼在一起……
 * 每改一处都记一笔，你能自己判断改得对不对。三步走：
 *   一段一段清洗 → 洗到能解析 → 再交给你格式化 / 折叠看 / 按路径取值 / 转表格。
 * 全部在本机算：贴进来的东西一个字节都不会离开浏览器，粘密钥、粘用户数据都放心。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $$ = _.$$;
  var bindSeg = _.bindSeg, copyText = _.copyText, download = _.download,
      esc = _.esc, panelOf = _.panelOf, setStat = _.setStat, valOf = _.valOf;

  var MAX_TEXT = 4000000;      // 超过这么多字符就不折腾了
  var MAX_TREE = 4000;         // 树形最多画这么多节点
  var MAX_CSV_ROWS = 20000;    // 转表格最多这么多行

  /* ======================================================================
     1. 分段：把「字符串里面」和「字符串外面」分开
     这是整个修复流程的地基 —— 只有分清内外，才不会把中文字符串里的逗号也当成分隔符改掉
     ====================================================================== */
  function segments(s) {
    var segs = [], i = 0, n = s.length, cur = '', inStr = false;
    while (i < n) {
      var c = s.charAt(i);
      if (inStr) {
        if (c === '\\') { cur += c + (s.charAt(i + 1) || ''); i += 2; continue; }
        if (c === '"') { cur += '"'; i++; inStr = false; segs.push({ str: true, text: cur }); cur = ''; continue; }
        cur += c; i++; continue;
      }
      if (c === '"') { if (cur) segs.push({ str: false, text: cur }); cur = '"'; i++; inStr = true; continue; }
      cur += c; i++;
    }
    if (cur) segs.push({ str: inStr, text: cur });
    return segs;
  }

  /** 只对「字符串外面」的片段做处理，字符串内容原样保留 */
  function outsideMap(s, fn) {
    var segs = segments(s), out = [], i;
    for (i = 0; i < segs.length; i++) out.push(segs[i].str ? segs[i].text : fn(segs[i].text));
    return out.join('');
  }

  /* ======================================================================
     2. 逐趟清洗：每一趟都记录改了什么
     ====================================================================== */
  function noteAdd(notes, key, n, text) {
    if (!n) return;
    if (!notes[key]) notes[key] = { title: key, n: 0, text: text };
    notes[key].n += n;
  }

  function notesToArr(notes) {
    return Object.keys(notes).map(function (k) { return notes[k]; });
  }

  /** 不可见字符：BOM、零宽空格、不间断空格 */
  function stripInvisible(s) {
    var n = 0;
    var out = s.replace(/[\uFEFF\u200B\u200C\u200D]/g, function () { n++; return ''; })
      .replace(/\u00A0/g, function () { n++; return ' '; });
    return { text: out, n: n };
  }

  var FW = {
    '，': ',', '：': ':', '；': ';', '｛': '{', '｝': '}', '［': '[', '］': ']',
    '（': '(', '）': ')', '　': ' ', '＝': '=', '．': '.',
    '\uff10': '0', '\uff11': '1', '\uff12': '2', '\uff13': '3', '\uff14': '4',
    '\uff15': '5', '\uff16': '6', '\uff17': '7', '\uff18': '8', '\uff19': '9'
  };

  /**
   * 主清洗：一次扫过去，把引号统一、注释去掉、全角标点摆正、字符串里的裸换行转义。
   * 之所以要一趟趟扫而不是一把 replace，就是因为每做一步都可能改变「现在是不是在字符串里」。
   */
  function normalizePass(s) {
    var out = '', i = 0, n = s.length, quote = '', inStr = false;
    var cnt = { 引号: 0, 注释: 0, 全角: 0, 换行: 0 };
    while (i < n) {
      var c = s.charAt(i);

      if (!inStr) {
        if (c === '"') { out += '"'; inStr = true; quote = '"'; i++; continue; }
        if (c === '\u201c' || c === '\u201d') {        // 中文左/右双引号
          out += '"'; cnt.引号++;
          if (c === '\u201c') { inStr = true; quote = '\u201d'; }
          i++; continue;
        }
        if (c === '\u2018' || c === '\u2019') {        // 中文左/右单引号
          out += '"'; cnt.引号++;
          if (c === '\u2018') { inStr = true; quote = '\u2019'; }
          i++; continue;
        }
        if (c === "'") { out += '"'; inStr = true; quote = "'"; cnt.引号++; i++; continue; }
        if (c === '/' && s.charAt(i + 1) === '/') {    // 行注释
          while (i < n && s.charAt(i) !== '\n') i++;
          cnt.注释++; continue;
        }
        if (c === '/' && s.charAt(i + 1) === '*') {    // 块注释
          i += 2;
          while (i < n && !(s.charAt(i) === '*' && s.charAt(i + 1) === '/')) i++;
          i += 2; cnt.注释++; continue;
        }
        if (FW[c] !== undefined) { out += FW[c]; cnt.全角++; i++; continue; }
        out += c; i++; continue;
      }

      // —— 以下都在字符串内部 ——
      if (c === '\\') {
        var nx = s.charAt(i + 1);
        if (quote === "'") {
          if (nx === "'") { out += "'"; i += 2; continue; }        // \' 在双引号串里不用转义
          if (nx === '"') { out += '\\"'; i += 2; continue; }
        }
        out += '\\' + nx; i += 2; continue;
      }
      if (c === quote) { out += '"'; inStr = false; i++; continue; }
      if (c === '"') { out += '\\"'; i++; continue; }              // 单引号串里夹着双引号
      if (c === '\n') { out += '\\n'; cnt.换行++; i++; continue; }
      if (c === '\r') { out += '\\r'; cnt.换行++; i++; continue; }
      if (c === '\t') { out += '\\t'; cnt.换行++; i++; continue; }
      out += c; i++; continue;
    }
    return { text: out, cnt: cnt };
  }

  /** 别的语言写法的值：True / None / NaN / undefined / Infinity */
  var VAL_FIX = [
    [/\bTrue\b/g, 'true', 'Python 写法的 True'],
    [/\bFalse\b/g, 'false', 'Python 写法的 False'],
    [/\bNone\b/g, 'null', 'Python 写法的 None'],
    [/\bTRUE\b/g, 'true', '大写的 TRUE'],
    [/\bFALSE\b/g, 'false', '大写的 FALSE'],
    [/\bNULL\b/g, 'null', '大写的 NULL'],
    [/\bundefined\b/g, 'null', 'undefined（JSON 里没有这个值）'],
    [/\bNaN\b/g, 'null', 'NaN（JSON 不支持这种数）'],
    [/\b[-+]?Infinity\b/g, 'null', 'Infinity（JSON 不支持这种数）'],
    [/\bnil\b/g, 'null', 'Ruby 写法的 nil']
  ];

  function fixValues(s) {
    var n = 0;
    var out = outsideMap(s, function (chunk) {
      for (var i = 0; i < VAL_FIX.length; i++) {
        chunk = chunk.replace(VAL_FIX[i][0], function () { n++; return VAL_FIX[i][1]; });
      }
      return chunk;
    });
    return { text: out, n: n };
  }

  /** 数字写法：.5 → 0.5、1. → 1.0、0x1F → 31、1_000 → 1000、+1 → 1 */
  function fixNumbers(s) {
    var n = 0;
    var out = outsideMap(s, function (chunk) {
      chunk = chunk.replace(/\b0[xX]([0-9a-fA-F]+)\b/g, function (m, h) { n++; return String(parseInt(h, 16)); });
      chunk = chunk.replace(/\b0[oO]([0-7]+)\b/g, function (m, o) { n++; return String(parseInt(o, 8)); });
      chunk = chunk.replace(/(\d)_(?=\d)/g, function (m, d) { n++; return d; });
      chunk = chunk.replace(/(^|[^\w."])\.(\d)/g, function (m, pre, d) { n++; return pre + '0.' + d; });
      chunk = chunk.replace(/(\d)\.(?=[^\d]|$)/g, function (m, d) { n++; return d + '.0'; });
      chunk = chunk.replace(/(^|[^\w.":])[-+]?\+(\d)/g, function (m, pre, d) { n++; return pre + d; });
      return chunk;
    });
    return { text: out, n: n };
  }

  /** 字段名没加引号：{a: 1} → {"a": 1} */
  function quoteKeys(s) {
    var n = 0;
    var out = outsideMap(s, function (chunk) {
      return chunk.replace(/([{\[,]\s*)([A-Za-z_$][A-Za-z0-9_$]*)(\s*:)/g, function (m, pre, key, post) {
        n++; return pre + '"' + key + '"' + post;
      });
    });
    return { text: out, n: n };
  }

  /** 多余的尾逗号：,} 与 ,]（连着写两个逗号也要一并收拾干净，所以要反复跑到不动为止） */
  function dropTrailingCommas(s) {
    var n = 0, prev = null, round = 0;
    while (prev !== s && round < 20) {
      prev = s; round++;
      s = outsideMap(s, function (chunk) {
        return chunk.replace(/,(\s*[}\]])/g, function (m, tail) { n++; return tail; });
      });
    }
    return { text: s, n: n };
  }

  /** 一串逗号连写：,, → , */
  function collapseCommas(s) {
    var n = 0;
    var out = outsideMap(s, function (chunk) {
      return chunk.replace(/,(\s*,)+/g, function () { n++; return ','; });
    });
    return { text: out, n: n };
  }

  /**
   * 缺逗号："a":1 "b":2 / [1 2 3]。
   * 做法是按「记号」扫，一个值记号紧跟着另一个值记号，中间就该有个逗号。
   * 之所以不一把 replace 了事，是因为数字、true/false/null 这类要整体识别，
   * 否则 1e5 里的 e 会被误判成"上一个值结束了"。
   */
  function insertMissingCommas(s) {
    var out = '', i = 0, n = s.length, cnt = 0, prevEnd = false, any = false;
    while (i < n) {
      var c = s.charAt(i);
      if (c === ' ' || c === '\n' || c === '\t' || c === '\r') { out += c; i++; continue; }
      var start = i, tok = '', end = false;
      if (c === '"') {
        i++;
        while (i < n) {
          if (s.charAt(i) === '\\') { i += 2; continue; }
          if (s.charAt(i) === '"') { i++; break; }
          i++;
        }
        tok = s.slice(start, i); end = true;
      } else if (c === '{' || c === '[' || c === ',' || c === ':') {
        tok = c; i++; end = false;
      } else if (c === '}' || c === ']') {
        tok = c; i++; end = true;
      } else {
        var m = /^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?|^[A-Za-z_$][A-Za-z0-9_$.]*/.exec(s.slice(i));
        if (m && m[0]) { tok = m[0]; i += m[0].length; end = true; }
        else { tok = c; i++; end = true; }
      }
      var startsValue = /^["{\[]/.test(tok) || /^[-+]?[\d.]/.test(tok) || /^[A-Za-z_$]/.test(tok);
      if (any && prevEnd && startsValue) { out += ','; cnt++; }
      out += tok;
      prevEnd = end;
      any = true;
    }
    return { text: out, n: cnt };
  }

  /** 括号配平：少补、多报、配错报 */
  function balanceBrackets(s) {
    var st = [], i, inStr = false;
    for (i = 0; i < s.length; i++) {
      var c = s.charAt(i);
      if (inStr) {
        if (c === '\\') { i++; continue; }
        if (c === '"') inStr = false;
        continue;
      }
      if (c === '"') { inStr = true; continue; }
      if (c === '{' || c === '[') st.push(c);
      else if (c === '}' || c === ']') {
        var o = st.pop();
        if (!o) return { text: s, n: 0, bad: '多了一个 `' + c + '`，前面没有和它配对的 ' + (c === '}' ? '`{`' : '`[`') };
        if ((c === '}') !== (o === '{')) return { text: s, n: 0, bad: '括号配错了：`' + o + '` 配上了 `' + c + '`' };
      }
    }
    if (inStr) return { text: s, n: 0, bad: '有一处引号没有收尾' };
    if (!st.length) return { text: s, n: 0, bad: '' };
    var add = '';
    for (i = st.length - 1; i >= 0; i--) add += st[i] === '{' ? '}' : ']';
    return { text: s + add, n: st.length, bad: '', add: add };
  }

  /** 整段就是一个对象体（缺外层花括号）："a":1,"b":2 → { ... } */
  function wrapBareObject(s) {
    var t = s.replace(/^\s+/, '');
    if (/^"[^"]*"\s*:/.test(t)) return { text: '{' + s + '}', n: 1 };
    return { text: s, n: 0 };
  }

  /* ======================================================================
     3. 修复主流程
     ====================================================================== */

  /**
   * @returns {{ok:boolean, text:string, notes:Array, value:any, bad:string,
   *            errLine:number, errCol:number, snippet:string}}
   */
  function repairJson(raw) {
    var notes = [];
    var s = String(raw == null ? '' : raw);
    if (s.length > MAX_TEXT) {
      return { ok: false, text: s, notes: [], value: undefined,
        bad: '内容超过 ' + Math.round(MAX_TEXT / 10000) + ' 万字，先裁小一点再试。' };
    }

    var r = stripInvisible(s);
    noteAdd(notes, '看不见的字符', r.n, 'BOM、零宽空格这类看不见的字符，去掉不影响内容');
    s = r.text;

    var np = normalizePass(s);
    noteAdd(notes, '引号', np.cnt.引号, '把中文引号或单引号换成了标准的英文双引号（JSON 只认双引号）');
    noteAdd(notes, '注释', np.cnt.注释, '去掉了注释 —— JSON 标准里没有注释这种东西');
    noteAdd(notes, '全角标点', np.cnt.全角, '全角的逗号、冒号、括号换成了半角');
    noteAdd(notes, '字符串里的换行', np.cnt.换行, '字符串里的换行、制表符改成了 \\n \\t 转义写法');
    s = np.text;

    // 先看是不是好几段 JSON 拼在一起（每行一段）。这一步必须抢在"补逗号"前面：
    // 补逗号会把几段之间的换行缝成一个大数组，再想分开就晚了。
    var jl0 = tryJsonLines(s);
    if (jl0) {
      noteAdd(notes, '拼接的多个 JSON', jl0.length,
        '看起来是 ' + jl0.length + ' 段 JSON 拼在一起，已经包成一个数组');
      return {
        ok: true, text: JSON.stringify(jl0, null, 2), notes: notesToArr(notes), value: jl0,
        before: raw, after: s
      };
    }

    r = quoteKeys(s);
    noteAdd(notes, '字段名没加引号', r.n, '给没加引号的字段名补上了双引号');
    s = r.text;

    r = fixValues(s);
    noteAdd(notes, '别的语言写法的值', r.n, 'True / None / NaN / undefined 这类值换成了 JSON 的 null 或 true/false');
    s = r.text;

    r = fixNumbers(s);
    noteAdd(notes, '数字写法', r.n, '把 .5、1.、0x1F、1_000 这类写法改成了普通的十进制数字');
    s = r.text;

    r = insertMissingCommas(s);
    noteAdd(notes, '缺少逗号', r.n, '两个值之间少了逗号，补上了');
    s = r.text;

    r = dropTrailingCommas(s);
    noteAdd(notes, '多余的逗号', r.n, '最后一项后面多了一个逗号，删掉了（JSON 不允许尾逗号）');
    s = r.text;

    r = collapseCommas(s);
    noteAdd(notes, '重复的逗号', r.n, '连着写了两个逗号，合并成一个');
    s = r.text;

    r = wrapBareObject(s);
    noteAdd(notes, '缺外层花括号', r.n, '这段内容是一堆字段，但没套上最外层的 { }');
    s = r.text;

    r = balanceBrackets(s);
    if (r.n) {
      noteAdd(notes, '括号补齐', r.n, '末尾少了的 ' + r.add + '，补上了' +
        ' —— 补出来的部分请自己核对一下是不是想要的');
      s = r.text;
    }

    // 先试着解析
    var value, ok = false, bad = r.bad || '';
    try { value = JSON.parse(s); ok = true; } catch (e) { bad = bad || e.message; }

    // 还不行的话，看看是不是好几段 JSON 拼在一起（每行一段，而且每行自己也有毛病）
    if (!ok) {
      var jl = [];
      var lines = s.split('\n').map(function (l) { return l.replace(/^\s+|\s+$/g, ''); })
        .filter(function (l) { return l; });
      if (lines.length > 1) {
        var allOk = true;
        for (var li = 0; li < lines.length; li++) {
          var one = repairJson(lines[li]);
          if (!one.ok) { allOk = false; break; }
          jl.push(one.value);
        }
        if (allOk) {
          noteAdd(notes, '拼接的多个 JSON', jl.length,
            '看起来是 ' + jl.length + ' 段 JSON 拼在一起，已经包成一个数组');
          return {
            ok: true, text: JSON.stringify(jl, null, 2), notes: notesToArr(notes), value: jl,
            before: raw, after: s
          };
        }
      }
    }

    // 再不行，看是不是缺最外层花括号（上面补过 {} 但风格可能不对）
    if (!ok) {
      var wrapped = dropTrailingCommas(quoteKeys('{' + s + '}').text).text;
      try {
        value = JSON.parse(wrapped);
        noteAdd(notes, '缺外层花括号', 1, '外面补了一对 { } 才成了一段完整的对象');
        s = wrapped; ok = true;
      } catch (e2) { /* 还是不行就算了 */ }
    }

    var notesArr = notesToArr(notes);
    if (!ok) {
      var pe = parseErrorCN(bad, s);
      return { ok: false, text: s, notes: notesArr, value: undefined,
        bad: pe.msg, errLine: pe.line, errCol: pe.col, snippet: pe.snippet,
        before: raw, after: s, rawMsg: bad };
    }
    return { ok: true, text: s, notes: notesArr, value: value, before: raw, after: s };
  }

  /** 好几段 JSON 拼在一起（每行一段） */
  function tryJsonLines(s) {
    var lines = s.split('\n').map(function (l) { return l.replace(/^\s+|\s+$/g, ''); })
      .filter(function (l) { return l; });
    if (lines.length < 2) return null;
    var vals = [];
    for (var i = 0; i < lines.length; i++) {
      try { vals.push(JSON.parse(lines[i])); } catch (e) { return null; }
    }
    return vals;
  }

  /** 把浏览器给的英文报错翻译成人话，并指出是第几行第几列、附近长什么样 */
  var PERR = [
    [/unexpected end of json input|unexpected end of input/i, '内容到一半就断了：括号或者引号没闭合'],
    [/unexpected token/i, '这里冒出来一个不该出现的符号'],
    [/expected property name or|property name expected/i, '这里应该是一个用双引号括起来的字段名'],
    [/expected ',' or '}' after property value/i, '这个字段的值后面少了一个逗号，或者少了一个右花括号'],
    [/expected ',' or ']' after array element/i, '这个数组元素后面少了一个逗号，或者少了一个右方括号'],
    [/expected ':' after property name/i, '字段名后面少了冒号'],
    [/expected double-quoted property name/i, '字段名必须用双引号括起来'],
    [/bad escaped character|bad escape/i, '字符串里有一个不合法的转义写法'],
    [/unterminated string/i, '有一处引号没有收尾'],
    [/unexpected non-whitespace character after json/i, '一段 JSON 结束了，后面还有多余的内容（可能是好几段拼在一起）'],
    [/no number after minus sign/i, '减号后面没有数字'],
    [/unexpected number in json/i, '数字写法不对'],
    [/invalid unicode escape/i, '\\u 后面不是合法的 Unicode 编码']
  ];

  function parseErrorCN(msg, text) {
    var m = (msg || '').toString();
    var posM = /position (\d+)/i.exec(m);
    var idx = posM ? parseInt(posM[1], 10) : -1;
    var lcM = /line (\d+) column (\d+)/i.exec(m);
    var line = 1, col = 1;
    if (lcM) { line = parseInt(lcM[1], 10); col = parseInt(lcM[2], 10); }
    else if (idx >= 0) {
      var head = text.slice(0, idx);
      line = head.split('\n').length;
      col = idx - head.lastIndexOf('\n');
    }
    var friendly = '';
    for (var i = 0; i < PERR.length; i++) {
      if (PERR[i][0].test(m)) { friendly = PERR[i][1]; break; }
    }
    if (!friendly) friendly = '浏览器说不认识这段内容：' + m.replace(/^JSON\.parse:\s*/i, '');
    var snippet = '';
    if (idx >= 0 || lcM) {
      var ls = text.split('\n');
      var li = Math.max(0, line - 1);
      var shown = ls[li] === undefined ? '' : ls[li];
      if (shown.length > 160) {
        var from = Math.max(0, col - 60);
        shown = (from ? '…' : '') + shown.slice(from, from + 160);
        col = col - from + (from ? 1 : 0);
      }
      snippet = '第 ' + line + ' 行：' + shown + '\n' + new Array(Math.max(1, col) + 2).join(' ') + '↑';
    } else {
      // 不知道具体位置（比如引号没闭合这种），就把最后一行摆出来——问题多半在那儿
      var ls2 = text.split('\n');
      var k = ls2.length - 1;
      while (k > 0 && !ls2[k].replace(/\s/g, '')) k--;
      var one = ls2[k] || '';
      if (one.length > 200) one = one.slice(0, 200) + '…';
      line = k + 1;
      snippet = '第 ' + line + ' 行：' + one + '\n（问题多半在这一段附近）';
    }
    return { msg: friendly, line: line, col: col, snippet: snippet };
  }

  /* ======================================================================
     4. 修好之后：排序、看结构、取值、转表格
     ====================================================================== */
  function sortDeep(v) {
    if (Array.isArray(v)) return v.map(sortDeep);
    if (v && typeof v === 'object') {
      var o = {};
      Object.keys(v).sort().forEach(function (k) { o[k] = sortDeep(v[k]); });
      return o;
    }
    return v;
  }

  /** 数一数有多少节点、嵌套多少层（层级只数"容器"，最里面的值不算一层） */
  function statsOf(v) {
    var nodes = 0, depth = 0;
    (function walk(x, d) {
      nodes++;
      var isC = Array.isArray(x) || (x !== null && typeof x === 'object');
      if (isC && d > depth) depth = d;
      if (Array.isArray(x)) { for (var i = 0; i < x.length; i++) walk(x[i], d + 1); }
      else if (isC) {
        var ks = Object.keys(x);
        for (var k = 0; k < ks.length; k++) walk(x[ks[k]], d + 1);
      }
    })(v, 1);
    return { nodes: nodes, depth: depth };
  }

  function typeName(v) {
    if (v === null) return '空值';
    if (Array.isArray(v)) return '数组（' + v.length + ' 项）';
    if (typeof v === 'object') return '对象（' + Object.keys(v).length + ' 个字段）';
    if (typeof v === 'string') return '文字';
    if (typeof v === 'number') return '数字';
    if (typeof v === 'boolean') return '是/否';
    return typeof v;
  }

  /** 路径写法：a.b / a[0] / a[*] / a[*].b / $ 开头也行 */
  function splitPath(path) {
    var s = String(path == null ? '' : path).replace(/^\s+|\s+$/g, '');
    if (s === '' || s === '$') return [];
    s = s.replace(/^\$/, '');
    var steps = [], i = 0;
    while (i < s.length) {
      var c = s.charAt(i);
      if (c === '.') { i++; continue; }
      if (c === '[') {
        var j = s.indexOf(']', i);
        if (j < 0) break;
        var inner = s.slice(i + 1, j).replace(/^\s+|\s+$/g, '');
        if (inner === '' || inner === '*') steps.push({ w: true });
        else if (/^\d+$/.test(inner)) steps.push({ i: parseInt(inner, 10) });
        else if (/^['"]/.test(inner)) steps.push({ k: inner.slice(1, -1) });
        else steps.push({ k: inner });
        i = j + 1; continue;
      }
      var m = /^[^.\[\]]+/.exec(s.slice(i));
      if (!m) { i++; continue; }
      steps.push({ k: m[0] });
      i += m[0].length;
    }
    return steps;
  }

  /**
   * 按路径取值。`[*]` 表示每一项都取；对数组写字段名也有用（会自动对每一项取该字段），
   * 因为 "list.name" 这样的写法比 "list[*].name" 更接近大家的直觉。
   */
  function walkPath(value, path) {
    var steps = splitPath(path), out = [];
    function rec(v, si, label) {
      if (out.length > 2000) return;
      if (si >= steps.length) { out.push({ path: label || '$', value: v }); return; }
      var st = steps[si];
      if (st.w) {
        if (Array.isArray(v)) {
          for (var i = 0; i < v.length; i++) rec(v[i], si + 1, label + '[' + i + ']');
        } else if (v && typeof v === 'object') {
          Object.keys(v).forEach(function (k) { rec(v[k], si + 1, label + '.' + k); });
        }
        return;
      }
      if (st.k !== undefined) {
        if (Array.isArray(v)) {
          var hit = false;
          for (var j = 0; j < v.length; j++) {
            if (v[j] && typeof v[j] === 'object' && !Array.isArray(v[j]) && st.k in v[j]) {
              hit = true; rec(v[j][st.k], si + 1, label + '[' + j + '].' + st.k);
            }
          }
          if (!hit) out.push({ path: label + '.' + st.k, miss: true });
          return;
        }
        if (v && typeof v === 'object' && st.k in v) rec(v[st.k], si + 1, label + '.' + st.k);
        else out.push({ path: label + '.' + (st.k === undefined ? st.i : st.k), miss: true });
        return;
      }
      if (st.i !== undefined) {
        if (Array.isArray(v) && st.i < v.length) rec(v[st.i], si + 1, label + '[' + st.i + ']');
        else out.push({ path: label + '[' + st.i + ']', miss: true });
      }
    }
    rec(value, 0, '$');
    return out;
  }

  /** 找出所有"能排成表格"的数组 */
  function detectTables(value) {
    var out = [];
    (function scan(v, path, depth) {
      if (out.length > 40 || depth > 4 || !v || typeof v !== 'object') return;
      if (Array.isArray(v)) {
        if (v.length && v.length <= MAX_CSV_ROWS) {
          var objs = 0, scalars = 0;
          for (var i = 0; i < v.length; i++) {
            var x = v[i];
            if (x && typeof x === 'object' && !Array.isArray(x)) objs++;
            else if (x === null || typeof x !== 'object') scalars++;
          }
          if (objs >= v.length * 0.5 || scalars === v.length) {
            out.push({ path: path || '$', label: path || '（最外层）', count: v.length,
              obj: objs > 0, val: v });
          }
        }
        var lim = Math.min(v.length, 3);
        for (var k = 0; k < lim; k++) scan(v[k], path + '[' + k + ']', depth + 1);
        return;
      }
      var ks = Object.keys(v);
      for (var j = 0; j < ks.length; j++) scan(v[ks[j]], path ? path + '.' + ks[j] : ks[j], depth + 1);
    })(value, '', 0);

    out.sort(function (a, b) {
      var sa = a.obj ? a.count * 2 : a.count;
      var sb = b.obj ? b.count * 2 : b.count;
      return sb - sa;
    });
    return out;
  }

  /** 一组数据 → 列名 + 行 */
  function tableOf(arr) {
    var cols = [], i, k;
    if (!Array.isArray(arr)) return { cols: [], rows: [] };
    if (arr.length && arr[0] && typeof arr[0] === 'object' && !Array.isArray(arr[0])) {
      for (i = 0; i < Math.min(arr.length, 200); i++) {
        var o = arr[i];
        if (!o || typeof o !== 'object') continue;
        for (k = 0; k < Object.keys(o).length; k++) {
          var key = Object.keys(o)[k];
          if (cols.indexOf(key) < 0) cols.push(key);
        }
      }
    } else if (arr.length && Array.isArray(arr[0])) {
      var wide = 0;
      for (i = 0; i < Math.min(arr.length, 200); i++) wide = Math.max(wide, arr[i].length);
      for (i = 0; i < wide; i++) cols.push('列' + (i + 1));
    } else {
      cols = ['值'];
    }
    var rows = arr.map(function (x) {
      if (Array.isArray(x)) {
        var r = [];
        for (i = 0; i < cols.length; i++) r.push(cellVal(x[i]));
        return r;
      }
      if (x && typeof x === 'object') return cols.map(function (c) { return cellVal(x[c]); });
      return [cellVal(x)];
    });
    return { cols: cols, rows: rows };
  }

  function cellVal(v) {
    if (v === undefined) return '';
    if (v === null) return '';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  }

  function csvCell(v) {
    var s = v === null || v === undefined ? '' : String(v);
    if (/[",\n\r]/.test(s) || /^\s|\s$/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function csvText(cols, rows, withHeader) {
    var out = [];
    if (withHeader) out.push(cols.map(csvCell).join(','));
    rows.forEach(function (r) { out.push(r.map(csvCell).join(',')); });
    return '\uFEFF' + out.join('\r\n') + '\r\n';   // 前面那个 BOM 是给 Excel 认 UTF-8 用的
  }

  /* ======================================================================
     5. 装配
     ====================================================================== */
  var DEMO = [
    '// 从配置文件里粘过来的，注释和单引号都是坏味道',
    '{',
    "  name: '龙兄',",
    '  age: 39,',
    "  tags: ['站点', '工具箱',],",
    '  /* 联系方式 */',
    '  "info": { "city": "射阳", "zip": 224300, },',
    '  active: True,',
    '  score: .95,',
    '  level: NaN,',
    '}'
  ].join('\n');

  function setupJson() {
    var P = panelOf('json');
    if (!P) return;

    var listBox = P.querySelector('[data-fixlist]');
    var outBox = P.querySelector('[data-res]');
    var treeBox = P.querySelector('[data-tree]');
    var resBox = P.querySelector('[data-qres]');
    var prevBox = P.querySelector('[data-qprev]');
    var tblSel = P.querySelector('[data-in="tbl"]');
    var state = { parsed: null, raw: '', tables: [], out: '', csv: '' };

    /** 提示条：写到当前可见的那一段里，避免"消息发到了看不见的地方" */
    function say(text, kind) {
      var subs = $$('[data-sub]', P), target = null, i;
      for (i = 0; i < subs.length; i++) {
        if (!subs[i].classList.contains('is-off')) { target = subs[i].querySelector('[data-msg]'); break; }
      }
      if (!target) target = P.querySelector('[data-msg]');
      if (!target) return;
      target.textContent = text;
      target.className = 'tl-msg on ' + (kind || 'ok');
      clearTimeout(target._t);
      if (kind !== 'err') target._t = setTimeout(function () { target.className = 'tl-msg'; }, 5200);
    }
    function sayClear() {
      $$('[data-msg]', P).forEach(function (m) {
        clearTimeout(m._t);
        m.className = 'tl-msg';
        m.textContent = '';
      });
    }

    function renderNotes(notes, ok, res) {
      if (!listBox) return;
      var html = '';
      if (!ok) {
        html += '<div class="tl-fixerr"><b>还有地方改不动</b><div>' + esc(res.bad) + '</div>' +
          (res.snippet ? '<pre class="tl-fixsnip">' + esc(res.snippet) + '</pre>' : '') +
          '<div class="tl-hint">上面已经改好的部分留在下面那栏里，可以对照着手工找一下。</div></div>';
      } else if (!notes.length) {
        html += '<div class="tl-fixok">这段内容本来就是合法 JSON，一个字都不用改。</div>';
      } else {
        notes.forEach(function (n) {
          html += '<div class="tl-fixrow"><span class="tl-fixn">' + n.n + ' 处</span>' +
            '<span class="tl-fixt"><b>' + esc(n.title) + '</b><span>' + esc(n.text) + '</span></span></div>';
        });
      }
      listBox.innerHTML = html;
    }

    function renderTree(value) {
      if (!treeBox) return;
      var budget = { n: 0 };
      function leafHtml(v) {
        if (v === null) return '<span class="tl-jv tl-jnull">null</span>';
        if (typeof v === 'string') return '<span class="tl-jv">"' + esc(v) + '"</span>';
        if (typeof v === 'number') return '<span class="tl-jv tl-jnum">' + esc(String(v)) + '</span>';
        if (typeof v === 'boolean') return '<span class="tl-jv tl-jbool">' + esc(String(v)) + '</span>';
        return '<span class="tl-jv">' + esc(String(v)) + '</span>';
      }
      function node(key, v, depth) {
        budget.n++;
        if (budget.n > MAX_TREE) return '<div class="tl-jleaf"><span class="tl-jt">…（内容太大，后面没画出来）</span></div>';
        var label = key === null ? '' : '<span class="tl-jk">' + esc(key) + '</span>';
        if (v === null || typeof v !== 'object') {
          return '<div class="tl-jleaf">' + label + leafHtml(v) + '</div>';
        }
        var isArr = Array.isArray(v);
        var keys = isArr ? null : Object.keys(v);
        var len = isArr ? v.length : keys.length;
        var head = isArr ? ('[ ' + len + ' 项 ]') : ('{ ' + len + ' 个字段 }');
        if (!len) {
          return '<div class="tl-jleaf">' + label + '<span class="tl-jt">' +
            (isArr ? '空数组' : '空对象') + '</span></div>';
        }
        var inner = '';
        for (var i = 0; i < len; i++) {
          if (budget.n > MAX_TREE) {
            inner += '<div class="tl-jleaf"><span class="tl-jt">… 还有 ' + (len - i) + ' 项没画出来</span></div>';
            break;
          }
          inner += node(isArr ? '[' + i + ']' : keys[i], isArr ? v[i] : v[keys[i]], depth + 1);
        }
        return '<details class="tl-jd"' + (depth < 2 ? ' open' : '') + '><summary>' + label +
          '<span class="tl-jt">' + esc(head) + '</span></summary>' +
          '<div class="tl-jc">' + inner + '</div></details>';
      }
      treeBox.innerHTML = node(null, value, 0);
    }

    function renderTables(tables) {
      if (!tblSel) return;
      if (!tables.length) {
        tblSel.innerHTML = '<option value="-1">（这段内容里没有能排成表格的一组数据）</option>';
        return;
      }
      tblSel.innerHTML = tables.map(function (t, i) {
        return '<option value="' + i + '">' + esc(t.label) + ' —— ' + t.count + ' 行' +
          (t.obj ? '、每行是对象' : '、每行是一个值') + '</option>';
      }).join('');
    }

    function renderPreview(arr) {
      if (!prevBox) return;
      if (!arr || !arr.length) { prevBox.innerHTML = ''; prevBox.className = 'tl-dtwrap'; return; }
      var t = tableOf(arr);
      var html = '<div class="tl-dtwrap-in"><table class="tl-dtbl"><thead><tr>';
      t.cols.forEach(function (c) { html += '<th>' + esc(c) + '</th>'; });
      html += '</tr></thead><tbody>';
      t.rows.slice(0, 8).forEach(function (r) {
        html += '<tr>';
        r.forEach(function (c) { html += '<td>' + (c === '' ? '<span class="tl-jt">—</span>' : esc(c)) + '</td>'; });
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      if (t.rows.length > 8) {
        html += '<div class="tl-dmore">一共 ' + t.rows.length + ' 行，这里先看前 8 行</div>';
      }
      prevBox.className = 'tl-dtwrap on';
      prevBox.innerHTML = html;
    }

    function currentTable() {
      var i = tblSel ? parseInt(tblSel.value, 10) : -1;
      if (!state.tables.length || !(i >= 0) || !state.tables[i]) return null;
      return state.tables[i].val;
    }

    function run() {
      var raw = String(valOf(P, 'raw') == null ? '' : valOf(P, 'raw'));
      if (!raw.replace(/^\s+|\s+$/g, '')) {
        sayClear();
        setStat(P, null);
        if (listBox) listBox.innerHTML = '';
        if (outBox) outBox.value = '';
        if (treeBox) treeBox.innerHTML = '<p class="tl-hint">上面贴进内容，这里会画成一棵可以展开收起的树。</p>';
        renderTables([]);
        renderPreview(null);
        if (resBox) resBox.innerHTML = '';
        state = { parsed: null, raw: '', tables: [], out: '', csv: '' };
        return;
      }

      var res = repairJson(raw);
      renderNotes(res.notes, res.ok, res);

      if (outBox) {
        outBox.value = res.ok
          ? fmt(res.value, !!valOf(P, 'pretty'), !!valOf(P, 'sortkey'))
          : res.text;
      }

      if (!res.ok) {
        say(res.bad + (res.snippet ? '（看下面「改了哪些地方」里有具体位置）' : ''), 'err');
        setStat(P, [
          ['结果', '还没修好'],
          ['改动', res.notes.length ? res.notes.length + ' 类' : '0 处'],
          ['出错位置', res.errLine ? '第 ' + res.errLine + ' 行 第 ' + res.errCol + ' 列' : '不确定']
        ], '下面列出的是已经改好的地方和还没解决的地方。改不动的部分留在输出栏里，你可以对照着手工处理。');
        state.parsed = null;
        state.tables = [];
        renderTables([]);
        renderPreview(null);
        if (treeBox) treeBox.innerHTML = '<p class="tl-hint">这段内容还没修好，先把它修成合法 JSON 再看结构。</p>';
        return;
      }

      var st = statsOf(res.value);
      state.parsed = res.value;
      state.raw = raw;
      state.out = outBox ? outBox.value : '';
      say(res.notes.length ? '已经修好了。下面列了 ' + res.notes.length + ' 类改动，逐条看看对不对。'
        : '这段内容本来就是合法 JSON，直接可用。', 'ok');

      setStat(P, [
        ['结果', '可以用'],
        ['类型', typeName(res.value)],
        ['改动', res.notes.length ? res.notes.length + ' 类' : '没有'],
        ['最多嵌套', Math.max(1, st.depth) + ' 层'],
        ['总节点', st.nodes + ' 个'],
        ['原文长度', raw.length + ' 字'],
        ['修复后', (outBox ? outBox.value.length : 0) + ' 字']
      ], '改动都是机械替换，不动语义：「引号」只改字符串边界，字符串里面的内容一个字没碰；' +
        '「缺失的逗号」只在两个值记号挨在一起时才补。');

      renderTree(res.value);
      state.tables = detectTables(res.value);
      renderTables(state.tables);
      renderPreview(currentTable());
      runQuery(true);
    }

    function fmt(v, pretty, sortKey) {
      var val = sortKey ? sortDeep(v) : v;
      return pretty ? JSON.stringify(val, null, 2) : JSON.stringify(val);
    }

    function rerenderOut() {
      if (!state.parsed || !outBox) return;
      outBox.value = fmt(state.parsed, !!valOf(P, 'pretty'), !!valOf(P, 'sortkey'));
      state.out = outBox.value;
    }

    /* ---- 取值与转表格 ---- */
    function runQuery(quiet) {
      if (!resBox) return;
      if (!state.parsed) { resBox.innerHTML = ''; state.csv = ''; if (!quiet) say('先把上面的内容修成合法 JSON，才能按路径取值。', 'err'); return; }
      var path = String(valOf(P, 'path') == null ? '' : valOf(P, 'path'));
      if (!path.replace(/^\s+|\s+$/g, '')) {
        resBox.innerHTML = '';
        state.csv = '';
        if (!quiet) say('先写一个路径，比如 data.list[0].name 或者 list[*].id。', 'err');
        return;
      }
      var hits = walkPath(state.parsed, path);
      var html = '';
      hits.slice(0, 200).forEach(function (h) {
        var v = h.miss ? '(没找到)' : (h.value === undefined ? '(没有值)' : (typeof h.value === 'object' ? JSON.stringify(h.value) : String(h.value)));
        var long = v.length > 400 ? v.slice(0, 400) + '…' : v;
        html += '<div class="tl-rxrow"><span class="tl-rxi">' + esc(h.path) + '</span>' +
          '<span class="tl-rxm">' + esc(long) + '</span>' +
          '<span class="tl-rxp"><span class="tl-rxg tl-rxg0">' +
          esc(h.miss ? '没找到' : typeName(h.value)) + '</span></span></div>';
      });
      if (!hits.length) html = '<div class="tl-fixok">这个路径下一处都没找到。</div>';
      resBox.innerHTML = html;
      if (!quiet) {
        say('按这个路径找到了 ' + hits.filter(function (h) { return !h.miss; }).length + ' 处值。', 'ok');
        var found = hits.filter(function (h) { return !h.miss; })[0];
        if (found && Array.isArray(found.value)) renderPreview(found.value);
      }
    }

    function doCsv(arr, quiet) {
      if (!arr || !arr.length) { if (!quiet) say('这段内容里没有能排成表格的一组数据。', 'err'); return ''; }
      if (arr.length > MAX_CSV_ROWS) { say('要转的这一组有 ' + arr.length + ' 行，一次最多转 ' + MAX_CSV_ROWS + ' 行。', 'err'); return ''; }
      var t = tableOf(arr);
      state.csv = csvText(t.cols, t.rows, true);
      if (!quiet) say('已经转好了：' + t.cols.length + ' 列、' + t.rows.length + ' 行。点「下载表格」就能存成 Excel 能直接打开的 .csv。', 'ok');
      return state.csv;
    }

    /* ---- 事件 ---- */
    var timer = 0;
    function schedule() {
      clearTimeout(timer);
      timer = setTimeout(run, 300);
    }
    var rawEl = P.querySelector('[data-in="raw"]');
    if (rawEl) rawEl.addEventListener('input', schedule);
    ['pretty', 'sortkey'].forEach(function (n) {
      var el = P.querySelector('[data-in="' + n + '"]');
      if (el) el.addEventListener('change', function () {
        if (!state.parsed) return;
        rerenderOut();
        setStat(P, [
          ['结果', '可以用'],
          ['类型', typeName(state.parsed)],
          ['最多嵌套', Math.max(1, statsOf(state.parsed).depth) + ' 层'],
          ['输出', valOf(P, 'pretty') ? '缩进多行' : '压成一行']
        ], valOf(P, 'sortkey') ? '字段名已经按字母顺序排列。' : '字段顺序保持原文的先后。');
      });
    });
    var pathEl = P.querySelector('[data-in="path"]');
    if (pathEl) {
      var pt = 0;
      pathEl.addEventListener('input', function () {
        clearTimeout(pt);
        pt = setTimeout(function () { runQuery(); }, 300);
      });
    }
    if (tblSel) {
      tblSel.addEventListener('change', function () {
        var arr = currentTable();
        renderPreview(arr);
        if (arr) doCsv(arr, true);
      });
    }

    var ACTS = {
      demo: function () {
        var el = P.querySelector('[data-in="raw"]');
        if (el) el.value = DEMO;
        run();
      },
      copy: function () {
        if (!state.out) { say('还没有可复制的结果。先把内容贴进来。', 'err'); return; }
        copyText(state.out).then(function () { say('修好的内容已经复制到剪贴板了。', 'ok'); },
          function (e) { say((e && e.message) || '这个浏览器不允许自动复制，请手动选中。', 'err'); });
      },
      csv: function () {
        if (!state.parsed) { say('上面还没修成合法 JSON，没有可以转的数据。', 'err'); return; }
        var arr = currentTable();
        if (!arr) { say('这段内容里没有能排成表格的一组数据（要有一列整齐的数组才行）。', 'err'); return; }
        var txt = doCsv(arr);
        if (txt) download(new Blob([txt], { type: 'text/csv;charset=utf-8' }), '表格.csv');
      },
      dl: function () {
        if (!state.out) { say('还没有可下载的结果。', 'err'); return; }
        download(new Blob([state.out], { type: 'application/json;charset=utf-8' }), '修好的数据.json');
        say('已经生成 .json 文件。', 'ok');
      },
      dlcsv: function () {
        if (!state.csv) { say('先点一次「转成表格」，有结果了才能下载。', 'err'); return; }
        download(new Blob([state.csv], { type: 'text/csv;charset=utf-8' }), '表格.csv');
        say('已经生成 .csv 文件，Excel 双击就能打开。', 'ok');
      },
      query: function () { runQuery(); },
      copycsv: function () {
        if (!state.csv) { say('先点一次「转成表格」，有结果了才能复制。', 'err'); return; }
        copyText(state.csv).then(function () { say('表格内容已经复制到剪贴板了。', 'ok'); },
          function (e) { say((e && e.message) || '这个浏览器不允许自动复制，请手动选中。', 'err'); });
      },
      clear: function () {
        var el = P.querySelector('[data-in="raw"]');
        if (el) el.value = '';
        var pe = P.querySelector('[data-in="path"]');
        if (pe) pe.value = '';
        state = { parsed: null, raw: '', tables: [], out: '', csv: '' };
        sayClear();
        run();
      }
    };

    $$('[data-act]', P).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var fn = ACTS[btn.getAttribute('data-act')];
        if (fn) fn();
      });
    });

    bindSeg(P);
    run();
  }

  window.LXTools.define('json', setupJson);
})();
