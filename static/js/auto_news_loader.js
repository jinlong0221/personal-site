/**
 * 自动新闻加载器
 * 根据当前页面自动加载对应的 *-news.json 文件并显示
 * 
 * 使用方式：
 *   1. 在页面中添加一个容器：<div id="autoNewsBody"></div>
 *   2. 引入本脚本：<script src="js/auto_news_loader.js"></script>
 */

(function () {
  // 页面 → JSON 文件映射
  const PAGE_MAP = {
    'herbs':     'herbs-news.json',
    'bracelet':  'bracelet-news.json',
    'zisha':     'zisha-news.json',
    'console':   'console-news.json',
    'marvel':    'marvel-news.json',
    'tesla':     'tesla-news.json',
    'health-tea': 'health-tea-news.json',
    'sheyang':   'sheyang-news.json',
  };

  // 获取当前页面对应的 JSON 文件
  function getJsonFile() {
    const path = window.location.pathname;
    const page = path.split('/').pop().replace('.html', '');
    return PAGE_MAP[page] || null;
  }

  // 渲染新闻列表
  function renderNews(container, news) {
    let html = '';
    news.forEach(function (item) {
      let tagHtml = '';
      (item.tags || []).forEach(function (t) {
        tagHtml += '<span class="news-tag ' + (t.class || 'default') + '">' + t.text + '</span>';
      });
      let link = item.url
        ? '<a href="' + item.url + '" target="_blank" rel="noopener" style="font-size:0.78rem;margin-left:6px;">🔗原文</a>'
        : '';
      html += '<div class="news-item">' +
                '<div class="news-date">' + item.date + '</div>' +
                '<div class="news-content">' + tagHtml +
                  '<p>' + item.content + link + '</p>' +
                '</div>' +
              '</div>';
    });
    container.innerHTML = html;
  }

  // 主函数
  function loadAutoNews() {
    const jsonFile = getJsonFile();
    if (!jsonFile) return;  // 当前页面不需要自动新闻

    const container = document.getElementById('autoNewsBody');
    const countEl   = document.getElementById('autoNewsCount');
    if (!container) return;  // 页面没有容器

    fetch(jsonFile + '?v=' + Date.now())
      .then(function (r) {
        if (!r.ok) throw new Error('Not found');
        return r.json();
      })
      .then(function (data) {
        if (!data.news || data.news.length === 0) return;
        if (countEl) countEl.textContent = data.news.length + '条';
        renderNews(container, data.news);
        // 显示整个折叠区域
        var wrapper = document.getElementById('hc-auto-news');
        if (wrapper) wrapper.style.display = 'block';
      })
      .catch(function (e) {
        console.log('[auto_news] 加载失败:', jsonFile, e);
      });
  }

  // DOM 就绪后执行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadAutoNews);
  } else {
    loadAutoNews();
  }
})();
