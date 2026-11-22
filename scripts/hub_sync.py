#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub sync (2026-11-21): the public statements of the diary's size and of the ledger's status, kept equal to the data.

Three kinds of edits, all idempotent and anchored (an anchor that is not found changes nothing):
  1. Count spans (sync_counts): Day and entry count measured from index.html (title 「倩小虾日记 · Day N」, the number of
     <div id="entry-N">, the newest entry's date line) are written into the hero / stats / FAQ / press spans listed in
     COUNT_RULES, and Blog.dateModified is raised (never lowered) to the newest entry's datePublished (for a backfill, its
     written date). These are the spans buildN.py does not bump itself (en hero 「DAY N」, en 「Public entries written」,
     press kit Day/entry lines, dated 「截至 … 已发布 N 篇」).
  2. FAQ correction pointers (faq_sync): an index.html / en.html / ja.html FAQPage answer that restates a call the ledger
     now marks ✗ or ◐ (or whose sub-claim a reconciliation judged wrong) gets a dated pointer to the ledger card that names
     the call's own ENTRY, placed before the answer's 「利益披露：」 / "Disclosure:" segment (else before the fund disclaimer,
     else at the end); the answer's own text is never rewritten (「不改原文、喂 HEAD」). Which call an answer restates:
       a. 「ENTRY N」 in the answer's lead (text before the first 「：」 / ": ");
       b. else the lead's date (「事件日 DATE」 first) when exactly one entry carries that date in index.html;
       c. data/ledger-overrides.json "faq_calls" {file: {question: [N…]}} replaces a/b for that question (ambiguous dates);
       d. plus any call whose retracted / judged-wrong wording (data/ledger.json) appears verbatim in the answer.
     A historical scorecard (「N 条挂账判断」, "N ledgered calls") gets a dated 「台账现状」 pointer with today's counts, and
     number_fixes() adds a number correction quoted from an existing English page (never machine-translated).
     Every pointer an answer already carries is regenerated from its call's current status (✗ / ◐ / ✓ / ⏳ templates) and
     put back at the anchor, so a later status change, including one to ✓ or ⏳, updates it (geo-check check 9 compares the
     status word with data/ledger.json).
  3. Entry-row number notes (row_fixes): the en.html entry row that states a number a later entry corrected gets the same
     dated note right after that sentence (gen-entries-en.py carries it to entries/en/<N>.html).
Callers: scripts/gen-ledger.py (writes, every run), scripts/geo-optimize.py (A3 count fixes; C7 warns when a pointer is
missing or stale) and scripts/geo-check.py (check 9). Deterministic, no I/O (file contents are passed in). Not a CLI.
"""
import re, json

BASE = "https://cynthia-git11.github.io/clawq-diary/"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# ---------------- site state (measured from index.html) ----------------
def site_state(idx):
    """latest: the newest entry's date line (its event date, the date its Day counts — the visible 「截至 DATE（Day N）」 /
    "Last updated DATE · Day N" spans pair the two); latest_iso: its @graph datePublished, which for a backfill (补记) is the written
    date (scripts/machine_dates.py) — only the machine Blog.dateModified is raised to it. Same value for a non-backfill."""
    n_ids = [int(x) for x in re.findall(r'<div id="entry-(\d+)"', idx)]
    latest = max(n_ids)
    dm = re.search(r"倩小虾日记 · Day (\d+)", idx)
    pm = re.search(r'#entry-%d",\s*"datePublished":\s*"([^"]+)"' % latest, idx) or re.search(r'"datePublished": "([^"]+)"', idx)
    if not (dm and pm): raise ValueError("index.html: Day in <title> or the newest datePublished not found")
    ev = entry_dates(idx).get(latest) or pm.group(1)[:10]
    return dict(entries=len(n_ids), latest_entry=latest, day=int(dm.group(1)), latest_iso=pm.group(1), latest=ev)

def entry_dates(idx):
    """{N: event date YYYY-MM-DD} from each entry's date line in index.html"""
    out = {}
    for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>\s*<div class="entry-date">\s*(\d{4})年(\d{1,2})月(\d{1,2})日', idx):
        out[int(m.group(1))] = f"{m.group(2)}-{int(m.group(3)):02d}-{int(m.group(4)):02d}"
    return out

