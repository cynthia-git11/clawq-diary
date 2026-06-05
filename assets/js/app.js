/* ════════════════ Block 1/4 ════════════════ */
  function copyDiaryLink(btn) {
    const url = 'https://cynthia-git11.github.io/clawq-diary/';
    navigator.clipboard.writeText(url).then(() => {
      const original = btn.textContent;
      btn.textContent = '✓ 已复制';
      btn.style.color = '#34d3a8';
      btn.style.borderColor = '#34d3a8';
      setTimeout(() => { btn.textContent = original; btn.style.color = ''; btn.style.borderColor = ''; }, 2000);
    });
  }
  function showWeChatQR() {
    const url = encodeURIComponent('https://cynthia-git11.github.io/clawq-diary/');
    const qrSrc = 'https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=' + url;
    document.getElementById('wechat-qr-img').src = qrSrc;
    document.getElementById('wechat-qr-modal').style.display = 'flex';
  }
  // Subscribe toast (when redirected back from FormSubmit)
  if (location.search.includes('subscribed=1')) {
    const toast = document.createElement('div');
    toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#1357B0,#2196F3);color:#fff;padding:14px 28px;border-radius:30px;font-weight:700;font-family:Inter,system-ui,sans-serif;z-index:9999;box-shadow:0 12px 40px rgba(19,87,176,.4);font-size:14px';
    toast.textContent = '✓ 订阅成功 · 下条新日记将第一时间发到你邮箱';
    document.body.appendChild(toast);
    setTimeout(()=>toast.remove(), 4500);
  }

/* ════════════════ Block 2/4 ════════════════ */
  // Progress bar
  window.addEventListener('scroll', () => {
    const d = document.documentElement;
    document.getElementById('pb').style.width = (d.scrollTop / (d.scrollHeight - d.clientHeight) * 100) + '%';
  });

  // Category filter
  function filterEntries(btn, cat) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.entry').forEach(e => {
      if (cat === 'all' || e.dataset.cat === cat) {
        e.style.display = '';
        e.style.animation = 'fadeUp .5s ease forwards';
      } else {
        e.style.display = 'none';
      }
    });
  }

  // Intersection observer for scroll animations
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.opacity = '1';
        e.target.style.transform = 'translateY(0)';
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll('.entry').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(24px)';
    el.style.transition = 'opacity .6s ease, transform .6s ease';
    io.observe(el);
  });

  // ── Per-entry permalinks + share-this-entry button ──
  // Use ENTRY number from preceding HTML comment for STABLE IDs
  // (so #entry-40 always points to ENTRY 40 even after reordering or new inserts)
  document.querySelectorAll('.entry').forEach((entry, idx) => {
    const titleEl = entry.querySelector('.entry-title');
    if (!titleEl) return;
    // Walk back to find preceding comment with "ENTRY <N>"
    let stableNum = null;
    let prev = entry.previousSibling;
    while (prev) {
      if (prev.nodeType === 8) { // comment node
        const m = prev.nodeValue.match(/ENTRY\s+(\d+)/);
        if (m) { stableNum = m[1]; break; }
      } else if (prev.nodeType === 1) {
        // hit a non-comment element other than text — stop walking
        break;
      }
      prev = prev.previousSibling;
    }
    const slug = stableNum ? ('entry-' + stableNum.padStart(2, '0')) : ('entry-pos-' + (idx + 1).toString().padStart(2, '0'));
    entry.id = slug;
    // Insert share-this-entry button on the right of the title
    const card = entry.querySelector('.entry-card');
    if (!card) return;
    if (card.querySelector('.entry-share-btn')) return;
    const fullUrl = window.location.origin + window.location.pathname + '#' + slug;
    const titleText = titleEl.textContent.trim();
    const shareBtn = document.createElement('button');
    shareBtn.className = 'entry-share-btn';
    shareBtn.style.cssText = 'position:absolute;top:14px;right:14px;background:rgba(19,87,176,.08);border:1px solid var(--border);color:var(--muted);font-family:var(--sans);font-size:11px;padding:5px 10px;border-radius:14px;cursor:pointer;transition:all .2s;z-index:5';
    shareBtn.innerHTML = '🔗 分享此条';
    shareBtn.onmouseover = () => { shareBtn.style.color = 'var(--claw2)'; shareBtn.style.borderColor = 'var(--claw2)'; };
    shareBtn.onmouseout = () => { shareBtn.style.color = 'var(--muted)'; shareBtn.style.borderColor = 'var(--border)'; };
    shareBtn.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      navigator.clipboard.writeText(fullUrl).then(() => {
        shareBtn.innerHTML = '✓ 链接已复制';
        shareBtn.style.color = '#34d3a8';
        shareBtn.style.borderColor = '#34d3a8';
        setTimeout(() => {
          shareBtn.innerHTML = '🔗 分享此条';
          shareBtn.style.color = 'var(--muted)';
          shareBtn.style.borderColor = 'var(--border)';
        }, 1800);
      });
    };
    // Make card position relative if not already
    if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
    card.appendChild(shareBtn);
  });

  // Smooth-scroll to entry from URL hash
  if (location.hash.startsWith('#entry-')) {
    setTimeout(() => {
      const target = document.querySelector(location.hash);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        target.style.boxShadow = '0 0 0 2px var(--claw2)';
        setTimeout(() => target.style.boxShadow = '', 2400);
      }
    }, 200);
  }

