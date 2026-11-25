#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: give every ENTRY its own URL.

Reads index.html (the single-page hub) and writes, idempotently:
  entries/<N>.html        one static page per ENTRY (same markup/classes as the hub, so main.css applies),
                          with BlogPosting + BreadcrumbList JSON-LD, canonical, og/twitter, speakable,
                          and a machine-readable breakdown of the footnote (来源｜证伪口｜口径注｜更正｜利益披露);
                          entries with a judgment-ledger card get a one-line status chip above .entry-body from data/ledger.json
                          (✗ / ◐ also get a CorrectionComment and a dated suffix on the description; title and body unchanged);
                          reader fold (2026-11-23): the footnote, the structured breakdown and the full ledger status sit in ONE
                          <details class="entry-fold"> right after the quote (scripts/entry_fold.py); the reader sees title, date,
                          body and quote first
  entries/index.html      archive list, newest first
  sitemap-entries.xml     one <url> per entry, lastmod = the page's dateModified date
  index.html              wraps every footnote in the reader fold (scripts/entry_fold.py; the footnote markup stays byte for byte);
                          adds a ¶ permalink inside each entry header (internal links = crawl discovery); a backfill's top-5
                          BlogPosting @graph datePublished / dateModified get its written date (scripts/machine_dates.py)
  atom.xml                per-entry page as the alternate link; a backfill's <published> / <updated> get its written date and
                          the feed <updated> follows the latest entry <updated> (entry order unchanged)
  sitemap.xml             when the newest entry is a backfill, buildN.py's page <lastmod> stamps (its event date) → its written date
  data/published-times.json  the time of day of each entry seen in the top-5 @graph, frozen (scripts/machine_dates.py)
  llms.txt                appends " · 单页 <url>" to each ENTRY list line that lacks it
  llms-full.txt           adds "URL: <url>" under each "## ENTRY N" header that lacks it; month headings follow each
                          section's own date (scripts/llms_sections.py months())
  robots.txt              adds Sitemap: line for sitemap-entries.xml if missing

