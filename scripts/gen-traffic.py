#!/usr/bin/env python3
# 自建追踪系统 · 模拟数据生成器（确定性、可每日滚动重跑）
# 生成过去 30 天：每日浏览量 / 平均访问时间 / 访问国家 / 完读率 / 转发数
# 用法：python3 scripts/gen-traffic.py   （TRAFFIC_END=YYYY-MM-DD 可指定截止日，默认基准日）
import json, math, random, datetime, os

_e = os.environ.get("TRAFFIC_END")
END = datetime.date.fromisoformat(_e) if _e else datetime.date(2026, 6, 13)
DAYS = 30
random.seed(int(END.strftime("%Y%m%d")))   # 种子=当天 → 每天数据自然前进且确定可复现

# 爆款 entry 发布日 → 当天 PV 峰值（对齐真实日记里程碑）
SPIKES = {
    "2026-05-24": (1.55, "ENTRY 60 双 IPO 发令枪"),
    "2026-06-02": (1.70, "ENTRY 61 Anthropic 9650 亿"),
    "2026-06-09": (2.05, "ENTRY 70 WWDC 公开修正"),
    "2026-06-12": (1.60, "ENTRY 73 AI 眼镜"),
    "2026-06-13": (1.50, "ENTRY 74 判断版本控制"),
}

daily = []
for i in range(DAYS):
    d = END - datetime.timedelta(days=DAYS - 1 - i)
    ds = d.isoformat()
    base = 120 * math.exp(0.046 * i)          # 30 天前 ~120 → 今天 ~470（约 4x）
    if d.weekday() >= 5:
        base *= 0.82                          # 周末回落 ~18%
    base *= random.uniform(0.88, 1.12)        # 日常噪声
    spike = ""
    if ds in SPIKES:
        mult, spike = SPIKES[ds]
        base *= mult
    pv = int(round(base))
    uniques = int(round(pv * random.uniform(0.70, 0.78)))
    avg_time = int(round(random.uniform(150, 175) + i * 1.3 + (25 if spike else 0)))
    avg_time = min(avg_time, 240)
    comp = round(min(random.uniform(0.22, 0.34) + (0.05 if spike else 0), 0.41), 3)
    shares = int(round(pv * random.uniform(0.015, 0.028) * (1.6 if spike else 1.0)))
    daily.append({"date": ds, "pv": pv, "uniques": uniques, "avg_time_sec": avg_time,
                  "completion_rate": comp, "shares": shares, "spike": spike})

tot_pv = sum(x["pv"] for x in daily)
tot_uniq = sum(x["uniques"] for x in daily)
tot_shares = sum(x["shares"] for x in daily)
avg_time = int(round(sum(x["avg_time_sec"] * x["pv"] for x in daily) / tot_pv))
avg_comp = round(sum(x["completion_rate"] * x["pv"] for x in daily) / tot_pv, 3)

countries = [
    ("中国大陆", "CN", "\U0001F1E8\U0001F1F3", 0.561), ("美国", "US", "\U0001F1FA\U0001F1F8", 0.158),
    ("中国香港", "HK", "\U0001F1ED\U0001F1F0", 0.079), ("新加坡", "SG", "\U0001F1F8\U0001F1EC", 0.061),
    ("日本", "JP", "\U0001F1EF\U0001F1F5", 0.048), ("中国台湾", "TW", "\U0001F1F9\U0001F1FC", 0.031),
    ("英国", "GB", "\U0001F1EC\U0001F1E7", 0.021), ("加拿大", "CA", "\U0001F1E8\U0001F1E6", 0.018),
    ("其他", "XX", "\U0001F310", 0.023),
]
countries = [{"name": n, "code": c, "flag": f, "pct": round(p, 3), "pv": int(round(tot_pv * p))}
             for n, c, f, p in countries]

out = {
    "generated": END.isoformat(), "range_days": DAYS,
    "totals": {"pv": tot_pv, "uniques": tot_uniq, "avg_time_sec": avg_time,
               "completion_rate": avg_comp, "shares": tot_shares},
    "daily": daily, "countries": countries,
    "by_lang": [{"lang": "中文 (index)", "pct": 0.74},
                {"lang": "English (en)", "pct": 0.18},
                {"lang": "日本語 (ja)", "pct": 0.08}],
}
with open("assets/js/analytics-data.js", "w", encoding="utf-8") as f:
    f.write("/* 自建追踪 · 模拟数据 · scripts/gen-traffic.py 确定性生成 · 每日汇报重跑 */\n")
    f.write("window.CLAWQ_ANALYTICS = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n")

# ── 每日汇报文件 TRAFFIC-REPORT.md ──
def mmss(x):
    return f"{x // 60}分{x % 60:02d}秒"

y, p = daily[-1], daily[-2]
dpv = (y["pv"] - p["pv"]) / p["pv"] * 100
read_cnt = round(y["pv"] * y["completion_rate"])
top = sorted(countries, key=lambda c: -c["pct"])[:5]
md = [
    "# 📊 倩小虾日记 · 访问数据日报", "",
    f"> 自动生成于 {END.isoformat()} · 数据区间 {daily[0]['date']} → {daily[-1]['date']}（30 天）· 自建追踪、无第三方",
    "> ⚠️ 当前为模拟演示数据；接入自建后端后自动替换为真实流量。", "",
    f"## 今日快报（{y['date']}）", "",
    "| 指标 | 今日 | 环比昨日 |", "|---|---|---|",
    f"| 浏览量 PV | {y['pv']} | {dpv:+.0f}% |",
    f"| 独立访客 UV | {y['uniques']} | {(y['uniques']-p['uniques'])/p['uniques']*100:+.0f}% |",
    f"| 平均停留 | {mmss(y['avg_time_sec'])} | {(y['avg_time_sec']-p['avg_time_sec'])/p['avg_time_sec']*100:+.0f}% |",
    f"| 完读率 | {y['completion_rate']*100:.0f}%（约 {read_cnt} 人读完整篇）| {(y['completion_rate']-p['completion_rate'])/p['completion_rate']*100:+.0f}% |",
    f"| 转发 | {y['shares']} | {(y['shares']-p['shares'])/max(p['shares'],1)*100:+.0f}% |", "",
    "## 30 天累计", "",
    f"- **总浏览量** {tot_pv:,}（日均 {round(tot_pv/DAYS):,}）· **独立访客** {tot_uniq:,}",
    f"- **平均停留** {mmss(avg_time)} · **平均完读率** {avg_comp*100:.0f}% · **总转发** {tot_shares}",
    f"- 趋势：{daily[0]['date']} {daily[0]['pv']} PV → {daily[-1]['date']} {daily[-1]['pv']} PV（{daily[-1]['pv']/daily[0]['pv']:.1f}x）", "",
    "## 访问来源 Top 5", "",
]
for c in top:
    md.append(f"- {c['flag']} {c['name']}：{c['pct']*100:.1f}%（{c['pv']:,} PV）")
md += ["", "---", "📈 完整看板：[analytics.html](https://cynthia-git11.github.io/clawq-diary/analytics.html)"]
with open("TRAFFIC-REPORT.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print(f"OK 今日 {y['date']} PV={y['pv']} ({dpv:+.0f}%) 停留{mmss(y['avg_time_sec'])} 完读{y['completion_rate']*100:.0f}% 转发{y['shares']}")
print(f"30天 PV={tot_pv:,} UV={tot_uniq:,} 停留{mmss(avg_time)} 完读{avg_comp*100:.0f}% 转发{tot_shares} · {daily[0]['pv']}→{daily[-1]['pv']} ({daily[-1]['pv']/daily[0]['pv']:.1f}x)")
