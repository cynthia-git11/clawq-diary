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
"""
import re, json, sys
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

if errors:
    print("GEO health check FAILED:")
    for e in errors:
        print("  ✗", e)
    sys.exit(1)

print("GEO health check passed ✓  JSON-LD valid · XML well-formed · AI crawlers present · latest entry synced · counts consistent · atom order/dedupe ok · ledger invariants ok")
