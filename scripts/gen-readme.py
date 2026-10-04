#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: README.md for the GitHub repo page (github.com is crawled heavily; the repo page is a discovery path into the diary).
Reads entries/ (via index.html), data/topics.json, data/answers.json. Deterministic, idempotent.
Usage: python3 scripts/gen-readme.py [--root DIR]"""
import os, re, sys, json, html
BASE = "https://cynthia-git11.github.io/clawq-diary/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = sys.argv[sys.argv.index("--root") + 1]
rd = lambda f: open(os.path.join(ROOT, f), encoding="utf-8").read()
strip = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()
idx = rd("index.html")
ents = []
for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>\s*<div class="entry-date">(.*?)</div>.*?<h3 class="entry-title">(.*?)</h3>', idx, re.S):
    n = int(m.group(1)); d = strip(m.group(2)).replace("¶", "").strip()
    dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", d)
    ents.append((n, f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}" if dm else "", strip(m.group(3))))
ents.sort(key=lambda e: -e[0])
topics = [t for t in json.load(open(os.path.join(ROOT, "data/topics.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "topics", t["slug"] + ".html"))]
answers = json.load(open(os.path.join(ROOT, "data/answers.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "data/answers.json")) else []
ledger = re.search(r"(\d+) 个重大判断", rd("llms.txt"))
md = []
md.append("# 倩小虾日记 · The ClawQ Chronicles\n")
md.append(f"天际资本（FutureX Capital）创始人张倩（Cynthia Zhang）的公开 AI 投资判断记录。不定期、有判断才写：每篇一个商业判断、一组可核对的数字、给创业者与投资人的落点，以及写明阈值、截止日和裁定源的证伪口。错了就在原篇公开更正。\n")
md.append(f"A public, auditable record of AI investment calls by Cynthia Zhang, founder of FutureX Capital. Each entry makes one call, shows its numbers, and states what would prove it wrong; corrections are made in public on the original entry.\n")
md.append(f"**网站 Site**：<{BASE}>　·　共 {len(ents)} 篇" + (f"　·　{ledger.group(1)} 个挂账判断" if ledger else "") + "\n")
md.append("## 怎么读 How to read\n")
md.append(f"- [全部单篇 · All entries]({BASE}entries/)：每篇一个独立页面，含结构化尾注（来源、口径注、证伪口、利益披露、更正）")
md.append(f"- [公司与议题 · Topics]({BASE}topics/)：按公司或议题聚合的判断脉络与挂账状态")
md.append(f"- [投资人与创业者问答 · Q&A]({BASE}answers/)（[English]({BASE}answers/en/)）：一题一页，答案数字与所引日记逐字一致")
md.append(f"- [判断台账 · Judgment ledger]({BASE}theses.html)：每个重大判断的验证状态（✓ 已验证 / ✗ 已证伪 / ⏳ 进行中）")
md.append(f"- [English edition]({BASE}en.html) · [日本語版]({BASE}ja.html)\n")
md.append("## 最新 15 篇 Latest entries\n")
for n, d, t in ents[:15]:
    md.append(f"- {d} · [ENTRY {n} · {t}]({BASE}entries/{n}.html)")
md.append(f"\n全部 {len(ents)} 篇见 [entries/]({BASE}entries/)。\n")
if topics:
    md.append("## 公司与议题 Topics\n")
    md.append("　·　".join(f"[{t['name']}]({BASE}topics/{t['slug']}.html)" for t in topics) + "\n")
if answers:
    md.append(f"## 投资人与创业者会问的 {len(answers)} 个问题 Questions\n")
    for grp, label in (("投资人", "投资人 Investors"), ("创业者", "创业者 Founders")):
        qs = [q for q in answers if q.get("persona_group") == grp and q.get("slug")]
        if not qs: continue
        md.append(f"**{label}**\n")
        for q in qs: md.append(f"- [{q['q_zh']}]({BASE}answers/{q['slug']}.html)")
        md.append("")
md.append("## 机器可读 Machine-readable\n")
md.append(f"- [llms.txt]({BASE}llms.txt) · [llms-full.txt]({BASE}llms-full.txt)")
md.append(f"- [Atom feed]({BASE}atom.xml) · [sitemap-index.xml]({BASE}sitemap-index.xml)")
md.append(f"- 判断台账结构化数据见 [theses.html]({BASE}theses.html) 的 JSON-LD\n")
md.append("## 说明 Notes\n")
md.append("- 本日记由 Claude 系工具辅助写作与核实；作者基金天际持有字节跳动、Mistral、小米、美团（月之暗面为间接权益）、Hugging Face，涉及这些公司的篇目在尾注首项披露并双向打折。")
md.append("- 本日记不构成对任何基金产品的推介或募集要约。This diary does not constitute promotion of, or an offer to subscribe for, any fund product.")
md.append(f"- 本文件由 `scripts/gen-readme.py` 根据站点内容自动生成，请勿手改。\n")
out = "\n".join(md)
p = os.path.join(ROOT, "README.md")
if not os.path.exists(p) or open(p, encoding="utf-8").read() != out:
    open(p, "w", encoding="utf-8").write(out); print(f"README.md written · entries {len(ents)} · topics {len(topics)} · answers {len(answers)}")
else:
    print("README.md unchanged")