Machine timestamps (2026-11-22): datePublished is the written date of a backfill (补记), else the entry date, at the frozen time of
day; the visible timeline date, Day and order stay on the event date. See scripts/machine_dates.py. A page's meta line reads
「发布 DATE」, or for a backfill 「写于 W（补记，事件日 E）」 (the English edition: "Written W (retrospective entry)", theses.html:
「补记 · 写于 W」): W is when it was written, which can be earlier than its first public commit (162–165: written 11-21, committed 11-22).
Deterministic — no LLM, nothing is paraphrased. Safe to run after every build.
Usage: python3 scripts/gen-entry-pages.py [--root DIR] [--dry]
"""
import re, os, sys, json, html, shutil, tempfile, datetime
sys.dont_write_bytecode = True   # no scripts/__pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from entry_dates import TODAY, entry_date_d, foot_of, foot_items, modified, ledger_dates, later_reading, topic_text, backfill_written
import llms_sections as LS
import machine_dates as MD   # datePublished / dateModified rule, backfill written dates, the frozen time of day, hub/atom post-processing
import entry_fold as EF      # reader fold: the footnote behind one <details> after the quote (index.html and the single pages)

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

idx0 = rd("index.html")
# reader fold first (2026-11-23): buildN.py writes the bare footnote; wrapping it here, before the blocks are read, gives the single
# pages the same wrapper in the same run. Idempotent: the wrapper is rebuilt from the footnote each time (label follows the segments).
idx, FOLDED = EF.fold_hub(idx0)

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
    day = (re.search(r"Day (\d+)", date_txt) or [None, ""])[1]
    date_d = entry_date_d(date_txt)   # full date, or "2026-02" for early month-only entries
    badge = strip((re.search(r'entry-date-badge">(.*?)</span>', blk, re.S) or [None, ""])[1])
    body = (re.search(r'<div class="entry-body">(.*?)$', blk, re.S) or [None, ""])[1]
    paras = [strip(p) for p in re.findall(r"<p>(.*?)</p>", body, re.S)]
    quote = strip((re.search(r'<div class="entry-quote">(.*?)</div>', body, re.S) or [None, ""])[1])
    foot_html, foot = foot_of(blk)
    try: written = backfill_written(blk, date_txt, date_d)   # "" unless a backfill (补记): scripts/entry_dates.py written_of
    except ValueError as _e: print(f"gen-entry-pages FAILED: ENTRY {n}: {_e}"); sys.exit(1)
    entries.append(dict(n=n, a=a, b=b, blk=blk, cat=cat, title=title, date_txt=date_txt, date_d=date_d, day=day,
                        badge=badge, paras=paras, quote=quote, foot=foot, foot_html=foot_html, written=written))
entries.sort(key=lambda e: -e["n"])
assert len({e["n"] for e in entries}) == len(entries), "duplicate entry ids"
byn = {e["n"]: e for e in entries}

# datePublished (scripts/machine_dates.py): publication date = the written date of a backfill (补记), else the entry date; time of day
# frozen in data/published-times.json the first time the entry is seen in index.html's top-5 @graph, else 13:00 — no longer read
# from the @graph on every run (until 2026-11-22 the time jumped from the @graph's 08:00 to 13:00 once an entry left the top 5)
TIMES = MD.load_times(SRC_ROOT, idx, ROOT)
def pdate(e): return MD.pub_date(e["date_d"], e["written"])
def iso(e): return MD.pub_iso(e["n"], e["date_d"], e["written"], TIMES)
def lastmod(e): return e["date_d"] if len(e["date_d"]) == 10 else (e["date_d"] + "-01" if len(e["date_d"]) == 7 else (e["date_d"] + "-01-01" if e["date_d"] else ""))

# ---------- footnote → machine-readable items, dateModified (scripts/entry_dates.py, shared with gen-entries-en.py) ----------
# foot_items(foot) → [(kind, text)]; modified(date_d, items) → latest dated change named in the footnote; ledger_dates(card)

# keywords / about: entities from data/topics.json whose aliases appear in the entry
try:
    TOPICS = json.load(open(os.path.join(SRC_ROOT, "data/topics.json"), encoding="utf-8"))
except Exception:
    TOPICS = []
try:
    EN_MAP = json.load(open(os.path.join(SRC_ROOT, "data/entries-en-map.json"), encoding="utf-8"))
except Exception:
    EN_MAP = {}
try:
    ANSWERS = json.load(open(os.path.join(SRC_ROOT, "data/answers.json"), encoding="utf-8"))
except Exception:
    ANSWERS = []
# judgment ledger (2026-11-21): data/ledger.json is written by scripts/gen-ledger.py, which gen-entries-en.py runs just before
# this script, so the status is fresh. Every word of the status strip is template text; every value is a ledger.json field.
LEDGER = {}
try:
    for _c in json.load(open(os.path.join(SRC_ROOT, "data/ledger.json"), encoding="utf-8"))["calls"]: LEDGER.setdefault(int(_c["entry"]), []).append(_c)
except FileNotFoundError:
    print("WARN gen-entry-pages: data/ledger.json missing — ledger status strips skipped (run scripts/gen-ledger.py)")
# a ledger edit to theses.html without gen-ledger.py (gen-entries-en.py runs it) leaves data/ledger.json stale: say so, the strips would be outdated
if LEDGER and os.path.exists(os.path.join(SRC_ROOT, "theses.html")):
    _th = open(os.path.join(SRC_ROOT, "theses.html"), encoding="utf-8").read(); _bad = []
    _ST = {"b-ok": "verified", "b-bad": "corrected", "b-part": "partly", "b-open": "open"}
    _cards = re.split(r'(?=<div class="call"[^>]*>)', _th)[1:]
    for _c in _cards:
        _n = re.search(r'<div class="claim"><a href="(?:index\.html#entry-|entries/)(\d+)', _c); _b = re.search(r'<span class="badge (b-ok|b-bad|b-part|b-open)">', _c)
        if _n and _b and [x["status"] for x in LEDGER.get(int(_n.group(1)), [])] != [_ST[_b.group(1)]]: _bad.append(_n.group(1))
    if _bad or len(_cards) != sum(len(v) for v in LEDGER.values()):
        print(f"WARN gen-entry-pages: data/ledger.json disagrees with theses.html (cards {len(_cards)} vs {sum(len(v) for v in LEDGER.values())}; "
              f"status differs for ENTRY {', '.join(_bad) or '—'}) — run scripts/gen-entries-en.py (it runs gen-ledger.py) before this script")
LZ = {"verified": "✓ 已验证", "corrected": "✗ 已公开修正", "partly": "◐ 部分成立", "open": "⏳ 进行中"}
def ledger_line(c):
    """one status line per ledger card → (html, plain text of the status part, CorrectionComment date or None)"""
    n, st, k = c["entry"], c["status"], c["correction_entry"]
    if st == "corrected" and c["corrected_on"]:
        # the correction entry is named by its own h1 (author text), so the strip says what was corrected
        kt = f'《{esc(html.unescape(byn[k]["title"]))}》' if k in byn else ""
        head = f'{LZ[st]}（{c["corrected_on"]}；更正见 <a href="{k}.html">ENTRY {k}{kt}</a>）' if k else f'{LZ[st]}（{c["corrected_on"]} 对账）'
    elif c["unresolvable"] and c["reconciled"]: head = f'{LZ[st]} · 裁定源缺失（{c["reconciled"]} 对账）'
    elif c["reconciled"]: head = f'{LZ[st]}（{c["reconciled"]} 对账）'
    else: head = LZ[st]
    bits = [f"<b>{head}</b>"]
    if later_reading(c): bits.append(f'最近读数 {c["last_reading"]}（见台账卡片）')
    if c["retracted"]: bits.append(f'对账收回的说法「{esc(c["retracted"])}」')
    if c["subclaim_judged_wrong"]: bits.append(f'对账判错的子判断「{esc(c["subclaim_judged_wrong"])}」')
    if st in ("corrected", "partly"): bits.append("原文保留不改")
    if st == "open" and c["resolve_dates"]: bits.append("卡片所列裁定日 " + "、".join(c["resolve_dates"]) + ("（已过期，待对账）" if c["overdue"] else ""))
    if c["backfill"]: bits.append(f'补记：写于 {c["written_date"]}（事件日 {c["event_date"]}），单独计数，不计入事前命中')
    status = "台账状态：" + " · ".join(bits)
    h = "⚖️ " + status + f' → <a href="../theses.html#call-{n}">判断台账 #call-{n}</a>'
    if c.get("first_commit"):
        lag = c.get("commit_lag_days")
        h += (f' · 首次公开提交 <a href="{esc(c["first_commit_url"])}" title="本篇首次出现在公开仓库的提交（北京时间）" '
              f'aria-label="首次公开提交 git {c["first_commit"][:7]}，{c["first_commit_date"]}">'
              f'git {c["first_commit"][:7]}</a>（{c["first_commit_date"]}' + (f'，晚于标注日 {lag} 天' if lag and lag > 1 and not c["backfill"] else "") + "）")
    when = c["corrected_on"] if st == "corrected" else (c["reconciled"] if st == "partly" else None)
    return h, html.unescape(strip(status)), when
def ledger_bits(e):
    """light line html, strip html, CorrectionComment list, description suffix, the ledger dates the strip shows, and the subset
    that are correction dates (✗ corrected_on; the reconciliation date of a ◐ call or of a sub-claim judged wrong), for one entry
    ("" / "" / [] / "" / [] / [] without cards)"""
    cs = LEDGER.get(e["n"], [])
    if not cs: return "", "", [], "", [], []
    lines = [ledger_line(c) for c in cs]
    strip_html = ('<div class="ep-ledger" id="ledger-status" role="note" aria-label="判断台账状态">'
                  + "".join(f'<p class="st-{c["status"]}">{h}</p>' for c, (h, _, _) in zip(cs, lines)) + "</div>")
    # one light line above the body (2026-11-23): status chip + 判断台账 link; the full strip above moves into the reader fold
    line_html = ('<p class="ep-ledger-line" role="note" aria-label="判断台账状态">'
                 + "".join(f'<span class="ep-chip st-{c["status"]}">{LZ[c["status"]]}</span>' for c in cs)
                 + f'<a href="../theses.html#call-{cs[0]["entry"]}">判断台账</a></p>')
    corr = [{"@type": "CorrectionComment", "text": t, **({"datePublished": w} if w else {}), "url": f"{BASE}theses.html#{c['call_id']}"}
            for c, (_, t, w) in zip(cs, lines) if c["status"] in ("corrected", "partly")]
    suf = ""
    c0 = next((c for c in cs if c["status"] == "corrected"), None) or next((c for c in cs if c["status"] == "partly"), None)
    if c0 and c0["status"] == "corrected": suf = f'（{c0["corrected_on"] + " " if c0["corrected_on"] else ""}已公开修正，见判断台账）'
    elif c0 and c0["reconciled"]: suf = f'（{c0["reconciled"]} 对账：部分成立）'
    elif c0: suf = "（对账：部分成立，见判断台账）"
    dates = [d for c in cs for d in ledger_dates(c)]
    corr_dates = ([c["corrected_on"] for c in cs if c["status"] == "corrected" and c["corrected_on"]]
                  + [c["reconciled"] for c in cs if c["reconciled"] and (c["status"] == "partly" or c.get("subclaim_judged_wrong"))])
    return line_html, strip_html, corr, suf, dates, corr_dates

def topics_for(e):
    txt = topic_text(e["blk"]).lower()   # same mention rule as the topic hubs (gen-topics.py): disclosure clauses do not count
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
    .ep-ledger{margin:0 0 16px;font-family:var(--sans,Inter,sans-serif);font-size:13px;line-height:1.75;color:var(--muted)}
    .ep-ledger p{margin:0;padding:8px 12px;border-left:3px solid var(--claw2,#B8860B);background:var(--bg2,#F6F0E3);border-radius:0 8px 8px 0}
    .ep-ledger p+p{margin-top:6px}
    .ep-ledger b{color:var(--text);font-weight:700}
    .ep-ledger a{color:#8A6414;text-decoration:none;border-bottom:1px dashed currentColor}
    .ep-ledger .st-corrected{border-left-color:var(--red,#B5462A)}.ep-ledger .st-corrected b{color:var(--red,#B5462A)}
    .ep-ledger .st-partly{border-left-color:#9a6a00}.ep-ledger .st-verified{border-left-color:#1B9E7C}
    /* reader view (2026-11-23): title, date, body and quote first; footnote, its breakdown and the full ledger status in one fold */
    .ep-wrap .entry-card,.ep-wrap .entry-body,.ep-facts{overflow-wrap:anywhere}
    .ep-wrap .entry-body{font-size:16px;line-height:1.85}
    .ep-wrap .entry-body>p{color:var(--text);max-width:42em}
    .ep-ledger-line{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;margin:0 0 14px;font-family:var(--sans,Inter,sans-serif);font-size:12.5px;line-height:1.6;color:var(--muted)}
    .ep-chip{display:inline-block;padding:1px 10px 1px 8px;border-left:3px solid var(--claw2,#B8860B);border-radius:0 999px 999px 0;background:var(--bg2,#F6F0E3);color:var(--text);font-weight:700}
    .ep-chip.st-corrected{border-left-color:var(--red,#B5462A)}.ep-chip.st-partly{border-left-color:#9a6a00}.ep-chip.st-verified{border-left-color:#1B9E7C}
    .ep-ledger-line a{color:#7A5810;text-decoration:none;border-bottom:1px dashed currentColor}
    .entry-fold{margin:2px 0 0;max-width:42em}
    .entry-fold>.ef-sum{display:inline-flex;align-items:center;gap:7px;max-width:100%;list-style:none;cursor:pointer;font-family:var(--sans,Inter,sans-serif);font-size:12.5px;font-weight:600;line-height:1.6;letter-spacing:.02em;color:var(--muted);padding:4px 2px;border-radius:6px;white-space:nowrap;-webkit-user-select:none;user-select:none}
    .entry-fold>.ef-sum::-webkit-details-marker{display:none}
    .entry-fold>.ef-sum::marker{content:""}
    .ef-sum-t{overflow:hidden;text-overflow:ellipsis;border-bottom:1px dashed var(--border2)}
    .ef-sum::after{content:"";flex:none;width:6px;height:6px;margin-left:1px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:translateY(-2px) rotate(45deg);transition:transform .2s ease}
    .entry-fold[open]>.ef-sum::after{transform:translateY(1px) rotate(-135deg)}
    .ef-sum:hover,.ef-sum:focus-visible{color:var(--text)}
    .ef-sum:hover .ef-sum-t{border-bottom-color:var(--claw)}
    .ef-sum:focus-visible{outline:2px solid var(--gold,#9A6B16);outline-offset:2px}
    .entry-fold .ep-ledger{margin:16px 0 0}
    .entry-fold .ep-facts{margin-top:12px;border-top:1px dashed var(--border2);padding-top:14px}
    .entry-fold .ep-facts h2{font-size:12px;margin-bottom:4px;text-transform:none;letter-spacing:.04em;color:var(--muted)}
    .entry-fold .ep-facts dl{display:block;font-size:13.5px;line-height:1.85;color:var(--muted)}
    .entry-fold .ep-facts dt{display:block;margin-top:14px;padding-top:0;font-size:12px;letter-spacing:.04em}
    .entry-fold .ep-facts dd{margin:2px 0 0}
    .entry-fold .ef-kh{font-weight:500;color:var(--muted)}
    .entry-fold .ep-facts~.entry-foot{display:none}
    .entry-fold>.entry-foot{margin-top:10px;padding-top:14px;border-top:1px dashed var(--border2);font-size:13.5px;line-height:1.85;color:var(--muted)}
    .ef-close{display:inline-flex;margin-top:14px;padding:4px 2px;background:none;border:0;border-radius:6px;cursor:pointer;font-family:var(--sans,Inter,sans-serif);font-size:12px;font-weight:600;color:var(--muted)}
    .ef-close:hover,.ef-close:focus-visible{color:var(--text)}.ef-close:focus-visible{outline:2px solid var(--gold,#9A6B16);outline-offset:2px}
    @media (max-width:600px){.ep-wrap .entry-card{padding:22px 18px;border-radius:14px}.ep-wrap .entry-body{font-size:15.5px}.ep-wrap h1.entry-title{font-size:21px}}
    @media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.ef-sum::after{transition:none}}
    @media print{.ef-close,.ef-sum::after{display:none!important}}
    @media print{details.entry-fold::details-content{content-visibility:visible;display:block}}
"""
HEAD_LINKS = """  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../assets/css/main.css?v=10" />
  <link rel="icon" type="image/png" href="../assets/clawq-square.jpg" />
  <link rel="alternate" type="application/atom+xml" title="倩小虾日记 Atom" href="../atom.xml" />"""

