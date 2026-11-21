#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: English per-entry pages entries/en/<N>.html, built from the verified English rows already published on en.html.
Mapping row -> ENTRY N is by "Day D" (rows with a Day that has a different number of Chinese entries are skipped);
within a day with several entries, the assignment is chosen by shared number tokens (EN text vs ZH entry text), and
any row whose best match shares too few numbers is skipped rather than guessed. Writes entries/en/index.html,
sitemap-entries-en.xml, data/entries-en-map.json (read by gen-entry-pages.py for hreflang), and per-row
"Read the entry" links on en.html, then runs scripts/gen-ledger.py on the same root (skip with --no-ledger) and rebuilds
the pages whose ledger status line (from data/ledger.json; template text + ledger fields, never translated) changed.
dateModified = max(published, the ledger dates the status line shows); a later dated footnote note on the Chinese original
(read from index.html with scripts/entry_dates.py, the same code gen-entry-pages.py uses) is named as not included here.
Deterministic, idempotent. Usage: python3 scripts/gen-entries-en.py [--root DIR] [--no-ledger]"""
import os, re, sys, json, html, itertools, collections
sys.dont_write_bytecode = True   # no scripts/__pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entry_dates as ED   # shared with gen-entry-pages.py: entry date, footnote items, dated changes, ledger dates
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
    date_d = ED.entry_date_d(ED.strip((re.search(r'<div class="entry-date">(.*?)</div>', blk, re.S) or [None, ""])[1]))
    zh[n] = dict(n=n, day=int(dm.group(1)) if dm else None, date=f"{ymd.group(1)}-{int(ymd.group(2)):02d}-{int(ymd.group(3)):02d}" if ymd else "",
                 pub=pub, title=strip((re.search(r'<h3 class="entry-title">(.*?)</h3>', blk, re.S) or [None, ""])[1]), text=strip(blk),
                 date_d=date_d, foot_mod=ED.modified(date_d, ED.foot_items(ED.foot_of(blk)[1])))   # same footnote date as the Chinese page
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
    .ee-ledger{margin:0 0 20px;font-family:var(--sans,Inter,sans-serif);font-size:13px;line-height:1.75;color:var(--muted)}
    .ee-ledger p{margin:0;padding:8px 12px;border-left:3px solid var(--claw2,#B8860B);background:var(--bg2,#F6F0E3);border-radius:0 8px 8px 0}.ee-ledger p+p{margin-top:6px}
    .ee-ledger b{color:var(--text);font-weight:700}.ee-ledger a{color:#8A6414;text-decoration:none;border-bottom:1px dashed currentColor}
    .ee-ledger .st-corrected{border-left-color:var(--red,#B5462A)}.ee-ledger .st-corrected b{color:var(--red,#B5462A)}.ee-ledger .st-partly{border-left-color:#9a6a00}.ee-ledger .st-verified{border-left-color:#1B9E7C}
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
                  f'<a href="{up}answers/en/">Q&amp;A</a><a href="{up}topics/">Topics</a><a href="{up}theses-en.html">⚖️ Ledger</a><a href="{up}">中文</a></nav>')
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

# judgment ledger status (2026-11-21): one line per data/ledger.json card, template text + ledger fields only (no translation;
# the author's Chinese wording is quoted as Chinese). Pages are built twice: before gen-ledger.py (which reads the English h1s
# written here) and again after it with the fresh ledger.json, so a status change reaches the English pages in the same run.
LE = {"verified": "✓ Verified", "corrected": "✗ Publicly corrected", "partly": "◐ Partly right", "open": "⏳ Open"}
def load_ledger():
    L = {}
    try:
        for c in json.load(open(os.path.join(ROOT, "data/ledger.json"), encoding="utf-8"))["calls"]: L.setdefault(int(c["entry"]), []).append(c)
    except FileNotFoundError:
        print("WARN gen-entries-en: data/ledger.json missing — ledger status lines skipped (run scripts/gen-ledger.py)")
    return L
def split_row(n):
    """English row of ENTRY n → (title, body, full text); the title is what the page's h1 shows"""
    text = strip(rows[mapping[n]][1])
    if " — " in text[:420]: title, body = text.split(" — ", 1)
    else:
        cut = re.search(r"[.!?](\s|$)", text[:300]); title = text[:cut.end()].strip() if cut else text[:120]; body = text[len(title):].strip()
    return title.strip().rstrip("."), body, text
