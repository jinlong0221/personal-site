// =====================================================================
// Gitalk 评论组件初始化（纯前端，评论存储于 GitHub Issues，无自有后端）
// ---------------------------------------------------------------------
// 配置（GitHub OAuth App 凭据）已填入下方。
//   - App 名称: longxiong
//   - 在 GitHub → Settings → Developer settings → OAuth Apps 创建
//   - Authorization callback URL 必须设为: https://longxiong.vip/oauth-callback.html
//     （不要填站点根;Gitalk 内部会用 location.href 作为 redirect_uri,
//      GitHub OAuth 要求精确匹配,所以走中转页把 redirect_uri 锁到固定路径）
//   - 说明：Gitalk 是纯前端组件，必须拿 clientSecret 到浏览器里换临时令牌，
//     所以这把 secret 会随网页源码对全网公开（这是 Gitalk 的设计，不是疏漏）。
//     风险面有限：他人最多用它往你 personal-site 仓库的 Issues 发评论。
//   - owner / repo / admin 已按本站默认填写；若想用独立评论仓库，改 repo 与 admin 即可。
//   - 首次需你本人以 GitHub 登录后在该页面发一条评论，Gitalk 才会创建对应 Issue，
//     之后访客登录 GitHub 即可在该 Issue 下评论。
//
// 必要的两个外部依赖：
//   1. oauth-callback.html 中转页（同目录 static/oauth-callback.html）— 已部署。
//   2. 自建 CORS proxy（Cloudflare Worker）— 用于把 GitHub access_token
//      POST 跨域转回同源。Gitalk 默认的 cors-anywhere.azm.workers.dev 已下线。
//      部署见 infra/gitalk-proxy/。proxy URL 填到下方 GITALK_CONFIG.proxy。
// =====================================================================

// (1) 启动时:如果从 oauth-callback.html 跳回,带 code 在 sessionStorage,
//             把它还原到 URL search,Gitalk 渲染时就能消费。
(function restoreOAuthCode () {
  var code = sessionStorage.getItem('gitalk_code');
  if (!code) return;
  sessionStorage.removeItem('gitalk_code');
  try {
    var url = new URL(location.href);
    url.searchParams.set('code', code);
    history.replaceState(null, '', url.toString());
  } catch (e) { /* 静默失败:让 Gitalk 自己报错 */ }
})();

window.GITALK_CONFIG = {
  clientID: '0v231iqSjAYPsiAMbxx6',          // GitHub OAuth App Client ID (longxiong)
  clientSecret: '21134a9c91ffebb742a80aec644959ca65b27380', // GitHub OAuth App Client Secret (longxiong)
  owner: 'jinlong0221',                     // 仓库所有者（GitHub 用户名）
  repo: 'personal-site',                    // 存放评论 Issue 的仓库
  admin: ['jinlong0221'],                   // 有写权限的管理员（用于初始化 Issue）
  // CORS proxy: 替换为部署好的 Cloudflare Worker URL,见 infra/gitalk-proxy/
  // 必须 https,允许 POST 跨域返回 application/json。
  // 部署后把 worker URL 填这里,并把 OAuth App 的 callback URL 同步设为:
  //   https://longxiong.vip/oauth-callback.html
  proxy: 'https://gitalk-proxy.longxiong-vip.workers.dev',
  distractionFreeMode: false
};

(function () {
  var GITALK_CSS = 'https://cdn.jsdelivr.net/npm/gitalk/dist/gitalk.css';
  var GITALK_JS = 'https://cdn.jsdelivr.net/npm/gitalk/dist/gitalk.min.js';

  function loadCSS () {
    if (document.querySelector('link[href*="gitalk.css"]')) return;
    var l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = GITALK_CSS;
    document.head.appendChild(l);
  }

  // Gitalk 的 id 需唯一且 ≤50 字符:用路径做稳定短哈希
  function shortId () {
    var s = location.pathname || '/';
    var h = 0;
    for (var i = 0; i < s.length; i++) { h = (h << 5) - h + s.charCodeAt(i); h |= 0; }
    return 'lx' + (h >>> 0).toString(36);
  }

  // 重写 Gitalk 的 loginLink getter:
  //   - redirect_uri 锁定到固定中转页 https://longxiong.vip/oauth-callback.html
  //   - 带上 return=<原页 path+query+hash>,中转页读完 code 后跳回原页
  // 这样 OAuth App 的 callback URL 只需设一个固定值,所有文章页都能用。
  var OAUTH_CALLBACK = 'https://longxiong.vip/oauth-callback.html';
  function patchedLoginLink (clientID) {
    var ret = location.pathname + location.search + location.hash;
    var q = {
      client_id: clientID,
      redirect_uri: OAUTH_CALLBACK + '?return=' + encodeURIComponent(ret),
      scope: 'public_repo'
    };
    return 'https://github.com/login/oauth/authorize?' + Object.keys(q).map(function (k) {
      return k + '=' + encodeURIComponent(q[k]);
    }).join('&');
  }

  function init () {
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

    // monkey-patch 实例的 loginLink getter(Gitalk 1.7.2 在原型上用 `get loginLink() {}` 定义,
    // 实例层 defineProperty 会覆盖之;handleLogin 内部用 this.loginLink 读取,所以会走到这里)。
    try {
      Object.defineProperty(g, 'loginLink', {
        configurable: true,
        get: function () { return patchedLoginLink(cfg.clientID); }
      });
    } catch (e) { /* 老浏览器降级:Gitalk 会跳原始 URL,失败也在评论容器显示 */ }

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