# ---------------- 1. count spans ----------------
def _cn_date(d): return f"{int(d[:4])} 年 {int(d[5:7])} 月 {int(d[8:10])} 日"
COUNT_RULES = {   # file → [(label, regex, replacement(st))]; every regex also matches its own output (idempotent)
    "index.html": [
        ("FAQ 截至…已发布 N 篇", r"截至 \d{4}-\d{2}-\d{2}（Day \d+）已发布 \d+ 篇", lambda s: f"截至 {s['latest']}（Day {s['day']}）已发布 {s['entries']} 篇"),
        ("「你正在这里」卡片", r"不定期更新 · Day \d+ · \d+ 篇</div>", lambda s: f"不定期更新 · Day {s['day']} · {s['entries']} 篇</div>"),
    ],
    "en.html": [
        ("hero DAY", r'<div class="mag-tag">DAY \d+</div>', lambda s: f'<div class="mag-tag">DAY {s["day"]}</div>'),
        ("stat Public entries written", r'<div class="stat-val claw-text">\d+</div><div class="stat-lbl">Public entries written</div>',
         lambda s: f'<div class="stat-val claw-text">{s["entries"]}</div><div class="stat-lbl">Public entries written</div>'),
    ],
    "ja.html": [
        ("FAQ 時点で N 篇", r"\d{4} 年 \d{1,2} 月 \d{1,2} 日時点で \d+ 篇", lambda s: f"{_cn_date(s['latest'])}時点で {s['entries']} 篇"),
    ],
    "theses.html": [   # buildN.py replaces exactly 「Day {PREV_DAY}、{PREV_N} 篇」 once, PREV_N = the newest ENTRY number (not the div count)
        ("lede Day、N 篇", r"这本日记写到 Day \d+、\d+ 篇", lambda s: f"这本日记写到 Day {s['day']}、{s['latest_entry']} 篇"),
    ],
    "press.html": [
        ("Last updated", r"Last updated \d{4}\.\d{2}\.\d{2} · Day \d+", lambda s: f"Last updated {s['latest'].replace('-', '.')} · Day {s['day']}"),
        ("fact sheet", r"· Day \d+ · \d+ 篇", lambda s: f"· Day {s['day']} · {s['entries']} 篇"),
        ("bio 目前写到", r"目前(?:已连续记录 \d+ 天|写到 Day \d+)、\d+ 篇真实判断", lambda s: f"目前写到 Day {s['day']}、{s['entries']} 篇真实判断"),
        # cadence wording as press-en.html's one-liner ("aperiodic — updated when there's a call worth making") and index.html
        ("bio cadence", r"起(?:每天写一本公开日记|公开写一本投资日记（不定期更新、有判断才写）)，记录天际",
         lambda s: "起公开写一本投资日记（不定期更新、有判断才写），记录天际"),
        ("long bio 目前写到 Day N", r"起(?:每天公开发布一篇投资日记《倩小虾日记》，已连续记录 \d+ 天|公开发布投资日记《倩小虾日记》（不定期更新、有判断才写），目前写到 Day \d+)。",
         lambda s: f"起公开发布投资日记《倩小虾日记》（不定期更新、有判断才写），目前写到 Day {s['day']}。"),
        # cadence wording as on index.html / 404.html (2026-06-14 起不定期更新)
        ("footer", r"(The ClawQ Chronicles</a> · )Day \d+ · (?:持续更新中|不定期更新、有判断才写)( 🦞)", lambda s: rf"\g<1>Day {s['day']} · 不定期更新、有判断才写\g<2>"),
    ],
    "press-en.html": [
        ("Last updated", r"Last updated \d{4}\.\d{2}\.\d{2} · Day \d+", lambda s: f"Last updated {s['latest'].replace('-', '.')} · Day {s['day']}"),
        ("fact sheet", r"· Day \d+ · \d+ entries", lambda s: f"· Day {s['day']} · {s['entries']} entries"),
        ("bio currently Day N, N entries", r"currently <strong>Day \d+, \d+ entries</strong>", lambda s: f"currently <strong>Day {s['day']}, {s['entries']} entries</strong>"),
        ("bio currently on Day N", r"currently on Day \d+\.", lambda s: f"currently on Day {s['day']}."),
        # cadence wording as on en.html's footer ("updated when it matters") — the diary has not been daily since 2026-06-14
        ("footer", r"(The ClawQ Chronicles</a> · )Day \d+ · (?:auto-updated daily|updated when it matters)( 🦞)", lambda s: rf"\g<1>Day {s['day']} · updated when it matters\g<2>"),
    ],
}
BLOG_DM = ("index.html", "en.html", "ja.html")