DESC_FIX = {  # n → [(原句, 摘要里的替换句)]：只用于搜索/社交摘要，正文与尾注保留原文
    135: [("天际持有被点名的小米，打折读。", "天际原持有被点名的小米（作者 2026-10-10 确认已全部退出，见尾注更新），打折读。")],
}

def page(e, prev_e, next_e):
    url = f"{BASE}entries/{e['n']}.html"
    desc = (e["paras"][0] if e["paras"] else e["title"])
    # 摘要字段（description/og/twitter）不复述已更正的事实；正文 articleBody 保留原文
    for old, new in DESC_FIX.get(e["n"], []): desc = desc.replace(old, new)
    lg_line, lg_html, lg_corr, lg_suf, lg_dates, lg_corr_dates = ledger_bits(e)
    # ✗ / ◐: the summary keeps the original opening and ends with the dated ledger status (cut from the original, never from the suffix)
    if len(desc) > 150 - len(lg_suf): desc = desc[:147 - len(lg_suf)] + "…"
    desc += lg_suf
    body_txt = " ".join(e["paras"] + ([e["quote"]] if e["quote"] else []))
    items = foot_items(e["foot"])
    tops = topics_for(e)
    kw = [t["name"] for t in tops][:8] + [e["cat"]]
    mod = modified(e["date_d"], items)
    # 「最后更正」 only when the date shown is a correction: a footnote 更正 / 勘误 / 纠偏 / 认错 / 后续修正 segment (foot_items
    # files a dated segment under 更正 only when a correction word is in its first 40 characters) or a ledger correction date; a 补记 write date,
    # a reading or a reconciliation that kept the status is 「最后更新」 (2026-11-21: 35 pages said 最后更正 with nothing corrected)
    mod_corr = modified(e["date_d"], [(k, v) for k, v in items if k in ("更正", "勘误", "纠偏", "认错", "后续修正")])
    mod_lab = "最后更正" if mod and (mod in lg_corr_dates or mod_corr == mod != modified(e["date_d"], [])) else "最后更新"
    if lg_dates and len(e["date_d"]) == 10 and max(lg_dates) > (mod or e["date_d"]):   # dates the ledger strip shows on this page
        mod = max(lg_dates)
        mod_lab = "最后更正" if mod in lg_corr_dates else "最后更新"   # a reconciliation that kept ⏳, a later reading or a 补记 write date is not a correction
    if e["written"]:   # a backfill: dates up to its written date (the 补记 write date included) are not changes after publication
        if mod and mod <= e["written"]: mod = ""
        MODS[e["n"]] = max(mod or e["written"], e["written"])
        mod_iso = MD.later(iso(e), mod + "T13:00:00+08:00") if mod else iso(e)
    else:
        MODS[e["n"]] = mod or lastmod(e)
        mod_iso = MD.later(iso(e), (mod + "T13:00:00+08:00") if (mod and mod != e["date_d"]) else iso(e))
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Person", "@id": f"{BASE}#cynthia", "name": "张倩 Cynthia Zhang", "url": BASE,
         "worksFor": {"@type": "Organization", "name": "天际资本 FutureX Capital", "url": "https://futurex.capital"}},
        {"@type": "Blog", "@id": f"{BASE}#blog", "name": "倩小虾日记 · The ClawQ Chronicles", "url": BASE, "inLanguage": "zh-CN"},
        {"@type": "BlogPosting", "@id": url, "mainEntityOfPage": url, "url": url, "headline": e["title"],
         "datePublished": iso(e), "dateModified": mod_iso, **({"correction": lg_corr[0] if len(lg_corr) == 1 else lg_corr} if lg_corr else {}),
         "inLanguage": "zh-CN", "articleSection": e["cat"],
         "about": [({"@type": "Organization", "name": t["name"], "url": t["url"]} if t.get("url") else {"@type": "Thing", "name": t["name"]}) for t in tops][:8],
         "keywords": kw, "description": desc, "articleBody": body_txt, "wordCount": len(re.sub(r"\s", "", body_txt)),
         "author": {"@id": f"{BASE}#cynthia"}, "publisher": {"@id": f"{BASE}#blog"}, "isPartOf": {"@id": f"{BASE}#blog"},
         "image": f"{BASE}assets/clawq-banner.jpg",
         "speakable": {"@type": "SpeakableSpecification", "cssSelector": [".entry-title", ".entry-body > p:first-of-type", ".entry-quote"] + ([".ep-ledger"] if lg_html else [])}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "倩小虾日记", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": "全部日记", "item": f"{BASE}entries/"},
            {"@type": "ListItem", "position": 3, "name": f"ENTRY {e['n']}", "item": url}]}]}
    # structured footnote (shown inside the reader fold): the plain text keeps a literal "<6.5%" and decodes &amp; once (entry_dates.strip
    # did neither); 利益披露 first, the fund disclaimer last; data-kind keeps the machine label
    def dt(k): return ("附注" if k == "其他" else esc(k)) + (f'<span class="ef-kh">：{EF.FALSIFIER_HINT}</span>' if k == "证伪口" else "")
    facts = "\n".join(f"    <dt>{dt(k)}</dt><dd data-kind=\"{esc(k)}\">{esc(v if not v.startswith(k) else v[len(k):].lstrip('：: '))}</dd>"
                      for k, v in EF.ordered(foot_items(EF.plain(e["foot_html"]))))
    facts_html = '<section class="ep-facts" aria-label="尾注结构化">\n  <h2>尾注 · 可核对项</h2>\n  <dl>\n' + facts + "\n  </dl>\n</section>"   # indented where placed
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
    if lg_line:   # ledger status: one line between the title and .entry-body; the full strip goes into the reader fold below
        blk, k = re.subn(r'(\n[ \t]*)(<div class="entry-body">)', lambda m: m.group(1) + lg_line + m.group(1) + m.group(2), blk, count=1)
        if not k: print(f"WARN gen-entry-pages: ENTRY {e['n']} has no .entry-body — ledger status line not placed")
    # reader fold: structured footnote (利益披露 first) and then the full ledger strip, right after the summary; the verbatim footnote
    # stays in the fold too (byte-identical to the hub, hidden by CSS while the structured copy is shown)
    blk, k = re.subn(r'(<details class="entry-fold">\n([ \t]*)<summary class="ef-sum">(?:(?!</summary>).)*</summary>\n)',
                     lambda m: m.group(1) + m.group(2) + facts_html.replace("\n", "\n" + m.group(2)) + "\n" + (m.group(2) + lg_html + "\n" if lg_html else ""),
                     blk, count=1, flags=re.S)
    facts_after = ""
    if not k:
        print(f"WARN gen-entry-pages: ENTRY {e['n']} has no reader fold — footnote breakdown placed after the entry")
        facts_after = "  " + facts_html.replace("\n", "\n  ") + "\n"
        if lg_html: blk = blk.replace(lg_line, lg_html, 1)
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
  <link rel="canonical" href="{url}" />{(chr(10) + f'  <link rel="alternate" hreflang="zh-CN" href="{url}" /><link rel="alternate" hreflang="en" href="{BASE}{EN_MAP[str(e["n"])]}" /><link rel="alternate" hreflang="x-default" href="{url}" />') if str(e["n"]) in EN_MAP else ""}
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
    <a class="ep-brand" href="../">🤖 倩小虾日记</a>
    <a href="./">全部日记</a>
    <a href="../topics/">主题</a>
    <a href="../answers/">问答</a>
    <a href="../theses.html">⚖️ 判断台账</a>
    <a href="../#entry-{e['n']}">在时间线中查看</a>
    <a href="{(f"en/{e['n']}.html" if str(e["n"]) in EN_MAP else "../en.html")}" hreflang="en">EN</a>
  </nav>
  <div class="ep-meta"><span>ENTRY {e['n']}</span><span>{'写于' if e["written"] else '发布'} <time datetime="{iso(e)}">{esc(pdate(e) if e["written"] else lastmod(e))}</time>{f'（补记，事件日 {e["date_d"]}）' if e["written"] else ''}{(f' · {mod_lab} <time datetime="{mod}">{mod}</time>') if mod and mod != (e["written"] or lastmod(e)) else ''}</span><span>张倩 Cynthia Zhang · FutureX Capital</span></div>
  <div class="timeline">
{blk}
  </div>
{facts_after}{related}
  <nav class="ep-pn" aria-label="前后篇">{pn}</nav>
  <footer class="ep-foot">
    本页是 <a href="../#entry-{e['n']}">倩小虾日记 ENTRY {e['n']}</a> 的独立页面，正文与时间线原文逐字一致。作者张倩（Cynthia Zhang），天际资本 FutureX Capital 创始人；日记由 Claude 系工具写作与核实，判断状态以 <a href="../theses.html">判断台账</a> 为准。本日记不构成对任何基金产品的推介或募集要约。
  </footer>
