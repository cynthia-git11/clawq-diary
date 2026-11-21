#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: one page per question, for investors and AI founders (zh + en).

Input : data/answers.json  — list of items:
        {id, slug(optional; frozen on first build), persona_group ("投资人"|"创业者"), persona, q_zh, q_en, date (YYYY-MM-DD),
         entries [int], topics [slug from data/topics.json], related [ids],
         lead_zh, judgment_zh, facts_zh, landing_zh, falsify_zh (verbatim from the ENTRY footnote), status_zh,
         lead_en, judgment_en, facts_en, landing_en, falsify_en,
         optional: verdict_zh (str or list: verbatim quote(s) of a dated reconciliation note on a cited entry), status_en
         (hand-written English status, CJK-free), entities [record names for the holdings disclosure],
         notes_reviewed {entry: date}: a newer dated note that was read and does not bear on this answer (it stays out of
         the lead; the STALE warning comes back as soon as a note newer than that date lands)}
        q20's lead may carry the placeholder {holdings}: it is replaced by holdings_lib.portfolio() (never typed by hand).
Reads : index.html (number-fidelity gate: every number in every text field must appear verbatim in a cited ENTRY, allowing
        亿↔B/M unit conversions ×/÷10,100,1000; falsify_zh must be verbatim, clause by clause, after the same normalisation),
        theses.html + index.html footnotes (dated notes 「（D 对账/补对账/读数/更正：…）」「｜D 对账：…」), data/ledger.json (status),
        data/entries-en-map.json + entries/en/<N>.html (English h1 for source links), data/topics.json (entity names,
        non-holdings disclosure sentences), holdings.json via scripts/holdings_lib.py (every holdings sentence).
Verdict-first lead (2026-11-21): when a cited card changed after the question's date, the lead opens with the dated note
        「D 对账（ENTRY N）：<verdict_zh>」 and then 「原判断（date）：<lead>」, newest note first. verdict_zh is allowed only as a
        verbatim quote (≥12 characters, starting and ending at a clause boundary of the note) of a 对账 / 补对账 / 读数 / 更正 note
        dated after the question; it is required (else a ledger-template line + WARN, never a failed build) when a cited call's
        status changed to ✗ / ◐ / ✓, or a sub-claim was judged wrong, after the question's date (the change date is the first
        note carrying that verdict, not the last reconciliation). A cited card whose newest dated note (any label) is later
        than both the question and every quoted verdict is listed as 'WARN STALE'. A cited entry written after the question
        gets a 「后续日记」/ 'Later entry' line (its own title / English h1 only). English pages never translate the
        note: the line is a template from data/ledger.json (status, dates; retracted wording quoted as Chinese original), and
        the status bar is status_en or, when no faithful English exists, a ledger.json template (WARN lists those questions);
        a hand-written status_en that no longer shows a cited call's ✗ / ◐ / ✓ is treated as stale and replaced the same way.
        Template text carries only ledger.json fields (dates, ENTRY numbers) and quotes already gated on the Chinese side.
