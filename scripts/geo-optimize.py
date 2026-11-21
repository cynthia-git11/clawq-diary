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
     B 的规则 2026-11-21 起自动并入 data/ledger.json 的撤回原话 / 判错分项；index / en / ja 的 FAQ 答案逐条整段判。
  C. 体检：死锚（#entry-N 指向不存在的条目）、篇数计数跨 carrier 一致、
     AI 爬虫清单是否覆盖 2026 主力 bot、最新一篇是否已进 FAQ、判断台账派生文件同步、
     单篇页台账状态条与徽章一致且 JSON-LD 可解析、FAQ 复述已 ✗/◐ 判断须带对账指针、已有指针须与判断现状一致（C7，scripts/hub_sync.py）。
  A3 的计数锚点表与 gen-ledger.py 共用 scripts/hub_sync.py（en hero、press、带日期的 FAQ 篇数、theses 导语）。
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

# ── A2. 新鲜度自动修：hub Blog.dateModified 与「N 篇真实判断」计数对齐最新一篇 ─────
if latest_date:
    h = rd("index.html"); h0 = h
    try:
        bi = h.index('"@type": "Blog"'); bj = h.index('"dateModified": "', bi); bk = h.index('"', bj + len('"dateModified": "'))
        cur = h[bj + len('"dateModified": "'):bk]
        latest_iso = (re.search(r'"datePublished": "([^"]+)"', h) or [None, latest_date + "T13:00:00+08:00"])[1]
        if cur[:10] < latest_iso[:10]: h = h[:bj] + '"dateModified": "' + latest_iso + h[bk:]
    except ValueError:
        pass
    n_entries = len(re.findall(r'<div id="entry-(\d+)"', h))
    h = re.sub(r"\d+ 篇真实判断与公开复盘", f"{n_entries} 篇真实判断与公开复盘", h)
    if h != h0:
        wr("index.html", h); fixes.append("index.html Blog.dateModified / 篇数计数已对齐最新一篇")

# ── A3. 新鲜度自动修：buildN 不改的 Day / 篇数锚点对齐 index.html（2026-10-02 起 press；2026-11-21 起改用
#    scripts/hub_sync.py 的同一张锚点表，与 gen-ledger.py 共用：en hero「DAY N」、en「Public entries written」、
#    index/ja FAQ 里带日期的篇数、theses 导语、press / press-en 的 Day 与篇数、en/ja Blog.dateModified）────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True   # no scripts/__pycache__ for geo-daily.yml's `git add -A`
import hub_sync as HS
if latest_date:
    try:
        _site = HS.site_state(rd("index.html"))
        for pf in HS.COUNT_RULES:
            if not os.path.exists(os.path.join(ROOT, pf)): continue
            s0 = rd(pf); s1, ch, _miss = HS.sync_counts(pf, s0, _site)
            if s1 != s0:
                wr(pf, s1); fixes.append(f"{pf} 计数/日期已对齐 Day {_site['day']} · {_site['entries']} 篇（{'、'.join(ch)}）")
    except ValueError as _e:
        warns.append("计数对齐跳过：" + str(_e))

# ── B. 判断腐烂守卫：已公开修正的旧说法不得出现在「活」carrier ──────────
# 每次做公开修正后，在这里加一条规则（token=旧说法, why=已被谁改, live=需检查的活文件）。
# 归档快照（llms-full.txt / 各 @graph[entry-N] 描述 / atom 旧 entry）保留原文、不检查。
# 每条：token=旧说法, why=已被谁改, fix=纠正关键词（token 附近出现它则视为已就地纠正、不告警),
#       live=需检查的「活」文件。归档快照（llms-full.txt / 各 @graph[entry-N] 描述 / atom 旧 entry）不检查。
DECAY_RULES = [
    # ENTRY 114 更正了 ENTRY 112 的数：K3 API 涨幅 2.1→3.7 倍
    {"token": "2.1 倍", "why": "ENTRY 114 更正 K3 API 涨幅为约原价 3.7 倍",
     "fix": ["3.7", "更正", "已修正"], "live": ["llms.txt", "index.html"]},
    {"token": "~2.1x", "why": "ENTRY 114 corrected the K3 API rise to ~3.7x the old price",
     "fix": ["3.7"], "live": ["en.html"]},
    # 2026-11-13 对账：ENTRY 140 ◐，「接钱的是 Kimi K3 与 OpenAI」不准（FAQ 原句换了说法，原文不改，靠对账指针）
    {"token": "接钱的是标价 $3/$15 的 Kimi K3", "why": "ENTRY 140 ◐ 部分成立，接钱的不是 Kimi K3 与 OpenAI",
     "fix": ["theses.html#call-140"], "live": ["index.html"]},
]
# 2026-11-21 起自动并入 data/ledger.json：每条 ✗ 的撤回原话（retracted）与对账判错的分项原话（subclaim_judged_wrong）。
# FAQ 答案里出现即须带 gen-ledger.py（scripts/hub_sync.py）写的对账指针 theses.html#call-N。
try:
    import json as _json
    for _c in _json.load(io.open(os.path.join(ROOT, "data/ledger.json"), encoding="utf-8"))["calls"]:
        for _k, _lab in (("retracted", "已认错撤回"), ("subclaim_judged_wrong", "对账判错的分项")):
            if _c.get(_k):
                DECAY_RULES.append({"token": _c[_k], "why": "ENTRY %d %s（判断台账 theses.html#call-%d）" % (_c["entry"], _lab, _c["entry"]),
                                    "fix": ["theses.html#call-%d" % _c["entry"], "theses-en.html#call-%d" % _c["entry"]],
                                    "live": ["llms.txt", "index.html", "en.html", "ja.html"]})
