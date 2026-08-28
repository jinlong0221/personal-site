/**
 * daily-item.js — 首页「每日一物」
 * 按日期确定性轮换展示一个国风知识卡（沉香/中药/紫砂/养生/文玩），
 * 同一天所有人看到同一物；可点「换一个」临时随机。
 */
(function () {
  var ITEMS = [
    { name: '沉香 · 生结', cat: '沉香', one: '活体自然创伤处凝脂，香气清扬通透', detail: '生结出于活树自然伤口，油脂线随木纹游走。上炉甜凉入喉，最宜静心独坐。' },
    { name: '沉香 · 熟结', cat: '沉香', one: '树身枯朽埋土，岁月醇化而成', detail: '熟结脱胎于腐朽，香韵醇厚绵长，是时间替你封存的沉静。' },
    { name: '沉香 · 虫漏', cat: '沉香', one: '蚁虫啃噬结香，纹如蜂房', detail: '虫漏因小虫而起，结油奇特，香中带一丝野趣与清甜。' },
    { name: '沉香 · 奇楠', cat: '沉香', one: '削之成卷、嚼之黏牙的香中舍利', detail: '奇楠软糯生香，凉韵直透百会。可遇不可求，是沉香里的“舍利”。' },
    { name: '檀香 · 老山', cat: '沉香', one: '甜润稳重的基底之香', detail: '老山檀是合香之骨，温润不燥，常与沉香为伴，支撑起一炉的底色。' },
    { name: '艾草', cat: '中药', one: '端午悬门，寻常却通阳', detail: '艾性温通，灸火可驱寒湿。民谚“家有三年艾，郎中不用来”。' },
    { name: '藿香', cat: '中药', one: '化湿和中，暑天良友', detail: '藿香正气之源，夏日胸闷呕恶时，一缕药香便能安宁肠胃。' },
    { name: '甘草', cat: '中药', one: '十方九草，和事之老', detail: '甘草调和诸药，甘缓守中。一味不起眼，却让一剂汤药有了温度。' },
    { name: '桂花', cat: '中药', one: '秋分之香，可食可薰', detail: '桂花温肺暖胃，糖渍入茶、干品入薰，一室都是故园的甜。' },
    { name: '紫砂 · 紫泥', cat: '紫砂', one: '沉稳温润，最宜泡茶的骨', detail: '紫泥透气而不渗，养久生包浆。一把好壶，是岁月与手掌共同写就。' },
    { name: '紫砂 · 朱泥', cat: '紫砂', one: '红润细腻，扬香利器', detail: '朱泥密度高、聚香好，最宜乌龙、高香红茶，出汤利落。' },
    { name: '紫砂 · 段泥', cat: '紫砂', one: '清雅米黄，显汤色', detail: '段泥砂质疏朗，宜绿茶、白茶，茶汤清亮，壶色也养得干净。' },
    { name: '文玩 · 沉香手串', cat: '文玩', one: '腕间一缕随体温醒的香', detail: '沉香珠不靠抛光夺目，靠体温慢慢唤醒油脂香，是低调的体己。' },
    { name: '文玩 · 星月菩提', cat: '文玩', one: '盘玩见性的修行物件', detail: '星月菩提盘久开片、挂瓷包浆，急不得——像许多事，慢即是快。' },
    { name: '养生 · 节气茶饮', cat: '养生', one: '顺时而饮，比进补更要紧', detail: '春饮花、夏饮绿、秋饮青、冬饮红。顺着节气喝茶，身体自有主张。' },
    { name: '养生 · 焚香静坐', cat: '养生', one: '十分钟香气里的松驰', detail: '不必繁文缛节，燃一炉沉香、闭目片刻，便是给神经的一次深呼吸。' },
    { name: '沉香 · 上炉', cat: '沉香', one: '隔火熏香，不烟不火', detail: '云母片隔火，炭温逼香不出烟。慢火文熏，香气才不焦不燥，层层绽开。' },
    { name: '香道 · 品香', cat: '沉香', one: '鼻观里的山水', detail: '品香先净手静心，三巡而止。香无定味，随心境流转，是独与天地往来的事。' }
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
