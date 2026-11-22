#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine timestamps of an ENTRY (2026-11-22, approved by the author): what crawlers and feed readers are told about when an
entry was published and last changed. Shared by gen-entries-en.py, gen-entry-pages.py and gen-topics.py. Not a CLI.

Publication date P
    A backfill (补记) is an entry written after its event: 「本篇写于 YYYY-MM-DD」 in the entry, or 「（M/D 补记）」 on its date line
    (ENTRY 126/127), later than its full event date (entry_dates.written_of: the rule gen-ledger.py uses for written_date in
    data/ledger.json). Its P is the written date; every other entry's P is its entry (event) date, so nothing changes for it.
Time of day
    data/published-times.json {"N": "HH:MM:SS"}: frozen the first time a generator sees ENTRY N in index.html's top-5 BlogPosting
    @graph, i.e. the hour buildN.py wrote (make_daily.py: the publishing hour, 08 for a backfill); an entry never seen there
    (everything before ENTRY 162) keeps 13:00:00, the time its page has always shown. Before 2026-11-22 a page took the time from
    the @graph while the entry was in the top 5 and fell back to 13:00 once it dropped out, so datePublished moved 5 hours a few
    days after publication. All times are +08:00.
datePublished = P + time; dateModified is never earlier than datePublished (max). A date the footnote or the ledger names that
    is on or before a backfill's written date is not a change after publication.
