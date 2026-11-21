# -*- coding: utf-8 -*-
"""llms.txt blocks owned by one generator each: <!-- gen:NAME --> … <!-- /gen:NAME -->.

gen-answers.py owns "answers" (Q&A index), gen-topics.py owns "topics" (topic hubs), gen-ledger.py owns "ledger" (ledger files
in 数据源 / 元数据). put() rewrites only the named block, so reruns are idempotent and the rest of llms.txt — the lines buildN.py
anchors on (the 「⚖️ **判断总账」 ledger line, the 「- [ENTRY N · Day …」 list lines), the hand-written prose — is never touched.
A block that is not there yet is inserted before the first anchor of `before` that exists (an anchor starting with "\n" is a
line start), followed by `sep`; with no anchor found it is appended.
Guard: a block may not carry a line buildN.py / gen-entry-pages.py would match ("- [ENTRY", "⚖️ **判断总账", "个重大判断").

months() (llms-full.txt, called by gen-entry-pages.py): one 「# YYYY 年 M 月 · 倩小虾日记存档」 heading before each run of entry sections
of the same month, taken from each section's own date. buildN.py inserts every new section in front of the previous newest one,
so before 2026-11-21 ENTRY 84–161 (June–November) all sat under the May heading. Only headings directly followed by a section are
regenerated; buildN.py's anchor (「## ENTRY N · Day D · 」) and the section text are never touched. Idempotent.
"""
import re

FORBIDDEN = ("- [ENTRY", "[ENTRY ", "⚖️ **判断总账", "个重大判断")


def put(text, name, body, before=("\n## 引用规范",), sep="\n\n"):
    body = body.strip("\n")
    for bad in FORBIDDEN:
        if bad in body: raise ValueError(f"llms.txt block {name}: may not contain {bad!r} (buildN.py anchor)")
    blk = f"<!-- gen:{name} -->\n{body}\n<!-- /gen:{name} -->"
    rx = re.compile(r"<!-- gen:%s -->.*?<!-- /gen:%s -->" % (re.escape(name), re.escape(name)), re.S)
    if len(rx.findall(text)) > 1: raise ValueError(f"llms.txt: block {name} appears more than once")
    if rx.search(text): return rx.sub(lambda _: blk, text, count=1)
    for a in before:
        i = text.find(a)
        if i != -1:
            j = i + 1 if a.startswith("\n") else i   # keep the blank line in front of a heading
            return text[:j] + blk + sep + text[j:]
    return text.rstrip("\n") + "\n\n" + blk + "\n"


MONTH_H = re.compile(r"^# \d{4} 年 \d{1,2} 月 · 倩小虾日记存档\n\n(?=## )", re.M)
TOP_H = re.compile(r"^# \d{4} 年 \d{1,2} 月 · 倩小虾日记存档\n\n(?=> )", re.M)   # the archive intro, not a month
SEC_H = re.compile(r"^## (?:ENTRY \d+ · Day \d+ · (\d{4})-(\d{2})-\d{2}|(\d{4})-(\d{2})-\d{2} · Day \d+ · ENTRY \d+ · )", re.M)


def months(text):
    t = TOP_H.sub("# 倩小虾日记存档 · 逐篇全文\n\n", MONTH_H.sub("", text), count=1)
    out, pos, last = [], 0, None
    for m in SEC_H.finditer(t):
        ym = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        if ym != last:
            out += [t[pos:m.start()], f"# {ym[0]} 年 {int(ym[1])} 月 · 倩小虾日记存档\n\n"]; pos, last = m.start(), ym
    return "".join(out) + t[pos:]