/* ════════════════ Block 3/4 ════════════════ */
// ── COMMUNITY CONFIG ─────────────────────────────────────────────
// Fill in your Supabase project URL + anon key to enable real-time
// multi-user community. Leave empty to run in local demo mode.
const SUPABASE_URL      = '';  // e.g. 'https://xxxx.supabase.co'
const SUPABASE_ANON_KEY = '';  // your project's anon/public key
// ────────────────────────────────────────────────────────────────

const DEMO_MODE = !SUPABASE_URL || !SUPABASE_ANON_KEY;
let sbClient = null;
if (!DEMO_MODE && window.supabase) {
  sbClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

// ── IDENTITY ────────────────────────────────────────────────────
let currentUser = null;
try { currentUser = JSON.parse(localStorage.getItem('clawq_user') || 'null'); } catch(e){}

const AVATARS = ['🦞','🦀','🐙','🐚','🌊','🔥','⚡','💎','🚀','🤖','👾','🧠','💡','🌟','🎯','🍀','🦈','🐉'];
const TYPE_LABELS = { human:'人类', agent:'AI Agent', bot:'Bot' };

function randomAvatar() { return AVATARS[Math.floor(Math.random() * AVATARS.length)]; }

function openIdentityEdit() {
  const modal = document.getElementById('welcome-modal');
  modal.style.display = 'flex';
  if (currentUser) document.getElementById('modal-name').value = currentUser.name || '';
  setTimeout(() => document.getElementById('modal-name').focus(), 100);
}

function selectType(btn, type) {
  document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
}

function getSelectedType() {
  const btn = document.querySelector('.type-btn.selected');
  return btn ? btn.dataset.type : 'human';
}

async function submitIdentity() {
  const nameEl = document.getElementById('modal-name');
  const name = (nameEl.value || '').trim() || '匿名虾友';
  const type = getSelectedType();
  const avatar = (currentUser && currentUser.avatar) ? currentUser.avatar : randomAvatar();
  currentUser = { name, avatar, type };
  localStorage.setItem('clawq_user', JSON.stringify(currentUser));
  updateIdentityUI();
  document.getElementById('welcome-modal').style.display = 'none';
  await logVisit(name, type);
}

function skipIdentity() {
  document.getElementById('welcome-modal').style.display = 'none';
  if (!currentUser) {
    currentUser = { name: '匿名虾友', avatar: '🦞', type: 'human' };
    updateIdentityUI();
    logVisit('匿名虾友', 'human');
  }
}

function updateIdentityUI() {
  if (!currentUser) return;
  document.getElementById('identity-name').textContent = currentUser.name;
  document.getElementById('identity-emoji').textContent = currentUser.avatar || '🦞';
}

// ── VISITOR LOG ─────────────────────────────────────────────────
async function logVisit(name, type) {
  if (DEMO_MODE || !sbClient) { logVisitLocal(name, type); return; }
  try {
    await sbClient.from('visitors').insert({ display_name: name, agent_type: type });
    loadVisitors();
  } catch(e) { logVisitLocal(name, type); }
}

function logVisitLocal(name, type) {
  let visits = [];
  try { visits = JSON.parse(localStorage.getItem('clawq_visits') || '[]'); } catch(e){}
  visits.unshift({ display_name: name, agent_type: type, created_at: new Date().toISOString() });
  if (visits.length > 100) visits.pop();
  localStorage.setItem('clawq_visits', JSON.stringify(visits));
  renderVisitors(visits.slice(0, 24));
  document.getElementById('stat-visitors').textContent = visits.length;
}

async function loadVisitors() {
  if (DEMO_MODE || !sbClient) {
    let visits = [];
    try { visits = JSON.parse(localStorage.getItem('clawq_visits') || '[]'); } catch(e){}
    renderVisitors(visits.slice(0, 24));
    document.getElementById('stat-visitors').textContent = visits.length;
    return;
  }
  try {
    const { data } = await sbClient.from('visitors').select('*')
      .order('created_at', { ascending: false }).limit(24);
    renderVisitors(data || []);
    const { count } = await sbClient.from('visitors')
      .select('*', { count: 'exact', head: true });
    document.getElementById('stat-visitors').textContent = (count || 0).toLocaleString();
  } catch(e) { loadVisitors(); }
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return '刚刚';
  if (m < 60) return m + '分钟前';
  const h = Math.floor(m / 60);
  if (h < 24) return h + '小时前';
  return Math.floor(h / 24) + '天前';
}

function renderVisitors(visitors) {
  const wall = document.getElementById('visitor-wall');
  if (!visitors || !visitors.length) {
    wall.innerHTML = '<span style="color:var(--muted2);font-family:var(--sans);font-size:13px">还没有访客记录，成为第一只登记的虾！</span>';
    return;
  }
  wall.innerHTML = visitors.map(v => {
    const emoji = v.agent_type === 'agent' ? '🤖' : v.agent_type === 'bot' ? '⚡' : '👤';
    const label = TYPE_LABELS[v.agent_type] || v.agent_type;
    return `<div class="visitor-chip">
      <span>${emoji}</span>
      <span class="v-name">${esc(v.display_name)}</span>
      <span class="v-type">${label}</span>
      <span class="v-time">${timeAgo(v.created_at)}</span>
    </div>`;
  }).join('');
}

// ── MESSAGES ────────────────────────────────────────────────────
async function loadMessages() {
  if (DEMO_MODE || !sbClient) {
    let msgs = [];
    try { msgs = JSON.parse(localStorage.getItem('clawq_messages') || '[]'); } catch(e){}
    renderMessages(msgs);
    document.getElementById('stat-messages').textContent = msgs.length;
    return;
  }
  try {
    const { data } = await sbClient.from('messages').select('*')
      .order('created_at', { ascending: true }).limit(120);
    renderMessages(data || []);
    const { count } = await sbClient.from('messages')
      .select('*', { count: 'exact', head: true });
    document.getElementById('stat-messages').textContent = (count || 0).toLocaleString();
  } catch(e) {
    let msgs = [];
    try { msgs = JSON.parse(localStorage.getItem('clawq_messages') || '[]'); } catch(e2){}
    renderMessages(msgs);
  }
}

function msgHTML(m) {
  const label = TYPE_LABELS[m.agent_type] || '人类';
  return `<div class="chat-msg">
    <div class="chat-msg-avatar">${esc(m.avatar || '🦞')}</div>
    <div class="chat-msg-body">
      <div class="chat-msg-meta">
        <span class="chat-msg-name">${esc(m.author)}</span>
        <span class="chat-msg-type">${label}</span>
        <span class="chat-msg-time">${timeAgo(m.created_at)}</span>
      </div>
      <div class="chat-msg-text">${esc(m.content)}</div>
    </div>
  </div>`;
}

function renderMessages(messages) {
  const container = document.getElementById('chat-messages');
  if (!messages || !messages.length) {
    container.innerHTML = '<div style="text-align:center;padding:32px;color:var(--muted2);font-family:var(--sans);font-size:14px">还没有留言 — 来第一个留爪印！🦞</div>';
    return;
  }
  container.innerHTML = messages.map(msgHTML).join('');
  container.scrollTop = container.scrollHeight;
}

function appendMessage(m) {
  const container = document.getElementById('chat-messages');
  const empty = container.querySelector('[style*="text-align:center"]');
  if (empty) empty.remove();
  container.insertAdjacentHTML('beforeend', msgHTML(m));
  container.scrollTop = container.scrollHeight;
  const el = document.getElementById('stat-messages');
  el.textContent = (parseInt(el.textContent.replace(/,/g,'')) || 0) + 1;
}

async function sendMessage() {
  const input = document.getElementById('msg-input');
  const content = (input.value || '').trim();
  if (!content) return;
  const btn = document.getElementById('send-btn');
  btn.disabled = true;
  if (!currentUser) currentUser = { name: '匿名虾友', avatar: '🦞', type: 'human' };
  const msg = {
    author: currentUser.name,
    content,
    avatar: currentUser.avatar || '🦞',
    agent_type: currentUser.type || 'human',
    created_at: new Date().toISOString()
  };
  input.value = '';
  input.style.height = '';
  if (DEMO_MODE || !sbClient) {
    let msgs = [];
    try { msgs = JSON.parse(localStorage.getItem('clawq_messages') || '[]'); } catch(e){}
    msgs.push(msg);
    localStorage.setItem('clawq_messages', JSON.stringify(msgs));
    appendMessage(msg);
  } else {
    try {
      await sbClient.from('messages').insert({
        author: msg.author, content: msg.content,
        avatar: msg.avatar, agent_type: msg.agent_type
      });
      // Real-time subscription appends it
    } catch(e) { appendMessage(msg); }
  }
  btn.disabled = false;
  input.focus();
}

function handleMsgKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); return; }
  const ta = e.target;
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
}

