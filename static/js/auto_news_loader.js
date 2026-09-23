/**
 * 自动新闻加载器
 * 根据当前页面自动加载对应的 *-news.json 文件并显示
 * 
 * 使用方式：
 *   1. 在页面中添加一个容器：<div id="autoNewsBody"></div>
 */

(function () {
  // 全局 API：折叠/展开 .home-collapsible 卡片
  // 委托入口在 app.js：点击 [data-act="toggleHomeSection"] 触发本函数
  // 复用 CSS 已就绪的 .open class 控制展开（grid-template-rows: 1fr），
  // 箭头由 CSS .home-collapsible.open .hc-arrow { transform: rotate(180deg) } 自动翻转
  window.toggleHomeSection = function (el) {
    var wrap = el && el.closest ? el.closest('.home-collapsible') : null;
    if (!wrap) return;
    wrap.classList.toggle('open');
  };

  // 页面 → JSON 文件映射
  const PAGE_MAP = {
    'bracelet':  'bracelet-news.json',
    'zisha':     'zisha-news.json',
    'console':   'console-news.json',
    'chinajoy':  'chinajoy-news.json',
    'tesla':     'tesla-news.json',
    'fsd':       'fsd-news.json',
    'health-tea': 'health-tea-news.json',
    'sheyang':   'sheyang-news.json',
    'marvel':   'marvel-news.json',
    'apple':    'apple-news.json',
  };

  // 获取当前页面对应的 JSON 文件
  function getJsonFile() {
    const path = window.location.pathname;
    const page = path.split('/').pop().replace('.html', '');
    return PAGE_MAP[page] || null;
  }

  // 安全转义：防止仓库/自动化被篡改时的存储型 XSS
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  // 行内 Markdown：先转义再替换，不引入 XSS 面（与 changelog.js 的 md() 同一套约定）。
  // 自动化写稿惯用 **加粗** 标关键词，旧版只转义不解析 → 页面上原样显示成刺眼的星号
  // （2026-09-22 修：全站 11 个 news JSON 共 900+ 处）。
  function md(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  }
  // 仅允许 http/https/mailto，阻断 javascript:/data: 等危险协议
  function safeUrl(u) {
    if (typeof u !== 'string') return '';
    return /^(https?:|mailto:)/i.test(u.trim()) ? u.trim() : '';
  }

  // 渲染新闻列表
  function renderNews(container, news) {
    let html = '';
    news.forEach(function (item) {
      let tagHtml = '';
      (item.tags || []).forEach(function (t) {
        tagHtml += '<span class="news-tag ' + esc(t.class || 'default') + '">' + esc(t.text) + '</span>';
      });
      let link = safeUrl(item.url)
        ? '<a href="' + esc(item.url) + '" target="_blank" rel="noopener" style="font-size:0.78rem;margin-left:6px;">🔗原文</a>'
        : '';
      html += '<div class="news-item">' +
                '<div class="news-date">' + esc(item.date) + '</div>' +
                '<div class="news-content">' + tagHtml +
                  '<p>' + md(item.content) + link + '</p>' +
                '</div>' +
              '</div>';
    });
    container.innerHTML = html;
  }

  // 「2026-09-23」→「今天 / 昨天 / 3 天前」。
  // 数据只有日期精度，相对天数就是它能给的唯一诚实表达；精确日期放 title 不丢信息。
  // 好处是跨天会自己变，用户开着页面过夜再切回来也是对的。
  function relDay(v) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v == null ? '' : v));
    if (!m) return String(v == null ? '' : v);
    var t = new Date(+m[1], +m[2] - 1, +m[3]);
    if (isNaN(t.getTime())) return String(v);
    var n = new Date();
    var days = Math.round((new Date(n.getFullYear(), n.getMonth(), n.getDate()) - t) / 86400000);
    if (days <= 0) return '今天';
    if (days === 1) return '昨天';
    if (days < 30) return days + ' 天前';
    return m[2] + '-' + m[3];   // 太久远就退回日期，不硬凑「N 个月前」
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
        // 同步"最后更新时间"为新闻实际更新日期，避免与「实时」徽标矛盾。
        // 显示成相对天数（今天/昨天/N 天前）而不是死日期——死日期看着像静态快照，
        // 相对天数会自己跨天变化，且精确日期仍挂在 title 上。
        var updEl = document.getElementById('lastNewsUpdate');
        if (updEl && data.updated) {
          var paintUpd = function () {
            updEl.textContent = relDay(data.updated);
            updEl.title = '板块资讯更新日：' + data.updated;
          };
          paintUpd();
          // 页面开着过夜再切回来时要重算，否则会一直停在「今天」
          document.addEventListener('visibilitychange', function () {
            if (!document.hidden) paintUpd();
          });
        }
        if (!data.news || data.news.length === 0) return;
        if (countEl) countEl.textContent = data.news.length + '条';
        renderNews(container, data.news);
        // 显示整个折叠区域（保留 grid 折叠动画：display:grid + 添加 open 类）
        var wrapper = document.getElementById('hc-auto-news');
        if (wrapper) {
          wrapper.style.display = 'grid';
          wrapper.classList.add('open');
        }
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