def ledger_line_en(c):
    """→ (html, plain text of the status part, CorrectionComment date or None); links are relative to entries/en/"""
    n, st, k = c["entry"], c["status"], c["correction_entry"]
    if st == "corrected" and c["corrected_on"]:
        # the correction entry is named by its own title: the English h1 when it has an English edition, else the Chinese h1, in Chinese
        if not k: where = " at the dated ledger reconciliation"
        elif k in mapping: where = f' in <a href="{k}.html">ENTRY {k} “{esc(split_row(k)[0])}”</a>'
        else: where = (f' in <a href="../{k}.html" hreflang="zh-CN">ENTRY {k}' + (f' <span lang="zh-CN">《{esc(zh[k]["title"])}》</span>' if k in zh else "") + "</a> (Chinese)")
        head = f'{LE[st]} on {c["corrected_on"]}{where}'
    elif c["unresolvable"] and c["reconciled"]: head = f'{LE[st]} · resolution source missing (reconciled {c["reconciled"]})'
    elif c["reconciled"]: head = f'{LE[st]} (reconciled {c["reconciled"]})'
    else: head = LE[st]
    bits = [f"<b>{head}</b>"]
    if ED.later_reading(c): bits.append(f'last reading {c["last_reading"]} (see the ledger card)')
    if c["retracted"]: bits.append(f'retracted wording (Chinese original): <span lang="zh-CN">「{esc(c["retracted"])}」</span>')
    if c["subclaim_judged_wrong"]: bits.append(f'sub-claim judged wrong at reconciliation (Chinese original): <span lang="zh-CN">「{esc(c["subclaim_judged_wrong"])}」</span>')
    if st in ("corrected", "partly"): bits.append("the original call is kept as written")
    if st == "open" and c["resolve_dates"]:
        rd_ = c["resolve_dates"]; bits.append(f'final / review-until date{"s" if len(rd_) > 1 else ""} read from the card {", ".join(rd_)}' + (" · overdue" if c["overdue"] else ""))
    if c["backfill"]: bits.append(f'Retrospective, written {c["written_date"]}; event {c["event_date"]}; not scored as a forward call')
    status = "Ledger status: " + " · ".join(bits)
    h = "⚖️ " + status + f' → <a href="../../theses-en.html#call-{n}">Ledger #call-{n}</a>'
    if c.get("first_commit"):
        lag = c.get("commit_lag_days")
        h += (f' · first public commit <a href="{esc(c["first_commit_url"])}" title="Commit in which this entry first appeared in the public repository (Beijing time)" '
              f'aria-label="First public commit git {c["first_commit"][:7]}, {c["first_commit_date"]}">'
              f'git {c["first_commit"][:7]}</a> ({c["first_commit_date"]}' + (f', first committed {lag} days after the stated date' if lag and lag > 1 and not c["backfill"] else "") + ")")
    return h, strip(status), (c["corrected_on"] if st == "corrected" else (c["reconciled"] if st == "partly" else None))

