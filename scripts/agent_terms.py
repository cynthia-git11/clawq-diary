#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent wording (2026-11-23, the author: 「所有用AI智能体替代…，不再出现…」).

The diary calls an agent 「AI智能体」 (en "AI agent", ja 「AIエージェント」) and uses 🤖 as its mark. The retired nickname — the
two-character Chinese word, its emoji, the English and Japanese words for it — is spelled in this file only through escapes
(RETIRED_*), because scripts/ is served by GitHub Pages too and geo-check.py check 12 fails on any served file that contains it.
倩小虾 (the diary's name), 虾友 (its readers) and the ClawQ brand are not touched.

  fix(text)    → text with the retired wording replaced; idempotent. Chinese: a measure word 只/条 before the word becomes 个
                 (「1 只…」→「1 个 AI智能体」), the word's 「…之父」 (OpenClaw's creator) becomes 「OpenClaw 之父」, 「养」+ its
                 one-character short form becomes 「养 AI智能体」; a space goes in front of the new word after a digit, a Latin
                 letter or a Chinese character (the site writes 「的 AI Agent」), except in the compound 「天际AI智能体」
                 (「天际AI智能体组织成长史」). English: "a …" → "an AI agent", "… (AI agent)" collapses to "AI agent". Also the
                 percent-encoded forms inside share URLs.
  hits(text)   → the retired tokens still present (the same test geo-check.py check 12 applies), [] when clean.

Used by buildN.py (every parts.json field before it writes), make_daily.py (every draft field, then a gate) and i18n_daily.py
(the en / ja rows). Deterministic, no I/O. CLI for a quick look: python3 scripts/agent_terms.py FILE... (prints the hits)."""
import re, sys

RETIRED_ZH = "\u9f99\u867e"            # the retired Chinese word
RETIRED_SHORT = "\u867e"               # its one-character short form (only in the 「养…」 phrase; 倩小虾 / 虾友 stay)
RETIRED_EMOJI = "\U0001F99E"           # the retired emoji
RETIRED_EN = "\u006cobster"            # the retired English word (any case, singular or plural)
RETIRED_JA = ("\u30ed\u30d6\u30b9\u30bf\u30fc", "\u30b6\u30ea\u30ac\u30cb")
RETIRED_PCT = tuple("".join("%%%02X" % b for b in w.encode("utf-8")) for w in (RETIRED_ZH, RETIRED_EMOJI))  # percent-encoded (share links)

ZH, EMOJI, EN, EN_TITLE, EN_PL, JA = "AI智能体", "\U0001F916", "AI agent", "AI Agent", "AI agents", "AIエージェント"
PCT = {RETIRED_PCT[0]: "AI%E6%99%BA%E8%83%BD%E4%BD%93", RETIRED_PCT[1]: "%F0%9F%A4%96"}

_L, _S = RETIRED_ZH, RETIRED_SHORT
_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_MEASURE = re.compile(r"(?<=[一二三四五六七八九十两几每某这那哪\d])( ?)[只条]" + _L)
_FATHER = re.compile(_L + "之父")
_RAISE = re.compile("养" + _S + "(?!友)")
_WORD = re.compile(_L)
_EN_GLOSS = re.compile(r"\b" + RETIRED_EN + r"(s?) \(AI agent(s?)\)", re.I)
_EN_ARTICLE = re.compile(r"\b([Aa]) " + RETIRED_EN + r"\b")
_EN_WORD = re.compile(RETIRED_EN + r"(s?)", re.I)
_HITS = re.compile("|".join([re.escape(RETIRED_ZH), re.escape(RETIRED_EMOJI), RETIRED_EN] + [re.escape(x) for x in RETIRED_JA]
                            + [re.escape(x) for x in RETIRED_PCT]), re.I)


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


def fix(text):
    """the retired wording → 「AI智能体」 / 🤖 / "AI agent" / 「AIエージェント」; idempotent"""
    if not text or not _HITS.search(text) and ("养" + _S) not in text:
        return text
    for old, new in PCT.items():
        text = re.sub(re.escape(old), new, text, flags=re.I)
    text = text.replace(RETIRED_EMOJI, EMOJI)
    text = text.replace("OpenClaw 作者（" + _L + "之父）", "OpenClaw 作者")      # the gloss would only repeat the name
    text = _MEASURE.sub(lambda m: m.group(1) + "个 " + ZH, text)
    text = _spaced(_FATHER, "OpenClaw 之父", text)
    text = _RAISE.sub("养 " + ZH, text)
    text = _spaced(_WORD, ZH, text)
    text = _EN_GLOSS.sub(lambda m: EN_PL if (m.group(1) or m.group(2)) else EN, text)
    text = _EN_ARTICLE.sub(lambda m: m.group(1) + "n " + EN, text)
    text = _EN_WORD.sub(_en_word, text)
    for w in RETIRED_JA:
        text = text.replace(w, JA)
    return text


def hits(text):
    """the retired tokens still in text ([] when clean)"""
    return _HITS.findall(text or "")


if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        h = hits(open(f, encoding="utf-8").read())
        if h:
            bad += 1
            print(f"{f}: {len(h)}")
    sys.exit(1 if bad else 0)
