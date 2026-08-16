// =====================================================================
// 热门精选「访问量」预留位（Umami 统计接入点）
// ---------------------------------------------------------------------
// 当前只是【预留位置】：首页热门精选卡片尚无真实文章路径，
// 故每个卡片的 data-views-path 留空，默认不显示数字。
//
// 若要真正展示访问量，需 Umami 统计 API 的只读 token（属于服务端密钥，
// 切勿硬编码在前端暴露；建议自行搭一个只转发 GET 的极简代理，或 Umami
// 官方的“分享链接”只读面板）。配置方式：在任意页面（如首页模板）设置：
//
//   window.UMAMI_HOT = {
//     apiUrl: 'https://umami.your-domain.com',   // Umami 实例地址
//     websiteId: 'YOUR_WEBSITE_ID',               // 站点 ID
//     token: 'READONLY_API_TOKEN'                // 只读 token
//   };
//
// 本脚本会在 window.UMAMI_HOT 存在时，按每张卡片的 data-views-path
// 拉取该页访问量并填入 .hot-views。未配置则静默不显示（位置保留）。
// 注意：Umami 不同版本 metrics 端点字段可能不同，按需微调下方 URL。
// =====================================================================
(function () {
  var cfg = window.UMAMI_HOT;
  if (!cfg || !cfg.apiUrl || !cfg.websiteId) return;

  function fill() {
    var nodes = document.querySelectorAll('.hot-views');
    nodes.forEach(function (n) {
      var path = n.getAttribute('data-views-path');
      if (!path) return; // 预留位但暂无真实路径，跳过
      fetch(
        cfg.apiUrl + '/api/websites/' + encodeURIComponent(cfg.websiteId) +
        '/metrics?type=url&url=' + encodeURIComponent(path),
        { headers: { 'x-umami-api-key': cfg.token || '' } }
      )
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var v = d && d[0] && d[0].value;
          n.textContent = (v != null) ? '👁 ' + v : '';
        })
        .catch(function () { n.textContent = ''; });
    });
  }

  if (document.readyState !== 'loading') fill();
  else document.addEventListener('DOMContentLoaded', fill);
})();
