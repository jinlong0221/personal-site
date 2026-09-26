/*!
 * tools/dataconv.js — 数据格式互转台（工具箱·按需加载子模块）
 *
 * 日常最烦的一件小事：从 Excel 里框一片、从网页表格里选一段、从群消息里复制一坨，
 * 粘到别处就全乱了——因为它到底是用制表符分的还是逗号分的，肉眼根本看不出来。
 *
 * 这个工具把这层"看"先替你做了：
 *   1. 自动认分隔符（制表符 / 逗号 / 分号 / 竖线 / 连续空格 / Markdown 表格 / JSON），
 *      并且把认出来的结论用大白话说给你听，还配一张预览表让你核对；
 *   2. 认出来之后再转：Markdown 表格 / CSV / JSON / SQL / HTML 表格 / 纯文本对齐。
 * 认错了也没关系，选项都摆在明面上，随手改一下就行。全部在本机算，不外发。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $$ = _.$$;
  var copyText = _.copyText, download = _.download,
      esc = _.esc, panelOf = _.panelOf, setStat = _.setStat, valOf = _.valOf;

  var MAX_ROWS = 5000;
  var MAX_COLS = 200;
  var SQL_CHUNK = 200;

  /* ======================================================================
     1. 认分隔符
     ====================================================================== */
  var CANDIDATES = [
    { d: '\t', name: '制表符', why: '一般是从 Excel 或网页表格里直接复制过来的' },
    { d: ',', name: '逗号', why: '像是 CSV 文件的内容' },
    { d: ';', name: '分号', why: '欧洲那边导出的 CSV 常用分号' },
    { d: '|', name: '竖线', why: '像是从 Markdown 表格或命令行输出里来的' },
    { d: '  ', name: '连续空格', why: '像是从控制台里对齐打印出来的' }
  ];

  function splitLines(text) {
    return String(text).replace(/\r\n?/g, '\n').split('\n')
      .filter(function (l) { return l.replace(/\s/g, '') !== ''; });
  }

  /**
   * 按一个字符切分，认双引号包裹（引号里的分隔符和换行都不算切分点）。
   * 这就是 CSV 的标准写法，粘进来的内容十有八九是这一套。
   */
  function parseDelim(text, delim) {
    var rows = [], row = [], cur = '', i = 0, inQ = false;
    var s = String(text).replace(/\r\n?/g, '\n');
    while (i < s.length) {
      var c = s.charAt(i);
      if (inQ) {
        if (c === '"' && s.charAt(i + 1) === '"') { cur += '"'; i += 2; continue; }
        if (c === '"') { inQ = false; i++; continue; }
        cur += c; i++; continue;
      }
      if (c === '"' && cur === '') { inQ = true; i++; continue; }
      if (c === '\n') {
        row.push(cur);
        if (row.length > 1 || row[0] !== '') rows.push(row);
        row = []; cur = ''; i++; continue;
      }
      if (c === delim) { row.push(cur); cur = ''; i++; continue; }
      cur += c; i++;
    }
    row.push(cur);
    if (row.length > 1 || row[0] !== '') rows.push(row);
    return rows;
  }

  /** 连续空格这种没法按单字符切，只能一行一行来 */
  function parseSpaces(text) {
    return splitLines(text).map(function (l) {
      return l.replace(/^\s+|\s+$/g, '').split(/\s{2,}/);
    });
  }

  /** Markdown 表格：第一行有竖线、第二行是 |---|---| 这种分隔线 */
  function parseMarkdown(text) {
    var lines = splitLines(text);
    if (lines.length < 2 || lines[0].indexOf('|') < 0) return null;
    var sep = lines[1].replace(/^\s*\|/, '').replace(/\|\s*$/, '').replace(/^\s+|\s+$/g, '');
    if (!/^:?-+:?(\s*\|\s*:?-+:?)*$/.test(sep)) return null;
    var body = [lines[0]].concat(lines.slice(2));
    return body.map(function (l) {
      return l.replace(/\\\|/g, '\u0001')
        .replace(/^\s*\|/, '').replace(/\|\s*$/, '')
        .split('|')
        .map(function (c) { return c.replace(/\u0001/g, '|').replace(/^\s+|\s+$/g, ''); });
    });
  }

  /** 这么多行里，最常见的列数占多大比例 —— 越"整齐"越像是真的分了列 */
  function scoreRows(rows) {
    var n = rows.length;
    if (n < 2) return 0;
    var freq = {}, best = 0, bestN = 0, k;
    for (var i = 0; i < n; i++) {
      k = rows[i].length;
      freq[k] = (freq[k] || 0) + 1;
      if (freq[k] > bestN) { bestN = freq[k]; best = k; }
    }
    if (best < 2) return 0;
    var consistency = bestN / n;
    if (consistency < 0.6) return 0;
    return best * consistency * consistency;
  }

  /** 把每行补齐到同样的列数（多出来的列也算，宁可宽一点也别丢数据） */
  function padRows(rows) {
    var wide = 0, i, j;
    for (i = 0; i < rows.length; i++) wide = Math.max(wide, rows[i].length);
    for (i = 0; i < rows.length; i++) {
      for (j = rows[i].length; j < wide; j++) rows[i].push('');
    }
    return wide;
  }

  /** 纯数字的格子？ */
  function looksNum(s) {
    return s !== '' && /^-?\d+(\.\d+)?$/.test(String(s).replace(/^\s+|\s+$/g, ''));
  }

  /**
   * 第一行到底是不是表头。给不出把握就一律返回「不是」——宁可不认，
   * 也不要替用户断言错（认错了列名会跟着错到 JSON 和 SQL 里）。判据两条，满足任一条才算：
   *   ① 第一行一个数字都没有，下面的行里却有数字 —— 也就是"它长得不像数据"；
   *   ② 两边都是纯文字时，看长短：表头通常比数据短（"姓名"比"内容运营"短）。
   * 另外：只有一列的表不认表头，第一行有空格的也不认。
   */
  function guessHeader(rows) {
    if (rows.length < 2) return false;
    var r0 = rows[0], wide = r0.length, i, j;
    if (wide < 2) return false;
    var num0 = 0, empty0 = 0, len0 = 0;
    for (i = 0; i < wide; i++) {
      var c0 = cell(r0[i]);
      if (looksNum(c0)) num0++;
      if (c0.replace(/\s/g, '') === '') empty0++;
      if (c0.length > 40) return false;
      len0 += c0.length;
    }
    if (num0 > 0 || empty0 > 0) return false;

    var total = 0, num = 0, lenB = 0;
    for (i = 1; i < rows.length; i++) {
      for (j = 0; j < rows[i].length; j++) {
        total++;
        lenB += cell(rows[i][j]).length;
        if (looksNum(rows[i][j])) num++;
      }
    }
    if (!total) return false;
    if (num / total > 0.15) return true;
    return (len0 / wide) < (lenB / total) * 0.8;
  }

  /** JSON 输入：从里面挑出一组最适合排成表格的数组 */
  function pickArrayFrom(v) {
    var best = null;
    (function scan(x, path, depth) {
      if (depth > 4 || !x || typeof x !== 'object') return;
      if (Array.isArray(x)) {
        if (x.length && x[0] !== null && typeof x[0] === 'object' && !Array.isArray(x[0])) {
          if (!best || x.length > best.val.length) best = { val: x, path: path || '$' };
        } else if (x.length && typeof x[0] !== 'object') {
          if (!best) best = { val: x, path: path || '$' };
        }
        for (var i = 0; i < Math.min(x.length, 3); i++) scan(x[i], path + '[' + i + ']', depth + 1);
        return;
      }
      var ks = Object.keys(x);
      for (var k = 0; k < ks.length; k++) scan(x[ks[k]], path ? path + '.' + ks[k] : ks[k], depth + 1);
    })(v, '', 0);
    return best;
  }

  function jsonToRows(arr) {
    if (arr.length && arr[0] !== null && typeof arr[0] === 'object' && !Array.isArray(arr[0])) {
      var cols = [];
      for (var i = 0; i < Math.min(arr.length, 500); i++) {
        var o = arr[i];
        if (!o || typeof o !== 'object') continue;
        var ks = Object.keys(o);
        for (var k = 0; k < ks.length; k++) if (cols.indexOf(ks[k]) < 0) cols.push(ks[k]);
      }
      var rows = [cols];
      arr.forEach(function (o) {
        rows.push(cols.map(function (c) {
          var v = o ? o[c] : undefined;
          if (v === undefined || v === null) return '';
          return typeof v === 'object' ? JSON.stringify(v) : String(v);
        }));
      });
      return { rows: rows, header: true };
    }
    if (arr.length && Array.isArray(arr[0])) {
      var rows2 = arr.map(function (r) { return r.map(function (x) { return x == null ? '' : String(x); }); });
      return { rows: rows2, header: false };
    }
    return { rows: arr.map(function (x) { return [x == null ? '' : String(x)]; }), header: false };
  }

  /**
   * 分析一段贴进来的内容。
   * @returns {{ok:boolean, kind:string, delim:string, name:string, why:string,
   *            cols:string[], rows:string[][], header:boolean, note:string, warn:string}}
   */
  function analyze(text) {
    var s = String(text == null ? '' : text).replace(/\uFEFF/g, '');
    if (!s.replace(/\s/g, '')) return { ok: false, kind: '', cols: [], rows: [], note: '', warn: '' };

    var trimmed = s.replace(/^\s+/, '');
    var allRows = null, kind = '', name = '', why = '', note = '';

    // —— JSON ——
    if (trimmed.charAt(0) === '[' || trimmed.charAt(0) === '{') {
      var parsed = null, parseOk = false;
      try { parsed = JSON.parse(trimmed); parseOk = true; } catch (e) { parseOk = false; }
      if (parseOk) {
        var best = pickArrayFrom(parsed);
        if (best) {
          var jr = jsonToRows(best.val);
          return finish(jr.rows, 'json', 'JSON',
            '这本身就是一段 JSON，已经把它里面的那组数据摊平成表格',
            '取的是 JSON 里 ' + best.path + ' 这一组（' + best.val.length + ' 条）。', jr.header);
        }
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed) && Object.keys(parsed).length) {
          var ks = Object.keys(parsed);
          var vals = ks.map(function (k) {
            var x = parsed[k];
            return x === null || x === undefined ? '' : (typeof x === 'object' ? JSON.stringify(x) : String(x));
          });
          return finish([ks, vals], 'json', 'JSON',
            '这是一段 JSON 对象，已经把它摊成「字段名 / 字段值」两列', '', true);
        }
        return finish([['值'], [JSON.stringify(parsed)]], 'json', 'JSON',
          '这是一段 JSON，已经把它当作一列数据放进来', '', true);
      }
    }

    // —— Markdown 表格 ——
    var md = parseMarkdown(s);
    if (md) {
      return finish(md, 'markdown', 'Markdown 表格',
        '这是 Markdown 表格，用竖线分列，第二行那条 |---| 是分隔线已经跳过', '', true);
    }

    // —— 逐个候选分隔符打分 ——
    var bestScore = 0, bestRows = null, bestName = '', bestWhy = '';
    CANDIDATES.forEach(function (c) {
      var rows = c.d === '  ' ? parseSpaces(s) : parseDelim(s, c.d);
      var sc = scoreRows(rows);
      if (sc > bestScore) { bestScore = sc; bestRows = rows; bestName = c.name; bestWhy = c.why; }
    });

    if (bestRows && bestScore >= 1) {
      return finish(bestRows, 'delim', bestName, '用「' + bestName + '」分列，' + bestWhy, '');
    }

    // 只有一行的时候没有"整齐不整齐"可比，但一行 CSV 也是很常见的用法：
    // 那就按最常见的那几种挨个试，谁切出来的格子多就用谁（多半就是它）。
    if (splitLines(s).length <= 1) {
      for (var ci = 0; ci < CANDIDATES.length; ci++) {
        if (CANDIDATES[ci].d === '  ') continue;
        var one = parseDelim(s, CANDIDATES[ci].d);
        if (one.length && one[0].length >= 2) {
          // 只有一行就把它当数据行（不然会得到一张没有数据的空表）
          return finish(one, 'delim', CANDIDATES[ci].name,
            '只有一行，按「' + CANDIDATES[ci].name + '」切开看了看，' + CANDIDATES[ci].why, '', false);
        }
      }
    }

    // —— 都没认出来，按一行一条 ——
    allRows = splitLines(s).map(function (l) { return [l]; });
    return finish(allRows, 'plain', '没认出来',
      '没看出用了哪种分隔符，就先按"一行一条记录"处理', '', false);
  }

  function finish(rows, kind, name, why, note, hdrForce) {
    var warn = '';
    var counts = {}, odd = 0, wide = 0, i;
    for (i = 0; i < rows.length; i++) {
      counts[rows[i].length] = (counts[rows[i].length] || 0) + 1;
      wide = Math.max(wide, rows[i].length);
    }
    var target = wide;
    if (Object.keys(counts).length > 1) {
      for (i = 0; i < rows.length; i++) if (rows[i].length !== target) odd++;
      warn = '有 ' + odd + ' 行的列数和别的行不一样，已经按最多的 ' + target + ' 列补齐，缺的格子留空。';
    }
    padRows(rows);
    if (rows.length > MAX_ROWS) {
      return { ok: false, kind: kind, cols: [], rows: [],
        note: '', warn: '内容有 ' + rows.length + ' 行，一次最多转 ' + MAX_ROWS + ' 行，先裁小一点。' };
    }
    if (wide > MAX_COLS) {
      return { ok: false, kind: kind, cols: [], rows: [],
        note: '', warn: '认出来有 ' + wide + ' 列，列数不正常，多半是分隔符认错了。换个写法再试。' };
    }
    var header = hdrForce === undefined ? guessHeader(rows) : !!hdrForce;
    var cols = null;
    if (header && rows.length) {
      cols = rows[0].map(function (c, k) { return c === '' ? '列' + (k + 1) : c; });
    }
    if (!cols) {
      cols = [];
      for (i = 0; i < wide; i++) cols.push('列' + (i + 1));
    }
    return {
      ok: true, kind: kind, name: name, why: why, note: note, warn: warn,
      header: header, cols: cols, rows: header ? rows.slice(1) : rows, all: rows
    };
  }

  /* ======================================================================
     2. 各种格式的输出
     ====================================================================== */
  function cell(v) { return v === null || v === undefined ? '' : String(v); }

  function mdCell(s) {
    return cell(s).replace(/\\/g, '\\\\').replace(/\|/g, '\\|').replace(/\r?\n/g, '<br>');
  }

  function toMarkdown(cols, rows) {
    var out = [];
    out.push('| ' + cols.map(mdCell).join(' | ') + ' |');
    out.push('| ' + cols.map(function () { return '---'; }).join(' | ') + ' |');
    rows.forEach(function (r) {
      out.push('| ' + cols.map(function (c, i) { return mdCell(r[i]); }).join(' | ') + ' |');
    });
    return out.join('\n') + '\n';
  }

  function csvCell(s) {
    var v = cell(s);
    if (/[",\n\r]/.test(v) || /^\s|\s$/.test(v)) return '"' + v.replace(/"/g, '""') + '"';
    return v;
  }

  function toCSV(cols, rows, withHeader) {
    var out = [];
    if (withHeader) out.push(cols.map(csvCell).join(','));
    rows.forEach(function (r) { out.push(cols.map(function (c, i) { return csvCell(r[i]); }).join(',')); });
    return '\uFEFF' + out.join('\r\n') + '\r\n';
  }

  function toJSON(cols, rows, numeric) {
    var arr = rows.map(function (r) {
      var o = {};
      cols.forEach(function (c, i) {
        var v = cell(r[i]).replace(/^\s+|\s+$/g, '');
        if (v === '') o[c] = null;
        else if (numeric && /^-?\d+(\.\d+)?$/.test(v)) o[c] = parseFloat(v);
        else o[c] = v;
      });
      return o;
    });
    return JSON.stringify(arr, null, 2) + '\n';
  }

  function colNameOf(name, style, i) {
    var s = cell(name).replace(/\s+/g, '_');
    if (!s) s = '列' + (i + 1);
    if (style === 'snake') {
      s = s.replace(/([a-z0-9])([A-Z])/g, '$1_$2').replace(/[-\s]+/g, '_').toLowerCase();
    } else if (style === 'camel') {
      var parts = s.split(/[_\-\s]+/).filter(function (x) { return x; });
      s = parts.map(function (p, k) {
        return k === 0 ? p.charAt(0).toLowerCase() + p.slice(1) : p.charAt(0).toUpperCase() + p.slice(1);
      }).join('');
    }
    if (!s) s = '列' + (i + 1);
    if (/^\d/.test(s)) s = 'c_' + s;
    return s.replace(/[^\w\u4e00-\u9fa5]/g, '_');
  }

  function sqlValue(v, numeric, emptyMode) {
    var s = cell(v).replace(/^\s+|\s+$/g, '');
    if (s === '') {
      if (emptyMode === 'dash') return "'—'";
      return 'NULL';
    }
    if (numeric && /^-?\d+(\.\d+)?$/.test(s)) return s;
    return "'" + s.replace(/'/g, "''") + "'";
  }

  function toSQL(cols, rows, opts) {
    var names = cols.map(function (c, i) { return colNameOf(c, opts.style, i); });
    var tbl = (opts.table || 'my_table').replace(/[^\w\u4e00-\u9fa5]/g, '_') || 'my_table';
    var head = '-- 共 ' + rows.length + ' 行';
    var out = [head];
    for (var s = 0; s < rows.length; s += SQL_CHUNK) {
      var part = rows.slice(s, s + SQL_CHUNK);
      var lines = part.map(function (r) {
        return '  (' + names.map(function (c, i) {
          return sqlValue(r[i], opts.numeric, opts.empty);
        }).join(', ') + ')';
      });
      out.push('INSERT INTO ' + tbl + ' (' + names.join(', ') + ') VALUES');
      out.push(lines.join(',\n') + ';');
    }
    if (!rows.length) out.push('-- 没有数据行');
    return out.join('\n') + '\n';
  }

  function toHTML(cols, rows, withHeader) {
    var out = ['<table>'];
    if (withHeader) {
      out.push('  <thead>');
      out.push('    <tr>' + cols.map(function (c) { return '<th>' + esc(c) + '</th>'; }).join('') + '</tr>');
      out.push('  </thead>');
    }
    out.push('  <tbody>');
    rows.forEach(function (r) {
      out.push('    <tr>' + cols.map(function (c, i) { return '<td>' + esc(cell(r[i])) + '</td>'; }).join('') + '</tr>');
    });
    out.push('  </tbody>');
    out.push('</table>');
    return out.join('\n') + '\n';
  }

  /** 中日韩字符按两个格子宽算，纯文本对齐才不会歪 */
  function widthOf(s) {
    var w = 0;
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      w += (c >= 0x1100 && (c <= 0x115f || c === 0x2329 || c === 0x232a ||
        (c >= 0x2e80 && c <= 0xa4cf && c !== 0x303f) ||
        (c >= 0xac00 && c <= 0xd7a3) || (c >= 0xf900 && c <= 0xfaff) ||
        (c >= 0xfe30 && c <= 0xfe6f) || (c >= 0xff00 && c <= 0xff60) ||
        (c >= 0xffe0 && c <= 0xffe6))) ? 2 : 1;
    }
    return w;
  }

  function toPlain(cols, rows, withHeader) {
    var body = withHeader ? [cols].concat(rows) : rows;
    if (!body.length) return '';
    var w = [], i, j;
    for (j = 0; j < cols.length; j++) {
      var m = withHeader ? widthOf(cell(cols[j])) : 0;
      for (i = 0; i < rows.length; i++) m = Math.max(m, widthOf(cell(rows[i][j])));
      w.push(m);
    }
    function line(r) {
      return r.map(function (c, k) {
        var s = cell(c).replace(/\r?\n/g, ' ');
        return s + new Array(Math.max(1, w[k] - widthOf(s) + 1)).join(' ');
      }).join('  ').replace(/\s+$/, '');
    }
    var out = body.map(line);
    if (withHeader) {
      out.splice(1, 0, w.map(function (n) { return new Array(n + 1).join('-'); }).join('  '));
    }
    return out.join('\n') + '\n';
  }

  var FORMATS = [
    { id: 'md', n: 'Markdown 表格', ext: 'md', type: 'text/markdown;charset=utf-8' },
    { id: 'csv', n: 'CSV', ext: 'csv', type: 'text/csv;charset=utf-8' },
    { id: 'json', n: 'JSON', ext: 'json', type: 'application/json;charset=utf-8' },
    { id: 'sql', n: 'SQL 语句', ext: 'sql', type: 'text/plain;charset=utf-8' },
    { id: 'html', n: 'HTML 表格', ext: 'html', type: 'text/html;charset=utf-8' },
    { id: 'text', n: '纯文本对齐', ext: 'txt', type: 'text/plain;charset=utf-8' }
  ];

  /* ======================================================================
     3. 装配
     ====================================================================== */
  var DEMO = [
    '姓名\t部门\t工号\t本月工时',
    '龙兄\t内容运营\tA1001\t168',
    '小王\t内容运营\tA1002\t152.5',
    '老李\t技术\tB2001\t176'
  ].join('\n');

  function setupDataConv() {
    var P = panelOf('dataconv');
    if (!P) return;

    var outBox = P.querySelector('[data-res]');
    var prevBox = P.querySelector('[data-prev]');
    var detectBox = P.querySelector('[data-detect]');
    var fmtBox = P.querySelector('[data-fmts]');
    var state = { an: null, fmt: 'md', out: '' };

    function opts() {
      return {
        header: !!valOf(P, 'hdr'),
        trim: valOf(P, 'trim') !== false,
        numeric: !!valOf(P, 'num'),
        empty: String(valOf(P, 'empty') || 'null'),
        table: String(valOf(P, 'tbl') == null ? 'my_table' : valOf(P, 'tbl')),
        style: String(valOf(P, 'cstyle') || 'snake')
      };
    }

    function say(text, kind) {
      var m = P.querySelector('[data-msg]');
      if (!m) return;
      m.textContent = text;
      m.className = 'tl-msg on ' + (kind || 'ok');
      clearTimeout(m._t);
      if (kind !== 'err') m._t = setTimeout(function () { m.className = 'tl-msg'; }, 5200);
    }
    function sayClear() {
      var m = P.querySelector('[data-msg]');
      if (!m) return;
      clearTimeout(m._t);
      m.className = 'tl-msg';
      m.textContent = '';
    }

    function clean(rows, o) {
      if (!o.trim) return rows;
      return rows.map(function (r) {
        return r.map(function (c) { return cell(c).replace(/^\s+|\s+$/g, ''); });
      });
    }

    function build() {
      var an = state.an;
      if (!an || !an.ok) return '';
      var o = opts();
      var cols = [];
      for (var i = 0; i < an.cols.length; i++) {
        var c = cell(an.cols[i]).replace(/^\s+|\s+$/g, '');
        cols.push(c === '' ? '列' + (i + 1) : c);
      }
      var rows = clean(an.rows, o);
      var withHeader = o.header && an.cols.length > 0;
      switch (state.fmt) {
        case 'csv': return toCSV(cols, rows, withHeader);
        case 'json': return toJSON(cols, rows, o.numeric);
        case 'sql': return toSQL(cols, rows, o);
        case 'html': return toHTML(cols, rows, withHeader);
        case 'text': return toPlain(cols, rows, withHeader);
        default: return toMarkdown(cols, rows);
      }
    }

    function renderPreview(an, o) {
      if (!prevBox) return;
      if (!an || !an.ok) { prevBox.className = 'tl-dtwrap'; prevBox.innerHTML = ''; return; }
      var cols = an.cols;
      var rows = clean(an.rows, o);
      var html = '<div class="tl-dtwrap-in"><table class="tl-dtbl"><thead><tr><th class="tl-dthn">#</th>';
      cols.forEach(function (c) { html += '<th>' + esc(c) + '</th>'; });
      html += '</tr></thead><tbody>';
      rows.slice(0, 8).forEach(function (r, i) {
        html += '<tr><td class="tl-dthn">' + (i + 1) + '</td>';
        cols.forEach(function (c, k) {
          var v = cell(r[k]);
          html += '<td>' + (v === '' ? '<span class="tl-jt">—</span>' : esc(v.length > 60 ? v.slice(0, 60) + '…' : v)) + '</td>';
        });
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      if (rows.length > 8) html += '<div class="tl-dmore">一共 ' + rows.length + ' 行（不含表头），这里先看前 8 行</div>';
      prevBox.className = 'tl-dtwrap on';
      prevBox.innerHTML = html;
    }

    function renderDetect(an) {
      if (!detectBox) return;
      if (!an || (!an.ok && !an.warn)) { detectBox.className = 'tl-detect'; detectBox.innerHTML = ''; return; }
      var lines = [];
      if (an.ok) {
        lines.push('<b>认出来了：</b>' + esc(an.why) + '。' +
          '共 <b>' + an.cols.length + '</b> 列、<b>' + an.rows.length + '</b> 行' +
          (an.header ? '（第 1 行认作表头）' : '（没认表头，全按数据行处理）') + '。' +
          (an.note ? esc(an.note) : ''));
        if (an.warn) lines.push('<span class="tl-dw2">' + esc(an.warn) + '</span>');
      } else {
        lines.push('<span class="tl-dw2">' + esc(an.warn || '这段内容暂时转不了。') + '</span>');
      }
      detectBox.className = 'tl-detect on';
      detectBox.innerHTML = lines.map(function (t) { return '<div>' + t + '</div>'; }).join('');
    }

    function renderFmts() {
      if (!fmtBox) return;
      fmtBox.innerHTML = FORMATS.map(function (f) {
        return '<button class="tl-chip' + (f.id === state.fmt ? ' on' : '') +
          '" type="button" data-fmt="' + f.id + '">' + f.n + '</button>';
      }).join('');
      $$('[data-fmt]', fmtBox).forEach(function (b) {
        b.addEventListener('click', function () {
          state.fmt = b.getAttribute('data-fmt');
          renderFmts();
          runOutput();
        });
      });
    }

    function runOutput() {
      var an = state.an, o = opts();
      if (!an || !an.ok) {
        state.out = '';
        if (outBox) outBox.value = '';
        return;
      }
      state.out = build();
      if (outBox) outBox.value = state.out;
      var f = FORMATS.filter(function (x) { return x.id === state.fmt; })[0];
      setStat(P, [
        ['列', an.cols.length + ' 列'],
        ['行', an.rows.length + ' 行'],
        ['分隔符', an.name],
        ['输出格式', f ? f.n : ''],
        ['输出长度', state.out.length + ' 字']
      ], '想换一种格式就点上面的按钮，数据本身不动。' +
        (state.fmt === 'json' ? 'JSON 里的数字要不要当成数字（而不是带引号的文字），看上面那个勾。' : '') +
        (state.fmt === 'sql' ? 'SQL 的表名和字段名风格都在上面可以改。' : ''));
    }

    function run() {
      var raw = String(valOf(P, 'raw') == null ? '' : valOf(P, 'raw'));
      if (!raw.replace(/\s/g, '')) {
        state.an = null;
        sayClear();
        setStat(P, null);
        if (outBox) outBox.value = '';
        renderDetect(null);
        renderPreview(null, opts());
        return;
      }
      var an = analyze(raw);
      state.an = an;
      var hdrEl = P.querySelector('[data-in="hdr"]');
      if (hdrEl && an.ok) hdrEl.checked = !!an.header;
      renderDetect(an);
      renderPreview(an, opts());
      if (an.ok) {
        sayClear();
        runOutput();
      } else {
        say(an.warn || '这段内容暂时转不了。', 'err');
        if (outBox) outBox.value = '';
        setStat(P, null);
      }
    }

    var timer = 0;
    var rawEl = P.querySelector('[data-in="raw"]');
    if (rawEl) {
      rawEl.addEventListener('input', function () {
        clearTimeout(timer);
        timer = setTimeout(run, 260);
      });
    }
    ['hdr', 'trim', 'num', 'empty', 'tbl', 'cstyle'].forEach(function (n) {
      var el = P.querySelector('[data-in="' + n + '"]');
      if (!el) return;
      el.addEventListener(el.tagName === 'SELECT' || el.type === 'checkbox' ? 'change' : 'input', function () {
        if (!state.an || !state.an.ok) return;
        renderPreview(state.an, opts());
        runOutput();
      });
    });

    var ACTS = {
      demo: function () {
        if (rawEl) rawEl.value = DEMO;
        run();
      },
      copy: function () {
        if (!state.out) { say('还没有可以复制的结果。先把内容贴进来。', 'err'); return; }
        copyText(state.out).then(function () { say('转换结果已经复制到剪贴板了。', 'ok'); },
          function (e) { say((e && e.message) || '这个浏览器不允许自动复制，请手动选中。', 'err'); });
      },
      dl: function () {
        if (!state.out) { say('还没有可以下载的结果。', 'err'); return; }
        var f = FORMATS.filter(function (x) { return x.id === state.fmt; })[0] || FORMATS[0];
        download(new Blob([state.out], { type: f.type }), '转换结果.' + f.ext);
        say('已经生成 .' + f.ext + ' 文件。', 'ok');
      },
      clear: function () {
        if (rawEl) rawEl.value = '';
        state.an = null;
        state.out = '';
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

    renderFmts();
    run();
  }

  window.LXTools.define('dataconv', setupDataConv);
})();
