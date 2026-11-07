/*!
 * tools/diff.js — 文本对比（工具箱·按需加载子模块）
 *
 * 把两段文字摆在一起，逐行对齐、逐词标出差异。算法全部自己实现（最长公共子序列），
 * 不引任何第三方库、不发任何请求——合同改稿、代码改动、公文两版对照都用得上。
 *
 * 三层做法：
 *   1. 行级对齐（LCS）→ 判断哪些行是新增 / 删除 / 改动；
 *   2. 成对的行再做词级 LCS → 只把真正变了的字词染色，其余保持原样；
 *   3. 显示层可选折叠没变的行，只留改动附近的上下文。
 *
 * 规模保护：纯 JS 的 LCS 是 O(行数 × 行数)。超过上限直接说清楚"太大"，而不是让
 * 标签页卡死。宁可少做，也不给用户一个转圈转半天的页面。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $$ = _.$$;
  var clearToast = _.clearToast, copyText = _.copyText, download = _.download,
      esc = _.esc, panelOf = _.panelOf, setStat = _.setStat, toast = _.toast,
      valOf = _.valOf;

  /** 两行「像到可以算改写」的门槛：低于它宁可拆成一行删除 + 一行新增，也不谎称是改写。
   *  取 0.5，意思是两行的词（汉字按字算）至少得有一半对得上。放松到 0.1 那一档会出洋相：
   *  「第三行要删」与「新增的一行」只因都带一个「行」字，就被判成同一行的改写 ——
   *  这等于替用户断言两行的关系，所以宁可老实拆成「删一行 + 增一行」。 */
  var SAME_ENOUGH = 0.5;

  /* ======================================================================
     1. 分词与比较键
     ====================================================================== */
  /** 一个汉字、一串英文数字、一段空白、一个标点，各算一个"词" */
  function tokenize(s) {
    var re = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]|[A-Za-z0-9_]+|\s+|[^\s]/g;
    var out = [], m;
    while ((m = re.exec(s))) out.push(m[0]);
    return out;
  }

  function keyOfLine(line, o) {
    var s = line;
    if (o.ws) s = s.replace(/\s+/g, ' ');
    if (o.tw) s = s.replace(/^\s+|\s+$/g, '');
    if (o.ic) s = s.toLowerCase();
    return s;
  }
  function keyOfTok(tok, o) {
    if (o.ws && /^\s+$/.test(tok)) return ' ';
    return o.ic ? tok.toLowerCase() : tok;
  }

  /* ======================================================================
     2. 最长公共子序列
     ====================================================================== */
  /** 只求长度（滚动数组，省内存），用来判断两行"像不像" */
  function lcsLen(a, b, cap) {
    var n = a.length, m = b.length;
    if (!n || !m) return 0;
    if (n * m > (cap || 400000)) return 0;
    var prev = new Uint32Array(m + 1), cur = new Uint32Array(m + 1), t;
    for (var i = 1; i <= n; i++) {
      for (var j = 1; j <= m; j++) {
        cur[j] = a[i - 1] === b[j - 1] ? prev[j - 1] + 1
          : (prev[j] >= cur[j - 1] ? prev[j] : cur[j - 1]);
      }
      t = prev; prev = cur; cur = t;
      cur.fill(0);
    }
    return prev[m];
  }

  /**
   * 对齐两个序列，返回按顺序排列的操作：
   *   {t:'same', i, j} | {t:'del', i} | {t:'add', j}
   * 代价相同的分支优先走「删」，这样成批的删除会排在新增前面，配起对来更像人眼看到的改动。
   */
  function align(a, b) {
    var n = a.length, m = b.length, W = m + 1;
    var dp = new Uint32Array((n + 1) * W), i, j, row, nrow;
    for (i = n - 1; i >= 0; i--) {
      row = i * W; nrow = (i + 1) * W;
      for (j = m - 1; j >= 0; j--) {
        dp[row + j] = a[i] === b[j] ? dp[nrow + j + 1] + 1
          : (dp[nrow + j] >= dp[row + j + 1] ? dp[nrow + j] : dp[row + j + 1]);
      }
    }
    var ops = [], x = 0, y = 0;
    while (x < n && y < m) {
      if (a[x] === b[y]) { ops.push({ t: 'same', i: x, j: y }); x++; y++; }
      else if (dp[(x + 1) * W + y] >= dp[x * W + y + 1]) { ops.push({ t: 'del', i: x }); x++; }
      else { ops.push({ t: 'add', j: y }); y++; }
    }
    while (x < n) { ops.push({ t: 'del', i: x }); x++; }
    while (y < m) { ops.push({ t: 'add', j: y }); y++; }
    return ops;
  }

  /** 两行的相似程度（0-1），用来决定这一对到底算"改动"还是"一删一增" */
  function pairSim(aLine, bLine, o) {
    var ta = tokenize(aLine).map(function (t) { return keyOfTok(t, o); });
    var tb = tokenize(bLine).map(function (t) { return keyOfTok(t, o); });
    var sum = ta.length + tb.length;
    if (!sum) return 1;
    if (sum > 2400) return 0.5;          // 太长了就不细算，当作"有点像"
    return (2 * lcsLen(ta, tb, 600000)) / sum;
  }

  /* ======================================================================
     3. 行级对齐 → 显示行
     ====================================================================== */
  /**
   * @returns {Array<{t:'same'|'mod'|'del'|'add', a:number, b:number}>} a/b 为 -1 表示该侧没有对应行
   */
  function buildRows(aLines, bLines, o) {
    var oa = { ic: o.ic, tw: o.tw, ws: o.ws };
    var ka = aLines.map(function (s) { return keyOfLine(s, oa); });
    var kb = bLines.map(function (s) { return keyOfLine(s, oa); });
    var ops = align(ka, kb);
    var rows = [], dels = [], adds = [];

    // 一段删除 + 一段新增，谁配谁？只看行数对齐是省事，但会把「删掉的第 3 行」硬说成
    // 「改成了新加的第 3 行」——这是替用户断言两行的关系。所以逐对单独判：够像的才算
    // 「同一行改写」；不像的攒起来，到最后统一按「先全部删除、再全部新增」输出。
    // 既不多认关系，顺序也不会乱（与通行的对照格式一致）。
    function flush() {
      var n = Math.min(dels.length, adds.length), k;
      var pendD = [], pendA = [];
      function spill() {
        var i;
        for (i = 0; i < pendD.length; i++) rows.push({ t: 'del', a: pendD[i], b: -1 });
        for (i = 0; i < pendA.length; i++) rows.push({ t: 'add', a: -1, b: pendA[i] });
        pendD = []; pendA = [];
      }
      for (k = 0; k < n; k++) {
        if (pairSim(aLines[dels[k]], bLines[adds[k]], oa) >= SAME_ENOUGH) {
          spill();
          rows.push({ t: 'mod', a: dels[k], b: adds[k] });
        } else {
          pendD.push(dels[k]); pendA.push(adds[k]);
        }
      }
      for (k = n; k < dels.length; k++) pendD.push(dels[k]);
      for (k = n; k < adds.length; k++) pendA.push(adds[k]);
      spill();
      dels = []; adds = [];
    }

    ops.forEach(function (op) {
      if (op.t === 'same') { flush(); rows.push({ t: 'same', a: op.i, b: op.j }); }
      else if (op.t === 'del') dels.push(op.i);
      else adds.push(op.j);
    });
    flush();
    return rows;
  }

  /* ======================================================================
     4. 渲染
     ====================================================================== */
  /**
   * 逐词标注一行里的改动。
   * st 是本次对比共享的预算：行内 LCS 是 O(词数²)，碰上"整段没有换行"的输入
   * 会变成几十万格。预算用完之后剩下的行就整行标色，不逐词了——结果依然正确，
   * 只是粒度粗一点，换来的是不会把标签页卡死。
   */
  function wordMark(aText, bText, o, st) {
    var ta = tokenize(aText), tb = tokenize(bText);
    var cost = (ta.length + 1) * (tb.length + 1);
    if (cost > 2000000 || st.budget + cost > 6000000) return null;
    st.budget += cost;

    var ka = ta.map(function (t) { return keyOfTok(t, o); });
    var kb = tb.map(function (t) { return keyOfTok(t, o); });
    var ops = align(ka, kb), ha = '', hb = '';
    ops.forEach(function (op) {
      if (op.t === 'same') { ha += esc(ta[op.i]); hb += esc(tb[op.j]); }
      else if (op.t === 'del') ha += '<span class="tl-dw">' + esc(ta[op.i]) + '</span>';
      else hb += '<span class="tl-iw">' + esc(tb[op.j]) + '</span>';
    });
    return { a: ha, b: hb };
  }

  function mark(num, side) {
    return '<span class="tl-dln ' + side + '">' + (num === -1 || num === '-1' ? '' : num) + '</span>';
  }
  function cell(text, side, vac) {
    if (vac) return '<span class="tl-dtx ' + side + ' tl-vac"></span>';
    return '<span class="tl-dtx ' + side + '">' + text + '</span>';
  }

  function rowHtml(r, aLines, bLines, o, st) {
    var aOk = r.a >= 0, bOk = r.b >= 0;
    var la = aOk ? r.a + 1 : -1, lb = bOk ? r.b + 1 : -1;
    if (r.t === 'del') la = '−' + la;
    else if (r.t === 'add') lb = '+' + lb;
    else if (r.t === 'mod') { la = '~' + la; lb = '~' + lb; }

    var ta, tb;
    if (r.t === 'mod') {
      var wt = wordMark(aLines[r.a], bLines[r.b], o, st);
      if (wt) { ta = wt.a; tb = wt.b; }
      else { ta = esc(aLines[r.a]); tb = esc(bLines[r.b]); }
    } else {
      ta = aOk ? esc(aLines[r.a]) : '';
      tb = bOk ? esc(bLines[r.b]) : '';
    }
    return '<div class="tl-drow t-' + r.t + '">' +
      mark(la, 'a') + cell(ta, 'a', !aOk) +
      mark(lb, 'b') + cell(tb, 'b', !bOk) + '</div>';
  }

  function renderRows(box, rows, aLines, bLines, o, fold) {
    if (!box) return;
    var ctx = 2, keep = null, i, n;
    if (fold) {
      keep = new Uint8Array(rows.length);
      for (i = 0; i < rows.length; i++) {
        if (rows[i].t === 'same') continue;
        for (n = Math.max(0, i - ctx); n <= Math.min(rows.length - 1, i + ctx); n++) keep[n] = 1;
      }
    }

    var st = { budget: 0 };
    var html = '<div class="tl-dhead"><span class="tl-dh a">原文</span>' +
      '<span class="tl-dh b">改后</span></div><div class="tl-dbody">';
    var bucket = 0;
    var shown = 0, CUT = 2500;

    function dumpHidden() {
      if (!bucket) return;
      html += '<div class="tl-dmore">… 中间 ' + bucket + ' 行没改动，已折叠</div>';
      bucket = 0;
    }

    for (i = 0; i < rows.length; i++) {
      if (keep && !keep[i]) { bucket++; continue; }
      dumpHidden();
      if (shown >= CUT) continue;
      html += rowHtml(rows[i], aLines, bLines, o, st);
      shown++;
    }
    dumpHidden();
    if (shown >= CUT) html += '<div class="tl-dmore">… 差异太多，先显示前 ' + CUT + ' 行</div>';
    html += '</div>';
    box.innerHTML = html;
    box.className = 'tl-diffwrap on';
  }

  /* ======================================================================
     5. 导出成通用对照格式（unified diff，给开发/文档存证用）
     ====================================================================== */
  function unifiedText(aLines, bLines, rows) {
    var flat = [], i;
    rows.forEach(function (r) {
      if (r.t === 'same') flat.push({ tag: ' ', a: r.a, b: r.b });
      else if (r.t === 'del') flat.push({ tag: '-', a: r.a, b: -1 });
      else if (r.t === 'add') flat.push({ tag: '+', a: -1, b: r.b });
      else { flat.push({ tag: '-', a: r.a, b: -1 }); flat.push({ tag: '+', a: -1, b: r.b }); }
    });

    var marks = [];
    for (i = 0; i < flat.length; i++) if (flat[i].tag !== ' ') marks.push(i);
    if (!marks.length) return '';

    var ctx = 3, groups = [], g = [marks[0]];
    for (i = 1; i < marks.length; i++) {
      if (marks[i] - marks[i - 1] <= ctx * 2 + 1) g.push(marks[i]);
      else { groups.push(g); g = [marks[i]]; }
    }
    groups.push(g);

    var out = ['--- 原文', '+++ 改后'];
    groups.forEach(function (grp) {
      var s = Math.max(0, grp[0] - ctx);
      var e = Math.min(flat.length - 1, grp[grp.length - 1] + ctx);
      var aStart = 0, bStart = 0, aCount = 0, bCount = 0, body = [];
      for (i = s; i <= e; i++) {
        var op = flat[i];
        if (op.a >= 0) { if (!aCount) aStart = op.a + 1; aCount++; }
        if (op.b >= 0) { if (!bCount) bStart = op.b + 1; bCount++; }
        body.push(op.tag + (op.tag === '+' ? bLines[op.b] : aLines[op.a]));
      }
      out.push('@@ -' + aStart + ',' + aCount + ' +' + bStart + ',' + bCount + ' @@');
      out = out.concat(body);
    });
    return out.join('\n') + '\n';
  }

  /* ======================================================================
     6. 装配
     ====================================================================== */
  var MAX_LINES = 4000;       // 单边行数上限
  var MAX_CELLS = 2500000;    // 对齐表格上限（约 1580 × 1580）

  function setupDiff() {
    var P = panelOf('diff');
    if (!P) return;

    var box = P.querySelector('[data-diffout]');
    var last = null;            // 上一次的结果，供"复制/下载"用

    function opts() {
      return {
        ic: !!valOf(P, 'ic'),
        tw: !!valOf(P, 'tw'),
        ws: !!valOf(P, 'ws'),
        fold: !!valOf(P, 'fold')
      };
    }

    function run() {
      clearToast(P);
      var a = String(valOf(P, 'ta') == null ? '' : valOf(P, 'ta'));
      var b = String(valOf(P, 'tb') == null ? '' : valOf(P, 'tb'));

      if (!a && !b) {
        toast(P, '先在「原文」和「改后」里各贴一段文字。', 'err');
        return;
      }
      if (a === b) {
        last = null;
        setStat(P, [['结果', '两边一模一样'], ['原文行数', String(splitLines(a).length)]],
          '一个字都没差，没有需要标出来的地方。');
        if (box) { box.innerHTML = ''; box.className = 'tl-diffwrap'; }
        return;
      }

      var aLines = splitLines(a), bLines = splitLines(b);
      if (aLines.length > MAX_LINES || bLines.length > MAX_LINES) {
        toast(P, '一边超过 ' + MAX_LINES + ' 行了，先分成两段再比。', 'err');
        return;
      }
      if (aLines.length * bLines.length > MAX_CELLS) {
        toast(P, '两边分别是 ' + aLines.length + ' 行和 ' + bLines.length +
          ' 行，逐行两两比对超出一次能算的范围。把两边裁剪短一些，或者分成两段再比。', 'err');
        return;
      }

      toast(P, '正在逐行对照…', 'ok');
      setTimeout(function () { compute(aLines, bLines); }, 0);
    }

    function compute(aLines, bLines) {
      var o = opts();
      var rows = buildRows(aLines, bLines, o);

      var same = 0, mod = 0, add = 0, del = 0;
      rows.forEach(function (r) {
        if (r.t === 'same') same++;
        else if (r.t === 'mod') mod++;
        else if (r.t === 'add') add++;
        else del++;
      });

      var pct = Math.round((same / Math.max(1, Math.max(aLines.length, bLines.length))) * 100);
      setStat(P, [
        ['原文行数', String(aLines.length)],
        ['改后行数', String(bLines.length)],
        ['没有变', same + ' 行'],
        ['改动了', mod + ' 行'],
        ['新增', add + ' 行'],
        ['删除', del + ' 行'],
        ['相同比例', pct + '%']
      ], '左边是原文、右边是改后，两边行号对齐。' +
        '<b>朱红</b>是删掉的内容（带 − 号），<b>金色</b>是新增的（带 + 号），' +
        '带 ~ 号的是同一行改写，行内染色的字词才是真正变了的部分。' +
        '<br>比较口径：' + (o.ic ? '忽略大小写；' : '') + (o.tw ? '忽略每行首尾空白；' : '') +
        (o.ws ? '连续空白折叠成一个；' : '') +
        (!o.ic && !o.tw && !o.ws ? '严格逐字符比较（可在上面勾选忽略项）。' : '') +
        '<br>「相同比例」= 没有变化的行数 ÷ 两边较多的行数。');

      renderRows(box, rows, aLines, bLines, o, o.fold);
      last = { a: aLines, b: bLines, rows: rows };
      clearToast(P);
      if (!same && !mod && !add && !del) toast(P, '两段文字的结构不一样，已经按整段替换标出来了。', 'ok');
    }

    function splitLines(s) {
      return s.replace(/\r\n?/g, '\n').split('\n');
    }

    var ACTS = {
      run: run,
      swap: function () {
        var a = valOf(P, 'ta'), b = valOf(P, 'tb');
        setVal('ta', b); setVal('tb', a);
        run();
      },
      clear: function () {
        setVal('ta', ''); setVal('tb', '');
        last = null;
        clearToast(P);
        setStat(P, null);
        if (box) { box.innerHTML = ''; box.className = 'tl-diffwrap'; }
      },
      copyB: function () {
        var b = String(valOf(P, 'tb') == null ? '' : valOf(P, 'tb'));
        if (!b) { toast(P, '「改后」这一栏是空的。', 'err'); return; }
        copyText(b).then(function () {
          toast(P, '改后全文已经复制到剪贴板了。', 'ok');
        }, function (e) {
          toast(P, (e && e.message) || '这个浏览器不允许自动复制，请手动选中。', 'err');
        });
      },
      dl: function () {
        if (!last) { toast(P, '先点一次「开始对比」，有结果了才能导出。', 'err'); return; }
        var txt = unifiedText(last.a, last.b, last.rows);
        if (!txt) { toast(P, '两边没有差异，导出的是空文件，就不生成了。', 'err'); return; }
        download(new Blob([txt], { type: 'text/plain;charset=utf-8' }), '文本对比结果.txt');
        toast(P, '已经生成对照文件，按标准的 diff 格式写的。', 'ok');
      }
    };

    function setVal(name, v) {
      var el = P.querySelector('[data-in="' + name + '"]');
      if (el) el.value = v == null ? '' : String(v);
    }

    // 「折叠没变的行」改一下就重画，不用重新点对比
    var foldEl = P.querySelector('[data-in="fold"]');
    if (foldEl) {
      foldEl.addEventListener('change', function () {
        if (!last || !box) return;
        renderRows(box, last.rows, last.a, last.b, opts(), !!foldEl.checked);
      });
    }

    $$('[data-act]', P).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var fn = ACTS[btn.getAttribute('data-act')];
        if (fn) fn();
      });
    });
  }

  window.LXTools.define('diff', setupDiff);
})();
