#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO: one page per question, for investors and AI founders (zh + en).

Input : data/answers.json  — list of items:
        {id, slug(optional; frozen on first build), persona_group ("投资人"|"创业者"), persona, q_zh, q_en, date (YYYY-MM-DD),
         entries [int], topics [slug from data/topics.json], related [ids],
         lead_zh, judgment_zh, facts_zh, landing_zh, falsify_zh (verbatim from the ENTRY footnote), status_zh,
         lead_en, judgment_en, facts_en, landing_en, falsify_en}
Reads : index.html (number-fidelity gate: every number in every text field must appear verbatim in a cited ENTRY, allowing
        亿↔B/M unit conversions ×/÷10,100,1000), data/topics.json (entity names + fixed disclosure sentences)
Writes: answers/<slug>.html, answers/en/<slug>.html, answers/index.html, answers/en/index.html, sitemap-answers.xml,
        robots.txt Sitemap line if missing. Slugs are frozen into data/answers.json on first build (never renamed after publish).
Usage : python3 scripts/gen-answers.py [--root DIR] [--dry] [--no-verify]
"""
import re, os, sys, json, html, shutil, tempfile

BASE = "https://cynthia-git11.github.io/clawq-diary/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv: ROOT = sys.argv[sys.argv.index("--root") + 1]
DRY = "--dry" in sys.argv; VERIFY = "--no-verify" not in sys.argv
SRC = ROOT
if DRY:
    W = tempfile.mkdtemp(prefix="answers-")
    for f in ["index.html", "robots.txt"]: shutil.copy(os.path.join(ROOT, f), W)
    shutil.copytree(os.path.join(ROOT, "data"), os.path.join(W, "data"))
    ROOT = W
def rd(f): return open(os.path.join(ROOT, f), encoding="utf-8").read()
def wr(f, s):
    p = os.path.join(ROOT, f); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(s)
def strip(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
def esc(s): return html.escape(s or "", quote=True)

Q = json.load(open(os.path.join(ROOT, "data/answers.json"), encoding="utf-8"))
TOPICS = {t["slug"]: t for t in json.load(open(os.path.join(ROOT, "data/topics.json"), encoding="utf-8"))}
idx = rd("index.html")
def block_at(s, start):
    i = start; depth = 0; tag = re.compile(r"<(/?)div\b[^>]*>", re.I)
    while True:
        m = tag.search(s, i); depth += -1 if m.group(1) else 1; i = m.end()
        if depth == 0: return i
etext = {}; etitle = {}; edate = {}
for m in re.finditer(r'<div id="entry-(\d+)"[^>]*>', idx):
    n = int(m.group(1)); blk = idx[m.start():block_at(idx, m.start())]
    etext[n] = strip(blk).replace(",", "").replace("，", ""); etitle[n] = strip((re.search(r'<h3 class="entry-title">(.*?)</h3>', blk, re.S) or [None, ""])[1])
    dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", blk); edate[n] = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}" if dm else ""

# ---------- slugs: frozen on first build ----------
STOP = set("a an the is are was were be been do does did has have had can could should would will may might of to in on for from by with as at and or vs vs. how what when why who which where whether if it its my our their this that these those i we you they them there here than then into over under about after before between still yet does".split())
def slugify(q):
    words = [w for w in re.sub(r"[^a-z0-9\s\-]", " ", q.lower()).split() if w not in STOP and len(w) > 1]
    return "-".join(words[:6]) or "q"
seen = set(); changed = False
for q in Q:
    if not q.get("slug"):
        s = slugify(q["q_en"]); base = s; k = 2
        while s in seen: s = f"{base}-{k}"; k += 1
        q["slug"] = s; changed = True
    seen.add(q["slug"])
if changed and not DRY:
    json.dump(Q, open(os.path.join(SRC, "data/answers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
assert len(seen) == len(Q), "duplicate slugs"

# ---------- number-fidelity gate ----------
FIELDS_ZH = ["lead_zh", "judgment_zh", "facts_zh", "landing_zh", "falsify_zh", "status_zh"]
FIELDS_EN = ["lead_en", "judgment_en", "facts_en", "landing_en", "falsify_en"]
NUM = re.compile(r"\d+(?:\.\d+)?")
SMALL = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "24", "30", "60", "90", "100"}
problems = []
for q in Q:
    q["entries"] = [int(n) for n in q["entries"]]
    cited = " ".join(etext.get(n, "") for n in q["entries"])
    for n in q["entries"]:
        if n not in etext: problems.append(f"{q['id']}: cites ENTRY {n} which does not exist")
    for t in q.get("topics", []):
        if t not in TOPICS: problems.append(f"{q['id']}: unknown topic slug {t}")
    for f in FIELDS_ZH + FIELDS_EN:
        txt = (q.get(f) or "").replace(",", "")
        txt = re.sub(r"ENTRY\s*\d+(?:\s*[/、和与&]\s*\d+)*", " ", txt)   # entry ids are references, not data
        for tok in set(NUM.findall(txt)):
            if tok in SMALL or re.fullmatch(r"20\d\d", tok): continue
            # unit conversions the English side makes: 亿↔B/M (×/÷10, 100, 1000) and 万↔absolute (×/÷10000)
            v = float(tok); alts = {tok} | {f"{v*10:g}", f"{v/10:g}", f"{v*100:g}", f"{v/100:g}", f"{v*1000:g}", f"{v/1000:g}", f"{v*10000:g}", f"{v/10000:g}"}
            if not any(a in cited for a in alts): problems.append(f"{q['id']} {f}: number {tok} not found in cited entries {q['entries']}")
if VERIFY and problems:
    print("NUMBER-FIDELITY GATE FAILED:"); [print("  ✗", p) for p in problems]; sys.exit(1)

# ---------- disclosure (fixed template, from data/topics.json) ----------
CLAUDE_ZH = "本日记由 Claude 系工具写作与核实，涉及 Anthropic 的判断（有利或不利）都请打折读"
CLAUDE_EN = "This diary is written and verified with Claude; discount any judgment about Anthropic, favourable or not"
def disclosure(q, zh):
    parts = [CLAUDE_ZH if zh else CLAUDE_EN]
    held = []
    for t in q.get("topics", []):
        d = TOPICS.get(t, {}).get("disclosure" if zh else "disclosure_en")
        if not d or t == "anthropic": continue          # the Claude sentence above already covers Anthropic
        d = re.sub(r"^本日记由 Claude 系工具写作(与核实)?，", "", d); d = re.sub(r"^This diary is written with Claude, which", "Claude", d)
        if d and d not in held: held.append(d)
    parts += held
    if not held: parts.append("本题涉及的公司，按公开可查信息天际（FutureX Capital）不持有" if zh else "FutureX Capital does not, on publicly available information, hold the companies discussed here")
    return ("利益披露：" if zh else "Disclosure: ") + ("；".join(parts) if zh else "; ".join(parts)) + ("。" if zh else ".")

CSS = """
    .aw-wrap{max-width:820px;margin:0 auto;padding:28px 18px 60px}
    .aw-nav{font-family:var(--sans,Inter,sans-serif);font-size:13px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:18px;color:var(--muted)}
    .aw-nav a{color:var(--claw2,#B8860B);text-decoration:none;font-weight:600}.aw-nav .aw-brand{font-weight:800;color:var(--text);font-size:15px}
    .aw-crumb{font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin-bottom:14px}.aw-crumb a{color:var(--muted2);text-decoration:none}
    h1.aw-h1{font-size:26px;line-height:1.35;margin-bottom:10px}
    .aw-meta{font-family:var(--sans,Inter,sans-serif);font-size:12.5px;color:var(--muted2);margin-bottom:20px;line-height:1.8}.aw-meta time{color:var(--muted)}
    .aw-lead{font-size:17px;line-height:1.85;color:var(--text);font-weight:600;margin-bottom:22px;padding:14px 16px;border-left:3px solid var(--claw2,#B8860B);background:var(--panel,rgba(0,0,0,.03))}
    .aw-h2{font-size:13px;font-family:var(--sans,Inter,sans-serif);letter-spacing:.06em;color:var(--muted);text-transform:uppercase;margin:26px 0 8px}
    .aw-p{font-size:15.5px;line-height:1.9;color:var(--muted)}.aw-p strong{color:var(--text)}
    .aw-falsify{font-size:13.5px;line-height:1.8;color:var(--muted);padding:12px 14px;border:1px dashed var(--border);border-radius:6px;margin-top:6px}
    .aw-status{font-family:var(--sans,Inter,sans-serif);font-size:13px;color:var(--text);margin-top:8px}
    .aw-disc{font-size:12.5px;line-height:1.75;color:var(--muted2);margin-top:26px;padding-top:14px;border-top:1px solid var(--border)}
    .aw-src,.aw-rel{font-family:var(--sans,Inter,sans-serif);font-size:13px;color:var(--muted);line-height:1.9;margin-top:14px}.aw-src a,.aw-rel a{color:var(--claw2,#B8860B);text-decoration:none}
    .aw-foot{margin-top:40px;font-size:12px;color:var(--muted2);line-height:1.7;border-top:1px solid var(--border);padding-top:16px}
    .aw-list{list-style:none;padding:0;margin:0 0 26px}.aw-list li{padding:12px 0;border-bottom:1px solid var(--border)}
    .aw-list a{font-size:16px;color:var(--text);text-decoration:none;font-weight:600;line-height:1.5}.aw-list a:hover{color:var(--claw2,#B8860B)}
    .aw-list .aw-lp{font-size:14px;color:var(--muted);line-height:1.75;margin-top:4px}.aw-list .aw-ld{font-family:var(--sans,Inter,sans-serif);font-size:12px;color:var(--muted2);margin-top:4px}
"""
def head_links(depth):
    up = "../" * depth
    return f"""  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{up}assets/css/main.css?v=10" />
  <link rel="icon" type="image/png" href="{up}assets/clawq-square.jpg" />"""
PERSON = {"@type": "Person", "@id": f"{BASE}#cynthia", "name": "张倩 Cynthia Zhang", "url": BASE, "worksFor": {"@type": "Organization", "name": "天际资本 FutureX Capital", "url": "https://futurex.capital"}}
BLOG = {"@type": "Blog", "@id": f"{BASE}#blog", "name": "倩小虾日记 · The ClawQ Chronicles", "url": BASE}
BYID = {q["id"]: q for q in Q}

def nav(zh, depth, alt_href):
    up = "../" * depth
    L = (["🦞 倩小虾日记", "问答", "EN", "主题", "全部日记", "⚖️ 判断台账"] if zh else ["🦞 The ClawQ Chronicles", "Q&A", "中文", "Topics", "All entries", "⚖️ Ledger"])
    idxh = f"{up}answers/" if zh else f"{up}answers/en/"
    return (f'<nav class="aw-nav" aria-label="nav"><a class="aw-brand" href="{up}">{L[0]}</a><a href="{idxh}">{L[1]}</a><a href="{alt_href}">{L[2]}</a>'
            f'<a href="{up}topics/">{L[3]}</a><a href="{up}entries/">{L[4]}</a><a href="{up}theses.html">{L[5]}</a></nav>')

def page(q, zh):
    depth = 1 if zh else 2; up = "../" * depth
    url = BASE + (f"answers/{q['slug']}.html" if zh else f"answers/en/{q['slug']}.html")
    alt = BASE + (f"answers/en/{q['slug']}.html" if zh else f"answers/{q['slug']}.html")
    alt_rel = f"en/{q['slug']}.html" if zh else f"../{q['slug']}.html"
    g = lambda k: q.get(k + ("_zh" if zh else "_en")) or ""
    title = g("q"); lead, judg, facts, land, fals = g("lead"), g("judgment"), g("facts"), g("landing"), g("falsify")
    status = q.get("status_zh", "")
    answer_txt = " ".join(x for x in [lead, judg, facts, land] if x)
    desc = (lead if len(lead) <= 300 else lead[:297] + "…")
    date = q.get("date") or max((edate.get(n, "") for n in q["entries"]), default="")
    src = " · ".join(f'<a href="{up}entries/{n}.html">ENTRY {n} · {esc(etitle.get(n, ""))}</a>' for n in q["entries"])
    rel = [BYID[r] for r in q.get("related", []) if r in BYID and r != q["id"]]
    rel_html = "".join(f'<li><a href="{(r["slug"] + ".html") if zh else (r["slug"] + ".html")}">{esc(r["q_zh"] if zh else r["q_en"])}</a></li>' for r in rel)
    tops = [TOPICS[t] for t in q.get("topics", []) if t in TOPICS]
    tops_html = " · ".join(f'<a href="{up}topics/{t["slug"]}.html">{esc(t["name"] if zh else t["name_en"])}</a>' for t in tops if os.path.exists(os.path.join(SRC, "topics", t["slug"] + ".html")))
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": ["WebPage", "FAQPage"], "@id": url, "url": url, "name": title, "headline": title, "description": desc, "inLanguage": "zh-CN" if zh else "en",
         "datePublished": date, "dateModified": date, "isPartOf": {"@id": f"{BASE}#blog"}, "author": {"@id": f"{BASE}#cynthia"},
         "about": [{"@type": "Organization", "name": t["name_en"] if not zh else t["name"], "url": t.get("url", "")} if t.get("url") else {"@type": "Thing", "name": t["name_en"] if not zh else t["name"]} for t in tops],
         "citation": [f"{BASE}entries/{n}.html" for n in q["entries"]],
         "speakable": {"@type": "SpeakableSpecification", "cssSelector": ["h1.aw-h1", ".aw-lead"]},
         "mainEntity": [{"@type": "Question", "@id": f"{url}#q", "name": title, "dateCreated": date, "author": {"@id": f"{BASE}#cynthia"},
                         "acceptedAnswer": {"@type": "Answer", "text": answer_txt, "dateCreated": date, "url": url, "author": {"@id": f"{BASE}#cynthia"},
                                            "citation": [f"{BASE}entries/{n}.html" for n in q["entries"]]}}]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "倩小虾日记" if zh else "The ClawQ Chronicles", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": "问答" if zh else "Q&A", "item": BASE + ("answers/" if zh else "answers/en/")},
            {"@type": "ListItem", "position": 3, "name": title, "item": url}]},
        PERSON, BLOG]}
    L = {"lead": "", "judg": "判断" if zh else "Judgment", "facts": "事实" if zh else "Facts", "land": "落点" if zh else "What to do", "fals": "证伪口（逐字取自日记尾注）" if zh else "Falsifier (verbatim from the diary footnote)",
         "status": "台账状态" if zh else "Ledger status", "src": "原文" if zh else "Source entries", "rel": "相关问题" if zh else "Related questions", "topics": "主题页" if zh else "Topic pages",
         "judged": "判断日期" if zh else "Judged", "who": "提问者" if zh else "Asked by", "home": "首页" if zh else "Home", "qa": "问答" if zh else "Q&A"}
    sections = []
    if judg: sections.append(f'  <h2 class="aw-h2">{L["judg"]}</h2>\n  <p class="aw-p">{esc(judg)}</p>')
    if facts: sections.append(f'  <h2 class="aw-h2">{L["facts"]}</h2>\n  <p class="aw-p">{esc(facts)}</p>')
    if land: sections.append(f'  <h2 class="aw-h2">{L["land"]}</h2>\n  <p class="aw-p">{esc(land)}</p>')
    if fals: sections.append(f'  <h2 class="aw-h2">{L["fals"]}</h2>\n  <div class="aw-falsify">{esc(fals)}</div>' + (f'\n  <div class="aw-status">{L["status"]}：{esc(status)}</div>' if status else ""))
    elif status: sections.append(f'  <div class="aw-status">{L["status"]}：{esc(status)}</div>')
    return f"""<!DOCTYPE html>
<html lang="{'zh-CN' if zh else 'en'}">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)} · {'倩小虾日记' if zh else 'The ClawQ Chronicles'}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="alternate" hreflang="{'zh-CN' if zh else 'en'}" href="{url}" /><link rel="alternate" hreflang="{'en' if zh else 'zh-CN'}" href="{alt}" /><link rel="alternate" hreflang="x-default" href="{BASE}answers/{q['slug']}.html" />
  <meta name="robots" content="index,follow,max-snippet:-1" />
  <meta property="og:type" content="article" /><meta property="og:title" content="{esc(title)}" /><meta property="og:description" content="{esc(desc)}" /><meta property="og:url" content="{url}" /><meta property="og:image" content="{BASE}assets/clawq-banner.jpg" />
  <meta property="article:published_time" content="{date}" /><meta name="author" content="张倩 Cynthia Zhang" />
{head_links(depth)}
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="aw-wrap">
  {nav(zh, depth, alt_rel)}
  <div class="aw-crumb"><a href="{up}">{L["home"]}</a> › <a href="{'./' if zh else './'}">{L["qa"]}</a> › {esc(title[:40])}</div>
  <h1 class="aw-h1">{esc(title)}</h1>
  <div class="aw-meta">{L["who"]}：{esc(q.get("persona", ""))} · {L["judged"]} <time datetime="{date}">{date}</time> · 张倩 Cynthia Zhang · FutureX Capital</div>
  <p class="aw-lead">{esc(lead)}</p>
{chr(10).join(sections)}
  <div class="aw-disc">{esc(disclosure(q, zh))}</div>
  <div class="aw-src">{L["src"]}：{src}</div>
{('  <div class="aw-rel">' + L["rel"] + '：<ul>' + rel_html + '</ul></div>') if rel_html else ''}
{('  <div class="aw-rel">' + L["topics"] + '：' + tops_html + '</div>') if tops_html else ''}
  <footer class="aw-foot">张倩 Cynthia Zhang · 天际资本 FutureX Capital · {'本日记不构成对任何基金产品的推介或募集要约；数字与原文逐字一致，判断的验证状态以判断台账为准。' if zh else 'Nothing here is an offer or solicitation for any fund product; numbers match the source entry verbatim, and verification status lives in the ledger.'}</footer>
</div>
</body>
</html>
"""

def index_page(zh):
    depth = 1 if zh else 2; up = "../" * depth
    url = BASE + ("answers/" if zh else "answers/en/"); alt = BASE + ("answers/en/" if zh else "answers/")
    items = [q for q in Q if q.get("lead_zh" if zh else "lead_en")]
    groups = [("投资人", "投资人 · 估值、退出、算力合同、份额" if zh else "Investors · valuation, exits, compute contracts, share"),
              ("创业者", "创业者 · 定价、融资、算力采购、合规、选型" if zh else "Founders · pricing, fundraising, compute, compliance, model choice")]
    secs = []
    for key, label in groups:
        qs = [q for q in items if q.get("persona_group") == key]
        if not qs: continue
        lis = "\n".join(f'''    <li><a href="{q['slug']}.html">{esc(q['q_zh'] if zh else q['q_en'])}</a>
      <div class="aw-lp">{esc(q.get('lead_zh' if zh else 'lead_en') or '')}</div>
      <div class="aw-ld">{esc(q.get('date',''))} · {' · '.join('ENTRY ' + str(n) for n in q['entries'])}</div></li>''' for q in qs)
        secs.append(f'  <h2 class="aw-h2">{esc(label)}</h2>\n  <ul class="aw-list">\n{lis}\n  </ul>')
    title = f"投资人与 AI 创业者会问的 {len(items)} 个问题" if zh else f"{len(items)} questions investors and AI founders ask"
    desc = ("张倩（FutureX Capital 创始人）用日记里的一手判断回答投资人与 AI 创业者此刻最常问的问题：估值倍数、上市时间表、算力合同、模型定价、网关份额、监管与出海。一题一页，每页带判断日期、证伪口与原文链接。" if zh else
            "Cynthia Zhang (founder, FutureX Capital) answers the questions investors and AI founders ask right now — valuation multiples, IPO timing, compute contracts, model pricing, gateway share, regulation. One page per question, each dated, with its falsifier and a link to the diary entry it comes from.")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": url, "url": url, "name": title, "description": desc, "inLanguage": "zh-CN" if zh else "en", "isPartOf": {"@id": f"{BASE}#blog"}, "author": {"@id": f"{BASE}#cynthia"},
         "dateModified": max((q.get("date", "") for q in items), default=""),
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "name": q["q_zh"] if zh else q["q_en"], "url": BASE + (f"answers/{q['slug']}.html" if zh else f"answers/en/{q['slug']}.html")} for i, q in enumerate(items)]}},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "倩小虾日记" if zh else "The ClawQ Chronicles", "item": BASE}, {"@type": "ListItem", "position": 2, "name": "问答" if zh else "Q&A", "item": url}]},
        PERSON, BLOG]}
    intro = ("每条答案都来自某一篇日记的原判断，带日期与链接；数字与原文逐字一致，证伪口逐字取自尾注，判断的验证状态以判断台账为准。本日记由 Claude 系工具写作与核实；作者基金天际持有 Hugging Face、小米、美团（月之暗面为间接权益）、字节跳动、Mistral，涉及这些公司的答案请打折读。" if zh else
             "Every answer is the judgment of one diary entry, dated and linked; numbers match the source verbatim, falsifiers are copied from the footnotes, and verification status lives in the ledger. This diary is written and verified with Claude; the author's fund holds Hugging Face, Xiaomi, Meituan (an indirect Moonshot stake), ByteDance and Mistral, so discount answers touching them.")
    return f"""<!DOCTYPE html>
<html lang="{'zh-CN' if zh else 'en'}">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)} · {'倩小虾日记' if zh else 'The ClawQ Chronicles'}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="alternate" hreflang="{'zh-CN' if zh else 'en'}" href="{url}" /><link rel="alternate" hreflang="{'en' if zh else 'zh-CN'}" href="{alt}" /><link rel="alternate" hreflang="x-default" href="{BASE}answers/" />
  <meta name="robots" content="index,follow,max-snippet:-1" />
  <meta property="og:type" content="website" /><meta property="og:title" content="{esc(title)}" /><meta property="og:description" content="{esc(desc)}" /><meta property="og:url" content="{url}" /><meta property="og:image" content="{BASE}assets/clawq-banner.jpg" />
{head_links(depth)}
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
  <style>{CSS}  </style>
</head>
<body>
<div class="aw-wrap">
  {nav(zh, depth, 'en/' if zh else '../')}
  <h1 class="aw-h1">{esc(title)}</h1>
  <p class="aw-p" style="margin-bottom:22px">{esc(intro)}</p>
{chr(10).join(secs)}
  <footer class="aw-foot">张倩 Cynthia Zhang · 天际资本 FutureX Capital · {'本日记不构成对任何基金产品的推介或募集要约。' if zh else 'Nothing here is an offer or solicitation for any fund product.'}</footer>
</div>
</body>
</html>
"""

for q in Q:
    wr(f"answers/{q['slug']}.html", page(q, True)); wr(f"answers/en/{q['slug']}.html", page(q, False))
wr("answers/index.html", index_page(True)); wr("answers/en/index.html", index_page(False))
last = max((q.get("date", "") for q in Q), default="")
urls = [(f"{BASE}answers/", last, "0.9"), (f"{BASE}answers/en/", last, "0.8")]
for q in Q: urls += [(f"{BASE}answers/{q['slug']}.html", q.get("date", last), "0.8"), (f"{BASE}answers/en/{q['slug']}.html", q.get("date", last), "0.7")]
wr("sitemap-answers.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
   "".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod><changefreq>weekly</changefreq><priority>{p}</priority></url>\n" for u, d, p in urls) + "</urlset>\n")
rb = rd("robots.txt")
if "sitemap-answers.xml" not in rb and "sitemap-index.xml" not in rb: wr("robots.txt", rb.rstrip("\n") + f"\nSitemap: {BASE}sitemap-answers.xml\n")
print(f"{'DRY RUN in ' + ROOT if DRY else 'OK'} · questions {len(Q)} · pages {2*len(Q)+2} · fidelity problems {len(problems)}{' (bypassed)' if problems and not VERIFY else ''}")
