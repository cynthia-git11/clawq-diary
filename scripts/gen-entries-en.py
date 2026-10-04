#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: English per-entry pages entries/en/<N>.html, built from the verified English rows already published on en.html.
Mapping row -> ENTRY N is by "Day D" (rows with a Day that has a different number of Chinese entries are skipped);
within a day with several entries, the assignment is chosen by shared number tokens (EN text vs ZH entry text), and
any row whose best match shares too few numbers is skipped rather than guessed. Writes entries/en/index.html,
sitemap-entries-en.xml, data/entries-en-map.json (read by gen-entry-pages.py for hreflang), and per-row
"Read the entry" links on en.html. Deterministic, idempotent. Usage: python3 scripts/gen-entries-en.py [--root DIR]"""
import os, re, sys, json, html, itertools, collections
BASE = "https://cynthia-git11.github.io/clawq-diary/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = sys.argv[sys.argv.index("--root") + 1]
def rd(f): return open(os.path.join(ROOT, f), encoding="utf-8").read()
def wr(f, s):
    p = os.path.join(ROOT, f); os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p) or open(p, encoding="utf-8").read() != s: open(p, "w", encoding="utf-8").write(s); return 1
    return 0
strip = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
esc = lambda s: html.escape(s or "", quote=True)
NUM = re.compile(r"\d+(?:\.\d+)?")
def nums(t):
    return {x for x in NUM.findall(t.replace(",", "")) if not re.fullmatch(r"20\d\d|\d", x)}

en = rd("en.html"); idx = rd("index.html")
ROW_RE = re.compile(r'<div class="entry-row">\s*<span class="erow-date">([^<]*)</span>\s*<span class="erow-title">(.*?)</span>\s*<span class="erow-tag">(.*?)</span>(?:\s*<a class="erow-link"[^>]*>[^<]*</a>)?\s*</div>', re.S)
rows = [(m.group(1).strip(), m.group(2), strip(m.group(3)), m) for m in ROW_RE.finditer(en)]
def block_at(s, start):
    i = start; depth = 0; tag = re.compile(r"<(/?)div\b[^>]*>", re.I)
    while True:
        m = tag.search(s, i); depth += -1 if m.group(1) else 1; i = m.end()
        if depth == 0: return i
zh = {}
for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>', idx):
    n = int(m.group(1)); blk = idx[m.start():block_at(idx, m.start())]
    dtxt = strip((re.search(r'<div class="entry-date">(.*?)</div>', blk, re.S) or [None, ""])[1])
    dm = re.search(r"Day (\d+)", dtxt); ymd = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", dtxt)
    pub = (re.search(r'"url": "[^"]*#entry-%d",\s*"datePublished": "([^"]+)"' % n, idx) or [None, None])[1]
    zh[n] = dict(n=n, day=int(dm.group(1)) if dm else None, date=f"{ymd.group(1)}-{int(ymd.group(2)):02d}-{int(ymd.group(3)):02d}" if ymd else "",
                 pub=pub, title=strip((re.search(r'<h3 class="entry-title">(.*?)</h3>', blk, re.S) or [None, ""])[1]), text=strip(blk))
byday = collections.defaultdict(list)
for z in zh.values(): byday[z["day"]].append(z["n"])
rday = collections.defaultdict(list)
for i, r in enumerate(rows):
    m = re.search(r"Day (\d+)", r[0]); rday[int(m.group(1)) if m else None].append(i)
mapping = {}; skipped = []
for D, ridx in rday.items():
    ns = sorted(byday.get(D, []), reverse=True)
    if D is None or len(ns) != len(ridx): skipped.append((D, len(ridx), ns)); continue
    rn = [nums(strip(rows[i][1])) for i in ridx]; zn = {n: nums(zh[n]["text"]) for n in ns}
    best = max(itertools.permutations(ns), key=lambda perm: (sum(len(rn[k] & zn[perm[k]]) for k in range(len(perm))), perm == tuple(ns)))
    for k, n in enumerate(best):
        shared = len(rn[k] & zn[n]); need = 1 if len(rn[k]) <= 2 else 2
        if shared < need: skipped.append((D, f"row {ridx[k]} low overlap {shared}/{len(rn[k])}", n)); continue
        mapping[n] = ridx[k]

CSS = """
    .ee-wrap{max-width:820px;margin:0 auto;padding:28px 18px 60px}
    .ee-nav{font-family:var(--sans,Inter,sans-serif);font-size:13px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:22px;color:var(--muted)}
    .ee-nav a{color:var(--claw2,#B8860B);text-decoration:none;font-weight:600}.ee-nav .ee-brand{font-weight:800;color:var(--text);font-size:15px}
    h1.ee-h1{font-size:26px;line-height:1.35;margin-bottom:10px}
    .ee-meta{font-family:var(--sans,Inter,sans-serif);font-size:12.5px;color:var(--muted2);margin-bottom:22px;line-height:1.8}.ee-meta a{color:var(--claw2,#B8860B);text-decoration:none}
    .ee-p{font-size:16px;line-height:1.85;color:var(--text);margin-bottom:14px}.ee-p b{color:var(--claw2,#B8860B)}
    .ee-foot{margin-top:36px;font-size:12px;color:var(--muted2);line-height:1.7;border-top:1px solid var(--border);padding-top:16px}.ee-foot a{color:var(--claw2,#B8860B)}
    .ee-pn{display:flex;justify-content:space-between;gap:16px;margin-top:28px;font-family:var(--sans,Inter,sans-serif);font-size:13px}.ee-pn a{color:var(--claw2,#B8860B);text-decoration:none;max-width:48%}
    .ee-list{list-style:none;padding:0;margin:0}.ee-list li{padding:10px 0;border-bottom:1px solid var(--border)}.ee-list a{color:var(--text);text-decoration:none;font-weight:600;font-size:15px}.ee-when{display:block;font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin-top:2px}
"""
def head(title, desc, url, alt_zh, depth=2, og="article"):
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="alternate" hreflang="en" href="{url}" />{f'<link rel="alternate" hreflang="zh-CN" href="{alt_zh}" /><link rel="alternate" hreflang="x-default" href="{alt_zh}" />' if alt_zh else ''}
  <meta name="robots" content="index,follow,max-snippet:-1" />
  <meta property="og:type" content="{og}" /><meta property="og:title" content="{esc(title)}" /><meta property="og:description" content="{esc(desc)}" /><meta property="og:url" content="{url}" /><meta property="og:image" content="{BASE}assets/clawq-banner.jpg" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{up}assets/css/main.css?v=10" />
  <link rel="icon" type="image/png" href="{up}assets/clawq-square.jpg" />"""
NAV = lambda up: (f'<nav class="ee-nav" aria-label="Site"><a class="ee-brand" href="{up}en.html">🦞 The ClawQ Chronicles</a><a href="./">All entries (English)</a>'
                  f'<a href="{up}answers/en/">Q&amp;A</a><a href="{up}topics/">Topics</a><a href="{up}theses.html">⚖️ Ledger</a><a href="{up}">中文</a></nav>')
LABELS = ["Investors:", "Founders:", "Falsifier:", "Ledger update", "Disclosure:", "Correction", "Verification point:", "Cross-reference:"]
def paragraphs(text):
    t = text
    for lab in LABELS: t = t.replace(" " + lab, "\n" + lab)
    t = t.replace(" This diary does not constitute", "\nThis diary does not constitute")
    out = []
    for para in [p.strip() for p in t.split("\n") if p.strip()]:
        e = esc(para)
        for lab in LABELS:
            if para.startswith(lab): e = f"<b>{esc(lab)}</b>" + esc(para[len(lab):]); break
        out.append(f'  <p class="ee-p">{e}</p>')
    return "\n".join(out)

pages = []; written = 0
for n in sorted(mapping, reverse=True):
    d, raw, tag, _ = rows[mapping[n]]; z = zh[n]
    text = strip(raw)
    if " — " in text[:420]: title, body = text.split(" — ", 1)
    else:
        cut = re.search(r"[.!?](\s|$)", text[:300]); title = text[:cut.end()].strip() if cut else text[:120]; body = text[len(title):].strip()
    title = title.strip().rstrip(".")
    desc = body[:157] + "…" if len(body) > 160 else body
    url = f"{BASE}entries/en/{n}.html"; zurl = f"{BASE}entries/{n}.html"
    pub = z["pub"] or (z["date"] + "T13:00:00+08:00" if z["date"] else "")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BlogPosting", "@id": url, "mainEntityOfPage": url, "url": url, "headline": title[:110], "description": desc, "inLanguage": "en",
         "datePublished": pub, "dateModified": pub, "author": {"@id": f"{BASE}#cynthia"}, "isPartOf": {"@id": f"{BASE}#blog"},
         "translationOfWork": {"@id": zurl}, "articleBody": text, "image": f"{BASE}assets/clawq-banner.jpg"},
        {"@type": "Person", "@id": f"{BASE}#cynthia", "name": "Cynthia Zhang (张倩)", "url": BASE, "jobTitle": "Founder, FutureX Capital",
         "worksFor": {"@type": "Organization", "name": "FutureX Capital", "url": "https://futurex.capital"}},
        {"@type": "Blog", "@id": f"{BASE}#blog", "name": "The ClawQ Chronicles · 倩小虾日记", "url": BASE},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The ClawQ Chronicles", "item": f"{BASE}en.html"},
            {"@type": "ListItem", "position": 2, "name": "All entries (English)", "item": f"{BASE}entries/en/"},
            {"@type": "ListItem", "position": 3, "name": f"ENTRY {n}", "item": url}]}]}
    pages.append(dict(n=n, title=title, date=z["date"], day=z["day"], tag=tag))
    older = next((m for m in sorted(mapping, reverse=True) if m < n), None); newer = next((m for m in sorted(mapping) if m > n), None)
    pn = (f'<a rel="prev" href="{older}.html">← ENTRY {older}</a>' if older else "<span></span>") + (f'<a rel="next" href="{newer}.html" style="text-align:right">ENTRY {newer} →</a>' if newer else "")
    page = head(f"{title} · ENTRY {n} · The ClawQ Chronicles", desc, url, zurl) + f"""
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="ee-wrap">
  {NAV("../../")}
  <h1 class="ee-h1">{esc(title)}</h1>
  <div class="ee-meta">ENTRY {n} · <time datetime="{esc(z['date'])}">{esc(d)}</time> · {esc(tag)} · Cynthia Zhang · FutureX Capital · <a href="../{n}.html" hreflang="zh-CN">中文原文 · Chinese original</a></div>
{paragraphs(body)}
  <nav class="ee-pn" aria-label="Previous and next">{pn}</nav>
  <footer class="ee-foot">English edition of <a href="../{n}.html">ENTRY {n}</a>; the Chinese original, with its full footnotes (sources, method notes, falsifier, disclosure, corrections), is the reference text. Written and verified with Claude; verification status lives in the <a href="../../theses.html">judgment ledger</a>. This diary does not constitute promotion of, or an offer to subscribe for, any fund product.</footer>
</div>
</body>
</html>
"""
    written += wr(f"entries/en/{n}.html", page)
rowsli = "\n".join(f'    <li><a href="{p["n"]}.html">{esc(p["title"])}</a><span class="ee-when">ENTRY {p["n"]} · {esc(p["date"])} · Day {p["day"]} · {esc(p["tag"])}</span></li>' for p in pages)
ld_idx = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "The ClawQ Chronicles · All entries (English)", "url": f"{BASE}entries/en/", "inLanguage": "en",
          "isPartOf": {"@id": f"{BASE}#blog"}, "hasPart": [{"@type": "BlogPosting", "@id": f"{BASE}entries/en/{p['n']}.html", "headline": p["title"][:110], "datePublished": p["date"]} for p in pages]}
written += wr("entries/en/index.html", head(f"All entries in English · {len(pages)} · The ClawQ Chronicles", f"English editions of {len(pages)} entries from Cynthia Zhang's AI investment diary: one call per entry, with the numbers and what would prove it wrong.", f"{BASE}entries/en/", f"{BASE}entries/", og="website") + f"""
  <script type="application/ld+json">
{json.dumps(ld_idx, ensure_ascii=False)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="ee-wrap">
  {NAV("../../")}
  <h1 class="ee-h1">All entries in English · {len(pages)}</h1>
  <p class="ee-p">English editions of the diary, one page per entry. The Chinese originals carry the full footnotes and are the reference text; the <a href="../">Chinese index</a> has all entries.</p>
  <ul class="ee-list">
{rowsli}
  </ul>
  <footer class="ee-foot">Cynthia Zhang · FutureX Capital. This diary does not constitute promotion of, or an offer to subscribe for, any fund product.</footer>
</div>
</body>
</html>
""")
urls = [f"  <url><loc>{BASE}entries/en/</loc><lastmod>{max(p['date'] for p in pages)}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>"]
urls += [f"  <url><loc>{BASE}entries/en/{p['n']}.html</loc><lastmod>{p['date']}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>" for p in pages if p["date"]]
written += wr("sitemap-entries-en.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")
written += wr("data/entries-en-map.json", json.dumps({str(p["n"]): f"entries/en/{p['n']}.html" for p in pages}, ensure_ascii=False, indent=1) + "\n")
# en.html: give each mapped row a crawlable link to its page (idempotent)
inv = {i: n for n, i in mapping.items()}
def addlink(m):
    i = next((k for k, r in enumerate(rows) if r[3].start() == m.start()), None)
    blk = m.group(0); blk = re.sub(r'\s*<a class="erow-link"[^>]*>[^<]*</a>', "", blk)
    if i is None or i not in inv: return blk
    return blk.replace("</span>\n    </div>", f'</span>\n      <a class="erow-link" href="entries/en/{inv[i]}.html">Read the entry →</a>\n    </div>', 1) if "</span>\n    </div>" in blk else blk
en2 = ROW_RE.sub(addlink, en)
if ".erow-link{" not in en2:
    en2 = en2.replace("</head>", "  <style>.entry-row .erow-link{grid-column:2;font-family:var(--sans);font-size:12px;font-weight:700;color:var(--claw2);text-decoration:none}</style>\n</head>", 1)
if 'href="entries/en/"' not in en2:
    i = en2.rfind("</footer>")
    if i > 0: en2 = en2[:i] + '  <p style="font-size:12px;opacity:.75"><a href="entries/en/">All entries in English</a></p>\n' + en2[i:]
written += wr("en.html", en2)
print(f"OK · EN pages {len(pages)} of {len(rows)} rows · skipped {len(skipped)}: {skipped} · files changed {written}")
