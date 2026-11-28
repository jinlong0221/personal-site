/*!
 * tools/pwd.js — 本地密码生成器（工具箱·按需加载子模块）
 *
 * 在浏览器里用 crypto.getRandomValues 现生成高强度随机密码，绝不联网、绝不上传、绝不留存。
 * 默认去掉 0/O、1/l 这类易混字符，可勾选放回来；长度、字符类自由组合，并显示理论熵。
 *
 * 生成策略：每个勾选的字符类至少出现一次（前几位各放一个），其余随机填满，再整体洗牌，
 * 既保证「该有的类都有」，又不会让前几位暴露规律。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $ = _.$, $$ = _.$$;
  var field = _.field, valOf = _.valOf, numOf = _.numOf, setStat = _.setStat, toast = _.toast, clearToast = _.clearToast, panelOf = _.panelOf, copyText = _.copyText;

  function randInt(n) {
    var a = new Uint32Array(1);
    crypto.getRandomValues(a);
    return a[0] % n;
  }
  function gen(len, opts) {
    var low = opts.amb ? 'abcdefghijklmnopqrstuvwxyz' : 'abcdefghijkmnpqrstuvwxyz';
    var up = opts.amb ? 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' : 'ABCDEFGHJKLMNPQRSTUVWXYZ';
    var dig = opts.amb ? '0123456789' : '23456789';
    var sym = '!@#$%^&*()-_=+[]{};:,.<>?';
    var pools = [];
    if (opts.lower) pools.push(low);
    if (opts.upper) pools.push(up);
    if (opts.digit) pools.push(dig);
    if (opts.sym) pools.push(sym);
    if (!pools.length) return '';
    var all = pools.join('');
    var out = [];
    for (var i = 0; i < Math.min(len, pools.length); i++) out.push(pools[i].charAt(randInt(pools[i].length)));
    for (var j = out.length; j < len; j++) out.push(all.charAt(randInt(all.length)));
    for (var k = out.length - 1; k > 0; k--) { var r = randInt(k + 1); var tmp = out[k]; out[k] = out[r]; out[r] = tmp; } // Fisher–Yates 洗牌
    return out.join('');
  }
  function entropy(len, poolN) { return Math.round(len * Math.log2(poolN || 1) * 10) / 10; }

  function setupPwd() {
    var P = panelOf('pwd');
    if (!P) return;

    function run() {
      clearToast(P);
      var len = Math.max(4, Math.min(64, Math.floor(numOf(P, 'len', 12))));
      var opts = {
        lower: !!valOf(P, 'lower'), upper: !!valOf(P, 'upper'),
        digit: !!valOf(P, 'digit'), sym: !!valOf(P, 'sym'), amb: !!valOf(P, 'amb')
      };
      var pw = gen(len, opts);
      if (!pw) { toast(P, '至少勾选一种字符（大写 / 小写 / 数字 / 符号）。', 'err'); return; }
      var poolN = (opts.lower ? 1 : 0) + (opts.upper ? 1 : 0) + (opts.digit ? 1 : 0) + (opts.sym ? 1 : 0);
      var e = entropy(len, poolN);
      var box = $('[data-out="pw"]', P);
      if (box) box.textContent = pw;
      var lo = $('[data-out="leno"]', P);
      if (lo) lo.textContent = String(len);
      var cells = [
        ['长度', String(len) + ' 位'],
        ['字符池', poolN + ' 类共 ' + pw.length + ' 个字符'],
        ['理论熵', e + ' bit']
      ];
      var note = '密码在浏览器里用 crypto.getRandomValues 现生成，<b>绝不联网、绝不上传</b>。熵越高越难被猜中：' +
        '12 位四类密码约 ' + e + ' bit，普通离线爆破基本够用；要更高就加长或加字符类。' +
        '默认已去掉 0/O、1/l 这类易混字符，可勾选「保留易混字符」放回来。';
      setStat(P, cells, note);
    }

    $$('[data-act]', P).forEach(function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act');
        if (act === 'gen') return run();
        if (act === 'copy') {
          var box = $('[data-out="pw"]', P);
          if (box && box.textContent) { copyText(box.textContent); toast(P, '已复制到剪贴板。', 'ok'); }
          return;
        }
      });
    });
    var li = field(P, 'len'); li && li.addEventListener('input', run);
    ['lower', 'upper', 'digit', 'sym', 'amb'].forEach(function (k) {
      var el = field(P, k); el && el.addEventListener('change', run);
    });
    run();
  }

  window.LXTools.define('pwd', setupPwd);
})();
