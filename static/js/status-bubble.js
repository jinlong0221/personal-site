/**
 * status-bubble.js - 龙兄状态气泡 + 近期动态新鲜度标签
 *
 * 逻辑：
 * 1. 优先读取 status.json → 显示今日状态（手动更新）
 * 2. 回退：status.json 无数据或过期 → 读 data/updates.json 最新板块
 * 3. 近期动态列表始终来自 data/updates.json
 */
(function () {
  // 计算时间差，返回友好的描述
  function getTimeAgo(dateStr) {
    if (!dateStr) return '';
    var now = new Date();
    var date = new Date(dateStr);
    var diff = now - date;
    var days = Math.floor(diff / (1000 * 60 * 60 * 24));
    var hours = Math.floor(diff / (1000 * 60 * 60));
    var minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 60) {
      return minutes <= 0 ? '刚刚' : minutes + '分钟前';
    } else if (hours < 24) {
      return hours + '小时前';
    } else if (days < 30) {
      return days + '天前';
    } else {
      return dateStr;
    }
  }

  // 计算新鲜度等级
  function getFreshnessLevel(dateStr) {
    if (!dateStr) return 'old';
    var now = new Date();
    var date = new Date(dateStr);
    var diff = now - date;
    var days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days <= 3) return 'fresh-3days';
    if (days <= 7) return 'fresh-week';
    return 'old';
  }

  // 获取基础路径
  function getBasePath() {
    var base = '';
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var m = scripts[i].src.match(/(.*\/)js\/.+/);
      if (m) { base = m[1]; break; }
    }
    return base;
  }

  // 显示状态气泡（来自 status.json）
  function showStatusBubble(data) {
    var statusInline = document.getElementById('todayStatusInline');
    if (statusInline) statusInline.style.display = 'flex';

    var statusText = document.getElementById('todayStatusText');
    var bubbleDate = document.getElementById('bubbleDate');
    var bubbleTime = document.getElementById('bubbleTime');

    if (statusText) statusText.textContent = data.status || '';
    if (bubbleDate) bubbleDate.textContent = data.date || '';
    if (bubbleTime) bubbleTime.textContent = getTimeAgo(data.updatedAt);

    // 同时更新杂志布局中的状态显示
    var magStatus = document.getElementById('magStatus');
    if (magStatus) magStatus.textContent = (data.status || '') + ' ' + (data.emoji || '');
  }

  // 回退：从 updates.json 找最新板块显示
  function fallbackToLatestUpdate(data) {
    var latestUpdate = null;
    var latestDate = null;

    for (var key in data) {
      if (data[key] && data[key].lastUpdate) {
        var updateDate = new Date(data[key].lastUpdate);
        if (!latestDate || updateDate > latestDate) {
          latestDate = updateDate;
          latestUpdate = data[key];
          latestUpdate.name = key;
        }
      }
    }

    if (latestUpdate) {
      showStatusBubble({
        status: '最近在折腾「' + latestUpdate.name + '」板块 🛠️',
        date: latestUpdate.lastUpdate,
        updatedAt: latestUpdate.lastUpdate
      });
    }
  }

  // 加载近期动态列表（来自 data/updates.json）
  function loadUpdatesList(data) {
    var updateList = document.getElementById('updateLogList');
    if (!updateList) return;

    var updates = [];
    for (var key in data) {
      if (data[key] && data[key].lastUpdate) {
        updates.push({
          name: key,
          url: data[key].url,
          lastUpdate: data[key].lastUpdate
        });
      }
    }
    updates.sort(function (a, b) {
      return new Date(b.lastUpdate) - new Date(a.lastUpdate);
    });
    updates = updates.slice(0, 6);

    var html = '';
    updates.forEach(function (item) {
      var freshness = getFreshnessLevel(item.lastUpdate);
      var timeAgo = getTimeAgo(item.lastUpdate);

      var badge = '';
      if (freshness === 'fresh-3days') {
        badge = '<span class="fresh-dot"></span>';
      } else if (freshness === 'fresh-week') {
        badge = '<span class="new-badge">新</span>';
      } else {
        badge = '<span style="width:8px;height:8px;flex-shrink:0;"></span>';
      }

      html += '<div class="update-item">' + badge +
        '<a href="' + item.url + '" class="update-text" style="text-decoration:none;color:inherit;">' + item.name + '</a>' +
        '<span class="update-time">' + timeAgo + '</span></div>';
    });

    updateList.innerHTML = html;
  }

  // 主入口：先读 status.json，失败再读 updates.json
  function loadStatusAndUpdates() {
    var base = getBasePath();

    // 1. 尝试读取 status.json（今日状态，优先；加时间戳破微信浏览器缓存）
    var statusXhr = new XMLHttpRequest();
    statusXhr.open('GET', base + 'status.json?t=' + Date.now(), true);
    statusXhr.responseType = 'json';
    statusXhr.setRequestHeader('Cache-Control', 'no-cache');

    statusXhr.onload = function () {
      if (statusXhr.status === 200 && statusXhr.response && statusXhr.response.status) {
        showStatusBubble(statusXhr.response);
      } else {
        // status.json 无数据，回退到 updates.json
        fallbackXhr(base);
      }
      // 无论 status.json 是否成功，都加载近期动态列表
      loadUpdatesListFromUrl(base);
    };

    statusXhr.onerror = function () {
      fallbackXhr(base);
      loadUpdatesListFromUrl(base);
    };

    statusXhr.send();
  }

  // 回退：读取 updates.json 找最新板块
  function fallbackXhr(base) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/updates.json', true);
    xhr.responseType = 'json';
    xhr.onload = function () {
      if (xhr.status === 200 && xhr.response) {
        fallbackToLatestUpdate(xhr.response);
      }
    };
    xhr.send();
  }

  // 加载近期动态列表
  function loadUpdatesListFromUrl(base) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/updates.json', true);
    xhr.responseType = 'json';
    xhr.onload = function () {
      if (xhr.status === 200 && xhr.response) {
        loadUpdatesList(xhr.response);
      }
    };
    xhr.send();
  }

  // 页面加载完成后执行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadStatusAndUpdates);
  } else {
    loadStatusAndUpdates();
  }
})();