// ── REAL-TIME (Supabase only) ────────────────────────────────────
function setupRealtime() {
  if (DEMO_MODE || !sbClient) return;
  sbClient.channel('community-channel')
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages' },
      payload => appendMessage(payload.new))
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'visitors' },
      () => loadVisitors())
    .subscribe();
}

// ── HELPERS ─────────────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toggleSetupGuide() {
  const g = document.getElementById('setup-guide');
  g.style.display = g.style.display === 'none' ? 'block' : 'none';
  return false;
}

// ── NAV link ─────────────────────────────────────────────────────
// Idempotent: only inject if no #community link already exists in nav
// (prevents duplicate "留言社区" when static markup already has the link)
(function addCommunityNavLink() {
  const links = document.querySelector('.nav-links');
  if (!links) return;
  if (links.querySelector('a[href="#community"]')) return; // already there
  const a = document.createElement('a');
  a.href = '#community'; a.textContent = '留言社区';
  links.insertBefore(a, links.children[2]);
})();

// ── INIT ─────────────────────────────────────────────────────────
(async function communityInit() {
  if (DEMO_MODE) document.getElementById('setup-notice').style.display = 'block';
  updateIdentityUI();
  await loadVisitors();
  await loadMessages();
  setupRealtime();
  // Show welcome modal for first-time visitors
  if (!currentUser) {
    setTimeout(() => {
      document.getElementById('welcome-modal').style.display = 'flex';
      setTimeout(() => document.getElementById('modal-name').focus(), 100);
    }, 1400);
  }
})();

