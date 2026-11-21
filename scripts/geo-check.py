#!/usr/bin/env python3
"""GEO health check for clawq-diary (hourly CI guard).

Deterministic, read-only. Exits non-zero on any failure so the workflow
fails and the owner is alerted. Does NOT edit content — unattended edits to
a public brand site are intentionally avoided; breakage is flagged for a
human/agent to fix correctly.

Checks:
  1. JSON-LD blocks parse in index/en/ja (the most common GEO breakage)
  2. atom.xml / sitemap.xml / atom.xsl are well-formed XML
  3. robots.txt still allows the key AI crawlers
  4. The newest entry (ItemList position 1) is synced across carriers
  4b. BlogPosting @graph contains all ItemList top-5 (anti silent drift)
  5. Day count is consistent (title vs stats) in index.html
  6. atom.xml entries: no duplicates, descending, newest == ItemList position 1
  7. Judgment ledger: theses.html card count == badge count == "N 个重大" (×3) == numberOfItems,
     one date-only dateModified, and the llms.txt ledger line a/b/c/d == the badge counts.
     These hold after buildN.py alone (it bumps all of them together); the files derived by
     scripts/gen-ledger.py (tiles, data/ledger.json, theses-en.html) are checked as warnings
     in geo-optimize.py instead, so a publish that skips gen-ledger never turns CI red.
  8. Q&A and topic pages (answers/, answers/en/, topics/): no banned disclosure phrase (a clause quoted verbatim
     from the original ENTRY 131–139 text is exempt), every English .aw-status is free of CJK characters, and every
     JSON-LD block parses. gen-answers.py / gen-topics.py stop on the same conditions, but the publish scripts pipe
     their output, so this hourly check is the one that actually blocks.
  9. FAQ answers (index/en/ja) that quote a wording data/ledger.json lists as retracted or judged wrong carry the dated
     theses.html#call-N pointer; every such pointer names a call on the ledger and carries that call's current status word
     (scripts/hub_sync.py STATUS_WORD); and no English answer or en.html entry row states "~2.1x" without the ~3.7x
     correction (all written by scripts/gen-ledger.py through scripts/hub_sync.py, in the same run as data/ledger.json).
 10. No dead URL in the discovery files: every <loc> and xhtml:link href in sitemap-index.xml and the sitemaps it lists, and
     every markdown link target on this site in llms.txt, is a file in the repo (a directory URL → its index.html). The
     press-ja.html hreflang alternate was a 404 for weeks: geo-work/hygiene0928.py add_ja copied every hreflang="en" link
     to a ja one without checking that the page exists.
"""
import re, json, sys, os, glob, html as _html
from xml.etree import ElementTree as ET

errors = []


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def jsonld_blocks(html):
    return re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)


# 1. JSON-LD valid
for f in ["index.html", "en.html", "ja.html", "theses.html", "theses-en.html"]:
    try:
        for i, b in enumerate(jsonld_blocks(read(f))):
            try:
                json.loads(b)
            except Exception as e:
                errors.append(f"{f}: JSON-LD block {i} invalid — {e}")
    except FileNotFoundError:
        errors.append(f"{f}: file missing")

# 2. XML well-formed
for f in ["atom.xml", "sitemap.xml", "atom.xsl"]:
    try:
        ET.parse(f)
    except Exception as e:
        errors.append(f"{f}: XML parse error — {e}")

# 3. robots.txt AI crawlers
try:
    robots = read("robots.txt")
    for bot in ["GPTBot", "ClaudeBot", "PerplexityBot", "OAI-SearchBot", "Google-Extended"]:
        if bot not in robots:
            errors.append(f"robots.txt: missing AI crawler {bot}")
except FileNotFoundError:
    errors.append("robots.txt: file missing")

# 4. Latest entry synced across carriers
idx = read("index.html")
m = re.search(r'"position":\s*1,\s*"url":\s*"[^"]*#(entry-\d+)"', idx)
if not m:
    errors.append("index.html: cannot locate latest entry in ItemList (position 1)")