Writes: answers/<slug>.html, answers/en/<slug>.html, answers/index.html, answers/en/index.html, sitemap-answers.xml,
        robots.txt Sitemap line if missing, and the llms.txt Q&A index (only its own <!-- gen:answers --> block, through
        scripts/llms_sections.py: one line per question with the zh + en URL, the question, the index page's dates and each
        cited entry's ledger status from data/ledger.json). Slugs are frozen into data/answers.json on first build (never renamed after publish).
        Pages that print the portfolio sentence (q20's {holdings}, the two index pages) take holdings.json's 'updated' as a
        modification date.
Guards: number / verdict / falsifier gate → exit 1 before writing; a banned phrase in any rendered page → exit 1 before
        anything is written; a record name / alias the question's text names but its disclosure omits → WARN (never printed);
        companies a question names that are not in holdings.json are printed as 'PENDING disclosure qNN: X' and nothing is
        said about holding them (--strict-disclosure makes that exit 1). geo-check.py repeats the page checks hourly in CI.
Usage : python3 scripts/gen-answers.py [--root DIR] [--dry] [--no-verify] [--strict-disclosure]   (root: --root, else $CLAWQ_ROOT)
"""
import re, os, sys, json, html, shutil, tempfile

BASE = "https://cynthia-git11.github.io/clawq-diary/"
ROOT = os.environ.get("CLAWQ_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = sys.argv[sys.argv.index("--root") + 1]
DRY = "--dry" in sys.argv; VERIFY = "--no-verify" not in sys.argv; STRICT_DISC = "--strict-disclosure" in sys.argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import holdings_lib as HL
import llms_sections as LS
HOLD = HL.load()
SRC = ROOT
if DRY:
    W = tempfile.mkdtemp(prefix="answers-")
    for f in ["index.html", "robots.txt", "llms.txt"]:
        if os.path.exists(os.path.join(ROOT, f)): shutil.copy(os.path.join(ROOT, f), W)
    shutil.copytree(os.path.join(ROOT, "data"), os.path.join(W, "data"))
    ROOT = W
def rd(f): return open(os.path.join(ROOT, f), encoding="utf-8").read()
def wr(f, s):
    p = os.path.join(ROOT, f); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(s)
def strip(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
def esc(s): return html.escape(s or "", quote=True)
TAG = re.compile(r"</?[A-Za-z][^>]*>")          # real tags only: card text has a literal "<8%"
def plain(s): return re.sub(r"\s+", " ", html.unescape(TAG.sub("", s or ""))).strip()
def norm(s): return re.sub(r"\s+", " ", html.unescape(s or "").replace(",", "").replace("，", "")).strip()   # = etext normalisation
WARN = []

Q = json.load(open(os.path.join(ROOT, "data/answers.json"), encoding="utf-8"))
TOPICS = {t["slug"]: t for t in json.load(open(os.path.join(ROOT, "data/topics.json"), encoding="utf-8"))}
idx = rd("index.html")
def block_at(s, start):
    i = start; depth = 0; tag = re.compile(r"<(/?)div\b[^>]*>", re.I)
    while True:
        m = tag.search(s, i); depth += -1 if m.group(1) else 1; i = m.end()
        if depth == 0: return i
etext = {}; etitle = {}; edate = {}; eblk = {}
for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>', idx):
    n = int(m.group(1)); blk = idx[m.start():block_at(idx, m.start())]; eblk[n] = blk
    etext[n] = strip(blk).replace(",", "").replace("，", ""); etitle[n] = strip((re.search(r'<h3 class="entry-title">(.*?)</h3>', blk, re.S) or [None, ""])[1])
    dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", blk); edate[n] = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}" if dm else ""

# ---------- slugs: frozen on first build ----------
STOP = set("a an the is are was were be been do does did has have had can could should would will may might of to in on for from by with as at and or vs vs. how what when why who which where whether if it its my our their this that these those i we you they them there here than then into over under about after before between still yet does".split())
def slugify(q):
    words = [w for w in re.sub(r"[^a-z0-9\s\-]", " ", q.lower()).split() if w not in STOP and len(w) > 1]
    return "-".join(words[:6]) or "q"
seen = set(); changed = False
for q in Q:
    if not q.get("slug"):
        s = slugify(q["q_en"]); base = s; k = 2
        while s in seen: s = f"{base}-{k}"; k += 1
        q["slug"] = s; changed = True
    seen.add(q["slug"])
if changed and not DRY:
    json.dump(Q, open(os.path.join(SRC, "data/answers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
assert len(seen) == len(Q), "duplicate slugs"

# ---------- ledger status, English titles, dated reconciliation notes ----------
LEDGER = {}
try:
    for c in json.load(open(os.path.join(ROOT, "data/ledger.json"), encoding="utf-8"))["calls"]: LEDGER[int(c["entry"])] = c
except FileNotFoundError:
    WARN.append("data/ledger.json missing — English status bars only point to the ledger (run scripts/gen-ledger.py)")
EN_TITLE = {}
try:
    for k, rel in json.load(open(os.path.join(SRC, "data/entries-en-map.json"), encoding="utf-8")).items():
        fp = os.path.join(SRC, rel)
        h1 = re.search(r'<h1 class="ee-h1">(.*?)</h1>', open(fp, encoding="utf-8").read(), re.S) if os.path.exists(fp) else None
        if h1: EN_TITLE[int(k)] = plain(h1.group(1))
except FileNotFoundError: pass
HAS_EN_LEDGER = os.path.exists(os.path.join(SRC, "theses-en.html"))
th_raw = open(os.path.join(SRC, "theses.html"), encoding="utf-8").read() if os.path.exists(os.path.join(SRC, "theses.html")) else ""
def paren_at(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == "（": d += 1
        elif s[j] == "）":
            d -= 1
            if d == 0: return s[i + 1:j]
    return s[i + 1:]
LABELS = r"(补?对账|读数|更正)"          # quotable dated notes (the author's ledger wording); 更新 footnotes are holdings updates
NOTE_CARD = re.compile(r"（(\d{4}-\d{2}-\d{2}) ?" + LABELS)
NOTE_FOOT = re.compile(r"^\s*(\d{4}-\d{2}-\d{2}) ?" + LABELS)
NOTE_ANY = re.compile(r"（(\d{4}-\d{2}-\d{2}) ?([^：（）\s]{1,10})：")   # any dated card note (分母修正, 补记 …): staleness only
_notes = {}; _cardseg = {}
def card_seg(n):
    if n not in _cardseg:
        i = th_raw.find(f'<div class="call" id="call-{n}"'); j = th_raw.find('<div class="call"', i + 10) if i != -1 else -1
        _cardseg[n] = plain(th_raw[i:j if j != -1 else len(th_raw)]) if i != -1 else ""
    return _cardseg[n]
def notes_for(n):
    """dated notes on ENTRY n → [(date, label, text, where)]: the theses.html card 「（D 对账：…）」 and the index.html
    footnote 「｜D 对账：…」, labels 对账 / 补对账 / 读数 / 更正 (the author's published wording; a verdict quotes one verbatim)"""
    if n in _notes: return _notes[n]
    out = []; seg = card_seg(n)
    for m in NOTE_CARD.finditer(seg):
        body = paren_at(seg, m.start()); k = body.find("：")
        out.append((m.group(1), m.group(2), body[k + 1:] if k != -1 else body, "card"))
    for part in plain(eblk.get(n, "")).split("｜"):
        m = NOTE_FOOT.match(part)
        if m: out.append((m.group(1), m.group(2), part[m.end():].lstrip("：，, "), "footnote"))
    _notes[n] = out; return out
def newest_note(n):
    """(date, label) of the newest dated note on ENTRY n: any label on the card, the quotable labels in the footnote"""
    xs = [(m.group(1), m.group(2)) for m in NOTE_ANY.finditer(card_seg(n))] + [(d, lab) for d, lab, _, w in notes_for(n) if w == "footnote"]
    return max(xs) if xs else None
BOUND = "：，；。"                        # clause boundaries; a quote may also start after an em dash 「——」
def quoted_in(v, body):
    """v is a verbatim quote of body: ≥12 characters, starting and ending at a clause boundary (or the note's start / end)"""
    v = plain(v).rstrip("。"); b = plain(body)
    if len(v) < 12: return False
    i = b.find(v)
    while i != -1:
        z = i + len(v)
        if (i == 0 or b[i - 1] in BOUND + "（—") and (z == len(b) or b[z] in BOUND + "）"): return True
        i = b.find(v, i + 1)
    return False
MARK = {"corrected": ("记 ✗", "✗ 认错"), "partly": ("◐", "部分成立"), "verified": ("✓", "已验证"), "open": ("记 ✗",)}   # a bare ✗ also
# appears in falsifier wording (「✗ 线」「✗ 条件成立中」), so an open card is matched only on 「记 ✗」 or the judged-wrong wording itself
def decision_date(n, c):
    """the date a call's status changed to ✗ / ◐ / ✓, or a sub-claim was judged wrong / wording retracted; None while plainly
    open. The change date is the first dated note that carries the verdict (a later reconciliation that keeps the status does
    not move it); ledger.json's reconciled (the last reconciliation) is only the fallback."""
    st = c["status"]
    if st == "corrected" and c.get("correction_entry") and c.get("corrected_on"): return c["corrected_on"]
    if st == "open" and not (c.get("subclaim_judged_wrong") or c.get("retracted")): return None
    marks = MARK.get(st, ()) + tuple(x for x in (c.get("subclaim_judged_wrong"), c.get("retracted")) if x)
    ds = sorted(d for d, lab, body, w in notes_for(n) if w == "card" and any(k in body for k in marks))
    return ds[0] if ds else (c.get("corrected_on") if st == "corrected" else None) or c.get("reconciled")
def written_of(n): return (LEDGER.get(n) or {}).get("written_date") or edate.get(n, "")

LE = {"verified": "✓ Verified", "corrected": "✗ Publicly corrected", "partly": "◐ Partly right", "open": "⏳ Open"}   # = gen-entries-en.py
NOTE_EN = {"对账": "reconciliation note", "补对账": "reconciliation note", "读数": "reading note", "更正": "correction note"}
def status_en_phrase(c, lead=False, quote=None, label="对账"):
    """English status from data/ledger.json fields only; the author's Chinese wording is quoted, never translated"""
    st = c["status"]; k = c.get("correction_entry"); rc = c.get("reconciled"); lr = c.get("last_reading")
    if st == "corrected": s = f'{LE[st]} on {c.get("corrected_on") or rc}' + (f" in ENTRY {k}" if k else " at the dated ledger reconciliation")
    elif st == "partly": s = f'{LE[st]} (reconciled {rc})'
    else: s = LE[st] + (" · resolution source missing" if c.get("unresolvable") else "") + (f' (reconciled {rc})' if rc else "")
    if lr and (not rc or lr > rc): s += f"; last reading {lr}"
    if lead:
        if c.get("retracted"): s += f'; retracted wording (Chinese original): 「{c["retracted"]}」'
        if c.get("subclaim_judged_wrong"): s += f'; sub-claim judged wrong at reconciliation (Chinese original): 「{c["subclaim_judged_wrong"]}」'
        if st == "open" and not (c.get("retracted") or c.get("subclaim_judged_wrong")) and quote: s += f"; {NOTE_EN.get(label, 'dated note')} (Chinese only): 「{quote}」"
    else:
        if c.get("retracted"): s += "; the retracted wording is quoted in Chinese on the ledger card"
        if c.get("subclaim_judged_wrong"): s += "; a sub-claim was judged wrong at reconciliation (wording in Chinese on the ledger card)"
        if st == "open" and c.get("resolve_dates"):
            r = c["resolve_dates"]; s += f'; final / review-until date{"s" if len(r) > 1 else ""} read from the card: {", ".join(r)}' + ("; overdue" if c.get("overdue") else "")
        if c.get("backfill"): s += f'; retrospective, written {c["written_date"]}, not scored as a forward call'
    return s
ZH_ST = {"verified": "✓ 已验证", "corrected": "✗ 已公开修正", "partly": "◐ 部分成立"}
def verdict_template_zh(n, c, d):
    """the lead line when no dated note has been quoted yet: ledger status words only"""
    k = c.get("correction_entry")
    if c["status"] == "corrected" and k: return f"{d} 更正（ENTRY {n}）：在 ENTRY {k} 记 ✗ 已公开修正，原判断照原文保留，见判断台账"
    if c["status"] == "corrected": return f"{d} 对账（ENTRY {n}）：记 ✗ 已公开修正，原判断照原文保留，见判断台账"
    if c["status"] in ZH_ST: return f"{d} 对账（ENTRY {n}）：记 {ZH_ST[c['status']]}，见判断台账"
    if c.get("subclaim_judged_wrong"): return f"{d} 对账（ENTRY {n}）：一条子判断记 ✗，卡片维持 ⏳ 进行中，见判断台账"
    return f"{d} 对账（ENTRY {n}）：撤回措辞「{c['retracted']}」，卡片维持 ⏳ 进行中，见判断台账"

# ---------- verdicts (verbatim dated notes) ----------
problems = []
VERD = {}; REVIEWED = []
for q in Q:
    q["entries"] = [int(n) for n in q["entries"]]
    vs = q.get("verdict_zh") or []
    vs = [vs] if isinstance(vs, str) else list(vs)
    got = []
    for k, v in enumerate(vs):
        hits = [(d, lab, n, w) for n in q["entries"] for d, lab, body, w in notes_for(n) if d > q["date"] and quoted_in(v, body)]
        if not hits:
            problems.append(f"{q['id']} verdict_zh: not a verbatim quote (≥12 characters, clause to clause) of a 对账/读数/更正 note dated after {q['date']} on a cited entry — {v[:40]}"); continue
        d, lab, n, w = max(hits, key=lambda h: (h[0], h[3] == "card"))
        c = LEDGER.get(n); v = v.rstrip("。")
        same = any(g["entry"] == n and g["date"] == d for g in got)   # a second quote from the same note: no repeated status
        got.append(dict(entry=n, date=d, rank=(0, k), zh=f"{d} {lab}（ENTRY {n}）：{v}",
                        en=(f"Same {d} {NOTE_EN.get(lab, 'dated note')} (ENTRY {n}, Chinese only): 「{v}」" if same else
                            f"Ledger update {d} (ENTRY {n}): " + (status_en_phrase(c, True, v, lab) if c else f"{NOTE_EN.get(lab, 'dated note')} (Chinese only): 「{v}」"))))
    for n in q["entries"]:       # required: a cited call whose status changed after the question was written
        c = LEDGER.get(n); d = decision_date(n, c) if c else None
        if not d or d <= q["date"] or any(g["entry"] == n and g["date"] >= d for g in got): continue
        WARN.append(f"VERDICT missing {q['id']}: ENTRY {n} is {c['status']} since {d} — lead shows the ledger template; quote the dated note into verdict_zh")
        got.append(dict(entry=n, date=d, rank=(1, q["entries"].index(n)), zh=verdict_template_zh(n, c, d), en=f"Ledger update {d} (ENTRY {n}): " + status_en_phrase(c, True)))
    seen_ok = {int(k): v for k, v in (q.get("notes_reviewed") or {}).items()}
    for n in q["entries"]:       # staleness: a dated note on a cited card that is newer than the question and every quoted verdict
        nn = newest_note(n)
        if not nn or nn[0] <= q["date"] or any(g["entry"] == n and g["date"] >= nn[0] for g in got): continue
        if seen_ok.get(n, "") >= nn[0]: REVIEWED.append(f"{q['id']}/ENTRY {n} ({nn[0]})"); continue
        WARN.append(f"STALE {q['id']}: ENTRY {n} has a {nn[1]} note dated {nn[0]} after the question and no verdict quotes it — quote it into verdict_zh")
    for n in q["entries"]:       # a cited entry written after the question: its own title / English h1, nothing else
        wd = written_of(n)
        if wd and wd > q["date"]:
            en = f"Later entry (English): ENTRY {n} · {EN_TITLE[n]} (written {wd})" if n in EN_TITLE else f"Later entry: ENTRY {n} (written {wd}; Chinese only)"
            got.append(dict(entry=n, date=wd, rank=(2, q["entries"].index(n)), zh=f"后续日记（ENTRY {n}，写于 {wd}）：{etitle.get(n, '')}", en=en, later=True))
            if f"ENTRY {n}" not in (q.get("status_zh") or ""): WARN.append(f"{q['id']} status_zh: says nothing about ENTRY {n}, written {wd} after the question")
    VERD[q["id"]] = sorted(got, key=lambda g: (g["date"], (-g["rank"][0], -g["rank"][1])), reverse=True)   # newest first

# ---------- number-fidelity gate (+ verbatim falsifier, + CJK-free status_en) ----------
FIELDS_ZH = ["lead_zh", "judgment_zh", "facts_zh", "landing_zh", "falsify_zh", "status_zh", "verdict_zh"]
FIELDS_EN = ["lead_en", "judgment_en", "facts_en", "landing_en", "falsify_en", "status_en"]
NUM = re.compile(r"\d+(?:\.\d+)?")
SMALL = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "24", "30", "60", "90", "100"}
def enorm(s): return strip(s or "").replace(",", "").replace("，", "")   # exactly how etext is normalised
for q in Q:
    cited = " ".join(etext.get(n, "") for n in q["entries"])
    for n in q["entries"]:
        if n not in etext: problems.append(f"{q['id']}: cites ENTRY {n} which does not exist")
    for t in q.get("topics", []):
        if t not in TOPICS: problems.append(f"{q['id']}: unknown topic slug {t}")
    for f in FIELDS_ZH + FIELDS_EN:
        v = q.get(f) or ""; v = "　".join(v) if isinstance(v, list) else v
        txt = v.replace(",", "")
        txt = re.sub(r"ENTRY\s*\d+(?:\s*[/、和与&]\s*\d+)*", " ", txt)   # entry ids are references, not data
        for tok in set(NUM.findall(txt)):
            if tok in SMALL or re.fullmatch(r"20\d\d", tok): continue
            # unit conversions the English side makes: 亿↔B/M (×/÷10, 100, 1000) and 万↔absolute (×/÷10000)
            v = float(tok); alts = {tok} | {f"{v*10:g}", f"{v/10:g}", f"{v*100:g}", f"{v/100:g}", f"{v*1000:g}", f"{v/1000:g}", f"{v*10000:g}", f"{v/10000:g}"}
            if not any(a in cited for a in alts): problems.append(f"{q['id']} {f}: number {tok} not found in cited entries {q['entries']}")
    # falsify_zh is labelled 逐字取自日记尾注: every clause must be verbatim in a cited entry, after the etext normalisation
    for seg in re.split(r"[。；｜]|ENTRY \d+：", enorm(q.get("falsify_zh"))):
        if len(seg.strip()) >= 8 and seg.strip() not in cited: problems.append(f"{q['id']} falsify_zh: clause not verbatim in cited entries — {seg.strip()[:40]}")
    if q.get("status_en") and HL.CJK.search(q["status_en"]): problems.append(f"{q['id']} status_en: contains CJK characters")
    if q.get("status_en"):          # a hand-written English status that no longer shows a cited call's ✗ / ◐ / ✓ is stale: template instead
        miss = [n for n in q["entries"] if n in LEDGER and {"corrected": "✗", "partly": "◐", "verified": "✓"}.get(LEDGER[n]["status"], "") not in q["status_en"]]
        if miss: WARN.append(f"{q['id']} status_en disagrees with the ledger for ENTRY {', '.join(map(str, miss))} — ledger template used"); q.pop("status_en")
    for f in ("lead_zh", "lead_en", "judgment_zh", "judgment_en", "facts_zh", "facts_en", "landing_zh", "landing_en", "status_zh", "status_en", "verdict_zh"):
        v = q.get(f) or ""; v = " ".join(v) if isinstance(v, list) else v
        if HL.banned_hits(v): problems.append(f"{q['id']} {f}: banned disclosure phrase {HL.banned_hits(v)}")
if VERIFY and problems:
    print("NUMBER-FIDELITY GATE FAILED:"); [print("  ✗", p) for p in problems]; sys.exit(1)
no_en = [q["id"] for q in Q if not q.get("status_en")]
if no_en: WARN.append(f"status_en: no faithful English status for {len(no_en)} questions — English status bars generated from data/ledger.json: {', '.join(no_en)}")

# ---------- disclosure: Claude sentence + holdings_lib (holdings.json, fixed sentences) + non-holdings topic sentences ----------
CLAUDE_ZH = "本日记由 Claude 系工具写作与核实，涉及 Anthropic 的判断（有利或不利）都请打折读"
CLAUDE_EN = "This diary is written and verified with Claude; discount any judgment about Anthropic, favourable or not"
PENDING = []
def entity_names(q):
    names = list(q.get("entities", []))
    for t in q.get("topics", []): names += HL.TOPIC_ENTITIES.get(t, []) + TOPICS.get(t, {}).get("entities", [])
    return names
def disclosure(q, zh):
    parts = [CLAUDE_ZH if zh else CLAUDE_EN]
    hs, pend = HL.statement(HOLD, entity_names(q), zh)
    if zh: PENDING.extend((q["id"], p) for p in pend if (q["id"], p) not in PENDING)
    parts += hs
    for t in q.get("topics", []):
        d = TOPICS.get(t, {}).get("disclosure" if zh else "disclosure_en")
        if not d or t == "anthropic": continue          # the Claude sentence above already covers Anthropic
        if re.search(r"天际|FutureX", d) or HL.banned_hits(d):   # holdings wording comes only from holdings.json
            w = f"topics.json {t}: disclosure carries holdings wording — ignored (holdings come from holdings.json)"
            if zh and w not in WARN: WARN.append(w)
            continue
        d = re.sub(r"^本日记由 Claude 系工具写作(与核实)?，", "", d); d = re.sub(r"^This diary is written with Claude, which", "Claude", d)
        if d and d not in parts: parts.append(d)
    return ("利益披露：" if zh else "Disclosure: ") + ("；".join(parts) if zh else ". ".join(parts)) + ("。" if zh else ".")
def uses_portfolio(q): return any("{holdings}" in (q.get(f) or "") for f in ("lead_zh", "lead_en"))
def fill(s, zh): return (s or "").replace("{holdings}", ("；".join(HL.portfolio(HOLD, True)) if zh else ". ".join(HL.portfolio(HOLD, False))))
TEXT_F = ["q_zh", "q_en", "lead_zh", "lead_en", "judgment_zh", "judgment_en", "facts_zh", "facts_en", "landing_zh", "landing_en",
          "falsify_zh", "falsify_en", "status_zh", "status_en", "verdict_zh"]
def named_not_disclosed(q):
    """record names / aliases the question's own text names (Latin: whole word, case-sensitive; CJK: substring) that its
    disclosure does not cover — a WARN for the author's checklist only; nothing is ever printed from this scan"""
    t = " ".join(" ".join(v) if isinstance(v, list) else (v or "") for v in (q.get(f) for f in TEXT_F))
    have = {(HL.lookup(HOLD, x) or {}).get("name") for x in entity_names(q)}; out = []
    if uses_portfolio(q): have |= {r["name"] for r in HOLD["rows"].values() if r["kind"] in ("held", "exited")}
    for r in HOLD["rows"].values():
        if r["name"] in have or r["kind"] == "fund": continue
        for a in [r["name"]] + r["aliases"] + SCAN_ONLY.get(r["name"], []):
            hit = (a in t) if HL.CJK.search(a) else re.search(r"(?<![A-Za-z0-9])" + re.escape(a) + r"(?![A-Za-z0-9])", t)
            if hit: out.append(f"{r['name']} (as {a})"); break
    return out
SCAN_ONLY = {"字节跳动": ["字节", "火山引擎"]}   # short forms the site writes; used by the WARN scan only, never printed
HOLD_UPD = HOLD.get("updated", "")

CSS = """
    .aw-wrap{max-width:820px;margin:0 auto;padding:28px 18px 60px}
    .aw-nav{font-family:var(--sans,Inter,sans-serif);font-size:13px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:18px;color:var(--muted)}
    .aw-nav a{color:var(--claw2,#B8860B);text-decoration:none;font-weight:600}.aw-nav .aw-brand{font-weight:800;color:var(--text);font-size:15px}
    .aw-crumb{font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin-bottom:14px}.aw-crumb a{color:var(--muted2);text-decoration:none}
    h1.aw-h1{font-size:26px;line-height:1.35;margin-bottom:10px}
    .aw-meta{font-family:var(--sans,Inter,sans-serif);font-size:12.5px;color:var(--muted2);margin-bottom:20px;line-height:1.8}.aw-meta time{color:var(--muted)}
    .aw-lead{font-size:17px;line-height:1.85;color:var(--text);font-weight:600;margin-bottom:22px;padding:14px 16px;border-left:3px solid var(--claw2,#B8860B);background:var(--panel,rgba(0,0,0,.03))}
    .aw-lead .aw-orig{display:inline-block;margin-top:8px;font-weight:500;color:var(--muted)}
    .aw-h2{font-size:13px;font-family:var(--sans,Inter,sans-serif);letter-spacing:.06em;color:var(--muted);text-transform:uppercase;margin:26px 0 8px}
    .aw-p{font-size:15.5px;line-height:1.9;color:var(--muted)}.aw-p strong{color:var(--text)}
    .aw-falsify{font-size:13.5px;line-height:1.8;color:var(--muted);padding:12px 14px;border:1px dashed var(--border);border-radius:6px;margin-top:6px}
    .aw-status{font-family:var(--sans,Inter,sans-serif);font-size:13px;color:var(--text);margin-top:8px}
    .aw-disc{font-size:12.5px;line-height:1.75;color:var(--muted2);margin-top:26px;padding-top:14px;border-top:1px solid var(--border)}
    .aw-src,.aw-rel{font-family:var(--sans,Inter,sans-serif);font-size:13px;color:var(--muted);line-height:1.9;margin-top:14px}.aw-src a,.aw-rel a{color:var(--claw2,#B8860B);text-decoration:none}
    .aw-foot{margin-top:40px;font-size:12px;color:var(--muted2);line-height:1.7;border-top:1px solid var(--border);padding-top:16px}
    .aw-list{list-style:none;padding:0;margin:0 0 26px}.aw-list li{padding:12px 0;border-bottom:1px solid var(--border)}
    .aw-list a{font-size:16px;color:var(--text);text-decoration:none;font-weight:600;line-height:1.5}.aw-list a:hover{color:var(--claw2,#B8860B)}
    .aw-list .aw-lp{font-size:14px;color:var(--muted);line-height:1.75;margin-top:4px}.aw-list .aw-ld{font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin-top:4px}
"""
def head_links(depth):
    up = "../" * depth
    return f"""  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{up}assets/css/main.css?v=10" />
  <link rel="icon" type="image/png" href="{up}assets/clawq-square.jpg" />"""
PERSON = {"@type": "Person", "@id": f"{BASE}#cynthia", "name": "张倩 Cynthia Zhang", "url": BASE, "worksFor": {"@type": "Organization", "name": "天际资本 FutureX Capital", "url": "https://futurex.capital"}}
BLOG = {"@type": "Blog", "@id": f"{BASE}#blog", "name": "倩小虾日记 · The ClawQ Chronicles", "url": BASE}
BYID = {q["id"]: q for q in Q}

def nav(zh, depth, alt_href):
    up = "../" * depth
    L = (["🦞 倩小虾日记", "问答", "EN", "主题", "全部日记", "⚖️ 判断台账"] if zh else ["🦞 The ClawQ Chronicles", "Q&A", "中文", "Topics", "All entries", "⚖️ Ledger"])
    idxh = f"{up}answers/" if zh else f"{up}answers/en/"
    ledger = f"{up}theses.html" if zh or not HAS_EN_LEDGER else f"{up}theses-en.html"
    return (f'<nav class="aw-nav" aria-label="nav"><a class="aw-brand" href="{up}">{L[0]}</a><a href="{idxh}">{L[1]}</a><a href="{alt_href}">{L[2]}</a>'
            f'<a href="{up}topics/">{L[3]}</a><a href="{up}entries/">{L[4]}</a><a href="{ledger}">{L[5]}</a></nav>')

ZHQ = re.compile(r"「[^「」]*(?:「[^「」]*」[^「」]*)*」")
def zh_spans(h): return ZHQ.sub(lambda m: f'<span lang="zh-CN">{m.group(0)}</span>', h)   # Chinese quotes on English pages
def cut300(s, n=300):
    """meta descriptions only: cut at a sentence end (。；！？ or '. ' / '; '), else a clause comma, else a space that does not
    split a number from its unit — never inside a number or a quote's unit"""
    if len(s) <= n: return s
    w = s[:n - 2]; cut = w.rstrip()
    for pat in (r"[。；！？]|[.;](?= )", r"[，,](?= ?\S)", r"(?<=[^\d.,$%–-]) (?=[^\d$%])"):
        ends = [m.end() for m in re.finditer(pat, w) if m.end() >= n // 2]
        if ends: cut = w[:ends[-1]].rstrip(" ，,；;"); break
    return cut + "…" + "」" * max(0, cut.count("「") - cut.count("」"))   # a cut inside a quote closes it
def lead_parts(q, zh):
    """→ (verdict line, lead line, description, last verdict date): the verdict-first lead"""
    lead = fill(q.get("lead_zh" if zh else "lead_en"), zh)
    vs = VERD.get(q["id"], [])
    if not vs: return "", lead, cut300(lead), ""
    end = lambda x, z: x if x[-1:] in ("。", "！", "？", ".") else x + ("。" if z else ".")
    vline = ("" if zh else " ").join(end(v["zh" if zh else "en"], zh) for v in vs)
    if not zh and any(not v.get("later") and (LEDGER.get(v["entry"]) or {}).get("status") in ("corrected", "partly") or
                      (LEDGER.get(v["entry"]) or {}).get("subclaim_judged_wrong") for v in vs):
        vline += " The original call below is kept as written."
    orig = f"原判断（{q['date']}）：{lead}" if zh else f"Original call ({q['date']}): {lead}"
    return vline, orig, cut300(vline + " " + orig), max(v["date"] for v in vs)
def page_updated(q):
    """→ (date, label kind): the newest of the question's own update, its verdicts, and the holdings record for {holdings}"""
    vdate = lead_parts(q, True)[3]
    u = max(q.get("updated", ""), q.get("date", ""), vdate, HOLD_UPD if uses_portfolio(q) else "")
    return u, ("ledger" if u == vdate else "page")
def status_en_html(q, up):
    """→ (html, plain): hand-written status_en, else one template line per cited entry from data/ledger.json"""
    if q.get("status_en"): return esc(q["status_en"]), q["status_en"]
    ledger = f"{up}theses-en.html" if HAS_EN_LEDGER else f"{up}theses.html"
    if not LEDGER: return f'see the <a href="{ledger}">judgment ledger</a>', "see the judgment ledger"
    hs, ps = [], []
    for n in q["entries"]:
        c = LEDGER.get(n)
        if not c: hs.append(f"ENTRY {n}: not on the judgment ledger"); ps.append(hs[-1]); continue
        t = status_en_phrase(c); ps.append(f"ENTRY {n}: {t}")
        hs.append(f'<a href="{ledger}#call-{n}">ENTRY {n}</a>: {esc(t)}')
    tail = "Generated from the judgment ledger; the dated reconciliation notes are in Chinese on the ledger cards."
    return " · ".join(hs) + ". " + tail, " · ".join(ps) + ". " + tail

def page(q, zh):
    depth = 1 if zh else 2; up = "../" * depth
    url = BASE + (f"answers/{q['slug']}.html" if zh else f"answers/en/{q['slug']}.html")
    alt = BASE + (f"answers/en/{q['slug']}.html" if zh else f"answers/{q['slug']}.html")
    alt_rel = f"en/{q['slug']}.html" if zh else f"../{q['slug']}.html"
    g = lambda k: q.get(k + ("_zh" if zh else "_en")) or ""
    title = g("q"); judg, facts, land, fals = g("judgment"), g("facts"), g("landing"), g("falsify")
    vline, orig, desc, vdate = lead_parts(q, zh)
    if zh: status_h = esc(q.get("status_zh", "")); status = q.get("status_zh", "")
    else: status_h, status = status_en_html(q, up)
    C = "：" if zh else ": "
    answer_txt = " ".join(x for x in [vline, orig, judg, facts, land, (("证伪口：" if zh else "Falsifier: ") + fals) if fals else "",
                                      (("台账状态：" if zh else "Ledger status: ") + status) if status else ""] if x)
    date = q.get("date") or max((edate.get(n, "") for n in q["entries"]), default="")
    updated, ukind = page_updated(q)
    def src1(n):
        if zh: return f'<a href="{up}entries/{n}.html">ENTRY {n} · {esc(etitle.get(n, ""))}</a>'
        if n in EN_TITLE: return f'<a href="{up}entries/en/{n}.html">ENTRY {n} · {esc(EN_TITLE[n])}</a>'
        return f'<a href="{up}entries/{n}.html" hreflang="zh-CN">ENTRY {n} · <span lang="zh-CN">{esc(etitle.get(n, ""))}</span></a> (Chinese)'
    src = " · ".join(src1(n) for n in q["entries"])
    cites = [f"{BASE}entries/{n}.html" if zh or n not in EN_TITLE else f"{BASE}entries/en/{n}.html" for n in q["entries"]]
    rel = [BYID[r] for r in q.get("related", []) if r in BYID and r != q["id"]]
    rel_html = "".join(f'<li><a href="{r["slug"]}.html">{esc(r["q_zh"] if zh else r["q_en"])}</a></li>' for r in rel)
    tops = [TOPICS[t] for t in q.get("topics", []) if t in TOPICS]
    tops_html = " · ".join(f'<a href="{up}topics/{t["slug"]}.html">{esc(t["name"] if zh else t["name_en"])}</a>' for t in tops if os.path.exists(os.path.join(SRC, "topics", t["slug"] + ".html")))
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": ["WebPage", "FAQPage"], "@id": url, "url": url, "name": title, "headline": title, "description": desc, "inLanguage": "zh-CN" if zh else "en",
         "datePublished": date, "dateModified": updated, "isPartOf": {"@id": f"{BASE}#blog"}, "author": {"@id": f"{BASE}#cynthia"},
         "about": [{"@type": "Organization", "name": t["name_en"] if not zh else t["name"], "url": t.get("url", "")} if t.get("url") else {"@type": "Thing", "name": t["name_en"] if not zh else t["name"]} for t in tops],
         "citation": cites,
         "speakable": {"@type": "SpeakableSpecification", "cssSelector": ["h1.aw-h1", ".aw-lead"]},
         "mainEntity": [{"@type": "Question", "@id": f"{url}#q", "name": title, "dateCreated": date, "author": {"@id": f"{BASE}#cynthia"},
                         "acceptedAnswer": {"@type": "Answer", "text": answer_txt, "dateCreated": date, **({"dateModified": updated} if updated != date else {}),
                                            "url": url, "author": {"@id": f"{BASE}#cynthia"}, "citation": cites}}]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "倩小虾日记" if zh else "The ClawQ Chronicles", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": "问答" if zh else "Q&A", "item": BASE + ("answers/" if zh else "answers/en/")},
            {"@type": "ListItem", "position": 3, "name": title, "item": url}]},
        PERSON, BLOG]}
    L = {"lead": "", "judg": "判断" if zh else "Judgment", "facts": "事实" if zh else "Facts", "land": "落点" if zh else "What to do", "fals": "证伪口（逐字取自日记尾注）" if zh else "Falsifier (verbatim from the diary footnote)",
         "status": "台账状态" if zh else "Ledger status", "src": "原文" if zh else "Source entries", "rel": "相关问题" if zh else "Related questions", "topics": "主题页" if zh else "Topic pages (Chinese)",
         "judged": "判断日期" if zh else "Judged", "who": "提问者" if zh else "Asked by", "home": "首页" if zh else "Home", "qa": "问答" if zh else "Q&A"}
    who = q.get("persona", "") if zh else {"投资人": "Investor", "创业者": "Founder"}.get(q.get("persona_group"), "")
    T = (lambda h: h) if zh else zh_spans
    lead_html = (f'<span class="aw-verdict">{T(esc(vline))}</span><br /> <span class="aw-orig">{T(esc(orig))}</span>' if vline else T(esc(orig)))
    sections = []
    if judg: sections.append(f'  <h2 class="aw-h2">{L["judg"]}</h2>\n  <p class="aw-p">{esc(judg)}</p>')
    if facts: sections.append(f'  <h2 class="aw-h2">{L["facts"]}</h2>\n  <p class="aw-p">{esc(facts)}</p>')
    if land: sections.append(f'  <h2 class="aw-h2">{L["land"]}</h2>\n  <p class="aw-p">{esc(land)}</p>')
    if fals: sections.append(f'  <h2 class="aw-h2">{L["fals"]}</h2>\n  <div class="aw-falsify">{esc(fals)}</div>' + (f'\n  <div class="aw-status">{L["status"]}{C}{status_h}</div>' if status else ""))
    elif status: sections.append(f'  <div class="aw-status">{L["status"]}{C}{status_h}</div>')
    mod = f'<meta property="article:modified_time" content="{updated}" />' if updated != date else ""
    rel_div = ('  <div class="aw-rel">' + L["rel"] + C + '<ul>' + rel_html + '</ul></div>') if rel_html else ''
    top_div = ('  <div class="aw-rel">' + L["topics"] + C + tops_html + '</div>') if tops_html else ''
    ulab = ("台账更新" if zh else "Ledger updated") if ukind == "ledger" else ("更新" if zh else "Updated")
    upd_meta = (f' · {ulab} <time datetime="{updated}">{updated}</time>') if updated != date else ''
    return f"""<!DOCTYPE html>
<html lang="{'zh-CN' if zh else 'en'}">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)} · {'倩小虾日记' if zh else 'The ClawQ Chronicles'}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="alternate" hreflang="{'zh-CN' if zh else 'en'}" href="{url}" /><link rel="alternate" hreflang="{'en' if zh else 'zh-CN'}" href="{alt}" /><link rel="alternate" hreflang="x-default" href="{BASE}answers/{q['slug']}.html" />
  <meta name="robots" content="index,follow,max-snippet:-1" />
  <meta property="og:type" content="article" /><meta property="og:title" content="{esc(title)}" /><meta property="og:description" content="{esc(desc)}" /><meta property="og:url" content="{url}" /><meta property="og:image" content="{BASE}assets/clawq-banner.jpg" />
  <meta property="article:published_time" content="{date}" />{mod}<meta name="author" content="张倩 Cynthia Zhang" />
{head_links(depth)}
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="aw-wrap">
  {nav(zh, depth, alt_rel)}
  <div class="aw-crumb"><a href="{up}">{L["home"]}</a> › <a href="./">{L["qa"]}</a> › {esc(title[:40])}</div>
  <h1 class="aw-h1">{esc(title)}</h1>
  <div class="aw-meta">{L["who"]}{C}{esc(who)} · {L["judged"]} <time datetime="{date}">{date}</time>{upd_meta} · 张倩 Cynthia Zhang · FutureX Capital</div>
  <p class="aw-lead">{lead_html}</p>
{chr(10).join(sections)}
  <div class="aw-disc">{esc(disclosure(q, zh))}</div>
  <div class="aw-src">{L["src"]}{C}{src}</div>
{rel_div}
{top_div}
  <footer class="aw-foot">张倩 Cynthia Zhang · 天际资本 FutureX Capital · {'本日记不构成对任何基金产品的推介或募集要约；数字与原文逐字一致，判断的验证状态以判断台账为准。' if zh else 'Nothing here is an offer or solicitation for any fund product; numbers match the source entry verbatim, and verification status lives in the ledger.'}</footer>
</div>
<script src="{up}assets/js/tracker.js?v=4" defer></script>
</body>
</html>
"""