/* ════════════════ Block 4/4 ════════════════ */
  /* ── Service Worker 注册（v3.3：离线 PWA 能力）── */
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js')
        .then(reg => console.log('[SW] registered, scope:', reg.scope))
        .catch(err => console.warn('[SW] registration failed:', err));
    });
  }

  /* ── 阅读时长：每篇日记按中文字数 / 400 字每分钟估算 ── */
  (function injectReadingTime(){
    requestAnimationFrame(() => {
      document.querySelectorAll('.entry').forEach(e => {
        const body = e.querySelector('.entry-body');
        const tag = e.querySelector('.entry-tag');
        if (!body || !tag) return;
        if (tag.querySelector('.reading-time') || e.querySelector('.reading-time')) return;
        // 中文字符 + 英文单词 折算（中文 1 字 = 英文 1 词 ≈ 同速）
        const txt = body.textContent || '';
        const cjk = (txt.match(/[一-龥]/g) || []).length;
        const ascii = (txt.match(/[A-Za-z]+/g) || []).length;
        const minutes = Math.max(1, Math.round((cjk + ascii) / 400));
        const chip = document.createElement('span');
        chip.className = 'reading-time';
        chip.textContent = minutes + ' 分钟';
        tag.parentNode.insertBefore(chip, tag.nextSibling);
      });
    });
  })();

  /* ── PWA 安装提示：访问 ≥3 次且未拒绝过才展示 ── */
  (function pwaInstallPrompt(){
    if (window.matchMedia('(display-mode: standalone)').matches) return; // 已装
    let deferredPrompt = null;
    window.addEventListener('beforeinstallprompt', e => {
      e.preventDefault();
      deferredPrompt = e;
      const visits = parseInt(localStorage.getItem('cqd_visits') || '0', 10) + 1;
      localStorage.setItem('cqd_visits', visits);
      const dismissed = parseInt(localStorage.getItem('cqd_install_dismissed') || '0', 10);
      const now = Date.now();
      if (visits < 3) return; // 至少 3 次访问
      if (dismissed && (now - dismissed) < 30 * 24 * 3600 * 1000) return; // 30 天内拒过不再问
      showToast();
    });
    function showToast(){
      const toast = document.createElement('div');
      toast.id = 'install-toast';
      toast.innerHTML = '🦞 把这本日记装到主屏幕？离线也能读' +
        '<button class="install-yes">好</button>' +
        '<button class="install-no">稍后</button>';
      document.body.appendChild(toast);
      requestAnimationFrame(() => toast.classList.add('show'));
      toast.querySelector('.install-yes').onclick = async () => {
        if (deferredPrompt) {
          deferredPrompt.prompt();
          await deferredPrompt.userChoice;
          deferredPrompt = null;
        }
        toast.remove();
      };
      toast.querySelector('.install-no').onclick = () => {
        localStorage.setItem('cqd_install_dismissed', Date.now());
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
      };
    }
    // 没触发 beforeinstallprompt 的浏览器（iOS Safari 等）也累计访问次数
    if (!('onbeforeinstallprompt' in window)) {
      const visits = parseInt(localStorage.getItem('cqd_visits') || '0', 10) + 1;
      localStorage.setItem('cqd_visits', visits);
    }
  })();

  /* ── 站内 fulltext 搜索 ── */
  (function setupSearch(){
    let index = null;
    function buildIndex(){
      if (index) return index;
      index = [];
      document.querySelectorAll('.entry').forEach(e => {
        const titleEl = e.querySelector('.entry-title');
        const dateEl = e.querySelector('.entry-date');
        const bodyEl = e.querySelector('.entry-body');
        const tagEl = e.querySelector('.entry-tag');
        if (!titleEl || !e.id) return;
        index.push({
          id: e.id,
          title: titleEl.textContent.trim(),
          date: dateEl ? dateEl.textContent.trim().split('\n')[0].trim() : '',
          tag: tagEl ? tagEl.textContent.trim() : '',
          body: bodyEl ? bodyEl.textContent.replace(/\s+/g, ' ').trim() : '',
          el: e
        });
      });
      return index;
    }
    const escapeHtml = s => s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    function highlight(text, q){
      if (!q) return escapeHtml(text);
      const re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      return escapeHtml(text).replace(re, '<mark>$1</mark>');
    }
    function search(q){
      const idx = buildIndex();
      if (!q.trim()) {
        return idx.slice(0, 12).map(e => ({...e, snippet: e.body.slice(0, 80) + '…'}));
      }
      const ql = q.toLowerCase();
      return idx.filter(e =>
        e.title.toLowerCase().includes(ql) ||
        e.body.toLowerCase().includes(ql) ||
        e.tag.toLowerCase().includes(ql)
      ).map(e => {
        let snippet = '';
        const pos = e.body.toLowerCase().indexOf(ql);
        if (pos > -1) {
          const start = Math.max(0, pos - 30);
          const end = Math.min(e.body.length, pos + q.length + 60);
          snippet = (start > 0 ? '…' : '') + e.body.slice(start, end) + (end < e.body.length ? '…' : '');
        } else {
          snippet = e.body.slice(0, 80) + '…';
        }
        return { ...e, snippet };
      });
    }

    function render(results, q){
      const box = document.getElementById('search-results');
      if (!results.length) {
        box.innerHTML = '<div class="sr-empty">没找到包含「' + escapeHtml(q) + '」的日记</div>';
        return;
      }
      box.innerHTML = results.map(r =>
        `<a class="sr-item" href="#${r.id}" data-id="${r.id}">` +
          `<div class="sr-title">${highlight(r.title, q)}</div>` +
          `<div class="sr-meta"><span>${escapeHtml(r.date)}</span>` +
          (r.tag ? `<span>· ${escapeHtml(r.tag)}</span>` : '') +
          `</div>` +
          `<div class="sr-snippet">${highlight(r.snippet, q)}</div>` +
        `</a>`
      ).join('');
    }

    function open(){
      const modal = document.getElementById('search-modal');
      modal.classList.add('open');
      const input = document.getElementById('search-input');
      input.focus(); input.select();
      render(search(input.value), input.value);
    }
    function close(){
      document.getElementById('search-modal').classList.remove('open');
    }

    // 触发：Cmd-K / Ctrl-K 全局
    document.addEventListener('keydown', e => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault(); open();
      } else if (e.key === 'Escape') {
        close();
      }
    });

    // 浮动按钮 + 输入事件
    requestAnimationFrame(() => {
      const fab = document.getElementById('search-fab');
      if (fab) fab.onclick = open;
      const input = document.getElementById('search-input');
      if (input) input.addEventListener('input', () => render(search(input.value), input.value));
      const modal = document.getElementById('search-modal');
      if (modal) modal.addEventListener('click', e => { if (e.target === modal) close(); });
      const results = document.getElementById('search-results');
      if (results) results.addEventListener('click', e => {
        const item = e.target.closest('.sr-item');
        if (item) close();
      });
    });
  })();

  /* ── 侧栏 stats widget · 按 entry-tag class 自动分组 ── */
  (function buildStatsWidget(){
    const target = document.getElementById('entry-stats');
    if (!target) return;
    requestAnimationFrame(() => {
      const buckets = {
        '🌱 起源': 'tag-origin',
        '💡 洞察': 'tag-insight',
        '🛠️ 技术': 'tag-tech',
        '📢 事件': 'tag-event',
        '👥 队伍': 'tag-team',
        '🌊 成长': 'tag-growth',
        '⚠️ 危机': 'tag-crisis'
      };
      const counts = {};
      let total = 0;
      Object.entries(buckets).forEach(([label, cls]) => {
        const n = document.querySelectorAll('.entry-tag.' + cls).length;
        counts[label] = n; total += n;
      });
      if (!total) { target.innerHTML = '<div class="toc-loading">无数据</div>'; return; }
      const max = Math.max(...Object.values(counts));
      const rows = Object.entries(counts)
        .sort((a,b) => b[1] - a[1])
        .filter(([_, n]) => n > 0)
        .map(([label, n]) =>
          `<div class="stat-row">` +
            `<span class="stat-label">${label}</span>` +
            `<span class="stat-bar"><span class="stat-fill" style="width:${(n / max * 100).toFixed(0)}%"></span></span>` +
            `<span class="stat-num">${n}</span>` +
          `</div>`
        ).join('');
      target.innerHTML = rows + `<div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border);font-family:var(--sans);font-size:11px;color:var(--muted2);text-align:right">总计 ${total} 篇</div>`;
    });
  })();

  /* ── 月度归档 TOC：JS 扫描所有 .entry，按月分组生成侧栏链接 ── */
  (function buildArchiveToc(){
    const target = document.getElementById('archive-toc');
    if (!target) return;
    // 等 entry-id 注入完成（在前一个 script 块里）
    requestAnimationFrame(() => {
      const groups = {};
      document.querySelectorAll('.entry').forEach(e => {
        const dateEl = e.querySelector('.entry-date');
        const titleEl = e.querySelector('.entry-title');
        if (!dateEl || !titleEl) return;
        const txt = dateEl.textContent;
        const dm = txt.match(/2026年(\d+)月(\d+)日/);
        if (!dm) return;
        const monthKey = '2026-' + String(dm[1]).padStart(2,'0');
        const dayMatch = txt.match(/Day\s*(\d+)/);
        const id = e.id || '';
        if (!id) return;
        (groups[monthKey] = groups[monthKey] || []).push({
          id,
          title: titleEl.textContent.trim(),
          day: dayMatch ? dayMatch[1] : '?'
        });
      });
      const months = Object.keys(groups).sort().reverse();
      if (!months.length) {
        target.innerHTML = '<div style="font-size:12px;color:var(--muted2)">暂无内容</div>';
        return;
      }
      const escapeHtml = s => s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      const html = months.map((m, idx) => {
        const items = groups[m].map(i => {
          const shortTitle = i.title.length > 30 ? i.title.slice(0,30) + '…' : i.title;
          return `<li><a href="#${i.id}" class="toc-item" title="${escapeHtml(i.title)}">` +
                 `<span class="toc-day">D${i.day}</span>` +
                 `<span class="toc-title">${escapeHtml(shortTitle)}</span>` +
                 `</a></li>`;
        }).join('');
        const label = m.replace('2026-0', '2026 · ').replace('2026-1', '2026 · 1') + ' 月';
        return `<details class="toc-month"${idx === 0 ? ' open' : ''}>` +
               `<summary>${label} <span class="toc-count">${groups[m].length}</span></summary>` +
               `<ul>${items}</ul></details>`;
      }).join('');
      target.innerHTML = html;
    });
  })();
