#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: the judgment ledger as data. theses.html cards stay the source of truth (buildN.py and the reconciliation
scripts write them); this script only READS the cards and derives everything else from them, deterministically.

Reads : theses.html (cards: date, Day, claim, badge class, ev text), index.html (entry title / date, 「本篇写于 YYYY-MM-DD」
        and 「（M/D 补记）」 backfill markers, correction-entry dates), data/entries-en-map.json + entries/en/<N>.html
        (English h1, never machine-translated), data/ledger-overrides.json (hand-filled correction entries),
        data/ledger-commits.json (first public commit per call, verified and frozen; new calls are looked up with
        `git log --reverse -S '<title>' -- index.html` and accepted only if that commit has id="entry-N" with the same title
        and is already on origin/main, so a commit later rewritten by `git pull --rebase` is never frozen)
Writes: data/ledger.json, ledger.csv (UTF-8 BOM), theses-en.html, data/ledger-commits.json (new calls only), and patches
        theses.html (id="call-N", computed tiles, first-commit links, backfill marks, Dataset + Claim JSON-LD, hreflang),
        llms.txt (ledger counts, exact buildN format; the ledger files in its own <!-- gen:ledger --> block; the calls due in the
        next 90 days in <!-- gen:due -->, dated --today), index.html / en.html / ja.html (track-record FAQ answers, en ledger link),
        sitemap.xml (plain <url> for theses-en.html, no xhtml:link so hygiene0928.add_ja leaves it alone); through
        scripts/hub_sync.py also the Day / entry-count spans buildN.py does not bump (en hero 「DAY N」, en 「Public entries
        written」, dated FAQ counts, theses lede, press.html / press-en.html) and the dated pointers to the ledger card on
        FAQ answers that restate a call now ✗ / ◐ (data/ledger-overrides.json "faq_calls" settles ambiguous lead dates;
        pointers already present follow their call's status, ✓ and ⏳ included), plus the ENTRY 114 number note on the
        en.html ENTRY 112 row.
Status comes ONLY from the badge class (b-ok / b-bad / b-part / b-open); nothing is inferred from prose. Dates are machine-read
        only from fixed wordings on the card (「DATE 终审」「终审 DATE」「续看至 DATE」「期限 DATE」「维持 ⏳ 至 DATE」, 「（DATE 对账：」
        「DATE 对账（ENTRY N）：」, 「（DATE 读数：」); a card without them is labelled "not machine-read", never "no date".
        Retracted wording = a 「…」 quote directly followed by a retraction verb in the latest reconciliation note.
Date-dependent: overdue / next_resolution, the Upcoming list on theses-en.html and the llms.txt 即将裁定 block depend on --today (default: today, Beijing),
        so a rerun on a later day can change theses-en.html without any card change; same-day reruns change nothing.
Guards: exit 1 when a card cannot be parsed, counts disagree, a backfill marker on the card contradicts index.html,
        or the buildN invariants on theses.html would break; also when the total drops, a call_id disappears, or a
        resolved call goes back to open (re-run with --accept after checking). Normal status changes are only printed.
Backfill: written_date comes from index.html only — 「本篇写于 YYYY-MM-DD」, or the date line's 「（M/D 补记）」 (ENTRY 126/127)
        (scripts/entry_dates.py written_of, the rule scripts/machine_dates.py also uses to date a backfill's datePublished / atom entry);
        a backfill (written_date > event date) is shown as 补记 / Retrospective and counted separately from calls written before the outcome.
Root  : --root DIR, else $CLAWQ_ROOT, else the repo this script lives in. Pipeline slot: after gen-entries-en.py, before
        gen-entry-pages.py (needs the fresh data/entries-en-map.json; accepts both index.html#entry-N and entries/N.html card links).
        gen-entries-en.py runs this script itself at its end (skip with its --no-ledger); buildN.py runs gen-entries-en.py after it
        adds a card, and publish_daily.sh / publish_backfill.sh / ledger_apply.sh run it again, so all of them pick the ledger up
        without changes; running it again explicitly is harmless (idempotent). A guard stop makes gen-entries-en.py exit 1.
Usage : python3 scripts/gen-ledger.py [--root DIR] [--dry] [--accept] [--no-git] [--today YYYY-MM-DD]
"""
import re, os, sys, json, html, csv, io, subprocess, datetime

BASE = "https://cynthia-git11.github.io/clawq-diary/"
GH = "https://github.com/cynthia-git11/clawq-diary/commit/"
ROOT = os.environ.get("CLAWQ_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = sys.argv[sys.argv.index("--root") + 1]
ROOT = os.path.abspath(ROOT)
DRY = "--dry" in sys.argv; ACCEPT = "--accept" in sys.argv; NO_GIT = "--no-git" in sys.argv
BJ = datetime.timezone(datetime.timedelta(hours=8))
TODAY = sys.argv[sys.argv.index("--today") + 1] if "--today" in sys.argv else datetime.datetime.now(BJ).strftime("%Y-%m-%d")
DISC_EN = "This diary does not constitute promotion of, or an offer to subscribe for, any fund product."
CLAUDE_EN = "This diary is written and verified with Claude; discount any judgment about Anthropic, favourable or not"   # same sentence as gen-answers.py

def rd(f): return open(os.path.join(ROOT, f), encoding="utf-8").read()
def strip(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()
def esc(s): return html.escape(s or "", quote=True)
def die(msg): print("gen-ledger FAILED: " + msg); sys.exit(1)
WARN = []
def warn(msg): WARN.append(msg)
def days(a, b): return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days
def block_at(s, start):
    i = start; depth = 0; tag = re.compile(r"<(/?)div\b[^>]*>", re.I)
    while True:
        m = tag.search(s, i)
        if not m: raise ValueError("unbalanced div")
        depth += -1 if m.group(1) else 1; i = m.end()
        if depth == 0: return i
def paren_at(s, i):
    """s[i] == '（': return the inner text up to the matching '）' (nested full-width parens allowed)."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "（": depth += 1
        elif s[j] == "）":
            depth -= 1
            if depth == 0: return s[i + 1:j]
    return s[i + 1:]
def cut(s, n): return s if len(s) <= n else s[:n - 1].rstrip("，、；：。 ") + "…"
# sentences that carry holdings / LP / disclosure wording are never copied into the JSON-LD excerpts
DISCL = re.compile(r"利益披露|天际|持有|持仓|头寸|LP|被投|股东")
def drop_notes(ev):
    """the card's own text: later dated notes 「（YYYY-MM-DD …）」 removed (they are quoted separately)."""
    out = []; i = 0
    while i < len(ev):
        if ev[i] == "（" and re.match(r"（\d{4}-\d{2}-\d{2}", ev[i:i + 12]):
            i += len(paren_at(ev, i)) + 2; continue
        out.append(ev[i]); i += 1
    return re.sub(r"\s+", " ", "".join(out)).strip()
def excerpt(ev, prefer=None, n=140):
    """consecutive sentences of the card's own text, starting at the first one matching `prefer` (else the first one),
    stopping before any disclosure sentence; cut to n characters."""
    ss = [x.strip() for x in re.split(r"(?<=[。！？])", drop_notes(ev)) if x.strip()]
    ok = [i for i, x in enumerate(ss) if not DISCL.search(x)]
    if not ok: return ""
    start = next((i for i in ok if prefer and re.search(prefer, ss[i])), ok[0])
    out = ""
    for x in ss[start:]:
        if DISCL.search(x) or len(out) >= n: break
        out += x
    out = cut(out, n).rstrip("。")
    return out.rstrip("、，；：") + "…" if out[-1:] in ("、", "，", "；", "：") else out
RB_RE = re.compile(r"(\d{4}-\d{2}-\d{2}) ?(?:前后)?终[审裁]|终[审裁] ?(\d{4}-\d{2}-\d{2})|续看至 ?(\d{4}-\d{2}-\d{2})|期限 ?(\d{4}-\d{2}-\d{2})|维持 ⏳ 至 ?(\d{4}-\d{2}-\d{2})")
REC_RE = re.compile(r"（(\d{4}-\d{2}-\d{2}) 补?对账：|(?<!（)(\d{4}-\d{2}-\d{2}) 对账（ENTRY \d+）：")
READ_RE = re.compile(r"（(\d{4}-\d{2}-\d{2}) 读数[：，]")
RETR_RE = re.compile(r"「([^「」]{2,40})」(?:撤回|不准|是过度外推|判错|不再成立|按预注册证伪|记为自我加压|收回)")
COI_RE = re.compile(r"利益披露|天际持有|天际不持有|天际持仓|天际已全部退出|天际已退出")

# ---------------- index.html: entries ----------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True   # no scripts/__pycache__ in the repo
import entry_dates as ED
idx = rd("index.html")
E = {}
for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>', idx):
    n = int(m.group(1)); blk = idx[m.start():block_at(idx, m.start())]
    raw = (re.search(r'<h3 class="entry-title">(.*?)</h3>', blk, re.S) or [None, ""])[1]
    dtxt = strip((re.search(r'<div class="entry-date">(.*?)</div>', blk, re.S) or [None, ""])[1])
    dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", dtxt)
    date_d = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}" if dm else ""
    # written date: 「本篇写于 YYYY-MM-DD」 anywhere in the entry, or the date line's 「（M/D 补记）」 (ENTRY 126/127 style);
    # scripts/entry_dates.py written_of, the same rule the machine timestamps use (scripts/machine_dates.py)
    try: written = ED.written_of(blk, dtxt, date_d)
    except ValueError as e: die(f"ENTRY {n}: {e}")
    E[n] = dict(raw=raw.strip(), title=strip(raw), date=date_d, written=written)
import hub_sync as HS
import llms_sections as LS
try: SITE = HS.site_state(idx)
except ValueError as e: die(str(e))
DATES = HS.entry_dates(idx)

# ---------------- theses.html: cards ----------------
th = rd("theses.html")
CARD_RE = re.compile(r'<div class="call"[^>]*>(.*?)</div>\s*</div>\s*</div>', re.S)
STATUS = {"b-ok": "verified", "b-bad": "corrected", "b-part": "partly", "b-open": "open"}
ZH = {"verified": "✓ 已验证", "corrected": "✗ 已公开修正", "partly": "◐ 部分成立", "open": "⏳ 进行中"}
EN = {"verified": "Verified", "corrected": "Publicly corrected", "partly": "Partly right", "open": "Open"}
BADGE = {v: k for k, v in STATUS.items()}
themes = [(m.start(), m.group(1), m.group(2)) for m in re.finditer(r'<h2 class="theme">(.*?)<span class="en">(.*?)</span></h2>', th)]
over = json.load(open(os.path.join(ROOT, "data/ledger-overrides.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "data/ledger-overrides.json")) else {}
CORR = {int(k): v for k, v in over.get("correction_entry", {}).items()}
en_map = json.load(open(os.path.join(ROOT, "data/entries-en-map.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "data/entries-en-map.json")) else {}
calls = []
for m in CARD_RE.finditer(th):
    c = m.group(1)
    nm = re.search(r'<div class="claim"><a href="(?:index\.html#entry-|entries/)(\d+)(?:\.html)?"', c)
    if not nm: die(f"card at offset {m.start()} has no entry link")
    n = int(nm.group(1))
    wm = re.search(r'<div class="when"><b>(\d{4}-\d{2}-\d{2})</b>\s*Day (\d+)', c)
    if not wm: die(f"card {n}: no date / Day in .when")
    cm = re.search(r'<div class="claim"><a[^>]*>(.*?)</a>', c, re.S)
    bm = re.findall(r'<span class="badge (b-ok|b-bad|b-part|b-open)">', c)
    if len(bm) != 1: die(f"card {n}: {len(bm)} badges")
    evm = re.search(r'<div class="ev">(.*)$', c, re.S)
    if not (cm and evm): die(f"card {n}: claim or ev missing")
    ev = strip(evm.group(1)); claim_zh = strip(cm.group(1)); status = STATUS[bm[0]]
    th_zh = th_en = ""
    for pos, a, b in themes:
        if pos < m.start(): th_zh, th_en = strip(a), strip(b)
    if not th_zh: warn(f"card {n}: no theme heading above it")
    event = wm.group(1)
    if n not in E: die(f"card {n}: ENTRY {n} not in index.html")
    if E[n]["date"] and E[n]["date"] != event: warn(f"card {n}: card date {event} ≠ entry date {E[n]['date']}")
    # backfill: index.html decides; explicit markers on the card itself must agree
    written = E[n]["written"] or event
    cw = set(re.findall(r"本篇写于 (\d{4}-\d{2}-\d{2})|本篇为 (\d{4}-\d{2}-\d{2}) 补记", ev)); cw = {x for p in cw for x in p if x}
    cw |= set(re.findall(r"(\d{4}-\d{2}-\d{2}) ?补记）", claim_zh))
    if len(cw) > 1 or (cw and cw != {written}): die(f"card {n}: card says written {sorted(cw)}, index.html says {written}")
    if E[n]["written"] and not cw: warn(f"card {n}: index.html marks it written {written}, the card text has no 补记 marker")
    if written < event: warn(f"card {n}: written {written} earlier than event {event} — marker ignored, written = event"); written = event
    recs = list(REC_RE.finditer(ev))
    reconciled = (recs[-1].group(1) or recs[-1].group(2)) if recs else None
    if not recs: rtext = ""
    elif recs[-1].group(1):          # 「（DATE 对账：…）」
        rtext = re.sub(r"^\d{4}-\d{2}-\d{2} 补?对账：", "", paren_at(ev, recs[-1].start()))
    else:                            # 「DATE 对账（ENTRY N）：…。」 (ENTRY 89 style): up to the end of that sentence
        rest = ev[recs[-1].end():]; d = 0; j = len(rest)
        for k, ch in enumerate(rest):
            d += (ch == "（") - (ch == "）")
            if ch == "。" and d <= 0: j = k + 1; break
        rtext = rest[:j]
    rds = sorted(READ_RE.findall(ev)); last_reading = rds[-1] if rds else None
    rb = sorted({x for g in RB_RE.findall(ev) for x in g if x})
    resolve_by = rb[-1] if rb else None
    next_res = next((x for x in rb if x >= TODAY), None)
    rr = RETR_RE.findall(rtext) if rtext else []
    retracted = rr[0] if rr and status == "corrected" else None
    judged_wrong = rr[0] if rr and status != "corrected" else None
    ce = CORR.get(n)
    corrected_on = None
    if status == "corrected":
        if ce:
            if ce not in E or not E[ce]["date"]: die(f"card {n}: correction entry {ce} has no date in index.html")
            corrected_on = E[ce]["date"]
        elif reconciled: corrected_on = reconciled
        else: warn(f"card {n}: ✗ without correction entry or reconciliation date")
    url_en = claim_en = None
    if str(n) in en_map and os.path.exists(os.path.join(ROOT, en_map[str(n)])):
        h1 = re.search(r'<h1 class="ee-h1">(.*?)</h1>', rd(en_map[str(n)]), re.S)
        if h1: url_en, claim_en = BASE + en_map[str(n)], strip(h1.group(1))
    calls.append(dict(call_id=f"call-{n}", entry=n, theme_zh=th_zh, theme_en=th_en, event_date=event, day=int(wm.group(2)),
        written_date=written, backfill=written > event, status=status, reconciled=reconciled, reconcile_note=rtext or None,
        last_reading=last_reading, resolve_dates=rb, resolve_by=resolve_by, next_resolution=next_res,
        unresolvable=bool(re.search(r"对账：[^）]*裁定源缺失", ev)),
        overdue=bool(status == "open" and resolve_by and resolve_by < TODAY), correction_entry=ce, corrected_on=corrected_on,
        retracted=retracted, subclaim_judged_wrong=judged_wrong, falsifier="证伪口" in ev,
        acceptance_line=("证伪口" not in ev) and bool(re.search(r"验收|回滚", ev)), coi=bool(COI_RE.search(claim_zh + ev)),
        url_zh=f"{BASE}entries/{n}.html", url_en=url_en, claim_zh=claim_zh, claim_en=claim_en,
        _start=m.start(), _ev=ev))

n_div = len(re.findall(r'<div class="call"[^>]*>', th))
n_badge = sum(len(re.findall(r'<span class="badge %s">' % b, th)) for b in STATUS)
if not (n_div == len(calls) == n_badge): die(f'<div class="call"> {n_div} · parsed {len(calls)} · badges {n_badge} must be equal')
if len({c["entry"] for c in calls}) != len(calls): die("two cards point to the same ENTRY (call ids would collide)")
for k in list(CORR):
    if k not in {c["entry"] for c in calls}: warn(f"ledger-overrides: card {k} not on the ledger")

# ---------------- first public commit per call ----------------
CP = os.path.join(ROOT, "data/ledger-commits.json")
commits = json.load(open(CP, encoding="utf-8")) if os.path.exists(CP) else {}
commits_before = json.dumps(commits, ensure_ascii=False, sort_keys=True)
def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
have_git = False
if not NO_GIT:
    try: have_git = os.path.realpath(git("rev-parse", "--show-toplevel").stdout.strip() or "/nonexistent") == os.path.realpath(ROOT)
    except Exception: have_git = False
for c in calls:
    n = c["entry"]
    if str(n) in commits or not have_git: continue
    r = git("log", "--reverse", "--format=%H %cI", "-S", E[n]["raw"], "--", "index.html")
    first = next((l for l in r.stdout.splitlines() if l.strip()), None)
    if not first: continue                     # not committed yet: picked up on the next run
    h, at = first.split()
    old = git("show", f"{h}:index.html").stdout
    om = re.search(r'<div id="entry-%d"[^>]*>' % n, old)
    ot = re.search(r'<h3 class="entry-title">(.*?)</h3>', old[om.start():block_at(old, om.start())], re.S) if om else None
    ok = bool(ot) and ot.group(1).strip() == E[n]["raw"]
    if not ok: warn(f"card {n}: first commit {h[:7]} for its title has no id=\"entry-{n}\" with that title — left unlinked, check by hand"); continue
    if git("merge-base", "--is-ancestor", h, "origin/main").returncode != 0:
        print(f"  ENTRY {n}: first commit {h[:7]} not on origin/main yet — linked on a later run"); continue
    d = datetime.datetime.fromisoformat(re.sub(r"Z$", "+00:00", at)).astimezone(BJ).strftime("%Y-%m-%d")
    commits[str(n)] = {"commit": h, "at": at, "date": d, "via": "title"}
    print(f"  first commit for ENTRY {n}: {h[:7]} {d}")
for c in calls:
    k = commits.get(str(c["entry"]))
    c["first_commit"] = k["commit"] if k else None
    c["first_commit_date"] = k["date"] if k else None
    c["first_commit_url"] = GH + k["commit"] if k else None
    c["commit_lag_days"] = days(c["event_date"], k["date"]) if k else None

# ---------------- stats ----------------
S = {s: sum(1 for c in calls if c["status"] == s) for s in STATUS.values()}
fwd = [c for c in calls if not c["backfill"]]; bf = [c for c in calls if c["backfill"]]
res = lambda L: sum(1 for c in L if c["status"] != "open")
corr = [c for c in calls if c["status"] == "corrected" and c["corrected_on"]]
lags = sorted(days(c["written_date"], c["corrected_on"]) for c in corr)
updated = max([c["written_date"] for c in calls] + [c["reconciled"] for c in calls if c["reconciled"]] + [c["corrected_on"] for c in corr])
stats = dict(total=len(calls), verified=S["verified"], corrected=S["corrected"], partly=S["partly"], open=S["open"],
             resolved=len(calls) - S["open"], unresolvable=sum(c["unresolvable"] for c in calls),
             overdue=sum(c["overdue"] for c in calls), open_no_date_parsed=sum(1 for c in calls if c["status"] == "open" and not c["resolve_by"]),
             backfilled=len(bf), forward=len(fwd), resolved_forward=res(fwd), resolved_backfilled=res(bf),
             resolved_with_dated_note=sum(1 for c in calls if c["status"] != "open" and c["reconciled"]),
             resolved_by_correction_entry=sum(1 for c in calls if c["status"] == "corrected" and c["correction_entry"]),
             with_falsifier=sum(c["falsifier"] for c in calls), with_acceptance_line=sum(c["acceptance_line"] for c in calls),
             with_coi_disclosure=sum(c["coi"] for c in calls), english=sum(1 for c in calls if c["claim_en"]),
             first_commit_linked=sum(1 for c in calls if c["first_commit"]),
             correction_days_min=lags[0] if lags else None, correction_days_max=lags[-1] if lags else None)
T = stats["total"]
ev_dates = sorted(c["event_date"] for c in calls)
coverage = f"{ev_dates[0]}/{ev_dates[-1]}"

# ---------------- guards vs the previous ledger.json ----------------
LP = os.path.join(ROOT, "data/ledger.json")
prev = json.load(open(LP, encoding="utf-8")) if os.path.exists(LP) else None
if prev:
    pc = {c["call_id"]: c["status"] for c in prev["calls"]}; nc = {c["call_id"]: c["status"] for c in calls}
    block = []
    if prev["stats"]["total"] > T: block.append(f"total {prev['stats']['total']} → {T}")
    gone = sorted(set(pc) - set(nc), key=lambda x: int(x[5:]))
    if gone: block.append("call ids gone: " + ", ".join(gone))
    back = [k for k in nc if k in pc and pc[k] != "open" and nc[k] == "open"]
    if back: block.append("resolved → open: " + ", ".join(back))
    for k in sorted(nc, key=lambda x: int(x[5:])):
        if k in pc and pc[k] != nc[k]: print(f"  status {k}: {pc[k]} → {nc[k]}")
        if k not in pc: print(f"  new {k}: {nc[k]}")
    if block and not ACCEPT: die("; ".join(block) + " — check the cards, then re-run with --accept")

# ---------------- data/ledger.json + ledger.csv ----------------
PUB = ["call_id", "entry", "theme_zh", "theme_en", "event_date", "day", "written_date", "backfill", "status", "reconciled", "reconcile_note",
       "last_reading", "resolve_dates", "resolve_by", "next_resolution", "unresolvable", "overdue", "correction_entry", "corrected_on", "retracted",
       "subclaim_judged_wrong", "falsifier", "acceptance_line", "coi", "url_zh", "url_en", "claim_zh",
       "claim_en", "first_commit", "first_commit_date", "first_commit_url", "commit_lag_days"]
by_n = sorted(calls, key=lambda c: c["entry"])
ledger = {"name": "The ClawQ Judgment Ledger · 判断总账", "source": f"{BASE}theses.html", "updated": updated, "temporal_coverage": coverage,
          "generated_by": "scripts/gen-ledger.py (status = badge on the theses.html card; nothing inferred from prose)",
          "stats": stats, "calls": [{k: c[k] for k in PUB} for c in by_n]}
OUT = {}
OUT["data/ledger.json"] = json.dumps(ledger, ensure_ascii=False, indent=1) + "\n"
COLS = ["call_id", "entry", "theme_en", "event_date", "written_date", "backfill", "status", "reconciled", "resolve_by", "next_resolution",
        "correction_entry", "url_zh", "url_en", "claim_zh", "claim_en", "corrected_on", "unresolvable", "first_commit", "first_commit_date", "first_commit_url"]
buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n"); w.writerow(COLS)
for c in by_n: w.writerow(["" if c[k] is None else (str(c[k]).lower() if isinstance(c[k], bool) else c[k]) for k in COLS])
OUT["ledger.csv"] = "﻿" + buf.getvalue()
if json.dumps(commits, ensure_ascii=False, sort_keys=True) != commits_before:
    OUT["data/ledger-commits.json"] = json.dumps(dict(sorted(commits.items(), key=lambda kv: (not kv[0].isdigit(), int(kv[0]) if kv[0].isdigit() else 0))), ensure_ascii=False, indent=1) + "\n"

# ---------------- theses.html ----------------
def desc_zh(c):
    s = f"状态：{ZH[c['status']][2:]} {EN[c['status']]}"
    if c["corrected_on"]: s += f"；{c['corrected_on']} 公开修正" + (f"（ENTRY {c['correction_entry']}）" if c["correction_entry"] else "")
    if c["reconcile_note"]: s += f"；{c['reconciled']} 对账：{cut(c['reconcile_note'], 160).rstrip('。')}"
    else:   # the card's own "why": evidence for resolved calls; falsifier / acceptance / rollback line for open and partly ones
        ex = excerpt(c["_ev"]) if c["status"] in ("verified", "corrected") else excerpt(c["_ev"], r"证伪口|验收|回滚")
        lab = "依据" if c["status"] in ("verified", "corrected") else ("验收/证伪条件" if re.search(r"证伪口|验收|回滚", ex) else "卡片要点")
        if ex: s += f"；{lab}（卡片原文节选）：{ex}"
    if c["last_reading"] and (not c["reconciled"] or c["last_reading"] > c["reconciled"]): s += f"；最近读数 {c['last_reading']}（见卡片）"
    if c["unresolvable"]: s += "；裁定源缺失"
    if c["status"] in ("open", "partly") and c["resolve_dates"]: s += f"；卡片所列裁定日 {'、'.join(c['resolve_dates'])}"
    if c["backfill"]: s += f"；事后补记，写于 {c['written_date']}，事件日 {c['event_date']}，单独计数"
    return s.rstrip("。") + "。"
DATASET = {"@context": "https://schema.org", "@type": "Dataset", "@id": f"{BASE}theses.html#dataset",
    "name": "The ClawQ Judgment Ledger · 判断总账",
    "description": f"张倩 Cynthia Zhang（FutureX Capital 创始人）公开投资判断的可审计台账：{T} 个重大判断，每个带日期戳、验证状态（已验证/已公开修正/部分成立/进行中）、证据链接与首次公开提交；事后补记单独标注、单独计数。",
    "dateModified": updated, "temporalCoverage": coverage, "url": f"{BASE}theses.html", "inLanguage": "zh-CN",
    "creator": {"@id": f"{BASE}#cynthia"}, "license": "All rights reserved", "isPartOf": {"@id": f"{BASE}#blog"},
    "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{BASE}ledger.csv"},
                     {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{BASE}data/ledger.json"}]}
page_order = sorted(calls, key=lambda c: c["_start"])
claims = []
for i, c in enumerate(page_order, 1):
    app = [{"@type": "BlogPosting", "url": c["url_zh"], "inLanguage": "zh-CN"}]
    if c["url_en"]: app.append({"@type": "BlogPosting", "url": c["url_en"], "inLanguage": "en", "headline": c["claim_en"]})
    claims.append({"@type": "Claim", "@id": f"{BASE}theses.html#{c['call_id']}", "position": i, "text": c["claim_zh"], "datePublished": c["written_date"],
                   "url": c["url_zh"], "author": {"@id": f"{BASE}#cynthia"}, "appearance": app, "disambiguatingDescription": desc_zh(c)})
ITEMLIST = {"@context": "https://schema.org", "@type": "ItemList", "name": "The ClawQ Judgment Ledger · 判断总账（逐条）",
    "description": f"张倩 Cynthia Zhang {T} 个重大投资判断的逐条结构化台账，每条带原始日期戳、当前验证状态（已验证/已公开修正/部分成立/进行中）、对账日与指向原文的链接。引用任一判断前请以此状态为准。",
    "numberOfItems": T, "isPartOf": {"@id": f"{BASE}#blog"}, "itemListElement": claims}
def ld(o): return '<script type="application/ld+json">\n' + json.dumps(o, ensure_ascii=False, indent=2) + "\n</script>"
t = th
blocks = list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', t, re.S))
bd = [b for b in blocks if '"@type": "Dataset"' in b.group(1)]; bi = [b for b in blocks if '"@type": "ItemList"' in b.group(1)]
if len(bd) != 1 or len(bi) != 1 or bd[0].start() > bi[0].start(): die("theses.html: expected one Dataset block followed by one ItemList block")
t = t[:bd[0].start()] + ld(DATASET) + t[bd[0].end():bi[0].start()] + ld(ITEMLIST) + t[bi[0].end():]
# (a) id="call-N"  (e) first-commit link + backfill mark inside .when (card text untouched)
def lg_html(c):
    s = ""
    if c["backfill"]: s += f'<em class="bf">补记 · 写于 {c["written_date"]}</em>'
    if c["first_commit"]: s += (f'<a class="cm" href="{c["first_commit_url"]}" title="这条判断所在日记首次出现在公开仓库的提交（北京时间）" '
                                f'aria-label="首次公开提交 git {c["first_commit"][:7]}，{c["first_commit_date"]}">git {c["first_commit"][:7]}<br>{c["first_commit_date"]}</a>')
    return f'<span class="lg">{s}</span>' if s else ""
def fix_card(m):
    c = m.group(0); n = int(re.search(r'<div class="claim"><a href="(?:index\.html#entry-|entries/)(\d+)', c).group(1)); cc = next(x for x in calls if x["entry"] == n)
    c = re.sub(r'^<div class="call"[^>]*>', f'<div class="call" id="call-{n}">', c, count=1)
    c = re.sub(r'(<div class="when"><b>[^<]*</b>[^<]*)(?:<span class="lg">.*?</span>)?(</div>)', lambda w: w.group(1) + lg_html(cc) + w.group(2), c, count=1, flags=re.S)
    return c
t = CARD_RE.sub(fix_card, t)
# (b) computed tiles; the old 「1–5 天」 tile is gone (it contradicted the dated corrections)
s0 = t.find('<div class="score">')
if s0 < 0: die('theses.html: <div class="score"> not found')
note = (f'已裁定 {stats["resolved"]} / {T}（✓+✗+◐） · 事前写下的 {stats["forward"]} 条中已裁定 {stats["resolved_forward"]}；事后补记 {stats["backfilled"]} 条中已裁定 {stats["resolved_backfilled"]}（补记单独计数）'
        f' · 裁定源缺失 {stats["unresolvable"]} · 逾期未裁 {stats["overdue"]} · 进行中且未从卡片解析出终审日 {stats["open_no_date_parsed"]}（以卡片原文为准）'
        f' · 逐条数据 <a href="ledger.csv">ledger.csv</a> · <a href="data/ledger.json">ledger.json</a> · <a href="theses-en.html" hreflang="en">English</a>')
score = ('<div class="score">\n'
         f'    <div class="s ok"><div class="v">{S["verified"]}</div><div class="l">✓ 已验证 Verified</div></div>\n'
         f'    <div class="s bad"><div class="v">{S["corrected"]}</div><div class="l">✗ 已公开修正 Corrected</div></div>\n'
         f'    <div class="s part"><div class="v">{S["partly"]}</div><div class="l">◐ 部分成立 Partly right</div></div>\n'
         f'    <div class="s open"><div class="v">{S["open"]}</div><div class="l">⏳ 进行中 Open</div></div>\n'
         f'    <div class="s-note">{note}</div>\n  </div>')
t = t[:s0] + score + t[block_at(t, s0):]
# method paragraph: computed correction-lag sentence replaces 「两次 ✗ 的发现-认错用时……」
batch = sorted({c["corrected_on"] for c in corr if not c["correction_entry"]})
nb = sum(1 for c in corr if not c["correction_entry"])
lag = (f'目前 {S["corrected"]} 个 ✗：从判断发布到公开修正，最短 {stats["correction_days_min"]} 天、最长 {stats["correction_days_max"]} 天'
       + (f'；其中 {nb} 个是在 {"、".join(batch)} 的集中对账里认的错' if nb else "")
       + '（逐条日期见 <a href="ledger.csv">ledger.csv</a> 和<a href="theses-en.html#corrected" hreflang="en">英文台账</a>）。') if lags else ""
OLD_LAG = re.compile(r"两次 ✗ 的发现-认错用时分别是 <b>1 天</b>（5月11日→5月12日两篇）和 <b>5 天</b>（6月7日→6月9日两篇）——这个数字比 6 个 ✓ 更能说明判断系统的质量。|<span class=\"lg-stat\">.*?</span>", re.S)
if lag and OLD_LAG.search(t): t = OLD_LAG.sub(lambda _: f'<span class="lg-stat">{lag}</span>', t, count=1)
elif lag: warn("theses.html: method sentence anchor not found — correction-lag sentence not written")
# (d) nav English → theses-en.html; hreflang pair in <head>
t = t.replace('<a href="en.html">English</a>', '<a href="theses-en.html" hreflang="en">English</a>', 1)
HREF = (f'<link rel="alternate" hreflang="zh-CN" href="{BASE}theses.html" /><link rel="alternate" hreflang="en" href="{BASE}theses-en.html" />'
        f'<link rel="alternate" hreflang="x-default" href="{BASE}theses.html" />')
if 'hreflang="en" href="' + BASE + 'theses-en.html"' not in t:
    t = t.replace(f'<link rel="canonical" href="{BASE}theses.html" />', f'<link rel="canonical" href="{BASE}theses.html" />\n{HREF}', 1)
CSS_ADD = ("  /* gen-ledger */.s.part{background:rgba(196,137,23,.08)}.s.part .v{color:#9a6a00}"
           ".s-note{grid-column:1/-1;font-size:12px;color:var(--muted);line-height:1.8;text-align:center}.s-note a{border-bottom:1px dashed var(--border2)}"
           ".when .lg{display:block;margin-top:6px}.when .lg em{display:block;font-style:normal;font-weight:700;color:#7a5400}"
           ".when .lg a{display:block;margin-top:4px;color:var(--muted);font-size:11px;border-bottom:1px dashed var(--border2)}.method a{border-bottom:1px dashed var(--border2)}\n")
if "/* gen-ledger */" in t: t = re.sub(r"  /\* gen-ledger \*/[^\n]*\n", lambda _: CSS_ADD, t, count=1)
else: t = t.replace("</style>", CSS_ADD + "</style>", 1)
# lede 「这本日记写到 Day N、N 篇」 = index.html (buildN.py replaces exactly the previous Day / count once)
t, _, miss = HS.sync_counts("theses.html", t, SITE)
for x in miss: warn(f"theses.html: count anchor 「{x}」 not found — not changed")
# buildN invariants (e136-work/buildN.py lines 165–177) — must hold before anything is written
if t.count(f"{T} 个重大") != 3 or int(re.search(r"(\d+) 个重大", t).group(1)) != T: die(f"theses.html: '{T} 个重大' must occur exactly 3 times and come first")
if t.count('"numberOfItems"') != 1 or t.count(f'"numberOfItems": {T}') != 1: die("theses.html: numberOfItems must occur once and equal the card count")
dm = re.search(r'"dateModified": "(\d{4}-\d{2}-\d{2})"', t)
if not dm or t.count(f'"dateModified": "{dm.group(1)}"') != 1 or t.count('"dateModified"') != 1: die("theses.html: exactly one date-only dateModified (the Dataset's)")
if t.count('"@type": "Claim"') != T or len(re.findall(r'id="call-\d+"', t)) != T: die("theses.html: Claim / id=call-N count ≠ cards")
OUT["theses.html"] = t

# ---------------- theses-en.html ----------------
css = re.search(r"<style>(.*?)</style>", t, re.S).group(1)
css = css.replace("  h2.theme{", "  h2.theme,h3.theme{", 1).replace("  h2.theme .en{", "  h2.theme .en,h3.theme .en{", 1)   # themes under "Open" are h3 here
css += ("  .wrap h2.sec{font-size:18px;font-weight:800;margin:44px 0 6px;padding-bottom:10px;border-bottom:2px solid var(--bg4)}\n"
        "  .wrap h2.sec .en{font-weight:600;color:var(--muted2);font-size:12.5px;margin-left:8px}\n"
        "  ul.up{margin:10px 0 0 18px;font-size:13px;color:var(--muted);line-height:1.9}ul.up a{border-bottom:1px dashed var(--border2)}\n"
        "  .what .claim .lbl{font-weight:600;color:var(--muted2);font-size:12px;margin-right:6px}.what .ev a{border-bottom:1px dashed var(--border2)}\n")
def en_row(c):
    n = c["entry"]
    lab = (f'<span class="lbl">Source entry</span><a href="entries/en/{n}.html">{esc(c["claim_en"])}</a>' if c["claim_en"]
           else f'(Chinese only) <a href="entries/{n}.html" hreflang="zh-CN" lang="zh-CN">{esc(c["claim_zh"])}</a>')
    bits = [f'Called {c["written_date"]}']
    if c["backfill"]: bits = [f'Retrospective, written {c["written_date"]}; event {c["event_date"]}; not scored as a forward call']
    if c["status"] == "corrected" and c["corrected_on"]:
        k = c["correction_entry"]
        where = ((f' in <a href="entries/en/{k}.html">ENTRY {k}</a>' if str(k) in en_map else f' in <a href="entries/{k}.html" hreflang="zh-CN">ENTRY {k}</a> (Chinese)')
                 if k else " at the dated ledger reconciliation")
        d = days(c["written_date"], c["corrected_on"])
        bits.append(f'publicly corrected {c["corrected_on"]}{where}, {d} day{"s" if d != 1 else ""} after the call (call date to correction date)')
    elif c["reconciled"]: bits.append(f'last reconciled {c["reconciled"]}')
    if c["last_reading"] and (not c["reconciled"] or c["last_reading"] > c["reconciled"]): bits.append(f'last reading {c["last_reading"]}')
    if c["retracted"]: bits.append(f'retracted wording (Chinese original): <span lang="zh-CN">「{esc(c["retracted"])}」</span>')
    if c["subclaim_judged_wrong"]: bits.append(f'sub-claim judged wrong at reconciliation (Chinese original): <span lang="zh-CN">「{esc(c["subclaim_judged_wrong"])}」</span>')
    if c["status"] in ("open", "partly"):
        if c["unresolvable"]: bits.append("resolution source missing (marked at reconciliation; badge unchanged)")
        rd_ = c["resolve_dates"]
        if rd_: bits.append(f'final / review-until date{"s" if len(rd_) > 1 else ""} read from the card {", ".join(rd_)}' + (" · overdue" if c["overdue"] else ""))
        elif c["status"] == "open": bits.append("no final date machine-read from the card — see card")
    bits.append(f'<a href="theses.html#call-{n}" hreflang="zh-CN">Chinese ledger card</a> (status, evidence and falsifier)')
    if c["coi"]: bits.append(f'conflict-of-interest disclosure: see the <a href="theses.html#call-{n}" hreflang="zh-CN">Chinese card</a> and the source entry')
    lg = (f'<span class="lg"><a class="cm" href="{c["first_commit_url"]}" title="Commit in which this entry first appeared in the public repository (Beijing time)" '
          f'aria-label="First public commit git {c["first_commit"][:7]}, {c["first_commit_date"]}">git {c["first_commit"][:7]}<br>{c["first_commit_date"]}</a></span>') if c["first_commit"] else ""
    return (f'  <div class="call" id="call-{n}">\n    <div class="when"><b>{c["event_date"]}</b>ENTRY {n}{lg}</div>\n    <div class="what">\n'
            f'      <div class="claim">{lab}<span class="badge {BADGE[c["status"]]}">{ZH[c["status"]][:1]} {EN[c["status"]]}</span></div>\n'
            f'      <div class="ev">{" · ".join(bits)}</div>\n    </div>\n  </div>\n')
sec = lambda i, title, sub: f'  <h2 class="sec" id="{i}">{title}<span class="en">{sub}</span></h2>\n'
corr_rows = sorted([c for c in calls if c["status"] == "corrected"], key=lambda c: (c["corrected_on"] or "", c["entry"]), reverse=True)
body = sec("corrected", f"Publicly corrected ({S['corrected']})", "newest correction first · 已公开修正") + "".join(en_row(c) for c in corr_rows)
body += sec("partly", f"Partly right ({S['partly']})", "◐ 部分成立") + "".join(en_row(c) for c in page_order if c["status"] == "partly")
body += sec("verified", f"Verified ({S['verified']})", "✓ 已验证") + "".join(en_row(c) for c in page_order if c["status"] == "verified")
horizon = (datetime.date.fromisoformat(TODAY) + datetime.timedelta(days=180)).isoformat()
up = sorted([c for c in calls if c["status"] in ("open", "partly") and c["next_resolution"] and c["next_resolution"] <= horizon], key=lambda c: (c["next_resolution"], c["entry"]))
uli = "".join(f'    <li>{c["next_resolution"]} · <a href="#call-{c["entry"]}">ENTRY {c["entry"]}</a> · {esc(c["claim_en"]) if c["claim_en"] else "Chinese-only entry"}'
              + (f' (later date on the card: {c["resolve_by"]})' if c["resolve_by"] != c["next_resolution"] else "") + '</li>\n' for c in up) \
      or "    <li>No resolution date machine-read from the cards falls in the next 180 days.</li>\n"
body += sec("upcoming", f"Upcoming resolutions ({len(up)})", f"dates machine-read from the cards, {TODAY} to {horizon}") + f'  <ul class="up">\n{uli}  </ul>\n'
body += (f'  <p class="lede" style="font-size:13px">Only dates written in fixed forms on the card (final resolution, review-until, deadline) are read; '
         f'{stats["open_no_date_parsed"]} open calls have none in those forms, and some state test windows in their own wording — see each Chinese card.</p>\n')
body += sec("open", f"Open ({S['open']})", "⏳ 进行中 · by theme")
seen_th = []
for c in page_order:
    if c["status"] == "open" and c["theme_en"] not in seen_th: seen_th.append(c["theme_en"])
for te in seen_th:
    tz = next(c["theme_zh"] for c in page_order if c["theme_en"] == te)
    body += f'  <h3 class="theme">{esc(te)}<span class="en" lang="zh-CN">{esc(tz)}</span></h3>\n' + "".join(en_row(c) for c in page_order if c["status"] == "open" and c["theme_en"] == te)
en_note = (f'Resolved {stats["resolved"]} of {T} (✓+✗+◐) · of {stats["forward"]} calls written before the outcome, {stats["resolved_forward"]} resolved; '
           f'of {stats["backfilled"]} retrospective entries, {stats["resolved_backfilled"]} resolved (counted separately)'
           f' · resolution source missing {stats["unresolvable"]} · overdue {stats["overdue"]} · open with no final date machine-read from the card {stats["open_no_date_parsed"]}'
           ' · data <a href="ledger.csv">ledger.csv</a> · <a href="data/ledger.json">ledger.json</a>')
title_en = f"Cynthia Zhang's Public Judgment Ledger: {T} AI Investment Calls, Scored"
desc_en = (f"Every major call from Cynthia Zhang's public AI investment diary, date-stamped and scored from the badges on the Chinese ledger: "
           f"{S['verified']} verified, {S['corrected']} publicly corrected, {S['partly']} partly right, {S['open']} open; {stats['backfilled']} retrospective entries counted separately. CSV download and first-commit links.")
DS_EN = dict(DATASET)
ce_nonote = sum(1 for c in calls if c["status"] == "corrected" and c["correction_entry"] and not c["reconciled"])
EN_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{esc(title_en)}</title>
<meta name="description" content="{esc(desc_en)}" />
<link rel="canonical" href="{BASE}theses-en.html" />
<link rel="alternate" hreflang="en" href="{BASE}theses-en.html" /><link rel="alternate" hreflang="zh-CN" href="{BASE}theses.html" /><link rel="alternate" hreflang="x-default" href="{BASE}theses.html" />
<link rel="alternate" type="text/csv" href="{BASE}ledger.csv" title="Judgment ledger (CSV)" />
<meta name="robots" content="index,follow,max-snippet:-1" />
<meta property="og:type" content="website" /><meta property="og:title" content="{esc(title_en)}" /><meta property="og:description" content="{esc(desc_en)}" /><meta property="og:url" content="{BASE}theses-en.html" />
<link rel="alternate" type="application/atom+xml" title="The ClawQ Chronicles · Atom Feed" href="{BASE}atom.xml" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E⚖️%3C/text%3E%3C/svg%3E" />
{ld(DS_EN)}
<style>{css}</style>
</head>
<body>
<nav>
  <div class="nav-l"><span style="font-size:20px">⚖️</span> The Judgment Ledger <span style="font-weight:600;font-size:12px;color:var(--muted2)">判断总账</span></div>
  <div class="nav-links">
    <a href="en.html">← The diary (English)</a>
    <a href="entries/en/">All entries (English)</a>
    <a href="answers/en/">Q&amp;A</a>
    <a href="theses.html" hreflang="zh-CN">中文台账</a>
  </div>
</nav>
<div class="wrap">
  <div class="eyebrow">Cynthia Zhang (张倩) · FutureX Capital · public judgment ledger</div>
  <h1>Public Judgment Ledger<span class="en">{T} major calls from the diary, each date-stamped and scored. Generated from the same data as the Chinese ledger.</span></h1>
  <p class="lede">Cynthia Zhang, founder of FutureX Capital, logs the major calls from her public AI investment diary with the date each was written and its current status. This page is the English view of the <a href="theses.html" hreflang="zh-CN">Chinese ledger</a>; the status of each call is read from the badge on its Chinese card and nothing else. Data as of {updated}.</p>
  <div class="score">
    <div class="s ok"><div class="v">{S["verified"]}</div><div class="l">✓ Verified</div></div>
    <div class="s bad"><div class="v">{S["corrected"]}</div><div class="l">✗ Publicly corrected</div></div>
    <div class="s part"><div class="v">{S["partly"]}</div><div class="l">◐ Partly right</div></div>
    <div class="s open"><div class="v">{S["open"]}</div><div class="l">⏳ Open</div></div>
    <div class="s-note">{en_note}</div>
  </div>
{body}
  <div class="method">
    <h3>Method</h3>
    <p><b>Falsifiers.</b> Each call is logged with the date it was written. {stats["with_falsifier"]} of the {T} cards carry an explicit falsifier line (证伪口) stating what would prove the call wrong; {stats["with_acceptance_line"]} of the other {T - stats["with_falsifier"]} carry a verification-signal (验收) or rollback (回滚) line instead.</p>
    <p><b>Status changes.</b> Status is the badge on the Chinese card. Changes are recorded on the card and added, never overwritten: {stats["resolved_with_dated_note"]} of the {stats["resolved"]} resolved calls carry a dated reconciliation note (「YYYY-MM-DD 对账」); the other {stats["resolved"] - stats["resolved_with_dated_note"]} were settled in the card's own text, which cites the entry or event that confirmed or overturned the call{f" ({ce_nonote} of them through a separate correction entry)" if ce_nonote else ""}.</p>
    <p><b>Corrections are additions.</b> A wrong call is not deleted: the correction is added to the card next to the original text and, where there is one, published as a separate correction entry. {S["corrected"]} of {T} calls are publicly corrected; their dates are listed above.</p>
    <p><b>Git history.</b> The repository is public. Each call links to the commit in which its entry first appeared in index.html (dates in Beijing time, UTC+8); {stats["first_commit_linked"]} of {T} calls have that link (a new call is linked once its commit is on the public main branch). The wording at that commit may differ from today's page, and every later edit is in the same history.</p>
    <p><b>Retrospective entries are counted separately.</b> {stats["backfilled"]} entries were written after the event they discuss and are marked Retrospective with both dates. Of the {stats["resolved"]} resolved calls, {stats["resolved_forward"]} were written before the outcome and {stats["resolved_backfilled"]} are retrospective.</p>
    <p><b>English text.</b> The English line on each call is the title of the English edition of its source entry, not a translation of the Chinese ledger claim. {T - stats["english"]} calls have no English edition and are shown in Chinese.</p>
    <p><b>Download.</b> <a href="ledger.csv">ledger.csv</a> (UTF-8, one row per call) · <a href="data/ledger.json">data/ledger.json</a></p>
  </div>
  <div class="compliance">{CLAUDE_EN}. Where a Chinese card carries a conflict-of-interest disclosure, its row here points to it; read those calls with that disclosure in mind. {DISC_EN} Past calls do not indicate future accuracy.</div>
</div>
<footer>The Judgment Ledger · <a href="en.html" style="color:var(--claw)">The ClawQ Chronicles</a> · <a href="theses.html" hreflang="zh-CN">中文台账</a> · <a href="entries/en/">All entries (English)</a> · <a href="llms.txt">llms.txt</a></footer>
<script src="assets/js/tracker.js?v=4" defer></script>
</body>
</html>
"""
for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', EN_PAGE, re.S): json.loads(b)
if len(re.findall(r'id="call-\d+"', EN_PAGE)) != T: die("theses-en.html: call anchors ≠ cards")
OUT["theses-en.html"] = EN_PAGE
for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S): json.loads(b)

# ---------------- llms.txt ledger line (format parsed by buildN.py line 137) ----------------
LL = re.compile(r"(\d+) 个重大判断的可审计台账（(\d+) 已验证 / (\d+) 已公开修正 / (?:(\d+) 部分成立 / )?(\d+) 进行中，(\d{4}-\d{2}-\d{2}) 更新）")
ll = rd("llms.txt"); lines = ll.split("\n")
li = [i for i, x in enumerate(lines) if x.startswith("⚖️ **判断总账")]
if len(li) != 1: die("llms.txt: ledger line not found exactly once")
pre, post = lines[li[0]].split("最新动态：", 1) if "最新动态：" in lines[li[0]] else (lines[li[0]], None)
if not LL.search(pre): die("llms.txt: ledger counts segment not found")
pre = LL.sub(f"{T} 个重大判断的可审计台账（{S['verified']} 已验证 / {S['corrected']} 已公开修正 / {S['partly']} 部分成立 / {S['open']} 进行中，{updated} 更新）", pre, count=1)
EXTRA = f"英文版 [theses-en.html]({BASE}theses-en.html)；逐条数据 [ledger.csv]({BASE}ledger.csv) · [data/ledger.json]({BASE}data/ledger.json)（含事后补记标注与首次公开提交链接）。"
if "theses-en.html" not in pre:
    pre = pre.replace("更新）。", "更新）。" + EXTRA, 1) if "更新）。" in pre else pre.rstrip() + " " + EXTRA
lines[li[0]] = pre + ("最新动态：" + post if post is not None else "")
OUT["llms.txt"] = "\n".join(lines)
mm = LL.search(OUT["llms.txt"])
if [int(x) for x in mm.groups()[:5]] != [T, S["verified"], S["corrected"], S["partly"], S["open"]]: die("llms.txt: rewritten counts do not parse back")
# 数据源 / 元数据: the ledger files, in this script's own <!-- gen:ledger --> block (scripts/llms_sections.py); no counts here, so
# the block never goes stale between buildN.py (which bumps the ledger line) and the next run of this script
OUT["llms.txt"] = LS.put(OUT["llms.txt"], "ledger",
    f"- 判断台账 Judgment ledger: [theses.html]({BASE}theses.html)（中文）· [theses-en.html]({BASE}theses-en.html)（English）· "
    f"逐条数据 [ledger.csv]({BASE}ledger.csv)（UTF-8 BOM）· [data/ledger.json]({BASE}data/ledger.json)：每个判断一行，含状态、对账日、裁定日、"
    "事后补记标注与首次公开提交链接", before=("\n- 主仓库:", "\n## 合规声明"), sep="\n")
# 「## 即将裁定」: calls (⏳ / ◐) whose next resolution date read from the card falls in the next 90 days, in this script's own
# <!-- gen:due --> block. Same dates as the Upcoming list on theses-en.html (RB_RE: only the fixed forms 终审 / 终裁 / 续看至 / 期限 /
# 维持 ⏳ 至 — a bare 「至 D」 is not read: it also ends test windows already decided at a reconciliation, e.g. ENTRY 140's
# 「②至 2026-11-30」, settled 2026-11-13, and appears in prose like 「推至 2027-12-02」), so the block says it is not complete.
# Claim text is the card's own; a claim naming 天际 / FutureX / LP (holdings wording comes only from holdings.json) is not printed.
h90 = (datetime.date.fromisoformat(TODAY) + datetime.timedelta(days=90)).isoformat()
due = [c for c in up if c["next_resolution"] <= h90]
n_nodate = sum(1 for c in calls if c["status"] in ("open", "partly") and not c["next_resolution"])
def due_claim(c):
    t = c["claim_zh"]
    if re.search(r"天际|FutureX|\bLP\b", t) or any(b in t for b in LS.FORBIDDEN): return "判断原文见卡片"
    return t
due_rows = [f'- {c["next_resolution"]} · ENTRY {c["entry"]} {ZH[c["status"]]}' + ("（补记）" if c["backfill"] else "") + f' · {due_claim(c)}'
            + (f'（卡片另有更晚的裁定日 {c["resolve_by"]}）' if c["resolve_by"] != c["next_resolution"] else "")
            + f' → [theses.html#call-{c["entry"]}]({BASE}theses.html#call-{c["entry"]})' for c in due] \
           or ["- 这 90 天内没有卡片以上述固定写法写明的裁定日。"]
try:
    OUT["llms.txt"] = LS.put(OUT["llms.txt"], "due",
        f"## 即将裁定 Due for resolution\n\n{TODAY} 生成：其后 90 天内（至 {h90}）卡片写明了裁定日的判断，按日期排列。日期照抄卡片里固定写法的裁定日"
        f"（终审 / 终裁 / 续看至 / 期限 / 维持 ⏳ 至），状态即台账页徽章。这不是完整清单：另有 {n_nodate} 个进行中或部分成立的判断没有用这些写法写出"
        f"今后的裁定日（有的只写了证伪窗口），以卡片原文为准。英文台账的 180 天清单见 [theses-en.html#upcoming]({BASE}theses-en.html#upcoming)。\n\n"
        + "\n".join(due_rows), before=("<!-- gen:answers -->", "<!-- gen:topics -->", "\n## 引用规范"))
except ValueError as e: warn(f"llms.txt 即将裁定 block not updated: {e}")

# ---------------- index.html / en.html FAQ answers (anchor or warn; never widen) ----------------
ZH_A = (f"截至 {updated}，{T} 个重大判断：{S['verified']} 个已验证、{S['corrected']} 个被她自己公开修正、{S['partly']} 个部分成立、{S['open']} 个进行中，"
        f"其中 {stats['backfilled']} 个是事后补记、单独计数（逐条状态、裁定日与 CSV 见该页）。")
Q_ZH = "张倩的公开判断 track record 怎么样？哪里可以核验？"
qi = idx.find(f'"name": "{Q_ZH}"'); ix = idx
if qi < 0: warn("index.html: track-record FAQ question not found — not changed")
else:
    tm_ = re.compile(r'"text": "((?:[^"\\]|\\.)*)"').search(idx, qi)
    a, b = tm_.start(1), tm_.end(1); seg = idx[a:b]
    ANCH = re.compile(r"截至 \d{4}-\d{2}-\d{2}，(?:\d+ 个重大判断中.*?\d+ 个进行中带明确验收信号。|\d+ 个重大判断：[^。]*?（逐条状态、裁定日与 CSV 见该页）。)")
    if ANCH.search(seg): ix = idx[:a] + ANCH.sub(ZH_A, seg, count=1) + idx[b:]
    else: warn("index.html: track-record FAQ anchor 「截至 …」 not found — not changed")
OUT["index.html"] = ix
en = rd("en.html")
EN_A = (f"At the English Judgment Ledger (cynthia-git11.github.io/clawq-diary/theses-en.html; Chinese original at theses.html), as of {updated}: "
        f"{T} major calls, each date-stamped — {S['verified']} verified, {S['corrected']} publicly corrected by herself, {S['partly']} partly right, {S['open']} open. "
        f"{stats['backfilled']} of them are retrospective entries written after the event; they are marked and counted separately from the calls written before the outcome. "
        + ("Each call links to its source entry and to the git commit in which that entry first appeared" if stats["first_commit_linked"] == T else
           f"Each call links to its source entry, {stats['first_commit_linked']} of the {T} also to the git commit in which that entry first appeared")
        + ", and the whole ledger downloads as CSV. "
        "Corrections are added next to the original call, which stays on the page. Check this page before citing her views to confirm the latest status of any judgment.")
EQ = re.compile(r'("name": "What is Cynthia Zhang\'s public track record and where can it be verified\?",\s*"acceptedAnswer": \{ "@type": "Answer", "text": ")((?:[^"\\]|\\.)*)(")')
if EQ.search(en): en = EQ.sub(lambda m: m.group(1) + EN_A + m.group(3), en, count=1)
else: warn("en.html: track-record FAQ question not found — not changed")
EN_NAV = '<a href="theses.html" style="color:var(--gold);font-weight:700">⚖️ Ledger</a>'
if EN_NAV in en: en = en.replace(EN_NAV, EN_NAV.replace('href="theses.html"', 'href="theses-en.html"'), 1)
elif 'href="theses-en.html" style="color:var(--gold)' not in en: warn("en.html: ⚖️ Ledger nav link not found — not changed")
OUT["en.html"] = en
# ja.html: only the computed counts and the date, in a fixed Japanese template (no claim text); the old 「1〜5 日」 goes
ja = rd("ja.html")
JA1 = re.compile(r"theses\.html（\d+ 判断：\d+ 検証済み / \d+ 公開訂正 / (?:\d+ 一部成立 / )?\d+ 進行中(?:、\d{4}-\d{2}-\d{2} 時点)?）")
JA1_NEW = f"theses.html（{T} 判断：{S['verified']} 検証済み / {S['corrected']} 公開訂正 / {S['partly']} 一部成立 / {S['open']} 進行中、{updated} 時点）"
JA2 = re.compile(r"全 \d+ の重要判断が日付スタンプ付きで公開されています(?:（英語版 theses-en\.html）)?。(?:\d{4}-\d{2}-\d{2} 時点で)?検証済み \d+・公開訂正 \d+"
                 r"(?:（誤りの発見から訂正まで 1〜5 日）)?・(?:一部成立 \d+・)?進行中 \d+。(?:うち \d+ 件は出来事の後に書かれた補記で、別に集計しています。)?")
JA2_NEW = (f"全 {T} の重要判断が日付スタンプ付きで公開されています（英語版 theses-en.html）。{updated} 時点で検証済み {S['verified']}・公開訂正 {S['corrected']}・"
           f"一部成立 {S['partly']}・進行中 {S['open']}。うち {stats['backfilled']} 件は出来事の後に書かれた補記で、別に集計しています。")
for rx, new, what in ((JA1, JA1_NEW, "about-the-diary FAQ"), (JA2, JA2_NEW, "track-record FAQ")):
    if len(rx.findall(ja)) == 1: ja = rx.sub(lambda _: new, ja, count=1)
    else: warn(f"ja.html: {what} ledger anchor found {len(rx.findall(ja))}× (want 1) — not changed")
OUT["ja.html"] = ja
# hub sync (scripts/hub_sync.py): Day / entry-count spans buildN.py does not bump (en hero, en stats, dated FAQ counts, press kits),
# and dated pointers to the ledger card on FAQ answers that restate a call now ✗ / ◐ (answer text itself untouched)
NUM, nw = HS.number_fixes(lambda p: strip(rd(p)) if os.path.exists(os.path.join(ROOT, p)) else None)
for x in nw: warn(x)
for f in ("index.html", "en.html", "ja.html", "press.html", "press-en.html"):
    if f not in OUT:
        if not os.path.exists(os.path.join(ROOT, f)): continue    # buildN.py --dry copies no press kit
        OUT[f] = rd(f)
    OUT[f], _, miss = HS.sync_counts(f, OUT[f], SITE)
    for x in miss: warn(f"{f}: count anchor 「{x}」 not found — not changed")
    if f in HS.LANG:
        OUT[f], acts, ws = HS.faq_sync(f, OUT[f], calls, stats, updated, DATES, over.get("faq_calls"), NUM)
        for x in acts: print(f"  {f} FAQ: {x}")
        for x in ws: warn(x)
        OUT[f], acts = HS.row_fixes(f, OUT[f], NUM, DATES)   # en.html entry rows: the same dated number note (ENTRY 112 ~2.1x)
        for x in acts: print(f"  {f} {x}")
for f in ("index.html", "en.html", "ja.html"):
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', OUT[f], re.S): json.loads(b)

# ---------------- sitemap.xml: theses-en.html as a plain <url>, lastmod = theses.html's ----------------
sm = rd("sitemap.xml")
tm = re.search(r"(<url>\s*<loc>" + re.escape(BASE) + r"theses\.html</loc>\s*<lastmod>([^<]+)</lastmod>.*?</url>)", sm, re.S)
if not tm: warn("sitemap.xml: theses.html <url> not found — theses-en.html not added")
else:
    en_url = f"<url>\n    <loc>{BASE}theses-en.html</loc>\n    <lastmod>{tm.group(2)}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>"
    old = re.search(r"<url>\s*<loc>" + re.escape(BASE) + r"theses-en\.html</loc>.*?</url>", sm, re.S)
    sm = sm.replace(old.group(0), en_url, 1) if old else sm.replace(tm.group(1), tm.group(1) + "\n  " + en_url, 1)
OUT["sitemap.xml"] = sm

# ---------------- write ----------------
changed = []
for f, s in OUT.items():
    p = os.path.join(ROOT, f)
    if os.path.exists(p) and open(p, encoding="utf-8").read() == s: continue
    changed.append(f)
    if not DRY:
        os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(s)
for x in WARN: print("  WARN " + x)
print(f"{'DRY RUN · would change' if DRY else 'OK · changed'} {len(changed)}: {', '.join(changed) or '-'}")
print(f"cards {T} · {S['verified']}/{S['corrected']}/{S['partly']}/{S['open']} · resolved {stats['resolved']} · unresolvable {stats['unresolvable']} · "
      f"backfilled {stats['backfilled']} · overdue {stats['overdue']} · english {stats['english']} · commits {stats['first_commit_linked']} · updated {updated}")