def index_page(zh):
    depth = 1 if zh else 2; up = "../" * depth
    url = BASE + ("answers/" if zh else "answers/en/"); alt = BASE + ("answers/en/" if zh else "answers/")
    items = [q for q in Q if q.get("lead_zh" if zh else "lead_en")]
    groups = [("投资人", "投资人 · 估值、退出、算力合同、份额" if zh else "Investors · valuation, exits, compute contracts, share"),
              ("创业者", "创业者 · 定价、融资、算力采购、合规、选型" if zh else "Founders · pricing, fundraising, compute, compliance, model choice")]
    upd = {q["id"]: page_updated(q) for q in items}
    T = (lambda h: h) if zh else zh_spans
    def li(q):
        u, uk = upd[q["id"]]
        ul = (" · " + (("台账更新 " if zh else "ledger updated ") if uk == "ledger" else ("更新 " if zh else "updated ")) + u) if u != q.get("date", "") else ""
        vline, orig = lead_parts(q, zh)[:2]      # the full lead, never the cut meta description
        return (f'    <li><a href="{q["slug"]}.html">{esc(q["q_zh"] if zh else q["q_en"])}</a>\n'
                f'      <div class="aw-lp">{T(esc((vline + " " + orig) if vline else orig))}</div>\n'
                f'      <div class="aw-ld">{esc(q.get("date", ""))}{ul} · {" · ".join("ENTRY " + str(n) for n in q["entries"])}</div></li>')
    secs = []
    for key, label in groups:
        qs = [q for q in items if q.get("persona_group") == key]
        if not qs: continue
        secs.append(f'  <h2 class="aw-h2">{esc(label)}</h2>\n  <ul class="aw-list">\n' + "\n".join(li(q) for q in qs) + '\n  </ul>')
    title = f"投资人与 AI 创业者会问的 {len(items)} 个问题" if zh else f"{len(items)} questions investors and AI founders ask"
    desc = ("张倩（FutureX Capital 创始人）用日记里的一手判断回答投资人与 AI 创业者此刻最常问的问题：估值倍数、上市时间表、算力合同、模型定价、网关份额、监管与出海。一题一页，每页带判断日期、证伪口与原文链接。" if zh else
            "Cynthia Zhang (founder, FutureX Capital) answers the questions investors and AI founders ask right now — valuation multiples, IPO timing, compute contracts, model pricing, gateway share, regulation. One page per question, each dated, with its falsifier and a link to the diary entry it comes from.")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": url, "url": url, "name": title, "description": desc, "inLanguage": "zh-CN" if zh else "en", "isPartOf": {"@id": f"{BASE}#blog"}, "author": {"@id": f"{BASE}#cynthia"},
         "dateModified": max([u for u, _ in upd.values()] + [HOLD_UPD]),
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "name": q["q_zh"] if zh else q["q_en"], "url": BASE + (f"answers/{q['slug']}.html" if zh else f"answers/en/{q['slug']}.html")} for i, q in enumerate(items)]}},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "倩小虾日记" if zh else "The ClawQ Chronicles", "item": BASE}, {"@type": "ListItem", "position": 2, "name": "问答" if zh else "Q&A", "item": url}]},
        PERSON, BLOG]}
    intro = ("每条答案都来自某一篇日记的原判断，带日期与链接；数字与原文逐字一致，证伪口逐字取自尾注，判断的验证状态以判断台账为准；原判断之后有对账结论的，答案先写对账结论、再写原判断。本日记由 Claude 系工具写作与核实，涉及 Anthropic 的答案请打折读。利益披露：" + "；".join(HL.portfolio(HOLD, True)) + "。" if zh else
             "Every answer is the judgment of one diary entry, dated and linked; numbers match the source verbatim, falsifiers are copied from the footnotes, and verification status lives in the ledger; where a later ledger reconciliation exists, the answer opens with it and then gives the original call. This diary is written and verified with Claude; discount answers touching Anthropic. Disclosure: " + ". ".join(HL.portfolio(HOLD, False)) + ".")
    return f"""<!DOCTYPE html>
<html lang="{'zh-CN' if zh else 'en'}">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)} · {'倩小虾日记' if zh else 'The ClawQ Chronicles'}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="alternate" hreflang="{'zh-CN' if zh else 'en'}" href="{url}" /><link rel="alternate" hreflang="{'en' if zh else 'zh-CN'}" href="{alt}" /><link rel="alternate" hreflang="x-default" href="{BASE}answers/" />
  <meta name="robots" content="index,follow,max-snippet:-1" />
  <meta property="og:type" content="website" /><meta property="og:title" content="{esc(title)}" /><meta property="og:description" content="{esc(desc)}" /><meta property="og:url" content="{url}" /><meta property="og:image" content="{BASE}assets/clawq-banner.jpg" />
{head_links(depth)}
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="aw-wrap">
  {nav(zh, depth, 'en/' if zh else '../')}
  <h1 class="aw-h1">{esc(title)}</h1>
  <p class="aw-p" style="margin-bottom:22px">{esc(intro)}</p>
{chr(10).join(secs)}
  <footer class="aw-foot">张倩 Cynthia Zhang · 天际资本 FutureX Capital · {'本日记不构成对任何基金产品的推介或募集要约。' if zh else 'Nothing here is an offer or solicitation for any fund product.'}</footer>
</div>
<script src="{up}assets/js/tracker.js?v=4" defer></script>
</body>
</html>
"""

