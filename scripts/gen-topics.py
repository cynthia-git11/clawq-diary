#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: entity hub pages — one URL per company/theme, aggregating every ENTRY that mentions it.

Input : data/topics.json  [{slug, name, name_en, aliases[], blurb(optional, verified prose), blurb_en(optional),
                           entities(optional: holdings-record names for the disclosure), disclosure(optional, non-holdings only)}]
Reads : index.html (entries), theses.html (ledger cards), holdings.json via scripts/holdings_lib.py (every holdings sentence:
        fixed table, TOPIC_ENTITIES[slug] + the topic's entities; names not in the record are printed as PENDING and nothing
        is said about holding them — no fallback sentence)
Writes: topics/<slug>.html, topics/index.html, sitemap-topics.xml (robots.txt Sitemap line added if missing), and the llms.txt
        topic-hub list (only its own <!-- gen:topics --> block, through scripts/llms_sections.py: the topics index rows)
Matching: a topic's name / aliases must appear in the entry outside its 利益披露 clauses (a company named only in the disclosure
        is not a mention) and outside dated 「更新」 footnote notes.

Machine dates (2026-11-22, scripts/machine_dates.py): hasPart datePublished is a backfill's written date (else the entry date), the
page's dateModified and sitemap lastmod the latest such date among its entries; the visible lists keep the event date.
Deterministic: the timeline items are the entry's own title + first sentence (verbatim, no paraphrase);
the optional blurb is the only authored prose and must be verified before it lands in data/topics.json.
Guard: a banned disclosure phrase in any rendered page → exit 1 before anything is written (a clause quoted verbatim from
ENTRY 131–139 is exempt).
Usage: python3 scripts/gen-topics.py [--root DIR] [--dry]   (root: --root, else $CLAWQ_ROOT)
"""
import re, os, sys, json, html, shutil, tempfile

BASE = "https://cynthia-git11.github.io/clawq-diary/"
ROOT = os.environ.get("CLAWQ_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = sys.argv[sys.argv.index("--root") + 1]
DRY = "--dry" in sys.argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True   # no scripts/__pycache__ in the repo
import holdings_lib as HL
import llms_sections as LS
import entry_dates as ED
HOLD = HL.load()
if DRY:
    W = tempfile.mkdtemp(prefix="topics-")
    for f in ["index.html", "theses.html", "robots.txt", "llms.txt"]:
        if os.path.exists(os.path.join(ROOT, f)): shutil.copy(os.path.join(ROOT, f), W)
    os.makedirs(os.path.join(W, "data")); shutil.copy(os.path.join(ROOT, "data/topics.json"), os.path.join(W, "data"))
    ROOT = W
def rd(f): return open(os.path.join(ROOT, f), encoding="utf-8").read()
def wr(f, s):
    p = os.path.join(ROOT, f); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(s)
def strip(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
def esc(s): return html.escape(s, quote=True)

topics = json.load(open(os.path.join(ROOT, "data/topics.json"), encoding="utf-8"))
idx = rd("index.html"); th = rd("theses.html")

def block_at(s, start):
    i = start; depth = 0; tag = re.compile(r"<(/?)div\b[^>]*>", re.I)
    while True:
        m = tag.search(s, i); depth += -1 if m.group(1) else 1; i = m.end()
        if depth == 0: return i
entries = []; ORIG = []
for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>', idx):
    n = int(m.group(1)); blk = idx[m.start():block_at(idx, m.start())]
    if 131 <= n <= 139: ORIG.append(html.unescape(strip(blk)))
    title = strip((re.search(r'<h3 class="entry-title">(.*?)</h3>', blk, re.S) or [None, ""])[1])
    date_txt = strip((re.search(r'<div class="entry-date">(.*?)</div>', blk, re.S) or [None, ""])[1]).replace(" ¶", "")
    dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_txt); ym = re.search(r"(\d{4})年(\d{1,2})月", date_txt)
    date_d = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}" if dm else (f"{ym.group(1)}-{int(ym.group(2)):02d}" if ym else "")
    body = (re.search(r'<div class="entry-body">(.*?)$', blk, re.S) or [None, ""])[1]
    paras = [strip(p) for p in re.findall(r"<p>(.*?)</p>", body, re.S)]
    first = re.split(r"(?<=[。！？])", paras[0])[0] if paras else ""
    quote = strip((re.search(r'<div class="entry-quote">(.*?)</div>', body, re.S) or [None, ""])[1])
    text = ED.topic_text(blk)   # 利益披露 clauses and dated 「更新」 notes are not mentions (scripts/entry_dates.py, shared with gen-entry-pages.py)
    # written date of a backfill (补记): scripts/entry_dates.py written_of, the rule gen-ledger.py and the machine timestamps use
    try: written = ED.backfill_written(blk, date_txt, date_d)
    except ValueError as _e: print(f"gen-topics FAILED: ENTRY {n}: {_e}"); sys.exit(1)
    entries.append(dict(n=n, title=title, date_txt=date_txt, date_d=date_d, first=first, quote=quote, text=text,
                        written=written, pub=written or date_d))   # pub: publication date for machine timestamps (scripts/machine_dates.py)
entries.sort(key=lambda e: -e["n"])

# ledger cards: (claim text, badge, entry n)
cards = []
for m in re.finditer(r'<div class="call"[^>]*>(.*?)</div>\s*</div>\s*</div>', th, re.S):   # cards carry id="call-N" since 2026-11-21 (gen-ledger.py)
    c = m.group(1); n = re.search(r'(?:index\.html#entry-|entries/)(\d+)(?:\.html)?"', c); claim = re.search(r'<div class="claim"><a[^>]*>(.*?)</a>', c, re.S); badge = re.search(r'<span class="badge[^"]*">(.*?)</span>', c, re.S)
    when = re.search(r'<div class="when"><b>([^<]*)</b>', c)
    if n and claim: cards.append(dict(n=int(n.group(1)), claim=strip(claim.group(1)), badge=strip(badge.group(1)) if badge else "", when=when.group(1) if when else ""))

CSS = """
    .tp-wrap{max-width:820px;margin:0 auto;padding:28px 18px 60px}
    .tp-nav{font-family:var(--sans,Inter,sans-serif);font-size:13px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:22px;color:var(--muted)}
    .tp-nav a{color:var(--claw2,#B8860B);text-decoration:none;font-weight:600}.tp-nav .tp-brand{font-weight:800;color:var(--text);font-size:15px}
    h1.tp-h1{font-size:26px;line-height:1.3;margin-bottom:8px}.tp-sub{font-family:var(--sans,Inter,sans-serif);font-size:13px;color:var(--muted2);margin-bottom:22px}
    .tp-blurb{font-size:15px;line-height:1.9;color:var(--muted);margin-bottom:26px}
    .tp-disc{font-family:var(--sans,Inter,sans-serif);font-size:12.5px;line-height:1.75;color:var(--muted2);margin-bottom:22px;padding:10px 12px;border:1px dashed var(--border);border-radius:6px}
    .tp-h2{font-size:14px;font-family:var(--sans,Inter,sans-serif);letter-spacing:.04em;color:var(--muted);text-transform:uppercase;margin:26px 0 10px;border-top:1px solid var(--border);padding-top:16px}
    .tp-list{list-style:none;padding:0;margin:0}.tp-list li{padding:12px 0;border-bottom:1px solid var(--border)}
    .tp-list a{color:var(--text);text-decoration:none;font-weight:600}.tp-list a:hover{color:var(--claw2,#B8860B)}
    .tp-when{display:block;font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin-top:2px}
    .tp-first{display:block;font-size:14px;line-height:1.7;color:var(--muted);margin-top:6px}
    .tp-ledger li{font-size:14px;line-height:1.6}.tp-badge{font-family:var(--sans,Inter,sans-serif);font-size:11px;padding:2px 8px;border-radius:10px;background:var(--bg3);color:var(--claw2,#B8860B);margin-left:8px}
    .tp-foot{margin-top:40px;font-size:12px;color:var(--muted2);line-height:1.7;border-top:1px solid var(--border);padding-top:16px}
"""
HEAD = """  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../assets/css/main.css?v=10" />
  <link rel="icon" type="image/png" href="../assets/clawq-square.jpg" />"""

def match(t, e):
    return any(a.lower() in e["text"].lower() for a in [t["name"]] + t.get("aliases", []))

ans_p = os.path.join(ROOT, "data/answers.json")
answers = json.load(open(ans_p, encoding="utf-8")) if os.path.exists(ans_p) else []
made = []; PENDING = []; OUT = {}
for t in topics:
    hits = [e for e in entries if match(t, e)]
    if len(hits) < t.get("min_entries", 3): continue
    hit_ns = {e["n"] for e in hits}; lcards = [c for c in cards if c["n"] in hit_ns]
    url = f"{BASE}topics/{t['slug']}.html"
    # machine timestamps: an entry is dated by its publication date (a backfill's written date); the page changed when the latest one landed
    last_pub = max((e["pub"] for e in hits), key=lambda d: d if len(d) == 10 else d + "-01")
    desc = t.get("blurb") or f"倩小虾日记里关于 {t['name']} 的全部 {len(hits)} 篇判断，按时间倒序，每篇附验证状态。"
    if len(desc) > 150: desc = desc[:147] + "…"
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": url, "url": url, "name": f"{t['name']} · 倩小虾日记判断脉络", "description": desc, "inLanguage": "zh-CN",
         "about": ({"@type": "Organization", "name": t["name"], "alternateName": t.get("aliases", [])[:6], "url": t["url"]} if t.get("url") else {"@type": "Thing", "name": t["name"], "alternateName": t.get("aliases", [])[:6]}),
         "isPartOf": {"@id": f"{BASE}#blog"}, "dateModified": last_pub,
         "hasPart": [{"@type": "BlogPosting", "@id": f"{BASE}entries/{e['n']}.html", "headline": e["title"], "datePublished": e["pub"]} for e in hits]},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "倩小虾日记", "item": BASE}, {"@type": "ListItem", "position": 2, "name": "主题", "item": f"{BASE}topics/"}, {"@type": "ListItem", "position": 3, "name": t["name"], "item": url}]}]}
    rows = "\n".join(f'      <li><a href="../entries/{e["n"]}.html">{esc(e["title"])}</a><span class="tp-when">ENTRY {e["n"]} · {esc(e["date_txt"])}</span><span class="tp-first">{esc(e["first"])}</span></li>' for e in hits)
    lrows = "\n".join(f'      <li><a href="../entries/{c["n"]}.html">{esc(c["claim"])}</a><span class="tp-badge">{esc(c["badge"])}</span><span class="tp-when">{esc(c["when"])} · ENTRY {c["n"]}</span></li>' for c in lcards) or "      <li>暂无挂账判断。</li>"
    blurb = f'  <p class="tp-blurb">{esc(t["blurb"])}</p>' if t.get("blurb") else ""
    hs, pend = HL.statement(HOLD, HL.TOPIC_ENTITIES.get(t["slug"], []) + t.get("entities", []), True)
    PENDING.extend(f"PENDING disclosure topic {t['slug']}: {p}" for p in pend)
    extra = t.get("disclosure") or ""
    if re.search(r"天际|FutureX", extra) or HL.banned_hits(extra):     # holdings wording comes only from holdings.json
        print(f"WARN topics.json {t['slug']}: disclosure carries holdings wording — ignored"); extra = ""
    head = "本日记由 Claude 系工具写作与核实"
    if re.match(r"本日记由 Claude 系工具写作(与核实)?，", extra): head += "，" + re.sub(r"^本日记由 Claude 系工具写作(与核实)?，", "", extra); extra = ""   # a Claude sentence stays with its subject
    disc = "利益披露：" + "；".join([head] + hs + ([extra] if extra else [])) + "。"
    qa = [q for q in answers if t["slug"] in q.get("topics", [])]
    qrows = "\n".join(f'      <li><a href="../answers/{q["slug"]}.html">{esc(q["q_zh"])}</a><span class="tp-when">{esc(q.get("date", ""))}</span></li>' for q in qa)
    qblock = (f'  <h2 class="tp-h2">投资人与创业者问过（{len(qa)}）</h2>\n  <ul class="tp-list">\n{qrows}\n  </ul>\n' if qa else "")
    OUT[f"topics/{t['slug']}.html"] = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(t['name'])} · 倩小虾日记 {len(hits)} 篇判断脉络</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <meta name="robots" content="index,follow,max-snippet:-1" />
  <meta property="og:type" content="website" /><meta property="og:title" content="{esc(t['name'])} · 倩小虾日记判断脉络" /><meta property="og:description" content="{esc(desc)}" /><meta property="og:url" content="{url}" /><meta property="og:image" content="{BASE}assets/clawq-banner.jpg" />
{HEAD}
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="tp-wrap">
  <nav class="tp-nav" aria-label="站点导航"><a class="tp-brand" href="../">🦞 倩小虾日记</a><a href="./">全部主题</a><a href="../entries/">全部日记</a><a href="../answers/">问答</a><a href="../theses.html">⚖️ 判断台账</a></nav>
  <h1 class="tp-h1">{esc(t['name'])}{(' · ' + esc(t['name_en'])) if t.get('name_en') else ''}</h1>
  <p class="tp-sub">本日记正文提到 {esc(t['name'])} 的 {len(hits)} 篇（只在利益披露里出现的不计） · 最近 {esc(hits[0]['date_txt'])} · 张倩 Cynthia Zhang · FutureX Capital</p>
{blurb}
  <p class="tp-disc">{esc(disc)}</p>
{qblock}  <h2 class="tp-h2">挂账判断（{len(lcards)}）</h2>
  <ul class="tp-list tp-ledger">
{lrows}
  </ul>
  <h2 class="tp-h2">全部相关日记（{len(hits)}，新→旧）</h2>
  <ul class="tp-list">
{rows}
  </ul>
  <footer class="tp-foot">每条只列该篇原标题与第一句，判断状态以 <a href="../theses.html">判断台账</a> 为准；利益披露见各篇尾注。日记由 Claude 系工具写作与核实。本日记不构成对任何基金产品的推介或募集要约。</footer>
</div>
<script src="../assets/js/tracker.js?v=4" defer></script>
</body>
</html>
"""
    made.append(dict(slug=t["slug"], name=t["name"], name_en=t.get("name_en", ""), n=len(hits), last=hits[0]["date_d"], last_written=hits[0]["written"], last_pub=last_pub))

rows = "\n".join(f'      <li><a href="{m["slug"]}.html">{esc(m["name"])}</a>{(" · " + esc(m["name_en"])) if m["name_en"] else ""}<span class="tp-when">{m["n"]} 篇 · 最近 {m["last"]}</span></li>' for m in made)
OUT["topics/index.html"] = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>主题索引 · {len(made)} 个公司与议题 · 倩小虾日记</title>
  <meta name="description" content="按公司与议题汇总倩小虾日记的判断脉络：{esc('、'.join(m['name'] for m in made[:10]))} 等，每个主题一页，列出全部相关日记与挂账判断。" />
  <link rel="canonical" href="{BASE}topics/" /><meta name="robots" content="index,follow" />
{HEAD}
  <script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": "倩小虾日记 · 主题索引", "url": f"{BASE}topics/", "inLanguage": "zh-CN", "hasPart": [{"@type": "CollectionPage", "@id": f"{BASE}topics/{m['slug']}.html", "name": m["name"]} for m in made]}, ensure_ascii=False)}</script>
  <style>{CSS}  </style>
</head>
<body>
<div class="tp-wrap">
  <nav class="tp-nav" aria-label="站点导航"><a class="tp-brand" href="../">🦞 倩小虾日记</a><a href="../entries/">全部日记</a><a href="../answers/">问答</a><a href="../theses.html">⚖️ 判断台账</a></nav>
  <h1 class="tp-h1">主题索引</h1>
  <p class="tp-sub">每个公司或议题一页：全部相关日记（新→旧）与挂账判断的当前状态。</p>
  <ul class="tp-list">
{rows}
  </ul>
  <footer class="tp-foot">张倩 Cynthia Zhang · 天际资本 FutureX Capital · 本日记不构成对任何基金产品的推介或募集要约。</footer>
</div>
<script src="../assets/js/tracker.js?v=4" defer></script>
</body>
</html>
"""
for p in PENDING: print(p)
bad = [(f, h) for f, s in OUT.items() for h in HL.banned_hits(html.unescape(strip(s)), " ".join(ORIG))]
for f, h in bad: print(f"  ✗ banned phrase in {f}: {h}")
if bad: print("gen-topics FAILED: banned disclosure phrase in output — nothing written"); sys.exit(1)
# llms.txt topic hubs: the same rows as topics/index.html (name · other names — entries · latest date), built before anything is
# written (LS.put refuses a block carrying a buildN.py anchor)
def _alt(m):
    en, nm = m["name_en"], m["name"]
    if not en or en in nm: return ""                                  # 「Mistral AI」「英伟达 NVIDIA」: nothing new to add
    return " · " + (en[len(nm) + 3:] if en.startswith(nm + " · ") else en)   # 「Anthropic · Claude」 → 「Claude」
_ll = _ll2 = None
if os.path.exists(os.path.join(ROOT, "llms.txt")):
    _rows = [f"- [{m['name']}]({BASE}topics/{m['slug']}.html){_alt(m)} — {m['n']} 篇 · 最近 {m['last']}"
             + (f"（补记，写于 {m['last_written']}）" if m["last_written"] else "") for m in made]
    _ll = rd("llms.txt")
    _ll2 = LS.put(_ll, "topics", f"## 主题页 Topic hubs\n\n{len(made)} 个公司与议题各一页（中文），列出正文提到它的全部日记（新→旧）与挂账判断的当前状态；"
                  "每行：主题 · 其他名称 — 相关日记篇数（只在利益披露里出现的不计）· 最近一篇的标注日期（补记篇为事件日，另注写作日）。"
                  f"总索引 [topics/]({BASE}topics/)，站点地图 [sitemap-topics.xml]({BASE}sitemap-topics.xml)。\n\n" + "\n".join(_rows))
else: print("WARN llms.txt not found — topic hubs not listed there")
for f, s in OUT.items(): wr(f, s)
def _lm(d): return d if len(d) == 10 else d + "-01"
urls = [f"  <url><loc>{BASE}topics/</loc><lastmod>{max(_lm(m['last_pub']) for m in made) if made else ''}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>"]
urls += [f"  <url><loc>{BASE}topics/{m['slug']}.html</loc><lastmod>{_lm(m['last_pub'])}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>" for m in made]
wr("sitemap-topics.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")
rb = rd("robots.txt")
if "sitemap-topics.xml" not in rb: wr("robots.txt", rb.rstrip("\n") + f"\nSitemap: {BASE}sitemap-topics.xml\n")
if _ll2 is not None and _ll2 != _ll: wr("llms.txt", _ll2)
print(f"{'DRY RUN in ' + ROOT if DRY else 'OK'} · topics {len(made)}/{len(topics)} · " + ", ".join(f"{m['slug']}={m['n']}" for m in made))