def sync_counts(name, text, st):
    """→ (text, changed labels, missing labels)"""
    changed, missing = [], []
    for label, rx, rep in COUNT_RULES.get(name, []):
        new, k = re.subn(rx, rep(st), text)
        if not k: missing.append(label)
        elif new != text: changed.append(label); text = new
    if name in BLOG_DM:
        m = re.search(r'("@type": "Blog",(?:(?!"@type")[\s\S])*?"dateModified": ")([^"]+)(")', text)
        if not m: missing.append("Blog.dateModified")
        elif m.group(2)[:10] < st["latest_iso"][:10]:
            text = text[:m.start(2)] + st["latest_iso"] + text[m.end(2):]; changed.append("Blog.dateModified")
    return text, changed, missing

# ---------------- 2. FAQ correction pointers ----------------
QA_RE = re.compile(r'"name":\s*"((?:[^"\\]|\\.)*)",\s*"acceptedAnswer":\s*\{\s*"@type":\s*"Answer",\s*"text":\s*"((?:[^"\\]|\\.)*)"')
LANG = {"index.html": "zh", "en.html": "en", "ja.html": "ja"}
TRACK_Q = {"张倩的公开判断 track record 怎么样？哪里可以核验？", "What is Cynthia Zhang's public track record and where can it be verified?",
           "張倩の実績はどこで検証できますか？"}   # kept current by gen-ledger.py itself
DISC_TAIL = {"zh": ["本日记不构成对任何基金产品的推介或募集要约。"],
             "en": ["This diary does not constitute the promotion of, or an offer to subscribe to, any fund product.",
                    "This diary does not constitute promotion of, or an offer to subscribe for, any fund product."],
             "ja": ["本日記はいかなるファンド商品の勧誘・募集の申出も構成しない。"]}
# the answer's own conflict-of-interest disclosure (every buildN answer since 2026-09-25 ends with one): pointers go before it,
# so a ledger status never reads as a verdict on a holding or a customer relationship
DISC_SEG = {"zh": ["利益披露："], "en": ["Disclosure:"], "ja": []}
# existing pointers, by call id (so a refresh replaces the right one); none of the templates below nest parentheses
PTR_RE = {"zh": re.compile(r"（[^（）]*?见[^（）]*?theses\.html#call-(\d+)）"),
          "en": re.compile(r" ?\([^()]*?; see theses-en\.html#call-(\d+)\)"),
          "ja": re.compile(r"（[^（）]*?判断台帳 theses\.html#call-(\d+) を参照）")}
# the status word each template carries (geo-check check 9 compares it with data/ledger.json); quoted 「…」 sub-claims excluded
STATUS_WORD = {"zh": {"corrected": "已认错", "partly": "部分成立", "verified": "已验证", "open": "进行中"},
               "en": {"corrected": "corrected", "partly": "partly right", "verified": "verified", "open": "open"},
               "ja": {"corrected": "公開訂正", "partly": "一部成立", "verified": "検証済み", "open": "進行中"}}
AGG_RE = {"zh": re.compile(r"\d+ (?:条挂账判断|个重大判断)"), "en": re.compile(r"\d+ (?:ledgered calls|major calls)")}
AGG_PTR = {"zh": re.compile(r"（台账现状 \d{4}-\d{2}-\d{2}：[^（）]*?见判断台账 theses\.html）"),
           "en": re.compile(r" ?\(Ledger status as of \d{4}-\d{2}-\d{2}: [^()]*?; see theses-en\.html\)")}
NUMFIX_RE = re.compile(r" ?\(Number corrected on \d{4}-\d{2}-\d{2} in ENTRY (\d+): [^()]*?; see entries/en/\d+\.html\)")