def build_pages(LG):
  pages = []; written = 0
  for n in sorted(mapping, reverse=True):
    d, raw, tag, _ = rows[mapping[n]]; z = zh[n]
    title, body, text = split_row(n)
    cs = LG.get(n, []); lines = [ledger_line_en(c) for c in cs]
    c0 = next((c for c in cs if c["status"] == "corrected"), None) or next((c for c in cs if c["status"] == "partly"), None)
    suf = ""   # ✗ / ◐: dated status at the end of the summary, cut from the English text, never from the suffix
    if c0 and c0["status"] == "corrected": suf = f' (publicly corrected{" on " + c0["corrected_on"] if c0["corrected_on"] else ""}; see the judgment ledger)'
    elif c0: suf = f' (reconciled{" " + c0["reconciled"] if c0["reconciled"] else ""}: partly right; see the judgment ledger)'
    # rows that are all title (ENTRY 36, 42) had an empty description; a body that opens mid-sentence in lowercase (the title split
    # at a dash) reads as broken, so those summaries start at the title
    lead = text if (body and body[:1].islower()) else (body or title)
    desc = (lead[:157 - len(suf)] + "…" if len(lead) > 160 - len(suf) else lead) + suf
    url = f"{BASE}entries/en/{n}.html"; zurl = f"{BASE}entries/{n}.html"
    pub = z["pub"] or (z["date"] + "T13:00:00+08:00" if z["date"] else "")
    # dateModified = max(published, the ledger dates this page's status line shows; same filter as the Chinese page: <= today,
    # full-date entries only). The Chinese page's later footnote dates are not claimed for this edition, which has no footnotes.
    lds = [dd for c in cs for dd in ED.ledger_dates(c)] if len(z["date_d"]) == 10 else []
    mod = max([x for x in [pub] + [dd + "T13:00:00+08:00" for dd in lds] if x] or [""])
    corr = [{"@type": "CorrectionComment", "text": t, **({"datePublished": w} if w else {}), "url": f"{BASE}theses-en.html#{c['call_id']}"}
            for c, (_, t, w) in zip(cs, lines) if c["status"] in ("corrected", "partly")]
    strip_html = (f'\n  <div class="ee-ledger" id="ledger-status" role="note" aria-label="Judgment ledger status">'
                  + "".join(f'<p class="st-{c["status"]}">{h}</p>' for c, (h, _, _) in zip(cs, lines)) + "</div>") if cs else ""
    # visible date: only a date the status line explains ("updated", not "corrected": it can be a reconciliation that kept ⏳,
    # a later reading or a 补记 write date); a later dated note in the Chinese footnotes is named as not included here
    last = f' · Last updated <time datetime="{mod[:10]}">{mod[:10]}</time>' if pub and mod[:10] > pub[:10] else ""
    zf = z["foot_mod"] if (pub and len(z["date_d"]) == 10) else ""
    if zf and zf > max(pub[:10], mod[:10]):
        last += (f' · The Chinese original has a footnote note dated <time datetime="{zf}">{zf}</time> that this English edition does not include'
                 f' → <a href="../{n}.html" hreflang="zh-CN">中文原文</a>')
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BlogPosting", "@id": url, "mainEntityOfPage": url, "url": url, "headline": title[:110], "description": desc, "inLanguage": "en",
         "datePublished": pub, "dateModified": mod or pub, **({"correction": corr[0] if len(corr) == 1 else corr} if corr else {}),
         "author": {"@id": f"{BASE}#cynthia"}, "isPartOf": {"@id": f"{BASE}#blog"},
         "translationOfWork": {"@id": zurl}, "articleBody": text, "image": f"{BASE}assets/clawq-banner.jpg"},
        {"@type": "Person", "@id": f"{BASE}#cynthia", "name": "Cynthia Zhang (张倩)", "url": BASE, "jobTitle": "Founder, FutureX Capital",
         "worksFor": {"@type": "Organization", "name": "FutureX Capital", "url": "https://futurex.capital"}},
        {"@type": "Blog", "@id": f"{BASE}#blog", "name": "The ClawQ Chronicles · 倩小虾日记", "url": BASE},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "The ClawQ Chronicles", "item": f"{BASE}en.html"},
            {"@type": "ListItem", "position": 2, "name": "All entries (English)", "item": f"{BASE}entries/en/"},
            {"@type": "ListItem", "position": 3, "name": f"ENTRY {n}", "item": url}]}]}
    pages.append(dict(n=n, title=title, date=z["date"], day=z["day"], tag=tag, mod=(mod or pub)[:10]))
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
  <div class="ee-meta">ENTRY {n} · <time datetime="{esc(z['date'])}">{esc(d)}</time> · {esc(tag)} · Cynthia Zhang · FutureX Capital · <a href="../{n}.html" hreflang="zh-CN">中文原文 · Chinese original</a>{last}</div>{strip_html}
{paragraphs(body)}
  <nav class="ee-pn" aria-label="Previous and next">{pn}</nav>
  <footer class="ee-foot">English edition of <a href="../{n}.html">ENTRY {n}</a>; the Chinese original, with its full footnotes (sources, method notes, falsifier, disclosure, corrections), is the reference text. Written and verified with Claude; verification status lives in the <a href="../../theses-en.html">judgment ledger</a>. This diary does not constitute promotion of, or an offer to subscribe for, any fund product.</footer>
</div>
</body>
</html>
"""
    written += wr(f"entries/en/{n}.html", page)
  return pages, written
pages, written = build_pages(load_ledger())
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
urls = [f"  <url><loc>{BASE}entries/en/</loc><lastmod>{max(p['mod'] or p['date'] for p in pages)}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>"]
urls += [f"  <url><loc>{BASE}entries/en/{p['n']}.html</loc><lastmod>{p['mod'] or p['date']}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>" for p in pages if p["date"]]   # lastmod = dateModified date
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
# judgment ledger (2026-11-21): gen-ledger.py reads the data/entries-en-map.json and the English h1s written above, so it runs here —
# buildN.py runs this script at its end (and asserts exit 0), and publish_daily.sh / publish_backfill.sh / ledger_apply.sh run it
# again; gen-entry-pages.py runs after this script and reads the same fresh ledger.json. Idempotent.
if "--no-ledger" not in sys.argv:
    import subprocess
    sys.stdout.flush()
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen-ledger.py"), "--root", ROOT])
    if r.returncode: sys.exit(r.returncode)
    # second pass: the English status lines now read the ledger.json gen-ledger.py just wrote (no-op when nothing changed)
    _, w2 = build_pages(load_ledger())
    if w2: print(f"OK · EN pages refreshed from the fresh ledger: {w2}")