</div>
<script>(function(){{function o(){{var t=null;try{{t=location.hash&&document.getElementById(decodeURIComponent(location.hash.slice(1)));}}catch(e){{}}var d=t&&t.closest&&t.closest("details.entry-fold");if(d&&!d.open){{d.open=true;t.scrollIntoView();}}}}o();addEventListener("hashchange",o);
document.addEventListener("toggle",function(e){{var d=e.target;if(!d.classList||!d.classList.contains("entry-fold")||!d.open||d.querySelector(".ef-close"))return;var b=document.createElement("button");b.type="button";b.className="ef-close";b.textContent="收起";b.addEventListener("click",function(){{d.open=false;var s=d.querySelector("summary");if(s.getBoundingClientRect().top<0)s.scrollIntoView({{block:"center"}});s.focus({{preventScroll:true}});}});d.appendChild(b);}},true);
addEventListener("beforeprint",function(){{document.querySelectorAll("details.entry-fold:not([open])").forEach(function(d){{d.dataset.pr="1";d.open=true;}});}});addEventListener("afterprint",function(){{document.querySelectorAll("details.entry-fold[data-pr]").forEach(function(d){{d.open=false;delete d.dataset.pr;}});}});}})();</script>
<script src="../assets/js/tracker.js?v=5" defer></script>
</body>
</html>
"""

# ---------- write pages ----------
written = 0; MODS = {}   # n → dateModified date (YYYY-MM-DD), for sitemap-entries.xml
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
  <nav class="ep-nav" aria-label="站点导航"><a class="ep-brand" href="../">🤖 倩小虾日记</a><a href="../theses.html">⚖️ 判断台账</a><a href="../en.html">EN</a><a href="../llms.txt">llms.txt</a></nav>
  <h1 class="entry-title" style="font-size:26px">全部日记 · {len(entries)} 篇</h1>
  <p class="entry-body">每篇一个独立 URL，正文与时间线原文一致。判断的验证状态见 <a href="../theses.html">判断台账</a>。</p>
  <ul class="ep-list">
{rows}
  </ul>
  <footer class="ep-foot">张倩 Cynthia Zhang · 天际资本 FutureX Capital · 本日记不构成对任何基金产品的推介或募集要约。</footer>
</div>
<script src="../assets/js/tracker.js?v=5" defer></script>
</body>
</html>
""")

