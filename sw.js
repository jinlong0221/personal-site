/* 龙兄知识库 Service Worker — 离线阅读（PWA）
 * 策略：
 *  - 安装期预缓存应用外壳（首页 / 离线页 / manifest / 图标 / favicon）。
 *  - 页面导航：网络优先，失败回退缓存，再失败回退离线页（保证离线可读已访问页）。
 *  - 静态资源（css/js/img/字体）：缓存优先 + 后台静默更新（内容寻址 ?v，天然长期缓存）。
 *  - 跨域请求（百度统计 / 不蒜子 / Open-Meteo 等）：不接管，交由浏览器正常请求。
 * 版本升级：修改 CACHE 常量名即可触发 activate 清理旧缓存。
 */
const CACHE = "lx-pwa-v1";
const PRECACHE = [
  "/",
  "/offline.html",
  "/manifest.webmanifest",
  "/favicon.svg",
  "/img/icon-192.png",
  "/img/icon-512.png"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(PRECACHE);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) {
        return caches.delete(k);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;

  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // 跨域不缓存、不接管

  if (req.mode === "navigate") {
    // 页面：网络优先 → 缓存 → 离线页
    event.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); });
        return res;
      }).catch(function () {
        return caches.match(req).then(function (r) {
          return r || caches.match("/offline.html");
        });
      })
    );
    return;
  }

  // 静态资源：缓存优先 + 后台更新
  event.respondWith(
    caches.match(req).then(function (cached) {
      if (cached) {
        // 后台静默刷新
        fetch(req).then(function (res) {
          if (res && res.status === 200) {
            caches.open(CACHE).then(function (c) { c.put(req, res.clone()); });
          }
        }).catch(function () {});
        return cached;
      }
      return fetch(req).then(function (res) {
        if (res && res.status === 200) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        return caches.match("/offline.html");
      });
    })
  );
});
