/**
 * daily-item.js — 首页「每日一物」
 * 按日期确定性轮换展示一个国风知识卡（沉香/中药/紫砂/养生/文玩），
 * 同一天所有人看到同一物；可点「换一个」临时随机。
 */
(function () {
  var ITEMS = [
    { name: '紫砂 · 紫泥', cat: '紫砂', one: '沉稳温润，最宜泡茶的骨', detail: '紫泥透气而不渗，养久生包浆。一把好壶，是岁月与手掌共同写就。' },
    { name: '紫砂 · 朱泥', cat: '紫砂', one: '红润细腻，扬香利器', detail: '朱泥密度高、聚香好，最宜乌龙、高香红茶，出汤利落。' },
    { name: '紫砂 · 段泥', cat: '紫砂', one: '清雅米黄，显汤色', detail: '段泥砂质疏朗，宜绿茶、白茶，茶汤清亮，壶色也养得干净。' },
    { name: '文玩 · 沉香手串', cat: '文玩', one: '腕间一缕随体温醒的香', detail: '沉香珠不靠抛光夺目，靠体温慢慢唤醒油脂香，是低调的体己。' },
    { name: '文玩 · 星月菩提', cat: '文玩', one: '盘玩见性的修行物件', detail: '星月菩提盘久开片、挂瓷包浆，急不得——像许多事，慢即是快。' },
    { name: '养生 · 节气茶饮', cat: '养生', one: '顺时而饮，比进补更要紧', detail: '春饮花、夏饮绿、秋饮青、冬饮红。顺着节气喝茶，身体自有主张。' },
    { name: '养生 · 焚香静坐', cat: '养生', one: '十分钟香气里的松驰', detail: '不必繁文缛节，燃一炉沉香、闭目片刻，便是给神经的一次深呼吸。' },
  ];

  function dayIndex() {
    var d = new Date();
    var key = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);
    return ((key % ITEMS.length) + ITEMS.length) % ITEMS.length;
  }

  function card(it) {
    return '<div class="di-cat">' + it.cat + '</div>' +
      '<div class="di-name">' + it.name + '</div>' +
      '<div class="di-one">' + it.one + '</div>' +
      '<div class="di-detail">' + it.detail + '</div>' +
      '<button class="di-shuffle" id="dailyShuffle">换一个 ↻</button>';
  }

  function render(seed) {
    var el = document.getElementById('dailyItem');
    if (!el) return;
    var i;
    if (typeof seed === 'number') i = seed;
    else i = dayIndex();
    el.innerHTML = card(ITEMS[i]);
  }

  function init() {
    render();
    document.addEventListener('click', function (e) {
      var b = e.target && e.target.closest && e.target.closest('#dailyShuffle');
      if (b) {
        var r = Math.floor(Math.random() * ITEMS.length);
        render(r);
      }
    });
  }

  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