except (FileNotFoundError, ValueError, KeyError):
    pass
def answer_surface(fp):
    """腐烂守卫只查「答案面」——真正会被 AI 当 HEAD 直接引用的，返回 [(文本, 是否整段判)]：
    llms.txt 全量（prose 索引/最新日记/判断台账，按 token 前后 80 字判）；index.html / en.html / ja.html 取
    FAQPage 的每条答案（整条答案算一段：对账指针写在答案末尾）+ 置顶卡。
    刻意排除 ItemList/@graph 的 per-entry 描述与 timeline 正文——那些是各条目的存档快照，
    HEAD 由最新条目自带的更正 + theses ✗ + llms 台账承载（本站「不改原文、喂 HEAD」模型）。"""
    t = rd(fp)
    if fp in HS.LANG:
        units = [(a, True) for _q, a in HS.faq_answers(fp, t)]
        fs = t.find('class="latest-feature"'); fe = t.find("</a>", fs) if fs >= 0 else -1
        if fs >= 0: units.append((t[fs:fe], False))
        return units
    return [(t, False)]
def uncorrected(text, token, markers, window=80, whole=False):
    """逐处检查 token：若其前后 window 字内（whole=True 时整段）都没有任何纠正关键词，则算「未就地纠正」。返回 True=有裸露旧说法。"""
    if whole: return token in text and not any(mk in text for mk in markers)
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
            if any(uncorrected(u, r["token"], r.get("fix", []), whole=w) for u, w in answer_surface(fp)):
                warns.append("判断腐烂：活文件 %s 仍有裸露的已修正旧说法「%s」（%s）——喂给世界的应是 HEAD" % (fp, r["token"], r["why"]))
        except FileNotFoundError:
            pass
# C7（2026-11-21）：FAQ 答案复述了已 ✗ / ◐ 的判断（按导语 ENTRY / 日期、faq_calls 覆盖表、原话命中）却缺对账指针，
# 或已有指针的状态与 data/ledger.json 不符（含改判 ✓ / ⏳）、位置不在利益披露之前，或「台账现状」过期——
# 这些由 gen-ledger.py 写；这里只告警，不在 CI 里改内容。
try:
    import json as _json, html as _html
    _L = _json.load(io.open(os.path.join(ROOT, "data/ledger.json"), encoding="utf-8"))
    _ov = _json.load(io.open(os.path.join(ROOT, "data/ledger-overrides.json"), encoding="utf-8")).get("faq_calls")
    _idx = rd("index.html")
    _plain = lambda p: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", rd(p)))).strip() if os.path.exists(os.path.join(ROOT, p)) else None
    _num, _ = HS.number_fixes(_plain)
    for fp in HS.LANG:
        _t, _acts, _ = HS.faq_sync(fp, rd(fp), _L["calls"], _L["stats"], _L["updated"], HS.entry_dates(_idx), _ov, _num)
        if _acts:
            warns.append("判断腐烂：%s 的 FAQ 答案缺对账指针或台账现状过期 %d 处（%s）——跑 python3 scripts/gen-ledger.py"
                         % (fp, len(_acts), "；".join(_acts[:4])))
except (FileNotFoundError, ValueError, KeyError) as _e:
    warns.append("FAQ 对账指针检查跳过：%s" % _e)

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