for q in Q:
    disclosure(q, True)               # collects PENDING before anything is written
    miss = named_not_disclosed(q)
    if miss: WARN.append(f"DISCLOSURE {q['id']}: the text names {', '.join(miss)} but its disclosure does not — add to entities if it is the company")
if PENDING:
    for qid, nme in PENDING: print(f"PENDING disclosure {qid}: {nme}")
    if STRICT_DISC: print("--strict-disclosure: the companies above are not in holdings.json"); sys.exit(1)
OUT = {}
for q in Q:
    OUT[f"answers/{q['slug']}.html"] = page(q, True); OUT[f"answers/en/{q['slug']}.html"] = page(q, False)
OUT["answers/index.html"] = index_page(True); OUT["answers/en/index.html"] = index_page(False)
# llms.txt Q&A index: its own <!-- gen:answers --> block (scripts/llms_sections.py), one line per question with both URLs, the
# question as the page title, the same dates as the index page and each cited entry's status from data/ledger.json
SYM = {"verified": "✓", "corrected": "✗", "partly": "◐", "open": "⏳"}
def llms_line(q):
    u, uk = page_updated(q)
    when = q.get("date", "") + ((" · " + ("台账更新 " if uk == "ledger" else "更新 ") + u) if u != q.get("date", "") else "")
    st = []
    for n in q["entries"]:
        c = LEDGER.get(n)
        st.append(f"ENTRY {n}" + ((f" {SYM[c['status']]}" + ("（补记）" if c.get("backfill") else "")) if c else ""))
    return (f"- [{q['q_zh']}]({BASE}answers/{q['slug']}.html) · [{q['q_en']}]({BASE}answers/en/{q['slug']}.html)"
            f" — {when} · {' · '.join(st)}")