else:
    latest = m.group(1)          # e.g. entry-89
    num = latest.split("-")[1]   # e.g. 89
    if f'id="{latest}"' not in idx:
        errors.append(f'index.html: missing <div id="{latest}"> for latest entry')
    if f"#{latest}" not in read("atom.xml"):
        errors.append(f"atom.xml: latest {latest} not present")
    if f"#{latest}" not in read("llms.txt"):
        errors.append(f"llms.txt: latest {latest} not present")
    if f"ENTRY {num}" not in read("llms-full.txt"):
        errors.append(f"llms-full.txt: ENTRY {num} not present")

# 4b. BlogPosting @graph must mirror ItemList top-5 (silent-drift guard;
# 2026-07-10: ENTRY 98 once vanished from @graph while ItemList was fine)
top5 = re.findall(r'"position":\s*\d+,\s*"url":\s*"[^"]*#(entry-\d+)"', idx)[:5]
gm = re.search(r'最新 5 篇 BlogPosting.*?<script type="application/ld\+json">(.*?)</script>', idx, re.S)
if not gm:
    errors.append("index.html: cannot locate BlogPosting @graph block")
elif top5:
    graph_ids = set(re.findall(r'#(entry-\d+)', gm.group(1)))
    missing = [e for e in top5 if e not in graph_ids]
    if missing:
        errors.append(f"index.html: BlogPosting @graph missing {', '.join(missing)} (ItemList top-5 must all be present)")

# 5. Day count consistency (title vs stats)
title_day = re.search(r"<title>[^<]*Day (\d+)", idx)
stats_day = re.search(r'stat-val claw-text">Day (\d+)<', idx)
if title_day and stats_day and title_day.group(1) != stats_day.group(1):
    errors.append(f"index.html: Day mismatch — title={title_day.group(1)} stats={stats_day.group(1)}")

# 6. atom.xml entries: no duplicate ENTRY numbers, descending order, newest == ItemList position 1
#    (2026-09-09: derived build scripts silently duplicated 130/132 and dropped 131/133; #entry-N existed in the
#     feed header so check 4 passed. Order/duplicate must be asserted explicitly.)
try:
    _atom = read("atom.xml")
    _nums = [int(x) for x in re.findall(r'<entry>\s*<title>ENTRY (\d+) ', _atom)]
    _dups = sorted({n for n in _nums if _nums.count(n) > 1})
    if _dups:
        errors.append(f"atom.xml: duplicate entries for ENTRY {_dups}")
    if _nums != sorted(_nums, reverse=True):
        errors.append("atom.xml: entries not in descending ENTRY order")
    if m and _nums and f"entry-{_nums[0]}" != latest:
        errors.append(f"atom.xml: first entry is ENTRY {_nums[0]} but ItemList position 1 is {latest}")
except Exception as _e:
    errors.append(f"atom.xml: order/duplicate check crashed — {_e}")

# 7. Judgment ledger invariants (2026-11-21, with scripts/gen-ledger.py). buildN.py asserts the first three
#    before it adds a card; if they break, the next daily build stops half-way through theses.html.
try:
    _th = read("theses.html")
    _cards = len(re.findall(r'<div class="call"[^>]*>', _th))
    _cnt = {k: len(re.findall(r'<span class="badge %s">' % k, _th)) for k in ("b-ok", "b-bad", "b-part", "b-open")}
    if sum(_cnt.values()) != _cards:
        errors.append(f"theses.html: {_cards} cards but {sum(_cnt.values())} status badges")
    _tot = re.search(r"(\d+) 个重大", _th)
    if not _tot or int(_tot.group(1)) != _cards or _th.count(f"{_cards} 个重大") != 3:
        errors.append(f"theses.html: '{_cards} 个重大' must appear exactly 3 times and match the {_cards} cards (buildN.py)")
    if _th.count('"numberOfItems"') != 1 or f'"numberOfItems": {_cards}' not in _th:
        errors.append(f"theses.html: exactly one numberOfItems, equal to {_cards} (buildN.py)")
    _dm = re.search(r'"dateModified": "(\d{4}-\d{2}-\d{2})"', _th)
    if not _dm or _th.count(f'"dateModified": "{_dm.group(1)}"') != 1:
        errors.append("theses.html: the first date-only dateModified must be unique in the file (buildN.py)")
    _ll = re.search(r"(\d+) 个重大判断的可审计台账（(\d+) 已验证 / (\d+) 已公开修正 / (?:(\d+) 部分成立 / )?(\d+) 进行中，(\d{4}-\d{2}-\d{2}) 更新）", read("llms.txt"))
    if not _ll:
        errors.append("llms.txt: ledger line not in the format buildN.py parses")
    else:
        _got = [int(_ll.group(1)), int(_ll.group(2)), int(_ll.group(3)), int(_ll.group(4) or 0), int(_ll.group(5))]
        _want = [_cards, _cnt["b-ok"], _cnt["b-bad"], _cnt["b-part"], _cnt["b-open"]]
        if _got != _want:
            errors.append(f"llms.txt: ledger line {_got} ≠ theses.html badges {_want} (total/✓/✗/◐/⏳) — run scripts/gen-ledger.py")
