/**
 * Cloudflare Worker — 为 longxiong.vip 补发 GitHub Pages 自定义域名无法下发的响应头
 *
 * 背景：GitHub Pages 自定义域名只能在 HTML 里用 <meta> 设 CSP（head.html 已有，含 sha256 哈希白名单），
 *       但 X-Content-Type-Options / X-Frame-Options / Permissions-Policy / 强 HSTS 等无法经仓库设置，
 *       只能在「站点的前置层」下发。本 Worker 即在 GitHub Pages 前兜一层，补这些头 + 优化缓存。
 *
 * 为何用 Worker 而非 Transform Rule：
 *   - Worker 在 Cloudflare 全计划（含 Free）可用，确定能跑；
 *   - Transform Rule 的「Modify Response Header」历史上是 Enterprise 才稳定，故以 Worker 为准。
 *
 * 重要：CSP 仍保留在 head.html 的 <meta> 里，本 Worker 不再额外设 CSP 响应头。
 *   原因：响应头 CSP 优先级高于 meta，若这里只写半截会覆盖 meta 导致脚本被拦断；
 *   想升级为「响应头版 CSP」时，必须把 head.html meta 内的全部 sha256 哈希原样搬进下面的
 *   responseHeaders.set("Content-Security-Policy", "...") 才能不破坏站点。
 *
 * 部署步骤（详见随附说明）：
 *   1. Cloudflare 添加站点 longxiong.vip；在阿里云域名控制台把 NS 改为 Cloudflare 提供的两条 NS。
 *   2. Cloudflare DNS 重建记录：A longxiong.vip → 185.199.108.153/109.153/110.153/111.153（与现一致）；
 *      www 用 CNAME → jinlong0221.github.io（若启用）；搜索验证 TXT 从阿里云 DNS 照抄。
 *   3. SSL/TLS → Overview → 模式设 Full（GitHub Pages 有有效证书，勿用 Flexible 以免回源降级）。
 *   4. 本文件建为 Worker，Routes 绑 longxiong.vip/*（www 启用则再加 www.longxiong.vip/*）。
 *   5. NS 生效（几分钟~24h）后 curl -I https://longxiong.vip/ 验证下列头出现。
 */

export default {
  async fetch(request) {
    const response = await fetch(request);
    const newHeaders = new Headers(response.headers);

    // —— 安全响应头（meta 做不到的部分）——
    // HSTS：强于 GitHub Pages 默认的 max-age=31556952（无 includeSubDomains）。
    // 若要加入 preload 列表，把下面末尾加上 "; preload" 并到 hstspreload.org 提交（撤销成本高，按需）。
    newHeaders.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
    newHeaders.set("X-Content-Type-Options", "nosniff");
    newHeaders.set("X-Frame-Options", "DENY"); // head.html 已有 frame-buster 脚本，此为兜底
    newHeaders.set("Referrer-Policy", "strict-origin-when-cross-origin");
    newHeaders.set("Permissions-Policy", "geolocation=(), microphone=(), camera=()");

    // —— 缓存：资源已用 ?v= 内容版本化，可长缓存降低回源；HTML 短缓存保证更新及时 ——
    const url = new URL(request.url);
    const isStatic = /\.(css|js|woff2?|png|jpe?g|webp|avif|gif|svg|ico|json|xml|txt|woff)$/i.test(url.pathname);
    if (isStatic) {
      newHeaders.set("Cache-Control", "public, max-age=86400, stale-while-revalidate=604800");
    } else {
      // HTML / 动态路径：保持较短缓存（与现状 max-age=600 同量级）
      newHeaders.set("Cache-Control", "public, max-age=600");
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders,
    });
  },
};
