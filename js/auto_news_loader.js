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

  // 全局 API：新闻条目「展开详情 / 收起详情」
  // 委托入口同样在 app.js：点击 [data-act="toggleNewsDetail"] 触发本函数（收按钮元素本身）。
  //
  // 🔴 显隐走 [hidden] **属性**，不走 class —— [hidden] 是 HTML 原生语义，
  //    屏幕阅读器靠它判断内容在不在，`aria-expanded` 也跟它对齐。
  //    代价是：style.css 里**不能**给 .news-detail 写 display（写了就把 [hidden] 顶掉、
  //    详情永远展着），必须写成 .news-detail[hidden]{display:none}。改样式时别踩。
  window.toggleNewsDetail = function (el) {
    if (!el || !el.closest) return;
    var box = el.closest('.news-content');
    var det = box ? box.querySelector('.news-detail') : null;
    if (!det) return;
    var willOpen = det.hasAttribute('hidden');        // 当前收着的 → 这一下要展开
    if (willOpen) { det.removeAttribute('hidden'); } else { det.setAttribute('hidden', ''); }
    el.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    el.classList.toggle('is-open', willOpen);
    var txt = el.querySelector('.news-more-txt');
    if (txt) txt.textContent = willOpen ? '收起详情' : '展开详情';
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
  //
  // 2026-09-24 改版：条目从「一段长正文」变成「摘要常显 + 正文折叠」。
  //   起因：全站 11 个板块 88 条，正文平均 612 字、最长 2358 字，而自动化提示词
  //   要求的是「content(50-100字摘要)」，实测超了 6–23 倍 —— 读者点进板块页看到的是
  //   一篇篇改写过的新闻稿，而不是「今天发生了什么」。摘要 = 摆在明面的那段。
  //   兼容：老数据没有 summary 时整段 content 照旧当摘要显示、按钮不出现，
  //   所以存量新闻不用等全部补写完就能上线（补写见 scripts/guard_news_length.py）。
  function renderNews(container, news) {
    let html = '';
    news.forEach(function (item, idx) {
      let tagHtml = '';
      (item.tags || []).forEach(function (t) {
        tagHtml += '<span class="news-tag ' + esc(t.class || 'default') + '">' + esc(t.text) + '</span>';
      });
      let link = safeUrl(item.url)
        ? '<a href="' + esc(item.url) + '" target="_blank" rel="noopener" style="font-size:0.78rem;margin-left:6px;">🔗原文</a>'
        : '';

      // 摘要压成单行：摘要的定位是「一眼看完」，带换行会把它变成小正文
      var sum  = String(item.summary == null ? '' : item.summary).replace(/\s+/g, ' ').trim();
      var body = String(item.content == null ? '' : item.content).trim();
      // 正文比摘要长出 30 字以上才值得折 —— 不然点开只多一两行，白给一个按钮
      var hasDetail = !!(sum && body && body.length > sum.length + 30);
      var detailId = 'nd-' + idx;

      html += '<div class="news-item">' +
                '<div class="news-date">' + esc(item.date) + '</div>' +
                '<div class="news-content">' + tagHtml +
                  '<p class="news-sum">' + md(sum || body) + link + '</p>' +
                  (hasDetail
                    ? '<button class="news-more" type="button" aria-expanded="false" aria-controls="' + detailId +
                        '" data-act="toggleNewsDetail"><span class="news-more-txt">展开详情</span>' +
                        '<span class="news-more-arrow" aria-hidden="true"></span></button>' +
                      '<div class="news-detail" id="' + detailId + '" hidden>' + detailHtml(body) + '</div>'
                    : '') +
                '</div>' +
              '</div>';
    });
    container.innerHTML = html;
  }

  // 详情正文：按行拆段。自动化写稿里 6/88 条带换行（漫威那条是 `\n\n· **档期大盘**：…`
  // 的准列表写法），塞进单个 <p> 会被 HTML 折成一大坨 —— 折叠区本来就长，
  // 再不给分段等于把「点开看详情」做成「点开看墙」。单行的 82 条拆分后仍是一段，无变化。
  function detailHtml(s) {
    return String(s == null ? '' : s)
      .split(/\n+/)
      .map(function (line) { return line.trim(); })
      .filter(function (line) { return line; })
      .map(function (line) { return '<p>' + md(line) + '</p>'; })
      .join('');
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

    fetch(jsonFile + '?t=' + Math.floor(Date.now() / 600000)) // 10 分钟窗口戳：同窗口内浏览器/CDN 直接命中缓存，不再每次击穿
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
