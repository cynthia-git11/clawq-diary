/* ════════════════════════════════════════════════════════════════
   倩小虾日记 · 自建访问追踪器 v1（无第三方、无 cookie、不存 PII）
   采集：PV · 可见停留时长 · 滚动完读 · 分享点击 · 时区粗推地区
   上报：navigator.sendBeacon → 自建 endpoint（占位）；localStorage 兜底累计
   ════════════════════════════════════════════════════════════════ */
(function () {
  if (location.search.indexOf('notrack') > -1) return;

  // 自建后端上报地址（部署 Cloudflare Worker / 自有函数后填入；当前仅本地累计）
  var ENDPOINT = '';

  var page = location.pathname.split('/').pop() || 'index.html';
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
