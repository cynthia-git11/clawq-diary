#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
倩小虾日记 · 访问数据日报生成器（真实数据版）

数据源：自建 Cloudflare Worker + D1（~/clawq-analytics-worker）
  环境变量 CLAWQ_STATS_URL 指向 Worker，例：
    export CLAWQ_STATS_URL=https://clawq-analytics.xxx.workers.dev

⚠️ 设计原则：拿不到真实数据就明确写"暂无数据"，**绝不回退造假**。
   （2026-08-03 前本脚本产出的是 random.seed 生成的模拟数据，已废弃。）
"""
import json, datetime, os, sys, urllib.request, urllib.error

STATS_URL = os.environ.get("CLAWQ_STATS_URL", "").rstrip("/")
DAYS = int(os.environ.get("TRAFFIC_DAYS", "30"))

try:
    from zoneinfo import ZoneInfo
    TODAY = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).date()
except Exception:
    TODAY = datetime.date.today()

CN_NAME = {
    "CN": ("中国大陆", "\U0001F1E8\U0001F1F3"), "US": ("美国", "\U0001F1FA\U0001F1F8"),
    "HK": ("中国香港", "\U0001F1ED\U0001F1F0"), "SG": ("新加坡", "\U0001F1F8\U0001F1EC"),
    "JP": ("日本", "\U0001F1EF\U0001F1F5"), "TW": ("中国台湾", "\U0001F1F9\U0001F1FC"),
    "GB": ("英国", "\U0001F1EC\U0001F1E7"), "CA": ("加拿大", "\U0001F1E8\U0001F1E6"),
    "DE": ("德国", "\U0001F1E9\U0001F1EA"), "KR": ("韩国", "\U0001F1F0\U0001F1F7"),
    "AU": ("澳大利亚", "\U0001F1E6\U0001F1FA"), "XX": ("其他", "\U0001F310"),
}
PAGE_NAME = {"index.html": "中文 (index)", "en.html": "English (en)",
             "ja.html": "日本語 (ja)", "theses.html": "判断总账 (theses)",
             "analytics.html": "数据看板", "": "中文 (index)"}


def fetch_stats():
    """拉真实数据；失败返回 None（不造假）。"""
    if not STATS_URL:
        return None, "未配置 CLAWQ_STATS_URL（Worker 尚未部署）"
    url = f"{STATS_URL}/stats?days={DAYS}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "clawq-traffic-report"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"Worker 返回 HTTP {e.code}"
    except Exception as e:
        return None, f"连接 Worker 失败：{type(e).__name__}"


def mmss(x):
    x = int(x or 0)
    return f"{x // 60}分{x % 60:02d}秒"


def pct_delta(cur, prev):
    if not prev:
        return "—"
    return f"{(cur - prev) / prev * 100:+.0f}%"


stats, err = fetch_stats()

# ────────────────────────── 无数据：明确标注，不造假 ──────────────────────────
if stats is None or not stats.get("daily"):
    reason = err or "Worker 已连通但暂无访问记录"
    out = {
        "generated": TODAY.isoformat(), "range_days": DAYS,
        "source": "none", "status": "no-data", "note": reason,
        "totals": {"pv": 0, "uniques": 0, "median_time_sec": 0, "completion_rate": 0, "shares": 0},
        "daily": [], "countries": [], "by_lang": [],
    }
    with open("assets/js/analytics-data.js", "w", encoding="utf-8") as f:
        f.write("/* 自建追踪 · 真实数据源（Cloudflare Worker + D1）· 当前无数据 */\n")
        f.write("window.CLAWQ_ANALYTICS = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n")

    md = [
        "# 📊 倩小虾日记 · 访问数据日报", "",
        f"> 生成于 {TODAY.isoformat()} · 数据源：自建 Cloudflare Worker + D1（无第三方、无 cookie）", "",
        "## ⚠️ 暂无真实数据", "",
        f"原因：{reason}", "",
        "本报告**不再生成模拟数据**。2026-08-03 之前的历史数字均为演示用模拟值，已作废。",
        "接入步骤见 `~/clawq-analytics-worker/DEPLOY.md`。", "",
        "---",
        "📈 看板：[analytics.html](https://cynthia-git11.github.io/clawq-diary/analytics.html)",
    ]
    with open("TRAFFIC-REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"NO-DATA · {reason} · 已写入占位（未造假）")
    sys.exit(0)

# ────────────────────────── 有真实数据 ──────────────────────────
daily = stats["daily"]
tot = stats["totals"]
tot_pv = tot.get("pv", 0)

countries = []
for c in stats.get("countries", []):
    name, flag = CN_NAME.get(c.get("code", "XX"), (c.get("code", "XX"), "\U0001F310"))
    countries.append({"name": name, "code": c.get("code"), "flag": flag,
                      "pct": c.get("pct", 0), "pv": c.get("pv", 0)})

by_lang = []
for p in stats.get("pages", []):
    label = PAGE_NAME.get(p.get("page", ""), p.get("page", ""))
    by_lang.append({"lang": label,
                    "pct": round(p.get("pv", 0) / tot_pv, 3) if tot_pv else 0})

out = {
    "generated": stats.get("generated", TODAY.isoformat()),
    "range_days": stats.get("range_days", DAYS),
    "source": "self-hosted-worker-d1", "status": "live",
    "totals": tot, "daily": daily, "countries": countries, "by_lang": by_lang,
    "referrers": stats.get("referrers", []),
}
with open("assets/js/analytics-data.js", "w", encoding="utf-8") as f:
    f.write("/* 自建追踪 · 真实数据（Cloudflare Worker + D1）· 无第三方、无 cookie、不存 PII */\n")
    f.write("window.CLAWQ_ANALYTICS = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n")

y = daily[-1]
p = daily[-2] if len(daily) > 1 else {}
read_cnt = round(y.get("pv", 0) * (y.get("completion_rate") or 0))
md = [
    "# 📊 倩小虾日记 · 访问数据日报", "",
    f"> 生成于 {out['generated']} · 数据区间 {daily[0]['date']} → {daily[-1]['date']}"
    f"（{len(daily)} 天）· 数据源：自建 Cloudflare Worker + D1 · 无第三方、无 cookie、不存 PII", "",
    f"## 今日快报（{y['date']}）", "",
    "| 指标 | 今日 | 环比昨日 |", "|---|---|---|",
    f"| 浏览量 PV | {y.get('pv',0)} | {pct_delta(y.get('pv',0), p.get('pv',0))} |",
    f"| 独立访客 UV | {y.get('uniques',0)} | {pct_delta(y.get('uniques',0), p.get('uniques',0))} |",
    f"| 停留中位数 | {mmss(y.get('median_time_sec'))} | {pct_delta(y.get('median_time_sec',0), p.get('median_time_sec',0))} |",
    f"| 完读率 | {(y.get('completion_rate') or 0)*100:.0f}%（约 {read_cnt} 人读完整篇）"
    f"| {pct_delta(y.get('completion_rate') or 0, p.get('completion_rate') or 0)} |",
    f"| 转发 | {y.get('shares',0)} | {pct_delta(y.get('shares',0), p.get('shares',0))} |", "",
    f"## {len(daily)} 天累计", "",
    f"- **总浏览量** {tot_pv:,}（日均 {round(tot_pv/max(len(daily),1)):,}）· **独立访客** {tot.get('uniques',0):,}",
    f"- **停留中位数** {mmss(tot.get('median_time_sec'))} · **平均完读率** {(tot.get('completion_rate') or 0)*100:.0f}%"
    f" · **总转发** {tot.get('shares',0)}",
]
if len(daily) > 1 and daily[0].get("pv"):
    md.append(f"- 趋势：{daily[0]['date']} {daily[0]['pv']} PV → {daily[-1]['date']} {daily[-1]['pv']} PV"
              f"（{daily[-1]['pv']/daily[0]['pv']:.1f}x）")
md += ["", "## 访问来源 Top 5", ""]
for c in countries[:5]:
    md.append(f"- {c['flag']} {c['name']}：{c['pct']*100:.1f}%（{c['pv']:,} PV）")
if stats.get("referrers"):
    md += ["", "## 来路 Top 5", ""]
    for r in stats["referrers"][:5]:
        md.append(f"- {r.get('ref','(direct)')}：{r.get('pv',0):,} PV")
md += ["", "---", "📈 完整看板：[analytics.html](https://cynthia-git11.github.io/clawq-diary/analytics.html)"]
with open("TRAFFIC-REPORT.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print(f"LIVE 今日 {y['date']} PV={y.get('pv',0)} UV={y.get('uniques',0)} "
      f"停留{mmss(y.get('median_time_sec'))} 完读{(y.get('completion_rate') or 0)*100:.0f}%")
print(f"{len(daily)}天 PV={tot_pv:,} UV={tot.get('uniques',0):,}")
