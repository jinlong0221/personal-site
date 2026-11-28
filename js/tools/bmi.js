/*!
 * tools/bmi.js — BMI / 健康计算（工具箱·按需加载子模块）
 *
 * 填身高（cm）与体重（kg），算 BMI 与分类（中国标准），以及健康体重范围。
 * 全部在用户设备上算，不联网、不读任何外部数据。
 *
 * 分类按中国成人 BMI 标准：<18.5 偏瘦、18.5–23.9 正常、24–27.9 超重、≥28 肥胖。
 * BMI 不区分肌肉与脂肪，健身人群会偏高，仅作粗略参考。
 */
(function () {
  'use strict';

  var _ = (window.LXTools || {}).api;
  if (!_) return;

  var $ = _.$, $$ = _.$$;
  var field = _.field, valOf = _.valOf, numOf = _.numOf, setStat = _.setStat, toast = _.toast, clearToast = _.clearToast, panelOf = _.panelOf;

  function cat(bmi) {
    if (bmi < 18.5) return ['偏瘦', '#4da6e8'];
    if (bmi < 24) return ['正常', '#3fb950'];
    if (bmi < 28) return ['超重', '#e3b341'];
    return ['肥胖', '#e5534b'];
  }

  function setupBmi() {
    var P = panelOf('bmi');
    if (!P) return;

    function run() {
      clearToast(P);
      var h = numOf(P, 'h', NaN), w = numOf(P, 'w', NaN);
      if (!isFinite(h) || !isFinite(w) || h <= 0 || w <= 0) { toast(P, '先填身高（cm）和体重（kg）。', 'err'); return; }
      var m = h / 100;
      var bmi = w / (m * m);
      var c = cat(bmi);
      var idealLo = 18.5 * m * m, idealHi = 23.9 * m * m;
      var cells = [
        ['BMI', bmi.toFixed(1)],
        ['分类（中国标准）', c[0]],
        ['健康体重范围', idealLo.toFixed(1) + ' ~ ' + idealHi.toFixed(1) + ' kg']
      ];
      var note = 'BMI = 体重(kg) ÷ 身高(m)²。分类按中国标准：<18.5 偏瘦、18.5–23.9 正常、24–27.9 超重、≥28 肥胖。' +
        'BMI 不区分肌肉和脂肪，健身人群会偏高；只作粗略参考，不代表健康全貌。';
      setStat(P, cells, note);
      var box = $('[data-out="bmicat"]', P);
      if (box) { box.textContent = c[0]; box.style.color = c[1]; }
    }

    $$('[data-act]', P).forEach(function (b) {
      if (b.getAttribute('data-act') === 'calc') b.addEventListener('click', run);
    });
    var hi = field(P, 'h'); hi && hi.addEventListener('input', run);
    var wi = field(P, 'w'); wi && wi.addEventListener('input', run);
    if (hi && !hi.value) hi.value = '170';
    if (wi && !wi.value) wi.value = '65';
    run();
  }

  window.LXTools.define('bmi', setupBmi);
})();