except FileNotFoundError as _e:
    errors.append(f"ledger check: file missing — {_e}")

# 8. Q&A / topic pages (2026-11-21). BANNED: keep in sync with scripts/holdings_lib.py
BANNED = ["按公开可查信息", "按公开信息无头寸", "本篇未核实", "on publicly available information"]
CJK = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]")
def _plain(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"</?[A-Za-z][^>]*>", "", s))).strip()
try:
    _orig = []
    for _n in range(131, 140):     # original entries whose footnotes predate the rule; never rewritten
        _i = idx.find(f'<div id="entry-{_n}"')
        if _i != -1:
            _j = idx.find('<div id="entry-', _i + 10)
            _orig.append(_plain(idx[_i:_j if _j != -1 else len(idx)]))
    _orig = " ".join(_orig)
    _pages = sorted(glob.glob("answers/*.html") + glob.glob("answers/en/*.html") + glob.glob("topics/*.html"))
    _ban, _cjk, _ld = [], [], []
    for _f in _pages:
        _h = read(_f); _t = _plain(_h)
        for _b in BANNED:
            for _m in re.finditer(re.escape(_b), _t, re.I):
                _a = max(_t.rfind(c, 0, _m.start()) for c in "。；｜") + 1
                _z = min([x for x in (_t.find(c, _m.end()) for c in "。；｜") if x != -1] or [len(_t)])
                _cl = _t[_a:_z].strip()
                if not (len(_cl) >= 12 and _cl in _orig):
                    _ban.append(f"{_f}: {_cl[:60]}")
        if _f.startswith("answers/en/"):
            for _st in re.findall(r'<div class="aw-status">(.*?)</div>', _h, re.S):
                if CJK.search(_plain(_st)):
                    _cjk.append(_f)
        for _i, _blk in enumerate(jsonld_blocks(_h)):
            try:
                json.loads(_blk)
            except Exception as _e:
                _ld.append(f"{_f} block {_i}: {_e}")
    if not _pages:
        errors.append("answers/ and topics/: no pages found")
    for _x in _ban[:10]:
        errors.append(f"banned disclosure phrase — {_x}")
    if len(_ban) > 10:
        errors.append(f"... {len(_ban) - 10} more banned-phrase hits")
    for _x in sorted(set(_cjk))[:10]:
        errors.append(f"{_x}: English .aw-status contains CJK characters")
    for _x in _ld[:10]:
        errors.append(f"JSON-LD invalid — {_x}")
except Exception as _e:
    errors.append(f"Q&A/topic page check crashed — {_e}")

