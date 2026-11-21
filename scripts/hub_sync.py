#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub sync (2026-11-21): the public statements of the diary's size and of the ledger's status, kept equal to the data.

Two kinds of edits, both idempotent and anchored (an anchor that is not found changes nothing):
  1. Count spans (sync_counts): Day and entry count measured from index.html (title 「倩小虾日记 · Day N」, the number of
     <div id="entry-N">, the newest entry's datePublished) are written into the hero / stats / FAQ / press spans listed in
     COUNT_RULES, and Blog.dateModified is raised (never lowered) to the newest entry. These are the spans buildN.py does
     not bump itself (en hero 「DAY N」, en 「Public entries written」, press kit Day/entry lines, dated 「截至 … 已发布 N 篇」).
  2. FAQ correction pointers (faq_sync): an index.html / en.html / ja.html FAQPage answer that restates a call the ledger
     now marks ✗ or ◐ (or whose sub-claim a reconciliation judged wrong) gets a dated pointer to the ledger card appended;
     the answer's own text is never rewritten (「不改原文、喂 HEAD」). Which call an answer restates:
       a. 「ENTRY N」 in the answer's lead (text before the first 「：」 / ": ");
       b. else the lead's date (「事件日 DATE」 first) when exactly one entry carries that date in index.html;
       c. data/ledger-overrides.json "faq_calls" {file: {question: [N…]}} replaces a/b for that question (ambiguous dates);
       d. plus any call whose retracted / judged-wrong wording (data/ledger.json) appears verbatim in the answer.
     A historical scorecard (「N 条挂账判断」, "N ledgered calls") gets a dated 「台账现状」 pointer with today's counts, and
     NUMBER_FIXES appends a number correction quoted from an existing English page (never machine-translated).
     A pointer already present is refreshed in place (matched by its call id), so a later status change updates it.
Callers: scripts/gen-ledger.py (writes, every run) and scripts/geo-optimize.py (A3 count fixes; C7 warns when a pointer is
missing). Deterministic, no I/O (file contents are passed in). Not a CLI.
"""
import re, json

BASE = "https://cynthia-git11.github.io/clawq-diary/"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# ---------------- site state (measured from index.html) ----------------
def site_state(idx):
    n_ids = [int(x) for x in re.findall(r'<div id="entry-(\d+)"', idx)]
    latest = max(n_ids)
    dm = re.search(r"倩小虾日记 · Day (\d+)", idx)
    pm = re.search(r'#entry-%d",\s*"datePublished":\s*"([^"]+)"' % latest, idx) or re.search(r'"datePublished": "([^"]+)"', idx)
    if not (dm and pm): raise ValueError("index.html: Day in <title> or the newest datePublished not found")
    return dict(entries=len(n_ids), latest_entry=latest, day=int(dm.group(1)), latest_iso=pm.group(1), latest=pm.group(1)[:10])

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
    ],
    "en.html": [
        ("hero DAY", r'<div class="mag-tag">DAY \d+</div>', lambda s: f'<div class="mag-tag">DAY {s["day"]}</div>'),
        ("stat Public entries written", r'<div class="stat-val claw-text">\d+</div><div class="stat-lbl">Public entries written</div>',
         lambda s: f'<div class="stat-val claw-text">{s["entries"]}</div><div class="stat-lbl">Public entries written</div>'),
    ],
    "ja.html": [
        ("FAQ 時点で N 篇", r"\d{4} 年 \d{1,2} 月 \d{1,2} 日時点で \d+ 篇", lambda s: f"{_cn_date(s['latest'])}時点で {s['entries']} 篇"),
    ],
    "theses.html": [   # buildN.py replaces exactly 「Day {prev Day}、{prev N} 篇」 once: keep it equal to index.html
        ("lede Day、N 篇", r"这本日记写到 Day \d+、\d+ 篇", lambda s: f"这本日记写到 Day {s['day']}、{s['entries']} 篇"),
    ],
    "press.html": [
        ("Last updated", r"Last updated \d{4}\.\d{2}\.\d{2} · Day \d+", lambda s: f"Last updated {s['latest'].replace('-', '.')} · Day {s['day']}"),
        ("fact sheet", r"· Day \d+ · \d+ 篇", lambda s: f"· Day {s['day']} · {s['entries']} 篇"),
        ("bio 目前写到", r"目前(?:已连续记录 \d+ 天|写到 Day \d+)、\d+ 篇真实判断", lambda s: f"目前写到 Day {s['day']}、{s['entries']} 篇真实判断"),
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
        elif m.group(2)[:10] < st["latest"]:
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
# existing pointers, by call id (so a refresh replaces the right one); none of the templates below nest parentheses
PTR_RE = {"zh": re.compile(r"（[^（）]*?见[^（）]*?theses\.html#call-(\d+)）"),
          "en": re.compile(r" ?\([^()]*?; see theses-en\.html#call-(\d+)\)"),
          "ja": re.compile(r"（[^（）]*?判断台帳 theses\.html#call-(\d+) を参照）")}
AGG_RE = {"zh": re.compile(r"\d+ (?:条挂账判断|个重大判断)"), "en": re.compile(r"\d+ (?:ledgered calls|major calls)")}
AGG_PTR = {"zh": re.compile(r"（台账现状 \d{4}-\d{2}-\d{2}：[^（）]*?见判断台账 theses\.html）"),
           "en": re.compile(r" ?\(Ledger status as of \d{4}-\d{2}-\d{2}: [^()]*?; see theses-en\.html\)")}

def qualifies(c):
    """a call an answer restates gets a pointer when the ledger marks it ✗ or ◐; an open call whose sub-claim was judged wrong
    gets one only where the answer quotes that sub-claim verbatim (rule d)"""
    return c["status"] in ("corrected", "partly")

def pointer(lang, c):
    n = c["entry"]; k = c.get("correction_entry"); st = c["status"]
    d = c.get("corrected_on") if st == "corrected" else c.get("reconciled")
    sub = c.get("subclaim_judged_wrong")
    if lang == "zh":
        if st == "corrected":
            if k and d: return f"（{d} 已认错，见 ENTRY {k} 与判断台账 theses.html#call-{n}）"
            return f"（{d + ' 对账：' if d else ''}已认错，见判断台账 theses.html#call-{n}）"
        if st == "partly": return f"（{d + ' 对账：' if d else ''}部分成立，见判断台账 theses.html#call-{n}）"
        return f"（{d + ' 对账：' if d else ''}其中「{sub}」判错，卡片仍为进行中，见判断台账 theses.html#call-{n}）"
    if lang == "en":
        if st == "corrected": return f" (Corrected on {d}{' in ENTRY %d' % k if k else ''}; see theses-en.html#call-{n})" if d else f" (Publicly corrected; see theses-en.html#call-{n})"
        if st == "partly": return f" (Partly right as of {d}; see theses-en.html#call-{n})" if d else f" (Partly right; see theses-en.html#call-{n})"
        return f" (A sub-claim was judged wrong{' on ' + d if d else ''}; the call stays open; see theses-en.html#call-{n})"
    if st == "corrected": return f"（{d + ' 時点で' if d else ''}公開訂正。判断台帳 theses.html#call-{n} を参照）"
    if st == "partly": return f"（{d + ' 時点で' if d else ''}一部成立。判断台帳 theses.html#call-{n} を参照）"
    return f"（{d + ' 時点で' if d else ''}一部の判断が誤り、判断は進行中。判断台帳 theses.html#call-{n} を参照）"

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

def _insert(raw, lang, ptr):
    """append ptr to a JSON-escaped answer string, before a trailing fund disclaimer if there is one"""
    enc = json.dumps(ptr, ensure_ascii=False)[1:-1]
    for d in DISC_TAIL[lang]:
        de = json.dumps(d, ensure_ascii=False)[1:-1]
        if raw.endswith(de):
            head = raw[:-len(de)]
            if lang == "en": return head.rstrip() + enc + " " + de
            return head + enc.lstrip() + de
    return raw.rstrip() + enc if lang == "en" else raw + enc.lstrip()

def faq_sync(name, text, calls, stats, updated, dates, overrides=None, num_rules=()):
    """→ (text, actions, warns). calls: data/ledger.json rows (or gen-ledger's in-memory rows with the same fields)."""
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
        want = []
        if q in ov: want = list(ov[q])
        else:
            ld = lead_of(t, lang)
            if ld and ld[0] == "entry": want = [ld[1]]
            elif ld and ld[0] == "date":
                cand = by_date.get(ld[1], [])
                if len(cand) == 1: want = cand
                elif any(n in C and qualifies(C[n]) for n in cand):
                    warns.append(f"{name}: 「{q[:30]}」 lead date {ld[1]} has entries {sorted(cand)} — add it to data/ledger-overrides.json faq_calls")
        want = {n for n in want if n in C and qualifies(C[n])} | {n for n, p in phr if p in t}
        want = sorted(want)
        new = raw
        for n in want:
            ptr = pointer(lang, C[n]); enc = json.dumps(ptr, ensure_ascii=False)[1:-1]
            old = [x for x in PTR_RE[lang].finditer(new) if int(x.group(1)) == n]
            if old:
                if old[0].group(0).strip() != enc.strip():
                    new = new[:old[0].start()] + (enc if lang == "en" else enc.lstrip()) + new[old[0].end():]; acts.append(f"refresh call-{n} · {q[:24]}")
            else:
                new = _insert(new, lang, ptr); acts.append(f"add call-{n} · {q[:24]}")
        for x in PTR_RE[lang].finditer(new):
            if int(x.group(1)) not in want: warns.append(f"{name}: 「{q[:30]}」 carries a pointer to call-{x.group(1)} that no longer applies — check by hand")
        if lang in AGG_RE and AGG_RE[lang].search(AGG_PTR[lang].sub("", t)):
            ap = json.dumps(agg_pointer(lang, stats, updated), ensure_ascii=False)[1:-1]
            om = AGG_PTR[lang].search(new)
            if not om: new = _insert(new, lang, agg_pointer(lang, stats, updated)); acts.append(f"add 台账现状 · {q[:24]}")
            elif om.group(0).strip() != ap.strip():
                new = new[:om.start()] + (ap if lang == "en" else ap.lstrip()) + new[om.end():]; acts.append(f"refresh 台账现状 · {q[:24]}")
        for r in num_rules:
            if r["file"] == name and r["token"] in t and r["marker"] not in t:
                d = dates.get(r["entry"], "")
                if d: new = _insert(new, lang, r["text"].format(d=d)); acts.append(f"add number fix ENTRY {r['entry']} · {q[:24]}")
        if new != raw:
            out.append(body[pos:m.start(2)] + new); pos = m.end(2)
    for q in ov:
        if q not in seen_q and not q.startswith("_"): warns.append(f"{name}: faq_calls override question not found: 「{q[:40]}」")
    if not out: return text, acts, warns
    body2 = "".join(out) + body[pos:]
    json.loads(body2)
    return text[:blk.start(1)] + body2 + text[blk.end(1):], acts, warns

def faq_answers(name, text):
    """[(question, answer)] of the page's FAQPage block (for checks)"""
    blk = next((m for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.S) if '"FAQPage"' in m.group(1)), None)
    return [(json.loads('"' + a + '"'), json.loads('"' + b + '"')) for a, b in QA_RE.findall(blk.group(1))] if blk else []
