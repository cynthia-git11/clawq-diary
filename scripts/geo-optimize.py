#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEO 每日优化器 · geo-optimize.py
--------------------------------------------------------------------
在 geo-check.py（硬不变量巡检）之上，做「主动优化」而非只巡检：

  A. 新鲜度自动修（安全幂等）：把核心页 sitemap <lastmod>、WebSite/Blog dateModified
     对齐到最新一篇的日期——只在确有偏差时改，改了就返回码 10 让 CI 提交。
  B. 判断腐烂守卫（本日记 GEO 命根子「喂给世界永远是 HEAD」）：
     扫 DECAY_RULES 里已被公开修正的旧数字/旧说法，若出现在「活」carrier
     （llms.txt / index.html 的 FAQ+ItemList+置顶卡，而非归档快照）里就告警。
  C. 体检：死锚（#entry-N 指向不存在的条目）、篇数计数跨 carrier 一致、
     AI 爬虫清单是否覆盖 2026 主力 bot、最新一篇是否已进 FAQ。
  D. GEO 健康分（0–100）+ 人读报告，打到 stdout（进 CI 日志）。

退出码：0=无需改动且无告警 · 10=已做安全新鲜度修复（CI 应提交）· 20=有告警需人看
（10 与 20 可叠加，取较大者；硬失败仍交给 geo-check.py）。
"""
import re, os, io, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def rd(p): return io.open(os.path.join(ROOT, p), encoding="utf-8").read()
def wr(p, s): io.open(os.path.join(ROOT, p), "w", encoding="utf-8").write(s)

warns, fixes, notes = [], [], []

idx = rd("index.html")

# ── 最新一篇：id 取最大、日期取该篇 @graph datePublished ──────────────
ids = sorted(set(int(x) for x in re.findall(r'id="entry-(\d+)"', idx)))
latest = max(ids)
m = re.search(r'#entry-%d",\s*"datePublished":\s*"(\d{4}-\d{2}-\d{2})' % latest, idx)
if not m:
    m = re.search(r'<span[^>]*>(\d{4})年(\d{1,2})月(\d{1,2})日 · Day', idx)
    latest_date = "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3))) if m else None
else:
    latest_date = m.group(1)
dm = re.search(r"<title>倩小虾日记 · Day (\d+)", idx)
title_day = int(dm.group(1)) if dm else None

# ── A. 新鲜度自动修：核心页 sitemap lastmod 对齐最新日期 ───────────────
CORE = ["https://cynthia-git11.github.io/clawq-diary/",
        "https://cynthia-git11.github.io/clawq-diary/en.html",
        "https://cynthia-git11.github.io/clawq-diary/ja.html",
        "https://cynthia-git11.github.io/clawq-diary/theses.html"]
if latest_date:
    sm = rd("sitemap.xml")
    orig = sm
    for loc in CORE:
        # 把该 loc 的 lastmod 抬到 latest_date（只抬旧的、不动更新的）
        pat = re.compile(r"(<loc>" + re.escape(loc) + r"</loc>\s*<lastmod>)(\d{4}-\d{2}-\d{2})(</lastmod>)")
        def bump(mm):
            return mm.group(1) + (latest_date if mm.group(2) < latest_date else mm.group(2)) + mm.group(3)
        sm = pat.sub(bump, sm)
    if sm != orig:
        wr("sitemap.xml", sm)
        fixes.append("sitemap.xml 核心页 <lastmod> 已对齐最新一篇日期 " + latest_date)

# ── B. 判断腐烂守卫：已公开修正的旧说法不得出现在「活」carrier ──────────
# 每次做公开修正后，在这里加一条规则（token=旧说法, why=已被谁改, live=需检查的活文件）。
# 归档快照（llms-full.txt / 各 @graph[entry-N] 描述 / atom 旧 entry）保留原文、不检查。
# 每条：token=旧说法, why=已被谁改, fix=纠正关键词（token 附近出现它则视为已就地纠正、不告警),
#       live=需检查的「活」文件。归档快照（llms-full.txt / 各 @graph[entry-N] 描述 / atom 旧 entry）不检查。
DECAY_RULES = [
    # ENTRY 114 更正了 ENTRY 112 的数：K3 API 涨幅 2.1→3.7 倍
    {"token": "2.1 倍", "why": "ENTRY 114 更正 K3 API 涨幅为约原价 3.7 倍",
     "fix": ["3.7", "更正", "已修正"], "live": ["llms.txt", "index.html"]},
]
def answer_surface(fp):
    """腐烂守卫只查「答案面」——真正会被 AI 当 HEAD 直接引用的：
    llms.txt 全量（prose 索引/最新日记/判断台账）；index.html 只取 FAQPage 答案 + 置顶卡。
    刻意排除 ItemList/@graph 的 per-entry 描述与 timeline 正文——那些是各条目的存档快照，
    HEAD 由最新条目自带的更正 + theses ✗ + llms 台账承载（本站「不改原文、喂 HEAD」模型）。"""
    t = rd(fp)
    if fp == "index.html":
        s = t.find("FAQPage JSON-LD"); e = t.find("</script>", s) if s >= 0 else -1
        faq = t[s:e] if s >= 0 and e >= 0 else ""
        fs = t.find('class="latest-feature"'); fe = t.find("</a>", fs) if fs >= 0 else -1
        feat = t[fs:fe] if fs >= 0 else ""
        return faq + "\n" + feat
    return t
def uncorrected(text, token, markers, window=80):
    """逐处检查 token：若其前后 window 字内都没有任何纠正关键词，则算「未就地纠正」。返回 True=有裸露旧说法。"""
    i, bare = text.find(token), False
    while i != -1:
        ctx = text[max(0, i - window): i + len(token) + window]
        if not any(mk in ctx for mk in markers):
            bare = True; break
        i = text.find(token, i + 1)
    return bare
for r in DECAY_RULES:
    for fp in r["live"]:
        try:
            if uncorrected(answer_surface(fp), r["token"], r.get("fix", [])):
                warns.append("判断腐烂：活文件 %s 仍有裸露的已修正旧说法「%s」（%s）——喂给世界的应是 HEAD" % (fp, r["token"], r["why"]))
        except FileNotFoundError:
            pass

# 通用腐烂守卫：theses.html 每条 ✗（已公开修正）都应能在 llms.txt 里被追溯到
try:
    th = rd("theses.html")
    llms = rd("llms.txt")
    n_bad = len(re.findall(r"✗ 已公开修正", th))
    if n_bad and ("已公开修正" not in llms and "修正" not in llms):
        warns.append("theses 有 %d 条 ✗ 已公开修正，但 llms.txt 未体现任何修正线索——LLM 可能引用被推翻的旧判断" % n_bad)
except FileNotFoundError:
    pass

# ── C1. 死锚：任何 #entry-N 引用都必须指向存在的条目 ─────────────────
idset = set(ids)
for fp in ["index.html", "theses.html", "en.html", "ja.html"]:
    try:
        refs = set(int(x) for x in re.findall(r"#entry-(\d+)", rd(fp)))
        dead = sorted(refs - idset)
        if dead:
            warns.append("死锚：%s 引用了不存在的条目 %s" % (fp, ", ".join("#entry-" + str(d) for d in dead)))
    except FileNotFoundError:
        pass

# ── C2. 篇数计数跨 carrier 一致（今天就踩过「114篇」漏改）──────────────
count_claims = {}
_ti = idx.find('<div class="timeline"'); _head = idx[:_ti] if _ti > 0 else idx  # timeline 前取计数，避开历史条目正文
for label, pat, src in [
    ("index 篇stat", r'claw-text">(\d+)篇', _head),
    ("index mag篇", r"已写 (\d+) 篇", _head),
    ("index meta篇", r'name="description" content="[^"]*?(\d+) 篇真实判断', _head),
    ("en entries", r"Read all (\d+) entries", None),
    ("en foot", r"· (\d+) entries · updated", None),
    ("ja entries", r"(\d+)エントリーをすべて読む", None),
]:
    try:
        text = src if src is not None else rd("en.html" if label.startswith("en") else "ja.html")
        for v in set(re.findall(pat, text)):
            count_claims.setdefault(int(v), []).append(label)
    except FileNotFoundError:
        pass
if len(count_claims) > 1:
    warns.append("篇数计数不一致：" + " / ".join("%d(%s)" % (k, ",".join(v)) for k, v in sorted(count_claims.items())))
elif count_claims and latest not in count_claims:
    notes.append("篇数=%s、最新条目=entry-%d（若非连续编号可忽略）" % (list(count_claims)[0], latest))

# ── C3. AI 爬虫清单覆盖 2026 主力 bot ───────────────────────────────
AI_BOTS_2026 = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-User",
                "Claude-SearchBot", "anthropic-ai", "PerplexityBot", "Google-Extended",
                "Applebot-Extended", "Amazonbot", "Bytespider", "CCBot", "cohere-ai",
                "Meta-ExternalAgent", "DuckAssistBot", "PetalBot", "Diffbot",
                "Timpibot", "ImagesiftBot", "YouBot"]
try:
    robots = rd("robots.txt")
    missing = [b for b in AI_BOTS_2026 if b not in robots]
    if missing:
        warns.append("robots.txt 缺显式放行的 AI 爬虫：" + ", ".join(missing))
except FileNotFoundError:
    warns.append("robots.txt 不存在")

# ── C4. 最新一篇是否已进 FAQ（提高被 AI Overviews / Perplexity 直接引用率）──
# 指纹 = 最新条目 headline 里的英文/产品词 token（Anthropic/OpenAI/Kimi K3/SpaceX…），
# 命中 FAQ 全文（问题名+答案）任一即视为已覆盖。
faq_blob = "".join(re.findall(r'"@type":\s*"Question".*?"text":\s*"[^"]+"', idx, re.DOTALL)[:6])
hm = re.search(r'"headline":\s*"([^"]+)",\s*\n\s*"url":\s*"[^"]*#entry-%d"' % latest, idx)
headline = hm.group(1) if hm else ""
toks = re.findall(r"[A-Za-z][A-Za-z0-9\- ]{2,}[A-Za-z0-9]", headline)  # 英文/产品词
toks = [t.strip() for t in toks if len(t.strip()) >= 3][:5]
covered = (not toks) or any(t in faq_blob for t in toks)
if not covered:
    notes.append("最新一篇（entry-%d，关键词 %s）似未进 FAQ——补一条 Q&A 可提升被直接引用率" % (latest, "/".join(toks)))

# ── D. GEO 健康分 ──────────────────────────────────────────────────
score = 100 - 12 * len(warns) - 3 * len(notes)
score = max(0, min(100, score))

# ── 报告 ───────────────────────────────────────────────────────────
print("=" * 60)
print("  GEO 每日优化报告 · 最新 entry-%d · Day %s · %s" % (latest, title_day, latest_date))
print("=" * 60)
print("GEO 健康分：%d / 100" % score)
if fixes:
    print("\n✅ 已自动修复（新鲜度，CI 将提交）：")
    for f in fixes: print("   · " + f)
if warns:
    print("\n⚠️  需处理的告警：")
    for w in warns: print("   · " + w)
if notes:
    print("\nℹ️  建议（非阻断）：")
    for n in notes: print("   · " + n)
if not (warns or notes):
    print("\n无告警——GEO 处于最优态。")
print("=" * 60)

code = 0
if fixes: code = max(code, 10)
if warns: code = max(code, 20)
sys.exit(code)
