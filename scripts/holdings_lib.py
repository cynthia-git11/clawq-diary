#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Holdings disclosure sentences for gen-answers.py and gen-topics.py (2026-11-21).

Source: the author's holdings record daily-x/holdings.json (outside the repo; $CLAWQ_HOLDINGS overrides the path).
Only the held / exited / not_held lists are read, and of each row only name, aliases and confirmed; a held row is also
checked for being a fund stake (name or note says fund), and fund stakes are never listed as companies.
scope, note, held_source, lp_relationships and unconfirmed_* are never printed (they are not read into any sentence).
Every sentence comes from the fixed table below; dates are the record's per-company confirmation dates, grouped by date.
A name that is not in the record (or is a fund stake) is returned as pending and nothing is said about holding it:
there is no fallback sentence. A missing record file stops the build instead of printing a fallback.
"""
import os, re, sys, json

DEFAULT = "/Users/cynthiazhang/.claude/projects/-Users-cynthiazhang-Library-Mobile-Documents-com-apple-CloudDocs-----/daily-x/holdings.json"
# phrases that must never appear in a disclosure (geo-check.py keeps its own copy of this list for CI)
BANNED = ["按公开可查信息", "按公开信息无头寸", "本篇未核实", "on publicly available information"]

# topic slug → record names (exact). Policy / IPO / pricing / neocloud / AI-coding / Vercel topics map to nothing here and use
# only the topic's own "entities" list in data/topics.json (no alias full-text matching, so e.g. "Scale" never mis-attaches).
TOPIC_ENTITIES = {"openai": ["OpenAI"], "deepseek": ["DeepSeek"], "moonshot-kimi": ["月之暗面"], "zhipu-glm": ["智谱"],
                  "alibaba-qwen": ["阿里巴巴"], "bytedance-doubao": ["字节跳动"], "meta-muse": ["Meta"], "mistral": ["Mistral"],
                  "nvidia": ["Nvidia"], "hugging-face": ["Hugging Face"], "typesafe-jev": ["TypeSafe"], "xiaomi-mimo": ["小米"],
                  "minimax": ["MiniMax"], "anthropic": ["Anthropic"]}

CJK = re.compile(r"[　-〿㐀-䶿一-鿿豈-﫿＀-￯]")

def load(path=None):
    p = path or os.environ.get("CLAWQ_HOLDINGS") or DEFAULT
    if not os.path.exists(p): sys.exit(f"holdings.json not found ({p}) — refusing to print a fallback disclosure")
    raw = json.load(open(p, encoding="utf-8"))
    rows = {}
    for kind in ("held", "exited", "not_held"):
        for r in raw.get(kind, []):
            fund = kind == "held" and bool(re.search(r"\bfund\b", r["name"], re.I) or "基金" in (r.get("note") or ""))
            rows[r["name"]] = {"name": r["name"], "aliases": list(r.get("aliases") or []), "confirmed": r.get("confirmed") or "",
                               "kind": "fund" if fund else kind}
    return {"rows": rows, "order": list(rows)}

def lookup(H, name):
    k = (name or "").strip().lower()
    for r in H["rows"].values():
        if k == r["name"].lower() or k in (a.lower() for a in r["aliases"]): return r
    return None

EN_NAME = {"月之暗面": "Moonshot AI"}   # display names only
def en_name(r):
    if r["name"] in EN_NAME: return EN_NAME[r["name"]]
    if not CJK.search(r["name"]): return r["name"]
    return next((a for a in r["aliases"] if not CJK.search(a)), r["name"])
def show(r, zh): return r["name"] if zh else en_name(r)
def sp(a, b): return a + (" " if b[:1].isascii() else "") + b   # site style: a space between CJK and Latin only
def join_en(xs, conj="and"): return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + f" {conj} " + xs[-1]
def by_date(rs):
    out = {}
    for r in rs: out.setdefault(r["confirmed"], []).append(r)
    return sorted(out.items())

# fixed relationship sentences (wording already published on the site), printed only while the record still supports them
def relations(H, rs, zh):
    names = {r["name"] for r in rs}; R = H["rows"]; out = []
    if names & {"Nvidia", "Hugging Face"} and R.get("Hugging Face", {}).get("kind") == "held":
        out.append("英伟达 2026-09-03 宣布收购天际持有的 Hugging Face（待交割）" if zh else
                   "Nvidia announced on Sep 3, 2026 that it would acquire Hugging Face, which FutureX holds (pending closing)")
    mt = R.get("美团")
    if "月之暗面" in names and "美团" not in names and mt and mt["kind"] == "exited":   # with 美团 listed, exits() says it
        out.append(f"天际已全部退出美团（作者 {mt['confirmed']} 确认），因此也无经美团持有的月之暗面间接权益" if zh else
                   f"FutureX has fully exited Meituan (confirmed by the author, {mt['confirmed']}), so it has no indirect interest in Moonshot AI through Meituan")
    return out
CORRECTED_EXITS = ["小米", "美团"]   # early entries disclosed these two as holdings and carry a dated correction (2026-10-11)
def exits(rs, zh):
    s = _dated(rs, zh, "exited"); names = [r["name"] for r in rs]
    cx = [r for n in CORRECTED_EXITS for r in rs if r["name"] == n]
    if cx: s += (f"，{'、'.join(show(r, True) for r in cx)}在早期篇目中按持有披露的已加注更正" if zh else
                 f"; earlier entries that disclosed {join_en([show(r, False) for r in cx])} as {'holdings' if len(cx) > 1 else 'a holding'} carry a correction")
    if "美团" in names: s += "；天际因此也无经美团持有的月之暗面间接权益" if zh else "; it therefore has no indirect interest in Moonshot AI through Meituan"
    return s

def _held(rs, zh):
    xs = [show(r, zh) for r in rs]
    if zh: return sp("天际持有", "、".join(xs)) + "，" + ("涉及这些公司" if len(xs) > 1 else sp("涉及", xs[0]) + (" " if xs[0][-1:].isascii() else "")) + "的结论请双向打折读"
    return f"FutureX holds {join_en(xs)}; discount conclusions touching {'them' if len(xs) > 1 else xs[0]} either way"
def _dated(rs, zh, kind):
    groups = by_date(rs)
    if zh:
        body = "、".join("、".join(show(r, True) for r in g) + f"（作者 {d} 确认）" for d, g in groups)
        return sp("天际已全部退出" if kind == "exited" else "天际不直接或经基金间接持有", body)
    body = (", and " if kind == "exited" else ", nor in ").join(join_en([show(r, False) for r in g], "and" if kind == "exited" else "or") + f" (confirmed by the author, {d})" for d, g in groups)
    return ("FutureX has fully exited " if kind == "exited" else "FutureX holds no direct or fund-level stake in ") + body

def statement(H, names, zh):
    """names → (list of sentences, pending names). Order: held, relationship, exited, not held."""
    seen, rs, pending = set(), [], []
    for n in names:
        r = lookup(H, n)
        if not r or r["kind"] == "fund":
            if n not in pending: pending.append(n)
            continue
        if r["name"] not in seen: seen.add(r["name"]); rs.append(r)
    out = []
    held = [r for r in rs if r["kind"] == "held"]; ex = [r for r in rs if r["kind"] == "exited"]; nh = [r for r in rs if r["kind"] == "not_held"]
    if held: out.append(_held(held, zh))
    out += relations(H, rs, zh)
    if ex: out.append(exits(ex, zh))
    if nh: out.append(_dated(nh, zh, "not_held"))
    return out, pending

def portfolio(H, zh):
    """every company the record lists as held (fund stakes excluded) and every exit, for the Q&A index and the holdings question"""
    held = [r for r in H["rows"].values() if r["kind"] == "held"]; ex = [r for r in H["rows"].values() if r["kind"] == "exited"]
    out = []
    if held:
        xs = [show(r, zh) for r in held]
        out.append(sp("天际持有", "、".join(xs)) + f"（作者确认记录中的 {len(xs)} 家，完整组合以天际官网 futurex.capital 为准），涉及这些公司的结论请双向打折读" if zh else
                   f"FutureX holds {join_en(xs)} ({len(xs)} companies in the author's confirmed record; the full portfolio is on futurex.capital); discount conclusions touching them either way")
    out += relations(H, held, zh)
    if ex: out.append(exits(ex, zh))
    return out

def banned_hits(text, originals=""):
    """banned phrases in text, ignoring a clause that is quoted verbatim from an original entry (entries 131–139 footnotes)"""
    hits = []
    for b in BANNED:
        for m in re.finditer(re.escape(b), text, re.I):
            a = max(text.rfind(c, 0, m.start()) for c in "。；｜<>\n") + 1
            z = min([x for x in (text.find(c, m.end()) for c in "。；｜<>\n") if x != -1] or [len(text)])
            clause = text[a:z].strip()
            if originals and len(clause) >= 12 and clause in originals: continue
            hits.append(clause[:80])
    return hits
