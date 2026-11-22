#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reader fold for the footnote of an ENTRY (2026-11-23, author: 「利益披露备注，如果读者点击再展示，不要占用日记文字」).

A reader sees the title, date, body and quote; the footnote (利益披露｜来源｜口径注｜更正｜证伪口 …) sits behind ONE
<details class="entry-fold"> right after the quote. The footnote markup itself is never touched: the <div class="entry-foot">
is wrapped as it is, byte for byte, so crawlers and no-JS readers keep the full text (a closed <details> is in the DOM).

  fold_hub(index_html)   → (html, n): wrap every <div class="entry-foot"> in index.html; idempotent — an existing wrapper is
                           taken off first and put back with a freshly computed label, so a footnote that gains a segment
                           (a correction, a 补记) gets the right label on the next run
  label(foot_html)       → the summary text: the segment kinds present, in LABEL_ORDER, at most three (「利益披露 · 来源 · 证伪口」),
                           plus 更正 right after 利益披露 whenever the footnote carries a correction (「利益披露 · 更正 · 来源 · 证伪口」)
  plain(foot_html)       → the footnote as plain text without losing a literal "<6.5%" (entry_dates.strip removes "<…>" spans)
  ordered(items)         → foot_items with the 利益披露 segment first (the reading order inside the fold; the source order is kept
                           in the HTML)

gen-entry-pages.py applies fold_hub to index.html before it reads the entry blocks (buildN.py writes the bare footnote and runs
gen-entry-pages.py right after), so the single pages carry the same wrapper. The look and the client-side segment labels live in
index.html's head (<style id="reader-css">, <script id="reader-js">) and in gen-entry-pages.py's page CSS.
Deterministic, no I/O. Not a CLI."""
import re, html

from entry_dates import foot_items

LABEL_ORDER = ["利益披露", "来源", "证伪口", "对账", "补记", "口径注"]
FALSIFIER_HINT = "什么情况下我认错"   # shown after 「证伪口：」 inside the fold
# a correction is never left out of the label (review 2026-11-23: with a cap of three it fell behind 来源 · 证伪口, and the
# timeline has no ledger chip, so a corrected entry looked uncorrected): 更正 and its siblings (认错, 订正, 勘误, 纠偏, 后续修正,
# 修正自己 …) count as 更正 and go right after 利益披露, as a fourth item when needed; 「更正：无」 does not count.
CORR_KIND = re.compile(r"更正|认错|订正|勘误|纠|修正")
NO_CORR = re.compile(r"^[\s：:]*无[。；;，,\s]*$")

def plain(foot_html):
    """footnote html → plain text; only real tags are removed (a literal "<6.5%" in the text stays)"""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"</?[A-Za-z][^>]*>", "", foot_html))).strip()

def label_kind(k, v):
    """a segment kind as the label names it: 自我披露 and other …披露 → 利益披露; the correction family → 更正 ("" for 「更正：无」)"""
    if k.endswith("披露"): return "利益披露"
    if k != "其他" and CORR_KIND.search(k):
        return "" if NO_CORR.match(v[len(k):] if v.startswith(k) else v) else "更正"
    return k

def label(foot_html):
    kinds = {label_kind(k, v) for k, v in foot_items(plain(foot_html))}
    picked = [k for k in LABEL_ORDER if k in kinds][:3]
    if "更正" in kinds: picked.insert(1 if picked[:1] == ["利益披露"] else 0, "更正")
    return " · ".join(picked) if picked else "尾注"

def ordered(items):
    """利益披露 first, 免责 (the fund disclaimer) last, everything else in source order"""
    first = [x for x in items if x[0] == "利益披露"]
    last = [x for x in items if x[0] == "免责"]
    return first + [x for x in items if x[0] not in ("利益披露", "免责")] + last

def summary_html(lab):
    """the one control: link-style text plus a CSS chevron; <details> gives keyboard and screen-reader behaviour for free"""
    return f'<summary class="ef-sum"><span class="ef-sum-t">{html.escape(lab, quote=False)}</span></summary>'

FOOT_RE = re.compile(r'([ \t]*)<div class="entry-foot">((?:(?!</div>).)*)</div>', re.S)
WRAP_RE = re.compile(r'([ \t]*)<details class="entry-fold">\n[ \t]*<summary class="ef-sum">(?:(?!</summary>).)*</summary>\n'
                     r'[ \t]*(<div class="entry-foot">(?:(?!</div>).)*</div>)\n[ \t]*</details>', re.S)

def unwrap(s):
    """take the generated wrapper off (exact inverse of wrap for markup this module wrote, indentation included)"""
    return WRAP_RE.sub(lambda m: m.group(1) + m.group(2), s)

def wrap(s):
    def one(m):
        ind, inner = m.group(1), m.group(2)
        return (f'{ind}<details class="entry-fold">\n{ind}  {summary_html(label(inner))}\n'
                f'{ind}  <div class="entry-foot">{inner}</div>\n{ind}</details>')
    return FOOT_RE.subn(one, s)

def fold_hub(s):
    """index.html → (index.html with every footnote folded, number of footnotes)"""
    base = unwrap(s)
    out, n = wrap(base)
    return out, n