def qualifies(c):
    """a call an answer restates gets a pointer when the ledger marks it ✗ or ◐, or when a reconciliation judged one of its
    sub-claims wrong while the card stays ⏳ (2026-11-21). A pointer already on an answer is refreshed whatever the status."""
    return c["status"] in ("corrected", "partly") or bool(c.get("subclaim_judged_wrong"))

def status_words(lang, ptr):
    """the status words a pointer carries, quoted 「…」 sub-claims left out"""
    t = re.sub(r"「[^」]*」", "", ptr)
    if lang == "en": return {k for k, w in STATUS_WORD[lang].items() if re.search(r"\b%s\b" % re.escape(w), t, re.I)}
    return {k for k, w in STATUS_WORD[lang].items() if w in t}

def pointer(lang, c, updated=None):
    """dated pointer to the ledger card, naming the call's own ENTRY (so it never reads as a verdict on a neighbouring
    sentence or on another entry). One template per status; dates are ledger fields, never inferred."""
    n = c["entry"]; k = c.get("correction_entry"); st = c["status"]
    d = c.get("corrected_on") if st == "corrected" else c.get("reconciled")
    sub = c.get("subclaim_judged_wrong")
    if lang == "zh":
        h = f"（ENTRY {n} 判断"; tail = f"见判断台账 theses.html#call-{n}）"
        if st == "corrected":
            if k and d: return f"{h} {d} 已认错，见 ENTRY {k} 与判断台账 theses.html#call-{n}）"
            return f"{h}{' ' + d + ' 对账：' if d else ''}已认错，{tail}"
        if st == "partly": return f"{h}{' ' + d + ' 对账：' if d else ''}部分成立{'，其中「%s」判错' % sub if sub else ''}，{tail}"
        if st == "verified": return f"{h}{' ' + d + ' 对账：' if d else ''}已验证，{tail}"
        if sub: return f"{h}{' ' + d + ' 对账：' if d else ''}其中「{sub}」判错，卡片仍为进行中，{tail}"
        return f"{h}{' ' + d + ' 对账：仍在' if d else '截至 %s 仍在' % updated if updated else '仍在'}进行中，{tail}"
    if lang == "en":
        h = f" (ENTRY {n} call"; tail = f"; see theses-en.html#call-{n})"
        if st == "corrected": return f"{h} corrected on {d}{' in ENTRY %d' % k if k else ''}{tail}" if d else f"{h} publicly corrected{tail}"
        if st == "partly": return f"{h} partly right{' as of ' + d if d else ''}{', one sub-claim judged wrong' if sub else ''}{tail}"
        if st == "verified": return f"{h} verified{' on ' + d if d else ''}{tail}"
        if sub: return f"{h} still open; a sub-claim was judged wrong{' on ' + d if d else ''}{tail}"
        return f"{h} still open{' as of ' + (d or updated) if (d or updated) else ''}{tail}"
    h = f"（ENTRY {n} の判断："; tail = f"判断台帳 theses.html#call-{n} を参照）"
    at = f"{d} 時点で" if d else ""
    if st == "corrected": return f"{h}{at}公開訂正。{tail}"
    if st == "partly": return f"{h}{at}一部成立{'、うち一部の判断は誤り' if sub else ''}。{tail}"
    if st == "verified": return f"{h}{at}検証済み。{tail}"
    if sub: return f"{h}{at}一部の判断が誤り、判断は進行中。{tail}"
    return f"{h}{(d or updated) + ' 時点で' if (d or updated) else ''}進行中。{tail}"

def agg_pointer(lang, stats, updated):
    s = stats
    if lang == "zh":
        return (f"（台账现状 {updated}：{s['total']} 个重大判断，{s['verified']} 已验证 / {s['corrected']} 已公开修正 / "
                f"{s['partly']} 部分成立 / {s['open']} 进行中，见判断台账 theses.html）")
    return (f" (Ledger status as of {updated}: {s['total']} calls — {s['verified']} verified, {s['corrected']} publicly corrected, "
            f"{s['partly']} partly right, {s['open']} open; see theses-en.html)")