LLMS = None
if os.path.exists(os.path.join(ROOT, "llms.txt")):
    _llq = [q for q in Q if q.get("lead_zh")]
    _llb = [f"## 问答索引 Q&A index\n\n{len(_llq)} 个投资人与 AI 创业者会问的问题，一题一页，中文与英文各一个 URL，链接文字照抄页面上的问题。"
            "每行之后：判断日（「台账更新 / 更新」日期与问答总索引页一致）· 所引日记及其在判断台账里的当前状态（✓ 已验证 / ✗ 已公开修正 / "
            "◐ 部分成立 / ⏳ 进行中，取自 data/ledger.json；「补记」为事后补记、单独计数；不在台账的只列编号）。"
            f"总索引 [answers/]({BASE}answers/) · [answers/en/]({BASE}answers/en/)，站点地图 [sitemap-answers.xml]({BASE}sitemap-answers.xml)。"]
    for key, label in (("投资人", "### 投资人 Investors"), ("创业者", "### 创业者 Founders")):
        qs = [q for q in _llq if q.get("persona_group") == key]
        if qs: _llb.append(label + "\n" + "\n".join(llms_line(q) for q in qs))
    LLMS = "\n\n".join(_llb)
else: WARN.append("llms.txt not found — Q&A index not written")
# output guard, before anything is written: no banned disclosure phrase in any rendered page (a clause quoted verbatim from
# ENTRY 131–139 is exempt)
ORIG = " ".join(plain(eblk.get(n, "")) for n in range(131, 140))
bad = [(f, h) for f, s in list(OUT.items()) + [("llms.txt <!-- gen:answers -->", LLMS or "")] for h in HL.banned_hits(plain(s), ORIG)]
for f, h in bad: print(f"  ✗ banned phrase in {f}: {h}")
if bad:
    for w in WARN: print("WARN " + w)
    print("gen-answers FAILED: banned disclosure phrase in output — nothing written"); sys.exit(1)