# ---------- sitemap-entries.xml ----------
# lastmod = the page's dateModified date (ledger strips and dated corrections are changes crawlers should re-fetch)
urls = [f"  <url><loc>{BASE}entries/</loc><lastmod>{max(MODS.values())}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>"]
urls += [f"  <url><loc>{BASE}entries/{e['n']}.html</loc><lastmod>{MODS[e['n']]}</lastmod><changefreq>monthly</changefreq><priority>{'0.9' if i < 10 else '0.6'}</priority></url>" for i, e in enumerate(entries) if e["date_d"]]
wr("sitemap-entries.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")

# ---------- hub: ¶ permalink inside each entry header (idempotent) ----------
added = 0
def add_link(m):
    global added
    n = m.group(1); head = m.group(0)
    if 'class="ep-link"' in head: return head
    added += 1
    return head.replace("</div>", f' <a class="ep-link" href="entries/{n}.html" title="本篇独立页面 ENTRY {n}">¶</a></div>', 1)
idx2 = re.sub(r'<div id="entry-(\d+)"[^>]*>\s*<div class="entry-date">.*?</div>', add_link, idx, flags=re.S)   # idx: already folded
if "ep-link{" not in idx2:
    idx2 = idx2.replace("</head>", "  <style>.ep-link{margin-left:10px;color:var(--muted2);text-decoration:none;font-family:var(--sans);font-size:12px}.ep-link:hover{color:var(--claw2)}</style>\n</head>", 1)