def number_fixes(read):
    """number corrections quoted from an existing English page; `read(path)` → that page's plain text or None.
    A rule whose quote is not on the page is dropped (and reported), never paraphrased."""
    rules, warns = [], []
    q = "the real move is ¥27→¥100, ~3.7x the old price"
    t = read("entries/en/114.html")
    if t and q in t: rules.append(dict(file="en.html", token="~2.1x", entry=114, marker="see entries/en/114.html)",
                                       text=" (Number corrected on {d} in ENTRY 114: " + q + "; see entries/en/114.html)"))
    else: warns.append("entries/en/114.html: the 3.7x correction sentence not found — ~2.1x pointer not written")
    return rules, warns

def lead_of(text, lang):
    seg = text[:140]
    k = seg.find("：") if lang in ("zh", "ja") else seg.find(": ")
    if k > 0: seg = seg[:k]
    m = re.search(r"ENTRY (\d+)", seg)
    if m: return ("entry", int(m.group(1)))
    m = re.search(r"事件日 (\d{4}-\d{2}-\d{2})", seg) or re.search(r"(\d{4}-\d{2}-\d{2})", seg)
    if m: return ("date", m.group(1))
    m = re.search(r"(%s) (\d{1,2}), (\d{4})" % "|".join(MONTHS), seg)
    if m: return ("date", f"{m.group(3)}-{MONTHS.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}")
    return None

def _anchor(t, lang):
    """where an answer's pointers go: before its own trailing 「利益披露：」 / "Disclosure:" segment, else before a trailing
    fund disclaimer, else at the end"""
    cands = [len(t) - len(d) for d in DISC_TAIL[lang] if t.endswith(d)]
    cands += [i for i in (t.rfind(s) for s in DISC_SEG[lang]) if i > 0]
    return min(cands) if cands else len(t)

def _place(t, lang, group):
    """insert the pointer strings `group` (en ones start with a space) at the answer's anchor"""
    if not group: return t
    i = _anchor(t, lang); head, rest = t[:i], t[i:]
    if lang == "en":
        g = "".join(" " + x.lstrip() for x in group)
        return head.rstrip() + g + (" " + rest.lstrip() if rest else "")
    return head + "".join(group) + rest

