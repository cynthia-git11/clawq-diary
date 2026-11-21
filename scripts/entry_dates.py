#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dates of an ENTRY, shared by gen-entry-pages.py (Chinese pages) and gen-entries-en.py (English editions).

Both scripts read the same things from index.html and data/ledger.json in the same run: the entry date, the footnote
items, the latest dated change the footnote names, and the ledger dates the status strip shows. Before 2026-11-21 the
English page read the Chinese page's previous build, so a footnote-only correction reached it one run late.
Deterministic, no I/O. Not a CLI."""
import re, datetime

TODAY = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d")   # Beijing date

def strip(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()

def entry_date_d(date_txt):
    """full date when present; early entries only carry a month ("2026年2月初") → partial ISO "2026-02" (valid schema.org Date)"""
    dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_txt)
    ym = re.search(r"(\d{4})年(\d{1,2})月", date_txt)
    yy = re.search(r"(\d{4})年", date_txt)
    return f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}" if dm else (f"{ym.group(1)}-{int(ym.group(2)):02d}" if ym else (yy.group(1) if yy else ""))

def foot_of(blk):
    """(footnote html, footnote text) of one index.html entry block"""
    body = (re.search(r'<div class="entry-body">(.*?)$', blk, re.S) or [None, ""])[1]
    foot_html = (re.search(r'<div class="entry-foot">(.*?)</div>', body, re.S) or [None, ""])[1]
    return foot_html, strip(foot_html)

# ---------- footnote → machine-readable items ----------
KINDS = ["来源", "证伪口", "口径注", "更正", "利益披露", "对账", "免责", "附注", "单源", "自首", "裁定", "升级线", "认错", "勘误",
         "诚信标注", "原文引语", "合规依据", "关联", "承接", "回滚点", "验收指标", "验收", "验证时限", "时限", "纠偏", "补记", "背景", "专名注",
         "类比出处", "待对账", "赌盘对账", "反向预登记", "后续修正", "事实边界", "时点口径", "工作量口径", "指控内容", "新规", "判断框架验证",
         "引用过往条目", "收获项存档", "纠三个错数", "历史尺子与口径", "表外敞口", "预注册", "金句", "共识", "更新", "注"]
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2})")
def foot_items(foot):
    parts = [p.strip() for p in re.split(r"｜", foot) if p.strip()]
    out = []
    for p in parts:
        k = "其他"
        for kk in KINDS:
            if p.startswith(kk): k = kk; break
        if k == "其他" and DATED.match(p): k = "更正" if re.search(r"更正|纠|勘误|回写|改口|认错", p[:40]) else "补记"
        if k == "其他" and p.startswith("ENTRY "): k = "关联"
        if k == "其他":
            lm = re.match(r"^([^：:，。；\s]{2,8})[：:]", p)
            if lm: k = lm.group(1)
        if "不构成对任何基金产品的推介" in p: k = "免责"
        out.append((k, p))
    return out

# dateModified: latest date named in 更正/对账/补记/后续修正 segments (ISO or M/D in the entry year), never earlier than datePublished.
# A note that opens with its own date (「2026-11-13 读数：…11/19 开始交易」) cannot record a change after that date: later dates
# inside it are event dates, and without this cap the page's date moved forward as days passed (2026-11-21). A date directly
# followed by a re-check verb (「2026-10-08 核对、10/10 复核」) is a later change written into the same segment and is not capped;
# authors adding a re-check can also open a new ｜ segment with its own date.
MOD_KINDS = ("更正", "对账", "补记", "后续修正", "纠偏", "认错", "勘误", "赌盘对账", "待对账", "更新")
RECHECK = re.compile(r"\s*(?:复核|核对|更正|修正|勘误|对账|回写|补记|改口|改为)")
def modified(date_d, items, today=None):
    today = today or TODAY
    best = date_d if len(date_d) == 10 else (date_d + "-01" if len(date_d) == 7 else "")  # 月份精度的旧条目也能记录后续更新
    yr = date_d[:4] if date_d else "2026"
    for k, v in items:
        if k not in MOD_KINDS: continue
        lead = re.match(r"(\d{4}-\d{2}-\d{2})|(\d{1,2})/(\d{1,2})(?![\d/])", (v[len(k):] if v.startswith(k) else v).lstrip("：: "))
        cap = (lead.group(1) or f"{yr}-{int(lead.group(2)):02d}-{int(lead.group(3)):02d}") if lead else today
        for m in list(re.finditer(r"(\d{4})-(\d{2})-(\d{2})", v)) + list(re.finditer(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])", v)):
            d = m.group(0) if m.lastindex == 3 else f"{yr}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
            lim = today if RECHECK.match(v, m.end()) else min(cap, today)
            if best and d > best and d <= lim: best = d
    return best

def ledger_dates(c, today=None):
    """the dates one data/ledger.json card's status line shows (correction / reconciliation, a later reading, a 补记 write date)
    — the only ledger dates allowed to date a page, so every date a page claims is visible on it"""
    today = today or TODAY
    d = [c["corrected_on"]] if (c["status"] == "corrected" and c["corrected_on"]) else ([c["reconciled"]] if c["reconciled"] else [])
    if later_reading(c): d.append(c["last_reading"])
    if c.get("backfill") and c.get("written_date"): d.append(c["written_date"])
    return [x for x in d if x and x <= today]

def later_reading(c):
    """a dated reading on the card later than its last reconciliation (gen-ledger.py shows it the same way)"""
    return bool(c.get("last_reading") and (not c["reconciled"] or c["last_reading"] > c["reconciled"]))