# ---------- hub: a backfill's top-5 @graph datePublished / dateModified carry its written date (buildN.py writes the event date) ----------
DATES = {e["n"]: (e["date_d"], e["written"]) for e in entries}
idx2, hub_fixed = MD.fix_hub(idx2, DATES, TIMES)
if idx2 != idx0: wr("index.html", idx2)

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
    # a backfill's <published> / <updated> carry its written date; the feed <updated> = the latest entry <updated> (order unchanged)
    at2, atom_fixed = MD.fix_atom(at2, DATES, TIMES)
    if atom_fixed: print(f"atom.xml: backfill timestamps set for {', '.join(str(x) for x in atom_fixed)}")
    if at2 != at: wr("atom.xml", at2)
# ---------- sitemap.xml: buildN.py's page stamps carry a newest backfill's written date, not its event date ----------
if os.path.exists(os.path.join(ROOT, "sitemap.xml")):
    _sm = rd("sitemap.xml"); _sm2, _smf = MD.fix_sitemap(_sm, DATES)
    if _smf and _sm2 != _sm: wr("sitemap.xml", _sm2); print(f"sitemap.xml: page <lastmod> stamps moved to the newest backfill's written date")
# ---------- theses.html: ledger cards link to the single page ----------
if os.path.exists(os.path.join(ROOT, "theses.html")):
    th = rd("theses.html"); th2 = re.sub(r'href="index\.html#entry-(\d+)"', r'href="entries/\1.html"', th)
    if th2 != th: wr("theses.html", th2)