# ── C5. 判断台账派生文件同步（scripts/gen-ledger.py 产出；2026-11-21 起）──────
# buildN.py 只改卡片、"N 个重大"、numberOfItems 和 llms.txt 台账行（这些由 geo-check 第 7 项硬拦）；
# 数字牌、id="call-N"、Claim JSON-LD、data/ledger.json、theses-en.html 要等 gen-ledger 跑过才同步。
# 这里只告警（geo-daily 会开待办 issue），不让每小时 CI 变红。
try:
    import json as _json
    th = rd("theses.html")
    cnt = {k: len(re.findall(r'<span class="badge %s">' % k, th)) for k in ("b-ok", "b-bad", "b-part", "b-open")}
    cards = len(re.findall(r'<div class="call"[^>]*>', th))
    tiles = {"b-" + k: int(v) for k, v in re.findall(r'<div class="s (ok|bad|part|open)"><div class="v">(\d+)</div>', th)}
    probs = []
    if tiles != cnt: probs.append("数字牌 %s ≠ 徽章 %s" % (tiles, cnt))
    no_id = cards - len(re.findall(r'<div class="call" id="call-\d+"', th))
    if no_id: probs.append("%d 张卡没有 id=call-N" % no_id)
    if th.count('"@type": "Claim"') != cards: probs.append("Claim JSON-LD %d 条 ≠ 卡片 %d 张" % (th.count('"@type": "Claim"'), cards))
    st = _json.load(io.open(os.path.join(ROOT, "data/ledger.json"), encoding="utf-8"))["stats"]
    if [st["total"], st["verified"], st["corrected"], st["partly"], st["open"]] != [cards, cnt["b-ok"], cnt["b-bad"], cnt["b-part"], cnt["b-open"]]:
        probs.append("data/ledger.json 计数过期")
    if len(re.findall(r'id="call-\d+"', rd("theses-en.html"))) != cards: probs.append("theses-en.html 条数过期")
    if probs:
        warns.append("判断台账派生文件与徽章计数不一致：" + "；".join(probs) + "——跑 python3 scripts/gen-ledger.py")
except FileNotFoundError:
    warns.append("判断台账派生文件缺失（data/ledger.json 或 theses-en.html）——跑 python3 scripts/gen-ledger.py")

# ── C6. 单篇页：台账状态条与 theses.html 徽章一致、JSON-LD 可解析（2026-11-21 起；只告警）──────
# 状态条由 gen-entry-pages.py / gen-entries-en.py 从 data/ledger.json 生成；ledger.json 过期或页面没重建时，
# 单篇页会给出与台账不同的状态。geo-check.py（每小时 CI）不读 entries/，所以放在这里。
try:
    import json as _json, glob as _glob
    _ST = {"b-ok": "verified", "b-bad": "corrected", "b-part": "partly", "b-open": "open"}
    want = {}
    for _c in re.split(r'(?=<div class="call"[^>]*>)', rd("theses.html"))[1:]:
        _n = re.search(r'<div class="claim"><a href="(?:index\.html#entry-|entries/)(\d+)', _c); _b = re.search(r'<span class="badge (b-ok|b-bad|b-part|b-open)">', _c)
        if _n and _b: want[int(_n.group(1))] = _ST[_b.group(1)]
    off, badld = [], []
    for fp in sorted(_glob.glob(os.path.join(ROOT, "entries", "*.html")) + _glob.glob(os.path.join(ROOT, "entries", "en", "*.html"))):
        s = io.open(fp, encoding="utf-8").read(); rel = os.path.relpath(fp, ROOT)
        for _blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try: _json.loads(_blk)
            except ValueError: badld.append(rel); break
        _m = re.match(r"(\d+)\.html$", os.path.basename(fp))
        if not _m: continue
        got = re.findall(r'<p class="st-(verified|corrected|partly|open)">', (re.search(r'<div class="e[pe]-ledger"[^>]*>(.*?)</div>', s, re.S) or [None, ""])[1])
        if got != ([want[int(_m.group(1))]] if int(_m.group(1)) in want else []): off.append(rel)
    if off: warns.append("单篇页台账状态条与 theses.html 徽章不一致：%d 页（%s）——先跑 scripts/gen-entries-en.py（含 gen-ledger.py）再跑 scripts/gen-entry-pages.py" % (len(off), ", ".join(off[:8])))
    if badld: warns.append("单篇页 JSON-LD 解析失败（与生成器输出不一致）：%d 页（%s）" % (len(badld), ", ".join(badld[:8])))
except FileNotFoundError:
    pass

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
