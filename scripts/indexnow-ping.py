#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IndexNow push for .github/workflows/geo-hourly.yml: every public page changed since the last successful push, plus the
fixed carriers, in batches of 500 URLs (the API takes up to 10,000 per request, so nothing is capped or dropped).

Base commit — the first that applies:
  1. --last-file holds the commit of the last successful push (the workflow keeps it in the actions cache) and it is an
     ancestor of HEAD; equal to HEAD means nothing new, so no push;
  2. --before, the push event's previous head (github.event.before), is an ancestor of HEAD;
  3. otherwise every commit of the last --window-hours hours (default 26: scheduled runs can be hours apart).
Pages: *.html except 404.html / analytics.html / integrations/, llms.txt, llms-full.txt, the top-level *.xml, ledger.csv,
        data/ledger.json; X/index.html is pushed as X/; files deleted by HEAD are left out. When nothing public changed
        (only analytics.html, TRAFFIC-REPORT.md, scripts …) there is no push. The fixed carriers (hub pages, theses.html,
        theses-en.html, llms.txt, ledger.csv, the sitemaps) go with every push.
--all : every <loc> of every sitemap listed in sitemap-index.xml, plus the fixed carriers (one-off full resubmission).
Result: when every batch answers HTTP 200 / 202, or when there was nothing to push, HEAD is written to --last-file and
        "advance=true" to $GITHUB_OUTPUT (the workflow then saves the cache); a failed batch changes neither, so the next run
        retries from the same base. Never fails the job (exit 0) unless the arguments are wrong. --dry posts nothing,
        writes nothing and prints the URL list.
Usage : python3 scripts/indexnow-ping.py [--last-file F] [--before SHA] [--window-hours H] [--all] [--dry]
"""
import os, re, sys, json, subprocess, urllib.request, urllib.error, urllib.parse

KEY = "d9cbec26916a25296455ffb28243f03f"; HOST = "cynthia-git11.github.io"; BASE = f"https://{HOST}/clawq-diary/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BATCH = 500
def arg(name, default=None): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
LAST_FILE = arg("--last-file"); BEFORE = (arg("--before") or "").strip(); HOURS = int(arg("--window-hours", "26"))
DRY = "--dry" in sys.argv; ALL = "--all" in sys.argv

def git(*a):
    r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout
def is_ancestor(sha):
    return (bool(re.fullmatch(r"[0-9a-f]{7,40}", sha or "")) and set(sha) != {"0"}
            and git("cat-file", "-e", sha + "^{commit}")[0] == 0 and git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0)
def lines(out): return [x for x in out.split("\n") if x.strip()]
def file_of(p): return os.path.join(ROOT, p + "index.html" if p == "" or p.endswith("/") else p)
def page(f):
    """repo path → URL path under BASE, or None when the file is not a public page"""
    if f.startswith(("integrations/", "assets/", "scripts/", ".github/", "archive/")): return None
    if f.endswith(".html"):
        if f in ("404.html", "analytics.html"): return None
        return f[:-len("index.html")] if f == "index.html" or f.endswith("/index.html") else f
    if f in ("llms.txt", "llms-full.txt", "ledger.csv", "data/ledger.json") or ("/" not in f and f.endswith(".xml")): return f
    return None

HEAD = git("rev-parse", "HEAD")[1].strip()
FIXED = ["", "en.html", "ja.html", "theses.html", "theses-en.html", "ledger.csv", "atom.xml", "llms.txt", "llms-full.txt",
         "sitemap-index.xml", "sitemap.xml", "sitemap-entries.xml", "sitemap-entries-en.xml", "sitemap-topics.xml",
         "sitemap-answers.xml", "entries/", "entries/en/", "topics/", "answers/", "answers/en/"]
FIXED = [p for p in FIXED if os.path.exists(file_of(p))]
last = open(LAST_FILE, encoding="utf-8").read().strip() if LAST_FILE and os.path.exists(LAST_FILE) else ""
DIFF = ("--name-only", "--no-renames", "--diff-filter=d")

paths = []
if ALL:
    how = "--all: every sitemap in sitemap-index.xml"
    idx = open(os.path.join(ROOT, "sitemap-index.xml"), encoding="utf-8").read()
    for sm in re.findall(r"<loc>([^<]+)</loc>", idx):
        if not sm.startswith(BASE): continue
        f = os.path.join(ROOT, sm[len(BASE):])
        if os.path.exists(f): paths += [u[len(BASE):] for u in re.findall(r"<loc>([^<]+)</loc>", open(f, encoding="utf-8").read()) if u.startswith(BASE)]
    changed = None
elif last and last == HEAD:
    print(f"IndexNow: nothing new since the last push ({HEAD[:7]}) — skip.")
    sys.exit(0)
elif is_ancestor(last):
    how = f"since the last successful push {last[:7]}"; changed = lines(git("diff", *DIFF, last, "HEAD")[1])
elif is_ancestor(BEFORE):
    how = f"since the push event's previous head {BEFORE[:7]}" + (f" (last-push record {last[:7]} not an ancestor of HEAD)" if last else " (no last-push record)")
    changed = lines(git("diff", *DIFF, BEFORE, "HEAD")[1])
else:
    how = f"in the last {HOURS} hours" + (f" (last-push record {last[:7]} not an ancestor of HEAD)" if last else " (no last-push record)")
    changed = lines(git("log", f"--since={HOURS} hours ago", "--pretty=format:", *DIFF)[1])
if changed is not None:
    for f in sorted(set(changed)):
        p = page(f)
        if p is not None and os.path.exists(file_of(p)): paths.append(p)

def advance():
    if DRY: return
    if LAST_FILE:
        os.makedirs(os.path.dirname(os.path.abspath(LAST_FILE)), exist_ok=True)
        open(LAST_FILE, "w", encoding="utf-8").write(HEAD + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh: fh.write("advance=true\n")

print(f"IndexNow: base {how} · {len(changed) if changed is not None else '-'} changed files · {len(paths)} public pages")
if not paths:
    print("IndexNow: no public page changed — skip (record moves to HEAD)."); advance(); sys.exit(0)
urls = list(dict.fromkeys(BASE + urllib.parse.quote(p) for p in FIXED + paths))
if DRY:
    print("\n".join(urls)); print(f"DRY RUN · would push {len(urls)} urls in {(len(urls) + BATCH - 1) // BATCH} batch(es)"); sys.exit(0)
ok = 0
for i in range(0, len(urls), BATCH):
    batch = urls[i:i + BATCH]
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"{BASE}{KEY}.txt", "urlList": batch}).encode()
    req = urllib.request.Request("https://api.indexnow.org/IndexNow", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  batch {i // BATCH + 1}: HTTP {r.status} · {len(batch)} urls")
            if r.status in (200, 202): ok += len(batch)
    except urllib.error.HTTPError as e: print(f"  batch {i // BATCH + 1}: HTTP {e.code} {e.read()[:200]!r}")
    except Exception as e: print(f"  batch {i // BATCH + 1}: failed — {e}")
print(f"IndexNow pinged {ok}/{len(urls)} urls.")
if ok == len(urls): advance()
else: print("IndexNow: not every batch accepted — the last-push record stays, the next run retries from the same base (non-fatal).")