# ---------- llms.txt / llms-full.txt / robots.txt ----------
l = rd("llms.txt"); l2 = re.sub(r"(- \[ENTRY (\d+) · [^\]]*\]\([^)]*#entry-\2\)[^\n]*?)(?<! 单页 )$",
    lambda m: m.group(1) if ("entries/" in m.group(1)) else m.group(1) + f" · 单页 {BASE}entries/{m.group(2)}.html", l, flags=re.M)
if "**单篇页面 Per-entry pages**" not in l2:   # 2026-10-11 修：原守卫查「## 单篇页面」永不命中，每次运行都多插一行
    l2 = l2.replace("⚖️ **判断总账", f"📄 **单篇页面 Per-entry pages**: [entries/]({BASE}entries/) — 每篇日记一个独立 URL（`entries/<N>.html`），含 BlogPosting JSON-LD 与结构化尾注；单篇引用请用这些 URL。站点地图 [sitemap-entries.xml]({BASE}sitemap-entries.xml)。\n\n⚖️ **判断总账", 1)
if l2 != l: wr("llms.txt", l2)
lf = rd("llms-full.txt"); lf2 = re.sub(r"(^## ENTRY (\d+) · [^\n]*\n)(?!URL: )", lambda m: m.group(1) + f"URL: {BASE}entries/{m.group(2)}.html\n", lf, flags=re.M)
lf2 = LS.months(lf2)   # month headings from each section's own date (scripts/llms_sections.py)
if lf2 != lf: wr("llms-full.txt", lf2)
rb = rd("robots.txt")
if "sitemap-entries.xml" not in rb: wr("robots.txt", rb.rstrip("\n") + f"\nSitemap: {BASE}sitemap-entries.xml\n")

if hub_fixed: print(f"index.html: backfill @graph timestamps set for ENTRY {', '.join(str(x) for x in hub_fixed)}")
print(f"{'DRY RUN in ' + ROOT if DRY else 'OK'} · entries {len(entries)} · pages (re)written {written} · hub permalinks added {added} · footnotes folded {FOLDED} · sitemap-entries {len(urls)} urls")
