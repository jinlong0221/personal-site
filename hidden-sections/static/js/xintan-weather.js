/* 新坍镇农田气象 —— 运行时数据获取 + 渲染
 * 设计：stale-while-revalidate
 *   - 页面打开先渲染本地缓存（localStorage）里上一次成功的数据，绝不空白；
 *   - 后台再向 Open-Meteo 拉最新；成功则更新缓存并刷新；
 *   - 拉取失败（国内网络偶尔连不上境外 API）则保留缓存数据，并提示「数据可能过期」。
 *   - fetch 带 9 秒超时，避免一直转圈。
 */
(function () {
  var LAT = 33.76, LON = 120.09;
  var CACHE_KEY = 'xw_weather_cache_v1';
  var CACHE_TTL = 3 * 60 * 60 * 1000; // 3 小时

  var codes = { 0:'☀️',1:'🌤️',2:'⛅',3:'☁️',45:'🌫️',48:'🌫️',51:'🌦️',53:'🌦️',55:'🌧️',61:'🌧️',63:'🌧️',65:'🌧️',71:'🌨️',73:'🌨️',75:'❄️',77:'🌨️',80:'🌦️',81:'🌧️',82:'⛈️',85:'🌨️',86:'🌨️',95:'⛈️',96:'⛈️',99:'⛈️' };
  var names = { 0:'晴',1:'晴间多云',2:'多云',3:'阴',45:'雾',48:'冻雾',51:'小毛毛雨',53:'毛毛雨',55:'大毛毛雨',61:'小雨',63:'中雨',65:'大雨',71:'小雪',73:'中雪',75:'大雪',77:'雨夹雪',80:'阵雨',81:'阵雨中雨',82:'大阵雨',85:'雨夹雪',86:'大阵雪',95:'雷暴',96:'雷阵雨',99:'强雷暴' };

  /* ---------- 本地缓存 ---------- */
  function loadCache() {
    try {
      var s = localStorage.getItem(CACHE_KEY);
      if (!s) return null;
      var o = JSON.parse(s);
      if (!o || !o.data || !o.data.current) return null;
      return o;
    } catch (e) { return null; }
  }
  function saveCache(om) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: om })); } catch (e) {}
  }
  function cacheAgeText(ts) {
    var mins = Math.round((Date.now() - ts) / 60000);
    if (mins < 1) return '刚刚';
    if (mins < 60) return mins + ' 分钟前';
    var h = Math.floor(mins / 60);
    if (h < 24) return h + ' 小时前';
    return Math.floor(h / 24) + ' 天前';
  }

  /* ---------- 数据获取（带超时） ---------- */
  function fetchWeather() {
    var url = 'https://api.open-meteo.com/v1/forecast'
      + '?latitude=' + LAT + '&longitude=' + LON
      + '&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation'
      + '&hourly=temperature_2m,precipitation_probability,weather_code'
      + '&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,sunrise,sunset'
      + '&timezone=Asia/Shanghai&forecast_days=3';
    var ctrl = new AbortController();
    var to = setTimeout(function () { ctrl.abort(); }, 9000);
    return fetch(url, { signal: ctrl.signal })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .finally(function () { clearTimeout(to); });
  }

  /* ---------- 渲染 ---------- */
  function render(om, noteHtml) {
    if (!om || !om.current) return false;
    var now = new Date(), hourIdx = now.getHours(), month = now.getMonth() + 1;
    var c = om.current, h = om.hourly, daily = om.daily;
    var t = Math.round(c.temperature_2m), fl = Math.round(c.apparent_temperature);
    var wind = Math.round(c.wind_speed_10m || 0);
    var hum = c.relative_humidity_2m || 0, rain = Math.round(c.precipitation || 0);

    var curIcon = codes[c.weather_code] || '🌡️';
    var curName = names[c.weather_code] || '未知';

    var sourceHtml = '<div class="xw-source"><span>🌐 <a id="sources" class="src-anchor"></a>数据来源：Open-Meteo</span></div>'
      + '<p class="ref-note">实时观测（温度 / 湿度 / 风 / 降水）来自 Open-Meteo，页面每次加载即取最新；农事指标与常年气候参数为人工整理，截至 2026-08，已交叉核对。'
      + (noteHtml || '') + '</p>';

    var curHtml = '<div class="xw-current">'
      + '<div class="xw-cur-icon">' + curIcon + '</div>'
      + '<div class="xw-cur-info">'
      + '<div class="xw-cur-name">' + curName + '</div>'
      + '<div class="xw-cur-time">' + now.getHours() + ':00 更新</div>'
      + '</div>'
      + '<div class="xw-cur-temp">' + t + '<span>°C</span></div>'
      + '</div>'
      + sourceHtml
      + '<div class="xw-grid">'
      + '<div class="xw-item"><div class="xw-item-label">🌡️ 体感温度</div><div class="xw-item-val">' + fl + '°C</div></div>'
      + '<div class="xw-item"><div class="xw-item-label">💧 相对湿度</div><div class="xw-item-val">' + hum + '%</div></div>'
      + '<div class="xw-item"><div class="xw-item-label">🌬️ 风速</div><div class="xw-item-val">' + wind + ' km/h</div></div>'
      + '<div class="xw-item"><div class="xw-item-label">🌧️ 降水</div><div class="xw-item-val">' + (rain > 0 ? rain + 'mm' : '无') + '</div></div>'
      + '</div>'
      + '<div class="xw-grid" style="margin-top:-8px;padding-top:0">'
      + '<div class="xw-item"><div class="xw-item-label">⬆️ 今日最高</div><div class="xw-item-val" style="color:#e65100">' + Math.round(daily.temperature_2m_max[0]) + '°C</div></div>'
      + '<div class="xw-item"><div class="xw-item-label">⬇️ 今日最低</div><div class="xw-item-val" style="color:#1565c0">' + Math.round(daily.temperature_2m_min[0]) + '°C</div></div>'
      + '<div class="xw-item"><div class="xw-item-label">🌅 日出/日落</div><div class="xw-item-val" style="font-size:0.7rem">' + (daily.sunrise[0] || '').slice(11, 16) + '/' + (daily.sunset[0] || '').slice(11, 16) + '</div></div>'
      + '<div class="xw-item"><div class="xw-item-label">💧 今日降水</div><div class="xw-item-val">' + Math.round(daily.precipitation_sum[0]) + 'mm</div></div>'
      + '</div>';

    /* ===== 灾害检测 ===== */
    var alerts = [];
    if (rain > 25) alerts.push({ t:'🌧️ 暴雨', m:'当前降水量' + rain + 'mm，请检查田间排水通畅，低洼田块及时排涝', l:'danger' });
    else if (rain >= 10) alerts.push({ t:'🌧️ 中到大雨', m:'注意清沟理墒，防止作物受淹', l:'warn' });
    if (wind >= 50) alerts.push({ t:'🌬️ 强风/大风', m:'请固定大棚支架、收拢薄膜，严防作物倒伏', l:'danger' });
    else if (wind >= 25) alerts.push({ t:'🌬️ 大风', m:'注意大棚薄膜撕裂，露天作物防倒伏', l:'warn' });
    var todayMin = daily.temperature_2m_min[0];
    if (todayMin < 2) alerts.push({ t:'❄️ 霜冻/低温', m:'气温接近冰点，覆盖作物保温（加盖草帘），防止冻害', l:'danger' });
    else if (todayMin < 5) alerts.push({ t:'❄️ 低温预警', m:'夜间保温，大棚加盖内膜或保温被', l:'warn' });
    if (c.weather_code >= 95) alerts.push({ t:'⛈️ 雷暴', m:'避免户外作业，切断露天地头电源，注意人员安全', l:'danger' });
    var rainyDays = 0; for (var di = 0; di < 3; di++) if (daily.precipitation_sum[di] > 1) rainyDays++;
    if (rainyDays >= 3) alerts.push({ t:'🌧️ 连续阴雨', m:'未来3天多阴雨，关注排水，防治纹枯病/白粉病蔓延', l:'warn' });

    /* ===== 3日预报 ===== */
    var fcTags = ['今天','明天','后天'];
    var fcHtml = '';
    for (var di = 0; di < 3; di++) {
      var dmax = Math.round(daily.temperature_2m_max[di]);
      var dmin = Math.round(daily.temperature_2m_min[di]);
      var dwc = daily.weather_code[di], dp = Math.round(daily.precipitation_sum[di]);
      var dname = names[dwc] || '未知';
      var tags = [];
      if (dwc >= 95) tags.push('防雷');
      if (dp > 15) tags.push('防涝');
      if (dmin < 5) tags.push('防霜');
      if (dwc <= 3 && dmax > 25) tags.push('打药');
      if (dwc === 0 && dp === 0) tags.push('晾晒');
      if (dwc <= 1 && dmax >= 20 && dmax <= 30) tags.push('施肥');
      if (tags.length === 0) tags.push('田间管理');
      var tagsHtml = tags.slice(0, 3).map(function (x) { return '<span class="xw-tag">' + x + '</span>'; }).join('');
      var isToday = di === 0 ? 'border-color:var(--gold);' : '';
      fcHtml += '<div class="xw-day" style="' + isToday + '">'
        + '<div class="xw-day-label">' + fcTags[di] + '</div>'
        + '<div class="xw-day-icon">' + (codes[dwc] || '🌡️') + '</div>'
        + '<div class="xw-day-temp">' + dmax + '°<span>/' + dmin + '°</span></div>'
        + '<div class="xw-day-desc">' + dname + ' · 降水' + dp + 'mm</div>'
        + '<div class="xw-day-tags">' + tagsHtml + '</div></div>';
    }

    /* ===== 逐时预报 · 每3小时一览 ===== */
    var hourlyHtml = '';
    if (!h.temperature_2m || !h.weather_code || !h.time) {
      hourlyHtml = '<div style="padding:16px;color:var(--text-muted)">逐时数据加载中…</div>';
    } else {
      var alignedHour = Math.floor(hourIdx / 3) * 3;
      var startIdx = alignedHour;
      if (hourIdx - alignedHour >= 2) startIdx = alignedHour + 3;
      var currentDay = '';
      function fmtLocalDate(d) { return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
      for (var hi = 0; hi < 24; hi += 3) {
        var realIdx = startIdx + hi;
        if (realIdx >= h.time.length) break;
        var rawHour = h.time[realIdx].slice(11, 16);
        var hIcon = codes[h.weather_code[realIdx]] || '🌡️';
        var hTemp = Math.round(h.temperature_2m[realIdx]);
        var hRain = h.precipitation_probability[realIdx] || 0;
        var dateStr = h.time[realIdx].slice(0, 10);
        var dayLabel = '';
        if (dateStr !== currentDay) {
          currentDay = dateStr;
          var todayStr = new Date(); todayStr.setHours(0, 0, 0, 0);
          var todayISO = fmtLocalDate(todayStr);
          var tomorrow = new Date(todayStr); tomorrow.setDate(tomorrow.getDate() + 1);
          var tomorrowISO = fmtLocalDate(tomorrow);
          var dayAfter = new Date(todayStr); dayAfter.setDate(dayAfter.getDate() + 2);
          var dayAfterISO = fmtLocalDate(dayAfter);
          if (dateStr === todayISO) dayLabel = '今天';
          else if (dateStr === tomorrowISO) dayLabel = '明天';
          else if (dateStr === dayAfterISO) dayLabel = '后天';
          else dayLabel = dateStr.slice(5);
        }
        var isFirst = (hi === 0);
        hourlyHtml += '<div class="xw-h-item' + (isFirst ? ' xw-h-day-start' : '') + '">'
          + (isFirst ? '<div class="xw-h-day-badge">' + dayLabel + '</div>' : '')
          + '<div class="xw-h-time">' + rawHour + '</div>'
          + '<div class="xw-h-icon">' + hIcon + '</div>'
          + '<div class="xw-h-temp">' + hTemp + '°</div>'
          + (hRain > 15 ? '<div class="xw-h-rain">💧' + hRain + '%</div>' : '')
          + '</div>';
      }
    }

    /* ===== 灾害预警 ===== */
    var alertHtml = '';
    if (alerts.length > 0) {
      alertHtml = '<div class="xw-section">⚠️ 风险提示</div><div class="xw-alert">'
        + alerts.map(function (a) {
          return '<div class="xw-alert-item xw-alert-' + a.l + '"><span class="xw-alert-type">' + a.t + '</span><span class="xw-alert-msg">' + a.m + '</span></div>';
        }).join('') + '</div>';
    }

    /* ===== 田间作业指导 ===== */
    var gt = '';
    if (month >= 5 && month <= 6) {
      if (daily.precipitation_sum[0] > 5) gt = { d:'🌾【小麦收割】今日有雨，不宜收割！提前检查收割机，利用停雨间隙抢收，及时烘干防霉变。', c:'🌾【小麦收割】今日有雨，不宜收割！提前检查收割机，利用停雨间隙抢收，及时烘干防霉变。' };
      else if (daily.precipitation_sum[0] === 0 && hum < 70) gt = { d:'🌾【小麦收割】今日适宜收割！建议上午10点后开始，露水干透再下地，割茬15-20cm，及时晾晒。', c:'🌾【小麦收割】今日适宜收割！建议上午10点后开始，露水干透再下地，割茬15-20cm，及时晾晒。' };
      else gt = { d:'🌾【小麦收割期】关注天气，抢收抢晒。小麦蜡熟末期为最佳收获期，籽粒含水量≤20%即可机械收割。', c:'🌾【小麦收割期】关注天气，抢收抢晒。小麦蜡熟末期为最佳收获期，籽粒含水量≤20%即可机械收割。' };
    } else if (month >= 3 && month <= 4) {
      if (t >= 12 && daily.precipitation_sum[0] > 0) gt = { d:'🌱【水稻育秧】温湿度适宜，抓紧播种！注意秧田水深，晴天勤通风炼苗，防止秧苗徒长。', c:'🌱【水稻育秧】温湿度适宜，抓紧播种！注意秧田水深，晴天勤通风炼苗，防止秧苗徒长。' };
      else gt = { d:'🌱【春播期】日均气温稳定通过12℃即可播种水稻。提前整地施肥，做好种子催芽，关注倒春寒。', c:'🌱【春播期】日均气温稳定通过12℃即可播种水稻。提前整地施肥，做好种子催芽，关注倒春寒。' };
    } else if (month >= 7 && month <= 8) {
      if (t >= 35) gt = { d:'🌾【高温热害】气温' + t + '°C！日灌夜排降低田间温度，增施叶面肥（磷酸二氢钾），防止高温逼熟。', c:'🌾【高温热害】气温' + t + '°C！日灌夜排降低田间温度，增施叶面肥（磷酸二氢钾），防止高温逼熟。' };
      else gt = { d:'🌾【水稻管理】加强田间肥水管理，烤田控蘖，防治稻瘟病、纹枯病。注意高温时段避免下田。', c:'🌾【水稻管理】加强田间肥水管理，烤田控蘖，防治稻瘟病、纹枯病。注意高温时段避免下田。' };
    } else if (month >= 9 && month <= 10) {
      gt = { d:'🚜【秋收秋播】密切关注天气预报，确保水稻、玉米及时收获。收获后趁墒播种小麦，争取一播全苗。', c:'🚜【秋收秋播】密切关注天气预报，确保水稻、玉米及时收获。收获后趁墒播种小麦，争取一播全苗。' };
    } else if (month >= 11 || month <= 2) {
      if (todayMin < 0) gt = { d:'❄️【越冬管理】小麦镇压弥缝保墒，大蒜田覆盖稻草或薄膜防冻，检查果树绑扎防寒，及时清雪排水。', c:'❄️【越冬管理】小麦镇压弥缝保墒，大蒜田覆盖稻草或薄膜防冻，检查果树绑扎防寒，及时清雪排水。' };
      else gt = { d:'❄️【越冬期】做好清沟理墒，趁晴天追施腊肥，提高作物抗寒能力。检查农机具，备足来年春耕物资。', c:'❄️【越冬期】做好清沟理墒，趁晴天追施腊肥，提高作物抗寒能力。检查农机具，备足来年春耕物资。' };
    } else {
      gt = { d:'🌿【日常管理】加强田间巡查，关注墒情变化，合理追肥打药，晴天及时防治病虫害。', c:'🌿【日常管理】加强田间巡查，关注墒情变化，合理追肥打药，晴天及时防治病虫害。' };
    }

    /* ===== 农事日历 ===== */
    var seasonName = '', seasonItems = [];
    if (month >= 3 && month <= 4) { seasonName = '🌱 春播期'; seasonItems = [{ i:'🌱', l:'水稻育秧', d:'日均温≥12℃播种' }, { i:'🚜', l:'整地施肥', d:'提前翻耕施底肥' }, { i:'❄️', l:'防倒春寒', d:'关注低温预警' }]; }
    else if (month >= 5 && month <= 6) { seasonName = '🌾 夏收夏种期'; seasonItems = [{ i:'🌾', l:'小麦收割', d:'蜡熟末期抢收' }, { i:'🌱', l:'水稻插秧', d:'收麦后及时移栽' }, { i:'🌧️', l:'防汛排涝', d:'梅雨季清沟理墒' }]; }
    else if (month >= 7 && month <= 8) { seasonName = '☀️ 夏管期'; seasonItems = [{ i:'🌾', l:'水稻管理', d:'烤田控蘖防病害' }, { i:'🌡️', l:'防高温', d:'日灌夜排降温' }, { i:'🐛', l:'病虫害', d:'防治稻瘟/纹枯病' }]; }
    else if (month >= 9 && month <= 10) { seasonName = '🚜 秋收秋播期'; seasonItems = [{ i:'🚜', l:'水稻收获', d:'适时收割晾晒' }, { i:'🌱', l:'小麦播种', d:'趁墒抢播' }, { i:'🌧️', l:'防秋雨', d:'关注连阴雨' }]; }
    else { seasonName = '❄️ 越冬期'; seasonItems = [{ i:'❄️', l:'防寒保温', d:'覆盖/镇压保墒' }, { i:'🌿', l:'追施腊肥', d:'趁晴天施用' }, { i:'🚜', l:'农机检修', d:'备春耕物资' }]; }
    var calHtml = '<div class="xw-section">📅 当前农事季节：' + seasonName + '</div><div class="xw-calendar"><div class="xw-cal-card">';
    for (var si = 0; si < seasonItems.length; si++) {
      var s = seasonItems[si];
      calHtml += '<div class="xw-cal-row"><span class="xw-cal-icon">' + s.i + '</span><span class="xw-cal-label">' + s.l + '</span><span>' + s.d + '</span></div>';
    }
    calHtml += '</div></div>';

    /* ===== 组装 ===== */
    var html = curHtml
      + '<div class="xw-section">🕐 逐3小时预报（未来24h · 共8个时段）</div>'
      + '<div class="xw-hourly">' + hourlyHtml + '</div>'
      + '<div class="xw-section">📅 3日天气预报</div>'
      + '<div class="xw-forecast">' + fcHtml + '</div>'
      + alertHtml
      + '<div class="xw-section">🚜 今日田间作业指导</div>'
      + '<div class="xw-guide"><div class="xw-guide-card">'
      + '<div class="xw-guide-title">📋 农事建议（点击复制可转发）</div>'
      + '<div class="xw-guide-text" id="xwGuideText">' + gt.d + '</div>'
      + '<button class="xw-copy-btn" data-act="xwCopy">📋 一键复制</button>'
      + '<textarea id="xwCopySrc" style="display:none">' + gt.c + '</textarea>'
      + '</div></div>'
      + calHtml;

    var loadingEl = document.getElementById('xwLoading');
    if (loadingEl) loadingEl.style.display = 'none';
    var contentEl = document.getElementById('xwContent');
    if (contentEl) { contentEl.style.display = 'block'; contentEl.innerHTML = html; }
    return true;
  }

  /* ---------- 主逻辑 ---------- */
  var cached = loadCache();
  if (cached && (Date.now() - cached.ts) < CACHE_TTL) {
    render(cached.data, '【本地缓存 · ' + cacheAgeText(cached.ts) + '，正在后台刷新】');
  }

  fetchWeather()
    .then(function (om) {
      saveCache(om);
      render(om, '');
    })
    .catch(function () {
      var loadingEl = document.getElementById('xwLoading');
      if (cached) {
        // 有缓存：保留缓存数据并提示过期，绝不空白
        render(cached.data, '【实时获取失败，显示本地缓存 · ' + cacheAgeText(cached.ts) + '，可能过期】');
      } else if (loadingEl) {
        loadingEl.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px">天气数据加载失败，请稍后刷新重试</div>';
      }
    });
})();
