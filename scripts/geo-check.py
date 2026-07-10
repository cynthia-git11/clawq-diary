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
for f in ["index.html", "en.html", "ja.html"]:
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

if errors:
    print("GEO health check FAILED:")
    for e in errors:
        print("  ✗", e)
    sys.exit(1)

print("GEO health check passed ✓  JSON-LD valid · XML well-formed · AI crawlers present · latest entry synced · counts consistent")