for f, s in OUT.items(): wr(f, s)
if LLMS is not None:
    _ll = rd("llms.txt"); _ll2 = LS.put(_ll, "answers", LLMS, before=("<!-- gen:topics -->", "\n## 引用规范"))
    if _ll2 != _ll: wr("llms.txt", _ll2)
LM = {q["id"]: page_updated(q)[0] for q in Q}
last = max(list(LM.values()) + [HOLD_UPD])
urls = [(f"{BASE}answers/", last, "0.9"), (f"{BASE}answers/en/", last, "0.8")]
for q in Q:
    lm = LM[q["id"]] or last
    urls += [(f"{BASE}answers/{q['slug']}.html", lm, "0.8"), (f"{BASE}answers/en/{q['slug']}.html", lm, "0.7")]
wr("sitemap-answers.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
   "".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod><changefreq>weekly</changefreq><priority>{p}</priority></url>\n" for u, d, p in urls) + "</urlset>\n")
rb = rd("robots.txt")
if "sitemap-answers.xml" not in rb and "sitemap-index.xml" not in rb: wr("robots.txt", rb.rstrip("\n") + f"\nSitemap: {BASE}sitemap-answers.xml\n")
for w in WARN: print("WARN " + w)
if REVIEWED: print(f"reviewed newer notes kept out of the lead (notes_reviewed): {', '.join(REVIEWED)}")
print(f"{'DRY RUN in ' + ROOT if DRY else 'OK'} · questions {len(Q)} · pages {2*len(Q)+2} · fidelity problems {len(problems)}{' (bypassed)' if problems and not VERIFY else ''}")