def faq_sync(name, text, calls, stats, updated, dates, overrides=None, num_rules=()):
    """→ (text, actions, warns). calls: data/ledger.json rows (or gen-ledger's in-memory rows with the same fields).
    Every pointer an answer carries is regenerated from the call's current status and placed at the answer's anchor
    (_anchor), so a status change, a template change or a misplaced pointer is fixed on the next run; idempotent."""
    lang = LANG[name]; acts, warns = [], []
    blk = next((m for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.S) if '"FAQPage"' in m.group(1)), None)
    if not blk: return text, acts, [f"{name}: FAQPage block not found"]
    C = {c["entry"]: c for c in calls}
    by_date = {}
    for n, d in dates.items(): by_date.setdefault(d, []).append(n)
    phr = [(c["entry"], p) for c in calls for p in (c.get("retracted"), c.get("subclaim_judged_wrong")) if p]
    ov = (overrides or {}).get(name, {})
    seen_q = set()
    body = blk.group(1); out = []; pos = 0
    for m in QA_RE.finditer(body):
        q = json.loads('"' + m.group(1) + '"'); raw = m.group(2); t = json.loads('"' + raw + '"'); seen_q.add(q)
        if q in TRACK_Q: continue
        old = {}
        for x in PTR_RE[lang].finditer(t): old.setdefault(int(x.group(1)), x.group(0))
        old_num = {int(x.group(1)): x.group(0) for x in NUMFIX_RE.finditer(t)} if lang == "en" else {}
        n_acts = len(acts)
        old_agg = AGG_PTR[lang].search(t) if lang in AGG_PTR else None
        base = PTR_RE[lang].sub("", t)
        base = NUMFIX_RE.sub("", base) if lang == "en" else base
        base = AGG_PTR[lang].sub("", base) if lang in AGG_PTR else base
        ld = lead_of(base, lang); primary = ld[1] if ld and ld[0] == "entry" else None
        want = []
        if q in ov: want = list(ov[q])
        elif ld and ld[0] == "entry": want = [ld[1]]
        elif ld and ld[0] == "date":
            cand = by_date.get(ld[1], [])
            if len(cand) == 1: want = cand; primary = cand[0]
            elif any(n in C and qualifies(C[n]) for n in cand):
                warns.append(f"{name}: 「{q[:30]}」 lead date {ld[1]} has entries {sorted(cand)} — add it to data/ledger-overrides.json faq_calls")
        want = {n for n in want if n in C and qualifies(C[n])} | {n for n, p in phr if p in base} | {n for n in old if n in C}
        for n in old:
            if n not in C: warns.append(f"{name}: 「{q[:30]}」 carries a pointer to call-{n}, which is not on the ledger — kept as written")
        order = ([primary] if primary in want else []) + sorted(n for n in want if n != primary)
        group = [pointer(lang, C[n], updated) for n in order] + [old[n] for n in old if n not in C]
        for n in order:
            p = pointer(lang, C[n], updated)
            if n not in old: acts.append(f"add call-{n} · {q[:24]}")
            elif old[n].strip() != p.strip(): acts.append(f"refresh call-{n} · {q[:24]}")
        nums, ruled = [], {r["entry"] for r in num_rules if r["file"] == name}
        for r in num_rules:
            if r["file"] == name and r["token"] in base and r["marker"] not in base and dates.get(r["entry"]):
                nums.append(r["text"].format(d=dates[r["entry"]]))
                if r["entry"] not in old_num: acts.append(f"add number fix ENTRY {r['entry']} · {q[:24]}")
        nums += [o for e, o in old_num.items() if e not in ruled]   # rule unavailable (quote gone from the page): kept as written
        agg = []
        if lang in AGG_RE and AGG_RE[lang].search(base):
            ap = agg_pointer(lang, stats, updated); agg = [ap]
            if not old_agg: acts.append(f"add 台账现状 · {q[:24]}")
            elif old_agg.group(0).strip() != ap.strip(): acts.append(f"refresh 台账现状 · {q[:24]}")
        new_t = _place(base, lang, group + nums + agg)
        if new_t != t:
            if len(acts) == n_acts: acts.append(f"reposition pointers · {q[:24]}")
            out.append(body[pos:m.start(2)] + json.dumps(new_t, ensure_ascii=False)[1:-1]); pos = m.end(2)
    for q in ov:
        if q not in seen_q and not q.startswith("_"): warns.append(f"{name}: faq_calls override question not found: 「{q[:40]}」")
    if not out: return text, acts, warns
    body2 = "".join(out) + body[pos:]
    json.loads(body2)
    return text[:blk.start(1)] + body2 + text[blk.end(1):], acts, warns

# ---------------- 3. number corrections on archived English entry rows (en.html) ----------------
ROW_TITLE_RE = re.compile(r'(<div class="entry-row">\s*<span class="erow-date">[^<]*</span>\s*<span class="erow-title">)(.*?)(</span>\s*<span class="erow-tag">.*?</span>'
                          r'(?:\s*<a class="erow-link" href="entries/en/(\d+)\.html">[^<]*</a>)?\s*</div>)', re.S)

def row_fixes(name, text, num_rules, dates):
    """→ (text, actions). The en.html entry row of an entry whose number a later entry corrected gets the same dated note as
    the FAQ answer, right after the sentence that states the old number (the row text is the published English summary and
    is otherwise left as written; gen-entries-en.py carries the note to entries/en/<N>.html). Idempotent (marker)."""
    acts = []
    for r in num_rules:
        if r["file"] != name or not dates.get(r["entry"]): continue
        note = r["text"].format(d=dates[r["entry"]])
        def fix(m):
            body = m.group(2)
            if r["token"] not in body or r["marker"] in body or m.group(4) == str(r["entry"]): return m.group(0)
            i = body.index(r["token"]); j = body.find(". ", i)
            j = len(body) if j < 0 else j + 1
            acts.append(f"row ENTRY {m.group(4) or '?'}: number fix from ENTRY {r['entry']}")
            return m.group(1) + body[:j] + note + body[j:] + m.group(3)
        text = ROW_TITLE_RE.sub(fix, text)
    return text, acts

def faq_answers(name, text):
    """[(question, answer)] of the page's FAQPage block (for checks)"""
    blk = next((m for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.S) if '"FAQPage"' in m.group(1)), None)
    return [(json.loads('"' + a + '"'), json.loads('"' + b + '"')) for a, b in QA_RE.findall(blk.group(1))] if blk else []
