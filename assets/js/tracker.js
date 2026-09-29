/* ════════════════════════════════════════════════════════════════
   倩小虾日记 · 自建访问追踪器 v4（无第三方、无 cookie、不存 PII）
   采集：PV · 可见停留时长 · 滚动完读 · 分享点击 · 时区粗推地区
   上报：navigator.sendBeacon → 自建 endpoint（占位）；localStorage 兜底累计
   v4：page 改为「相对站点根的路径」——站点根由本脚本自身的 src 推出
       （…/assets/js/tracker.js 之前的部分），因此 GitHub Pages 子路径与
       将来的自有域名根路径都记同一套标识：
         顶层页保持旧名（index.html / en.html / ja.html / theses.html…，根路径记 index.html）
         子目录页去掉 .html（entries/12 · answers/<slug> · answers/en/<slug> · topics/<slug>）
         目录索引页记 <dir>/index；超过 64 字符时取前 55 字符 + ~ + 8 位十六进制哈希
   ════════════════════════════════════════════════════════════════ */
(function () {
  if (location.search.indexOf('notrack') > -1) return;

  // 自建后端上报地址（部署 Cloudflare Worker / 自有函数后填入；当前仅本地累计）
  var ENDPOINT = 'https://clawq-analytics.clawq.workers.dev/collect';
  var SELF = 'assets/js/tracker.js';
  var MAX_ID = 64;

  // 站点根：同步取 document.currentScript.src（defer 脚本执行期间可用）；取不到时在 document.scripts 里找本脚本
  function siteRoot() {
    var src = '';
    try { src = (document.currentScript && document.currentScript.src) || ''; } catch (e) {}
    if (!src) {
      var ss = document.scripts || [];
      for (var i = 0; i < ss.length; i++) {
        if (ss[i] && ss[i].src && ss[i].src.indexOf(SELF) > -1) { src = ss[i].src; break; }
      }
    }
    if (!src) return '';
    var path = '';
    try { path = new URL(src, location.href).pathname; }
    catch (e) { path = src.replace(/^[a-z][a-z0-9+.\-]*:\/\/[^\/]*/i, '').split('?')[0].split('#')[0]; }
    var k = path.indexOf(SELF);
    return k > -1 ? path.slice(0, k) : '';
  }

  // 稳定字符串哈希（djb2，32 位），输出 8 位十六进制
  function hash8(str) {
    var h = 5381;
    for (var i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0;
    return ('00000000' + (h >>> 0).toString(16)).slice(-8);
  }

  function pageId() {
    var root = siteRoot();
    var p = location.pathname || '/';
    var rel;
    if (root && p.indexOf(root) === 0) rel = p.slice(root.length);
    else if (root && p + '/' === root) rel = '';
    else rel = p.split('/').pop();                       // 推不出站点根：退回 v3 行为（只取文件名）
    if (!rel || rel === 'index.html') return 'index.html';
    if (rel.indexOf('/') === -1) return rel;             // 顶层页保持旧名，历史数据连续
    if (rel.charAt(rel.length - 1) === '/') rel += 'index';
    rel = rel.replace(/\.html$/, '');
    if (rel.length > MAX_ID) rel = rel.slice(0, MAX_ID - 9) + '~' + hash8(rel);
    return rel;
  }

  var page = pageId();
  var lang = document.documentElement.lang || 'zh-CN';
  var tz = '';
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}

  function inferRegion() {
    var map = {
      'Asia/Shanghai': 'CN', 'Asia/Chongqing': 'CN', 'Asia/Urumqi': 'CN',
      'Asia/Hong_Kong': 'HK', 'Asia/Taipei': 'TW', 'Asia/Singapore': 'SG',
      'Asia/Tokyo': 'JP', 'Asia/Seoul': 'KR', 'America/New_York': 'US',
      'America/Los_Angeles': 'US', 'America/Chicago': 'US',
      'Europe/London': 'GB', 'America/Toronto': 'CA'
    };
    if (map[tz]) return map[tz];
    var l = (navigator.language || '').toLowerCase();
    if (l.indexOf('zh-tw') > -1) return 'TW';
    if (l.indexOf('zh-hk') > -1) return 'HK';
    if (l.indexOf('zh') > -1) return 'CN';
    if (l.indexOf('ja') > -1) return 'JP';
    if (l.indexOf('en') > -1) return 'US';
    return 'XX';
  }

  var s = {
    page: page, lang: lang, region: inferRegion(), tz: tz,
    ref: document.referrer ? (function () { try { return new URL(document.referrer).hostname; } catch (e) { return '(direct)'; } })() : '(direct)',
    // ?utm_source=xxx —— 推广渠道归因；无参数时为空，由服务端按 referrer 归类
    utm: (function () { try { return (new URLSearchParams(location.search).get('utm_source') || '').slice(0, 32); } catch (e) { return ''; } })(),
    t_enter: Date.now(), visible_ms: 0, max_scroll: 0, completed: false, shares: 0
  };

  var lastShow = Date.now();
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { s.visible_ms += Date.now() - lastShow; } else { lastShow = Date.now(); }
  });

  function onScroll() {
    var h = document.documentElement;
    var depth = (h.scrollTop + window.innerHeight) / h.scrollHeight;
    if (depth > s.max_scroll) s.max_scroll = depth;
    if (depth >= 0.9 && !s.completed && s.visible_ms + (Date.now() - lastShow) > 15000) {
      s.completed = true; // 滚到 90% 且累计停留 >15s → 计为"读完整篇"，过滤秒滑
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });

  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.share-btn, [data-share], a[href*="twitter.com/intent"], a[href*="service.weibo.com"], a[href*="linkedin.com/sharing"]');
    if (t) { s.shares++; flush('share'); }
  }, true);

  function payload(kind) {
    s.visible_ms += Date.now() - lastShow; lastShow = Date.now();
    return {
      kind: kind, page: s.page, lang: s.lang, region: s.region, ref: s.ref,
      utm_source: s.utm,
      dwell_s: Math.round(s.visible_ms / 1000), scroll: +s.max_scroll.toFixed(2),
      completed: s.completed, shares: s.shares, ts: new Date().toISOString().slice(0, 10)
    };
  }
  function flush(kind) {
    var d = payload(kind);
    if (ENDPOINT && navigator.sendBeacon) {
      try { navigator.sendBeacon(ENDPOINT, JSON.stringify(d)); } catch (e) {}
    }
    try {
      var k = 'cqd_track_' + d.ts, cur = JSON.parse(localStorage.getItem(k) || '{}');
      cur.pv = (cur.pv || 0) + (kind === 'pv' ? 1 : 0);
      cur.dwell_s = Math.max(cur.dwell_s || 0, d.dwell_s);
      cur.completed = cur.completed || d.completed;
      cur.shares = (cur.shares || 0) + (kind === 'share' ? 1 : 0);
      localStorage.setItem(k, JSON.stringify(cur));
    } catch (e) {}
  }

  flush('pv');
  window.addEventListener('beforeunload', function () { flush('exit'); });
  document.addEventListener('visibilitychange', function () { if (document.hidden) flush('hide'); });
})();
