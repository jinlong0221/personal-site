// =====================================================================
// Gitalk 评论组件初始化（纯前端，评论存储于 GitHub Issues，无自有后端）
// ---------------------------------------------------------------------
// 配置（GitHub OAuth App 凭据）已填入下方。
//   - App 名称: longxiong
//   - 在 GitHub → Settings → Developer settings → OAuth Apps 创建
//   - Authorization callback URL: https://longxiong.vip/
//   - 说明：Gitalk 是纯前端组件，必须拿 clientSecret 到浏览器里换临时令牌，
//     所以这把 secret 会随网页源码对全网公开（这是 Gitalk 的设计，不是疏漏）。
//     风险面有限：他人最多用它往你 personal-site 仓库的 Issues 发评论。
//   - owner / repo / admin 已按本站默认填写；若想用独立评论仓库，改 repo 与 admin 即可。
//   - 首次需你本人以 GitHub 登录后在该页面发一条评论，Gitalk 才会创建对应 Issue，
//     之后访客登录 GitHub 即可在该 Issue 下评论。
// =====================================================================
window.GITALK_CONFIG = {
  clientID: '0v231iqSjAYPsiAMbxx6',          // GitHub OAuth App Client ID (longxiong)
  clientSecret: '21134a9c91ffebb742a80aec644959ca65b27380', // GitHub OAuth App Client Secret (longxiong)
  owner: 'jinlong0221',                     // 仓库所有者（GitHub 用户名）
  repo: 'personal-site',                    // 存放评论 Issue 的仓库
  admin: ['jinlong0221'],                   // 有写权限的管理员（用于初始化 Issue）
  distractionFreeMode: false
};

(function () {
  var GITALK_CSS = 'https://cdn.jsdelivr.net/npm/gitalk/dist/gitalk.css';
  var GITALK_JS = 'https://cdn.jsdelivr.net/npm/gitalk/dist/gitalk.min.js';

  function loadCSS() {
    if (document.querySelector('link[href*="gitalk.css"]')) return;
    var l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = GITALK_CSS;
    document.head.appendChild(l);
  }

  // Gitalk 的 id 需唯一且 ≤50 字符：用路径做稳定短哈希
  function shortId() {
    var s = location.pathname || '/';
    var h = 0;
    for (var i = 0; i < s.length; i++) { h = (h << 5) - h + s.charCodeAt(i); h |= 0; }
    return 'lx' + (h >>> 0).toString(36);
  }

  function init() {
    var box = document.querySelector('.gitalk-container');
    if (!box) return;
    var cfg = window.GITALK_CONFIG || {};
    if (!cfg.clientID || cfg.clientID === 'GITHUB_OAUTH_CLIENT_ID' ||
        !cfg.clientSecret || cfg.clientSecret === 'GITHUB_OAUTH_CLIENT_SECRET') {
      box.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;padding:8px 0">' +
        '评论功能待配置（请在 static/js/gitalk-init.js 填写 GitHub OAuth Client ID / Client Secret）。</p>';
      return;
    }
    var g = new Gitalk(Object.assign({}, cfg, { id: shortId() }));
    g.render(box);
  }

  loadCSS();
  if (window.Gitalk) { init(); return; }
  var sc = document.createElement('script');
  sc.src = GITALK_JS;
  sc.onload = init;
  sc.onerror = function () {
    var box = document.querySelector('.gitalk-container');
    if (box) box.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem">评论组件加载失败（CDN 被拦截或网络异常）。</p>';
  };
  document.head.appendChild(sc);
})();
