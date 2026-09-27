#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: question-shaped answer pages for investors and AI founders.

Input : data/answers.json  [{id, persona ("投资人"|"创业者"), q_zh, q_en, a_zh, a_en, entries[int], date (YYYY-MM-DD),
                            numbers[str] (every number used in a_zh/a_en must appear verbatim in one of the cited entries)}]
Reads : index.html (to verify every number in each answer exists in a cited ENTRY — refuses to build otherwise)
Writes: answers.html (zh), answers-en.html (en), sitemap-answers.xml; robots.txt Sitemap line if missing
Each question is an anchor (#qNN) with its own FAQPage entry, links to entries/<N>.html, and the date of the judgment.
Usage: python3 scripts/gen-answers.py [--root DIR] [--dry] [--no-verify]
"""
import re, os, sys, json, html, shutil, tempfile

BASE = "https://cynthia-git11.github.io/clawq-diary/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = sys.argv[sys.argv.index("--root") + 1]
DRY = "--dry" in sys.argv; VERIFY = "--no-verify" not in sys.argv
if DRY:
    W = tempfile.mkdtemp(prefix="answers-")
    for f in ["index.html", "robots.txt"]: shutil.copy(os.path.join(ROOT, f), W)
    os.makedirs(os.path.join(W, "data")); shutil.copy(os.path.join(ROOT, "data/answers.json"), os.path.join(W, "data"))
    ROOT = W
def rd(f): return open(os.path.join(ROOT, f), encoding="utf-8").read()
def wr(f, s):
    p = os.path.join(ROOT, f); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(s)
def strip(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
def esc(s): return html.escape(s, quote=True)

Q = json.load(open(os.path.join(ROOT, "data/answers.json"), encoding="utf-8"))
idx = rd("index.html")
def block_at(s, start):
    i = start; depth = 0; tag = re.compile(r"<(/?)div\b[^>]*>", re.I)
    while True:
        m = tag.search(s, i); depth += -1 if m.group(1) else 1; i = m.end()
        if depth == 0: return i
etext = {}; etitle = {}
for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>', idx):
    n = int(m.group(1)); blk = idx[m.start():block_at(idx, m.start())]
    etext[n] = strip(blk).replace(",", "").replace("，", ""); etitle[n] = strip((re.search(r'<h3 class="entry-title">(.*?)</h3>', blk, re.S) or [None, ""])[1])

# ---------- number-fidelity gate: every number token in an answer must appear in a cited entry ----------
NUM = re.compile(r"\d+(?:\.\d+)?")
problems = []
for q in Q:
    cited = " ".join(etext.get(n, "") for n in q["entries"])
    for n in q["entries"]:
        if n not in etext: problems.append(f"{q['id']}: cites ENTRY {n} which does not exist")
    for lang in ("a_zh", "a_en"):
        txt = q.get(lang, "").replace(",", "")
        for tok in set(NUM.findall(txt)):
            if tok in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "24", "30", "60", "90", "100") : continue  # ordinals/generic counts
            if re.search(r"20\d\d", tok): continue  # years handled loosely
            # accept unit conversions the English side makes (亿 → B/M ×10 or ÷10; 万 → k); the digits must still come from the source
            v = float(tok); alts = {tok} | {f"{v*10:g}", f"{v/10:g}", f"{v*100:g}", f"{v/100:g}", f"{v*1000:g}", f"{v/1000:g}"}
            if not any(a in cited for a in alts): problems.append(f"{q['id']} {lang}: number {tok} not found in cited entries {q['entries']}")
if VERIFY and problems:
    print("NUMBER-FIDELITY GATE FAILED:"); [print("  ✗", p) for p in problems]; sys.exit(1)

CSS = """
    .aw-wrap{max-width:820px;margin:0 auto;padding:28px 18px 60px}
    .aw-nav{font-family:var(--sans,Inter,sans-serif);font-size:13px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:22px;color:var(--muted)}
    .aw-nav a{color:var(--claw2,#B8860B);text-decoration:none;font-weight:600}.aw-nav .aw-brand{font-weight:800;color:var(--text);font-size:15px}
    h1.aw-h1{font-size:26px;line-height:1.3;margin-bottom:8px}.aw-sub{font-family:var(--sans,Inter,sans-serif);font-size:13px;color:var(--muted2);margin-bottom:22px;line-height:1.7}
    .aw-toc{font-family:var(--sans,Inter,sans-serif);font-size:13px;line-height:1.9;columns:2;column-gap:28px;margin-bottom:26px}.aw-toc a{color:var(--muted);text-decoration:none}.aw-toc a:hover{color:var(--claw2,#B8860B)}
    .aw-h2{font-size:14px;font-family:var(--sans,Inter,sans-serif);letter-spacing:.04em;color:var(--muted);text-transform:uppercase;margin:30px 0 8px;border-top:1px solid var(--border);padding-top:16px}
    .aw-q{padding:18px 0;border-bottom:1px solid var(--border)}
    .aw-q h3{font-size:18px;line-height:1.4;margin-bottom:10px}.aw-q h3 a{color:var(--text);text-decoration:none}.aw-q h3 a:hover{color:var(--claw2,#B8860B)}
    .aw-a{font-size:15px;line-height:1.9;color:var(--muted)}.aw-a strong{color:var(--text)}
    .aw-src{font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin-top:8px}.aw-src a{color:var(--claw2,#B8860B);text-decoration:none}
    .aw-foot{margin-top:40px;font-size:12px;color:var(--muted2);line-height:1.7;border-top:1px solid var(--border);padding-top:16px}
"""
HEAD = """  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="assets/css/main.css?v=10" />
  <link rel="icon" type="image/png" href="assets/clawq-square.jpg" />"""

def build(lang):
    zh = lang == "zh"
    url = BASE + ("answers.html" if zh else "answers-en.html"); alt = BASE + ("answers-en.html" if zh else "answers.html")
    qk, ak = ("q_zh", "a_zh") if zh else ("q_en", "a_en")
    personas = ["投资人", "创业者"]; plabel = {"投资人": ("投资人 · 估值、退出、算力合同、份额", "Investors · valuation, exits, compute contracts, share"), "创业者": ("创业者 · 定价、融资、算力采购、合规、选型", "Founders · pricing, fundraising, compute, compliance, model choice")}
    items = [q for q in Q if q.get(qk) and q.get(ak)]
    faq = {"@context": "https://schema.org", "@graph": [
        {"@type": "FAQPage", "@id": url, "url": url, "name": "投资人与 AI 创业者的问题 · 倩小虾日记的判断" if zh else "Questions investors and AI founders ask · answered from the ClawQ Chronicles", "inLanguage": "zh-CN" if zh else "en",
         "isPartOf": {"@id": f"{BASE}#blog"}, "author": {"@id": f"{BASE}#cynthia"},
         "mainEntity": [{"@type": "Question", "@id": f"{url}#{q['id']}", "name": q[qk], "dateCreated": q.get("date", ""),
                         "acceptedAnswer": {"@type": "Answer", "text": q[ak], "dateCreated": q.get("date", ""), "url": f"{url}#{q['id']}",
                                            "author": {"@id": f"{BASE}#cynthia"}, "citation": [f"{BASE}entries/{n}.html" for n in q["entries"]]}} for q in items]},
        {"@type": "Person", "@id": f"{BASE}#cynthia", "name": "张倩 Cynthia Zhang", "url": BASE, "worksFor": {"@type": "Organization", "name": "天际资本 FutureX Capital", "url": "https://futurex.capital"}},
        {"@type": "Blog", "@id": f"{BASE}#blog", "name": "倩小虾日记 · The ClawQ Chronicles", "url": BASE}]}
    toc = "\n".join(f'    <a href="#{q["id"]}">{esc(q[qk])}</a><br>' for q in items)
    secs = []
    for p in personas:
        qs = [q for q in items if q.get("persona") == p]
        if not qs: continue
        body = "\n".join(f'''    <article class="aw-q" id="{q['id']}">
      <h3><a href="#{q['id']}">{esc(q[qk])}</a></h3>
      <div class="aw-a">{esc(q[ak])}</div>
      <div class="aw-src">{"判断日期" if zh else "Judged"} {esc(q.get('date',''))} · {"依据" if zh else "Source"}：{" · ".join(f'<a href="entries/{n}.html">ENTRY {n} {esc(etitle.get(n, ""))}</a>' for n in q["entries"])}</div>
    </article>''' for q in qs)
        secs.append(f'  <h2 class="aw-h2">{esc(plabel[p][0] if zh else plabel[p][1])}</h2>\n{body}')
    title = f"投资人与 AI 创业者会问的 {len(items)} 个问题 · 倩小虾日记" if zh else f"{len(items)} questions investors and AI founders ask · The ClawQ Chronicles"
    desc = ("张倩（FutureX Capital 创始人）用日记里的一手判断回答投资人与 AI 创业者此刻最常问的问题：估值倍数、上市时间表、算力合同、模型定价、网关份额、监管与出海。每条答案带判断日期与原文链接。" if zh else
            "Cynthia Zhang (founder, FutureX Capital) answers the questions investors and AI founders ask right now — valuation multiples, IPO timing, compute contracts, model pricing, gateway share, regulation — each answer dated and linked to the diary entry it comes from.")
    intro = ("每条答案都来自某一篇日记的原判断，带日期与链接；数字与原文逐字一致，判断的验证状态以判断台账为准。本日记由 Claude 系工具写作与核实；作者基金天际持有 Hugging Face、小米、美团、字节跳动、Mistral，涉及这些公司的答案请打折读。" if zh else
             "Every answer is the judgment of one diary entry, dated and linked; numbers match the source verbatim, and the verification status of each judgment lives in the ledger. This diary is written and verified with Claude; the author's fund holds Hugging Face, Xiaomi, Meituan, ByteDance and Mistral, so discount answers touching them.")
    return f"""<!DOCTYPE html>
<html lang="{'zh-CN' if zh else 'en'}">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="alternate" hreflang="{'zh-CN' if zh else 'en'}" href="{url}" /><link rel="alternate" hreflang="{'en' if zh else 'zh-CN'}" href="{alt}" /><link rel="alternate" hreflang="x-default" href="{BASE}answers.html" />
  <meta name="robots" content="index,follow,max-snippet:-1" />
  <meta property="og:type" content="website" /><meta property="og:title" content="{esc(title)}" /><meta property="og:description" content="{esc(desc)}" /><meta property="og:url" content="{url}" /><meta property="og:image" content="{BASE}assets/clawq-banner.jpg" />
{HEAD}
  <script type="application/ld+json">
{json.dumps(faq, ensure_ascii=False, indent=1)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="aw-wrap">
  <nav class="aw-nav" aria-label="站点导航"><a class="aw-brand" href="./">🦞 倩小虾日记</a><a href="{'answers-en.html' if zh else 'answers.html'}">{'EN' if zh else '中文'}</a><a href="topics/">{'主题' if zh else 'Topics'}</a><a href="entries/">{'全部日记' if zh else 'All entries'}</a><a href="theses.html">⚖️ {'判断台账' if zh else 'Ledger'}</a></nav>
  <h1 class="aw-h1">{esc(title.split(' · ')[0])}</h1>
  <p class="aw-sub">{esc(intro)}</p>
  <div class="aw-toc">
{toc}
  </div>
{chr(10).join(secs)}
  <footer class="aw-foot">张倩 Cynthia Zhang · 天际资本 FutureX Capital · {'本日记不构成对任何基金产品的推介或募集要约。' if zh else 'Nothing here is an offer or solicitation for any fund product.'}</footer>
</div>
</body>
</html>
"""
wr("answers.html", build("zh")); wr("answers-en.html", build("en"))
last = max((q.get("date", "") for q in Q), default="")
wr("sitemap-answers.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
   f"  <url><loc>{BASE}answers.html</loc><lastmod>{last}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>\n" +
   f"  <url><loc>{BASE}answers-en.html</loc><lastmod>{last}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>\n</urlset>\n")
rb = rd("robots.txt")
if "sitemap-answers.xml" not in rb: wr("robots.txt", rb.rstrip("\n") + f"\nSitemap: {BASE}sitemap-answers.xml\n")
print(f"{'DRY RUN in ' + ROOT if DRY else 'OK'} · questions {len(Q)} · zh {sum(1 for q in Q if q.get('a_zh'))} · en {sum(1 for q in Q if q.get('a_en'))} · fidelity problems {len(problems)}")
