/**
 * solar-term.js — 首页「节气钟」
 * 按日期算当前 24 节气 + 距下一节气倒计时 + 当日物候/一句/香事。
 * 算法：21 世纪寿星公式，y=年份后两位，L=floor(y/4)，±1 天误差（显示标“约”）。
 * 纯客户端，无依赖、无后端。
 */
(function () {
  var TERMS = ['小寒', '大寒', '立春', '雨水', '惊蛰', '春分', '清明', '谷雨',
    '立夏', '小满', '芒种', '夏至', '小暑', '大暑', '立秋', '处暑',
    '白露', '秋分', '寒露', '霜降', '立冬', '小雪', '大雪', '冬至'];
  var C = [5.4055, 20.12, 3.87, 18.73, 5.63, 20.646, 4.81, 20.1, 5.52, 21.04,
    5.678, 21.37, 7.108, 22.83, 7.5, 23.13, 7.646, 23.042, 8.318, 23.438,
    7.438, 22.36, 7.18, 21.94];
  var MONTH = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12];

  var INFO = {
    '立春': { phen: '东风解冻 · 蛰虫始振 · 鱼陟负冰', poem: '律回岁晚冰霜少，春到人间草木知', inc: '焚甘松，启户迎新' },
    '雨水': { phen: '獭祭鱼 · 候雁北 · 草木萌动', poem: '随风潜入夜，润物细无声', inc: '煮雨前茶，配淡淡白檀' },
    '惊蛰': { phen: '桃始华 · 仓庚鸣 · 鹰化为鸠', poem: '微雨众卉新，一雷惊蛰始', inc: '焚艾草，驱晦醒神' },
    '春分': { phen: '玄鸟至 · 雷乃发声 · 始电', poem: '仲春初四日，春色正中分', inc: '焚玫瑰檀，调和肝脾' },
    '清明': { phen: '桐始华 · 田鼠化鴽 · 虹始见', poem: '清明时节雨纷纷', inc: '焚柏子，清心明志' },
    '谷雨': { phen: '萍始生 · 鸣鸠拂羽 · 戴胜降桑', poem: '谷雨春光晓，山川黛色青', inc: '焙新茶，配沉香尾韵' },
    '立夏': { phen: '蝼蝈鸣 · 蚯蚓出 · 王瓜生', poem: '绿树阴浓夏日长', inc: '焚薄荷配檀，清暑' },
    '小满': { phen: '苦菜秀 · 靡草死 · 麦秋至', poem: '小满江河易满', inc: '焚藿香，化湿和中' },
    '芒种': { phen: '螳螂生 · 鵙始鸣 · 反舌无声', poem: '时雨及芒种，四野皆插秧', inc: '田家焚艾，驱虫祈丰' },
    '夏至': { phen: '鹿角解 · 蜩始鸣 · 半夏生', poem: '昼晷已云极，宵漏自此长', inc: '焚沉香，静心避暑' },
    '小暑': { phen: '温风至 · 蟋蟀居壁 · 鹰始鸷', poem: '倏忽温风至，因循小暑来', inc: '焚清香，纳凉读史' },
    '大暑': { phen: '腐草为萤 · 土润溽暑 · 大雨时行', poem: '桂轮开子夜，萤火照空时', inc: '焚龙涎，化湿醒神' },
    '立秋': { phen: '凉风至 · 白露降 · 寒蝉鸣', poem: '一叶梧桐一报秋', inc: '焚桂花沉，迎秋' },
    '处暑': { phen: '鹰乃祭鸟 · 天地始肃 · 禾乃登', poem: '离离暑云散，袅袅凉风起', inc: '焚菊檀，肃净心神' },
    '白露': { phen: '鸿雁来 · 玄鸟归 · 群鸟养羞', poem: '蒹葭苍苍，白露为霜', inc: '焚白檀，润燥' },
    '秋分': { phen: '雷始收声 · 蛰虫坯户 · 水始涸', poem: '金气秋分，风清露冷秋期半', inc: '焚沉香，平分昼夜' },
    '寒露': { phen: '鸿雁来宾 · 雀入水为蛤 · 菊有黄华', poem: '袅袅凉风动，凄凄寒露零', inc: '焚茱萸配沉，暖身' },
    '霜降': { phen: '豺乃祭兽 · 草木黄落 · 蛰虫咸俯', poem: '霜叶红于二月花', inc: '焚桂皮香，温中' },
    '立冬': { phen: '水始冰 · 地始冻 · 雉入大水', poem: '冻笔新诗懒写，寒炉美酒时温', inc: '焚沉香，围炉' },
    '小雪': { phen: '虹藏不见 · 天气上升 · 闭塞成冬', poem: '久雨重阳后，清寒小雪前', inc: '焚甘松，温室' },
    '大雪': { phen: '鹖鴠不鸣 · 虎始交 · 荔挺出', poem: '夜深知雪重，时闻折竹声', inc: '焚暖香，御寒' },
    '冬至': { phen: '蚯蚓结 · 麋角解 · 水泉动', poem: '天时人事日相催，冬至阳生春又来', inc: '焚沉香，一阳来复' },
    '小寒': { phen: '雁北乡 · 鹊始巢 · 雉始雊', poem: '小寒料峭，一番春意换年芳', inc: '围炉焚沉，静待春信' },
    '大寒': { phen: '鸡始乳 · 征鸟厉疾 · 水泽腹坚', poem: '旧雪未及消，新雪又拥户', inc: '煮茶配檀，岁末清供' }
  };

  function termDate(year, n) {
    var y = year % 100;
    var day = Math.floor(y * 0.2422 + C[n - 1]) - Math.floor(y / 4);
    return new Date(year, MONTH[n - 1] - 1, day);
  }

  function pad(d) { return (d < 10 ? '0' : '') + d; }
  function fmt(dt) { return dt.getFullYear() + '.' + pad(dt.getMonth() + 1) + '.' + pad(dt.getDate()); }

  function render() {
    var el = document.getElementById('solarTerm');
    if (!el) return;

    var now = new Date();
    var y = now.getFullYear();
    var dates = [];
    for (var i = 1; i <= 24; i++) dates.push(termDate(y, i));

    var cur = 23;
    for (var i = 0; i < 24; i++) { if (dates[i] <= now) cur = i; }

    var curName, curDate, nextName, nextDate;
    if (cur >= 0 && dates[cur] <= now) {
      curName = TERMS[cur]; curDate = dates[cur];
      var ni = cur + 1;
      if (ni < 24) { nextName = TERMS[ni]; nextDate = dates[ni]; }
      else { nextName = TERMS[0]; nextDate = termDate(y + 1, 1); }
    } else {
      curName = TERMS[23]; curDate = termDate(y - 1, 24);
      nextName = TERMS[0]; nextDate = dates[0];
    }

    var days = Math.ceil((nextDate - now) / 86400000);
    var info = INFO[curName] || { phen: '', poem: '', inc: '' };

    el.innerHTML =
      '<div class="st-term">' + curName + '</div>' +
      '<div class="st-sub">' + fmt(curDate) + ' – ' + fmt(nextDate) + '（约）</div>' +
      '<div class="st-count">距 <b>' + nextName + '</b> 还有 <b>' + days + '</b> 天</div>' +
      '<div class="st-phen">' + info.phen + '</div>' +
      '<div class="st-poem">「' + info.poem + '」</div>' +
      '<div class="st-inc">香事 · ' + info.inc + '</div>';
  }

  if (document.readyState !== 'loading') render();
  else document.addEventListener('DOMContentLoaded', render);
})();
