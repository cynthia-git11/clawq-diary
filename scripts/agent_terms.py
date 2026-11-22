#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent wording (2026-11-23, the author: 「所有用AI智能体替代…，不再出现…」).

The diary calls an agent 「AI智能体」 (en "AI agent", ja 「AIエージェント」) and uses 🤖 as its mark. The retired nickname — the
two-character Chinese word, its emoji, the English and Japanese words for it — is spelled in this file only through escapes
(RETIRED_*, and {L} {E} {W} {J} placeholders in the self-test), because scripts/ is served by GitHub Pages too and geo-check.py
check 12 fails on any served file that contains it. 倩小虾 (the diary's name), 虾友 (its readers) and the ClawQ brand are not touched.
"Agent" / "AI Agent" stay ordinary words; only the retired nickname is rewritten.

  fix(text)       → text with the retired wording replaced; idempotent. Chinese: the diminutive (小 + the word, a common name for
                    OpenClaw) and an 「AI」 prefix fold into the word; a gloss next to an existing agent word is dropped
                    (「…（AI Agent）」, 「AI Agent（…）」 → one term); a measure word 只/条 before the word becomes 个
                    (「1 只…」→「1 个 AI智能体」, 「上百只…」→「上百个 AI智能体」), and 只 before Agent / AI智能体 becomes 个 too;
                    「…之父」 (OpenClaw's creator) becomes 「OpenClaw 之父」; 「养」+ the one-character short form becomes
                    「养 AI智能体」; a space goes in front of the new word after a digit, a Latin letter or a Chinese character
                    (the site writes 「的 AI Agent」), except in the compound 「天际AI智能体」. English: "AI …" / "… agent" /
                    "… (AI agent)" / "AI agent (…)" collapse to one "AI agent"; "a …" → "an AI agent" in any case.
                    Japanese: 「AI」+ the word folds too. Never inside a link: href / src / srcset / action / poster / cite values
                    and bare http(s) URLs are left as they are, so a source link is never broken — hits() still reports it, and
                    the make_daily.py gate / buildN.py assert / geo-check.py check 12 stop the page so the author picks another
                    source or drops the link.
  hits(text)      → the retired tokens still present anywhere, links included (what geo-check.py check 12 tests), [] when clean.
  url_hits(text)  → the subset of hits() that sit inside a link (fix() leaves those alone on purpose).
  measure_hits(t) → 只 used as the measure word for an agent (「一只 AI Agent」) — the house style is 个.

Used by buildN.py (every parts.json field before it writes, then asserts hits() is empty), make_daily.py (every draft field,
then a gate) and i18n_daily.py (the en / ja rows). Deterministic, no I/O.
CLI: python3 scripts/agent_terms.py FILE...   (prints the hits)   ·   python3 scripts/agent_terms.py --selftest"""
import re, sys

RETIRED_ZH = "\u9f99\u867e"            # the retired Chinese word
RETIRED_SHORT = "\u867e"               # its one-character short form (only in the 「养…」 phrase; 倩小虾 / 虾友 stay)
RETIRED_EMOJI = "\U0001F99E"           # the retired emoji
RETIRED_EN = "\u006cobster"            # the retired English word (any case, singular or plural)
RETIRED_JA = ("\u30ed\u30d6\u30b9\u30bf\u30fc", "\u30b6\u30ea\u30ac\u30cb")
RETIRED_PCT = tuple("".join("%%%02X" % b for b in w.encode("utf-8")) for w in (RETIRED_ZH, RETIRED_EMOJI))  # percent-encoded (links)

ZH, EMOJI, EN, EN_TITLE, EN_PL, JA = "AI智能体", "\U0001F916", "AI agent", "AI Agent", "AI agents", "AIエージェント"

_L, _S, _W = RETIRED_ZH, RETIRED_SHORT, RETIRED_EN
_NUM = "一二三四五六七八九十两几每某这那哪多百千万数半0-9０-９"
_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
# links: attribute values that hold a URL, and bare http(s) URLs (stop at whitespace, quotes, brackets, CJK punctuation)
_URL = re.compile(r"""\b(?:href|src|srcset|action|poster|cite)\s*=\s*(?:"[^"]*"|'[^']*')"""
                  r"""|https?://[^\s"'<>()\[\]{}（）「」『』【】《》，。；：！？、]+""", re.I)
# Chinese
_DIMINUTIVE = re.compile("小" + _L)                                         # the common nickname → the word
_AI_PREFIX = re.compile(r"(?<![A-Za-z])AI ?" + _L)                           # 「AI + the word」 → the word (not OpenAI + it)
_GLOSS_AFTER = re.compile(_L + r" ?[（(] ?(?:AI ?)?(?:Agent|智能体|AI智能体) ?[)）]", re.I)   # 「the word（AI Agent）」 → the word
_GLOSS_BEFORE = re.compile(r"((?:AI ?)?(?:Agent|智能体)) ?[（(] ?" + _L + r" ?[)）]", re.I)  # 「AI Agent（the word）」 → AI Agent
_AGENT_AFTER = re.compile(_L + r" ?(?:AI ?)?Agents?\b(?: (?=[㐀-䶿一-鿿豈-﫿]))?")  # 「the word Agent 框架」 → 「the word框架」
_MEASURE = re.compile(r"(?<=[" + _NUM + r"])( ?)[只条]( ?)" + _L)
_MEASURE_AGENT = re.compile(r"(?<=[" + _NUM + r"])( ?)只(?= ?(?:AI ?)?(?:Agent|智能体))")
_FATHER = re.compile(_L + "之父")
_RAISE = re.compile("养" + _S + "(?!友)")
_WORD = re.compile(_L)
# English
_EN_GLOSS = re.compile(r"\b" + _W + r"(s?) \(AI agent(s?)\)", re.I)          # "… (AI agent)" → "AI agent"
_EN_GLOSS_BEFORE = re.compile(r"\b(AI agent)(s?) \(" + _W + r"s?\)", re.I)    # "AI agent (…)" → "AI agent"
_EN_AI = re.compile(r"\bAI (" + _W + r"s?)\b", re.I)                         # "AI …" → "…" (then → "AI agent")
_EN_AGENT = re.compile(r"\b(" + _W + r")(s?) (agent)(s?)\b", re.I)            # "… agent(s)" → "…(s)"
_EN_ARTICLE = re.compile(r"\b([Aa]) (?=(?i:" + _W + r"))")
_EN_WORD = re.compile(_W + r"(s?)", re.I)
# Japanese
_JA_AI = re.compile(r"(?<![A-Za-z])AI ?(?:" + "|".join(re.escape(x) for x in RETIRED_JA) + ")")

_TOKENS = [re.escape(RETIRED_ZH), re.escape(RETIRED_EMOJI), _W] + [re.escape(x) for x in RETIRED_JA] + [re.escape(x) for x in RETIRED_PCT]
_HITS = re.compile("|".join(_TOKENS), re.I)
_MEASURE_HITS = re.compile(r"[" + _NUM + r"] ?只 ?(?:AI ?)?(?:Agent|智能体)")


def _space_before(text, i):
    """a space goes in front of a Latin-initial word at text[i] after a digit / Latin letter / Chinese character, not after 天际"""
    if i == 0:
        return ""
    p = text[i - 1]
    if text[max(0, i - 2):i] == "天际":
        return ""
    return " " if (p.isascii() and p.isalnum()) or _CJK.match(p) else ""


def _spaced(rx, new, text):
    return rx.sub(lambda m: _space_before(text, m.start()) + new, text)


def _en_word(m):
    w, pl = m.group(0), m.group(1)
    if w.isupper():
        return (EN_PL if pl else EN).upper()
    if pl:
        return EN_PL                                   # "…s are not productivity tools" → "AI agents are …"
    return EN_TITLE if w[0].isupper() else EN          # "The … Organization" → "The AI Agent Organization"


def _keep_agent(m):
    """「AI Agent（the word）是…」 → 「AI Agent 是…」: drop the gloss, keep the site's space between a Latin word and Chinese"""
    g, nxt = m.group(1), m.string[m.end():m.end() + 1]
    return g + (" " if g[-1].isascii() and nxt and _CJK.match(nxt) else "")


def _fix_prose(text):
    """the rewrite on text that holds no link"""
    text = text.replace(RETIRED_EMOJI, EMOJI)
    # Chinese: fold the variants into the bare word first, so the measure / spacing rules below see one form
    text = text.replace("OpenClaw 作者（" + _L + "之父）", "OpenClaw 作者")      # the gloss would only repeat the name
    text = _DIMINUTIVE.sub(_L, text)
    text = _AI_PREFIX.sub(_L, text)
    text = _GLOSS_AFTER.sub(_L, text)
    text = _GLOSS_BEFORE.sub(_keep_agent, text)
    text = _AGENT_AFTER.sub(_L, text)
    text = _MEASURE.sub(lambda m: m.group(1) + "个 " + ZH, text)
    text = _MEASURE_AGENT.sub(lambda m: m.group(1) + "个", text)
    text = _spaced(_FATHER, "OpenClaw 之父", text)
    text = _RAISE.sub("养 " + ZH, text)
    text = _spaced(_WORD, ZH, text)
    # English
    text = _EN_GLOSS.sub(lambda m: EN_PL if (m.group(1) or m.group(2)) else EN, text)
    text = _EN_GLOSS_BEFORE.sub(lambda m: m.group(1) + m.group(2), text)
    text = _EN_AI.sub(lambda m: m.group(1), text)
    text = _EN_AGENT.sub(lambda m: m.group(1) + (m.group(2) or m.group(4)), text)
    text = _EN_ARTICLE.sub(lambda m: m.group(1) + "n ", text)
    text = _EN_WORD.sub(_en_word, text)
    # Japanese
    text = _JA_AI.sub(JA, text)
    for w in RETIRED_JA:
        text = text.replace(w, JA)
    return text


def fix(text):
    """the retired wording → 「AI智能体」 / 🤖 / "AI agent" / 「AIエージェント」 outside links; idempotent"""
    if not text or not (_HITS.search(text) or ("养" + _S) in text or _MEASURE_HITS.search(text)):
        return text
    out, last = [], 0
    for m in _URL.finditer(text):
        out.append(_fix_prose(text[last:m.start()]))
        out.append(m.group(0))                         # a link is never rewritten
        last = m.end()
    out.append(_fix_prose(text[last:]))
    return "".join(out)


def hits(text):
    """the retired tokens still in text, links included ([] when clean)"""
    return _HITS.findall(text or "")


def url_hits(text):
    """the retired tokens that sit inside a link (fix() leaves links alone)"""
    return [h for m in _URL.finditer(text or "") for h in _HITS.findall(m.group(0))]


def measure_hits(text):
    """只 as the measure word for an agent (「一只 AI Agent」); the house style is 个"""
    return _MEASURE_HITS.findall(text or "")


# ── self-test (python3 scripts/agent_terms.py --selftest; geo-check.py check 12 runs it too) ──────────────────────────────
# {L} the Chinese word · {E} the emoji · {W} the English word · {J} the Japanese word — filled in at run time.
_CASES = [
    ("1 只{L}", "1 个 AI智能体"),
    ("上百只{L}在跑", "上百个 AI智能体在跑"),
    ("多只{L}", "多个 AI智能体"),
    ("每人至少一只{L}，最厉害的养了八只", "每人至少一个 AI智能体，最厉害的养了八只"),
    ("小{L}会写验收标准吗？", "AI智能体会写验收标准吗？"),
    ("一只小{L}", "一个 AI智能体"),
    ("AI {L}与小{L}：", "AI智能体与 AI智能体："),
    ("的AI{L}", "的 AI智能体"),
    ("{L}（AI Agent）是什么", "AI智能体是什么"),
    ("AI Agent（{L}）是什么", "AI Agent 是什么"),
    ("OpenAI{L}", "OpenAI AI智能体"),
    ("{L} Agent 框架", "AI智能体框架"),
    ("{L}们", "AI智能体们"),
    ("天际{L}组织成长史", "天际AI智能体组织成长史"),
    ("OpenClaw 作者（{L}之父）", "OpenClaw 作者"),
    ("{L}之父", "OpenClaw 之父"),
    ("养虾", "养 AI智能体"),
    ("虾友 倩小虾", "虾友 倩小虾"),
    ("一只 AI Agent 帮我", "一个 AI Agent 帮我"),
    ("由一只 Agent 维护", "由一个 Agent 维护"),
    ("整条 Agent 链路", "整条 Agent 链路"),
    ("我的{E}", "我的\U0001F916"),
    ("a {W} squad", "an AI agent squad"),
    ("a {W_T} Squad", "an AI Agent Squad"),
    ("A {W} walks", "An AI agent walks"),
    ("1 {W} (AI agent)", "1 AI agent"),
    ("AI agent ({W})", "AI agent"),
    ("AI {W}s and {W} agents", "AI agents and AI agents"),
    ("{W_T}s are not productivity tools", "AI agents are not productivity tools"),
    ("The {W_T} Organization", "The AI Agent Organization"),
    ("AI{J}と{J}", "AIエージェントとAIエージェント"),
    ('<a href="https://x.com/openclaw-{W}-agents/">{W}</a>', '<a href="https://x.com/openclaw-{W}-agents/">AI agent</a>'),
    ("见 https://x.com/q={PCT}，{L}", "见 https://x.com/q={PCT}，AI智能体"),
    ('<img src="a-{W}.jpg" alt="{L}">', '<img src="a-{W}.jpg" alt="AI智能体">'),
]


def _selftest():
    sub = {"L": RETIRED_ZH, "E": RETIRED_EMOJI, "W": RETIRED_EN, "W_T": RETIRED_EN.title(), "J": RETIRED_JA[0], "PCT": RETIRED_PCT[0]}
    bad = []
    for src, want in _CASES:
        s, w = src.format(**sub), want.format(**sub)
        got = fix(s)
        if got != w:
            bad.append(f"fix({s!r}) = {got!r}, want {w!r}")
        elif fix(got) != got:
            bad.append(f"fix not idempotent on {s!r}")
    link = '<a href="https://x.com/{W}">t</a>'.format(**sub)
    if url_hits(link) != [RETIRED_EN] or url_hits(fix("{L}".format(**sub))):
        bad.append("url_hits")
    if measure_hits("一只 AI Agent") != ["一只 AI Agent"] or measure_hits("整条 Agent"):
        bad.append("measure_hits")
    return bad


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        b = _selftest()
        print("\n".join(b) if b else f"agent_terms self-test: {len(_CASES)} cases ok")
        sys.exit(1 if b else 0)
    bad = 0
    for f in sys.argv[1:]:
        h = hits(open(f, encoding="utf-8").read())
        if h:
            bad += 1
            print(f"{f}: {len(h)}")
    sys.exit(1 if bad else 0)
