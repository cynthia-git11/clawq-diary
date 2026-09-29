#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tracker coverage check: every content page must load assets/js/tracker.js?v=4 exactly once.

Scans every *.html under the repo (excluding .git/, integrations/, 404.html, analytics.html) and asserts:
  1. exactly one <script src="...assets/js/tracker.js?v=4"> tag
  2. the relative src resolves (from the page's own directory) to an existing file
  3. no stale reference to another tracker.js version
Prints a per-directory summary; exits non-zero and lists the offending files when anything is missing.
Usage: python3 scripts/check-tracker-coverage.py [--root DIR]
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = os.path.abspath(sys.argv[sys.argv.index("--root") + 1])
WANT = "assets/js/tracker.js?v=4"
SKIP_DIRS = {".git", "integrations", "node_modules"}
SKIP_FILES = {"404.html", "analytics.html"}
TAG = re.compile(r'<script\b[^>]*\bsrc="([^"]*assets/js/tracker\.js[^"]*)"[^>]*>', re.I)

pages = []
for dp, dns, fns in os.walk(ROOT):
    dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
    rel_dir = os.path.relpath(dp, ROOT)
    for fn in sorted(fns):
        if not fn.endswith(".html"): continue
        rel = fn if rel_dir == "." else os.path.join(rel_dir, fn)
        if rel in SKIP_FILES: continue
        pages.append(rel)

problems = []; per_dir = {}
for rel in pages:
    d = os.path.dirname(rel) or "."
    per_dir.setdefault(d, [0, 0]); per_dir[d][0] += 1
    src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    refs = TAG.findall(src)
    good = [r for r in refs if r.endswith(WANT)]
    stale = [r for r in refs if not r.endswith(WANT)]
    if len(good) != 1:
        problems.append(f"{rel}: {len(good)} reference(s) to {WANT} (need exactly 1)")
    if stale:
        problems.append(f"{rel}: stale tracker reference(s) {stale}")
    for r in good:
        target = os.path.normpath(os.path.join(ROOT, os.path.dirname(rel), r.split("?")[0]))
        if not os.path.isfile(target):
            problems.append(f"{rel}: src {r} -> {os.path.relpath(target, ROOT)} does not exist")
        elif os.path.relpath(target, ROOT) != "assets/js/tracker.js":
            problems.append(f"{rel}: src {r} resolves to {os.path.relpath(target, ROOT)}, not assets/js/tracker.js")
    if len(good) == 1 and not stale and not any(p.startswith(rel + ":") for p in problems):
        per_dir[d][1] += 1

for d in sorted(per_dir):
    n, ok = per_dir[d]
    print(f"{d:12s} {ok}/{n} pages OK")
print(f"total        {sum(v[1] for v in per_dir.values())}/{len(pages)} pages OK")
if problems:
    print(f"\nTRACKER COVERAGE FAILED ({len(problems)}):")
    for p in problems: print("  ✗", p)
    sys.exit(1)
print("tracker coverage OK ✓")
