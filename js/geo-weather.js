/**
 * geo-weather.js — 顶部天气胶囊「定位到用户所在城市」+ 天气页本地天气横幅
 *
 * 行为：
 *   1) 全站胶囊升级：若 localStorage 里存有新鲜的「用户本地天气」，优先把
 *      #navWeather 显示成「城市 温度°」，而不是默认的射阳天气。
 *   2) 天气页（weather.html）顶部横幅：进入页面即尝试浏览器定位，定位成功后
 *      反查城市名（BigDataCloud，免 Key）+ 拉取实时天气（Open-Meteo，免 Key），
 *      渲染「您当前位置 · 城市 · 天气 · 温度」。拒绝授权时给出「授权并查看」按钮。
 *
 * 纯原生，无依赖；被 weather.html 引入。
 */
(function () {
  'use strict';

  var LS_KEY = 'lx_local_wx';
  var TTL_MS = 30 * 60 * 1000; // 30 分钟，天气会变，过期回退默认

  // WMO 天气代码 → 中文简述
  function wxText(c) {
    c = +c;
    if (c === 0) return '晴';
    if (c === 1) return '晴间多云';
    if (c === 2) return '多云';
    if (c === 3) return '阴';
    if (c === 45 || c === 48) return '雾';
    if (c >= 51 && c <= 57) return '毛毛雨';
    if (c >= 61 && c <= 67) return '小雨';
    if (c >= 71 && c <= 77) return '雪';
    if (c >= 80 && c <= 82) return '阵雨';
    if (c >= 85 && c <= 86) return '阵雪';
    if (c >= 95) return '雷阵雨';
    return '未知';
  }

  // WMO → 图标（与 app.js 一致）
  var ICONS = {
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5v2.5M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8l1.8-1.8M18 6l1.8-1.8"/>',
    'cloud-sun': '<circle cx="8.5" cy="8.5" r="3"/><path d="M8.5 2.5v2M3.3 8.5h2M4.6 4.6l1.4 1.4"/><path d="M11 18a3.2 3.2 0 010-6.4 4.2 4.2 0 018.1-1.2A3.2 3.2 0 0118.5 18H11z"/>',
    cloud: '<path d="M7 18a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 18H7z"/>',
    fog: '<path d="M7 17a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 17H7z"/><path d="M7 20h11M8.5 22.5h8"/>',
    rain: '<path d="M7 16a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 16H7z"/><path d="M8 19l-1 3M12 19l-1 3M16 19l-1 3"/>',
    snow: '<path d="M7 16a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 16H7z"/><path d="M8 19.5v3M12 19.5v3M16 19.5v3"/>',
    thunder: '<path d="M7 16a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 16H7z"/><path d="M11 18l-2.5 4h3l-2.5 4"/>'
  };
  function iconSvg(key) {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[key] || ICONS.cloud) + '</svg>';
  }
  function iconKey(c) {
    c = +c;
    if (c === 0) return 'sun';
    if (c === 1 || c === 2) return 'cloud-sun';
    if (c === 3) return 'cloud';
    if (c === 45 || c === 48) return 'fog';
    if (c >= 51 && c <= 67) return 'rain';
    if (c >= 71 && c <= 77) return 'snow';
    if (c >= 80 && c <= 86) return 'rain';
    if (c >= 95) return 'thunder';
    return 'cloud';
  }

  function readLS() {
    try {
      var raw = localStorage.getItem(LS_KEY);
      if (!raw) return null;
      var o = JSON.parse(raw);
      if (!o || typeof o.temp !== 'number' || !o.name) return null;
      if (Date.now() - (o.ts || 0) > TTL_MS) return null;
      return o;
    } catch (e) { return null; }
  }
  function writeLS(o) {
    try { o.ts = Date.now(); localStorage.setItem(LS_KEY, JSON.stringify(o)); } catch (e) {}
  }

  // 把反查结果拼成友好地名（用 city / 省级，避开接口返回的繁体 locality）
  function placeName(g) {
    if (!g) return '';
    if (g.city) return g.city;
    if (g.principalSubdivision) return g.principalSubdivision;
    if (g.countryName) return g.countryName;
    return '您的位置';
  }

  // 升级全站胶囊：本地天气新鲜则优先显示用户所在城市
  function upgradeCapsule() {
    var el = document.getElementById('navWeather');
    if (!el) return;
    var o = readLS();
    if (!o) return;
    el.innerHTML = iconSvg(iconKey(o.code)) + '<span style="margin-left:3px">' + o.name + ' ' + Math.round(o.temp) + '°</span>';
    el.setAttribute('title', o.name + '实时天气，点击查看天气页');
    el.setAttribute('aria-label', o.name + '实时天气');
  }

  // 天气页本地天气横幅
  function renderLocalWeather() {
    var box = document.getElementById('localWeather');
    if (!box) return;

    function showLoading() {
      box.innerHTML = '<div class="lw-card lw-loading"><span class="lw-spin"></span><span>正在获取您的位置与实时天气…</span></div>';
    }
    function showDenied() {
      box.innerHTML =
        '<div class="lw-card lw-denied">' +
        '<div class="lw-title">📍 显示您所在城市的天气</div>' +
        '<p class="lw-sub">授权浏览器定位后，这里会显示您当前位置的实时天气（仅本地使用，不上传任何数据）。</p>' +
        '<button type="button" class="lw-btn" id="lwAuthBtn">授权并查看我的天气</button>' +
        '</div>';
      var b = document.getElementById('lwAuthBtn');
      if (b) b.addEventListener('click', function () { attempt(true); });
    }
    function showError(msg) {
      box.innerHTML =
        '<div class="lw-card lw-denied"><div class="lw-title">⚠️ 暂时无法获取天气</div>' +
        '<p class="lw-sub">' + (msg || '网络异常，请稍后重试。') + '</p>' +
        '<button type="button" class="lw-btn" id="lwAuthBtn">重试</button></div>';
      var b = document.getElementById('lwAuthBtn');
      if (b) b.addEventListener('click', function () { attempt(true); });
    }
    function render(name, temp, code) {
      var t = Math.round(temp);
      box.innerHTML =
        '<div class="lw-card">' +
        '<div class="lw-badge">您当前位置</div>' +
        '<div class="lw-main">' + iconSvg(iconKey(code)) +
        '<div class="lw-now"><span class="lw-temp">' + t + '°</span>' +
        '<span class="lw-desc">' + wxText(code) + '</span></div></div>' +
        '<div class="lw-place">' + name + '</div>' +
        '<div class="lw-foot">数据来自 Open-Meteo · 实时更新</div>' +
        '</div>';
    }

    function fetchWeather(lat, lon, name) {
      var u = 'https://api.open-meteo.com/v1/forecast?latitude=' + lat + '&longitude=' + lon +
        '&current=temperature_2m,weather_code&timezone=auto';
      fetch(u).then(function (r) { return r.json(); }).then(function (d) {
        if (d && d.current) {
          var o = { name: name, temp: d.current.temperature_2m, code: d.current.weather_code };
          writeLS(o);
          render(o.name, o.temp, o.code);
          upgradeCapsule(); // 当前页胶囊也同步成用户城市
        } else {
          showError('天气数据解析失败。');
        }
      }).catch(function () { showError('天气接口请求失败。'); });
    }

    function reverse(lat, lon, cb) {
      var u = 'https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=' + lat +
        '&longitude=' + lon + '&localityLanguage=zh';
      fetch(u).then(function (r) { return r.json(); }).then(function (g) {
        cb(placeName(g) || '您的位置');
      }).catch(function () { cb('您的位置'); });
    }

    function attempt(fromButton) {
      if (!window.navigator || !navigator.geolocation) {
        showDenied();
        return;
      }
      showLoading();
      navigator.geolocation.getCurrentPosition(function (pos) {
        var lat = pos.coords.latitude, lon = pos.coords.longitude;
        reverse(lat, lon, function (name) {
          fetchWeather(lat, lon, name);
        });
      }, function () {
        // 用户拒绝或获取失败 → 给出授权按钮
        showDenied();
      }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
    }

    // 已有新鲜本地天气则直接渲染，避免重复弹权限
    var cached = readLS();
    if (cached) {
      render(cached.name, cached.temp, cached.code);
    } else {
      attempt(false);
    }
  }

  function init() {
    upgradeCapsule();
    var p = window.location.pathname || '';
    if (p.indexOf('weather.html') !== -1) {
      renderLocalWeather();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
