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
     to a ja one without checking that the page exists. Names are compared exactly (git ls-files: tracked + untracked, not
     ignored; os.walk when not in a git checkout), because macOS ignores case and Pages does not: topics/MiniMax.html
     passes os.path.exists on a Mac and is a 404 online.
 11. Machine timestamps (2026-11-22, author-approved; scripts/machine_dates.py, applied by gen-entry-pages.py, which buildN.py
     runs after every entry): a backfill's (补记) datePublished is its written date (scripts/entry_dates.py, the rule behind
     data/ledger.json written_date) on entries/<N>.html, entries/en/<N>.html, in the index.html top-5 @graph and as its atom
     <published>; dateModified / <updated> is never earlier than datePublished / <published>; a page's article:published_time /
     modified_time equal its JSON-LD; an entry in the top-5 @graph has the same datePublished there as on its pages (the time of
     day no longer moves when it leaves the top 5); the feed <updated> is not earlier than any entry <updated>.
 12. Agent wording (2026-11-23, the author: 「所有用AI智能体替代…，不再出现…」): no served file outside archive/ contains the retired
     nickname — the Chinese word, its emoji, the English word in any case, the Japanese words, or their percent-encoded forms in
     share URLs (scripts/agent_terms.py hits(); the tokens are spelled there only as escapes, since scripts/ is served too).
     Served = what the dead-URL check lists (tracked + untracked-not-ignored), minus archive/ and every path with a part starting
     with "." or "_" (Jekyll does not publish those), text files only. buildN.py, make_daily.py and i18n_daily.py run
     agent_terms.fix() on what they insert, so a draft that still uses the old word is rewritten before it reaches a page.
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
def _site_files():
    """exact (case-sensitive) relative paths that GitHub Pages will serve: tracked plus untracked-not-ignored files (the
    publish scripts run this check before `git add -A`, so a new entries/<N>.html is still untracked here). os.path.exists
    ignores case on macOS, where the publish scripts run this check, while Pages and the ubuntu CI do not."""
    import subprocess
    try:
        _r = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], capture_output=True, timeout=60)
        _s = {p for p in _r.stdout.decode("utf-8").split("\0") if p} if _r.returncode == 0 else set()
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        _s = set()
    if _s:
        return _s
    _s = set()      # not a git checkout (e.g. a plain copy for a rehearsal): every file on disk, exact names
    for _d, _sub, _fs in os.walk("."):
        _sub[:] = [x for x in _sub if x != ".git"]
        _s.update(os.path.relpath(os.path.join(_d, x), ".").replace(os.sep, "/") for x in _fs)
    return _s
def _served(u, files):
    p = _url_file(u)
    return p in files and os.path.isfile(p)     # a tracked file deleted from the work tree is gone after `git add -A`
try:
    _dead = []
    _files = _site_files()
    _maps = ["sitemap-index.xml"] + [u[len(BASE):] for u in re.findall(r"<loc>([^<]+)</loc>", read("sitemap-index.xml")) if u.startswith(BASE)]
    for _f in dict.fromkeys(_maps + ["sitemap.xml"]):
        if _f not in _files or not os.path.isfile(_f):
            _dead.append(f"sitemap-index.xml → {_f} (missing sitemap)")
            continue
        _s = read(_f)
        for _u in re.findall(r"<loc>([^<]+)</loc>", _s) + re.findall(r'<xhtml:link[^>]*href="([^"]+)"', _s):
            if _u.startswith(BASE) and not _served(_u, _files):
                _dead.append(f"{_f} → {_u}")
    for _u in re.findall(r"\]\((" + re.escape(BASE) + r"[^)\s]*)\)", read("llms.txt")):
        if not _served(_u, _files):
            _dead.append(f"llms.txt → {_u}")
    for _x in _dead[:10]:
        errors.append(f"dead URL — {_x}")
    if len(_dead) > 10:
        errors.append(f"... {len(_dead) - 10} more dead URLs")
except Exception as _e:
    errors.append(f"dead-URL check crashed — {_e}")

