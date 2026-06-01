/* ──────────────────────────────────────────────────────────────────
 * 倩小虾日记 · Service Worker v3.3
 *
 * 策略：
 *   · HTML 页面：network-first（保证读到当天最新日记），网络挂掉再退到缓存
 *   · 静态资源（图片 / 字体 / CSS / JS）：cache-first（节省流量、离线可读）
 *   · 跨域第三方（Plausible 等分析）：直接放行，不缓存
 *
 * Scope：sw.js 自动以自身路径为 scope，GH Pages 下是 /clawq-diary/，
 *        Cloudflare/自定义域下是 /，两边都兼容。
 * ───────────────────────────────────────────────────────────────── */

const VERSION = 'v3.3.0';
const STATIC_CACHE = `clawq-static-${VERSION}`;
const RUNTIME_CACHE = `clawq-runtime-${VERSION}`;

// 必须预缓存的核心资源（首次访问后即可离线打开主页）
const PRECACHE = [
  './',
  './index.html',
  './en.html',
  './manifest.json',
  './atom.xml',
  './sitemap.xml',
  './assets/logo-clawq.png',
  './assets/qianxiaxia.png',
  './assets/portrait-studio.jpeg',
  './assets/clawq-banner.jpg',
  './assets/clawq-square.jpg',
];

// 允许 cache-first 的字体 CDN
const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

// install: 预缓存核心资源，立即激活新版本
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE).catch(err => {
        // 个别资源 404 不该让整个 SW 安装失败 —— 容错
        console.warn('[SW] partial precache failure:', err);
      }))
      .then(() => self.skipWaiting())
  );
});

// activate: 清掉旧版本缓存
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys
        .filter(k => k.startsWith('clawq-') && !k.endsWith(VERSION))
        .map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

// fetch: 双策略路由
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  // 仅处理 GET
  if (req.method !== 'GET') return;

  // 跨域第三方分析 / 追踪 — 不拦截
  if (url.origin !== location.origin && !FONT_HOSTS.includes(url.host)) {
    return;
  }

  // HTML 文档：network-first
  if (req.mode === 'navigate' || req.destination === 'document') {
    event.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(RUNTIME_CACHE).then(c => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req).then(cached => cached || caches.match('./index.html')))
    );
    return;
  }

  // 静态资源：cache-first
  event.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(res => {
        // 只缓存成功的同源 / 字体响应
        if (res.ok && (url.origin === location.origin || FONT_HOSTS.includes(url.host))) {
          const copy = res.clone();
          caches.open(RUNTIME_CACHE).then(c => c.put(req, copy));
        }
        return res;
      }).catch(() => {
        // 图片资源离线时返回 1px 透明 PNG 占位
        if (req.destination === 'image') {
          return new Response(
            atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIAAAUAAeImBZsAAAAASUVORK5CYII='),
            { headers: { 'Content-Type': 'image/png' } }
          );
        }
        return new Response('Offline', { status: 503, statusText: 'Offline' });
      });
    })
  );
});

// 来自页面的消息：可选地强制刷新缓存
self.addEventListener('message', event => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});
