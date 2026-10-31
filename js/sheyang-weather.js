/* 射阳天气 —— 运行时数据获取 + 渲染
 * 设计：stale-while-revalidate
 *   - 页面打开先渲染本地缓存（localStorage）里上一次成功的数据，绝不空白；
 *   - 后台再向 Open-Meteo 拉最新；成功则更新缓存并刷新；
 *   - 拉取失败（国内网络偶尔连不上境外 API）则保留缓存数据，并提示「数据可能过期」。
 *   - fetch 带 8 秒超时，避免一直转圈。
 */
(function () {
  var LAT = 33.77, LON = 120.26;
  var CACHE_KEY = 'sy_weather_cache_v1';
  var CACHE_TTL = 30 * 60 * 1000; // 30 分钟
  var FETCH_TIMEOUT = 8000; // 8 秒

  var WMO = {
    0: "晴", 1: "晴", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
    95: "雷暴", 96: "雷暴+冰雹", 99: "雷暴+大冰雹"
  };

  var WIND = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"];

  function weatherDesc(code) { return WMO[code] || "未知"; }
  function windDir(deg) { return WIND[Math.round(deg / 45) % 8]; }

  function dressAdvice(temp, hum, code) {
    var tips = [];
    if (temp >= 35) tips.push("高温酷热，减少外出，注意防暑");
    else if (temp >= 30) tips.push("炎热，室外注意防晒补水");
    else if (temp >= 25) tips.push("较热，适合短袖");
    else if (temp >= 18) tips.push("舒适，适宜户外活动");
    else if (temp >= 10) tips.push("微凉，建议加件外套");
    else if (temp >= 0) tips.push("较冷，注意保暖");
    else tips.push("严寒，尽量减少外出");

    if (hum >= 90) tips.push("湿度极高，体感闷热，注意防潮");
    else if (hum >= 75) tips.push("湿度偏高，略闷");
    else if (hum <= 30) tips.push("空气干燥，注意保湿");

    if ([61, 63, 65, 80, 81, 82, 95, 96, 99].indexOf(code) !== -1) tips.push("有雨/雷暴，外出带伞");
    if ([71, 73, 75, 85, 86].indexOf(code) !== -1) tips.push("有雪，注意路滑");

    return tips.join("；");
  }

  function getWeekDay(dateStr) {
    var days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
    return days[new Date(dateStr).getDay()];
  }

  var tileColors = ["tile-green", "tile-orange", "tile-purple", "tile-cyan", "tile-pink", "tile-yellow"];
  var colorIndex = 0;
  function nextColor() { return tileColors[colorIndex++ % tileColors.length]; }

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
  function saveCache(data) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: data })); } catch (e) {}
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
      + '&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m'
      + '&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum'
      + '&timezone=Asia/Shanghai&forecast_days=4';
    var ctrl = new AbortController();
    var to = setTimeout(function () { ctrl.abort(); }, FETCH_TIMEOUT);
    return fetch(url, { signal: ctrl.signal })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .finally(function () { clearTimeout(to); });
  }

  /* ---------- 渲染 ---------- */
  function render(data, noteHtml) {
    var c = data.current;
    var temp = c.temperature_2m;
    var hum = c.relative_humidity_2m;
    var code = c.weather_code;
    var ws = c.wind_speed_10m;
    var wd = windDir(c.wind_direction_10m);
    var desc = weatherDesc(code);
    var advice = dressAdvice(temp, hum, code);

    var now = new Date();
    var ts = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0') + ' '
           + String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');

    var noteStr = noteHtml ? '<div style="font-size:12px;opacity:.7;margin-top:6px;">' + noteHtml + '</div>' : '';

    var html = '<div class="tile tile-large tile-blue weather-main">'
      + '<div class="temp">' + temp + '°</div>'
      + '<div class="desc">' + desc + '</div>'
      + '<div class="details">'
      + '<span>💧 湿度 ' + hum + '%</span>'
      + '<span>🌬️ ' + wd + ' ' + ws.toFixed(1) + ' km/h</span>'
      + '</div>'
      + '<div class="update-time">最后更新：' + ts + '</div>'
      + noteStr
      + '</div>';

    if (data.daily) {
      for (var i = 1; i < Math.min(4, data.daily.time.length); i++) {
        var dayName = getWeekDay(data.daily.time[i]);
        var hi = data.daily.temperature_2m_max[i];
        var lo = data.daily.temperature_2m_min[i];
        var wd2 = weatherDesc(data.daily.weather_code[i]);
        var rain = data.daily.precipitation_sum[i];
        var rainStr = rain > 0 ? '降水 ' + rain + 'mm' : '';
        html += '<div class="tile tile-small ' + nextColor() + ' forecast-tile">'
          + '<div class="day">' + dayName + '</div>'
          + '<div class="forecast-desc">' + wd2 + '</div>'
          + '<div class="forecast-temp">' + lo + '~' + hi + '°</div>'
          + '<div class="forecast-rain">' + rainStr + '</div>'
          + '</div>';
      }
    }

    html += '<div class="tile tile-dark advice-tile">'
      + '<h3>👔 出行建议</h3>'
      + '<p>' + advice + '</p>'
      + '</div>'
      + '<div class="tile tile-dark tip-tile">'
      + '<strong>💡 说明</strong>'
      + '<p>天气数据来自 Open-Meteo 开放气象 API，每次打开页面自动获取最新数据，每10分钟自动刷新。</p>'
      + '</div>';

    document.getElementById('tile-grid').innerHTML = html;
  }

  /* ---------- 主逻辑 ---------- */
  var cached = loadCache();
  if (cached && (Date.now() - cached.ts) < CACHE_TTL) {
    render(cached.data, '本地缓存 · ' + cacheAgeText(cached.ts) + '，正在后台刷新');
  }

  function refresh() {
    fetchWeather()
      .then(function (data) {
        saveCache(data);
        render(data, '');
      })
      .catch(function (err) {
        if (cached) {
          render(cached.data, '实时获取失败，显示本地缓存 · ' + cacheAgeText(cached.ts));
        } else {
          document.getElementById('tile-grid').innerHTML = '<div class="error-tile">⚠️ 天气数据获取失败，请稍后刷新</div>';
        }
        console.error('Weather load error:', err);
      });
  }

  refresh();
  setInterval(refresh, 10 * 60 * 1000);
})();
