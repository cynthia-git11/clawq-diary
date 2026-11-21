# -*- coding: utf-8 -*-
"""llms.txt blocks owned by one generator each: <!-- gen:NAME --> … <!-- /gen:NAME -->.

gen-answers.py owns "answers" (Q&A index), gen-topics.py owns "topics" (topic hubs), gen-ledger.py owns "ledger" (ledger files
in 数据源 / 元数据). put() rewrites only the named block, so reruns are idempotent and the rest of llms.txt — the lines buildN.py
anchors on (the 「⚖️ **判断总账」 ledger line, the 「- [ENTRY N · Day …」 list lines), the hand-written prose — is never touched.
A block that is not there yet is inserted before the first anchor of `before` that exists (an anchor starting with "\n" is a
line start), followed by `sep`; with no anchor found it is appended.
Guard: a block may not carry a line buildN.py / gen-entry-pages.py would match ("- [ENTRY", "⚖️ **判断总账", "个重大判断").
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
