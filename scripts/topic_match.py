# -*- coding: utf-8 -*-
"""Topic alias matching shared by gen-topics.py and gen-entry-pages.py (one rule, so hubs and entry pages agree).
2026-11-25: plain substring matching tagged entries by accident — the OpenAI alias 'Sol' hit 'Apex Enterprise Solutions' and
'sold', the ByteDance alias 字节 hit 每字节比特 (bits per byte). Rule now:
  - an ASCII-only alias matches on word boundaries (no letter or digit right before or after it), case-insensitive;
  - 字节 does not match the byte unit (每字节 / 逐字节 / 千字节 / 字节比特 / a number followed by 字节);
  - any other alias (CJK) matches as a substring, as before."""
import re

_ASCII = re.compile(r"[A-Za-z0-9 .\-+&']+")
_CACHE = {}

def _rx(alias):
    r = _CACHE.get(alias)
    if r is None:
        if _ASCII.fullmatch(alias):
            r = re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])", re.I)
        elif alias == "字节":
            r = re.compile(r"(?<![每逐千兆0-9])(?<![0-9] )字节(?!比特|数|码)")   # 每字节 / 逐字节 / 千字节 are byte units
        else:
            r = None
        _CACHE[alias] = r
    return r

def hit(alias, text):
    """True when alias is mentioned in text under the rule above."""
    r = _rx(alias)
    return bool(r.search(text)) if r is not None else alias.lower() in text.lower()

def matches(topic, text):
    return any(hit(a, text) for a in [topic["name"]] + topic.get("aliases", []))