Where (each writer applies the same rule)
    entries/<N>.html, entries/en/<N>.html  JSON-LD, article:published_time / modified_time, the visible 发布 / Written line;
    entries/, entries/en/, topics/*.html   CollectionPage hasPart datePublished (topic dateModified and sitemap-topics lastmod:
                                            the latest P of the topic's entries);
    index.html, atom.xml, sitemap.xml      post-processing of what buildN.py writes (it stamps the event date): fix_hub() sets a
                                            backfill's top-5 @graph datePublished / dateModified, fix_atom() a backfill's
                                            <published> / <updated> and the feed <updated> (= the latest entry <updated>),
                                            fix_sitemap() buildN.py's page <lastmod> stamps when the newest entry is a backfill.
                                            Run by gen-entry-pages.py, which buildN.py runs after every entry, so the next
                                            buildN.py run reads a fixed tree (it keys on titles, entry numbers, the @graph order
                                            and size, and the first <updated>, which stays the feed's own).
Unchanged: the human-visible timeline date, Day number, entry order (index.html, atom.xml: by ENTRY number, descending, as
    geo-check.py check 6 requires) and titles.
Deterministic and idempotent; the only I/O is data/published-times.json (load_times)."""
import re, os, json, datetime

BASE = "https://cynthia-git11.github.io/clawq-diary/"
BJ = datetime.timezone(datetime.timedelta(hours=8))
TIMES_FILE = "data/published-times.json"
DEFAULT_TOD = "13:00:00"

def pub_date(date_d, written):
    """publication date P: the written date of a backfill, else the entry date (partial "2026-02" for month-only entries)"""
    return written or date_d

def pub_iso(n, date_d, written, times):
    p = pub_date(date_d, written)
    return f"{p}T{times.get(n, DEFAULT_TOD)}+08:00" if len(p) == 10 else p

def _dt(s):
    try: return datetime.datetime.fromisoformat(s)
    except (TypeError, ValueError): return None

def later(a, b):
    """the later of two ISO timestamps (a full timestamp beats a partial date of the same day; ties keep a)"""
    if not a: return b
    if not b: return a
    da, db = _dt(a), _dt(b)
    if da and db and (da.tzinfo is None) == (db.tzinfo is None): return b if db > da else a
    return b if b > a else a

def _graph_block(idx):
    """(start, end) of the index.html JSON-LD block that carries the top-5 BlogPosting @graph (buildN.py's json_block)"""
    i = idx.find('"@type": "BlogPosting"')
    if i < 0: return None
    tag = '<script type="application/ld+json">'; a = idx.rfind(tag, 0, i)
    if a < 0: return None
    a += len(tag); b = idx.find("</script>", i)
    return (a, b) if b > a else None

GRAPH_RE = re.compile(r'("url": "' + re.escape(BASE) + r'#entry-(\d+)",\s*"datePublished": ")([^"]+)(",\s*"dateModified": ")([^"]+)(")')

def graph_times(idx):
    """{N: time of day "HH:MM:SS" (+08:00)} of the entries in index.html's top-5 BlogPosting @graph"""
    gb = _graph_block(idx); out = {}
    if not gb: return out
    for m in GRAPH_RE.finditer(idx, gb[0], gb[1]):
        d = _dt(m.group(3))
        if d and d.tzinfo is not None: out[int(m.group(2))] = d.astimezone(BJ).strftime("%H:%M:%S")
    return out

def load_times(read_root, idx, write_root=None):
    """data/published-times.json, plus the entries index.html's top-5 @graph shows that it does not hold yet (frozen from then on;
    written back to write_root, default read_root, only when something was added). → {N: "HH:MM:SS"}"""
    p = os.path.join(read_root, TIMES_FILE)
    raw = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    times = {int(k): v for k, v in raw.items()}
    new = {n: t for n, t in graph_times(idx).items() if n not in times}
    if new or not os.path.exists(p):
        times.update(new)
        q = os.path.join(write_root or read_root, TIMES_FILE); os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "w", encoding="utf-8").write(json.dumps({str(n): times[n] for n in sorted(times)}, indent=1) + "\n")
    return times

# dates (fix_hub / fix_atom / fix_sitemap): {N: (entry date, backfill written date or "")}, as gen-entry-pages.py reads them with
# entry_dates.backfill_written

def fix_hub(idx, dates, times):
    """index.html top-5 BlogPosting @graph: a backfill's datePublished = its written date (+ frozen time), dateModified = the later
    of the two; non-backfills untouched. Text edit in place (buildN.py re-parses the block and asserts its order and size)."""
    gb = _graph_block(idx)
    if not gb: return idx, []
    changed = []
    def rep(m):
        n = int(m.group(2)); d = dates.get(n)
        if not d or not d[1]: return m.group(0)
        pi = pub_iso(n, d[0], d[1], times); mi = later(m.group(5), pi)
        if (m.group(3), m.group(5)) != (pi, mi): changed.append(n)
        return m.group(1) + pi + m.group(4) + mi + m.group(6)
    blk = GRAPH_RE.sub(rep, idx[gb[0]:gb[1]])
    return idx[:gb[0]] + blk + idx[gb[1]:], changed

def fix_sitemap(sm, dates):
    """sitemap.xml: buildN.py stamps every page <lastmod> carrying the previous stamp with the new entry's event date (「all page
    lastmods carry the latest publish date」). When the newest entry is a backfill and the first <lastmod> is still its event date,
    those stamps become its written date, so the hub pages are not dated before the day they changed and the next buildN.py run
    finds them all on one value again. No-op otherwise (idempotent: afterwards the first <lastmod> is the written date)."""
    if not dates: return sm, False
    date_d, written = dates[max(dates)]
    fm = re.search(r"<lastmod>([^<]+)</lastmod>", sm)
    if not (written and fm and fm.group(1) == date_d): return sm, False
    return sm.replace(f"<lastmod>{date_d}</lastmod>", f"<lastmod>{written}</lastmod>"), True

ATOM_NUM_RE = re.compile(r"<id>" + re.escape(BASE) + r"entries/(\d+)</id>|href=\"" + re.escape(BASE) + r"entries/(\d+)\.html\"")

def fix_atom(at, dates, times):
    """atom.xml: a backfill's <published> = its written date (+ frozen time), <updated> = the later of the two; the feed <updated>
    (the first one, before any <entry>, which buildN.py reads and rewrites) = the latest entry <updated>. Entries keep their order
    (ENTRY number, descending) and are found by their title 「ENTRY N · 」; an <id> or alternate link naming another number is skipped."""
    changed = []
    def ent(m):
        blk = m.group(0)
        tm = re.search(r"<title>ENTRY (\d+) ", blk)
        if not tm: return blk
        n = int(tm.group(1)); d = dates.get(n)
        if not d or not d[1]: return blk
        named = {int(x) for g in ATOM_NUM_RE.findall(blk) for x in g if x}
        if named - {n}: return blk
        pm = re.search(r"<published>([^<]+)</published>", blk); um = re.search(r"<updated>([^<]+)</updated>", blk)
        if not (pm and um): return blk
        pi = pub_iso(n, d[0], d[1], times); ui = later(um.group(1), pi)
        if (pm.group(1), um.group(1)) == (pi, ui): return blk
        changed.append(n)
        return blk.replace(pm.group(0), f"<published>{pi}</published>", 1).replace(um.group(0), f"<updated>{ui}</updated>", 1)
    at2 = re.sub(r"<entry>.*?</entry>", ent, at, flags=re.S)
    first_entry = at2.find("<entry>")
    fm = re.search(r"<updated>([^<]+)</updated>", at2)
    if fm and 0 <= first_entry and fm.start() < first_entry:
        ups = [um.group(1) for um in (re.search(r"<updated>([^<]+)</updated>", b) for b in re.findall(r"<entry>.*?</entry>", at2, flags=re.S)) if um]
        if ups:
            top = ups[0]
            for u in ups[1:]: top = later(top, u)
            if top != fm.group(1):
                at2 = at2[:fm.start(1)] + top + at2[fm.end(1):]; changed.append("feed")
    return at2, changed
