#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: give every ENTRY its own URL.

Reads index.html (the single-page hub) and writes, idempotently:
  entries/<N>.html        one static page per ENTRY (same markup/classes as the hub, so main.css applies),
                          with BlogPosting + BreadcrumbList JSON-LD, canonical, og/twitter, speakable,
                          and a machine-readable breakdown of the footnote (来源｜证伪口｜口径注｜更正｜利益披露)
  entries/index.html      archive list, newest first
  sitemap-entries.xml     one <url> per entry, lastmod = entry date
  index.html              adds a ¶ permalink inside each entry header (internal links = crawl discovery)
  llms.txt                appends " · 单页 <url>" to each ENTRY list line that lacks it
  llms-full.txt           adds "URL: <url>" under each "## ENTRY N" header that lacks it
  robots.txt              adds Sitemap: line for sitemap-entries.xml if missing

Deterministic — no LLM, nothing is paraphrased. Safe to run after every build.
Usage: python3 scripts/gen-entry-pages.py [--root DIR] [--dry]
"""
import re, os, sys, json, html, shutil, tempfile, datetime

BASE = "https://cynthia-git11.github.io/clawq-diary/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = sys.argv[sys.argv.index("--root") + 1]
DRY = "--dry" in sys.argv
SRC_ROOT = ROOT
if DRY:
    W = tempfile.mkdtemp(prefix="entrypages-")
    for f in ["index.html", "llms.txt", "llms-full.txt", "robots.txt", "sitemap.xml", "atom.xml", "atom.xsl", "en.html", "ja.html", "theses.html"]:
        shutil.copy(os.path.join(ROOT, f), W)
    shutil.copytree(os.path.join(ROOT, "scripts"), os.path.join(W, "scripts"))
    ROOT = W

def rd(f): return open(os.path.join(ROOT, f), encoding="utf-8").read()
def wr(f, s):
    p = os.path.join(ROOT, f); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(s)
def strip(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
def esc(s): return html.escape(s, quote=True)

idx = rd("index.html")

# ---------- locate every entry block (div id="entry-N" ... matching close) ----------
def block_at(s, start):
    """return end index of the div starting at s[start:] (start points at '<div')."""
    i = start; depth = 0
    tag = re.compile(r"<(/?)div\b[^>]*>", re.I)
    while True:
        m = tag.search(s, i)
        if not m: raise ValueError("unbalanced div")
        depth += -1 if m.group(1) else 1
        i = m.end()
        if depth == 0: return i

entries = []
for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>', idx):
    n = int(m.group(1)); a = m.start(); b = block_at(idx, a)
    blk = idx[a:b]
    cat = (re.search(r'data-cat="([a-z]+)"', m.group(0)) or [None, "insight"])[1]
    title = strip((re.search(r'<h3 class="entry-title">(.*?)</h3>', blk, re.S) or [None, f"ENTRY {n}"])[1])
    date_txt = strip((re.search(r'<div class="entry-date">(.*?)</div>', blk, re.S) or [None, ""])[1])
    dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_txt)
    ym = re.search(r"(\d{4})年(\d{1,2})月", date_txt)
    day = (re.search(r"Day (\d+)", date_txt) or [None, ""])[1]
    # full date when present; early entries only carry a month ("2026年2月初") → partial ISO "2026-02" (valid schema.org Date)
    yy = re.search(r"(\d{4})年", date_txt)
    date_d = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}" if dm else (f"{ym.group(1)}-{int(ym.group(2)):02d}" if ym else (yy.group(1) if yy else ""))
    badge = strip((re.search(r'entry-date-badge">(.*?)</span>', blk, re.S) or [None, ""])[1])
    body = (re.search(r'<div class="entry-body">(.*?)$', blk, re.S) or [None, ""])[1]
    paras = [strip(p) for p in re.findall(r"<p>(.*?)</p>", body, re.S)]
    quote = strip((re.search(r'<div class="entry-quote">(.*?)</div>', body, re.S) or [None, ""])[1])
    foot_html = (re.search(r'<div class="entry-foot">(.*?)</div>', body, re.S) or [None, ""])[1]
    foot = strip(foot_html)
    entries.append(dict(n=n, a=a, b=b, blk=blk, cat=cat, title=title, date_txt=date_txt, date_d=date_d, day=day,
                        badge=badge, paras=paras, quote=quote, foot=foot, foot_html=foot_html))
entries.sort(key=lambda e: -e["n"])
assert len({e["n"] for e in entries}) == len(entries), "duplicate entry ids"
byn = {e["n"]: e for e in entries}

# datePublished: prefer the @graph value when present (top-5), else 13:00 CST of the entry date
pub = dict(re.findall(r'"url": "[^"]*#entry-(\d+)",\s*"datePublished": "([^"]+)"', idx))
def iso(e): return pub.get(str(e["n"])) or ((e["date_d"] + "T13:00:00+08:00") if len(e["date_d"]) == 10 else e["date_d"])
def lastmod(e): return e["date_d"] if len(e["date_d"]) == 10 else (e["date_d"] + "-01" if len(e["date_d"]) == 7 else (e["date_d"] + "-01-01" if e["date_d"] else ""))

# ---------- footnote → machine-readable items ----------
KINDS = ["来源", "证伪口", "口径注", "更正", "利益披露", "对账", "免责", "附注", "单源", "自首", "裁定", "升级线", "认错", "勘误",
         "诚信标注", "原文引语", "合规依据", "关联", "承接", "回滚点", "验收指标", "验收", "验证时限", "时限", "纠偏", "补记", "背景", "专名注",
         "类比出处", "待对账", "赌盘对账", "反向预登记", "后续修正", "事实边界", "时点口径", "工作量口径", "指控内容", "新规", "判断框架验证",
         "引用过往条目", "收获项存档", "纠三个错数", "历史尺子与口径", "表外敞口", "预注册", "金句", "共识", "更新", "注"]
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2})")
def foot_items(foot):
    parts = [p.strip() for p in re.split(r"｜", foot) if p.strip()]
    out = []
    for p in parts:
        k = "其他"
        for kk in KINDS:
            if p.startswith(kk): k = kk; break
        if k == "其他" and DATED.match(p): k = "更正" if re.search(r"更正|纠|勘误|回写|改口|认错", p[:40]) else "补记"
        if k == "其他" and p.startswith("ENTRY "): k = "关联"
        if k == "其他":
            lm = re.match(r"^([^：:，。；\s]{2,8})[：:]", p)
            if lm: k = lm.group(1)
        if "不构成对任何基金产品的推介" in p: k = "免责"
        out.append((k, p))
    return out

# dateModified: latest date named in 更正/对账/补记/后续修正 segments (ISO or M/D in the entry year), never earlier than datePublished
def modified(e, items):
    best = e["date_d"] if len(e["date_d"]) == 10 else ""
    yr = e["date_d"][:4] if e["date_d"] else "2026"
    for k, v in items:
        if k not in ("更正", "对账", "补记", "后续修正", "纠偏", "认错", "勘误", "赌盘对账", "待对账", "更新"): continue
        for m in re.finditer(r"(\d{4})-(\d{2})-(\d{2})", v):
            d = m.group(0)
            if best and d > best and d <= TODAY: best = d
        for m in re.finditer(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])", v):
            d = f"{yr}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
            if best and d > best and d <= TODAY: best = d
    return best
import datetime as _dt
TODAY = (_dt.datetime.utcnow() + _dt.timedelta(hours=8)).strftime("%Y-%m-%d")

# keywords / about: entities from data/topics.json whose aliases appear in the entry
try:
    TOPICS = json.load(open(os.path.join(SRC_ROOT, "data/topics.json"), encoding="utf-8"))
except Exception:
    TOPICS = []
try:
    ANSWERS = json.load(open(os.path.join(SRC_ROOT, "data/answers.json"), encoding="utf-8"))
except Exception:
    ANSWERS = []
def topics_for(e):
    txt = strip(e["blk"]).lower()
    return [t for t in TOPICS if any(a.lower() in txt for a in [t["name"]] + t.get("aliases", []))]

# ---------- page template ----------
CSS = """
    .ep-wrap{max-width:820px;margin:0 auto;padding:28px 18px 60px}
    .ep-nav{font-family:var(--sans,Inter,sans-serif);font-size:13px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:22px;color:var(--muted)}
    .ep-nav a{color:var(--claw2,#B8860B);text-decoration:none;font-weight:600}
    .ep-nav .ep-brand{font-weight:800;color:var(--text);font-size:15px}
    .ep-wrap .entry{margin:0}
    .ep-wrap h1.entry-title{font-size:24px}
    .ep-wrap .entry-date time{font:inherit;color:inherit}
    .ep-wrap .timeline{padding-left:0}
    .ep-wrap .timeline::before{display:none}
    .ep-meta{font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin:14px 0 26px;display:flex;gap:14px;flex-wrap:wrap}
    .ep-facts{margin-top:30px;border-top:1px solid var(--border);padding-top:18px}
    .ep-facts h2{font-size:14px;font-family:var(--sans,Inter,sans-serif);letter-spacing:.04em;color:var(--muted);margin-bottom:12px;text-transform:uppercase}
    .ep-facts dl{display:grid;grid-template-columns:5.5em 1fr;gap:8px 14px;font-size:13px;line-height:1.75;color:var(--muted)}
    .ep-facts dt{font-weight:700;color:var(--text);font-family:var(--sans,Inter,sans-serif);font-size:12px;padding-top:2px}
    .ep-facts dd{margin:0}
    .ep-rel{margin-top:22px;font-family:var(--sans,Inter,sans-serif);font-size:13px;line-height:1.9;color:var(--muted)}
    .ep-rel a{color:var(--claw2,#B8860B);text-decoration:none}
    .ep-pn{display:flex;justify-content:space-between;gap:16px;margin-top:34px;font-family:var(--sans,Inter,sans-serif);font-size:13px}
    .ep-pn a{color:var(--claw2,#B8860B);text-decoration:none;max-width:48%}
    .ep-foot{margin-top:40px;font-size:12px;color:var(--muted2);line-height:1.7;border-top:1px solid var(--border);padding-top:16px}
    .ep-link{margin-left:10px;color:var(--muted2);text-decoration:none;font-family:var(--sans,Inter,sans-serif);font-size:12px}
    .ep-link:hover{color:var(--claw2,#B8860B)}
"""
HEAD_LINKS = """  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../assets/css/main.css?v=10" />
  <link rel="icon" type="image/png" href="../assets/clawq-square.jpg" />
  <link rel="alternate" type="application/atom+xml" title="倩小虾日记 Atom" href="../atom.xml" />"""

def page(e, prev_e, next_e):
    url = f"{BASE}entries/{e['n']}.html"
    desc = (e["paras"][0] if e["paras"] else e["title"])
    if len(desc) > 150: desc = desc[:147] + "…"
    body_txt = " ".join(e["paras"] + ([e["quote"]] if e["quote"] else []))
    items = foot_items(e["foot"])
    tops = topics_for(e)
    kw = [t["name"] for t in tops][:8] + [e["cat"]]
    mod = modified(e, items)
    mod_iso = (mod + "T13:00:00+08:00") if (mod and mod != e["date_d"]) else iso(e)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Person", "@id": f"{BASE}#cynthia", "name": "张倩 Cynthia Zhang", "url": BASE,
         "worksFor": {"@type": "Organization", "name": "天际资本 FutureX Capital", "url": "https://futurex.capital"}},
        {"@type": "Blog", "@id": f"{BASE}#blog", "name": "倩小虾日记 · The ClawQ Chronicles", "url": BASE, "inLanguage": "zh-CN"},
        {"@type": "BlogPosting", "@id": url, "mainEntityOfPage": url, "url": url, "headline": e["title"],
         "datePublished": iso(e), "dateModified": mod_iso, "inLanguage": "zh-CN", "articleSection": e["cat"],
         "about": [({"@type": "Organization", "name": t["name"], "url": t["url"]} if t.get("url") else {"@type": "Thing", "name": t["name"]}) for t in tops][:8],
         "keywords": kw, "description": desc, "articleBody": body_txt, "wordCount": len(re.sub(r"\s", "", body_txt)),
         "author": {"@id": f"{BASE}#cynthia"}, "publisher": {"@id": f"{BASE}#blog"}, "isPartOf": {"@id": f"{BASE}#blog"},
         "image": f"{BASE}assets/clawq-banner.jpg",
         "speakable": {"@type": "SpeakableSpecification", "cssSelector": [".entry-title", ".entry-body > p:first-of-type", ".entry-quote"]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "倩小虾日记", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": "全部日记", "item": f"{BASE}entries/"},
            {"@type": "ListItem", "position": 3, "name": f"ENTRY {e['n']}", "item": url}]}]}
    facts = "\n".join(f"      <dt>{esc(k)}</dt><dd data-kind=\"{esc(k)}\">{esc(v if not v.startswith(k) else v[len(k):].lstrip('：: '))}</dd>" for k, v in items)
    rel_t = [t for t in tops if os.path.exists(os.path.join(SRC_ROOT, "topics", t["slug"] + ".html"))][:8]
    rel_q = [q for q in ANSWERS if e["n"] in [int(x) for x in q.get("entries", [])]][:8]
    related = ""
    if rel_t or rel_q:
        related = '  <section class="ep-rel" aria-label="相关">\n'
        if rel_t: related += '    <p><strong>相关主题</strong>：' + " · ".join(f'<a href="../topics/{t["slug"]}.html">{esc(t["name"])}</a>' for t in rel_t) + "</p>\n"
        if rel_q: related += '    <p><strong>这篇回答了</strong>：' + " · ".join(f'<a href="../answers/{q["slug"]}.html">{esc(q["q_zh"])}</a>' for q in rel_q if q.get("slug")) + "</p>\n"
        related += "  </section>"
    pn = ""
    if prev_e: pn += f'<a rel="prev" href="{prev_e["n"]}.html">← ENTRY {prev_e["n"]} · {esc(prev_e["title"])}</a>'
    else: pn += "<span></span>"
    if next_e: pn += f'<a rel="next" href="{next_e["n"]}.html" style="text-align:right">ENTRY {next_e["n"]} · {esc(next_e["title"])} →</a>'
    # entry block: drop the (最新) comment if any, keep classes; strip the ¶ permalink if present (page is the permalink)
    blk = re.sub(r'\s*<a class="ep-link"[^>]*>¶</a>', "", e["blk"])
    blk = blk.replace('<h3 class="entry-title">', '<h1 class="entry-title">', 1).replace("</h3>", "</h1>", 1) if '<h3 class="entry-title">' in blk else blk
    lm = lastmod(e)
    if lm and e["date_txt"]:
        blk = re.sub(r'(<div class="entry-date">)(.*?)(</div>)', lambda m: m.group(1) + f'<time datetime="{lm}">' + m.group(2) + "</time>" + m.group(3), blk, count=1, flags=re.S)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(e['title'])} · ENTRY {e['n']} · 倩小虾日记</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{esc(e['title'])} · 倩小虾日记 ENTRY {e['n']}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:site_name" content="倩小虾日记 · The ClawQ Chronicles" />
  <meta property="og:image" content="{BASE}assets/clawq-banner.jpg" />
  <meta property="article:published_time" content="{iso(e)}" />
  <meta property="article:modified_time" content="{mod_iso}" />
  <meta property="article:author" content="张倩 Cynthia Zhang" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{esc(e['title'])}" />
  <meta name="twitter:description" content="{esc(desc)}" />
{HEAD_LINKS}
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="ep-wrap">
  <nav class="ep-nav" aria-label="站点导航">
    <a class="ep-brand" href="../">🦞 倩小虾日记</a>
    <a href="./">全部日记</a>
    <a href="../topics/">主题</a>
    <a href="../answers/">问答</a>
    <a href="../theses.html">⚖️ 判断台账</a>
    <a href="../#entry-{e['n']}">在时间线中查看</a>
    <a href="../en.html">EN</a>
  </nav>
  <div class="ep-meta"><span>ENTRY {e['n']}</span><span>发布 <time datetime="{iso(e)}">{esc(lastmod(e))}</time>{(' · 最后更正 <time datetime="' + mod + '">' + mod + '</time>') if mod and mod != e['date_d'] else ''}</span><span>张倩 Cynthia Zhang · FutureX Capital</span></div>
  <div class="timeline">
{blk}
  </div>
  <section class="ep-facts" aria-label="尾注结构化">
    <h2>尾注 · 可核对项</h2>
    <dl>
{facts}
    </dl>
  </section>
{related}
  <nav class="ep-pn" aria-label="前后篇">{pn}</nav>
  <footer class="ep-foot">
    本页是 <a href="../#entry-{e['n']}">倩小虾日记 ENTRY {e['n']}</a> 的独立页面，正文与时间线原文逐字一致。作者张倩（Cynthia Zhang），天际资本 FutureX Capital 创始人；日记由 Claude 系工具写作与核实，判断状态以 <a href="../theses.html">判断台账</a> 为准。本日记不构成对任何基金产品的推介或募集要约。
  </footer>
</div>
<script src="../assets/js/tracker.js?v=4" defer></script>
</body>
</html>
"""

# ---------- write pages ----------
written = 0
for i, e in enumerate(entries):
    newer = entries[i - 1] if i > 0 else None      # list is newest-first: index i-1 is newer
    older = entries[i + 1] if i + 1 < len(entries) else None
    html_out = page(e, older, newer)
    p = f"entries/{e['n']}.html"
    if not os.path.exists(os.path.join(ROOT, p)) or rd(p) != html_out: wr(p, html_out); written += 1

# ---------- archive index ----------
rows = "\n".join(f'      <li><a href="{e["n"]}.html">{esc(e["title"])}</a> <span class="ep-when">ENTRY {e["n"]} · {esc(e["date_d"])}{" · Day " + e["day"] if e["day"] else ""}</span></li>' for e in entries)
ld_idx = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "倩小虾日记 · 全部日记", "url": f"{BASE}entries/", "inLanguage": "zh-CN",
          "isPartOf": {"@id": f"{BASE}#blog"}, "hasPart": [{"@type": "BlogPosting", "@id": f"{BASE}entries/{e['n']}.html", "headline": e["title"], "datePublished": iso(e)} for e in entries]}
wr("entries/index.html", f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>全部日记 · {len(entries)} 篇 · 倩小虾日记</title>
  <meta name="description" content="张倩（FutureX Capital 创始人）AI 投资日记全部 {len(entries)} 篇的独立页面索引，按时间倒序；每篇一个 URL，正文 350 字内的商业判断加可核对的尾注。" />
  <link rel="canonical" href="{BASE}entries/" />
  <meta name="robots" content="index,follow" />
{HEAD_LINKS}
  <script type="application/ld+json">
{json.dumps(ld_idx, ensure_ascii=False)}
  </script>
  <style>{CSS}
    .ep-list{{list-style:none;padding:0;margin:0}} .ep-list li{{padding:10px 0;border-bottom:1px solid var(--border);font-size:15px;line-height:1.5}}
    .ep-list a{{color:var(--text);text-decoration:none;font-weight:600}} .ep-list a:hover{{color:var(--claw2,#B8860B)}}
    .ep-when{{display:block;font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin-top:2px}}
  </style>
</head>
<body>
<div class="ep-wrap">
  <nav class="ep-nav" aria-label="站点导航"><a class="ep-brand" href="../">🦞 倩小虾日记</a><a href="../theses.html">⚖️ 判断台账</a><a href="../en.html">EN</a><a href="../llms.txt">llms.txt</a></nav>
  <h1 class="entry-title" style="font-size:26px">全部日记 · {len(entries)} 篇</h1>
  <p class="entry-body">每篇一个独立 URL，正文与时间线原文一致。判断的验证状态见 <a href="../theses.html">判断台账</a>。</p>
  <ul class="ep-list">
{rows}
  </ul>
  <footer class="ep-foot">张倩 Cynthia Zhang · 天际资本 FutureX Capital · 本日记不构成对任何基金产品的推介或募集要约。</footer>
</div>
<script src="../assets/js/tracker.js?v=4" defer></script>
</body>
</html>
""")

# ---------- sitemap-entries.xml ----------
urls = [f"  <url><loc>{BASE}entries/</loc><lastmod>{entries[0]['date_d']}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>"]
urls += [f"  <url><loc>{BASE}entries/{e['n']}.html</loc><lastmod>{lastmod(e)}</lastmod><changefreq>monthly</changefreq><priority>{'0.9' if i < 10 else '0.6'}</priority></url>" for i, e in enumerate(entries) if e["date_d"]]
wr("sitemap-entries.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")

# ---------- hub: ¶ permalink inside each entry header (idempotent) ----------
added = 0
def add_link(m):
    global added
    n = m.group(1); head = m.group(0)
    if 'class="ep-link"' in head: return head
    added += 1
    return head.replace("</div>", f' <a class="ep-link" href="entries/{n}.html" title="本篇独立页面 ENTRY {n}">¶</a></div>', 1)
idx2 = re.sub(r'<div id="entry-(\d+)"[^>]*>\s*<div class="entry-date">.*?</div>', add_link, idx, flags=re.S)
if "ep-link{" not in idx2:
    idx2 = idx2.replace("</head>", "  <style>.ep-link{margin-left:10px;color:var(--muted2);text-decoration:none;font-family:var(--sans);font-size:12px}.ep-link:hover{color:var(--claw2)}</style>\n</head>", 1)
if idx2 != idx: wr("index.html", idx2)

# ---------- atom.xml: per-entry page becomes the alternate link; the hub anchor stays as rel="related" (geo-check keeps finding #entry-N) ----------
if os.path.exists(os.path.join(ROOT, "atom.xml")):
    at = rd("atom.xml")
    at2 = re.sub(r'<link href="' + re.escape(BASE) + r'#entry-(\d+)" ?/>',
                 lambda m: f'<link rel="alternate" type="text/html" href="{BASE}entries/{m.group(1)}.html" />\n    <link rel="related" href="{BASE}#entry-{m.group(1)}" />', at)
    # a few 2026-05 entries linked the hub section (#diary) instead of their anchor: use the <id> number
    def fix_diary(m):
        blk = m.group(0); idm = re.search(r"<id>" + re.escape(BASE) + r"entries/(\d+)</id>", blk)
        if not idm or 'href="' + BASE + '#diary"' not in blk: return blk
        n = idm.group(1)
        return re.sub(r'<link href="' + re.escape(BASE) + r'#diary" ?/>', f'<link rel="alternate" type="text/html" href="{BASE}entries/{n}.html" />\n    <link rel="related" href="{BASE}#entry-{n}" />', blk, count=1)
    at2 = re.sub(r"<entry>.*?</entry>", fix_diary, at2, flags=re.S)
    if at2 != at: wr("atom.xml", at2)
# ---------- theses.html: ledger cards link to the single page ----------
if os.path.exists(os.path.join(ROOT, "theses.html")):
    th = rd("theses.html"); th2 = re.sub(r'href="index\.html#entry-(\d+)"', r'href="entries/\1.html"', th)
    if th2 != th: wr("theses.html", th2)

# ---------- llms.txt / llms-full.txt / robots.txt ----------
l = rd("llms.txt"); l2 = re.sub(r"(- \[ENTRY (\d+) · [^\]]*\]\([^)]*#entry-\2\)[^\n]*?)(?<! 单页 )$",
    lambda m: m.group(1) if ("entries/" in m.group(1)) else m.group(1) + f" · 单页 {BASE}entries/{m.group(2)}.html", l, flags=re.M)
if "## 单篇页面" not in l2:
    l2 = l2.replace("⚖️ **判断总账", f"📄 **单篇页面 Per-entry pages**: [entries/]({BASE}entries/) — 每篇日记一个独立 URL（`entries/<N>.html`），含 BlogPosting JSON-LD 与结构化尾注；单篇引用请用这些 URL。站点地图 [sitemap-entries.xml]({BASE}sitemap-entries.xml)。\n\n⚖️ **判断总账", 1)
if l2 != l: wr("llms.txt", l2)
lf = rd("llms-full.txt"); lf2 = re.sub(r"(^## ENTRY (\d+) · [^\n]*\n)(?!URL: )", lambda m: m.group(1) + f"URL: {BASE}entries/{m.group(2)}.html\n", lf, flags=re.M)
if lf2 != lf: wr("llms-full.txt", lf2)
rb = rd("robots.txt")
if "sitemap-entries.xml" not in rb: wr("robots.txt", rb.rstrip("\n") + f"\nSitemap: {BASE}sitemap-entries.xml\n")

print(f"{'DRY RUN in ' + ROOT if DRY else 'OK'} · entries {len(entries)} · pages (re)written {written} · hub permalinks added {added} · sitemap-entries {len(urls)} urls")