# 9. FAQ answers (index/en/ja FAQPage) that quote a wording the ledger retracted (✗) or judged wrong at reconciliation
#    carry the dated pointer to that card (#call-N), and no English answer states "~2.1x" without the 3.7x correction
#    (2026-11-21). The wordings come from data/ledger.json, which gen-ledger.py writes in the same run as the pointers
#    (scripts/hub_sync.py), so a reconciliation that has not been through gen-ledger.py yet does not turn this red.
#    Each pointer's status word must equal the call's status in data/ledger.json (a call moved to ✓ / ⏳ is refreshed too),
#    and the en.html entry rows follow the same ~2.1x rule.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.dont_write_bytecode = True
    import hub_sync as _HS
    _L = json.loads(read("data/ledger.json"))
    _C = {c["entry"]: c for c in _L["calls"]}
    _ph = [(c["entry"], p) for c in _L["calls"] for p in (c.get("retracted"), c.get("subclaim_judged_wrong")) if p]
    for _f in ["index.html", "en.html", "ja.html"]:
        _fb = next((b for b in jsonld_blocks(read(_f)) if '"FAQPage"' in b), None)
        if _fb is None:
            errors.append(f"{_f}: FAQPage block not found")
            continue
        _lang = _HS.LANG[_f]
        for _q in json.loads(_fb)["mainEntity"]:
            _t = _q["acceptedAnswer"]["text"]
            for _n, _p in _ph:
                if _p in _t and not re.search(r"#call-%d\b" % _n, _t):
                    errors.append(f"{_f}: FAQ 「{_q['name'][:30]}」 quotes 「{_p}」 (ENTRY {_n}, ledger) without the theses.html#call-{_n} pointer — run scripts/gen-ledger.py")
            if _q["name"] not in _HS.TRACK_Q:
                for _m in _HS.PTR_RE[_lang].finditer(_t):
                    _n = int(_m.group(1)); _w = _HS.status_words(_lang, _m.group(0))
                    if _n not in _C:
                        errors.append(f"{_f}: FAQ 「{_q['name'][:30]}」 points to call-{_n}, which is not on the ledger")
                    elif _w != {_C[_n]["status"]}:
                        errors.append(f"{_f}: FAQ 「{_q['name'][:30]}」 pointer to call-{_n} says {sorted(_w)}, ledger says {_C[_n]['status']} — run scripts/gen-ledger.py")
            if _f == "en.html" and "~2.1x" in _t and "3.7" not in _t:
                errors.append(f"en.html: FAQ 「{_q['name'][:30]}」 states ~2.1x without the ENTRY 114 ~3.7x correction — run scripts/gen-ledger.py")
    for _m in _HS.ROW_TITLE_RE.finditer(read("en.html")):
        if "~2.1x" in _m.group(2) and "3.7" not in _m.group(2):
            errors.append(f"en.html: entry row {_m.group(4) or '?'} states ~2.1x without the ENTRY 114 ~3.7x correction — run scripts/gen-ledger.py")
except Exception as _e:
    errors.append(f"FAQ ledger-pointer check crashed — {_e}")

# 10. Discovery files point only at pages that exist (2026-11-21)
BASE = "https://cynthia-git11.github.io/clawq-diary/"
def _url_file(u):
    r = u[len(BASE):].split("#")[0].split("?")[0]
    return r + "index.html" if r == "" or r.endswith("/") else r
try:
    _dead = []
    _maps = ["sitemap-index.xml"] + [u[len(BASE):] for u in re.findall(r"<loc>([^<]+)</loc>", read("sitemap-index.xml")) if u.startswith(BASE)]
    for _f in dict.fromkeys(_maps + ["sitemap.xml"]):
        if not os.path.exists(_f):
            _dead.append(f"sitemap-index.xml → {_f} (missing sitemap)")
            continue
        _s = read(_f)
        for _u in re.findall(r"<loc>([^<]+)</loc>", _s) + re.findall(r'<xhtml:link[^>]*href="([^"]+)"', _s):
            if _u.startswith(BASE) and not os.path.exists(_url_file(_u)):
                _dead.append(f"{_f} → {_u}")
    for _u in re.findall(r"\]\((" + re.escape(BASE) + r"[^)\s]*)\)", read("llms.txt")):
        if not os.path.exists(_url_file(_u)):
            _dead.append(f"llms.txt → {_u}")
    for _x in _dead[:10]:
        errors.append(f"dead URL — {_x}")
    if len(_dead) > 10:
        errors.append(f"... {len(_dead) - 10} more dead URLs")
except Exception as _e:
    errors.append(f"dead-URL check crashed — {_e}")

if errors:
    print("GEO health check FAILED:")
    for e in errors:
        print("  ✗", e)
    sys.exit(1)

print("GEO health check passed ✓  JSON-LD valid · XML well-formed · AI crawlers present · latest entry synced · counts consistent · atom order/dedupe ok · ledger invariants ok · Q&A/topic pages ok · FAQ ledger pointers ok · no dead sitemap / llms.txt URLs")
