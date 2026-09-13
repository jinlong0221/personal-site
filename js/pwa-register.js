/* 龙兄知识库 PWA 注册器 — 离线阅读
 * 同源外部脚本（/sw.js），受 meta CSP 的 script-src 'self' 允许。
 * 在页面 load 后注册 Service Worker；失败仅告警，不影响站点正常功能。
 */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function (err) {
      console.warn("[PWA] Service Worker 注册失败：", err);
    });
  });
}
