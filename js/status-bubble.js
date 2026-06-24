/**
 * status-bubble.js - 龙兄状态气泡 + 近期动态新鲜度标签
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

  // 加载龙兄状态和更新日志
  function loadStatusAndUpdates() {
    var base = getBasePath();
    
    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/updates.json', true);
    xhr.responseType = 'json';
    
    xhr.onload = function () {
      if (xhr.status !== 200) return;
      var data = xhr.response;
      if (!data) return;
      
      // 显示龙兄状态气泡
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
        var statusInline = document.getElementById('todayStatusInline');
        if (statusInline) {
          statusInline.style.display = 'flex';
        }
        
        var statusText = document.getElementById('todayStatusText');
        var bubbleDate = document.getElementById('bubbleDate');
        var bubbleTime = document.getElementById('bubbleTime');
        
        if (statusText) {
          statusText.textContent = '最近在折腾「' + latestUpdate.name + '」板块 🛠️';
        }
        if (bubbleDate) {
          bubbleDate.textContent = latestUpdate.lastUpdate;
        }
        if (bubbleTime) {
          bubbleTime.textContent = getTimeAgo(latestUpdate.lastUpdate);
        }
      }
      
      // 显示近期动态列表
      var updateList = document.getElementById('updateLogList');
      if (!updateList) return;
      
      // 按日期排序（最新在前）
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
      updates.sort(function(a, b) {
        return new Date(b.lastUpdate) - new Date(a.lastUpdate);
      });
      
      // 只显示最新的6条
      updates = updates.slice(0, 6);
      
      var html = '';
      updates.forEach(function(item) {
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