# 11. Machine timestamps (2026-11-22): see the header
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import machine_dates as _MD
    _idx = read("index.html")
    _D = _MD.index_dates(_idx)
    _bad = []
    def _ge(a, b):
        """a is not earlier than b (ISO dates / timestamps, the comparison machine_dates.later uses)"""
        return _MD.later(a, b) == a
    def _pub_ok(where, n, pub, field="datePublished"):
        w = _D.get(n, ("", ""))[1]
        if w and pub[:10] != w:
            _bad.append(f"{where}: ENTRY {n} is a backfill written {w} but {field} is {pub}")
    _page_pub = {}
    for _f in sorted(glob.glob("entries/[0-9]*.html") + glob.glob("entries/en/[0-9]*.html")):
        if not re.fullmatch(r"\d+\.html", os.path.basename(_f)):
            continue
        _n = int(os.path.basename(_f)[:-5])
        _t = read(_f)
        _bp = None
        for _b in jsonld_blocks(_t):
            try:
                _j = json.loads(_b)
            except Exception:
                continue
            for _o in (_j.get("@graph", [_j]) if isinstance(_j, dict) else []):
                if isinstance(_o, dict) and _o.get("@type") == "BlogPosting":
                    _bp = _o
        if not _bp or not _bp.get("datePublished"):
            _bad.append(f"{_f}: no BlogPosting datePublished")
            continue
        _p, _m = _bp["datePublished"], _bp.get("dateModified") or _bp["datePublished"]
        _page_pub.setdefault(_n, set()).add(_p)
        _pub_ok(_f, _n, _p)
        if not _ge(_m, _p):
            _bad.append(f"{_f}: dateModified {_m} is earlier than datePublished {_p}")
        for _k, _v in (("published_time", _p), ("modified_time", _m)):
            _mm = re.search(r'<meta property="article:' + _k + r'" content="([^"]+)"', _t)
            if _mm and _mm.group(1) != _v:
                _bad.append(f"{_f}: article:{_k} {_mm.group(1)} ≠ JSON-LD {_v}")
    _gb = _MD._graph_block(_idx)
    for _g in (_MD.GRAPH_RE.finditer(_idx, _gb[0], _gb[1]) if _gb else []):
        _n, _p, _m = int(_g.group(2)), _g.group(3), _g.group(5)
        _pub_ok("index.html @graph", _n, _p)
        if not _ge(_m, _p):
            _bad.append(f"index.html @graph: ENTRY {_n} dateModified {_m} is earlier than datePublished {_p}")
        if _page_pub.get(_n, {_p}) != {_p}:
            _bad.append(f"index.html @graph: ENTRY {_n} datePublished {_p} ≠ its pages' {sorted(_page_pub[_n])}")
    _at = read("atom.xml")
    _ups = []
    for _e in re.findall(r"<entry>.*?</entry>", _at, re.S):
        _tm = re.search(r"<title>ENTRY (\d+) ", _e)
        _pm = re.search(r"<published>([^<]+)</published>", _e)
        _um = re.search(r"<updated>([^<]+)</updated>", _e)
        if _um:
            _ups.append(_um.group(1))
        if not (_tm and _pm and _um):
            continue
        _n = int(_tm.group(1))
        if {int(x) for g in _MD.ATOM_NUM_RE.findall(_e) for x in g if x} - {_n}:
            continue    # id / link name another entry (130/132 → 131/133, a known slip): machine_dates.fix_atom skips it too
        _pub_ok("atom.xml", _n, _pm.group(1), "<published>")
        if not _ge(_um.group(1), _pm.group(1)):
            _bad.append(f"atom.xml: ENTRY {_n} <updated> {_um.group(1)} is earlier than <published> {_pm.group(1)}")
    _fu = re.search(r"<updated>([^<]+)</updated>", _at.split("<entry>")[0])
    if _fu and _ups and not all(_ge(_fu.group(1), _u) for _u in _ups):
        _bad.append(f"atom.xml: feed <updated> {_fu.group(1)} is earlier than an entry's <updated>")
    for _x in _bad[:10]:
        errors.append(f"machine timestamps — {_x}")
    if len(_bad) > 10:
        errors.append(f"... {len(_bad) - 10} more machine-timestamp problems")
except Exception as _e:
    errors.append(f"machine-timestamp check crashed — {_e}")

# 12. Agent wording (2026-11-23): see the header
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import agent_terms as _AT
    _ret = []
    for _f in sorted(_site_files()):
        if _f.startswith("archive/") or any(_p.startswith((".", "_")) for _p in _f.split("/")) or not os.path.isfile(_f):
            continue
        try:
            with open(_f, encoding="utf-8") as _fh:
                _t = _fh.read()
        except (UnicodeDecodeError, OSError):
            continue                                    # images and other binary files
        _h = _AT.hits(_t)
        if _h:
            _ret.append(f"{_f}: {len(_h)}×")
    for _x in _ret[:10]:
        errors.append(f"retired agent wording — {_x} (scripts/agent_terms.py fix() rewrites it)")
    if len(_ret) > 10:
        errors.append(f"... {len(_ret) - 10} more files with retired agent wording")
except Exception as _e:
    errors.append(f"agent-wording check crashed — {_e}")

if errors:
    print("GEO health check FAILED:")
    for e in errors:
        print("  ✗", e)
    sys.exit(1)

print("GEO health check passed ✓  JSON-LD valid · XML well-formed · AI crawlers present · latest entry synced · counts consistent · atom order/dedupe ok · ledger invariants ok · Q&A/topic pages ok · FAQ ledger pointers ok · no dead sitemap / llms.txt URLs · machine timestamps ok · agent wording ok")
